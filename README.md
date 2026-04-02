<p align="center">
  <img src="assets/banner.png" alt="GAJ - Get A Job" width="400">
</p>

<p align="center">by <a href="https://stackproof.app">StackProof</a></p>

Run your entire job search from the terminal. Investigates everything before you make a move.

Designed for Claude Code. Works with 30+ LLM environments.

## What this is

A recruiter messages you about a "Senior AI role at a leading enterprise software company." You don't know if the recruiter is legitimate, who the actual client is, or whether the comp is real. GAJ figures it out. It runs parallel research agents that check the recruiter's track record, cross-reference the job description against known companies to identify the unnamed client, and verify compensation against market data. You get a detective report before you write a single word back.

Then it drafts your response. Based on the research, GAJ classifies your interest level and generates a calibrated reply: engage and ask the right questions, decline but keep the recruiter warm for future roles, or pass entirely. Every message, inbound and outbound, is stored with full context so nothing falls through the cracks.

Beyond recruiter correspondence: cover letter generation in a Hook/Proof/Close format that doesn't read like AI wrote it. Salary negotiation using the Ackerman model with market data. Batch triage that scores a pile of LinkedIn alerts and surfaces the three worth your time. Pipeline tracking across every stage from first contact to signed offer. All data stays on your machine in SQLite.

## Install

Requires [Claude Code](https://claude.ai/claude-code).

```bash
npx skills add stackproof/GAJ
```

## Quick start

First time you run `/gaj`, setup runs automatically:

1. Creates `~/gaj/` with database and config
2. Seeds salary data (27 roles across levels and locations)
3. Generates `~/gaj/context/about-me.md` for personalized output

Fill in `about-me.md` with your target roles, salary floor, and key achievements.

## When a recruiter reaches out

`/gaj:respond` — Researches the recruiter, the company (or deduces the unnamed client), checks comp against market data, assesses your interest on 5 criteria, and drafts a calibrated response. Stores all correspondence.

## When you find a job worth tracking

`/gaj:add` — Adds the job and runs detective research before it hits your pipeline. Company intel, recruiter verification, comp reality check.

`/gaj:cover-letter` — Generates a Hook/Proof/Close cover letter matched to the role. Tone controls for formal, conversational, or direct.

## When your inbox is a wall of alerts

`/gaj:triage` — Scores a batch of job listings on role fit, stack match, company quality, comp signal, and strategic value. Surfaces the signal, filters the noise.

## When you get an offer

`/gaj:negotiate` — Ackerman model negotiation with market data lookup. Tracks concession steps, flags walk-away signals, handles W-2 vs 1099.

## Pipeline management

`/gaj:list` `/gaj:status` `/gaj:search` `/gaj:stats` `/gaj:sync`

Track every opportunity from first contact to signed offer. Filter by status, search by company or keyword, export to Google Sheets.

`/gaj` — Dashboard. `/gaj:profile` — Update your search profile. `/gaj:help` — Full command reference.

## Examples

**Add a job (detective research runs automatically):**

```
> /gaj:add Senior Platform Engineer at a staffing firm, $190k, found on LinkedIn

Launching research agents...
  - Recruiter: 4 years at firm, specialized in cloud infra, clean Glassdoor
  - Company: Staffing firm withholds client name
  - Mystery client: Cross-referencing "cloud-native platform" + "Series C" +
    "$190k base" + "Austin preferred" against known companies...
    → 78% match: DataStax. Evidence: tech stack, salary band, location, headcount.
  - Comp check: $190k is 95th percentile for Austin senior platform eng. Legit.
  - Stack fit: 4/5 criteria match your about-me.md profile

Detective Report:
| Signal        | Finding                              | Confidence |
|---------------|--------------------------------------|------------|
| Client ID     | Likely DataStax (Series C, Austin)   | 78%        |
| Comp vs market| At 95th percentile for role/location | High       |
| Recruiter     | Legitimate, 4yr tenure, clean record | High       |
| Red flags     | None detected                        | -          |

Added to pipeline: ID 7, pending-review
```

**Respond to a recruiter:**

```
> /gaj:respond Got a message from a recruiter about a Staff ML role, comp not mentioned

[Runs detective research: recruiter reputation, company intel, comp estimate]
[Presents findings, then assesses interest on 5 criteria]

Interest: curious (3/5 criteria met, missing comp and stack details)

Draft response (curious mode, 127 words):
"The ML infrastructure work sounds interesting, especially the real-time
serving layer. I have a few questions before committing time to a call..."

[Logs inbound + outbound correspondence, linked to pipeline entry]
```

**Triage a LinkedIn digest:**

```
> /gaj:triage [paste 6 jobs from LinkedIn alert]

| # | Company     | Role              | Score | Verdict |
|---|-------------|-------------------|-------|---------|
| 1 | Meridian    | Staff Engineer    | 8.2   | PURSUE  |
| 2 | Cobalt AI   | Senior ML Eng     | 7.1   | PURSUE  |
| 3 | TechForce   | Platform Lead     | 5.4   | MAYBE   |
| 4 | GlobalSync  | Senior Developer  | 4.0   | MAYBE   |
| 5 | Recruitify  | "AI Engineer"     | 2.1   | SKIP    |
| 6 | StaffMax    | Contract Dev      | 1.8   | SKIP    |

Run detective research on your picks? [1, 2, or both]
```

## How it works

All data lives on your machine:

- **Database:** `~/gaj/gaj.db` (SQLite)
- **Config:** `~/gaj/config.yaml`
- **Context:** `~/gaj/context/about-me.md` (your profile for personalized output)

The CLI at `scripts/pipeline-cli.ts` handles database operations. Skills read from and write to the database through this CLI.

**Detective research** launches parallel agents on every job add and recruiter response. The agents investigate recruiter legitimacy, identify unnamed clients by cross-referencing JD clues against known companies, verify compensation against seeded market data, and flag red flags. Findings are stored in the `job_data` field for each pipeline entry and persist across sessions.

**Writing quality** is enforced automatically on every piece of generated text. Cover letters, recruiter responses, and negotiation language all pass through anti-AI rules before you see them. No em dashes, no "delve," no "I hope this helps." There is no separate humanize step because nothing leaves the box sounding like a bot wrote it.

## Google Sheets sync

Optional. Requires your own Google Cloud credentials.

1. Enable the Google Sheets API in [Google Cloud Console](https://console.cloud.google.com)
2. Create a service account and download credentials
3. Save to `~/gaj/credentials.json`
4. Update `~/gaj/config.yaml` with your sheet ID
5. Run `/gaj:sync`

## Job statuses

`pending-review` > `approved` > `cover-letter-ready` > `applied` > `interview` > `offer`

Side tracks: `rejected`, `expired`, `filtered`

## Built by

[StackProof](https://stackproof.app) securely scans and analyzes your GitHub repos, finds jobs worth your time from sources like Cursor, Greenhouse, and Y Combinator, then prepares you for interviews using evidence from your own code. GAJ is the open-source command line. StackProof is the full platform.

## License

MIT
