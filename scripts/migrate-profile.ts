#!/usr/bin/env tsx
// migrate-profile.ts — One-shot interactive filler that writes ~/gaj/context/profile.yaml.
// Pre-fills from ~/gaj/gaj.json where possible; prompts for ATS-critical fields
// not present in gaj.json. Flags: --dry-run, --force.

import { copyFileSync, existsSync, readFileSync, writeFileSync } from 'fs';
import { join } from 'path';
import { homedir } from 'os';
import { stringify as stringifyYaml } from 'yaml';
import { createInterface } from 'node:readline';
import { stdin as input, stdout as output } from 'node:process';
import { resolveProfilePath, ensureProfileDir } from './lib/profile-path.js';
import {
  defaultProfile,
  validateProfile,
  type Profile,
  type WorkAuthStatus,
  type EmploymentStatus,
  type EeocGender,
  type EeocEthnicity,
  type EeocVeteranStatus,
  type EeocDisabilityStatus,
  type ResumeVariant,
} from './lib/profile-schema.js';

interface GajJsonShape {
  profile?: {
    name?: string;
    email?: string;
    location?: string;
    linkedin?: string;
    github?: string;
    target_roles?: string[];
    employment_types?: string[];
    resume_variants?: Record<string, string>;
    tech_stack?: string[];
  };
  context?: {
    resume?: string;
  };
}

const GAJ_JSON_PATH = join(homedir(), 'gaj', 'gaj.json');

function humanizeKey(key: string): string {
  return key
    .split('_')
    .map((w) => {
      if (w.toLowerCase() === 'ai') return 'AI';
      if (w.length === 0) return w;
      return w.charAt(0).toUpperCase() + w.slice(1);
    })
    .join(' ');
}

function withScheme(url: string): string {
  const trimmed = url.trim();
  if (trimmed === '') return '';
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  return `https://${trimmed}`;
}

function parseLocation(loc: string): { city: string; state: string } {
  const m = loc.trim().match(/^(.+?),\s*([A-Z]{2})$/);
  if (!m) return { city: '', state: '' };
  return { city: m[1]!.trim(), state: m[2]! };
}

function loadGajJson(): GajJsonShape | null {
  if (!existsSync(GAJ_JSON_PATH)) return null;
  try {
    const raw = readFileSync(GAJ_JSON_PATH, 'utf8');
    return JSON.parse(raw) as GajJsonShape;
  } catch (err) {
    console.error(
      `Could not parse ${GAJ_JSON_PATH}: ${(err as Error).message}. Starting from defaults.`
    );
    return null;
  }
}

function prefillFromGajJson(profile: Profile, gaj: GajJsonShape): Profile {
  const p = gaj.profile ?? {};
  const log = (msg: string) => console.error(`  pre-fill: ${msg}`);

  if (p.name) {
    profile.identity.full_name = p.name;
    log('identity.full_name ← gaj.json profile.name');
  }
  if (p.email) {
    profile.identity.email = p.email;
    log('identity.email ← gaj.json profile.email');
  }
  if (p.linkedin) {
    profile.identity.linkedin_url = withScheme(p.linkedin);
    log('identity.linkedin_url ← gaj.json profile.linkedin');
  }
  if (p.github) {
    profile.identity.github_url = withScheme(p.github);
    log('identity.github_url ← gaj.json profile.github');
  }
  if (p.location) {
    const { city, state } = parseLocation(p.location);
    profile.address.city = city;
    profile.address.state = state;
    log(`address.{city,state} ← gaj.json profile.location (parsed: "${city}"/"${state}")`);
  }
  if (Array.isArray(p.target_roles)) {
    profile.target_roles = [...p.target_roles];
    log(`target_roles ← gaj.json profile.target_roles (${p.target_roles.length} entries)`);
  }
  if (Array.isArray(p.employment_types)) {
    profile.employment_types = [...p.employment_types];
    log('employment_types ← gaj.json profile.employment_types');
  }
  if (p.resume_variants && typeof p.resume_variants === 'object') {
    const resumePath = gaj.context?.resume ?? '';
    const variants: ResumeVariant[] = Object.entries(p.resume_variants).map(
      ([key, useWhen]) => ({
        key,
        label: humanizeKey(key),
        path: resumePath,
        use_when: useWhen,
      })
    );
    profile.resume.variants = variants;
    log(`resume.variants ← gaj.json profile.resume_variants (${variants.length} entries)`);
  }
  // Log prompts ahead-of-time for fields the script always prompts for.
  console.error('  phone: prompting (not in gaj.json)');
  console.error('  work_auth: prompting (not in gaj.json)');
  console.error('  eeoc_voluntary: prompting, all default to decline_to_state');
  console.error('  employment, relocation: prompting with sensible defaults');
  return profile;
}

