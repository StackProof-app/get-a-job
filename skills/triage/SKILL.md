---
name: gaj:triage
description: |
  Batch-triage job alert digests from LinkedIn or email. Triggers on /gaj:triage,
  "triage my inbox", "filter these jobs", "here's a digest", "LinkedIn alerts",
  "batch these jobs", or when the user pastes multiple job listings at once.
---

# gaj:triage - Batch Job Triage

Score, filter, and surface the signal from high-volume job alert digests. This is for
inbox buildup and tidal waves. For a single specific job, use `gaj:add` instead.

## When to use

- User pastes a LinkedIn job alert digest (3-4+ jobs in one email)
- User has multiple job listings to evaluate at once
- User says "triage", "filter these", "batch", or "inbox buildup"
- User forwards or pastes any multi-job email

## Process

### Step 1: Extract all jobs from the digest

Parse the user's input and extract every job listing. For each job, capture whatever
is visible in the digest:

| Field | Source |
|-------|--------|
| Job title | Digest text |
| Company name | Digest text |
| Location / remote | Digest text |
| Salary (if shown) | Digest text |
| URL | LinkedIn link if present |
| Source | `linkedin-alert`, `job-board`, etc. |

Present the raw extraction as a numbered list so the user can verify nothing was missed.

### Step 2: Quick score each job (30 seconds per job, no deep research)

Apply the scoring rubric to each job using ONLY information visible in the digest
plus basic knowledge (is the company public? is it a known startup?). Do NOT run
full detective research at this stage.

**Scoring rubric (0-10 weighted)**

| Criteria | Weight | What it measures |
|----------|--------|-----------------|
| Role fit | 2x | Senior/staff level, AI/ML/LLM in scope, engineering not support |
| Stack match | 1x | TypeScript, Python, React, distributed systems, AI frameworks |
| Company quality | 1.5x | Known stage, funding, reputation (surface-level only) |
| Comp signal | 1x | Above $180k floor, or unstated (benefit of doubt = 5/10) |
| Strategic value | 1.5x | Resume impact, springboard potential, market positioning |

**Scoring guidelines:**
- Unstated salary gets a neutral 5/10 (benefit of doubt, will clarify later)
- European remote roles get a strategic value bonus if the role involves real AI work
  (thinner talent pool = easier placement = springboard potential)
- "Junior" or "Mid" in title = automatic 0/10 on role fit
- On-site only with no relocation interest = 2/10 on role fit
- Known Series B+ or F500 with AI initiative = 8/10 on company quality
- Unknown company = 5/10 on company quality (neutral, not penalized)

**Calculate weighted score:**
```
score = (role_fit * 2 + stack_match * 1 + company_quality * 1.5 + comp * 1 + strategic * 1.5) / 7
```

### Step 3: Present the triage table

Sort by score descending. Color-code the recommendation:

```
TRIAGE RESULTS
==============

| # | Score | Company | Role | Signal | Action |
|---|-------|---------|------|--------|--------|
| 1 | 8.2 | Acme AI | Staff AI Engineer | Series B, remote, $200k | PURSUE |
| 2 | 7.1 | DataCorp | Senior ML Eng | F500, remote, no salary | PURSUE |
| 3 | 5.4 | MedWidget | AI Developer | Seed, hybrid, $140k | MAYBE |
| 4 | 3.1 | BuzzCo | Mid Engineer | Unknown, on-site | SKIP |
| 5 | 1.8 | StaffHaus | Jr Developer | Staffing, contract | SKIP |

PURSUE (7+): Full detective research + pipeline ingestion
MAYBE (4-6): One-liner in table. Promote to PURSUE if you want.
SKIP (0-3): Auto-filtered. Reason noted.
```

### Step 4: User picks

Ask the user: "Which ones do you want the full detective report on? I recommend
the PURSUE entries. You can also promote any MAYBE."

The user can:
- Approve all PURSUE entries: "run them all"
- Cherry-pick: "do 1 and 3"
- Override: "skip 2, promote 4"
- Add context: "I know someone at DataCorp, bump that one"

### Step 5: Detective research on picks (parallel)

For each picked job, run the full detective research from `gaj:add` Step 0:
- Company research (funding, tech stack, AI investment, Glassdoor)
- Compensation reality check
- Stack and role fit analysis

Launch research agents in parallel for all picked jobs simultaneously.

**CRITICAL: Detective research is a secret weapon for the user only.** Never reveal
research findings in any outbound communication. The edge only works if it stays hidden.

### Step 6: Present detective reports + ingest

For each researched job, present:
1. Detective report with evidence table
2. Interest assessment (strong interest / curious / warm decline)
3. Draft response if the user wants one (via `gaj:respond` flow)

Ingest all researched jobs into the pipeline via `gaj:add` CLI command.
Store research findings in the `job_data` field.

### Step 7: Handle the SKIPs

For jobs scored SKIP (0-3), offer two options:
- "Auto-filter all SKIPs" → adds them as `filtered` status with the reason
- "Just ignore them" → does not add to pipeline at all

Do not ingest SKIP jobs unless the user explicitly asks to track them.

## Digest formats supported

- **LinkedIn job alert digest**: Usually has 3-5 jobs with title, company, location,
  and a "See job" link. May include salary range.
- **LinkedIn recruiter digest**: Multiple recruiter messages, each with different roles.
  Extract each as a separate job.
- **Email forwards**: User may forward job alert emails. Parse the email body.
- **Pasted list**: User may just paste a list of companies and roles.
- **URLs only**: User pastes LinkedIn job URLs. Navigate to each (if browser available)
  or ask user to paste the JD text.

## Handling LinkedIn job URLs

If the user provides LinkedIn job URLs, try to extract job details from the URL
parameters (job ID, company name). If insufficient, ask the user to paste the
job description text from each link.

Do NOT attempt to scrape LinkedIn URLs via browser automation (login walls, bot detection).

## CLI reference

Uses the same CLI as `gaj:add`:

```bash
npx tsx scripts/pipeline-cli.ts add '<json>'
npx tsx scripts/pipeline-cli.ts search '<query>'
```

## Volume guidelines

- Up to 5 jobs: triage all in one pass
- 6-10 jobs: triage in two passes (first 5, then remaining)
- 10+ jobs: warn the user that detective research on all PURSUE picks will take time,
  suggest processing in batches of 5

## Example flow

User pastes a LinkedIn digest with 4 jobs. Triage scores them: 8.1, 6.3, 4.2, 2.0.

```
TRIAGE RESULTS

| # | Score | Company | Role | Signal | Action |
|---|-------|---------|------|--------|--------|
| 1 | 8.1 | Nexus AI | Staff Engineer, AI Platform | Series C, remote, $220k | PURSUE |
| 2 | 6.3 | HealthGrid | Senior ML Engineer | Series A, hybrid, no salary | MAYBE |
| 3 | 4.2 | LogiParts | AI Developer | Unknown, remote, $130k | MAYBE |
| 4 | 2.0 | TalentBridge | Mid Software Dev | Staffing, on-site, $95k | SKIP |

PURSUE: #1 gets full detective research.
MAYBE: #2 and #3 available if you want them.
SKIP: #4 auto-filtered (mid-level, on-site, below floor).

Which ones do you want the full report on?
```

User says "1 and 2." Detective research runs in parallel on Nexus AI and HealthGrid.
Reports presented. Jobs ingested. Responses drafted if requested.
