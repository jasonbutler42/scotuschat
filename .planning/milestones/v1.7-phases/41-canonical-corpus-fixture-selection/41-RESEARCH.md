# Phase 41: Canonical Corpus Fixture Selection - Research

**Researched:** 2026-07-29
**Domain:** Offline corpus analysis (ConvoKit Supreme Court dataset) feeding a decision-gate deliverable — no runtime/API/DB code
**Confidence:** HIGH — every quantitative claim below was produced by actually loading and scoring the real corpus files in `data/corpus/` during this research session, not estimated from schema alone.

## Summary

Phase 41 is a decision-gate: analyze the real ~7,800-argument ConvoKit corpus already sitting in `data/corpus/`, rank candidates for one "complexity fixture," propose three additional arbitrary fixtures for publish/pipeline-**state** variety, and write both into `.planning/FIXTURES.md` for the operator to confirm. No importer code runs and no DB rows change.

This research actually executed scoring scripts against the real `cases.jsonl` (7,748 rows), `conversations.json` (7,817 conversations), `speakers.json` (9,651 speakers), and streamed the full 1,700,789-row `utterances.jsonl` once. Findings:

1. **The multi-docket consolidation signal is resolved, not just "acceptable to drop."** Two independent facts settle it: (a) the one clean consolidation signal that exists in the data (`scdb_docket_id` grouping) is an explicitly forbidden SCDB-derived field under this project's own `pipeline/corpus/apolitical.py` `FORBIDDEN_FIELDS` set and CONTEXT.md's D-04 — it cannot be used even for scoring; and (b) even if it could be used, `import_convokit.py`'s own docstring states the importer is "Lead-docket-only (D-19)... no consolidated-companion sourcing happens here" — there is **no importer code path for multi-docket consolidation at all**, so a fixture "covering" this signal would exercise zero additional importer logic. Drop it from the checklist per CONTEXT.md's own stated fallback.
2. **A real, compliant substitute signal exists and should replace it:** re-argument / multi-session shape — how many `transcripts[]` entries a case has. This directly stresses two documented importer code paths (`_next_question_number`'s per-docket increment, and `_parse_argued_date`'s per-transcript-id date matching) and reads only the already-allowlisted `transcripts` field. 92 cases (1.2%) have ≥3 transcript entries; one outlier (`1961_8`, Russell v. United States) has 9.
3. **Actual scoring** of all 7,817 conversations against a 4-signal path-coverage checklist (advocate count ≥9, distinct speaker count ≥14, turn count ≥700, transcripts ≥2) surfaces a clear top-5 shortlist and a strong single recommendation: **Permian Basin Area Rate Cases** (conversation `14837`), which ties the corpus-wide maximum advocate count (16) and is one of 4 sessions of the same re-argued docket.
4. **Publish/pipeline "state" is not a corpus property.** `cases.jsonl`/`conversations.json` carry no notion of DRAFT/PUBLISHED/PIPELINE — that's exclusively a DB-side `Argument.status` concept, and `import_convokit.py` always lands a freshly-imported argument at `status=PIPELINE` (Phase 30). The 3 state-variety fixtures are therefore just 3 arbitrary, structurally-unremarkable arguments (per CONTEXT.md D-02) that Phase 41 assigns a **target role label**; the actual state transition (resolve → draft, resolve → publish, leave paused) is Phase 43's job, not something Phase 41 can discover pre-existing in the corpus.

