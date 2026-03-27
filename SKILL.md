---
name: gaj
description: |
  Manage your entire job search from Claude Code. Track opportunities, draft recruiter
  responses, generate cover letters, negotiate salary, triage job alert digests, and run
  detective research on every opportunity. Triggers on /gaj, job pipeline, job search,
  add a job, respond to recruiter, cover letter, negotiate salary, triage inbox, pipeline
  status, or any job search management request.
---

When this skill loads, display the banner:

```bash
echo -e '\033[38;2;216;199;178m   ██████╗  █████╗      ██╗\033[0m'
echo -e '\033[38;2;216;199;178m  ██╔════╝ ██╔══██╗     ██║\033[0m'
echo -e '\033[38;2;216;199;178m  ██║  ███╗███████║     ██║\033[0m'
echo -e '\033[38;2;216;199;178m  ██║   ██║██╔══██║██   ██║\033[0m'
echo -e '\033[38;2;216;199;178m  ╚██████╔╝██║  ██║╚█████╔╝\033[0m'
echo -e '\033[38;2;216;199;178m   ╚═════╝ ╚═╝  ╚═╝ ╚════╝\033[0m'
echo ''
echo -e '\033[38;2;216;199;178m  Get A Job\033[0m  v1.0.0'
```

# GAJ - Job Search Pipeline

Manage your entire job search from Claude Code. Track opportunities, update statuses, search, and get stats.

## Setup check

Before any operation, verify the database exists:

```bash
ls ~/gaj/gaj.db
```

If the database does not exist, run the first-run setup:

1. Create the GAJ directory structure:
   ```bash
   mkdir -p ~/gaj/context
   ```

2. Set up the database:
   ```bash
   npx tsx scripts/setup-db.ts
   ```

3. Create `~/gaj/config.yaml` with default content:
   ```yaml
   # GAJ Configuration
   # Uncomment and fill in to enable Google Sheets sync:
   # sheets_id: "your-google-sheet-id"
   # credentials_path: "~/gaj/credentials.json"
   ```

4. Create `~/gaj/context/about-me.md` with this template:
   ```markdown
   # About Me

   ## Target roles
   <!-- e.g., Senior Software Engineer, Staff Engineer, Engineering Manager -->

   ## Salary floor
   <!-- e.g., $180,000 base (W-2) -->

   ## Preferred tech stack
   <!-- e.g., TypeScript, React, Node.js, PostgreSQL -->

   ## Evaluation criteria
   <!-- What matters most: remote work, team size, product domain, growth path -->

   ## Location preferences
   <!-- e.g., Remote only, SF Bay Area, open to relocation -->

   ## Key achievements
   <!-- 2-3 quantified achievements for cover letters and recruiter responses -->
   ```

5. Tell the user:
   > Database ready. Fill in `~/gaj/context/about-me.md` for personalized cover letters and recruiter responses. Google Sheets sync is optional, configure in `~/gaj/config.yaml`.

6. Run `gaj:stats` to show the empty pipeline dashboard.

Then stop. Do not attempt other pipeline operations until setup completes.

## Routing

When the user gives a natural language instruction, route to the correct sub-command:

| User says | Route |
|-----------|-------|
| "Add [company] [role]" or provides job details | `gaj:add` |
| "What's in my pipeline?" or "Show my jobs" | `gaj:list` |
| "Show [status] jobs" or "List pending jobs" | `gaj:list` |
| "Update [company] to [status]" or "Mark as [status]" | `gaj:status` |
| "Mark [company] as rejected/applied/approved" | `gaj:status` |
| "Find [company]" or "Search for [keyword]" | `gaj:search` |
| "How many jobs?" or "Pipeline stats" | `gaj:stats` |
| "Write a cover letter for [company]" or "Draft a letter" | `gaj:cover-letter` |
| "Reply to recruiter" or "Respond to [name]" | `gaj:respond` |
| "Negotiate salary" or "Counter offer for [company]" | `gaj:negotiate` |
| "Sync to sheets" or "Export pipeline" | `gaj:sync` |
| "Triage these jobs" or "Filter this digest" or pastes multiple jobs | `gaj:triage` |
| "Here's a LinkedIn alert" or "Batch these" or "Inbox buildup" | `gaj:triage` |

If the user invokes `/gaj` without a specific task, run `gaj:stats` and present a pipeline dashboard.

## CLI tool

All database operations go through the pipeline CLI. Run from the GAJ repo directory:

```bash
npx tsx scripts/pipeline-cli.ts <command> [args]
```

The CLI outputs JSON. Never show raw JSON to the user. Always parse it and present as clean markdown tables.

## Job statuses

| Status | Meaning |
|--------|---------|
| `pending-review` | New, awaiting evaluation |
| `approved` | User approved, ready for cover letter |
| `cover-letter-ready` | Cover letter generated |
| `applied` | Application submitted |
| `interview` | Interview stage |
| `offer` | Offer received |
| `rejected` | Rejected by user or company |
| `expired` | Job listing no longer active |
| `filtered` | Filtered out during qualification |

## Output rules

- Present pipeline data as markdown tables with columns: ID, Company, Role, Status, Source, Added
- After mutations (add, update, status change), confirm what changed in one sentence
- When listing jobs, sort by most recent first
- For stats, present totals and breakdowns in a clean summary, not a table dump

## Voice rules

Apply these to all responses when this skill is active:

- No em dashes. Use commas or periods.
- No exclamation marks.
- No "I hope this helps" or "please don't hesitate" or "happy to help."
- No "excited," "thrilled," "delighted," or similar.
- Be direct. Name the company, the role, the number.
- Short responses. State what happened, offer the next logical action, stop.
