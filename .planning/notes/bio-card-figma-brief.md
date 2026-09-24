# Bio Card — Figma Design Brief

**Written:** 2026-09-24. Paste the whole of §1–§8 to the Figma agent as the opening prompt.
**Assumes:** portraits exist for every justice (see `person-photo-asset-spec.md`), and the FJC
biographical data below has been imported.

---

## 1. What you are designing

SCOTUS Chat renders Supreme Court oral arguments as a chat transcript. Tapping a speaker's avatar
opens a **speaker card** — a popover showing who that person is.

That card exists today and is deliberately thin: photo, name, role pill, birth/death dates, an
empty bio slot, and a tenure list. You are redesigning it now that there is real biographical data
to put in it.

Design **two states of the same card**, because the underlying data is asymmetric:

- **Bench (Justice)** — full portrait, birth/death, tenure history, education, career history
- **Advocate** — a name, and in most cases nothing else

These are not two components. They are one component whose sections appear or disappear with the
data. That distinction is the whole design problem — see §6.

---

## 2. The data you have

### For a Justice (114 of them, essentially complete coverage)

| Field | Example | Notes |
|---|---|---|
| Full name | `Ruth Bader Ginsburg` | |
| Corpus display name | `Ruth Bader Ginsburg` | the form used in transcript attribution |
| Portrait | 400×400 square | circular crop, see §4 |
| Birth date / death date | `1933-03-15` / `2020-09-18` | either may be absent for living justices |
| Birth place | `Brooklyn, NY` | city + state |
| Office | `Associate Justice` or `Chief Justice` | some justices held both, sequentially |
| Tenure dates | `1993-08-10` – `2020-09-18` | one block per office held |
| Appointed by | `Bill Clinton` | per tenure |
| Appointing president's party | `Democratic` | per tenure — **this is the president's party, not the justice's** |
| How the tenure ended | `Death`, `Retirement`, `Promoted to Chief Justice` | |
| Nomination / confirmation dates | `1993-06-22` / `1993-08-03` | |
| Senate vote | `96-3` | only 29 of 113 have this |
| Education | up to 5 rows of `school · degree · year` | |
| Professional career | see below | |

### Professional career — the substantial field

A semicolon-delimited chronological career list. Present for every justice, back to 1789.

Median **343 characters / 6 entries**. Longest is Kagan at **754 characters / 14 entries**.

Two real examples, unedited:

> **Thurgood Marshall** — Private practice, Baltimore, Maryland, 1933-1937; NAACP, Baltimore
> [Maryland] Regional Office, 1934-1940; counsel, 1934-1936; special assistant counsel, 1936-1938;
> special counsel, 1938-1940; Director/counsel, NAACP Legal Defense and Educational Fund, 1940-1961;
> Solicitor general of the United States, 1965-1967

> **John Marshall** — Culpeper County [Virginia] Minutemen lieutenant, 1775-1776; Continental Army
> lieutenant, Eleventh Virginia Regiment, 1776-1780; Private practice, Fauquier County, Virginia,
> 1780-1783; Private practice, Richmond, Virginia, 1783-1797; State delegate, Virginia, 1782,
> 1784-1785, 1787-1788; Member, Virginia Council of State, 1782-1784; Recorder, Richmond City
> [Virginia] Hustings Court, 1785-1788; Delegate, Virginia convention to ratify the U.S.
> Constitution, 1788; Minister to France, U.S. Department of State, 1797-1798; U.S. representative
> from Virginia, 1799-1800; Secretary of State, 1800-1801

