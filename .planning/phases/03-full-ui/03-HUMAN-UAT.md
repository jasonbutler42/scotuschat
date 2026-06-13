---
status: partial
phase: 03-full-ui
source: [03-VERIFICATION.md]
started: 2026-06-12
updated: 2026-06-12
---

## Current Test

[awaiting human testing]

## Tests

### 1. Case list page visual render
expected: Navigate to /cases; cards render with case name, docket number, and argued date. Empty state shows "No cases loaded" when no cases are ingested.
result: [pending]

### 2. Single-argument case navigation
expected: Click a case card from /cases; navigate through /cases/{slug} with a 307 redirect directly to /cases/{slug}/arguments/{id} — no intermediate page visible to the user.
result: [pending]

### 3. SSR on hard refresh
expected: Direct-load /cases/{slug}/arguments/{id} via hard refresh (or curl); full HTML including case name and utterances is in the initial response — not hydration-only JavaScript.
result: [pending]

### 4. SectionRail scroll-spy
expected: Scroll through an argument with multiple sections; the active section button in the left rail gains a #93c5fd left border and weight 600 as utterances enter the IntersectionObserver visibility zone.
result: [pending]

### 5. Mobile breakpoint
expected: At viewport width < 768px, the left nav rail (.nav-rail) is hidden and the chat column spans the full viewport width.
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
