---
name: gaj:list
description: |
  List and filter job pipeline entries. Triggers on /gaj:list, "show my jobs",
  "what's in my pipeline", "list pipeline", "show pending/applied/approved jobs",
  or any request to view pipeline contents.
---

# gaj:list - List Pipeline Entries

Show all jobs in the pipeline, optionally filtered by status.

## When to use

- User wants to see their full pipeline
- User asks for jobs with a specific status ("show pending jobs")
- User says "what's in my pipeline" or "show my jobs"

## Process

1. Determine if the user wants a status filter. If they mention a specific status, pass it as an argument.

2. Run the CLI:

```bash
npx tsx scripts/pipeline-cli.ts list [status]
```

Valid status filters: `pending-review`, `approved`, `cover-letter-ready`, `applied`, `interview`, `offer`, `rejected`, `expired`, `filtered`

3. Parse the JSON response. Present as a markdown table:

```
| ID | Company | Role | Status | Source | Salary | Added |
|----|---------|------|--------|--------|--------|-------|
| ... | ... | ... | ... | ... | ... | ... |
```

4. If no jobs found:
   - Without filter: "No jobs in the pipeline yet. Use `/gaj:add` to add one."
   - With filter: "No jobs with status '[status]'. Try `/gaj:list` to see all jobs."

5. After listing, state the count: "[N] jobs in the pipeline" or "[N] jobs with status [status]."

## CLI reference

```
npx tsx scripts/pipeline-cli.ts list [status]
```

Returns: `{ "count": N, "jobs": [{ "id", "company", "role", "status", "source", "salary", "url", "added" }] }`
