---
phase: 41-canonical-corpus-fixture-selection
reviewed: 2026-07-29T00:00:00Z
depth: standard
files_reviewed: 1
files_reviewed_list:
  - scripts/select_corpus_fixtures.py
findings:
  critical: 0
  warning: 6
  info: 0
  total: 6
status: issues_found
---

# Phase 41: Code Review Report

**Reviewed:** 2026-07-29T00:00:00Z
**Depth:** standard
**Files Reviewed:** 1
**Status:** issues_found

## Summary

Reviewed `scripts/select_corpus_fixtures.py`, an offline read-only path-coverage scoring script over the local ConvoKit corpus. The apolitical-extraction containment (D-04) is well-implemented for `cases.jsonl`/`conversations.json` reads and is exercised by a self-check harness; the total-order ranking logic (D-03) is correct and its tie-breaking is verified against synthetic fixtures with a matching expected order. I traced the ranking math, the self-check assertions, and cross-checked the reproduced `_parse_argued_date`/speaker-classification logic against its stated source of truth (`pipeline/commands/import_convokit.py`) — the constants and transcript-selection rule match exactly.

No critical/security defects were found: the script never persists or prints a `FORBIDDEN_FIELDS` name in any real code path, and file I/O is scoped to the documented corpus directory and an explicit `--cache`/`--cache-out` path.

However, several robustness and correctness gaps exist around cache handling, CLI input validation, and the speaker-classification default, all of which could silently produce a wrong or confusing result rather than a clear failure. These are detailed below as warnings.

## Warnings

### WR-01: Missing/unrecognized speaker id is silently counted as a "real" distinct speaker

**File:** `scripts/select_corpus_fixtures.py:213-222`
**Issue:** In `_stream_signals`, `speaker_id = row.get("speaker")` may be `None` (row lacks a `speaker` field) or may reference an id absent from `speakers.json`. In both cases `speaker_meta = speakers.get(speaker_id) or {}` yields `{}`, so `speaker_type` becomes `""`. Since `""` is not a member of `UNATTRIBUTED_TYPE_VALUES = {"u", "unattributed", "unknown"}`, the code takes the `if speaker_type not in UNATTRIBUTED_TYPE_VALUES:` branch and adds the (possibly `None`) speaker id to `speaker_sets`, inflating `distinct_speaker_count` and therefore `coverage`/`magnitude_sum` for that conversation. This inverts the intended "safe default": an unknown/missing speaker reference should not silently count as a legitimate, dedup-worthy speaker.
**Fix:**
```python
speaker_meta = speakers.get(speaker_id)
if speaker_id is None or speaker_meta is None:
    continue  # or: treat as unattributed
speaker_type = str(speaker_meta.get("type") or "").strip().lower()
if speaker_type not in UNATTRIBUTED_TYPE_VALUES:
    speaker_sets.setdefault(cid, set()).add(speaker_id)
```

### WR-02: `--cache-out` is silently ignored when `--cache` is also passed

**File:** `scripts/select_corpus_fixtures.py:816-830`
**Issue:** In `main()`, the `if args.cache: ... else: ... if args.cache_out: _write_cache(...)` structure means that when both `--cache` and `--cache-out` are supplied on the same invocation, no streaming happens and `_write_cache` is never called — `--cache-out` is dropped without any warning. An operator who passes both flags (e.g. re-ranking from a cache while intending to also refresh/round-trip it) will get no error and no new cache file, and may not notice.
**Fix:** Either treat the combination as invalid (`argparse` mutual exclusivity or an explicit `ERROR:` message) or write the loaded `cache_payload["aggregates"]` back out to `--cache-out` for round-tripping:
```python
if args.cache and args.cache_out:
    print("ERROR: --cache and --cache-out are mutually exclusive.", file=sys.stderr)
    return 1
```

### WR-03: Cache `complete` flag reflects whether `--max-utterance-rows` was *passed*, not whether the scan was actually truncated

