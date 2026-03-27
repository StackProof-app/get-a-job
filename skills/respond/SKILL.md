---
name: gaj:respond
description: |
  Assess recruiter outreach and draft a calibrated response. Triggers on /gaj:respond,
  "reply to recruiter", "respond to [name]", "draft a response to [message]",
  "assess this opportunity", or any request to evaluate and reply to recruiter outreach.
---

# gaj:respond - Recruiter Response

Assess interest level in a recruiter's outreach, draft a mode-appropriate response, and store all correspondence.

## When to use

- User receives a recruiter message and wants to evaluate it
- User wants to draft a reply to a recruiter (LinkedIn, email, referral)
- User says "reply to this recruiter" or "what should I say to [name]"
- User wants to decline an opportunity gracefully
- User wants to follow up after a recruiter went silent

## Process

### Step 1: Accept the recruiter's message

The user will provide one of:
- Pasted message text (LinkedIn, email, etc.)
- Screenshot description or forwarded email content
- Summary of what the recruiter said

Extract from the message: recruiter name, company, role, platform (LinkedIn/email), and any compensation details mentioned.

### Step 2: Identify or create the pipeline job

Search the pipeline for the company:

```bash
npx tsx scripts/pipeline-cli.ts search '<company name>'
```

If a match exists, use that job ID. If multiple matches, show them and ask the user to pick.

If no match, offer to create a new pipeline entry:

```bash
npx tsx scripts/pipeline-cli.ts add '{"company_name":"<company>","job_title":"<role>","status":"pending-review","source":"recruiter"}'
```

### Step 3: Log the inbound message

Store the recruiter's message in the correspondence table:

```bash
npx tsx scripts/pipeline-cli.ts log-message '{"job_id":<id>,"direction":"inbound","platform":"<linkedin|email>","sender_name":"<recruiter name>","message_text":"<their message>"}'
```

### Step 4: Detective research (mandatory)

Before assessing interest or drafting any response, run deep investigative research
using parallel subagents. This research directly determines pass-or-pursue decisions.

**Launch these research threads in parallel:**

1. **The recruiter**: Firm name, recruiter tenure, LinkedIn profile, Glassdoor reviews,
   specialization, geographic footprint. Is this person legitimate and senior, or a
   cold-calling junior recruiter?

2. **The company/client**: If named, research AI/tech investment, engineering culture,
   tech stack, news, leadership, funding. If unnamed (staffing firm), cross-reference
   JD clues (industry, stack, location, salary band, company descriptors) to identify
   the likely client. Rank candidates with evidence.

3. **Compensation and market fit**: Compare stated comp to market rates and user's floor
   from about-me.md. Check stack alignment.

Present findings as a structured **detective report** with evidence tables.
Store research in `job_data` via update if the pipeline entry already exists.

**CRITICAL: The detective report is a secret weapon for the user only.** Never reveal
research findings in any outbound communication. Outbound messages must reference ONLY
information the recruiter explicitly provided. Do not quote back salary numbers (forces
re-anchoring), hint at knowing the unnamed client, or reference Glassdoor/market data.
Ask open questions that make the recruiter reveal information rather than showing you
already know it. The edge only works if it stays hidden.

### Step 4b: Gather context

**User preferences:**
- Check if `~/gaj/context/about-me.md` exists. If yes, read it for role targets, salary floor, tech stack, and evaluation criteria.
- If it does not exist: ask the user for their role targets, salary floor, and key tech preferences. Mention they can set these up permanently later.

**Conversation history:**
- Check for prior correspondence on this job:

```bash
npx tsx scripts/pipeline-cli.ts get-correspondence <job-id>
```

If prior messages exist, factor them into the response (don't repeat questions already answered, acknowledge previous exchanges).

### Step 5: Assess interest (informed by detective research)

Apply the 5 criteria from @prompts/recruiter-response-system.md:

1. Role fit
2. Tech stack match
3. Company stage
4. Compensation
5. Mission alignment

Classify as: `strong-interest`, `curious`, `warm-decline`, or `hard-pass`.

For `hard-pass`: explain the assessment to the user, do not draft a response, and offer to mark the job as `filtered`.

### Step 6: Draft the response

Read @prompts/recruiter-response-system.md for generation rules.
Read @prompts/response-templates.md for the structural scaffold matching the classification.
Apply @prompts/writing-rules.md to all output.

Draft a response using the appropriate mode:
- `strong-interest` -> Mode 1 (Strong Interest)
- `curious` -> Mode 2 (Curious but Cautious)
- `warm-decline` -> Mode 3 (Warm Decline)

### Step 7: Present the draft

Show the user:
1. **Interest assessment**: which classification and why (list criteria met/unmet)
2. **Word count** (must be within mode constraints)
3. **The draft message**
4. Any qualifying questions recommended for a call (for strong-interest/curious)

### Step 8: Offer refinement

After presenting, offer:
- "Adjust tone" (more casual, more formal, more direct)
- "Add questions" (include specific qualifying questions)
- "Remove questions" (trim to just the response)
- "Switch mode" (reassess at a different interest level)
- "Shorten" (cut further)

Iterate until the user approves.

### Step 9: Store the approved response

After user approval, log the outbound draft:

```bash
npx tsx scripts/pipeline-cli.ts log-message '{"job_id":<id>,"direction":"outbound","message_text":"<approved text>","ai_draft":"<original draft>","tone":"<tone used>","classification":"<classification>"}'
```

### Step 10: Offer status update

If the interest assessment suggests a status change, offer it:
- `strong-interest` -> suggest `approved` status
- `curious` -> keep at `pending-review`
- `warm-decline` -> suggest `rejected` status

```bash
npx tsx scripts/pipeline-cli.ts status <id> <new-status>
```

## CLI reference

```
npx tsx scripts/pipeline-cli.ts search '<company>'
npx tsx scripts/pipeline-cli.ts add '<json>'
npx tsx scripts/pipeline-cli.ts log-message '<json>'
npx tsx scripts/pipeline-cli.ts get-correspondence <job-id>
npx tsx scripts/pipeline-cli.ts status <id> <new-status>
```

## Follow-up mode

If the user says "follow up with [recruiter]" or "they haven't responded":
1. Look up prior correspondence via `get-correspondence`
2. Check how long since the last outbound message
3. If 5+ business days: use Mode 4 (Follow-up After Silence) from the response templates
4. If fewer than 5 days: suggest waiting
