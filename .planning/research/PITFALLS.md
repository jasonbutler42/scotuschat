# Domain Pitfalls

**Domain:** LLM-based legal transcript parsing pipeline + SCOTUS oral argument chat interface
**Researched:** 2026-06-11
**Scope:** LLM pipelines, SCOTUS transcript quirks, speaker resolution, SvelteKit/FastAPI integration, apolitical framing, pipeline orchestration, government data ingestion

---

## Critical Pitfalls

Mistakes that cause rewrites, data corruption, or fundamental architectural problems.

---

### Pitfall C1: Retrying Structural LLM Failures Treats Them as Transient

**What goes wrong:** Naive retry logic catches every LLM failure and resubmits the same prompt. When the failure is structural — the prompt is ambiguous, the schema is incompatible with the model's output style, or the input is too large — every retry produces the same bad output or valid-looking JSON with hallucinated values. The pipeline reports success. Downstream rows are silently corrupted.

**Why it happens:** Engineers borrow retry patterns from HTTP networking (where failures are mostly transient). LLM failures have four distinct categories that need different responses: transient infrastructure errors (rate limits, timeouts — safe to retry), prompt-induced failures (same output every time — fix the prompt), schema mismatch (structural incompatibility — fix the schema), and context window overflow (input too large — chunk differently). A single catch-and-retry branch conflates all four.

**Consequences:**
- Database accumulates hallucinated utterances, wrong speaker assignments, or truncated segments with no error signal.
- Retry metrics look healthy (success rate high) while data quality degrades.
- Issues surface only at UI review time, requiring re-running the full pipeline.

**Prevention:**
- Classify failures before deciding to retry. HTTP 429 / 503 → retry with backoff. HTTP 400 / 422 / JSON parse error → log, alert, stop.
- Validate LLM output against a strict Pydantic schema at the pipeline boundary. A valid JSON envelope that fails schema validation is a structural failure, not a transient one.
- Never retry more than 2 times on the same prompt+input combination. On the second failure, write a `pipeline_run_step` error record and halt that step for manual review.
- Track `retry_count` and `failure_reason` in the `pipeline_run` table.

**Warning signs:**
- Retry rate on the Parse step consistently above 5%.
- Utterance counts per argument vary wildly across reruns.
- Speaker names in the DB that do not match any known pattern (hallucinated names).

**Phase:** Pipeline Steps (Parse, Resolve) — must be addressed before first end-to-end run.

---

### Pitfall C2: Pre-2004 Transcripts Use "QUESTION" Instead of Justice Names

**What goes wrong:** The Court's policy until October Term 2003 was to label all Justice speech as "QUESTION" rather than using the Justice's name. A parsing strategy that assumes speaker labels are names will correctly attribute post-2004 arguments and silently fail for everything before 2004. The pipeline succeeds — it just assigns all Justice utterances to a fictional speaker named "QUESTION".

**Why it happens:** Testing only against recent (post-2004) transcripts creates false confidence. The format difference is not a parsing error — the text is valid — so no exception is raised.

**Consequences:**
- Pre-2004 arguments appear to have a single "QUESTION" speaker instead of individual Justices.
- The Resolve step has nothing to match — "QUESTION" is not a person record.
- If pre-2004 cases are ever ingested, all their Justice attribution is wrong.

**Prevention:**
- Identify transcript era (pre- vs. post-2004) at the Ingest step and tag the `argument` record with a `transcript_format_version` field.
- Pre-2004 format: a separate parsing strategy that marks Justice utterances as unattributed and notes the era limitation in the UI.
- Project scope explicitly defers pre-2000 transcripts. Enforce a guard at the Ingest step that rejects any transcript identified as pre-2004 with a clear error rather than silently accepting it.

**Warning signs:**
- Resolve step finds a raw speaker name of "QUESTION" or "Q" in the `utterance` table.
- Argument records show one Justice-role speaker for all bench utterances.

**Phase:** Pipeline Step 1 (Ingest) and Step 2 (Parse) — format detection must be wired in at ingest, not retrofitted.

---

### Pitfall C3: Chunking a Transcript Breaks Speaker Turn Continuity

