#!/usr/bin/env npx tsx
// pipeline-cli.ts — CLI for GAJ pipeline management
// Usage: npx tsx scripts/pipeline-cli.ts <command> [args...]
//
// Commands:
//   list [status]              — List jobs, optionally filtered by status
//   add <json>                 — Add a job from JSON object
//   update <id> <field> <val>  — Update a field on a job
//   salary-lookup <role> [level] [location] — Look up market salary data
//   status <id> <new-status>   — Change job status
//   search <query>             — Search jobs by company or title
//   stats                      — Pipeline statistics
//   log-message <json>         — Log a correspondence message
//   get-correspondence <id>    — Get correspondence history for a job

import Database from 'better-sqlite3';
import { existsSync } from 'fs';
import { join } from 'path';
import { homedir } from 'os';

const DB_PATH = join(homedir(), 'gaj', 'gaj.db');

if (!existsSync(DB_PATH)) {
  console.error(JSON.stringify({
    error: 'Database not found. Run setup first: npx tsx scripts/setup-db.ts'
  }));
  process.exit(1);
}

const db = new Database(DB_PATH);
const [, , command, ...args] = process.argv;

function list(statusFilter?: string) {
  let query = 'SELECT id, company_name, job_title, status, source, salary_raw, created_at, url FROM jobs';
  const params: string[] = [];
  if (statusFilter) {
    query += ' WHERE status = ?';
    params.push(statusFilter);
  }
  query += ' ORDER BY created_at DESC';
  const rows = db.prepare(query).all(...params) as Record<string, unknown>[];
  if (rows.length === 0) {
    console.log(JSON.stringify({ count: 0, jobs: [] }));
    return;
  }
  console.log(JSON.stringify({
    count: rows.length,
    jobs: rows.map(r => ({
      id: r.id,
      company: r.company_name,
      role: r.job_title,
      status: r.status,
      source: r.source,
      salary: r.salary_raw,
      url: r.url,
      added: (r.created_at as string)?.split('T')[0]
    }))
  }, null, 2));
}