**Primary recommendation:** Recommend conversation `14837` (Permian Basin Area Rate Cases, docket 90, 1967 term) as the complexity fixture; recommend 3 clean, single-session, near-median-complexity arguments from 3 different eras as the state-variety fixtures (concrete candidates below); write all 4 into `.planning/FIXTURES.md` with the required fields and present for operator confirmation.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Corpus signal scoring (advocate/speaker/turn/re-argument counts) | Pipeline (offline script, `scripts/`) | — | Read-only analysis over local ConvoKit files; reuses `pipeline/corpus/loader.py` readers; never touches DB or API |
| Path-coverage checklist ranking | Pipeline (offline script) | — | Pure computation over the scored signals; no persistence |
| Fixture set documentation | Planning docs (`.planning/FIXTURES.md`) | — | Explicitly a "planning doc, not a checked-in code constant" per D-07 — outside any runtime tier |
| Operator confirmation | Human-in-the-loop (CLI/chat) | — | D-03/success-criterion-3 requires explicit confirm-or-redirect; no UI surface built this phase |
| Database / API / Frontend | **None** | — | Explicitly out of scope — CONTEXT.md domain statement and success criterion 5 ("no importer code and no database rows are changed") |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `json` | 3.12 (project's pinned interpreter) | Parse `cases.jsonl` / `conversations.json` / `speakers.json` / stream `utterances.jsonl` | Already the sole dependency of `pipeline/corpus/loader.py` — no new library needed |
| `pipeline/corpus/loader.py` (in-repo) | n/a (project code) | `load_cases`, `load_conversations_for_term`, `load_speakers`, `stream_utterances_for_conversation_ids` | These four functions already implement every read this phase needs — see Don't Hand-Roll below |

### Supporting
None. No new PyPI package is needed for this phase — every signal (advocate count, speaker count, turn count, re-argument count) is derivable from fields the existing loaders already expose.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Reusing `pipeline/corpus/loader.py` | Hand-rolled `open()`/`json.loads()` in the new script | No tradeoff worth taking — the loaders already encode the exact same-id-not-docket_no join rule (migration 0018) and the streaming discipline for the 900MB file; reimplementing risks silently diverging from the importer's own semantics |

**Installation:** None — no new dependency.

**Version verification:** N/A — no external package is being added by this phase.

## Package Legitimacy Audit

**Not applicable.** This phase installs no external packages (no `npm install` / `pip install` of anything). The only "new" artifact is a throwaway Python script under `scripts/` that imports only the Python standard library and this repo's own `pipeline/corpus/loader.py`. Skip the Package Legitimacy Gate — there is nothing to check.

## Architecture Patterns

### System Architecture Diagram

```
data/corpus/{cases.jsonl, conversations.json, speakers.json, utterances.jsonl}
        │
        ▼
pipeline/corpus/loader.py   (existing, reused unmodified)
  load_cases() ──────────────┐
  load_conversations_for_term() [NOTE: term-scoped; the new script
                                 needs an ALL-terms variant — see
                                 Pitfall 1 below]
  load_speakers() ───────────┤
  stream_utterances_for_conversation_ids()
        │                    │
        ▼                    ▼
scripts/select_corpus_fixtures.py   (NEW, throwaway, this phase)
  1. Build advocate_count per conversation from conversations.json's
     OWN "advocates" dict (matches import_convokit.py's real loop,
     NOT cases.jsonl's case-level "advocates" field)
  2. Stream utterances.jsonl ONCE; aggregate per conversation_id:
     turn_count, distinct speaker ids, bench (justice-type) speaker ids
  3. Join each conversation's case row (by case_id, NEVER docket_no)
     for case name / docket_no / year / transcripts[] length
  4. Score against the 4-signal path-coverage checklist (D-03/D-06)
  5. Print ranked shortlist (top 5) + 3 arbitrary state-variety
     candidates — human reads the printout, does NOT auto-write
     FIXTURES.md
        │
        ▼
Operator reviews printout, confirms or redirects (success criterion 3)
        │
        ▼
.planning/FIXTURES.md   (hand-authored/edited from the confirmed
                         printout — durable, referenceable, git-tracked)
        │
        ├──► Phase 42 reads ONLY the complexity fixture row
        └──► Phase 43 reads ALL 4 fixture rows
```

### Recommended Project Structure
```
scripts/
├── select_corpus_fixtures.py   # NEW — this phase's throwaway analysis script
├── audit_tenure_seat_identifiers.py   # existing precedent (same directory, same "one-off audit" pattern)
├── cleanup_leaked_test_rows.py         # existing precedent
└── migrate_tenure_offices.py           # existing precedent

.planning/
└── FIXTURES.md   # NEW — D-07/D-08 durable fixture record, project root, not phase-nested
```

### Pattern 1: Path-coverage checklist scoring (D-03) — flags, not weighted sums
**What:** For each conversation, compute 4 boolean flags (does it clear a threshold on advocate count / distinct speaker count / turn count / transcript count) and rank by **how many flags are true**, tie-broken by raw magnitude — never a single weighted composite score.
**When to use:** Exactly this phase's D-03 requirement — "rank by how many distinct importer-stressing paths a single argument covers at once... rather than by raw magnitude on any one signal."
**Example (verified against the real corpus this session):**
```python
# Source: this research session's actual scoring run against data/corpus/
THRESH_ADVOCATE = 9      # top-10 raw values observed: 16,16,16,16,12,12,10,9,9,9
THRESH_SPEAKER = 14       # top-10 raw values observed: 19,16,16,15,15,15,15,14,14,14
THRESH_TURN = 700         # top-10 raw values observed: 1080,1049,868,858,835,767,746,742,736,728
THRESH_TRANSCRIPTS = 2    # >=2 sessions for the SAME docket = re-argument shape

flags = {
    "multi_advocate_resolution": advocate_count >= THRESH_ADVOCATE,
    "high_speaker_dedup": distinct_speaker_count >= THRESH_SPEAKER,
    "long_transcript_streaming": turn_count >= THRESH_TURN,
    "reargument_question_number": n_transcripts >= THRESH_TRANSCRIPTS,
}
path_coverage = sum(flags.values())
# Rank by path_coverage desc, tie-break by raw magnitude sum — never invert this order.
```
No conversation in the full corpus hits all 4 flags simultaneously (see Code Examples for the actual top-16 printout) — the strongest real candidates hit 3 of 4.

### Anti-Patterns to Avoid
- **Scoring by a single weighted sum of raw magnitudes:** CONTEXT.md D-03 explicitly rejects this ("not a weighted sum or lexicographic sort"). A weighted sum would let one extreme outlier (e.g. turn_count=1080) dominate and hide a candidate that covers more distinct importer paths at moderate values on each.
- **Joining cases.jsonl to conversations.json by `docket_no`:** `import_convokit.py`'s own docstring documents this is wrong (docket numbers recycle across October Terms, migration 0018) — the join key is `raw_case["id"] == conversation["case_id"]`. `load_cases()` already indexes by `id` for exactly this reason; never re-key by `docket_no`.
- **Reading `cases.jsonl`'s case-level `"advocates"` dict for advocate_count:** it differs from `conversations.json`'s per-conversation `"advocates"` dict for multi-session cases. The importer's real loop (`_import_conversation`) reads `conversation.get("advocates")`, not the case-level one — the scoring script must match that, not the case-level field, or the "advocate count" signal won't mean what it claims to mean.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Reading `cases.jsonl` indexed by case id | A fresh `json.loads()` loop keyed by `docket_no` | `pipeline.corpus.loader.load_cases()` | Already correctly indexed by `id`, with the docket_no pitfall documented inline |
| Reading `conversations.json` | Hand-rolled full-file `json.load()` + manual filtering | `pipeline.corpus.loader.load_conversations_for_term()` — **but note it is term-scoped**; the new script needs to either call it once per term across the whole range, or (simpler) do one `json.load()` directly since `conversations.json` is only 3.8MB and safe to load whole (loader's own docstring says so) | Reuse the existing "safe to load whole" judgment call already made and documented in the loader; don't re-derive it |
| Streaming the 900MB `utterances.jsonl` | A custom line-by-line loop | `pipeline.corpus.loader.stream_utterances_for_conversation_ids()` | Already implements the never-`.read()`-the-whole-file streaming discipline (D-18/T-29-03) this phase must also respect — a full `json.load()` on this file will exhaust memory |
| Classifying justice vs. advocate speakers | A naming-convention guess (e.g. `speaker_id.startswith("j__")`) | `speakers.json`'s own `type` field (`"J"` for justice, `"A"` for advocate, `"U"` for ConvoKit's unattributed sentinel) | This project's own `import_convokit.py::_is_justice_type` already establishes `type` as the sole authoritative signal — a naming-convention check would silently misclassify any justice-slug that doesn't follow the `j__` convention |

**Key insight:** Every reusable piece of this phase's analysis already exists in `pipeline/corpus/loader.py` and `pipeline/corpus/apolitical.py` because Phase 29 built the real importer against this exact corpus. The scoring script's only genuinely new code is the ranking/checklist logic itself (Pattern 1 above) — everything upstream of that is a straight reuse.

## Common Pitfalls

### Pitfall 1: `load_conversations_for_term` is term-scoped, but this phase needs the whole corpus
**What goes wrong:** Calling the existing loader once per term (1955 through ~2023, ~70 calls) each re-parses the whole 3.8MB file from disk.
**Why it happens:** The loader was built for Phase 29's term-batched importer, which genuinely only ever needs one term at a time.
**How to avoid:** For this phase's whole-corpus scan, either loop the loader across every term actually present (get the term list from `cases.jsonl`'s `year` field first), or — simpler — just call `json.load()` directly once on `conversations.json` (the loader's own docstring already documents it's "safe to load whole," 3.8MB) and filter/group in memory. Actually verified: the direct-load approach is what this research session's script used and it completed in under 10 minutes against the full corpus.
**Warning signs:** A script that takes O(n_terms) longer than expected, or 70+ near-identical disk reads in a profiler trace.