**What goes wrong:** A typical SCOTUS oral argument transcript is 60–100 pages. Splitting it into fixed-size chunks for LLM processing creates chunk boundaries that cut through a speaker's utterance. The LLM sees a chunk that starts mid-sentence without knowing who was speaking. It invents a speaker attribution or assigns the fragment to the previous speaker it can infer.

**Why it happens:** Context window limits require chunking. The naive approach — split on page count or character count — does not respect the document's logical structure. LLMs exhibit a "lost in the middle" effect: information about who was speaking, established early in the chunk, degrades by the end.

**Consequences:**
- Utterances near chunk boundaries are misattributed or truncated.
- Short interjections (a one-word interruption by a Justice) at chunk edges are dropped entirely.
- Stitching chunks back into an ordered utterance list produces duplicates or gaps at seam points.

**Prevention:**
- Chunk on speaker-turn boundaries, not character count. Before LLM processing, run a lightweight regex pass to identify speaker label lines (all-caps name followed by colon) and use those as split points.
- Add a 2–3 turn overlap between chunks (last N speaker turns of chunk K become the first N turns of chunk K+1) so the LLM always has context about who was speaking.
- Deduplicate on reassembly using turn sequence numbers, not content matching.
- For typical SCOTUS transcripts (post-2004, 60–100 pages), a single modern LLM with a 200K+ context window can often process the whole transcript without chunking. Verify current model context limits before designing a chunking strategy.

**Warning signs:**
- Utterance count from a re-run differs from the prior run by more than 5%.
- Utterances with no speaker label, or with speaker label "continued" or "CONT'D".
- Two consecutive utterances with the same speaker where the second starts mid-sentence.

**Phase:** Pipeline Step 2 (Parse) — chunk strategy must be in the design before first prompt is written.

---

### Pitfall C4: Speaker Resolution Fails on Surname-Only and Role-Only Labels

**What goes wrong:** SCOTUS transcripts use inconsistent speaker labels. Advocates appear as "MR. BOPP", "MS. JACKSON", or "GENERAL PRELOGAR". Justices appear as "JUSTICE SOTOMAYOR" or just "CHIEF JUSTICE". The same person may appear with different labels across arguments (e.g., an advocate who later becomes a Justice). Simple string matching fails to resolve these to people records. LLM-based resolution hallucinates confident matches for ambiguous names.

**Why it happens:** The Resolve step is treated as a lookup table problem. It is actually an entity disambiguation problem with incomplete context. Surname-only labels ("MR. SMITH") are genuinely ambiguous — multiple advocates named Smith exist in SCOTUS history. Role labels ("GENERAL") refer to different people across terms.

**Consequences:**
- Utterances assigned to wrong person records, especially for common surnames.
- People records created as duplicates (same person under two slightly different names).
- Chief Justice and Solicitor General roles resolving correctly for one term, wrong for another.

**Prevention:**
- Use case metadata (term year, docket number, parties, counsel of record) as context for every resolution call — not just the speaker label string in isolation.
- Maintain a canonical `speaker_alias` table that maps known raw label patterns to person IDs. Pre-seed it with the known Justice roster and common Solicitor General patterns.
- When LLM resolution is below a confidence threshold, write a `needs_review` flag to the utterance rather than committing a guess. Surface these in an admin UI for manual confirmation.
- Never allow the Resolve step to create new person records without human approval. It may only match to existing records or flag as unresolved.

**Warning signs:**
- Duplicate person records with names that differ only in middle initial or suffix.
- A single argument showing two different person_ids for the same Justice.
- "GENERAL" resolving to the same person across terms where the Solicitor General changed.

**Phase:** Pipeline Step 3 (Resolve) — the alias table and confidence-gating logic must be designed before any production resolution runs.

---

### Pitfall C5: Consolidated Cases Assumed to Have One Docket Number

**What goes wrong:** Some SCOTUS arguments hear multiple consolidated cases in a single session. The official transcript covers one hearing but references multiple docket numbers. A pipeline that creates one `argument` record per PDF and one `case` record per docket number will either create orphaned argument records or silently associate utterances with only the lead docket, losing the relationship to consolidated dockets.

