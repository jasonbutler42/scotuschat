# Phase 2: Speaker Resolution - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-12
**Phase:** 2-Speaker Resolution
**Areas discussed:** Alias table schema, People + seed delivery, Resolve algorithm, UI speaker data flow, Em dash bug

---

## Alias Table Schema

**Pre-discussion clarification:** User clarified the overall resolution approach before questions were asked — the goal is to automatically identify speakers and tie them to DB entries. Exact matches auto-resolve; unrecognised labels prompt the operator interactively. Creating new people records is fine as long as the operator confirms it.

| Option | Description | Selected |
|--------|-------------|----------|
| Exact string match | Literal string stored per row; fast lookup, predictable | ✓ |
| Regex patterns | Rows store regex for flexible matching | |
| Exact for Justices, regex for counsel | Mixed match_type | |

**User's choice:** Exact string match
**Notes:** User described the resolution process organically — alias table is the fast-path; interactive prompt is the fallback. This is simpler and more reliable than regex or LLM-driven approaches.

---

## Normalization

| Option | Description | Selected |
|--------|-------------|----------|
| Uppercase + strip trailing colon/whitespace | "Justice Kagan:" → "JUSTICE KAGAN" | ✓ |
| Exact as-is | No normalization; alias must match transcript exactly | |

**User's choice:** Uppercase + strip trailing colon/whitespace
**Notes:** Handles casing and punctuation variants from pdfplumber without requiring duplicate alias rows.

---

## Resolve Scope (must-resolve-all vs. skip-allowed)

| Option | Description | Selected |
|--------|-------------|----------|
| Must resolve all | Step only completes when every unique non-null label is resolved | ✓ |
| Skip allowed | Operator can skip; UI falls back to raw label for unresolved speakers | |

**User's choice:** Must resolve all
**Notes:** Guarantees the UI always shows a real name. Stage directions (null raw_speaker_label) are excluded from the resolve requirement.

---

## People + Seed Delivery

| Option | Description | Selected |
|--------|-------------|----------|
| Pre-seed current Justices | Seed file with current + historical Justices via CLI command | ✓ |
| Start empty, build interactively | No pre-seeding; operator handles all labels on first run | |

**User's choice:** Pre-seed current Justices
**Notes:** Justices appear in every argument transcript; pre-seeding them avoids repeated interactive resolution. Counsel is created interactively and persisted to the alias table.

---

## Resolve Interactive Prompt UX

| Option | Description | Selected |
|--------|-------------|----------|
| Show existing people + Create new option | Numbered list of existing people; "Create new person" as last option | ✓ |
| Free-text name entry | Operator types name; auto-creates if not found | |

**User's choice:** Show existing people + Create new option
**Notes:** Numbered list is more reliable — avoids name typos creating duplicate people records.

---

## UI Speaker Data Flow

| Option | Description | Selected |
|--------|-------------|----------|
| Embed in utterances API response | JOIN to people + roles in API-01; add speaker_name + speaker_role fields | ✓ |
| Frontend calls GET /people/{id} per speaker | Separate N API calls from SvelteKit | |

**User's choice:** Embed in utterances API response
**Notes:** Fits SSR pattern — page.server.ts loads everything in one call. No N+1 per-speaker requests.

---

## Em Dash Bug

| Option | Description | Selected |
|--------|-------------|----------|
| Fix now as standalone patch | Targeted edit to parser before Phase 2 planning | ✓ |
| Fix in Phase 2 | Add text normalization to Phase 2 scope | |
| Defer to Phase 3 | Accept bug for now | |

**User's choice:** Fix now as standalone patch
**Notes:** Em dash → `&shy;` (U+00AD soft hyphen) corruption in pdfplumber text extraction. Fix in `pipeline/parser/extractor.py` or `state_machine.py`. Re-parse Obergefell after fix.

---

## Claude's Discretion

- Exact `speaker_alias` table column names and schema details
- Whether `argument_participants.person_id` is also updated during resolve (in addition to `utterances.person_id`)
- Seed data file format and `seed-aliases` CLI implementation
- Interactive prompt display details (paging, formatting)
- `role_name` derivation (join people → roles)
- `people.full_name` display format ("Elena Kagan" vs. "Kagan, Elena")

## Deferred Ideas

- LLM-assisted matching (PIPE-07 original spec) — replaced by interactive-first; revisit when batch processing many transcripts
- `photo_url` on Person — Phase 3 (needed for avatars)
- Obergefell Q2 session — can be loaded after Phase 2 validates the pipeline
- Additional cases beyond Obergefell — pipeline supports them; out of Phase 2 scope
