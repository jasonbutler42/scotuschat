completed: 2026-08-21
---
created: 2026-08-19T00:00:00.000Z
title: Unpublishing an argument does not hide it from /cases or direct view
area: api
severity: major
files:

  - api/services/admin_arguments.py (unpublish_argument, ~line 777)
  - api/services/cases.py (line 34)
  - api/services/arguments.py (line 50)

---

## Problem

Found live during Phase 48-08 checkpoint testing (2026-08-19) by the operator.
Unpublishing an argument in the admin UI reports success, flips the status
badge to UNPUBLISHED, and writes the audit log row — but the argument remains
listed on `/cases` and remains directly viewable by URL. Unpublish does not
unpublish.

**Root cause: two different sources of truth for "is this public?"**

`unpublish_argument` (`api/services/admin_arguments.py:802-808`) sets
`status = UNPUBLISHED` and *deliberately* leaves `published_at` unchanged. That
is documented and intentional — the docstring cites D-02, so the Status card
can still show the argument's most recent publish date:

    published_at is intentionally LEFT UNCHANGED (D-02) so the Status card can
    still show the argument's most recent publish date.

But both public read paths gate on `published_at`, not on `status`:

- `api/services/cases.py:34` — `.where(Argument.published_at.isnot(None))`
- `api/services/arguments.py:50` — `.where(Argument.published_at.isnot(None))`

So an unpublished argument still satisfies the public filter. Each half is
individually reasonable; together they mean the UNPUBLISHED state has no
effect on public visibility at all.

This is a content-visibility correctness bug on a public site, not a cosmetic
one: the operator's only "take this down" control does not take anything down.

## Fix options

1. **Filter the public queries on `status` instead of `published_at`** (or on
   both). Preserves the D-02 audit date, single-line change per query. Safer,
   and preferred — `status` is the explicit lifecycle enum and is already what
   every admin guard keys on since Phase 48-04.

2. Clear `published_at` on unpublish and store the last-published date in a
   separate column. Larger change; requires a migration; loses nothing but
   costs more.

Whichever is chosen, add a regression test asserting an UNPUBLISHED argument
is absent from `/cases` **and** 404s (or is otherwise not served) on direct
fetch. There is currently no test covering this, which is why the invariant
drifted.

## Not previously captured

Checked `.planning/WINDOWS.md`, `.planning/todos/`, `.planning/debug/`, and
`ROADMAP.md` — no existing entry. The `# hide unpublished arguments (BUG-01/D-02)`
comment in `arguments.py:50` refers to the *original* filter being added, not to
this interaction with the unpublish path.

---

## Resolution (2026-08-21)

Closed by **Phase 48 plan 10 (Defect 2)**, verified at 48-UAT.md test 65 (48-10 D3).

Root cause was as diagnosed: `unpublish_argument` deliberately retains `published_at`
(D-02, so the Status card can still show the last publish date), so `published_at`
alone stopped distinguishing PUBLISHED from UNPUBLISHED. The fix adds a
`status == ArgumentStatusEnum.PUBLISHED` predicate **in addition to** the existing
`published_at IS NOT NULL` gate — never in place of it — across all three public
read paths:

- `api/services/cases.py:41` (`get_cases`)
- `api/services/arguments.py:65` (`get_argument_with_utterances`)
- `api/services/speakers.py:154` (`get_argument_speakers`)

`api/tests/test_published_gate.py` pins both predicates by exact substring, and
`api/tests/test_phase48_unpublish_visibility.py` covers the behavior.

Marked complete during Phase 48 close-out; the todo had gone stale in `pending/`.
