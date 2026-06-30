# Phase 19: Pipeline Reliability - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-30
**Phase:** 19-pipeline-reliability
**Areas discussed:** Uniqueness basis, Duplicate warning UX, Metadata write-back, Docket prefill scope, Where operator sees prefilled metadata, Docket field behavior at ingest time, question_number in the duplicate preflight

---

## Uniqueness basis

| Option | Description | Selected |
|--------|-------------|----------|
| Source URL/key | Add source_url column to Argument (pdf_url or spaces_key). Works for both modes; upload deduplication is filename-based. | |
| Docket + question_number | Natural business key — same hearing session should never produce two rows. | ✓ |
| PDF content hash (SHA-256) | Byte-level identity. No false positives or collisions. Most robust but most code. | |

**User's choice:** Docket + question_number

**Follow-up — constraint structure:**
| Option | Description | Selected |
|--------|-------------|----------|
| Denormalize: add source_docket to Argument | Add source_docket VARCHAR column to Argument with UNIQUE(source_docket, question_number). | ✓ |
| Constraint via case_arguments join | Unique partial index on join table — harder to express as standard DB constraint. | |

**Follow-up — behavior when DB constraint fires:**
| Option | Description | Selected |
|--------|-------------|----------|
| Raise hard error — mark job FAILED | IntegrityError surfaces as FAILED with human-readable error_message. | ✓ |
| Return existing argument — mark job COMPLETED | Detect conflict, fetch existing Argument, set argument_id, mark COMPLETED. | |

---

## Duplicate warning UX

| Option | Description | Selected |
|--------|-------------|----------|
| Server-side: form action returns warning state | SvelteKit action checks for matching source_docket, returns warning state. | |
| Client-side: JS preflight API call on submit | JS calls GET endpoint before form submits; shows inline warning if match found. | ✓ |
| Warn on page load when docket is in query params | Only checks if operator pre-fills docket in URL. Limited coverage. | |

**User's choice:** Client-side JS preflight

**Follow-up — what preflight checks (docket not in form currently):**
| Option | Description | Selected |
|--------|-------------|----------|
| Source URL for URL mode (best-effort) | Check pdf_url against existing jobs/arguments. Upload mode gets no pre-submit warning. | |
| Add a docket field to the start form | Make docket a visible optional input. JS checks by docket+question. Consistent with DB constraint key. | ✓ |

**Follow-up — docket field required vs. optional:**
| Option | Description | Selected |
|--------|-------------|----------|
| Optional | If filled, JS preflight checks; if empty, no preflight fires. | ✓ |
| Required | Operator must enter docket before submitting. | |

**Follow-up — warning UX when preflight finds match:**
| Option | Description | Selected |
|--------|-------------|----------|
| Inline warning banner with link, operator can proceed | Warning above Submit: link to existing argument + Cancel + Start anyway. | ✓ |
| Block submission entirely | Submit disabled; no way to re-run intentionally. | |

---

## Metadata write-back

| Option | Description | Selected |
|--------|-------------|----------|
| Parse step auto-writes at end of parse | Parse calls cover extractor, writes results to DB after parse completes. | ✓ |
| Separate post-parse enrichment step | New CLI subcommand (enrich) that operator triggers explicitly. | |
| On-demand via job detail page | Job detail shows extracted values; operator clicks Apply to write to DB. | |

**Follow-up — conditional vs. unconditional:**
| Option | Description | Selected |
|--------|-------------|----------|
| Conditional: only overwrite placeholders | Parse checks for placeholder values before overwriting. | ✓ |
| Unconditional: always overwrite | Parse always writes extractor results over whatever is in DB. | |

**Follow-up — if extraction fails:**
| Option | Description | Selected |
|--------|-------------|----------|
| Leave placeholder values unchanged — continue parse normally | (Original option) | |
| Mark parse as partial success / log a warning | (Original option) | |

**User's free-text response:** "Instead of the current placeholders, I'd rather the fields that can't be extracted are left empty. If the fields are populated, even with obvious placeholder values, I'm more likely to accidentally think it was successful. Perhaps we need a small indicator that denotes if a value was extracted."

**Decision: leave fields null (not synthetic placeholders) when extraction can't populate them. Show extracted value as hint text on fields that already have operator-entered values.**

**Follow-up — argued_date nullable:**
| Option | Description | Selected |
|--------|-------------|----------|
| Yes — make argued_date nullable via migration | Migration 0011 makes argued_date nullable. Job-driven ingest leaves it NULL. | ✓ |
| Keep NOT NULL — use a sentinel date | Keep schema strict; use clearly invalid date as placeholder. | |

**Follow-up — extraction indicator:**
| Option | Description | Selected |
|--------|-------------|----------|
| Empty field = not extracted — no extra indicator | Emptiness itself is the signal. | ✓ |
| Small badge or icon next to extracted fields | Field-level visual decoration; extra columns required. | |
| Single status indicator on job/argument page | Overall extraction status, not field-level. | |

---

## Docket prefill scope

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — extend extractor to parse docket numbers | Add docket regex to cover_extractor.py for both Alderson and Heritage formats. | ✓ |
| No — prefill only argued_date and case_name | Docket stays operator-entered; success criteria scoped down. | |

**Follow-up — if operator provided docket AND extraction finds one:**
| Option | Description | Selected |
|--------|-------------|----------|
| Operator input wins — extraction only fills if null | If source_docket was set at ingest, parse skips it. | |
| Extraction wins — always overwrite | Parse always writes extracted docket, even if operator entered one. | |

**User's free-text response:** "I want the operator to see any extracted data, even if it's for a field that was previously populated, so they can decide if they want to use the extracted data or keep their edits. Don't auto-populate extracted data unless the field was already blank. Show the extracted data below the field with small text like 'Extracted data: [data]'."

**Decision: null fields get auto-populated; populated fields get hint text "Extracted: [value]" below the input stored via cover_metadata JSONB column.**

**Follow-up — where to store raw extraction output:**
| Option | Description | Selected |
|--------|-------------|----------|
| New cover_metadata JSONB column on arguments | Migration adds arguments.cover_metadata JSONB. Parse always writes here. | ✓ |
| Reuse admin_jobs.discrepancies JSONB | No new column; simpler migration. But wrong table for argument editor access. | |

---

## Where operator sees prefilled metadata

| Option | Description | Selected |
|--------|-------------|----------|
| Job detail page only — add metadata fields there | Editable inputs on /admin/pipeline/[id] alongside step status. | ✓ |
| Argument editor only — link from job detail | Link to existing /admin/arguments/[id] editor; no new form on job detail. | |
| Both — summary on job detail, full editor in argument admin | Read-only summary on job detail with Edit → link. | |

---

## Docket field behavior at ingest time

| Option | Description | Selected |
|--------|-------------|----------|
| Pass through to ingest — creates real Case row immediately | Docket from form passed as --primary-docket to ingest subprocess. | ✓ |
| Only used for preflight — not passed to ingest | Docket field is check-only; ingest still runs with synthetic docket. | |

---

## question_number in the duplicate preflight

| Option | Description | Selected |
|--------|-------------|----------|
| Add question_number to the start form, default 1 | Show Q1/Q2 toggle/select on start form; preflight checks (docket, question). | ✓ |
| Always assume Q1 in the preflight | Preflight always checks Q1; Q2 arguments could get false "no duplicate". | |

---

## Claude's Discretion

None — user made explicit choices for all decisions.

## Deferred Ideas

- **"Live polling for pipeline list page job cards"** — reviewed todo, not folded. Belongs to Phase 20: Live Pipeline Status (PIPE-23, PIPE-24).
