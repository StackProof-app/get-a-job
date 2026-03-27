#!/usr/bin/env npx tsx
// sync-sheets.ts — Export GAJ pipeline data to Google Sheets
// Usage: npx tsx scripts/sync-sheets.ts
//
// Reads ~/gaj/config.yaml for:
//   sheets_id: Google Sheet ID
//   credentials_path: Path to OAuth credentials JSON
//
// Exports all jobs to the configured sheet, replacing existing data.

import Database from 'better-sqlite3';
import { existsSync, readFileSync } from 'fs';
import { join } from 'path';
import { homedir } from 'os';
import { google } from 'googleapis';
import { parse } from 'yaml';

const GAJ_DIR = join(homedir(), 'gaj');
const DB_PATH = join(GAJ_DIR, 'gaj.db');
const CONFIG_PATH = join(GAJ_DIR, 'config.yaml');

interface Config {
  sheets_id?: string;
  credentials_path?: string;
}

interface JobRow {
  id: number;
  company_name: string;
  job_title: string;
  status: string;
  source: string;
  salary_raw: string;
  url: string;
  created_at: string;
}

function loadConfig(): Config {
  if (!existsSync(CONFIG_PATH)) {
    console.error(JSON.stringify({
      error: 'Config not found at ~/gaj/config.yaml',
      hint: 'Run /gaj to set up your configuration, or create ~/gaj/config.yaml with sheets_id and credentials_path'
    }));
    process.exit(1);
  }
  const raw = readFileSync(CONFIG_PATH, 'utf-8');
  return parse(raw) || {};
}

async function main() {
  const config = loadConfig();

  if (!config.sheets_id) {
    console.error(JSON.stringify({
      error: 'sheets_id not configured in ~/gaj/config.yaml',
      hint: 'Add: sheets_id: "your-google-sheet-id" to ~/gaj/config.yaml'
    }));
    process.exit(1);
  }

  const credsPath = config.credentials_path
    ? config.credentials_path.replace('~', homedir())
    : join(GAJ_DIR, 'credentials.json');

  if (!existsSync(credsPath)) {
    console.error(JSON.stringify({
      error: `Credentials not found at ${credsPath}`,
      hint: 'Set up Google OAuth credentials: https://console.cloud.google.com/apis/credentials'
    }));
    process.exit(1);
  }

  if (!existsSync(DB_PATH)) {
    console.error(JSON.stringify({
      error: 'Database not found. Run setup first: npx tsx scripts/setup-db.ts'
    }));
    process.exit(1);
  }

  // Load credentials and authenticate
  const creds = JSON.parse(readFileSync(credsPath, 'utf-8'));
  const auth = new google.auth.GoogleAuth({
    credentials: creds,
    scopes: ['https://www.googleapis.com/auth/spreadsheets'],
  });
  const sheets = google.sheets({ version: 'v4', auth });

  // Read all jobs from database
  const db = new Database(DB_PATH);
  const rows = db.prepare(
    'SELECT id, company_name, job_title, status, source, salary_raw, url, created_at FROM jobs ORDER BY created_at DESC'
  ).all() as JobRow[];
  db.close();

  // Build sheet data: header + rows
  const header = ['ID', 'Company', 'Role', 'Status', 'Source', 'Salary', 'URL', 'Date Added'];
  const data = rows.map(r => [
    r.id,
    r.company_name,
    r.job_title,
    r.status,
    r.source,
    r.salary_raw,
    r.url,
    r.created_at?.split('T')[0] || ''
  ]);

  // Clear existing data and write in a single batch
  const range = 'Sheet1';
  await sheets.spreadsheets.values.clear({
    spreadsheetId: config.sheets_id,
    range,
  });
  await sheets.spreadsheets.values.update({
    spreadsheetId: config.sheets_id,
    range: 'Sheet1!A1',
    valueInputOption: 'RAW',
    requestBody: {
      values: [header, ...data],
    },
  });

  console.log(JSON.stringify({
    synced: rows.length,
    sheet_id: config.sheets_id,
    columns: header
  }));
}

main().catch(err => {
  console.error(JSON.stringify({
    error: 'Sync failed',
    message: err.message
  }));
  process.exit(1);
});
