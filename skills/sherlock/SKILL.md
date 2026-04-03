---
name: gaj:sherlock
description: |
  Deep detective investigation on any company, recruiter, or job listing.
  Triggers on /gaj:sherlock, "investigate [company]", "research [company]",
  "sherlock [anything]", "vet this company", "is [company] legit",
  or any request for deep company/recruiter/listing research.
---

# gaj:sherlock - Detective Investigation

Run deep investigative research on a company, recruiter, job listing, or any
combination. Produces an opinionated intelligence report with evidence-backed
red flags, compensation analysis, and a pass/pursue/dig-deeper verdict.

## When to use

- User wants to research a company before applying
- User wants to vet a staffing firm or recruiter
- User wants to investigate a job listing (URL or pasted JD)
- User says "is [company] legit" or "what do you know about [company]"
- User pastes a LinkedIn URL and wants the full picture
- Called internally by /gaj:respond Step 4

## Process

### Step 1: Accept and parse input

The user provides any combination of:
- A URL (LinkedIn job, LinkedIn profile, company website)
- Pasted job description text
- A company name
- A recruiter name
- Any mix of the above

**Parse rules:**

| Input pattern | Type | Action |
|--------------|------|--------|
| Contains `linkedin.com/jobs/view/` or `/comm/jobs/view/` | LinkedIn job URL | WebFetch the listing, extract title, company, location, pay, JD, poster |
| Contains `linkedin.com/in/` | LinkedIn profile URL | WebFetch the profile, extract name, company, headline |
| Any other URL | Company website | WebFetch the page, extract company info |
| Multi-line text with role/requirements language | Pasted JD | Parse title, company, stack, comp, location from text |
| Short text, no URL | Name | Ask: "Is this a company name, a person, or something else?" |

When inputs overlap (URL + pasted JD), merge. URL-sourced facts take precedence.
Pasted text fills gaps.

### Step 2: Check pipeline (optional)

Search the pipeline for the company:

```bash
npx tsx scripts/pipeline-cli.ts search '<company name>'
```

If a match exists:
- Note the job ID for later storage
- Check for prior sherlock findings:

```bash
npx tsx scripts/pipeline-cli.ts get-job <id>
```

If `job_data.sherlock.investigated_at` exists and is < 24 hours old, ask:
"I have recent findings for [company]. Re-investigate or show existing?"

If the user wants existing findings, present the stored report and stop.

### Step 3: Run investigation (parallel subagents)

Read @prompts/sherlock-system.md for the full investigation framework.

Launch up to 5 parallel subagents, one per investigation dimension. Each
subagent gets:
- The parsed input data relevant to its dimension
- The investigation instructions from sherlock-system.md for its dimension
- Access to WebSearch and WebFetch tools

**Subagent dispatch:**

1. **Recruiter analysis** - only if recruiter name or firm name available
2. **Company analysis** - always (company name extractable from most inputs)
3. **Mystery client resolution** - only if posting is from a staffing firm
4. **Compensation reality check** - only if comp data is stated or extractable
5. **Red flag detection** - always, runs after dimensions 1-4 return

Read ~/gaj/context/about-me.md for the user's salary floor, tech stack, and
role targets. Pass these to the comp and stack fit investigators.

### Step 4: Assemble the report

Collect findings from all subagents. Follow the narrative output template
from @prompts/sherlock-system.md exactly. Omit sections with no data.

Apply @prompts/writing-rules.md to all narrative output.

End the report with a Sources section listing all URLs used as markdown links.

### Step 5: Store findings (silent, if pipeline-linked)

If a pipeline entry was found in Step 2, store the structured findings:

```bash
npx tsx scripts/pipeline-cli.ts update <id> 'job_data' '<JSON string of sherlock findings>'
```

Use the JSON schema from @prompts/sherlock-system.md.

If no pipeline entry exists, offer at the end of the report:
"Want me to add this to your pipeline?"

If the user accepts, create the entry:

```bash
npx tsx scripts/pipeline-cli.ts add '{"company_name":"<company>","job_title":"<role>","status":"pending-review","source":"sherlock","job_data":<findings JSON>}'
```

## Internal invocation (from respond)

When called by /gaj:respond, sherlock runs the same process but:
- Does not display the banner or check pipeline (respond already did that)
- Returns findings to the calling skill rather than presenting to user
- Respond presents a condensed version of the report as part of its own flow
- Storage happens through respond's pipeline entry

## CLI reference

```
npx tsx scripts/pipeline-cli.ts search '<company>'
npx tsx scripts/pipeline-cli.ts get-job <id>
npx tsx scripts/pipeline-cli.ts update <id> 'job_data' '<json>'
npx tsx scripts/pipeline-cli.ts add '<json>'
```
