---
name: gaj:help
description: Show all GAJ commands, what they do, and suggested workflow order
---

<objective>
Display the GAJ command reference and getting-started guide.

Output ONLY the reference content below. Do NOT add project-specific analysis, git status, or commentary beyond the reference.
</objective>

<process>

Display this exactly:

```
GAJ — Job Search Pipeline
══════════════════════════

Run your entire job search from here. Every recruiter and company
gets investigated before you respond to anything.

Get started:
  /gaj                  Pipeline dashboard (or first-run setup)
  /gaj:profile          View or update your search profile
  Fill in ~/gaj/context/about-me.md with your targets, salary floor, and achievements

Pipeline commands:
  /gaj:add              Add a job to the pipeline
  /gaj:list             List/filter pipeline items
  /gaj:status           Update a job's status
  /gaj:search           Search by company, title, or keyword
  /gaj:stats            Pipeline statistics

Generation commands:
  /gaj:cover-letter     Generate a Hook/Proof/Close cover letter
  /gaj:respond          Assess interest and draft a recruiter response
  /gaj:sherlock         Deep investigation on a company, recruiter, or listing
  /gaj:negotiate        Ackerman-based salary negotiation guidance

Workflow commands:
  /gaj:triage           Batch-filter a job alert digest
  /gaj:sync             Export pipeline to Google Sheets

Suggested order for a new opportunity:
  1. /gaj:add            Add the job
  2. /gaj:respond        If a recruiter reached out, draft your reply
  3. /gaj:cover-letter   Generate a cover letter
  4. /gaj:status         Update status as you progress
  5. /gaj:negotiate      When you reach the offer stage

All data lives in ~/gaj/gaj.db. Run /gaj:help any time.
```

</process>