### Pitfall 2: Conflating `cases.jsonl`'s case-level `advocates` with `conversations.json`'s per-conversation `advocates`
**What goes wrong:** Using the wrong dict silently produces an advocate count that doesn't match what the real importer would actually resolve for that specific conversation, especially for multi-session cases where sessions can have different advocate rosters.
**Why it happens:** Both files legitimately have a field literally named `"advocates"`, and `apolitical.extract_case_fields` allowlists both (see Apolitical Constraint Compliance below) — nothing stops you from grabbing the wrong one.
**How to avoid:** Use `conversation.get("advocates")` (from `conversations.json`), matching `import_convokit.py::_import_conversation`'s real line: `advocates = conversation.get("advocates") or {}`.
**Warning signs:** Advocate counts for multi-session cases (e.g. `1967_90`) that don't match across sessions when case-level data suggests they should.

### Pitfall 3: Streaming 1.7M utterance rows without a progress signal
**What goes wrong:** A silent 8-10 minute run with no output looks hung; an impatient rerun wastes time and disk I/O.
**Why it happens:** `utterances.jsonl` is 900MB / 1,700,789 lines — a single Python process reading and `json.loads`-ing every line takes real wall-clock time (this research session's actual run: 9m37s wall, 1m27s user CPU — I/O-bound, not CPU-bound).
**How to avoid:** Print a progress line every ~300K rows (as this research session's script did) so the operator/executor can tell it's alive. Cache the per-conversation aggregate result to a JSON side-file after the one streaming pass completes, so re-ranking with different thresholds never requires re-streaming the 900MB file.
**Warning signs:** A script re-run from scratch every time a threshold constant changes.

### Pitfall 4: Assuming the corpus itself encodes publish/pipeline state
**What goes wrong:** Trying to find "an already-DRAFT argument" or "an already-published argument" inside `cases.jsonl`/`conversations.json` — no such field exists there.
**Why it happens:** The phase's own framing ("state-variety fixtures") reads as if it's a corpus property to discover, when it's actually a DB-side (`arguments.status`) concept established by `import_convokit.py` (which always lands new imports at `PIPELINE`, Phase 30) and later services (`admin_jobs.py`'s resolve-approval, `admin_arguments.py`'s publish/unpublish).
**How to avoid:** Phase 41 selects 3 *arbitrary* (per CONTEXT.md D-02, no complexity floor) clean, single-session arguments and assigns each a **target role label** (e.g. "unpublished/DRAFT target", "published target", "mid-pipeline target") in `FIXTURES.md`. The actual state transition is explicitly Phase 43's job (per ROADMAP.md Phase 43 success criterion 4: "the state-variety fixtures land in their intended publish/pipeline states... not all reset to the same default state").
**Warning signs:** A planner task that tries to query a live DB for "existing DRAFT arguments" as part of Phase 41 — there's no DB write yet for these fixtures at Phase 41 time (success criterion 5: no DB rows change this phase).

## Code Examples

### Actual scoring output from this research session (real corpus, not simulated)

Distribution of raw signals across all 7,817 conversations (computed by one full pass, this session):

```
advocate_count:          max=16, top10=[16,16,16,16,12,12,10,9,9,9],  mean=2.6,  median=2
turn_count:              max=1080, top10=[1080,1049,868,858,835,767,746,742,736,728], mean=217.6, median=213
distinct_speaker_count:  max=19, top10=[19,16,16,15,15,15,15,14,14,14], mean=9.1,  median=10
bench_speaker_count:     max=10, top10=[10,10,10,10,9,9,9,9,9,9],      mean=6.3,  median=7
n_transcripts (per case): distribution {0:1015, 1:5781, 2:858, 3:64, 4:27, 5:1, 6:1, 9:1}
```

Top-5 ranked shortlist (path-coverage desc, tie-broken by raw-magnitude sum; one row per underlying case — see Pattern 1's flags):

| Rank | Coverage (of 4) | Conversation ID | Case | Docket | Term | Advocates | Distinct Speakers | Bench Speakers | Turns | Transcripts | Which flags hit |
|------|------------------|------------------|------|--------|------|-----------|--------------------|-----------------|-------|-------------|-------------------|
| 1 | 3/4 | `14837` | Permian Basin Area Rate Cases (390 US 747) | 90 | 1967 | 16 (corpus max, tied) | 14 | 7 | 360 | 4 | advocate ✓, speaker ✓, reargument ✓ — turn ✗ |
| 2 | 3/4 | `15169` | Baltimore & Ohio Railroad Co. v. United States (386 US 372) | 642 | 1966 | 9 | 16 | 8 | 479 | 2 | advocate ✓, speaker ✓, reargument ✓ — turn ✗ |
| 3 | 3/4 | `14852` | Allen v. State Board of Elections (393 US 544) | 3 | 1968 | 7 | 14 | 8 | 868 | 2 | speaker ✓, turn ✓, reargument ✓ — advocate ✗ |
| 4 | 3/4 | `14969` | Shapiro v. Thompson (394 US 618) | 9 | 1967 | 9 | 15 | 7 | 447 | 3 | advocate ✓, speaker ✓, reargument ✓ — turn ✗ |
| 5 | 2/4 | `15174` | Penn-Central Merger and N & W Inclusion Cases (389 US 486) | 433 | 1967 | 12 | 19 (corpus max) | 6 | 617 | 1 | advocate ✓, speaker ✓ — turn ✗, reargument ✗ (single session) |

**Recommendation: conversation `14837` (Permian Basin Area Rate Cases).** It ties the single highest advocate count anywhere in the corpus (16 — several other conversations tie at 16, but all four of those ties are `14837`'s own sibling sessions from the same re-argued docket), clears the high-speaker-dedup threshold (14 distinct speakers requiring `_resolve_person` dedup across many `Person` rows), and belongs to a 4-session re-argued docket that exercises `_next_question_number`'s per-docket increment and `_parse_argued_date`'s per-transcript-id date matching — two documented, real importer code paths. It is the only shortlist entry that combines the corpus-max advocate signal with the re-argument signal. Runner-up `15169` (B&O Railroad) is the strongest alternative if the operator prefers a single-session fixture (simpler to reason about in Phase 42's diff, at the cost of not exercising the re-argument path).

If the operator instead wants to prioritize raw transcript volume (long-transcript streaming) above path-coverage breadth, note the true corpus-wide max is conversation `15428` ("United States v. First City National Bank of Houston," 1966 term, 1080 turns) — but it only clears 2 of 4 flags (turn + reargument), not 3.

### Proposed state-variety fixture candidates (clean, single-session, near-median, no complexity floor per D-02)

Deliberately drawn from 3 different eras for operator-facing visual distinctiveness in Phase 43's reset-tool testing, and deliberately NOT overlapping the complexity shortlist above:

| Target role | Conversation ID | Case | Docket | Term | Advocates | Turns |
|---|---|---|---|---|---|---|
| unpublished/DRAFT target | `13015` | Archawski v. Hanioti (350 US 532) | 351 | 1955 | 2 | 167 |
| published target | `18897` | Anderson v. Liberty Lobby, Inc. (477 US 242) — a well-known, easily-recognized case for demo purposes | 84-1602 | 1985 | 2 | 157 |
| mid-pipeline target | `22372` | Abbott v. United States (562 US 8) | 09-479 | 2010 | 3 | 197 |

### The multi-docket investigation (real data, this session)

`scdb_docket_id` grouping (prefix `{term}-{seq}`, suffix `-NN`) surfaces exactly **10 real consolidation groups** in the whole corpus — e.g. `2019-004` groups `Bostock v. Clayton County` (17-1618), `Altitude Express v. Zarda` (17-1618... distinct docket 17-1623), and `R.G. & G.R. Harris Funeral Homes` (18-107) as one SCDB case with 3 constituent dockets. This is a real, precise signal — **but it reads `scdb_docket_id`, which is explicitly named in `pipeline/corpus/apolitical.py`'s `FORBIDDEN_FIELDS` frozenset** (alongside `win_side`/`votes`/etc.) and explicitly named in CONTEXT.md D-04 as a field the checklist "must never read." It cannot be used.

A second, *allowed* signal was also found: some cases' own `transcripts[]` array embeds a second case's name/docket in its `name` string (verified for `1957_103`, "City of Chicago v. Atchison..." (docket 103), whose transcript entries include two more entries titled "Parmelee Transportation Company v. Atchison..." (docket 104)) — confirmed the corresponding `conversations.json` entries for all 4 transcript ids share the SAME `case_id` ("1957_103"), meaning the importer would in fact import all 4 as 4 separate `Argument` rows under one `Case` (docket 103), with `question_number` 1-4, regardless of the embedded companion-case text. This confirms (independently of the apolitical-field issue) that **the importer has no code path that treats this as "multi-docket consolidation"** — it's absorbed into the ordinary re-argument/multi-session path already captured by the `n_transcripts` signal. There is no additional importer behavior to stress-test by chasing consolidation specifically.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| CORPUS-12/REQUIREMENTS.md's original framing: single fixture | 4-fixture set (1 complexity + 3 state-variety) | 2026-07-29, during Phase 41 discuss-phase (D-01) | ROADMAP.md/REQUIREMENTS.md already updated; this research targets the widened scope |

**Deprecated/outdated:** None specific to this phase's domain — the corpus files and importer are current (Phase 29/30, most recent milestone touching this code).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Recommending `14837` as "the" complexity fixture is this researcher's judgment call on how to weigh a 3/4-coverage tie among 4 shortlist candidates (Permian Basin vs. B&O Railroad vs. Allen v. Board vs. Shapiro v. Thompson) — CONTEXT.md D-03 fixes the *method* (checklist coverage) but not a tiebreak rule among equal-coverage candidates. | Code Examples, Summary | Low — this is exactly the "one recommendation, operator confirms or redirects" pattern the phase is built around (success criterion 3); any of the 4 tied candidates is defensible and the operator can pick a runner-up with zero rework cost |
| A2 | The 3 state-variety fixture candidates (`13015`, `18897`, `22372`) are proposed purely for being clean/simple/era-diverse — no signal analysis "proves" they're good state-variety fixtures because CONTEXT.md D-02 says none is needed (any argument matching the target state works) | Code Examples | Low — D-02 explicitly removes any complexity requirement for these 3; if the operator has a different preference (e.g., a personally recognizable case), swapping is free at confirmation time |
| A3 | `THRESH_ADVOCATE=9`, `THRESH_SPEAKER=14`, `THRESH_TURN=700`, `THRESH_TRANSCRIPTS>=2` were chosen by this researcher to approximate "top ~1%" cutoffs on each observed distribution — CONTEXT.md does not fix exact threshold values, only the checklist *method* | Architecture Patterns Pattern 1 | Low — thresholds only affect *where the shortlist boundary falls*, not the recommended candidate (which clears 3 signals decisively above any plausible top-1%-ish cutoff); the planner/executor may re-tune these constants without changing the conclusion |

**If this table is empty:** N/A — see rows above. All three assumptions are explicitly low-risk / self-correcting via the phase's own operator-confirmation step.

## Open Questions

1. **Exact final wording/format of `.planning/FIXTURES.md`.**
   - What we know: D-08 fixes the location (`.planning/FIXTURES.md`, project root) and required fields (ConvoKit conversation id, case name, docket(s), term, argued date, role). ROADMAP.md's Phase 42/43 sections describe consuming "the confirmed fixture set" and "the fixture set" respectively, without dictating table-vs-prose.
   - What's unclear: whether Phase 43's reset-tool implementation will want machine-parseable fields (e.g., a fenced code block or simple table it can grep/parse) versus prose is fine since a human wires the reseed script by hand.
   - Recommendation: A markdown table (one row per fixture, columns matching D-08's required fields plus a `Role` column) is the safest default — human-readable for the operator-confirmation step, and trivially greppable/parseable if Phase 43's implementer wants light automation. See the Code Examples tables above for the exact shape to reuse.

2. **Should the scoring script's output be captured anywhere durable (e.g., committed alongside FIXTURES.md), or is it truly throwaway?**
   - What we know: `scripts/` precedent (`audit_tenure_seat_identifiers.py`, `migrate_tenure_offices.py`) commits the *script* to git but its *output* is not separately preserved — the script is re-runnable.
   - What's unclear: whether the planner wants the actual ranked-shortlist printout preserved as an artifact (e.g., pasted into `.planning/phases/41.../41-EXECUTION.md` or similar) for audit-trail purposes, given this phase's whole value is "showing the work."
   - Recommendation: Preserve the actual ranked-shortlist output (the top-16 table and the state-fixture candidates) directly in `FIXTURES.md` or an adjacent note — that satisfies success criterion 1 ("a ranked shortlist... is presented") durably, without needing to re-run the 900MB streaming pass to reproduce it later.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3 (stdlib only) | Scoring script | ✓ | 3.14 (system `python3` used this session; project's pinned CLI stack is Python 3.12 per CLAUDE.md) | — |
| `data/corpus/{cases.jsonl,conversations.json,speakers.json,utterances.jsonl}` | All analysis | ✓ | Present, verified this session (7,748 / 7,817 / 9,651 / 1,700,789 rows respectively) | If missing on the executor's machine, the operator must re-copy the gitignored ConvoKit source files per `pipeline/commands/import_convokit.py`'s `_resolve_corpus_dir` error message convention |
| `pipeline/corpus/loader.py` | Reused readers | ✓ | In-repo, unmodified | — |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None currently missing — corpus files were confirmed present and readable this session.

## Validation Architecture

This phase produces a planning document and a throwaway analysis script, not runtime application behavior — there is no unit/integration test surface for `arguments`/`utterances`/API behavior to add here (that's Phase 42/43's job). Validation for THIS phase is checkpoint/manual, matching its "decision-gate" nature.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (project-wide, `pytest.ini` at repo root) — **not exercised by this phase's own deliverable**, since no importer/API/model code changes |
| Config file | `pytest.ini` (existing) |
| Quick run command | N/A for this phase's own script (no pytest suite needed for a throwaway analysis script) |
| Full suite command | `.\.venv\Scripts\python.exe -m pytest` (existing project-wide command, per `.planning/config.json`) — run only to confirm this phase's changes (a new `scripts/*.py` file + a new `.planning/FIXTURES.md`) did not accidentally touch anything under `api/`, `pipeline/`, or `app/` that the suite covers |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CORPUS-12 | Ranked shortlist + recommendation presented, operator confirms 4-fixture set, `.planning/FIXTURES.md` written with required fields, no importer/DB code touched | manual / checkpoint | `git diff --stat` (confirm only `scripts/*.py` + `.planning/FIXTURES.md` changed — nothing under `api/`, `pipeline/`, `alembic/`) | N/A — this is a documentation/checkpoint deliverable, not app code |

### Sampling Rate
- **Per task commit:** `git status` / `git diff --stat` sanity check that no `api/`, `pipeline/commands/`, `pipeline/corpus/`, or `alembic/` file was modified (success criterion 5).
- **Per wave merge:** Same check, plus confirm `.planning/FIXTURES.md` exists at project root (not nested under the phase directory, per D-08) with all 4 fixtures and all required fields present.
- **Phase gate:** Operator's explicit confirmation (or redirect) of the 4-fixture set IS the phase gate (success criterion 3) — there is no automated test that can substitute for this human decision point.

### Wave 0 Gaps
None — no test infrastructure gap exists because this phase adds no testable runtime code. `git diff --stat` and a manual read of `FIXTURES.md` are sufficient and already available.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No auth surface — offline script, operator-run |
| V3 Session Management | No | N/A |
| V4 Access Control | No | N/A — no API/DB write path this phase |
| V5 Input Validation | Marginal | The scoring script takes no untrusted external input — it reads local, operator-supplied ConvoKit files already validated by `import_convokit.py`'s own `_resolve_corpus_dir` existence check; reuse that same fail-fast pattern (clear error, not a bare `FileNotFoundError` traceback) if the script is given a `--corpus-dir` flag |
| V6 Cryptography | No | N/A |

### Known Threat Patterns for this stack
None specific to this phase — it is a read-only, offline, local-file analysis script with no network exposure, no user input beyond an optional local file path, and no persistence beyond a markdown planning doc. The one project-wide constraint that IS directly relevant is **not a security control but a data-governance one**: the apolitical hard exclusion (CLAUDE.md, D-04) — treat it with the same rigor as a security boundary, since violating it (reading `win_side`/`votes`/`scdb_docket_id` even transiently for "just scoring") would be a compliance regression, not merely a style issue. See the multi-docket investigation above for how this was concretely respected.

## Project Constraints (from CLAUDE.md)

- **Apolitical framing is a hard constraint.** Directly governs D-04: the scoring script must build its signals only from `advocate_count` (conversations.json's own `advocates` dict), `distinct_speaker_count`/`bench_speaker_count` (utterances.jsonl's `speaker` field cross-referenced against `speakers.json`'s `type`), `turn_count` (utterances.jsonl row count), and `n_transcripts` (cases.jsonl's allowlisted `transcripts` field) — never `win_side`, `votes`, `votes_detail`, `votes_side`, `win_side_detail`, or `scdb_docket_id`.
- **Pipeline is offline only.** The new scoring script belongs in `scripts/` (matching existing precedent), never exposed as an HTTP endpoint or triggered from the API/frontend.
- **Raw PDFs/corpus files are immutable.** The scoring script must only read `data/corpus/*` — never modify, rewrite, or filter the source files themselves.
- **Alembic is the sole DDL authority.** Not applicable — this phase makes no schema changes (reinforces success criterion 5: no DB rows change).

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CORPUS-12 | A 4-argument fixture set is identified from the ~7,800-argument ConvoKit dataset: one canonical audit fixture selected for structural complexity plus three additional arguments selected for publish/pipeline-state variety — the full set confirmed with the user before use | This document's ranked shortlist (Code Examples), the resolved multi-docket question (Summary point 1-2, full investigation in Code Examples), the 3 proposed state-variety candidates, and the recommended `.planning/FIXTURES.md` shape (Open Questions #1) together give the planner everything needed to build tasks that: (a) implement/adapt the scoring script, (b) present the shortlist + recommendation to the operator for confirmation, (c) write the confirmed set into `.planning/FIXTURES.md` with the required fields |
</phase_requirements>

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Fixture set widened from 1 to 4 arguments: 1 complexity fixture (Phase 42's diff target, unchanged in purpose) + 3 publish/pipeline-state variety fixtures (unpublished/DRAFT, published, mid-pipeline) for Phase 43/45. — **Reversibility:** costly — ROADMAP.md (Phase 41/42/43 goals + success criteria) and REQUIREMENTS.md (CORPUS-12, DEVTOOL-01) were already edited to reflect this during this discussion; reverting means re-editing both docs and re-narrowing three phases' success criteria.
- **D-02:** The 3 state-variety fixtures need no complexity floor — any argument matching the target publish/pipeline state is fine. Chosen for state-transition testing focus, not data complexity (that's what the complexity fixture is for).
- **D-03:** Score/rank candidates for the complexity fixture using a **path-coverage checklist**, not a weighted sum or lexicographic sort — rank by how many distinct importer-stressing paths a single argument covers at once (multi-advocate resolution, high-speaker-count dedup, long-transcript streaming, and — if resolvable, see Claude's Discretion below — multi-docket consolidation), rather than by raw magnitude on any one signal.
- **D-04:** Apolitical scoring boundary is a **hard exclusion rule**: the path-coverage checklist and any scoring must use only structural signals (advocate count, bench speaker count, utterance/turn count, docket/consolidation count) and must never read `win_side`, `votes_side`, `win_side_detail`, `votes_detail`, or any other outcome/SCDB-derived field from `cases.jsonl` — even though they sit in the same JSON record. — **Reversibility:** one-way — this is a direct instantiation of CLAUDE.md's apolitical hard constraint (identical treatment for every speaker, no derived political/outcome insight); relaxing it would violate a project-wide constraint, not just a phase decision.
- **D-05:** Ranked shortlist shows the **top 5** candidates for the complexity fixture (state-variety fixtures aren't ranked — see D-02).
- **D-06:** Each shortlisted candidate shows raw signal numbers (advocate count, speaker count, utterance count) **plus** the path-coverage checklist annotation (which importer paths it covers) — matches the D-03 scoring method so the "why it ranked here" reasoning is visible, not just the numbers.
- **D-07:** The confirmed fixture set is recorded as a **planning doc**, not a checked-in code constant — keeps this phase's "selection and confirmation only" boundary (no code changes) intact. Phase 43 (and any other consumer) reads the doc directly rather than importing a Python constant.
- **D-08:** File location: **`.planning/FIXTURES.md`** at the project root (not nested under the phase directory) — a cross-phase reference that Phase 42, 43, and 45 need to find without knowing Phase 41's directory name. Must record, per fixture: ConvoKit conversation id, case name, docket(s), term, argued date, and its role (complexity fixture, or which state variant).

### Claude's Discretion

- **Multi-docket consolidation signal is unresolved — needs one more research pass.** During this discussion, a naive check found 0 cases with comma-separated `docket_no` values and 0 conversations joined to more than one `cases.jsonl` row via `transcripts[].id`. `pipeline/commands/import_convokit.py`'s own module docstring notes the case/conversation join is done on `raw_case["id"] == conversation["case_id"]`, not on `docket_no` (which recycles across terms) — so a docket_no-format check was probably the wrong approach. Before dropping the multi-docket signal from the path-coverage checklist (D-03), the researcher should check `scdb_docket_id` and case-title patterns for a cleaner consolidation signal. If nothing surfaces, proceed with a 3-signal checklist (advocate count, speaker count, utterance count) — this is an acceptable fallback per D-03's intent, not a blocker.
  - **RESOLVED THIS SESSION:** see Summary points 1-2 and the full "multi-docket investigation" in Code Examples. `scdb_docket_id` grouping DOES surface a clean signal (10 real consolidation groups) but is an explicitly forbidden field (D-04, `apolitical.py`'s `FORBIDDEN_FIELDS`) — cannot be used regardless of how clean it looks. A second, allowed signal (`transcripts[].name` embedding a companion case) was also found and confirmed compliant, but investigation showed the importer has no multi-docket-consolidation code path at all (D-19, lead-docket-only) — so neither signal would exercise any additional importer behavior. Recommendation: **drop multi-docket entirely**, and substitute the allowed, importer-relevant **re-argument / transcript-count signal** (which does exercise real importer code, per Summary point 2) as the 4th checklist dimension in its place, rather than falling all the way back to the bare 3-signal checklist.
- Exact wording/format of the `.planning/FIXTURES.md` doc (table vs. prose per fixture) is left to planning — D-08 only fixes location and required fields. See Open Questions #1 for this researcher's recommendation (markdown table).

### Deferred Ideas (OUT OF SCOPE)

- **Rename "Case" to "Argument" across DB schema, API routes (`/cases/`), and frontend.** Raised during this discussion as a valid observation (the product is arguments-only, "case" language is a holdover), but it's a cross-cutting rename spanning the DB model, routes, and corpus-loader naming — genuinely its own phase or milestone, not part of fixture selection. Logged in `.planning/REQUIREMENTS.md` Out of Scope and `.planning/STATE.md` Roadmap Evolution; not actioned this milestone.
</user_constraints>

## Sources

### Primary (HIGH confidence — verified by direct execution against the real corpus this session)
- `data/corpus/cases.jsonl` (7,748 rows) — loaded and scanned in full this session
- `data/corpus/conversations.json` (7,817 conversations) — loaded and scanned in full this session
- `data/corpus/speakers.json` (9,651 speakers) — loaded and scanned in full this session
- `data/corpus/utterances.jsonl` (1,700,789 rows, 900MB) — streamed in full this session (one pass, ~9m37s wall clock)
- `pipeline/corpus/loader.py` — read in full; every function's docstring cross-checked against actual file shapes this session
- `pipeline/corpus/apolitical.py` — read in full; `FORBIDDEN_FIELDS` frozenset confirmed to include `scdb_docket_id`
- `pipeline/commands/import_convokit.py` — read in full; `_get_or_create_case`'s "Lead-docket-only (D-19)" docstring, `_next_question_number`, `_parse_argued_date`, `_import_conversation`'s `advocates = conversation.get("advocates")` line all directly informed the path-coverage signal choices
- `api/models/models.py` — read in full; `ArgumentStatusEnum` (PIPELINE/DRAFT/PUBLISHED/UNPUBLISHED), `Argument.published_at`/`resolved_at`, `CaseArgument`/`Argument.source_dockets` (confirms DB-side consolidation support exists but is unused by the ConvoKit import path)
- `api/services/admin_arguments.py`, `api/services/admin_jobs.py` — read (excerpts) to confirm publish/pipeline state is exclusively DB/service-side, never corpus-side
- `scripts/audit_tenure_seat_identifiers.py` — read in full as the `scripts/` directory precedent for a throwaway audit script's shape/conventions
- `.planning/ROADMAP.md` §Phase 41/42/43 — read in full for exact success-criteria wording and FIXTURES.md consumption description
- `.planning/REQUIREMENTS.md`, `.planning/STATE.md`, `.planning/phases/41-canonical-corpus-fixture-selection/41-CONTEXT.md` — read in full (upstream inputs to this research)
- `CLAUDE.md` — read in full for the apolitical hard constraint and pipeline-offline-only rule
- `pytest.ini`, `.planning/config.json`, `tests/conftest.py` — read to confirm test-infra shape and that `nyquist_validation` is enabled

### Secondary (MEDIUM confidence)
None used — every quantitative claim in this document was verified directly against the real corpus files rather than sourced from external documentation or web search (this phase's domain is entirely internal/first-party data, so no external library or API research was needed).

### Tertiary (LOW confidence)
None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependency; 100% reuse of existing, already-tested `pipeline/corpus/loader.py`.
- Architecture: HIGH — the scoring script's shape is dictated directly by CONTEXT.md D-03/D-05/D-06 and verified against the real data this session.
- Pitfalls: HIGH — every pitfall listed was either directly observed while writing/running the analysis scripts this session, or is drawn verbatim from `import_convokit.py`'s own documented gap-closures (docket_no recycling, per-transcript date matching).
- Multi-docket resolution: HIGH — resolved with concrete evidence (10 real `scdb_docket_id` groups found, cross-checked against `conversations.json`'s `case_id` field for the `1957_103` example, and cross-checked against `import_convokit.py`'s explicit "lead-docket-only" docstring).

**Research date:** 2026-07-29
**Valid until:** Indefinite for the qualitative findings (apolitical constraint, importer's lead-docket-only design, loader function shapes) — these are structural, not time-sensitive. The exact quantitative shortlist (Code Examples tables) is valid as long as `data/corpus/*` is unchanged; if the operator later drops in an updated ConvoKit corpus snapshot, re-run the scoring script rather than trusting these numbers.
