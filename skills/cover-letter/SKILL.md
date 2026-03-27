---
name: gaj:cover-letter
description: |
  Generate a cover letter for a job in the pipeline. Triggers on /gaj:cover-letter,
  "write a cover letter", "draft a letter for [company]", "cover letter for [role]",
  or any request to create a cover letter for a job opportunity.
---

# gaj:cover-letter - Generate Cover Letter

Generate a Hook/Proof/Close cover letter tailored to a specific job and company.

## When to use

- User wants a cover letter for a job in their pipeline
- User says "write a cover letter for [company]"
- User has a job listing and wants a tailored letter

## Process

### Step 1: Identify the job

Accept one of:
- A numeric pipeline ID (e.g., "cover letter for job 3")
- A company name (e.g., "cover letter for Acme")
- Fresh job details provided directly by the user

If an ID or company name is given, look up the job:

```bash
npx tsx scripts/pipeline-cli.ts search '<company or id>'
```

If multiple matches, show them and ask the user to pick one. Extract: company name, job title, URL, salary info.

### Step 2: Gather context

**Resume and preferences:**
- Check if `~/gaj/context/resume.md` exists. If yes, read it.
- Check if `~/gaj/context/about-me.md` exists. If yes, read it.
- If neither exists: ask the user for 2-3 relevant achievements and their current role/title. Mention they can set these up permanently later.

**Company research:**
- If a job URL is available, review the posting for: exact skills language, team description, project mentions, company tone.
- Note specific company facts (not generic). A recent launch, a funding round, a specific product feature.

### Step 3: Generate the cover letter

Read and follow @prompts/cover-letter-system.md for the generation format.
Apply @prompts/writing-rules.md to all output.

Use the Hook/Proof/Close structure:
- **Hook:** Company-specific opener connecting their work to the applicant's experience
- **Proof:** 2 achievements from the resume, mirroring the job posting's language, with specific numbers
- **Close:** Concrete fit statement and call to action

### Step 4: Present the draft

Show the cover letter with:
- The word count (must be 250-400)
- The tone used (confident/conversational/technical/formal)

### Step 5: Offer refinement

After presenting, offer:
- "Adjust tone" (more casual, more formal, more technical)
- "Swap achievements" (use different resume highlights)
- "Shorten" (cut to ~250 words)
- "Lengthen" (expand to ~400 words)
- "Strengthen hook" (rewrite paragraph 1)

Iterate until the user approves.

### Step 6: Store the result

After user approval, save the cover letter to the pipeline:

```bash
npx tsx scripts/pipeline-cli.ts update <id> cover_letter '<approved cover letter text>'
```

Then offer to update the job status:

```bash
npx tsx scripts/pipeline-cli.ts status <id> cover-letter-ready
```

## CLI reference

```
npx tsx scripts/pipeline-cli.ts search '<company>'
npx tsx scripts/pipeline-cli.ts update <id> cover_letter '<text>'
npx tsx scripts/pipeline-cli.ts status <id> cover-letter-ready
```

## Tone control

Users can request a tone when invoking the skill:
- "/gaj:cover-letter for Acme, technical tone"
- "/gaj:cover-letter for job 5, keep it conversational"

Default: match the company's posting tone.