**Why it happens:** The happy-path data model assumes 1 PDF = 1 case = 1 argument. Real SCOTUS data has N-to-1 and 1-to-N relationships that only appear in edge cases (approximately 10–15% of argued cases in any given term involve consolidation).

**Consequences:**
- Schema cannot correctly represent consolidated cases without a many-to-many relationship between cases and arguments.
- If schema doesn't support consolidation at build time, adding it later requires a migration and re-parsing of affected transcripts.
- Users see an argument attributed to only one case when it actually resolved two.

**Prevention:**
- Design the `argument` ↔ `case` relationship as many-to-many from the start (a join table, not a foreign key on `argument`).
- At the Ingest step, parse the transcript header for all docket numbers referenced and create case records for each, linking all to the argument record.
- This is noted as a schema forward-compatibility requirement in PROJECT.md — treat it as a hard constraint, not a "nice to have."

**Warning signs:**
- Transcript header contains a slash-separated docket number (e.g., "Nos. 21-476 and 21-477").
- Oyez API returns multiple docket IDs for a single argument date.

**Phase:** Schema design (Phase 1 / database modeling) — cannot be retrofitted without migration.

---

## Moderate Pitfalls

Problems that cause significant rework but not full rewrites.

---

### Pitfall M1: Re-Arguments Treated as Duplicate Ingests

**What goes wrong:** A small number of cases are re-argued — the same case is heard twice in separate sessions (e.g., Citizens United v. FEC). If the pipeline deduplicates on case docket number, the second argument overwrites or is rejected as a duplicate. If it deduplicates on transcript date, both are ingested but float as two separate cases with the same name, confusing users.

**Prevention:**
- The schema correctly places utterances under `argument` records, not `case` records (as PROJECT.md specifies). Honor this strictly.
- Deduplication key for `argument` should be `(case_id, argument_date)`, not just `case_id`.
- The Ingest step must create a new `argument` record for each distinct hearing, even if the case already exists.
- Surface re-argument status in the UI so users understand why the same case appears twice.

**Phase:** Pipeline Step 1 (Ingest) and schema design.

---

### Pitfall M2: Stage Direction Lines Incorrectly Parsed as Utterances

**What goes wrong:** SCOTUS transcripts include parenthetical stage directions: `(Laughter.)`, `(Pause.)`, `(Recess.)`. These are not speech. An LLM prompt that extracts "everything a speaker says" may include stage directions as utterances, or may incorrectly assign them to the preceding speaker.

**Prevention:**
- Include explicit instructions in the parse prompt: "Lines enclosed in parentheses are stage directions, not speech. Extract them as a separate `stage_direction` utterance type with no speaker."
- Add a post-parse validation rule: utterances of type `speech` must have a non-null speaker. Utterances matching the `(...)` pattern and flagged as speech are a validation failure.

**Phase:** Pipeline Step 2 (Parse).

---

### Pitfall M3: SvelteKit SSR Fetch vs. Browser Fetch CORS Confusion

**What goes wrong:** SvelteKit's server-side `load` functions run in Node.js, where CORS does not apply. The same fetch call made from a browser after hydration is subject to CORS. Developers configure FastAPI's CORS middleware correctly for the browser case, but during SSR the request goes server-to-server and bypasses CORS entirely. This creates an asymmetry: pages work fine on SSR but fail in client-side navigation (or vice versa), and the errors look different in each environment.

**Prevention:**
- Use SvelteKit's built-in `fetch` inside `load` functions only — it handles cookie forwarding and deduplication. Never import a raw `fetch` polyfill or use `axios` directly in a `+page.server.ts` load function.
- Configure FastAPI's `CORSMiddleware` to allow the production SvelteKit origin explicitly. In dev, allow `localhost:5173`. Never use `allow_origins=["*"]` in production.
- Test navigation flows client-side (not just full-page load) before considering an API integration complete.
- CORS errors do not return a response object — they throw an exception. Code that checks `response.ok` after a CORS failure will crash, not gracefully handle the error.

**Phase:** API integration (any phase that wires SvelteKit to FastAPI).

---

### Pitfall M4: PDF Extraction Reading Order Mangled by Layout

