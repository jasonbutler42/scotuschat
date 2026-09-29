---
status: testing
phase: 53-undetermined-speakers-marker-normalisation
source: [53-VERIFICATION.md]
started: 2026-09-29T15:48:26Z
updated: 2026-09-29T15:48:26Z
---

## Current Test

number: 1
name: Treatment D at rest — visual read-check against Figma node 33:2 (fixture 15169), desktop and 390px
expected: |
  Treatment D reads noticeably narrower with reserved empty space on both rails; the "undetermined speaker" label reads as visibly different (italic, muted) from a real speaker name; a whole-turn (Inaudible) body reads as a transcriber's note rather than spoken words. Matches the approved mockup.
awaiting: user response

## Tests

### 1. Treatment D at rest — visual read-check against Figma node 33:2 (fixture 15169), desktop and 390px
expected: Treatment D reads noticeably narrower with reserved empty space on both rails; the "undetermined speaker" label reads as visibly different (italic, muted) from a real speaker name; a whole-turn (Inaudible) body reads as a transcriber's note rather than spoken words. Matches the approved mockup.
result: [pending]

### 2. Explanation card — visual and device fidelity against Figma node 33:62, desktop and a real touch device
expected: Card matches the approved mockup's spacing and divider placement; rest/hover/tap states behave correctly on an actual touch device; the D-15 first-paragraph swap reads correctly for a real inaudible-marker turn.
result: [pending]

### 3. Live admin round-trip — majority-undetermined blocker sentence and override publish
expected: All three admin surfaces (argument detail, arguments list, review queue) show the identical sentence, e.g. "68% of turns have an undetermined speaker (more than half)."; the existing typed-reason override still publishes one argument at a time, with no new gate or bulk shortcut.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
