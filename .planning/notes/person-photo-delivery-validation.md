# Person Photo Delivery — Validation Report

**Validated:** 2026-09-24 against `.planning/notes/person-photo-asset-spec.md`.
**Asset location:** `/home/jason/scotuschat/person-photos` — **outside this repository**, alongside
`project/`, not inside it. 114 `.webp` files plus `manifest.csv`.
**Verdict:** accepted. Every mechanical check in the spec passes. Three items below need an
operator decision before or during Phase 54.1; none of them block ingest.

---

## Mechanical checks — all pass

| Check | Result |
|---|---|
| File count | 114 |
| Set match against corpus `oyez_speaker_id` | Exact — no extra files, no missing justices |
| Format | 114/114 real WebP, verified by Pillow `Image.open()` + `verify()`, not by extension |
| Colour mode | 114/114 RGB |
| Square | 114/114 |
| File size | min 3.0 KB, max 45.4 KB (ceiling was 120 KB) |
| EXIF / ICC | None present on any file |
| Manifest columns | All 10 required columns present |
| Manifest rows | 114, zero empty values in any required field |
| Reconciliation | Every file has a manifest row; every row has a file |
| Duplicate image bytes | None |
| Licence | **Every row public domain.** No CC-BY-SA, no non-commercial, anywhere |

### Undersized files — 19, all correctly declared

The spec permits undersized delivery ("undersized is acceptable, invented detail is not") provided
the true size is recorded. All 19 declare it in `delivered_px` with **zero mismatches**. Smallest is
`j__william_b_woods` at 209px, extracted from an 1886 group portrait. All read acceptably at the
60px popover render size.

### Collision set — correctly distinguished

The four known identity traps were each resolved to the right person:

| Id | Person |
|---|---|
| `j__john_m_harlan` | John Marshall Harlan (grandfather, 1877–1911) |
| `j__john_m_harlan2` | John Marshall Harlan II (grandson, 1955–1971) |
| `j__salmon_p_chase` | Salmon P. Chase |
| `j__samuel_chase` | Samuel Chase (different person) |
| `j__brockholst_livingston` | Henry Brockholst Livingston |

### Unprompted spec compliance worth noting

`j__william_cushing` uses the **unrestored** Commons original rather than the restored version that
sits in the article infobox, and the manifest says so. That is the spec's no-retouching rule applied
without being asked. Do not "upgrade" it later.

---

## Three items for the operator

### 1. Three licence claims are plausible but unverified

Self-flagged by the compiler rather than hidden. All three are near-certainly PD-USGov; the doubt is
about the *immediate* Commons source, not the underlying work.

| Justice | Issue |
|---|---|
| `j__byron_r_white` | Official SCOTUS photograph; Commons immediate source is eBay |
| `j__warren_e_burger` | Official SCOTUS photograph; Commons immediate source is an autograph auction listing |
| `j__john_paul_stevens` | Commons file carries a PDreview flag (immediate source is a news site); image is the official SCOTUS portrait |

These are the three rows an attribution audit would land on. Low risk, but they are the known weak
points and should not be rediscovered from scratch later.

### 2. `j__byron_r_white` framing is the outlier

Head occupies ~94% of the frame against the spec's 55–65% target. Visibly tighter than every
neighbour at 60px — the head touches the circle edge. Recrop if a larger source turns up; otherwise
accept it as the best available.

### 3. Background luminance varies widely — a design consequence, not a defect

Measured as mean luminance of the annulus just inside the circular mask. The page background is
`#0f1117` (luminance 15).

```
dark   (blends into the page)   67 files
mid                             34
light                           12
very light (bright disc)         1   ← j__samuel_blatchford, luminance 213
```

The asset spec deliberately forbids matting backgrounds to a flat colour, on the grounds that
varied backgrounds across eras are honest and a uniform matte is a fabrication. The consequence is
that roughly a dozen 19th-century engravings will render as bright discs against the dark page while
modern photographs sink into it.

**This is a design decision that has already been made by omission.** Options if it reads badly in
the Figma mockups: accept it, add a subtle ring or border to every avatar so the light ones are
bounded rather than floating, or revisit the no-matte rule. The middle option treats every speaker
identically and changes no source pixels, so it is the one that survives the apolitical constraint
most easily.

**A contact sheet exists for exactly this.** `/home/jason/scotuschat/justice-portraits-contact-sheet.png`
— all 114 portraits at 60px in a circular mask on the real page background, ordered by background
luminance so the spread is visible at a glance, plus each of the four extreme cases rendered at 80px,
60px, and 32px. Generated 2026-09-24. It sits beside `person-photos/`, outside this repository, because
it is a derived artifact of an asset set that also lives outside the repo. Send it to the Figma agent
before it finalises the card, so this is designed for rather than discovered.

---

## Reproducing this validation

Everything above came from `manifest.csv` plus Pillow reads of the 114 files. No network access, no
external tooling. Re-run it against any future re-delivery before ingest — the checks that matter
most are the set match against `speakers.json` (catches a renamed or dropped file) and the duplicate
byte hash (catches one portrait used for two people, the Harlan/Chase failure mode).
