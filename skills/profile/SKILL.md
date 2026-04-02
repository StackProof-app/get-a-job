---
name: gaj:profile
description: |
  View or update your job search profile. Triggers on /gaj:profile,
  "update my profile", "change my targets", "edit about-me",
  "update my salary floor", or any request to modify search preferences.
---

# gaj:profile - Search Profile

View or update the user's search profile stored in `~/gaj/context/about-me.md`.

## When to use

- User wants to see their current profile
- User wants to update salary floor, target roles, location, or other preferences
- User says "update my profile" or "change my targets"
- Goals or circumstances have changed since initial setup

## Process

### Step 1: Read the current profile

```bash
cat ~/gaj/context/about-me.md
```

If the file does not exist, route to the first-run setup in the root SKILL.md.

### Step 2: Display as a clean summary

Present the profile as a formatted summary, not raw markdown. Example:

```
Your search profile:

  Targeting:       Senior Software Engineer, Staff ML Engineer
  Employment:      W-2 salaried, 1099 independent
  Comp floors:     W-2: $180,000/yr | 1099: $130/hr
  Tech stack:      TypeScript, React, Python, PostgreSQL
  Location:        Remote only
  Company stage:   Series B+, 50-500 employees
  Priorities:      Tech stack, growth path, team quality
  Resume:          ~/gaj/context/resume-ai.md
  Contact:         hello@example.com
```

### Step 3: Ask what to change

If invoked with context (e.g., "/gaj:profile update my salary floor"):
- Jump directly to that field
- Accept the new value
- Update the file

If invoked without context:
- Ask: "What would you like to change?"
- Accept natural language: "raise my W-2 floor to $200k", "add contract-to-hire at $95/hr", "switch to remote + hybrid"

### Step 4: Update the file

Read `~/gaj/context/about-me.md`, modify the relevant section, write the file back.

Show what changed: "Updated compensation floors: W-2 salaried $180,000/yr -> $200,000/yr"

## Voice rules

Apply the same voice rules as the root SKILL.md. Direct, no filler.