**What goes wrong:** SCOTUS transcripts are typeset with wide left margins (speaker names) and body text in a narrower column. PDF character positions are absolute. A naive text extractor (e.g., raw `pypdf` without layout mode) extracts characters in the order they appear in the PDF stream, which may not match reading order. The result: speaker labels and speech content interleaved incorrectly, or lines from page headers/footers injected mid-utterance.

**Prevention:**
- Use `pdfplumber` rather than `pypdf` for initial text extraction. Its layout mode uses character positioning to reconstruct reading order.
- Strip page headers and footers before LLM processing. SCOTUS transcript headers include the case name and page number on every page — these must be filtered or they appear as utterance fragments.
- After extraction but before LLM processing, run a sanity check: does the text begin with the standard SCOTUS transcript opening ("IN THE SUPREME COURT OF THE UNITED STATES")? If not, the extraction likely failed or produced a garbled result.

**Phase:** Pipeline Step 2 (Parse) — PDF extraction strategy chosen before first prompt design.

---

### Pitfall M5: LLM Output Schema Version Not Tracked

**What goes wrong:** The parse prompt evolves. An early version extracts `{speaker, text}`. A later version adds `{speaker, text, utterance_type, citations}`. If schema version is not recorded alongside each parsed result, old rows and new rows in the database are structurally inconsistent. Queries that expect `utterance_type` return null for all old rows, and it is impossible to know which rows need reprocessing without examining each one.

**Prevention:**
- Store `prompt_version` and `schema_version` on every `pipeline_run` record (and by extension on every row derived from that run).
- When the schema changes, the prior `pipeline_run` rows are not updated — they are preserved as-is and a new run is triggered.
- The PROJECT.md design of `pipeline_run_id` on derived rows (re-runnable steps with old rows preserved) naturally supports this if `prompt_version` is added to the `pipeline_run` table.

**Phase:** Schema design and Pipeline Step 2 — add versioning before the first prompt is finalized.

---

### Pitfall M6: Oyez API Rate Limits and Availability Are Not Guaranteed

**What goes wrong:** The Oyez Project API (oyez.org) is an academic/nonprofit service with no documented SLA, rate limits, or uptime guarantees. The Enrich step calls it for Justice bio data, tenure dates, and photos. If the API is unavailable or changes its response schema, the Enrich step fails or silently produces empty records.

**Prevention:**
- Treat Oyez API responses as cacheable enrichment data, not real-time dependencies. Cache all API responses to the database on first successful fetch.
- The Enrich step should be re-runnable independently (PROJECT.md specifies this). If an Oyez call fails, write a `needs_enrichment` flag and continue — do not block argument display.
- Add a schema version check to Oyez API responses. If the response shape changes, fail loudly rather than writing partial data.
- Implement a polite crawl delay (2+ seconds between requests) and honor any `Retry-After` headers.

**Phase:** Pipeline Step 4 (Enrich).

---

### Pitfall M7: Apolitical Framing Broken by Asymmetric Bio Depth

**What goes wrong:** The hard constraint is that every speaker gets identical schema, depth, and treatment. The practical failure mode: Justice bios are easily sourced (Federal Judicial Center, Oyez, Wikipedia) and come pre-written. Advocate bios require more effort and may be sparse or unavailable. The UI ends up with rich Justice profiles and stub advocate profiles, which creates visible asymmetry that undermines the "uniformly formatted" constraint.

**Prevention:**
- Define the bio schema (fields, character limits, required vs. optional) before building the Enrich step. Every person record must have the same fields, even if some are null.
- Nulls must render gracefully in the UI — an empty field should not create a visual gap. Design the bio component to show "Not available" or omit the field entirely if null, not a blank space.
- Set a policy: no Justice bio field is populated unless the equivalent advocate bio field is also populated or confirmed unavailable. This prevents scope creep where Justices get special treatment.

**Phase:** Pipeline Step 4 (Enrich) and UI design.

---

## Minor Pitfalls

Annoying but recoverable issues.

---

### Pitfall N1: INAUDIBLE Speaker Tags in Oyez Data

**What goes wrong:** Some Oyez transcript entries have `<INAUDIBLE>` as the speaker — an interjection was heard but the speaker could not be identified. If the Resolve step is not designed for this, it will either crash on a null speaker label or create a person record named "INAUDIBLE."

