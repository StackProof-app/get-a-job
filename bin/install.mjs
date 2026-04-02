#!/usr/bin/env node

import { fileURLToPath } from 'url';
import { dirname, join, resolve } from 'path';
import { cpSync, mkdirSync, readdirSync, existsSync } from 'fs';
import { execFileSync } from 'child_process';
import { homedir } from 'os';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const pkgRoot = resolve(__dirname, '..');

const claudeDir = join(homedir(), '.claude');
const skillDir = join(claudeDir, 'skills', 'gaj');
const cmdDir = join(claudeDir, 'commands', 'gaj');

const BEIGE = '\x1b[38;2;216;199;178m';
const GREEN = '\x1b[32m';
const RESET = '\x1b[0m';

// Banner
console.log('');
console.log(BEIGE + '   ██████╗  █████╗      ██╗' + RESET);
console.log(BEIGE + '  ██╔════╝ ██╔══██╗     ██║' + RESET);
console.log(BEIGE + '  ██║  ███╗███████║     ██║' + RESET);
console.log(BEIGE + '  ██║   ██║██╔══██║██   ██║' + RESET);
console.log(BEIGE + '  ╚██████╔╝██║  ██║╚█████╔╝' + RESET);
console.log(BEIGE + '   ╚═════╝ ╚═╝  ╚═╝ ╚════╝' + RESET);
console.log('');
console.log(BEIGE + '  Get A Job' + RESET + '  v1.0.0');
console.log('  Run your job search from Claude Code. By StackProof.app');
console.log('');

// Create target directories
mkdirSync(skillDir, { recursive: true });
mkdirSync(cmdDir, { recursive: true });

// Copy root SKILL.md
cpSync(join(pkgRoot, 'SKILL.md'), join(skillDir, 'SKILL.md'));

// Copy sub-skills (skills/*/SKILL.md)
const skillsSource = join(pkgRoot, 'skills');
for (const sub of readdirSync(skillsSource, { withFileTypes: true })) {
  if (!sub.isDirectory()) continue;
  const srcFile = join(skillsSource, sub.name, 'SKILL.md');
  if (!existsSync(srcFile)) continue;
  const destDir = join(skillDir, 'skills', sub.name);
  mkdirSync(destDir, { recursive: true });
  cpSync(srcFile, join(destDir, 'SKILL.md'));
}

// Copy command stubs (commands/*.md)
const cmdsSource = join(pkgRoot, 'commands');
for (const file of readdirSync(cmdsSource)) {
  if (!file.endsWith('.md')) continue;
  cpSync(join(cmdsSource, file), join(cmdDir, file));
}

// Copy prompts (prompts/*.md)
const promptsSource = join(pkgRoot, 'prompts');
const promptsDest = join(skillDir, 'prompts');
mkdirSync(promptsDest, { recursive: true });
for (const file of readdirSync(promptsSource)) {
  if (!file.endsWith('.md')) continue;
  cpSync(join(promptsSource, file), join(promptsDest, file));
}

// Copy scripts
const scriptsSource = join(pkgRoot, 'scripts');
const scriptsDest = join(skillDir, 'scripts');
mkdirSync(scriptsDest, { recursive: true });
for (const file of readdirSync(scriptsSource)) {
  cpSync(join(scriptsSource, file), join(scriptsDest, file));
}

// Copy package.json and tsconfig.json for the CLI tool
cpSync(join(pkgRoot, 'package.json'), join(skillDir, 'package.json'));
cpSync(join(pkgRoot, 'tsconfig.json'), join(skillDir, 'tsconfig.json'));

console.log(GREEN + '  ✓' + RESET + ' Installed skills/gaj');
console.log(GREEN + '  ✓' + RESET + ' Installed commands/gaj');

// Install production dependencies
try {
  execFileSync('npm', ['install', '--production', '--silent'], {
    cwd: skillDir,
    stdio: 'pipe',
  });
  console.log(GREEN + '  ✓' + RESET + ' Installed dependencies');
} catch (err) {
  console.error('  ✗ Failed to install dependencies:', err.message);
  process.exit(1);
}

console.log('');
console.log('  Done! Run /gaj:help to get started.');
console.log('');
