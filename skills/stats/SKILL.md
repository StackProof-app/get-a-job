---
name: gaj:stats
description: |
  Show pipeline statistics and overview. Triggers on /gaj:stats, "how many jobs",
  "pipeline stats", "pipeline overview", "show me a summary", or any request for
  aggregate pipeline data.
---

# gaj:stats - Pipeline Statistics

Show totals and breakdowns of the job pipeline.

## When to use

- User asks "how many jobs do I have?"
- User wants a pipeline overview or summary
- User invokes `/gaj` without a specific task (root skill routes here)

## Process

1. Run the CLI:

```bash
npx tsx scripts/pipeline-cli.ts stats
```

2. Parse the JSON response and present as a formatted summary:

```
Pipeline: [total] jobs

By status:
  [status]: [count]
  [status]: [count]
  ...

By source:
  [source]: [count]
  [source]: [count]
  ...
```

3. If the pipeline is empty: "Pipeline is empty. Use `/gaj:add` to start tracking jobs."

4. If the pipeline has jobs, offer: "Use `/gaj:list` to see details, or `/gaj:add` to add more."

## CLI reference

```
npx tsx scripts/pipeline-cli.ts stats
```

Returns: `{ "total": N, "by_status": { "status": count, ... }, "by_source": { "source": count, ... } }`
