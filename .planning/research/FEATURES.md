# Feature Landscape

**Domain:** Legal transcript reader / Supreme Court oral argument viewer
**Researched:** 2026-06-11
**Primary competitor analyzed:** Oyez.org (oyez.org)

---

## Oyez.org Competitive Analysis

Oyez is the primary product to differentiate from. Understanding its strengths and gaps directly
shapes what this project must match, exceed, or deliberately leave out.

### What Oyez Does Well

| Capability | Detail |
|------------|--------|
| Audio + transcript sync | Audio aligned to sentence-level segments; click any paragraph to jump the audio playhead |
| Speaker identification | Per-utterance speaker labels (retroactively applied back to 1955 for pre-2004 transcripts that originally used "The Court" for all justices) |
| Justice biographies | Biographical sketches for current and historical justices |
| Advocate profiles | Information on attorneys who have argued before the Court |
| Case summaries | Plain-English case abstracts alongside the transcript |
| Audio download | MP3 download and streaming for 5,000+ hours of oral arguments |
| Case browsing | Cases browseable by term; sort by name or chronology |
| Subject-area filtering | Cases filterable by issue/topic area |
| Mobile app (iOS/Android) | Synchronized audio + transcript on mobile; streaming or offline download |
| Scale | 8,300+ oral argument transcripts; 1,800,000+ utterances in corpus |

### What Oyez Does Not Do Well (gaps this project can exploit)

| Gap | Impact |
|-----|--------|
| Transcript is displayed as a dense text wall, not a conversation | Hard to follow rapid turn-taking among multiple justices |
| No visual differentiation between Bench and advocates | Reader must track speaker names manually in a dense block |
| No avatar/photo treatment that makes the speaker feel present | Justices and advocates are names in text only |
| Stage directions (laughter, pause) are buried inline in parentheses | No semantic differentiation from spoken content |
| Justice bio depth varies; not guaranteed uniform schema | Inconsistent experience across justices and historical figures |
| No structured rendering of argument structure (rebuttal time, amicus) | Loses the procedural shape of the argument |
| Not optimized for non-lawyers — assumes legal literacy | Barrier for civic education and general public use |

---

## Table Stakes

Features users expect from any legal transcript viewer. Absence signals the product is incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Per-utterance speaker attribution | Every competing tool labels who is speaking | Low | Oyez, CourtListener, and supremecourt.gov PDFs all provide this |
| Case title and docket number displayed | Standard metadata on every legal resource | Low | Must appear on case landing page |
| Argument date and term year | Required to place argument in historical context | Low | Pairs with case title |
| Browseable case list | Users need a way to find arguments without knowing exact case name | Low | By term, at minimum |
| Readable transcript with clear speaker labels | Core function — the raw text must be comprehensible | Low | Even plain PDF provides this; must meet or exceed |
| Mobile-responsive layout | Majority of incidental users will be on phones | Medium | Chat-style layout naturally adapts; test wrapping for long utterances |
| Stable, shareable URLs per case and per argument | Users copy links to share arguments; permalinks are expected | Low | `/cases/{slug}` pattern; must work on refresh |
| Stage direction / parenthetical rendering | Oyez transcripts include them; dropping them loses fidelity | Low | Distinct visual treatment, not deletion |
| Open Graph / social preview metadata | When shared to social or messaging, unfurled preview should show case name, date, and a useful description | Low | `<meta>` tags; no backend required |
| Accessible color contrast and readable type | WCAG 2.1 AA minimum — legal content has a high proportion of users with disabilities | Low-Medium | 4.5:1 contrast ratio; sufficient font size for dense text |
| Keyboard navigation | Transcript should be fully navigable without a mouse | Low | Particularly important for power users and AT users |

---

## Differentiators

Features that set this product apart from Oyez and every flat PDF viewer. Not expected baseline — but
valued and sticky when present.