// Line-queued reader: node:readline/promises mishandles piped stdin across
// sequential questions (consumes all input on the first read). Classic readline
// with a manual line queue + waiter pattern is reliable for both TTY and pipe.
class LineReader {
  private lines: string[] = [];
  private waiters: Array<(s: string) => void> = [];
  private closed = false;
  private rl: ReturnType<typeof createInterface>;

  constructor() {
    this.rl = createInterface({ input, output, terminal: false });
    this.rl.on('line', (line) => {
      const w = this.waiters.shift();
      if (w) w(line);
      else this.lines.push(line);
    });
    this.rl.on('close', () => {
      this.closed = true;
      while (this.waiters.length > 0) {
        const w = this.waiters.shift()!;
        w('');
      }
    });
  }

  async question(prompt: string): Promise<string> {
    output.write(prompt);
    if (this.lines.length > 0) return this.lines.shift()!;
    if (this.closed) return '';
    return new Promise((resolve) => {
      this.waiters.push(resolve);
    });
  }

  close(): void {
    this.rl.close();
  }
}

async function promptText(
  rl: LineReader,
  message: string,
  current: string
): Promise<string> {
  const suffix = current ? ` [${current}]` : '';
  const answer = (await rl.question(`${message}${suffix}: `)).trim();
  if (answer === '') return current;
  return answer;
}

async function promptYesNo(
  rl: LineReader,
  message: string,
  def: boolean
): Promise<boolean> {
  const suffix = def ? ' (Y/n)' : ' (y/N)';
  const answer = (await rl.question(`${message}${suffix}: `)).trim().toLowerCase();
  if (answer === '') return def;
  if (answer === 'y' || answer === 'yes') return true;
  if (answer === 'n' || answer === 'no') return false;
  return def;
}

async function promptEnum<T extends string>(
  rl: LineReader,
  message: string,
  options: ReadonlyArray<T>,
  def: T
): Promise<T> {
  const lines = [message];
  options.forEach((opt, i) => lines.push(`  ${i + 1}) ${opt}`));
  const defaultIdx = options.indexOf(def) + 1;
  const prompt = `${lines.join('\n')}\nChoose 1-${options.length} [${defaultIdx}]: `;
  const answer = (await rl.question(prompt)).trim();
  if (answer === '') return def;
  const asInt = Number.parseInt(answer, 10);
  if (!Number.isNaN(asInt) && asInt >= 1 && asInt <= options.length) {
    return options[asInt - 1]!;
  }
  if (options.includes(answer as T)) return answer as T;
  console.error(`  Invalid choice, keeping default: ${def}`);
  return def;
}

async function promptInt(
  rl: LineReader,
  message: string,
  def: number
): Promise<number> {
  const answer = (await rl.question(`${message} [${def}]: `)).trim();
  if (answer === '') return def;
  const n = Number.parseInt(answer, 10);
  if (Number.isNaN(n)) return def;
  return n;
}

async function runInteractive(profile: Profile, rl: LineReader): Promise<Profile> {
    console.error('\n--- Identity ---');
    profile.identity.phone = await promptText(
      rl,
      'Phone number (digits, hyphens OK)',
      profile.identity.phone
    );

    console.error('\n--- Work Authorization ---');
    const workAuthOpts: ReadonlyArray<WorkAuthStatus> = [
      'us_citizen',
      'permanent_resident',
      'visa_holder',
      'needs_sponsorship',
    ];
    profile.work_auth.status = await promptEnum(
      rl,
      'Work authorization status?',
      workAuthOpts,
      profile.work_auth.status
    );
    profile.work_auth.sponsorship_required_now = await promptYesNo(
      rl,
      'Sponsorship required NOW to begin employment?',
      profile.work_auth.sponsorship_required_now
    );
    profile.work_auth.sponsorship_required_future = await promptYesNo(
      rl,
      'Sponsorship required in the FUTURE to continue employment?',
      profile.work_auth.sponsorship_required_future
    );

    console.error('\n--- Address (Enter to keep pre-filled value) ---');
    profile.address.city = await promptText(rl, 'City', profile.address.city);
    profile.address.state = await promptText(rl, 'State (2 letters)', profile.address.state);
    profile.address.postal_code = await promptText(
      rl,
      'Postal code',
      profile.address.postal_code
    );
    profile.address.country = await promptText(rl, 'Country', profile.address.country);

    console.error('\n--- Employment ---');
    const employmentOpts: ReadonlyArray<EmploymentStatus> = [
      'employed',
      'unemployed',
      'freelance',
    ];
    profile.employment.current_status = await promptEnum(
      rl,
      'Current employment status?',
      employmentOpts,
      profile.employment.current_status
    );
    profile.employment.notice_period_days = await promptInt(
      rl,
      'Notice period (days)',
      profile.employment.notice_period_days
    );
    profile.employment.earliest_start_date = await promptText(
      rl,
      'Earliest start date (ISO YYYY-MM-DD)',
      profile.employment.earliest_start_date
    );

    console.error('\n--- Relocation ---');
    profile.relocation.willing_to_relocate = await promptYesNo(
      rl,
      'Willing to relocate?',
      profile.relocation.willing_to_relocate
    );

    console.error('\n--- EEOC Voluntary Disclosures (Enter to decline) ---');
    const genderOpts: ReadonlyArray<EeocGender> = [
      'male',
      'female',
      'non_binary',
      'decline_to_state',
    ];
    profile.eeoc_voluntary.gender = await promptEnum(
      rl,
      'Gender?',
      genderOpts,
      profile.eeoc_voluntary.gender
    );
    const ethnicityOpts: ReadonlyArray<EeocEthnicity> = [
      'white',
      'black_or_african_american',
      'hispanic_or_latino',
      'asian',
      'native_american',
      'pacific_islander',
      'two_or_more',
      'decline_to_state',
    ];
    profile.eeoc_voluntary.ethnicity = await promptEnum(
      rl,
      'Ethnicity?',
      ethnicityOpts,
      profile.eeoc_voluntary.ethnicity
    );
    const veteranOpts: ReadonlyArray<EeocVeteranStatus> = [
      'protected_veteran',
      'not_a_veteran',
      'decline_to_state',
    ];
    profile.eeoc_voluntary.veteran_status = await promptEnum(
      rl,
      'Veteran status?',
      veteranOpts,
      profile.eeoc_voluntary.veteran_status
    );
    const disabilityOpts: ReadonlyArray<EeocDisabilityStatus> = [
      'yes',
      'no',
      'decline_to_state',
    ];
    profile.eeoc_voluntary.disability_status = await promptEnum(
      rl,
      'Disability status?',
      disabilityOpts,
      profile.eeoc_voluntary.disability_status
    );

  return profile;
}

