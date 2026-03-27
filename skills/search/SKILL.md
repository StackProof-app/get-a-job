---
name: gaj:search
description: |
  Search the job pipeline by company name or job title. Triggers on /gaj:search,
  "find [company]", "search for [keyword]", "do I have [company] in my pipeline",
  or any request to look up a specific job.
---

# gaj:search - Search Pipeline

Search jobs by company name or job title keyword.

## When to use

- User wants to find a specific job in their pipeline
- User asks "do I have [company] in my pipeline?"
- User needs to look up a job before updating it

## Process

1. Extract the search query from the user's input. This can be a company name, job title, or keyword.

2. Run the CLI:

```bash
npx tsx scripts/pipeline-cli.ts search '<query>'
```

3. Parse the JSON response. Present matches as a markdown table:

```
| ID | Company | Role | Status | Source | Salary | Added |
|----|---------|------|--------|--------|--------|-------|
| ... | ... | ... | ... | ... | ... | ... |
```

4. State the result: "Found [N] jobs matching '[query]'."

5. If no results: "No jobs found matching '[query]'. Try a broader search term, or use `/gaj:list` to see everything."

## CLI reference

```
npx tsx scripts/pipeline-cli.ts search '<query>'
```

Returns: `{ "query": "...", "count": N, "jobs": [{ "id", "company", "role", "status", "source", "salary", "url", "added" }] }`
