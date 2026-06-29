# Phase 14: Speaker Popover Card - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-25
**Phase:** 14-speaker-popover-card
**Areas discussed:** API data strategy, Trigger scope, Tenure logic, Popover card layout

---

## API Data Strategy

### Q1: How should the server load function get full speaker data?

| Option | Description | Selected |
|--------|-------------|----------|
| New GET /arguments/{id}/speakers endpoint | One call returns all speakers pre-assembled. Single round-trip. | ✓ |
| Loop over person_ids in the load function | Parallel fetches via Promise.all on existing /people/{id} endpoint. 9–20 calls. | |
| Expand the utterances response | Embed full speaker detail inline on each utterance. Heavier payload. | |

**User's choice:** New dedicated endpoint  
**Notes:** Recommended option accepted without modification.

---

### Q2: What fields does each speaker entry return?

| Option | Description | Selected |
|--------|-------------|----------|
| person_id + full_name + role_name + photo_url + tenure[] + appointing_president | Everything the popover needs. | ✓ |
| Same fields + include side (BENCH/ADVOCATE) | Redundant — side is already on utterances. | |
| You decide | Claude picks the field set. | |

**User's choice:** Recommended field set  
**Notes:** Accepted; `side` excluded as redundant since it's already available on utterances.

---

## Trigger Scope

### Q1: Where do the clickable avatars live?

| Option | Description | Selected |
|--------|-------------|----------|
| ChatBubble avatars only | 32px circles in utterance bubbles become clickable. Roster unchanged. | |
| ChatBubble avatars + add avatars to header roster | Both locations get clickable avatars. Roster entries get avatar circles added. | ✓ |
| Header roster avatars only | Roster-only. Not recommended; violates PUB-01. | |

**User's choice:** Both ChatBubble avatars and header roster  
**Notes:** Adds avatar circles to the header roster alongside existing text names.

---

### Q2: Avatar placement in the header roster

| Option | Description | Selected |
|--------|-------------|----------|
| Avatar circle to the left of the name text | Flex row: [avatar] [name]. Mirrors ChatBubble bubble header. | ✓ |
| Avatar circle replacing the name text | Avatar-only roster. Compact but loses at-a-glance names. | |
| You decide | Claude picks the placement. | |

**User's choice:** Avatar to the left of the name text  
**Notes:** Consistent with ChatBubble header row pattern.

---

## Tenure Logic

### Q1: Which court_tenure rows to display?

| Option | Description | Selected |
|--------|-------------|----------|
| All tenure rows for this person | Show full history sorted chronologically. | ✓ |
| Most recent tenure row only | Show only the latest start_date row. | |
| The tenure overlapping the argument's argued_date | Contextually accurate but requires date join; fails with gaps. | |

**User's choice:** All tenure rows  
**Notes:** Handles multi-tenure Justices naturally; sorted by start_date ASC.

---

### Q2: How to display active Justices (end_date null)?

| Option | Description | Selected |
|--------|-------------|----------|
| "[start_year]–present" | e.g. "2005–present". | ✓ |
| Show only start year, omit the end | e.g. "Since 2005". | |
| You decide | Claude picks the format. | |

**User's choice:** "[start_year]–present"  
**Notes:** User then noted that for Justices with multiple tenures (e.g., Rehnquist as Associate Justice by Nixon, then Chief Justice by Reagan), the ideal solution would link appointing_president to individual tenure rows. This would require a data model change and was deferred to a future phase.

---

## Popover Card Layout

### Q1: How should the card be laid out?

| Option | Description | Selected |
|--------|-------------|----------|
| Photo left + text right (horizontal) | Compact contact-card pattern. Recommended for desktop. | ✓ |
| Photo above text (vertical card) | More spacious but taller; may clip on mobile. | |
| You decide | Claude picks the layout. | |

**User's choice:** Horizontal on desktop  
**Notes:** User specified "I like option 1 for desktop but we may need a vertical layout on mobile." Decision: responsive — horizontal at ≥768px, vertical stack below 768px.

---

### Q2: Bench vs. advocate visual distinction

| Option | Description | Selected |
|--------|-------------|----------|
| Identical layout, different field sets | One component. Bench fields conditional. | ✓ |
| Different visual treatment for bench vs. advocate | e.g. border accent or different bg for bench. | |

**User's choice:** Identical layout, different field sets  
**Notes:** Consistent with apolitical framing constraint — no visual ranking between speaker types.

---

## Claude's Discretion

- Whether the header roster trigger wraps avatar-only or avatar+name together
- Exact `SpeakerPopover` card dimensions and padding
- Photo/initials circle size in the popover card (suggested 56–64px)
- Whether `Popover.Content` includes a close button in addition to Escape
- Popover arrow/caret presence

---

## Deferred Ideas

- **Tenure-linked appointment attribution**: Link appointing_president to individual court_tenure rows (Rehnquist example). Requires data model change. Future phase.
- **Advocate firm/organization (ADV-01)**: Advocate affiliation field. Already in REQUIREMENTS.md Future Requirements. Not in scope for Phase 14.
- **Photo loading shimmer**: Animated skeleton while photo resolves. Initials fallback handles missing photos; shimmer is cosmetic.
