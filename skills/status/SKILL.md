---
name: gaj:status
description: |
  Update the status of a job in the pipeline. Triggers on /gaj:status, "update status",
  "mark as applied", "move to interview", "reject", or any request to change a job's
  pipeline stage.
---

# gaj:status - Update Job Status

Change the status of a job in the pipeline.

## When to use

- User wants to move a job to a new stage
- User says "mark [company] as [status]"
- User says "update [company] to applied/rejected/interview"

## Process

1. Identify the job. The user may provide:
   - A numeric ID (e.g., "update job 3 to applied")
   - A company name (e.g., "mark Acme as rejected")

2. If the user gives a company name, first find the job:

```bash
npx tsx scripts/pipeline-cli.ts search '<company>'
```

If multiple matches, show them and ask the user to specify by ID.

3. Determine the new status. Valid statuses:

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

4. Run the CLI:

```bash
npx tsx scripts/pipeline-cli.ts status <id> <new-status>
```

5. Confirm the change: "Updated [Company] ([Role]) to [status]."

6. If the new status suggests a next action, mention it:
   - `approved` → "Ready for a cover letter. Use `/gaj:cover-letter` when available."
   - `applied` → "Good luck. Update to `interview` when you hear back."
   - `offer` → "Use `/gaj:negotiate` when available to prepare."

## CLI reference

```
npx tsx scripts/pipeline-cli.ts status <id> <new-status>
npx tsx scripts/pipeline-cli.ts search '<company>'
```

Status returns: `{ "updated": <id>, "field": "status", "value": "<status>" }`
Search returns: `{ "query": "...", "count": N, "jobs": [...] }`