**Prevention:** Treat `<INAUDIBLE>` and similar sentinel values (`[UNKNOWN]`, `UNKNOWN SPEAKER`) as reserved labels at the Resolve step. Map them to a system-level `unattributed_utterance` type rather than a person record.

**Phase:** Pipeline Step 3 (Resolve).

---

### Pitfall N2: Docket Number Format Inconsistencies

**What goes wrong:** SCOTUS docket numbers are typically `YY-NNNN` but original jurisdiction cases use `NNN ORIG` (e.g., `10 ORIG`). File names on supremecourt.gov use underscores in place of spaces (`10_ORIG`). A lookup keyed on raw docket string will fail to join across these representations.

**Prevention:** Normalize docket numbers to a canonical form (e.g., replace spaces with hyphens, lowercase "orig") at ingest and store both the raw and normalized forms. All lookups use the normalized form.

**Phase:** Pipeline Step 1 (Ingest).

---

### Pitfall N3: Absolute URLs in SvelteKit Load Functions Cause Double Fetches

**What goes wrong:** Using an absolute URL (e.g., `http://localhost:8000/api/...`) in a SvelteKit universal `load` function causes the fetch to run twice: once during SSR on the server, once again during client hydration. Relative URLs avoid double fetching but do not forward cookies automatically. This creates either a performance issue or an auth issue depending on which approach is used.

**Prevention:** Use server-only `load` functions (`+page.server.ts`) for all API calls that require auth context. Use the SvelteKit-provided `fetch` with relative paths. Pass data to the client via the `load` return value, not by re-fetching in `onMount`.

**Phase:** SvelteKit frontend implementation.

---

### Pitfall N4: Citation Extraction Scope Creep

**What goes wrong:** The pipeline has a Step 5 for citation extraction. During implementation, it is tempting to start resolving citations (linking "Brown v. Board" to a case record) because the data is right there. Citation resolution is explicitly out of scope and adds significant complexity (ambiguous case names, partial citations, cross-era references).

**Prevention:** Step 5 must write raw citation strings only. Add a database constraint or code comment that the `citation.resolved_case_id` column remains null until a future milestone explicitly addresses resolution. Do not build a resolver in Step 5.

**Phase:** Pipeline Step 5 (Citations).

---

### Pitfall N5: supremecourt.gov PDF URLs Are Not Stable Across Terms

**What goes wrong:** The URL pattern for transcript PDFs on supremecourt.gov changes by term year. A downloader hardcoded to one URL pattern will fail silently for newer or older terms. The site has also returned HTTP 403 to automated clients at times.

**Prevention:**
- Treat the PDF URL as a field stored in the `argument` record at Ingest time — do not reconstruct it from docket number + term year at download time.
- Test the download step against the URL stored at ingest. If the URL returns non-200, log it and do not proceed to parse. Never silently parse a partial or error-page PDF.
- Store the raw PDF bytes in local storage (or Digital Ocean Spaces) immediately on download. All subsequent pipeline steps read from the stored copy, not from supremecourt.gov. This also implements the "immutable source" constraint from PROJECT.md.

