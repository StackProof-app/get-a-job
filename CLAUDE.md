# GAJ (Get A Job)

A unified Claude Code skill for engineers managing their job search. Pipeline tracking, recruiter communication, cover letter generation, salary negotiation, and correspondence history in one install.

## Architecture

- **Type:** Claude Code skill with sub-commands (`gaj:X`)
- **Database:** SQLite via better-sqlite3 at `~/gaj/gaj.db`
- **Config:** YAML at `~/gaj/config.yaml`
- **Pattern:** Like GSD (`gsd:command`) or GVB (`viral:command`). One install, multiple slash commands.
- **Install:** `npx skills add stackproof-app/GAJ`

## Key constraints

- No external API dependencies. Uses the user's own Claude subscription through Claude Code.
- Anti-AI writing rules apply to all generated text. Output should not read like ChatGPT wrote it.
- SQLite is the only data store. No cloud database, no server.
- `~/gaj/` directory is created at runtime, not committed to the repo.
- Google Sheets sync is optional and requires the user's own OAuth credentials.

## Sub-commands

| Command | Purpose |
|---------|---------|
| `/gaj` | Pipeline summary dashboard |
| `/gaj:profile` | View or update search profile |
| `/gaj:add` | Add a job to the pipeline |
| `/gaj:list` | List/filter pipeline items |
| `/gaj:status` | Update job status |
| `/gaj:search` | Search by company/title/keyword |
| `/gaj:stats` | Pipeline statistics |
| `/gaj:cover-letter` | Generate Hook/Proof/Close cover letter |
| `/gaj:respond` | Assess interest and draft recruiter response |
| `/gaj:negotiate` | Ackerman-based salary negotiation |
| `/gaj:sync` | Export to Google Sheets |

## Development

- Scripts run via `npx tsx scripts/<name>.ts`
- `npm install` for dependencies
- Database setup: `npx tsx scripts/setup-db.ts`
- CLI tool: `npx tsx scripts/pipeline-cli.ts <command> [args]`

## Project management

PAUL framework files in `.paul/` track project state, plans, and roadmap. Do not modify `.paul/` files directly during feature work.
