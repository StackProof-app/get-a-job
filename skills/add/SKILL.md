---
name: gaj:add
description: |
  Add a job opportunity to the pipeline. Triggers on /gaj:add, "add a job",
  "new opportunity", "track this role", or when the user provides job details
  to be saved to the pipeline.
---

# gaj:add - Add a Job to the Pipeline

Extract job details from the user's input and insert into the pipeline database.

## When to use

- User provides a job opportunity to track (company name, role, URL, salary, source)
- User pastes a job listing and wants it saved
- User says "add" or "track" with job details

## Process

### Step 0: Detective research (mandatory)

Before adding anything to the database, run deep investigative research using parallel
subagents. This is the core differentiator of the tool and is non-negotiable.

**Launch these research threads in parallel:**

1. **The recruiter** (if from a staffing firm): Firm reputation, recruiter tenure and
   LinkedIn profile, Glassdoor reviews, specialization, geographic footprint, legitimacy
   signals. Flag any red flags (MLM, fake listings, bait-and-switch patterns).

2. **The company** (if named): AI/tech investment signals, engineering culture, tech stack,
   recent news, leadership, funding stage, Glassdoor, headcount trends. Check if they
   actually build what the JD describes or if it is aspirational.

3. **The mystery client** (if staffing firm withholds the name): Cross-reference clues
   from the JD (industry vertical, tech stack, location hints, salary band, company
   size descriptors) against known companies in that space. Rank candidates with evidence.

4. **Compensation reality check**: Compare stated comp to market rates for the
   role/location/company tier. Flag if below user's floor from about-me.md.

5. **Stack and role fit**: Compare JD requirements against user's tech stack preferences
   from about-me.md. Note alignment and mismatches.

Present findings as a structured **detective report** with evidence tables before
proceeding to database insertion. Store all research findings in the `job_data` field.

**CRITICAL: The detective report is a secret weapon for the user only.** Never reveal
research findings in any outbound communication. Do not reference identified clients,
salary data, Glassdoor scores, or market intelligence in recruiter responses. The edge
only works if it stays hidden.

### Step 1: Extract fields

Extract these fields from the user's input:

| Field | Required | Notes |
|-------|----------|-------|
| `company_name` | Yes | Company name as stated (include staffing firm: "Company (via Firm)") |
| `job_title` | Yes | Role/position title |
| `source` | No | Where the job came from (default: `manual`) |
| `url` | No | Job posting URL if available |
| `salary_raw` | No | Salary as stated (e.g., "$180k-$220k") |
| `job_data` | No | JSON object with research findings, recruiter info, requirements, notes |

2. If company_name or job_title is missing, ask the user for it. Do not guess.

3. Run the CLI:

```bash
npx tsx scripts/pipeline-cli.ts add '{"company_name":"...","job_title":"...","source":"...","url":"...","salary_raw":"...","job_data":{...}}'
```

4. Parse the JSON response and present:

```
Added to pipeline:

| ID | Company | Role | Status |
|----|---------|------|--------|
| <id> | <company> | <role> | pending-review |
```

5. After adding, offer: "Update status, add notes, or add another?"

## Sources

Common values for the `source` field:

- `recruiter-linkedin` - LinkedIn recruiter outreach
- `linkedin-alert` - LinkedIn job alert
- `job-board` - Indeed, Glassdoor, etc.
- `referral` - Personal referral
- `stackproof` - Saved from StackProof
- `manual` - Manually added (default)

## CLI reference

```
npx tsx scripts/pipeline-cli.ts add '<json>'
```

Returns: `{ "inserted": <id>, "company": "...", "role": "...", "status": "..." }`
