#!/usr/bin/env npx tsx
// setup-db.ts — Initialize GAJ database at ~/gaj/gaj.db
// Creates tables (jobs, correspondence, salary_data) and seeds salary data.
// Idempotent: safe to run multiple times.

import Database from 'better-sqlite3';
import { mkdirSync, existsSync } from 'fs';
import { join } from 'path';
import { homedir } from 'os';

const GAJ_DIR = join(homedir(), 'gaj');
const DB_PATH = join(GAJ_DIR, 'gaj.db');

// Ensure ~/gaj/ exists
if (!existsSync(GAJ_DIR)) {
  mkdirSync(GAJ_DIR, { recursive: true });
  console.log(`Created directory: ${GAJ_DIR}`);
}

const db = new Database(DB_PATH);
db.pragma('journal_mode = WAL');

const setup = db.transaction(() => {
  // Jobs table
  db.exec(`
    CREATE TABLE IF NOT EXISTS jobs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      company_name TEXT NOT NULL,
      job_title TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'pending-review',
      source TEXT,
      url TEXT,
      salary_raw TEXT,
      salary_min INTEGER,
      salary_max INTEGER,
      cover_letter TEXT,
      cover_letter_edited TEXT,
      applied_via TEXT,
      outcome TEXT,
      current_step TEXT DEFAULT 'qualification',
      match_result TEXT,
      research_notes TEXT,
      cover_letter_doc_url TEXT,
      normalized_url TEXT,
      dedup_key TEXT,
      job_data TEXT DEFAULT '{}',
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
  `);

  // Correspondence table
  db.exec(`
    CREATE TABLE IF NOT EXISTS correspondence (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      job_id INTEGER REFERENCES jobs(id),
      direction TEXT NOT NULL,
      platform TEXT,
      sender_name TEXT,
      message_text TEXT NOT NULL,
      ai_draft TEXT,
      tone TEXT,
      classification TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
  `);

  // Salary data table
  db.exec(`
    CREATE TABLE IF NOT EXISTS salary_data (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      role TEXT NOT NULL,
      level TEXT NOT NULL,
      location TEXT NOT NULL,
      p25 INTEGER NOT NULL,
      p50 INTEGER NOT NULL,
      p75 INTEGER NOT NULL
    )
  `);

  // Seed salary data only if table is empty
  const count = (db.prepare('SELECT COUNT(*) as c FROM salary_data').get() as { c: number }).c;
  if (count === 0) {
    const insert = db.prepare(
      'INSERT INTO salary_data (role, level, location, p25, p50, p75) VALUES (?, ?, ?, ?, ?, ?)'
    );

    const entries: [string, string, string, number, number, number][] = [
      // Software Engineer
      ['Software Engineer', 'Mid',    'SF Bay Area', 155000, 185000, 220000],
      ['Software Engineer', 'Senior', 'SF Bay Area', 200000, 245000, 300000],
      ['Software Engineer', 'Staff',  'SF Bay Area', 280000, 340000, 420000],
      ['Software Engineer', 'Mid',    'NYC',         145000, 175000, 210000],
      ['Software Engineer', 'Senior', 'NYC',         190000, 235000, 285000],
      ['Software Engineer', 'Staff',  'NYC',         265000, 320000, 400000],
      ['Software Engineer', 'Mid',    'Remote US',   130000, 160000, 195000],
      ['Software Engineer', 'Senior', 'Remote US',   170000, 210000, 260000],
      ['Software Engineer', 'Staff',  'Remote US',   230000, 290000, 360000],

      // AI/ML Engineer
      ['AI/ML Engineer', 'Mid',    'SF Bay Area', 170000, 205000, 250000],
      ['AI/ML Engineer', 'Senior', 'SF Bay Area', 220000, 275000, 340000],
      ['AI/ML Engineer', 'Staff',  'SF Bay Area', 310000, 380000, 470000],
      ['AI/ML Engineer', 'Mid',    'NYC',         160000, 195000, 240000],
      ['AI/ML Engineer', 'Senior', 'NYC',         210000, 260000, 320000],
      ['AI/ML Engineer', 'Staff',  'NYC',         290000, 360000, 450000],
      ['AI/ML Engineer', 'Mid',    'Remote US',   145000, 180000, 225000],
      ['AI/ML Engineer', 'Senior', 'Remote US',   190000, 240000, 300000],
      ['AI/ML Engineer', 'Staff',  'Remote US',   260000, 325000, 410000],

      // Engineering Manager
      ['Engineering Manager', 'Mid',    'SF Bay Area', 190000, 230000, 275000],
      ['Engineering Manager', 'Senior', 'SF Bay Area', 240000, 295000, 360000],
      ['Engineering Manager', 'Staff',  'SF Bay Area', 300000, 370000, 450000],
      ['Engineering Manager', 'Mid',    'NYC',         180000, 220000, 265000],
      ['Engineering Manager', 'Senior', 'NYC',         230000, 280000, 340000],
      ['Engineering Manager', 'Staff',  'NYC',         285000, 350000, 430000],
      ['Engineering Manager', 'Mid',    'Remote US',   160000, 200000, 245000],
      ['Engineering Manager', 'Senior', 'Remote US',   200000, 255000, 315000],
      ['Engineering Manager', 'Staff',  'Remote US',   250000, 315000, 395000],
    ];

    for (const entry of entries) {
      insert.run(...entry);
    }

    console.log(`Seeded ${entries.length} salary data entries`);
  } else {
    console.log(`Salary data already exists (${count} entries), skipping seed`);
  }
});

setup();

// Report
const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").all() as { name: string }[];
const salaryCount = (db.prepare('SELECT COUNT(*) as c FROM salary_data').get() as { c: number }).c;

console.log(JSON.stringify({
  database: DB_PATH,
  tables: tables.map(t => t.name),
  salary_entries: salaryCount
}, null, 2));

db.close();