Note the shape: each entry is `role, place, years`. Several entries are sub-roles of the entry above
them (Marshall's "counsel, 1934-1936" belongs under NAACP). **Whether to parse that nesting out or
render the string as prose is one of the questions this design should answer.**

### For an Advocate (9,535 of them)

A name. That is all. There is no advocate biographical source, and inventing one is prohibited.

---

## 3. Design system — use these exact values

Dark theme only. There is no light mode.

**Colour**

```
--color-bg              #0f1117   page background
--color-surface         #1e293b   card background
--color-border          #334155   dividers, 1px
--color-text-primary    #e2e8f0   names, headings
--color-text-secondary  #94a3b8   body copy, labels, dates
--color-accent          #93c5fd   links only
```

Each speaker also carries a **per-speaker accent colour** assigned at render time from an 11-colour
categorical palette. The avatar ring and the role pill paint in that speaker's colour so the card
visibly matches the avatar that opened it. Treat it as a variable, not a fixed hue — design with two
or three different speaker colours to prove the layout holds.

**Type** — system UI stack, five sizes, two weights. Do not add a size or a weight.

```
caption   14px / 1.4
body      16px / 1.5
lead      18px / 1.6
heading   20px / 1.2
display   32px / 1.2

regular   400
semibold  600
```

**Spacing** — eight steps, all multiples of 4. Use only these.

```
xs 4   sm 8   md 12   lg 16   xl 24   2xl 32   3xl 48   4xl 64
```

**Existing patterns to keep**

- Section dividers are `1px solid --color-border` with `lg` (16px) padding above and below
- The role pill is a fully-rounded outline chip, `xs sm` padding, caption size, semibold
- Avatars are circular, `object-fit: cover`
- Body copy is caption size in `--color-text-secondary`; names are body size semibold in
  `--color-text-primary`

---

## 4. The card as it exists today

Build from this, do not replace it wholesale. Current vertical order:

```
┌──────────────────────────────────────────┐
│  ⬤ 60px    Ruth Bader Ginsburg           │   header row, gap: lg
│  portrait   [ Associate Justice ]        │   role pill, speaker colour
├──────────────────────────────────────────┤   divider
│  b. March 15, 1933 · d. Sept 18, 2020    │   caption, secondary — bench only
├──────────────────────────────────────────┤
│  (bio text — currently always empty)     │
├──────────────────────────────────────────┤
│  Associate Justice      1993 – 2020      │   tenure block, bench only
│  Bill Clinton · Democratic      Death    │   one block per office held
└──────────────────────────────────────────┘
```

For advocates, everything below the header is replaced by a single italic **"Coming soon"** line.
Replacing that placeholder with something honest is part of this brief.

---

## 5. Hard constraints

These are not preferences. A design that breaks one of them cannot ship.

**1. No editorial content whatsoever.** No summaries, no "notable for…", no highlights, no
characterisation, no statistics, no rankings. Every word on the card must be a sourced fact or a
field label. The card presents; the reader interprets. If a layout decision implies that one part of
a career mattered more than another, that is editorialising through design.

**2. Identical treatment for every speaker.** Same component, same section order, same visual
weight, same type sizes for a Justice and an advocate. Sections vary by *available data*, never by
*who the person is*. A Justice's card is longer because more is known, not because the design gives
them more room.

**3. Absent data renders as absent.** No "No bio available", no "—", no greyed placeholder rows, no
skeleton. A section with no data is simply not there, and the sections below close up. This is
existing, shipped behaviour and it is deliberate.

**4. Never invent plausible-looking data.** Do not populate an advocate mockup with a fictional firm
or a fictional career to make the layout look balanced. Use the real emptiness.

**5. Dates are formatted, never computed.** Show `1993 – 2020`. Do not show a calculated tenure
length, an age, or a duration — a derived number is an assertion.

**6. No utility-CSS framework.** Deliver tokens and measurements. Do not deliver Tailwind classes.

---

## 6. The central design problem

**The popover currently forbids truncation.** No line clamp, no "Read more", no internal scroll. Long
content simply makes the card taller. This is a locked decision (P-06) taken because a collapsed bio
with an expand toggle shipped once and was removed as the wrong pattern for popover content.

Now put a 754-character career history into that card.

A popover tall enough for Kagan's 14 career entries is not a popover any more — on a phone it is
taller than the viewport. But clamping it is banned, and dropping entries is editorialising about
which parts of a career matter.

**Resolve this. It is the main thing the design needs to answer.** Some directions worth exploring —
none of them pre-decided:

- **Split the surface.** The popover keeps the identity summary (portrait, name, office, tenure,
  dates); a dedicated full person page holds education and career. The popover gets a plain link.
  Costs a navigation step, keeps the popover a popover.
- **Restructure the career string.** Parsed into a compact dated list — years in a narrow left
  column, role in the right — it may be scannable enough that 14 entries read as a timeline rather
  than as a wall. Measure it before assuming.
- **Revisit P-06 specifically for career history.** The strongest case would be that a career list
  is structurally different from a bio paragraph: a list has natural item boundaries, so showing
  six of fourteen is not a mid-sentence cut. Make the argument explicitly if you take this route —
  it amends a locked decision.

Show the tradeoff rather than picking silently. Mock the extreme case (Kagan, 14 entries) and the
median case (6 entries) side by side.

---

## 7. Cases the design must survive

Mock every one of these. They are the real shape of the data, not edge cases.

1. **Modern justice, full data** — Ruth Bader Ginsburg: portrait, both dates, one tenure, 3 schools, 7 career entries
2. **Living justice** — Amy Coney Barrett: no death date, open-ended tenure ("2020 – "), still in office
3. **Two offices** — Harlan Fiske Stone: Associate 1925–1941 (appointed by Coolidge, Republican), then Chief 1941–1946 (appointed by Roosevelt, Democratic). Two tenure blocks, two presidents, two parties, one person.
4. **Longest career** — Elena Kagan: 14 entries, 754 characters
5. **Shortest career** — George Shiras: 2 entries, 97 characters
6. **18th-century justice** — John Marshall: 1755 birth, no photograph guarantee, 11 career entries, birthplace "Prince William County, VA"
7. **Advocate** — a name and nothing else
8. **Missing portrait** — falls back to a coloured circle with initials in the speaker's colour. Must not look broken or second-class.
9. **Long name** — `John Marshall Harlan, II` with a suffix, alongside a long role pill

Widths: **375px** (phone) and **768px+** (desktop). The card is a popover on desktop; decide and show
what it becomes on a phone.

---

## 8. Deliverables

1. The redesigned speaker card, bench and advocate states, at both widths
2. All nine cases from §7 as separate frames
3. If you propose a separate person page, that page too
4. A short written rationale for whichever §6 direction you took — specifically, what a reader loses
   under it
5. Redlines in the tokens from §3: every spacing value named (`lg`, not `16px`), every colour named

Flag anything you needed that §2 does not list. Do not fill a gap by inventing a field.
