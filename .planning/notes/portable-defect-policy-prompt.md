# Portable prompt — defect policy + tooling ratio

Paste into another Claude Code project. Adjust the paths/framing in the last
paragraph if that project doesn't use CLAUDE.md.

---

I'm the sole developer and sole reviewer on this project. There is no hand-off,
no second reviewer, and no auditor. I'm a UX practitioner by trade — I'm here for
the product decisions, and I'm expecting you to handle the engineering so I don't
have to context-switch into it.

Add the following two policies to CLAUDE.md, then follow them for the rest of this
project. They override your default checkpoint and confirmation instincts, and they
override any workflow tooling that wants to route defects to me for approval.

## Defect Policy

The line is: **is the correct behavior already determined, or does it need my taste?**

### Yours, always — fix it, don't ask

Anything where what should happen is already settled and only the implementation is
in question. Fix it where you find it, commit it, report it in one line. No
questions, no checkpoints, no options tables, no UAT items.

- Race conditions, transaction boundaries, lock ordering, concurrency
- Idempotency, replay, retry, double-submit semantics
- FK cascades, orphan rows, constraint violations, NULL handling
- Failing tests — a red test is a bug report, not a decision request
- Stale-state and reactivity bugs, cache invalidation
- Off-by-one, ordering, sort stability, pagination
- Error handling, fail-closed defaults, input validation
- Anything contradicting a constraint or locked decision already written down

The correct amount of attention for me to spend on the above is approximately zero.
Bringing one of these to me as a question is itself a defect in how the work is
being done.

### Mine — ask before deciding

Anything where what should happen is a product, design, or domain judgment.

- What a screen shows, in what order, with what words
- Whether a state is reachable at all
- Whether a condition blocks an action or merely flags it
- Domain semantics and the right granularity for a rule
- Scope: whether a newly discovered requirement belongs in this unit of work,
  a later one, or the backlog
- Anything that would make previously-approved visual work look different

### Test for the line

If the answer lives in a spec, a locked decision, or a correctness argument, it's
yours. If it needs my taste, it's mine. When genuinely ambiguous: do everything that
doesn't depend on the answer first, then ask me one precise question.

### Reporting

One line per fixed defect: what broke, what fixed it, which test proves it. Don't
narrate the investigation, don't enumerate alternatives you rejected, don't preserve
deviation archaeology for a reader who does not exist.

## Testing Policy

- **Hard ceiling: total tooling/test lines must never exceed 2:1 against production
  lines.** Not a smell threshold — a rule. If a change would push the ratio over 2:1,
  the change isn't done until something retires. Report the ratio whenever you add a
  meaningful number of tests.
- **No static source-text contract tests for frontend behavior.** Asserting that a
  string appears in a component file proves a declaration is present and proves
  nothing about the rendered page. A suite full of these goes green against a
  completely broken UI. Frontend behavior is verified by my eye or by a real browser
  driver, or it is not verified — don't manufacture the appearance of coverage.
  - Narrow exception: a *structural ban* sweep, proving a forbidden identifier
    reaches no public surface. Absence across a computed file set is one of the few
    things source text can actually prove.
- **Tests retire with the behavior they pinned.** When work supersedes behavior,
  delete that behavior's tests in the same commit. A test asserting a superseded
  contract is worse than no test: it still costs maintenance and it lies about
  coverage.
- **Name test modules after the unit under test**, never after the phase, ticket, or
  plan that added them. Phase-numbered test files are how a suite accretes modules
  nobody can later evaluate for relevance.
- **Prefer few real tests to many shallow ones.** A test that exercises the actual
  database, the actual service, or the actual rule is worth twenty that assert a
  declaration exists.

Once both policies are in CLAUDE.md, measure the current test-to-production line
ratio and tell me where it stands. If it's over 2:1, propose a specific deletion
list — files and line counts — before deleting anything.
