---
created: 2026-08-14T00:00:00.000Z
title: Revisit removal of the retired pre-relocation checkout after a period of running from the new location
area: dev-environment
priority: low
files:
  - .planning/phases/46-dev-environment-reliability/46-RELOCATION.md
---

## Problem

Phase 46 Plan 06 Task 2 decided (option-c: "leave it in place, marked as
retired") to retain the pre-relocation checkout at
`/mnt/c/workspace/scotuschat/project` (9p/DrvFs Windows-mounted filesystem)
rather than deleting it or pushing-then-deleting, now that the relocated
repository at `/home/jason/scotuschat/project` (native ext4) has been fully
proved working end to end (plans 46-04 and 46-05).

The checkout was left in place because it is the only offline second copy of
217+ commits not yet pushed to `origin`, and of the untracked payload
(`.env`, `app/.env`, `data/corpus`, `data/pdfs`, `data/uploads`) that is not
recoverable from git if the surviving copy is ever damaged. A plain-text
marker file (`RETIRED-CHECKOUT.txt`, untracked) was written at its root
naming the current repository path and stating plainly that it must not be
committed into.

## Why this is a real risk, not just tidiness

Two live checkouts of `main` continue to coexist. The marker is advisory
only — a stray shell, editor window, or scheduled task that still opens the
old path could still commit into it, silently forking history in a way that
is expensive to notice late. The stale copy will also drift further from the
live one over time as normal development continues at the new location,
making an accidental commit there increasingly misleading rather than
merely redundant. The retired in-repository PostgreSQL directories
(`data/pgsql`, `data/pgdata`) also survive on disk at the old checkout
(though `.gitignore`'d, so this doesn't affect tracked history).

## Suggested next step

After running from `/home/jason/scotuschat/project` for a period (the
operator's own judgment on how long is "long enough" — e.g. several weeks of
normal development with no incidents), revisit this decision:

1. Confirm the 217+ commits (or however many now exist) are either pushed to
   `origin`, or still deliberately unpushed for a documented reason.
2. If comfortable, delete `/mnt/c/workspace/scotuschat/project` entirely
   (one-way — it is on a Windows-mounted drive, so a WSL removal does not go
   to a recycle bin) — or push to `origin` first, then delete (option-b from
   the original Phase 46 Plan 06 Task 2 decision).
3. Confirm afterward that the surviving repository at
   `/home/jason/scotuschat/project` is unaffected: `git fsck --no-dangling`
   clean, `git status --porcelain -uno` empty, HEAD unmoved.

Not blocking any current work — filed per Phase 46 Plan 06 Task 2's own
resume-signal instruction ("Option-c skips the removal in Task 3 and files a
follow-up todo to revisit after a period of running from the new
location").
