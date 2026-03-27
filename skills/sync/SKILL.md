---
name: gaj:sync
description: |
  Export pipeline data to Google Sheets. Triggers on /gaj:sync,
  "sync to sheets", "export pipeline", "update my spreadsheet",
  "push to Google Sheets", or any request to export job data.
---

# gaj:sync - Export Pipeline to Google Sheets

Export all pipeline jobs to a Google Sheet for sharing, visualization, or backup.

## When to use

- User wants to export pipeline data to Google Sheets
- User says "sync to sheets" or "export pipeline"
- User wants a shareable view of their job search

## Prerequisites

This sub-command requires setup before first use:
- A Google Cloud project with Sheets API enabled
- OAuth credentials (service account or OAuth2 client)
- A Google Sheet to export to

## Process

### Step 1: Check configuration

Read `~/gaj/config.yaml` and verify:
- `sheets_id` is set (the Google Sheet ID from the URL)
- `credentials_path` is set (path to OAuth credentials JSON, defaults to `~/gaj/credentials.json`)

If either is missing, walk the user through setup:

1. "Create a Google Cloud project at https://console.cloud.google.com"
2. "Enable the Google Sheets API"
3. "Create a service account and download the JSON credentials"
4. "Save the credentials to ~/gaj/credentials.json"
5. "Create a Google Sheet and share it with the service account email"
6. "Copy the Sheet ID from the URL (the long string between /d/ and /edit)"
7. "Add to ~/gaj/config.yaml:"
   ```yaml
   sheets_id: "your-sheet-id-here"
   credentials_path: "~/gaj/credentials.json"
   ```

After setup is complete, re-run `/gaj:sync`.

### Step 2: Run the sync

```bash
npx tsx scripts/sync-sheets.ts
```

This will:
- Read all jobs from the pipeline database
- Clear the existing sheet data
- Write a header row: ID, Company, Role, Status, Source, Salary, URL, Date Added
- Write all jobs below the header

### Step 3: Report results

Parse the JSON output and report:
- Number of rows synced
- Link to the sheet: `https://docs.google.com/spreadsheets/d/<sheets_id>`

If the sync fails, show the error message and suggest fixes:
- Auth errors: check credentials file and service account permissions
- Sheet not found: verify sheets_id in config.yaml
- API errors: check that Google Sheets API is enabled in the Cloud project

## CLI reference

```
npx tsx scripts/sync-sheets.ts
```

Output format:
```json
{
  "synced": 15,
  "sheet_id": "abc123...",
  "columns": ["ID", "Company", "Role", "Status", "Source", "Salary", "URL", "Date Added"]
}
```