**File:** `scripts/select_corpus_fixtures.py:823-830` (write side), `scripts/select_corpus_fixtures.py:510-527` (`_write_cache`)
**Issue:** `complete=(args.max_utterance_rows is None)` marks a cache incomplete any time `--max-utterance-rows` was supplied, even if the supplied bound was never actually reached (e.g. `--max-utterance-rows 999999999` on a corpus with fewer matching rows). `_stream_signals` never reports back whether the loop actually broke early via the `max_rows` bound vs. exhausting the generator naturally. This means a fully-complete scan can be mislabeled `complete: false`, forcing later `--cache` reads to require `--allow-partial` even though the data is not actually partial.
**Fix:** Have `_stream_signals` return (or set) an explicit "was truncated" flag based on whether the loop hit `break` due to `max_rows`, rather than deriving `complete` solely from whether the CLI arg was set:
```python
def _stream_signals(...) -> tuple[dict[str, dict], bool]:
    truncated = False
    ...
    if max_rows is not None and i >= max_rows:
        truncated = True
        break
    return aggregates, not truncated
```

### WR-04: No cross-check that a `--cache` file's conversation ids match the current run's `conversations.json`

**File:** `scripts/select_corpus_fixtures.py:816-818`, `scripts/select_corpus_fixtures.py:271-276`
**Issue:** When `--cache` is supplied, `signals = cache_payload["aggregates"]` is used as-is with no validation that its keys correspond to `wanted_ids = set(conversations.keys())` from the currently-loaded `conversations.json`. `_conversation_rows` silently defaults any missing id's signals to all-zero (`signals.get(cid) or {...zero defaults...}`). A stale cache (e.g. generated against an older corpus snapshot, or a different `--corpus-dir`) will silently zero out turn/speaker counts for some or all conversations rather than erroring, producing a misleading ranking/recommendation with no indication anything is wrong.
**Fix:** After loading, compare `set(signals) ` against `wanted_ids` and print a warning (or fail per `--allow-partial` semantics) when there's a meaningful mismatch:
```python
missing = wanted_ids - set(signals)
if missing:
    print(f"WARNING: --cache is missing {len(missing)} conversation id(s) present in "
          f"conversations.json; their signals will be treated as zero.", file=sys.stderr)
```

### WR-05: `--top` accepts negative values, producing a confusing silent truncation instead of an error

**File:** `scripts/select_corpus_fixtures.py:136-141`, `scripts/select_corpus_fixtures.py:349`
**Issue:** `--top` is declared as a plain `type=int` with no range validation. `_rank_candidates` uses `annotated[:top]`, so `--top -1` returns every ranked row except the last one (Python negative-slice semantics) instead of erroring — silently producing a nonsensical shortlist rather than surfacing the invalid input.
**Fix:**
```python
if args.top < 0:
    print(f"ERROR: --top must be >= 0, got {args.top}.", file=sys.stderr)
    return 1
```

### WR-06: Malformed-but-versioned cache file (missing `aggregates` key) crashes with a raw traceback instead of the script's own friendly error style

**File:** `scripts/select_corpus_fixtures.py:816-818`, `scripts/select_corpus_fixtures.py:529-565`
**Issue:** `_read_cache` validates `schema_version` and `complete`, but never validates that the `"aggregates"` key exists in the loaded JSON payload. If a cache file has a matching `schema_version` but a missing/renamed `aggregates` key (e.g. hand-edited, or written by a future/buggy version of this script), `cache_payload["aggregates"]` in `main()` raises an uncaught `KeyError`, which is not one of the caught exception types (`FileNotFoundError, OSError, ValueError`). The process still exits non-zero, but with a raw Python traceback rather than the documented `ERROR: ...` message style used everywhere else in this script.
**Fix:** Validate the payload shape inside `_read_cache` and raise `ValueError` (which is already caught) on a missing/malformed `aggregates` key:
```python
if "aggregates" not in payload or not isinstance(payload["aggregates"], dict):
    raise ValueError(f"--cache file {cache_path} is missing a valid 'aggregates' object.")
```

---

_Reviewed: 2026-07-29T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
