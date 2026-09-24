# Person Photo Asset Specification

**Status:** draft — written 2026-09-24 for an external asset-compilation pass.
**Audience:** whoever (human or agent) compiles and formats the public-domain justice portraits.
**Scope:** the image files only. Ingest tooling, schema changes, and site rendering are separate work.

This document is the acceptance contract for the delivered asset set. An asset that meets
everything below drops into the existing upload path with no code change.

---

## 1. What the site does with these images today

Three render sites, all circular, all `object-fit: cover`:

| Surface | File | Rendered size | Renders a photo today? |
|---|---|---|---|
| Transcript speaker rail | `app/src/routes/arguments/[slug]/+page.svelte` | **32 × 32** | **No** — initials only (`speaker-fill` div, no `<img>`) |
| Speaker popover | `app/src/lib/public/SpeakerPopover.svelte` | **60 × 60** | Yes, with initials fallback |
| Admin person page | `app/src/routes/admin/people/[id]/+page.svelte` | **80 × 80** | Yes, with initials fallback |

Largest current render is **80 px**. The transcript rail is initials-only and will need a code
change before photos appear there — that is out of scope for the asset pass, but it is why the
spec below does not optimise for 32 px.

Every surface applies `border-radius: 50%`. **The image is cropped to a circle at render time.**
Anything outside the inscribed circle of the square is never seen.

---

## 2. Deliverable: one file per person

| Property | Value |
|---|---|
| Dimensions | **400 × 400 px**, exactly square |
| Format | **WebP** |
| Quality | ~82 (target ≤ 60 KB/file; do not exceed 120 KB) |
| Colour space | **sRGB**, 8-bit |
| Metadata | **Stripped** — no EXIF, no ICC beyond sRGB, no XMP |
| Transparency | None — flatten to opaque |
| Filename | `{oyez_speaker_id}.webp` (see §4) |

### Why 400 × 400

80 px is the largest render, and 3× DPR takes that to 240 px. 400 px clears it with headroom for a
larger bio card later, and costs ~30 KB. Going higher buys nothing a circular 80 px crop can show.

### Why not an image set

**Deliver a single file. Do not produce 1×/2×/3× variants or a `srcset` set.**

This is a constraint of the storage layer, not an aesthetic preference. `api/services/admin_people.py:841`
writes exactly one object per person — `people/{id}.{ext}` — and `people.photo_url` is a single
scalar `String(500)` column. There is no place to put a second variant without a schema change and a
storage-key change.

A 400 px WebP at ~30 KB is smaller than one of the page's JS chunks. Multi-variant delivery would be
a deviation requiring its own phase; flag it if you think the tradeoff is wrong, but do not deliver
variants speculatively — they cannot be stored.

---

## 3. Framing and crop

The circular mask is the whole reason this section exists. **Crop upstream — do not ship a
rectangular portrait and let `object-fit: cover` centre-crop it.** `cover` crops to the centre of
the frame, which on a standing or three-quarter portrait cuts the head off.

Target framing, head-and-shoulders:

```
┌─────────────────────┐  400px
│      ·  ~12%  ·     │   headroom above the crown
│    ┌─────────┐      │
│    │  head   │      │   head height ≈ 55–65% of frame
│    └─────────┘      │
│   eyes at ~38–42%   │   measured from the top edge
│  ╱  shoulders  ╲    │
└─────────────────────┘
```

- **Eyeline at 38–42% from the top.** This is the single measurement that makes a circular crop
  read correctly. Get this right and the rest is forgiving.
- **Head occupies 55–65% of the frame height.** Tighter looks claustrophobic in a 60 px circle;
  looser makes the face unreadable.
- **Horizontally centre the face**, not the body. On a three-quarter pose the body centre and the
  face centre are different points.
- Corners will be discarded by the circle. Do not put anything meaningful there.

### Historical material

Much of this set is 19th-century engravings, daguerreotypes, and painted portraits, not photographs.

- **Do not upscale** past the source's real resolution. A soft 400 px beats a sharpened 400 px.
  If a source only supports 250 px at the target framing, deliver 250 × 250 and note it in the
  manifest — undersized is acceptable, invented detail is not.
- **Do not colourise, retouch, de-noise, or "restore".** Faithful presentation is a project
  constraint. Ship the artefact as it is, cropped and resized only.
- **Do not matte the background to a flat colour.** Varied backgrounds across eras are honest;
  a uniform matte is a fabrication.
- Rotation to true vertical and straightforward crop/resize are the only permitted edits.

---

## 4. Filenames: use `oyez_speaker_id`, never `person_id`

**Name every file `{oyez_speaker_id}.webp`.** For example:

```
j__brett_m_kavanaugh.webp
j__brockholst_livingston.webp
j__byron_r_white.webp
```