| Feature | Value Proposition | Complexity | Dependencies |
|---------|-------------------|------------|--------------|
| Chat-style two-sided layout | Turn-taking is instantly visually obvious; Bench on one side, advocates on the other; matches how people already read conversations | Medium | Speaker resolution must be complete before render; requires a "side" attribute per speaker role |
| Speaker avatars with consistent sizing | Gives each voice a face; makes the Court feel like people not institutions | Low-Medium | Photo sourcing from Oyez API / FJC; fallback initials avatar when no photo available |
| Uniform bio schema for every speaker | Every justice and advocate has identical fields — no one gets more or less editorial treatment | Medium | Enrichment pipeline step; data from FJC + supremecourt.gov + Oyez API |
| Stage directions rendered as a distinct component | "(Laughter.)" and "(Pause.)" rendered as a centered, muted annotation between bubbles — not inside a speech bubble | Low | Parser must classify utterance type: speech vs. stage direction |
| Argument-level navigation (sections) | Oral arguments have a defined structure: Petitioner → Respondent → Rebuttal → Amicus. A navigation rail lets users jump to each speaker's block | Medium | Requires argument-section tagging; depends on transcript structure being consistent enough to auto-detect |
| Speaker role indicators | "Chief Justice", "Associate Justice", "Counsel for Petitioner" badges on bio cards so users know the structural role of each speaker without background | Low | Role data from speaker resolution step |
| Citation callouts | Raw legal citations surfaced inline as styled text; future-ready for hyperlinking to resolved cases | Low | Pipeline already captures citations; frontend renders them with distinct visual style |
| Re-argument awareness | When a case was re-argued, both argument sessions are accessible and clearly labeled as distinct events | Low | Schema already supports this; frontend must expose it |
| Responsive chat bubbles with sane max-width | Long utterances wrap gracefully without becoming a wall of text; max-width ~65ch maintains readability | Low | Pure CSS; apply prose width constraint to bubble content |
| Argument-at-a-glance header | Case name, docket, argued date, decided date (if available), and a speaker roster before the transcript begins | Low | Assembles from existing data fields; no new pipeline work |

---

## Anti-Features

Things to deliberately NOT build. Each anti-feature has a specific reason tied to the project's
apolitical constraint, scope discipline, or technical risk.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| AI-generated case summaries | Any LLM summary of a constitutional case will reflect the framing choices of the model, which cannot be uniformly neutral; users cannot verify what was omitted or reframed | Display only the raw transcript and structured metadata; let users draw their own conclusions |
| "What this case means" editorial annotations | Adding interpretation is editorializing even when intended as neutral — every framing choice implies a stance | Link to external resources (Oyez, SCOTUSblog) for analysis; never produce it in-house |
| Predicted/likely outcome indicators | Inferring how justices will vote from oral argument questions is common academic practice but inherently editorial and often wrong | Do not surface question counts, interruption metrics, or sentiment signals as predictive features |
| Justice sentiment or tone analysis | Labeling a justice's tone as "skeptical," "hostile," or "sympathetic" introduces political interpretation | Render the verbatim text; let users read tone themselves |
| Topic / subject tagging | Tagging a case as "abortion," "gun rights," or "voting rights" immediately creates politically charged filter hierarchies; flagged as deferred in PROJECT.md for this reason | Defer; if implemented later, use neutral procedural categories (First Amendment, Commerce Clause) sourced from official Court classification, not editorial assignment |
| User accounts and social features | Not in scope; adds auth complexity, moderation surface, and content liability | Keep the product read-only; no comments, ratings, or contributions |
| Cross-case analysis / justice statistics | "Justice X asks the most questions" or "Justice Y interrupts most" produces statistical artifacts that will be shared out of context and interpreted politically | Defer cross-case queries; schema supports it for future; do not surface aggregate stats in initial product |
| Notifications / email alerts | CourtListener offers this; it is a power-user workflow feature adding backend complexity for marginal MVP value | Defer; users can bookmark and return |
| Audio playback | Requires licensing clarity (audio belongs to the Court; Oyez has an established relationship); adds significant frontend complexity; Oyez already serves this well | Link to the Oyez argument page for audio; do not duplicate |
| PDF download / export | Transforms the viewer into a document tool; adds scope; PDFs are already on supremecourt.gov | Link to the official PDF source; do not re-host or generate |
| Full-text search across all cases | High infrastructure cost; CourtListener and Oyez already do this well; not differentiating for MVP | Provide within-argument text search (browser CTRL+F is sufficient for MVP); defer cross-case search |
| Advocate win/loss records | Framing an advocate as "X wins, Y loses" encourages users to evaluate lawyers rather than arguments; adds editorial interpretation | Display advocate name, bar status, and role in this argument only |
| Dark patterns in sharing | Pre-populated social sharing text that frames the case | Share raw URL only; let the user write their own post |

---

## Feature Dependencies

Understanding which features must exist before others can be built:

