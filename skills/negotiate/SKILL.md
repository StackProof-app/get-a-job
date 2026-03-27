---
name: gaj:negotiate
description: |
  Handle salary and rate negotiation using Ackerman concession model with market data.
  Triggers on /gaj:negotiate, "negotiate salary", "counter-offer", "negotiate rate",
  "they offered $X", "counter their offer", or any request to handle compensation negotiation.
---

# gaj:negotiate - Salary Negotiation

Ackerman-based salary and rate negotiation with market data from the salary_data table, structured concession steps, and walk-away signal detection.

## When to use

- User receives a salary or rate offer and wants to counter
- User says "they offered $X" or "negotiate this offer"
- User wants to know market rates for a role
- User needs a counter-offer strategy before a negotiation call
- User returns with "they came back with $X" (ongoing negotiation)

## Process

### Step 1: Accept offer details

The user will provide one of:
- A specific offer ("they offered $180k base" or "$95/hr contract")
- A verbal range from a recruiter ("they said $150-180k")
- A request to prepare for an upcoming negotiation call

Extract: company, role, offered amount, engagement type (W-2 salaried, W-2 contract-to-hire, 1099).

### Step 2: Identify the pipeline job

Search the pipeline for the company:

```bash
npx tsx scripts/pipeline-cli.ts search '<company name>'
```

If a match exists, use that job ID. If multiple matches, show them and ask the user to pick.

If no match, offer to create a new pipeline entry:

```bash
npx tsx scripts/pipeline-cli.ts add '{"company_name":"<company>","job_title":"<role>","status":"interview","source":"<source>"}'
```

### Step 3: Gather compensation context

**User preferences:**
- Check if `~/gaj/context/about-me.md` exists. If yes, read it for salary floor, target range, and engagement type preferences.
- If it does not exist: ask the user for their target compensation and floor. Mention they can set these up permanently later.

**Prior correspondence:**
- Check for existing conversation context:

```bash
npx tsx scripts/pipeline-cli.ts get-correspondence <job-id>
```

If prior negotiation messages exist, determine which Ackerman step was last used and advance to the next one.

**Clarify engagement type:**
- W-2 salaried: compare directly to annual salary data
- W-2 contract-to-hire: use W-2 rates, ask about conversion terms
- 1099: apply 30-40% premium over W-2 equivalent (covers self-employment tax, insurance, no PTO)

### Step 4: Look up market data

```bash
npx tsx scripts/pipeline-cli.ts salary-lookup '<role>' '<level>' '<location>'
```

If the exact role isn't in the table, try broader matches. Present the closest data available. If no data matches, note the gap and use whatever context the user provides.

### Step 5: Check walk-away signals

Apply the 6 walk-away signals from @prompts/negotiation-system.md:

1. Client unnamed before interview
2. Rate >25% below floor with no flexibility signal
3. Team is just you
4. Scope expands without compensation movement
5. Pressure to decide without basic information
6. Ghost after verbal agreement

Assess as: Clear, Yellow (1 signal), or Red (2+ signals).

If Red: present concerns to the user. Recommend declining or resolving the signals before continuing negotiation. Do not draft a counter-offer until the user decides to proceed.

### Step 6: Calculate Ackerman anchors

From the user's target compensation:
- Step 1 anchor: target * 1.15 (round to a specific, non-round number)
- Step 2 anchor: target * 1.05 (round to a specific, non-round number)
- Step 3 anchor: target (exact, with non-monetary sweetener)

Determine which step applies:
- First counter-offer: use Step 1
- After pushback on first counter: use Step 2
- Final round: use Step 3
- Check prior correspondence to detect which step was used previously

### Step 7: Draft the counter-offer

Read and follow @prompts/negotiation-system.md for generation rules.
Apply @prompts/writing-rules.md to all output.

Draft using the counter-offer message rules:
- Lead with genuine interest in the role
- State range matter-of-factly
- Justify with market context in one sentence
- Close with calibrated question

### Step 8: Present the strategy

Show the user:

1. **Market data table**: p25/p50/p75 for matching roles from salary-lookup
2. **Ackerman ladder**: all 3 steps with calculated dollar amounts
3. **Current position**: which step this draft uses and why
4. **Walk-away assessment**: Clear/Yellow/Red with details
5. **The draft message**
6. **Non-monetary items**: relevant options for Step 3 or to strengthen any step

### Step 9: Offer refinement

After presenting, offer:
- "Adjust tone" (more assertive, more collaborative, more matter-of-fact)
- "Change anchor" (use a different target, recalculate all steps)
- "Add non-monetary" (include specific non-monetary requests in the message)
- "Switch step" (draft using a different Ackerman step)
- "Intel mode" (draft questions to gather info instead of countering)
- "Shorten" (trim the message)

Iterate until the user approves.

### Step 10: Store the approved draft

After user approval, log the negotiation draft:

```bash
npx tsx scripts/pipeline-cli.ts log-message '{"job_id":<id>,"direction":"outbound","message_text":"<approved text>","ai_draft":"<original draft>","tone":"negotiation","classification":"counter-offer-step-<1|2|3>"}'
```

### Step 11: Offer status update

If the job status should change, suggest it:
- If not already at `interview`: suggest updating to `interview`
- If offer received: suggest updating to `offer`

```bash
npx tsx scripts/pipeline-cli.ts status <id> <new-status>
```

## Ongoing negotiation

When the user returns with "they came back with $X" or "they countered":

1. Look up prior correspondence via `get-correspondence`
2. Identify the last Ackerman step used (from classification field: `counter-offer-step-1`, `counter-offer-step-2`, `counter-offer-step-3`)
3. Advance to the next step
4. If already at Step 3 and they're still pushing: present walk-away analysis. The Ackerman model is exhausted. The user decides whether to hold, walk, or accept.

## Market data only mode

If the user says "what's the market rate for [role]" without a specific negotiation:

1. Run salary-lookup
2. Present the data as a clean table
3. Offer context on engagement type differences
4. No Ackerman steps, no counter-offer draft

## CLI reference

```
npx tsx scripts/pipeline-cli.ts search '<company>'
npx tsx scripts/pipeline-cli.ts add '<json>'
npx tsx scripts/pipeline-cli.ts salary-lookup '<role>' '<level>' '<location>'
npx tsx scripts/pipeline-cli.ts get-correspondence <job-id>
npx tsx scripts/pipeline-cli.ts log-message '<json>'
npx tsx scripts/pipeline-cli.ts status <id> <new-status>
```
