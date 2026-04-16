// db-path.ts — Shared resolver for GAJ's database location.
// Precedence: env GAJ_DB_PATH → ~/gaj/config.yaml (db_path) → ~/gaj/gaj.db.

import { existsSync, mkdirSync, readFileSync } from 'fs';
import { dirname, join } from 'path';
import { homedir } from 'os';
import { parse as parseYaml } from 'yaml';

const DEFAULT_GAJ_DIR = join(homedir(), 'gaj');
const DEFAULT_DB_PATH = join(DEFAULT_GAJ_DIR, 'gaj.db');
const CONFIG_PATH = join(DEFAULT_GAJ_DIR, 'config.yaml');

export function resolveDbPath(): string {
  const envPath = process.env.GAJ_DB_PATH;
  if (envPath && envPath.trim().length > 0) {
    return envPath.trim();
  }

  if (existsSync(CONFIG_PATH)) {
    try {
      const raw = readFileSync(CONFIG_PATH, 'utf8');
      const parsed = parseYaml(raw) as { db_path?: unknown } | undefined;
      if (parsed && typeof parsed.db_path === 'string' && parsed.db_path.trim().length > 0) {
        return parsed.db_path.trim();
      }
    } catch {
      // Silent fallthrough to default.
    }
  }

  return DEFAULT_DB_PATH;
}

// Creates the parent directory only for paths under ~/gaj. For any other
// location (including the production DB at ANTIGRAVITY PROJECTS), the directory
// must already exist — we refuse to mkdir outside the user's gaj/ sandbox to
// avoid accidentally scaffolding directories in unrelated project trees.
export function ensureDbDir(dbPath: string): void {
  const parent = dirname(dbPath);
  if (parent === DEFAULT_GAJ_DIR) {
    if (!existsSync(parent)) {
      mkdirSync(parent, { recursive: true });
    }
    return;
  }
  if (!existsSync(parent)) {
    throw new Error(
      `DB parent directory does not exist: ${parent}. ` +
        `Create it manually or point GAJ_DB_PATH at a path under ~/gaj/.`
    );
  }
}
