# Phase 22: Schema Foundations - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-02
**Phase:** 22-schema-foundations
**Areas discussed:** Migration structure, Status log columns, Appointed-by backfill, Advocate title extraction

---

## Migration Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Two migrations (0012 + 0013) | 0012: enum expansion + argument_status_log; 0013: column additions/moves. Each has a clean downgrade() with a single concern. | ✓ |
| One migration (0012) | All 4 changes together. Simpler file count. Precedent: 0008 combined enum + column. | |

**User's choice:** Two migrations
**Notes:** No additional notes.

---

## Status Log Columns

**Question 1: What columns should argument_status_log have?**

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal: id, argument_id, status, created_at | Everything Phase 26 needs. Status value tells you what the argument became at that timestamp. | ✓ |
| With previous_status | Shows 'Draft → Published' explicitly; requires extra logic when writing log entries. | |
| With notes TEXT | Nullable notes for context like 'Unpublished — outdated'. | |

**User's choice:** Minimal schema

**Question 2: Backfill timestamp source?**

| Option | Description | Selected |
|--------|-------------|----------|
| resolved_at when available, else CURRENT_TIMESTAMP | Best available proxy for when the argument first existed. | ✓ |
| Always CURRENT_TIMESTAMP | Simpler SQL; all backfilled entries show migration date. | |

**User's choice:** resolved_at when available, else CURRENT_TIMESTAMP

---

## Appointed-by Backfill

**Question 1: Multi-tenure Justice backfill strategy?**

| Option | Description | Selected |
|--------|-------------|----------|
| Copy to ALL tenure rows | Simple SQL UPDATE JOIN; edge cases fixed via Phase 27 UI. | |
| Copy only to earliest tenure row | Conservative; leaves gaps that Phase 27 UI must fill. | |
| No backfill — clean slate | User indicated existing data is incorrect/test data; nuke it. | ✓ |

**User's choice:** No backfill — clean slate
**Notes:** User stated: "I haven't put enough work into these and most of what I've put in was incorrect for testing so I'm okay with NO backfilling here. Just nuke it and give me a clean slate."

**Question 2: Drop old people columns in same migration or staged?**

| Option | Description | Selected |
|--------|-------------|----------|
| Drop in same migration (0013) | Add nullable columns to court_tenures, no backfill, drop from people — one clean migration. | ✓ |
| Stage it: add now, drop in 0014 | Safer if any existing API reads people.appointed_by. | |

**User's choice:** Drop in same migration (0013)

---

## Advocate Title Extraction

**Question 1: What does argument_participants.title capture?**

| Option | Description | Selected |
|--------|-------------|----------|
| The subtitle line after the name | Extract 'Solicitor General', 'Counsel of Record' etc. from line after advocate name in TOC. NULL when absent. | ✓ |
| Name-line prefix/suffix only | Capture 'GEN.' or 'ESQ.' from name line. Simpler regex but less meaningful. | |
| Manual entry only — schema only in Phase 22 | Add column but skip parse extraction; operator fills via Phase 23 UI. | |

**User's choice:** The subtitle line after the name

**Question 2: Extraction failure handling?**

| Option | Description | Selected |
|--------|-------------|----------|
| Silent NULL | Never raise on extraction failure. NULL = not found. Parse step continues normally. | ✓ |
| Log a warning and continue | Print notice when no subtitle found. Useful for monitoring extraction quality. | |

**User's choice:** Silent NULL — leave title as NULL

**Question 3: Where does extraction logic live?**

| Option | Description | Selected |
|--------|-------------|----------|
| Extend cover_extractor.py | New function alongside extract_advocate_sides. TOC parsed once; both functions share the read. | ✓ |
| New function inline in parse.py | Closer to where it's used; keeps cover_extractor.py smaller. | |

**User's choice:** Extend cover_extractor.py

---

## Claude's Discretion

- **Migration ordering within 0012**: Enum expansion must precede CREATE TABLE due to PG constraint — not a judgment call. Confirmed as technically mandated.

## Deferred Ideas

None — discussion stayed within phase scope.
