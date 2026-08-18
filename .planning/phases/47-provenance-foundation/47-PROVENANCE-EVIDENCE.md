# Phase 47 — Provenance Evidence (D-06 three-combination verification)

This document records the actual rows read back after re-seeding the dev database through the
real `reset_to_fixture` path, and after driving the two `pdf_pipeline` legs through the real
`pipeline.commands.parse.run_parse` writer. Every value below is copied verbatim from a live
query or test run output — no value has been rounded, paraphrased, or inferred.

**Reminder (CLAUDE.md / apolitical framing constraint):** `source` / `method` / `external_id`
are operator-facing lineage only. Nothing recorded here is, or should be, surfaced on the public
site as a quality, credibility, or trust signal to end users.

---

## corpus/direct (live re-seed)

**Timestamp (UTC):** 2026-08-18T14:05:08.016279+00:00
**Resolved database:** `postgresql+asyncpg://scotus:***@172.26.32.1:5432/scotus` (masked; host `172.26.32.1`, db `scotus`)
**Alembic revision confirmed before and after the reseed:** `0026 (head)`

**Method:** A scratchpad script (`reset_and_readback.py`) opened a real `AsyncSession` against
`DATABASE_URL` and called `api.services.admin_dev.reset_to_fixture(db)` directly — the real
production function, no HTTP server, no hand-rolled substitute. `reset_to_fixture` completed in
**77.2s**. Provenance was then read back with raw SQL off the live rows in a fresh session (to
avoid any identity-map staleness), joining `arguments` to `import_run` — no inference, no ORM
convenience property, the query reads the columns directly.

### Pre-seed row counts (captured before the reseed)

| Table | Count |
|---|---|
| arguments | 4 |
| utterances | 0 |
| import_run | 0 |
| cases | 4 |
| people | 36 |
| admin_jobs | 4 |
| court_tenures | 0 |
| case_arguments | 4 |
| argument_participants | 38 |

### Post-reseed row counts (exact)

| Table | Count |
|---|---|
| arguments | 4 |
| utterances | 1001 |
| import_run | 4 |
| cases | 4 |
| people | 36 |
| admin_jobs | 4 |
| court_tenures | 0 |
| case_arguments | 4 |
| argument_participants | 38 |

### `reset_to_fixture` return payload — four fixtures seeded

| conversation_id | case_name | role | argument_id | argument_status | admin_job_status |
|---|---|---|---|---|---|
| 15169 | Baltimore & Ohio Railroad Company v. United States | Complexity | 1771 | pipeline | paused |
| 13015 | Archawski v. Hanioti | Draft | 1772 | draft | completed |
| 18897 | Anderson v. Liberty Lobby, Inc. | Published | 1773 | published | completed |
| 22372 | Abbott v. United States | Mid-pipeline | 1774 | pipeline | running |

### Per-term import stats (from the run log)

| Term | Arguments created | Cases created | Utterances created | Stage-direction utterances | People created | People reused | Unattributed speakers skipped | Bench tenure mismatches | Conversations errored | Utterance rows errored | Docket/question conflicts |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1966 | 1 | 1 | 467 | 13 | 17 | 0 | 1 | 8 | 0 | 0 | 0 |
| 1955 | 1 | 1 | 164 | 3 | 4 | 1 | 0 | 3 | 0 | 0 | 0 |
| 1985 | 1 | 1 | 157 | 0 | 6 | 1 | 0 | 5 | 0 | 0 | 0 |
| 2010 | 1 | 1 | 197 | 0 | 9 | 0 | 1 | 6 | 0 | 0 | 0 |

Every term reported 0 conversations errored, 0 utterance rows errored, 0 docket/question
conflicts, 0 speakers flagged.

> **Note on `bench_tenure_mismatch` warnings:** these are pre-existing, D-03 flag-only behavior
> (`court_tenures` is 0 in this fixture set — no `CourtTenure` rows exist to match against). They
> are observed here for completeness but are unrelated to Phase 47 and are not a Phase 47 defect.

### `import_run` rows for the four `FIXTURE_SET` conversation ids (read directly off the live rows)

Query (no join-based inference beyond `arguments.id = import_run.argument_id`, every column
selected directly):

```sql
SELECT
    a.oyez_transcript_id AS conversation_id,
    a.id AS argument_id,
    r.id AS import_run_id,
    r.step,
    r.status,
    r.source,
    r.method,
    r.external_id,
    r.pdf_path,
    r.pdf_url
FROM arguments a
JOIN import_run r ON r.argument_id = a.id
WHERE a.oyez_transcript_id IN ('15169', '13015', '18897', '22372')
ORDER BY a.oyez_transcript_id, r.id
```

| conversation_id | argument_id | import_run_id | step | status | source | method | external_id | pdf_path | pdf_url |
|---|---|---|---|---|---|---|---|---|---|
| 13015 | 1772 | 2 | parse | completed | corpus | direct | 13015 | NULL | NULL |
| 15169 | 1771 | 1 | parse | completed | corpus | direct | 15169 | NULL | NULL |
| 18897 | 1773 | 3 | parse | completed | corpus | direct | 18897 | NULL | NULL |
| 22372 | 1774 | 4 | parse | completed | corpus | direct | 22372 | NULL | NULL |

Every row reads `source = 'corpus'`, `method = 'direct'`, `external_id` equal to the conversation
id, `pdf_path IS NULL`, `pdf_url IS NULL` — exactly as PROV-05 (reframed by D-03) requires.
`Argument.oyez_transcript_id` for each of the four rows still equals its `external_id` (both are
the same conversation id) — the `import_run.external_id` dual-write did not relocate the corpus
dedup key or the public API field.

### Corroborating integrity assertions (same run, live dev database)

| Assertion | Query | Result |
|---|---|---|
| Argument rows matching the four `FIXTURE_SET` conversation ids | `SELECT count(*) FROM arguments WHERE oyez_transcript_id IN ('15169','13015','18897','22372')` | **4** (re-import created no duplicate `Argument`) |
| Orphan utterances (no matching `import_run`) | `SELECT count(*) FROM utterances u LEFT JOIN import_run r ON u.import_run_id = r.id WHERE r.id IS NULL` | **0** |
| `strategy` column existence, `utterances` and `import_run` | `SELECT table_name, column_name FROM information_schema.columns WHERE table_name IN ('utterances','import_run') AND column_name = 'strategy'` | **zero rows returned** — the column is gone from both tables |