function add(jsonStr: string) {
  const data = JSON.parse(jsonStr);
  const dedupKey = `${(data.company_name || '').toLowerCase().replace(/[^a-z0-9]+/g, '-')}-${(data.job_title || '').toLowerCase().replace(/[^a-z0-9]+/g, '-')}`;
  const normalizedUrl = (data.url || '').split('?')[0].replace(/\/+$/, '');
  const result = db.prepare(`
    INSERT INTO jobs (company_name, job_title, status, source, url, salary_raw, job_data, dedup_key, normalized_url)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(
    data.company_name || '',
    data.job_title || '',
    data.status || 'pending-review',
    data.source || 'manual',
    data.url || '',
    data.salary_raw || '',
    data.job_data ? JSON.stringify(data.job_data) : '{}',
    dedupKey,
    normalizedUrl
  );
  console.log(JSON.stringify({
    inserted: result.lastInsertRowid,
    company: data.company_name,
    role: data.job_title,
    status: data.status || 'pending-review'
  }));
}

function updateField(id: string, field: string, value: string) {
  const allowedFields = [
    'status', 'company_name', 'job_title', 'salary_raw', 'source', 'url',
    'outcome', 'current_step', 'match_result', 'cover_letter',
    'cover_letter_edited', 'cover_letter_doc_url', 'applied_via', 'research_notes',
    'job_data'
  ];
  if (!allowedFields.includes(field)) {
    console.error(JSON.stringify({
      error: `Field '${field}' not allowed. Allowed: ${allowedFields.join(', ')}`
    }));
    process.exit(1);
  }

  const numericId = Number(id);
  let targetId: number | bigint;

  if (!isNaN(numericId)) {
    // Direct ID lookup
    const row = db.prepare('SELECT id FROM jobs WHERE id = ?').get(numericId) as { id: number } | undefined;
    if (!row) {
      console.error(JSON.stringify({ error: `No job found with id ${id}` }));
      process.exit(1);
    }
    targetId = row.id;
  } else {
    // Partial match by company name
    const row = db.prepare('SELECT id FROM jobs WHERE company_name LIKE ? LIMIT 1').get(`%${id}%`) as { id: number } | undefined;
    if (!row) {
      console.error(JSON.stringify({ error: `No job found matching '${id}'` }));
      process.exit(1);
    }
    targetId = row.id;
  }

  db.prepare(`UPDATE jobs SET ${field} = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?`).run(value, targetId);
  console.log(JSON.stringify({ updated: targetId, field, value }));
}

function search(query: string) {
  const rows = db.prepare(
    'SELECT id, company_name, job_title, status, source, salary_raw, url, created_at FROM jobs WHERE company_name LIKE ? OR job_title LIKE ? ORDER BY created_at DESC'
  ).all(`%${query}%`, `%${query}%`) as Record<string, unknown>[];
  console.log(JSON.stringify({
    query,
    count: rows.length,
    jobs: rows.map(r => ({
      id: r.id,
      company: r.company_name,
      role: r.job_title,
      status: r.status,
      source: r.source,
      salary: r.salary_raw,
      url: r.url,
      added: (r.created_at as string)?.split('T')[0]
    }))
  }, null, 2));
}

function stats() {
  const total = (db.prepare('SELECT COUNT(*) as c FROM jobs').get() as { c: number }).c;
  const byStatus = db.prepare('SELECT status, COUNT(*) as c FROM jobs GROUP BY status ORDER BY c DESC').all() as { status: string; c: number }[];
  const bySource = db.prepare('SELECT source, COUNT(*) as c FROM jobs GROUP BY source ORDER BY c DESC').all() as { source: string; c: number }[];
  console.log(JSON.stringify({
    total,
    by_status: Object.fromEntries(byStatus.map(r => [r.status, r.c])),
    by_source: Object.fromEntries(bySource.map(r => [r.source, r.c]))
  }, null, 2));
}

function logMessage(jsonStr: string) {
  const data = JSON.parse(jsonStr);
  if (!data.job_id || !data.direction || !data.message_text) {
    console.error(JSON.stringify({
      error: 'Required fields: job_id (integer), direction ("inbound" or "outbound"), message_text (string)'
    }));
    process.exit(1);
  }
  if (!['inbound', 'outbound'].includes(data.direction)) {
    console.error(JSON.stringify({ error: 'direction must be "inbound" or "outbound"' }));
    process.exit(1);
  }
  // Verify the job exists
  const job = db.prepare('SELECT id FROM jobs WHERE id = ?').get(data.job_id) as { id: number } | undefined;
  if (!job) {
    console.error(JSON.stringify({ error: `No job found with id ${data.job_id}` }));
    process.exit(1);
  }
  const result = db.prepare(`
    INSERT INTO correspondence (job_id, direction, platform, sender_name, message_text, ai_draft, tone, classification)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
  `).run(
    data.job_id,
    data.direction,
    data.platform || null,
    data.sender_name || null,
    data.message_text,
    data.ai_draft || null,
    data.tone || null,
    data.classification || null
  );
  console.log(JSON.stringify({
    logged: result.lastInsertRowid,
    job_id: data.job_id,
    direction: data.direction,
    classification: data.classification || null
  }));
}

function getCorrespondence(jobIdStr: string) {
  const jobId = Number(jobIdStr);
  if (isNaN(jobId)) {
    console.error(JSON.stringify({ error: 'job-id must be a number' }));
    process.exit(1);
  }
  const rows = db.prepare(
    'SELECT id, job_id, direction, platform, sender_name, message_text, ai_draft, tone, classification, created_at FROM correspondence WHERE job_id = ? ORDER BY created_at ASC'
  ).all(jobId) as Record<string, unknown>[];
  console.log(JSON.stringify({
    job_id: jobId,
    count: rows.length,
    messages: rows.map(r => ({
      id: r.id,
      direction: r.direction,
      platform: r.platform,
      sender: r.sender_name,
      text: r.message_text,
      draft: r.ai_draft,
      tone: r.tone,
      classification: r.classification,
      date: (r.created_at as string)?.split('T')[0]
    }))
  }, null, 2));
}

function salaryLookup(role: string, level?: string, location?: string) {
  if (!role) {
    console.error(JSON.stringify({ error: 'role is required. Usage: salary-lookup <role> [level] [location]' }));
    process.exit(1);
  }
  let query = 'SELECT role, level, location, p25, p50, p75 FROM salary_data WHERE role LIKE ?';
  const params: string[] = [`%${role}%`];
  if (level) {
    query += ' AND level LIKE ?';
    params.push(`%${level}%`);
  }
  if (location) {
    query += ' AND location LIKE ?';
    params.push(`%${location}%`);
  }
  query += ' ORDER BY role, level, p50 DESC';
  const rows = db.prepare(query).all(...params) as { role: string; level: string; location: string; p25: number; p50: number; p75: number }[];
  if (rows.length === 0) {
    console.log(JSON.stringify({
      query: { role, level: level || null, location: location || null },
      count: 0,
      data: [],
      message: 'No matching salary data found'
    }, null, 2));
    return;
  }
  console.log(JSON.stringify({
    query: { role, level: level || null, location: location || null },
    count: rows.length,
    data: rows.map(r => ({
      role: r.role,
      level: r.level,
      location: r.location,
      p25: r.p25,
      p50: r.p50,
      p75: r.p75
    }))
  }, null, 2));
}

function getJob(idStr: string) {
  const numericId = Number(idStr);
  let row: Record<string, unknown> | undefined;

  if (!isNaN(numericId)) {
    row = db.prepare('SELECT * FROM jobs WHERE id = ?').get(numericId) as Record<string, unknown> | undefined;
  } else {
    row = db.prepare('SELECT * FROM jobs WHERE company_name LIKE ? LIMIT 1').get(`%${idStr}%`) as Record<string, unknown> | undefined;
  }

  if (!row) {
    console.error(JSON.stringify({ error: `No job found matching '${idStr}'` }));
    process.exit(1);
  }

  // Parse job_data from JSON string
  let jobData = {};
  try {
    jobData = JSON.parse(row.job_data as string || '{}');
  } catch { /* keep empty */ }

  console.log(JSON.stringify({
    id: row.id,
    company: row.company_name,
    role: row.job_title,
    status: row.status,
    source: row.source,
    salary: row.salary_raw,
    url: row.url,
    job_data: jobData,
    created_at: row.created_at,
    updated_at: row.updated_at
  }, null, 2));
}

switch (command) {
  case 'list':               list(args[0]); break;
  case 'add':                add(args[0]); break;
  case 'update':             updateField(args[0], args[1], args[2]); break;
  case 'status':             updateField(args[0], 'status', args[1]); break;
  case 'search':             search(args[0]); break;
  case 'stats':              stats(); break;
  case 'log-message':        logMessage(args[0]); break;
  case 'get-correspondence': getCorrespondence(args[0]); break;
  case 'get-job':            getJob(args[0]); break;
  case 'salary-lookup':      salaryLookup(args[0], args[1], args[2]); break;
  default:
    console.log('Usage: pipeline-cli.ts <list|add|update|status|search|stats|log-message|get-correspondence|get-job|salary-lookup> [args...]');
    process.exit(1);
}

db.close();