**Phase:** Pipeline Step 1 (Ingest).

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|----------------|------------|
| Database schema design | Consolidated cases need M:M case-argument relationship | Hard-code M:M from the start (C5) |
| Database schema design | Re-arguments need argument-scoped utterances | Enforce argument_id on utterances, not case_id (M1) |
| PDF download / Ingest | supremecourt.gov URL instability, HTTP 403 | Store URL at ingest; cache PDFs locally (N5) |
| PDF extraction | Mangled reading order from absolute positioning | Use pdfplumber in layout mode; strip headers/footers (M4) |
| LLM parse prompt | Chunk boundaries break speaker turns | Chunk on speaker-turn boundaries with overlap (C3) |
| LLM parse prompt | Pre-2004 "QUESTION" labels | Detect era at ingest; reject pre-2004 with clear error (C2) |
| LLM parse step | Structural failures retried as transient | Classify failures before retrying; 2-retry max (C1) |
| LLM parse step | Schema version drift | Store prompt_version and schema_version on pipeline_run (M5) |
| Stage direction parsing | Parentheticals extracted as speech | Explicit prompt instruction + post-parse validation (M2) |
| Speaker resolution | Surname-only and role-only labels | Alias table + case metadata context + confidence gating (C4) |
| Speaker resolution | INAUDIBLE and unknown speaker tags | Reserve sentinel values; never create person records for them (N1) |
| Speaker resolution | Docket number format variants | Normalize at ingest; store raw and normalized (N2) |
| Enrich step | Oyez API unavailability | Cache responses; degrade gracefully; flag for retry (M6) |
| Enrich step | Asymmetric bio depth breaks apolitical constraint | Define bio schema with required/optional fields before building (M7) |
| SvelteKit/FastAPI wiring | CORS asymmetry between SSR and client | Configure CORSMiddleware explicitly; use server load functions (M3) |
| SvelteKit load functions | Double fetches with absolute URLs | Use server-only load functions with relative URLs (N3) |
| Citation extraction | Scope creep into resolution | Step 5 writes raw strings only; nullify resolved_case_id by constraint (N4) |

---

## Sources

- [LLMs for Structured Data Extraction from PDFs — Unstract](https://unstract.com/blog/comparing-approaches-for-using-llms-for-structured-data-extraction-from-pdfs/)
- [The LLM Retry Loop That Looks Like Progress and Does Nothing — Pithy Cyborg](https://pithycyborg.substack.com/p/the-llm-retry-loop-that-looks-like)
- [LLM Structured Outputs: Schema Validation for Real Pipelines — Collin Wilkins](https://collinwilkins.com/articles/structured-output)
- [Why PDFs Fail Under LLM Parsing — Untethered AI](https://untetheredai.substack.com/p/why-pdfs-fail-under-llm-parsing)
- [Debugging LLM-as-a-Judge: Why 42% of Hallucinations are Actually Pipeline Failures — Dev|Journal](https://earezki.com/ai-news/2026-05-03-your-llm-as-a-judge-sees-86-hallucinations-42-are-your-pipeline/)
- [Transcripts and Recordings of Oral Arguments — supremecourt.gov](https://www.supremecourt.gov/oral_arguments/availabilityoforalargumenttranscripts.aspx)
- [U.S. Supreme Court Transcripts — Lone Dissent](https://lonedissent.org/transcripts/)
- [Computational Analysis of Oral Argument in the Supreme Court — arXiv 2306.05373](https://arxiv.org/abs/2306.05373)
- [Pardon the Interruption: Gender and Turn-Taking in SCOTUS — arXiv 2009.07391](https://arxiv.org/abs/2009.07391)
- [walkerdb/supreme_court_transcripts — GitHub](https://github.com/walkerdb/supreme_court_transcripts)
- [hlepp/pardontheinterruption — GitHub](https://github.com/hlepp/pardontheinterruption)
- [Entity Resolution with Elasticsearch and LLMs — Elastic](https://www.elastic.co/search-labs/blog/entity-resolution-llm-elasticsearch)
- [CORS issues during SSR — SvelteKit GitHub Discussion #9295](https://github.com/sveltejs/kit/discussions/9295)
- [SvelteKit fetch double request issue — GitHub Issue #3892](https://github.com/sveltejs/kit/issues/3892)
- [Idempotency in Data Pipelines — Prefect](https://www.prefect.io/blog/the-importance-of-idempotent-data-pipelines-for-resilience)
- [Building Idempotent Data Pipelines — Medium / Towards Data Engineering](https://medium.com/towards-data-engineering/building-idempotent-data-pipelines-a-practical-guide-to-reliability-at-scale-2afc1dcb7251)
- [LLM Context Window Management — Tanuj Garg](https://tanujgarg.com/blog/llm-context-window-management-production)
- [pdfplumber — GitHub](https://github.com/jsvine/pdfplumber)
- [Extract Text from a PDF — pypdf documentation](https://pypdf.readthedocs.io/en/stable/user/extract-text.html)
- [Oyez Supreme Court Oral Arguments Dataset — ConvoKit](https://convokit.cornell.edu/documentation/oyez.html)