The ids are in `data/corpus/speakers.json` — the 114 entries with `"role": "justice"`. They are
already filesystem-safe: lowercase, ASCII, underscore-separated.

**Why this matters.** The storage layer currently keys on `person_id` (`people/{person_id}.jpg`),
but `person_id` is a Postgres autoincrement that **does not survive `reset_to_fixture`** — this
project reseeds rather than migrates, so the table is truncated and ids are reissued. A photo set
named by `person_id` silently misattributes every portrait after the first reseed.

`oyez_speaker_id` is the stable key, and Phase 52 (Justice Identity) is the phase that makes it
authoritative and enforces its uniqueness at the database level. Name by it now and the ingest
step is a lookup; name by `person_id` and the set has a time bomb in it.

---

## 5. Roster

`data/corpus/supreme_court_justices_sections.csv` holds **116 distinct people** across 121 tenure
rows (five justices were promoted from Associate to Chief and appear twice — one person, two
tenures, one photo).

**114** of those have an `oyez_speaker_id` because they appear in the corpus. Those 114 are the
required set. The remaining two never spoke in a recorded argument; photos for them are optional
and, if supplied, need a manifest note since they have no id to key on.

Two name forms differ between our seed CSV and external sources — worth knowing while searching:

| Our CSV | Commonly catalogued as |
|---|---|
| `Brockholst Livingston` | Henry Brockholst Livingston |
| `Fred Vinson` | Frederick Moore Vinson |

There are also **two different John Marshall Harlans** — grandfather (1877–1911) and grandson
(1955–1971, suffixed `II`) — and **Salmon P. Chase** is a different person from **Samuel Chase**.
These four are the known collision set; check them by hand rather than by name match.

---

## 6. Licensing and the manifest

**Public domain only.** The safe categories:

- Works of the US federal government (17 U.S.C. §105) — official Supreme Court portraits,
  Library of Congress holdings, federal agency photographs
- Anything published in the US before 1930
- Works explicitly released to the public domain (CC0, PD-self)

Avoid anything under CC-BY-SA or a non-commercial clause. If the only available image of a justice
carries a share-alike licence, **flag it rather than including it** — the decision to accept an
attribution obligation is the operator's, not the compiler's.

### Required sidecar: `manifest.csv`

Ship alongside the images. One row per delivered file:

| Column | Notes |
|---|---|
| `oyez_speaker_id` | Must match the filename stem exactly |
| `full_name` | As catalogued at the source, for eyeball verification |
| `source_url` | Direct link to the asset page, not a search result |
| `source_institution` | e.g. "Library of Congress", "Supreme Court of the United States" |
| `license` | e.g. "PD-USGov", "PD-US-expired", "CC0" |
| `creator` | Photographer, engraver, or painter; `unknown` is acceptable |
| `date_created` | Year or range; `unknown` is acceptable |
| `date_accessed` | ISO 8601 |
| `delivered_px` | The actual square size shipped, if under 400 |
| `notes` | Anything the operator should see — a licence doubt, an identity ambiguity, a poor source |

The manifest is not bureaucracy. The project maintains a provenance-and-trust model
(`.planning/notes/provenance-and-trust-model.md`), an About page is planned for Phase 56, and
attribution for these images will have to come from somewhere. Reconstructing it later from 114
files is far more expensive than recording it once.

---

## 7. Validation before hand-off

The upload endpoint (`api/routers/admin.py`, `upload_person_photo`) will reject anything that fails
these, so check them first:

- [ ] Accepted formats are **JPEG, PNG, WebP only** — validated server-side by Pillow
      `Image.open()` + `verify()`, not by file extension. A mislabelled file is a 422.
- [ ] Every file is exactly square
- [ ] Every filename stem is a real `oyez_speaker_id` from `speakers.json`
- [ ] No duplicate stems
- [ ] Every file has a manifest row, and every manifest row has a file
- [ ] Nothing over 120 KB
- [ ] Spot-check 10 files at 60 px in a circular mask — that is the size most viewers will see,
      and framing errors that are invisible at 400 px are obvious at 60 px

---

## 8. Open questions for the operator

Not blockers for compiling the set, but they need answers before it ships.

1. **Advocates.** 9,535 advocates appear in the corpus and will have no photograph. The project's
   apolitical constraint requires that *every speaker gets identical schema, depth, and treatment*.
   Photographed justices next to initials-only advocates is a visible asymmetry that reads as
   status. Options: accept it, drop photos entirely, or use photos only where the popover already
   distinguishes bench from advocate. **This is a design decision, not a data one.**

2. **Transcript rail.** 32 px avatars are initials-only today. Do photos belong there, or does the
   rail stay initials with photos appearing only on the popover and bio card?

3. **Missing coverage.** If a justice has no findable public-domain portrait, the initials fallback
   already handles it gracefully. Confirm that a partial set is acceptable rather than all-or-nothing.
