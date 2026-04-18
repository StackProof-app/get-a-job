// profile-path.ts — Shared resolver for GAJ's profile location.
// Precedence: env GAJ_PROFILE_PATH → ~/gaj/config.yaml (profile_path) → ~/gaj/context/profile.yaml.

import { existsSync, mkdirSync, readFileSync } from 'fs';
import { dirname, join } from 'path';
import { homedir } from 'os';
import { parse as parseYaml } from 'yaml';

const DEFAULT_GAJ_DIR = join(homedir(), 'gaj');
const DEFAULT_CONTEXT_DIR = join(DEFAULT_GAJ_DIR, 'context');
const DEFAULT_PROFILE_PATH = join(DEFAULT_CONTEXT_DIR, 'profile.yaml');
const CONFIG_PATH = join(DEFAULT_GAJ_DIR, 'config.yaml');

export function resolveProfilePath(): string {
  const envPath = process.env.GAJ_PROFILE_PATH;
  if (envPath && envPath.trim().length > 0) {
    return envPath.trim();
  }

  if (existsSync(CONFIG_PATH)) {
    try {
      const raw = readFileSync(CONFIG_PATH, 'utf8');
      const parsed = parseYaml(raw) as { profile_path?: unknown } | undefined;
      if (
        parsed &&
        typeof parsed.profile_path === 'string' &&
        parsed.profile_path.trim().length > 0
      ) {
        return parsed.profile_path.trim();
      }
    } catch {
      // Silent fallthrough to default.
    }
  }

  return DEFAULT_PROFILE_PATH;
}

// Mirrors ensureDbDir's scoping philosophy: only mkdir when the parent is the
// user's ~/gaj/context/ sandbox. For any other location, the directory must
// already exist — we refuse to scaffold directories in unrelated project trees.
export function ensureProfileDir(profilePath: string): void {
  const parent = dirname(profilePath);
  if (parent === DEFAULT_CONTEXT_DIR) {
    if (!existsSync(parent)) {
      mkdirSync(parent, { recursive: true });
    }
    return;
  }
  if (!existsSync(parent)) {
    throw new Error(
      `Profile parent directory does not exist: ${parent}. ` +
        `Create it manually or point GAJ_PROFILE_PATH at a path under ~/gaj/context/.`
    );
  }
}