```
Speaker resolution (pipeline) → Chat layout (cannot assign "side" without knowing role)
Speaker resolution (pipeline) → Avatars (cannot display photo without resolved person record)
Speaker resolution (pipeline) → Bio cards (no bio without person record)
Utterance classification (speech vs. stage direction) → Stage direction rendering
Citation extraction (pipeline) → Citation callout styling (frontend)
Argument section detection → Section navigation rail
Case metadata (case, argument records) → Argument-at-a-glance header
Stable URL scheme → Open Graph / social previews
All of the above → Full chat view
```

The pipeline is the foundation. No frontend differentiator works without complete, resolved speaker
data. This means the pipeline must be the first working piece, even if the frontend starts simple.

---

## MVP Feature Set Recommendation

### Must Have at Launch (Proof of Concept)

1. Case list page — browseable list of hand-picked arguments by term/case name
2. Chat view — two-sided layout, speaker avatars with initials fallback, speaker name + role label
3. Stage direction rendering — visually distinct from speech bubbles
4. Bio card — consistent schema for every speaker (name, role, tenure dates, appointing president for justices; bar status for advocates) — no editorializing
5. Argument header — case name, docket, date argued, speaker roster
6. Citation display — raw citation text styled distinctly (not linked, not resolved)
7. Stable URLs — `/cases/{slug}/arguments/{id}` pattern
8. Open Graph metadata — case name + date in unfurl preview
9. Mobile-responsive layout — chat bubbles stack cleanly on 375px viewport
10. Keyboard navigable

### Defer to Later Phase

| Feature | Reason to Defer |
|---------|-----------------|
| Argument section navigation rail | Requires reliable section detection; can add without schema change |
| Re-argument multi-session UI | Schema ready; display logic simple; low urgency for MVP |
| Within-argument text search | Browser search sufficient for MVP; proper implementation can be Phase 2 |
| Full case list with term filter | Start with a curated set; browsing at scale comes later |
| Photo enrichment for all advocates | Justice photos available; advocate photos less consistently available |

---

## Accessibility Notes

| Concern | Requirement | Rationale |
|---------|-------------|-----------|
| Color contrast | WCAG 2.1 AA (4.5:1 minimum for body text) | Dense legal text + sustained reading sessions require high contrast |
| Font size | 16px minimum body; no sub-12px UI text | Long-form reading use case; users include older adults and legal professionals reading for detail |
| Speaker differentiation | Do NOT rely solely on color to distinguish Bench vs. advocate side | Color blindness; layout position (left/right) must carry the primary meaning |
| Screen reader support | Speaker name must be in the DOM before the utterance text, not just shown via avatar | AT users need the "who" before the "what" |
| Touch targets | 44×44px minimum tap targets for any interactive element (bio card links, navigation) | WCAG 2.5.5; mobile users with motor impairments |
| Reduced motion | Bio card hover animations and any scroll transitions must respect `prefers-reduced-motion` | Vestibular disorders |
| Focus management | If bio card opens as a modal/overlay, focus must trap inside and return to trigger on close | Keyboard and AT users |

---

## Sources

- Oyez Project Wikipedia: https://en.wikipedia.org/wiki/Oyez_Project
- CourtListener Oral Argument Transcripts launch: https://free.law/2025/07/31/oral-argument-transcripts/
- SCOTUSblog on Oyez audio alignment: https://www.scotusblog.com/2022/01/now-available-on-oyez-january-oral-argument-audio-aligned-with-the-transcripts/
- Oyez speaker identification history: https://scotusoa.com/oyez-history/
- Oyez iOS app features: https://apps.apple.com/us/app/oyez/id346152567
- CourtListener advanced oral argument search: https://www.courtlistener.com/audio/
- WCAG 2.2 Chat Widget Accessibility Checklist: https://threada.ai/blog/wcag-22-chat-widget-accessibility-checklist/
- Chat UI Design best practices: https://www.uxpin.com/studio/blog/chat-user-interface-design/
- Legal Software UX: https://smotrow.com/insights/legal-software-ux-how-to-design-interfaces-that-lawyers-adopt
- Computational Analysis of SCOTUS Oral Argument: https://arxiv.org/pdf/2306.05373
- AI summarization bias research: https://arxiv.org/pdf/2411.04093
- Justia SCOTUS case browse by topic: https://supreme.justia.com/cases-by-topic/