async function confirmOverwrite(targetPath: string, rl: LineReader): Promise<boolean> {
  const existing = readFileSync(targetPath, 'utf8');
  const lines = existing.split('\n').slice(0, 15);
  console.error(`\nExisting profile.yaml at: ${targetPath}`);
  console.error('--- First 15 lines ---');
  console.error(lines.join('\n'));
  console.error('--- End preview ---\n');
  const answer = (await rl.question('Overwrite? (y/N): ')).trim().toLowerCase();
  return answer === 'y' || answer === 'yes';
}

function backupExisting(targetPath: string): string {
  const iso = new Date().toISOString().replace(/:/g, '-');
  const backupPath = `${targetPath}.bak.${iso}`;
  copyFileSync(targetPath, backupPath);
  return backupPath;
}

function countFields(obj: unknown, depth = 0): number {
  if (depth > 5) return 0;
  if (Array.isArray(obj)) return obj.length;
  if (typeof obj !== 'object' || obj === null) return 1;
  let count = 0;
  for (const v of Object.values(obj)) {
    count += countFields(v, depth + 1);
  }
  return count;
}

async function main(): Promise<void> {
  const args = process.argv.slice(2);
  const dryRun = args.includes('--dry-run');
  const force = args.includes('--force');

  process.on('SIGINT', () => {
    console.error('\nAborted. No changes written.');
    process.exit(130);
  });

  const targetPath = resolveProfilePath();
  console.error(`Target: ${targetPath}`);

  if (!dryRun) {
    ensureProfileDir(targetPath);
  }

  // Single LineReader shared across overwrite prompt + interactive flow so
  // piped stdin is consumed line-by-line without the reader closing early.
  const rl = !dryRun ? new LineReader() : null;

  if (existsSync(targetPath) && !dryRun && !force) {
    const ok = await confirmOverwrite(targetPath, rl!);
    if (!ok) {
      console.error('No changes.');
      rl?.close();
      process.exit(0);
    }
  }

  let profile = defaultProfile();
  const gaj = loadGajJson();
  if (gaj) {
    console.error(`\nPre-fill source: ${GAJ_JSON_PATH}`);
    profile = prefillFromGajJson(profile, gaj);
  } else {
    console.error('\nNo ~/gaj/gaj.json found. Starting from defaults.');
  }

  if (dryRun) {
    const yaml = stringifyYaml(profile);
    process.stdout.write(yaml);
    return;
  }

  profile = await runInteractive(profile, rl!);
  rl?.close();

  const validation = validateProfile(profile);
  if (!validation.ok) {
    console.error('\nValidation failed:');
    for (const err of validation.errors) {
      console.error(`  - ${err}`);
    }
    process.exit(1);
  }

  if (existsSync(targetPath) && force) {
    const backup = backupExisting(targetPath);
    console.error(`Backed up existing to: ${backup}`);
  }

  const yaml = stringifyYaml(validation.profile);
  writeFileSync(targetPath, yaml, 'utf8');
  const fieldCount = countFields(validation.profile);
  console.error(`\nWrote ${targetPath} (${fieldCount} leaf values).`);
}

main().catch((err) => {
  console.error(`Error: ${(err as Error).message}`);
  process.exit(1);
});
