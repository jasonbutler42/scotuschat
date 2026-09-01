<script lang="ts">
	import { flushSync } from 'svelte';
	import { enhance } from '$app/forms';
	import CopyableExtractedValue from '$lib/admin/CopyableExtractedValue.svelte';
	import CreatePersonPopover from '$lib/admin/CreatePersonPopover.svelte';
	// G-49-3/D-35 (plan 49-10): the bucket rule, the operator-visible role
	// labels, and the specific-advocate-role helper are shared with the
	// argument-detail Speakers card — both cards import from the single
	// source of truth rather than each declaring their own copy.
	import { SIDE_LABEL, sideBucket, specificAdvocateRole, crossesSideBoundary } from '$lib/participantSide';

	// Phase 25 — Restructured Resolve card (D-10 through D-19, D-21, PJOB-14 through PJOB-19, PJOB-21).
	// Phase 44 (RESOLVE-01/D-03/D-04) — five-column rework: the Action column is deleted and
	// its two person-matching buttons fold into a single combobox entry point inside Resolved
	// As; Descriptor (renamed from Title, Phase 44 Plan 01) now always renders instead of
	// disappearing for bench/gated rows.
	// Phase 44 Plan 05 (RESOLVE-07/08, Figma reconciliation) — four-column merge: the
	// standalone Bench/Advocate column is deleted; the segmented toggle and the person
	// control are stacked inside the single Resolved As cell. The confirm/correct
	// disposition state machine (the click-to-reveal search handler, the Change link,
	// the Select-person link, and the checkmark-plus-name confirmation banner) is
	// deleted entirely — the person control is a single always-rendered searchable
	// dropdown, gated (never removed) via disabled/aria-disabled when the row's side
	// has not yet been chosen.
	// Locked column order: Raw Label, Resolved As, Argument Role, Descriptor.
	//
	// Two backend data sources are merged by raw_speaker_label:
	//  - resolveRows (GET .../resolve-rows, Plan 25-02): the authoritative side/descriptor/
	//    argument_role/bench_role/missing_tenure/editable state for every participant.
	//  - discrepancies (AdminJobResponse.discrepancies, pre-Phase-25): only populated
	//    while jobStatus === 'paused' — carries auto-match candidates for the operator's
	//    person-matching flow that ArgumentParticipant.person_id has not yet committed.
	//
	// Side/descriptor edits submit immediately per-row via ?/saveResolveRow (T-25-16: job_id
	// is the only trust boundary; participant ownership is re-verified server-side).
	// Person-matching (search/select/create person) accumulates client-side and submits
	// as a batch via ?/resolve when the primary CTA is clicked (existing pipeline
	// resolve-step contract, unchanged by Phase 25).

	interface Candidate {
		id: number;
		full_name: string;
		role_name?: string | null;
		// Phase 44 Plan 07 (RESOLVE-09): optional because not every candidate source
		// carries it — the `people` prop always does (PersonListItem), but a
		// discrepancy-snapshot candidate (pipeline/commands/resolve.py) and a
		// freshly-created candidate that predates handlePersonCreated's enrichment
		// do not. That optionality is exactly what sideScopedCandidates' fail-open
		// rule below exists to handle.
		is_justice?: boolean;
	}

	interface Discrepancy {
		raw_speaker_label: string;
		auto_match_id?: number | null;
		auto_match_name?: string | null;
		auto_match_role?: string | null;
		auto_resolved?: boolean | null;
		candidates: Candidate[];
		// Phase 44 hint-snapshot fix: the side as classified at parse/import
		// time, frozen into the discrepancy blob before any operator edit can
		// overwrite ArgumentParticipant.side — lets the Resolve As hint show
		// what was actually extracted independent of the live toggle. Absent
		// on discrepancies created before this fix shipped (older jobs).
		extracted_side?: string | null;
	}

	interface ResolveRow {
		participant_id: number;
		raw_speaker_label: string;
		person_id: number | null;
		full_name: string | null;
		photo_url: string | null;
		side: string;
		argument_role: string | null;
		descriptor: string | null;
		descriptor_hint: string | null;
		bench_role: string | null;
		missing_tenure: boolean;
		person_edit_href: string | null;
		editable: boolean;
	}

	interface ResolveCardProps {
		resolveRows: ResolveRow[];
		discrepancies: Discrepancy[] | null;
		people: Candidate[];
		peopleLoadError?: string | null;
		jobStatus: string;
		readonlyMode: boolean;
		resolveFormError?: string | null;
		// Phase 44 Plan 07 (RESOLVE-10): the job's real ingestion provenance,
		// already derived by the API (api/schemas/admin_jobs.py); no default —
		// the parent always supplies it.
		source: 'pdf' | 'corpus';
		// Plan 44-09 tenure-preview follow-up: needed to call the job-scoped
		// bench-role-preview proxy endpoint (app/src/routes/admin/pipeline/
		// [job_id]/bench-role-preview/+server.ts) — never used for anything else.
		jobId: number;
	}

	let {
		resolveRows,
		discrepancies = null,
		people = [],
		peopleLoadError = null,
		jobStatus,
		readonlyMode,
		resolveFormError = null,
		source,
		jobId,
	}: ResolveCardProps = $props();

	let isPaused = $derived(jobStatus === 'paused');
	let interactive = $derived(!readonlyMode);
	// Phase 44 Plan 07 (RESOLVE-10): one AdminJob has exactly one ingestion
	// source, so this prefix is uniform for every row and every hinted cell of
	// one card. Derived once from the API's own already-computed answer —
	// never re-derived here from any pipeline-internal implementation detail.
	let sourcePrefix = $derived(source === 'corpus' ? 'Imported' : 'Extracted');

	interface MergedRow extends ResolveRow {
		discrepancy: Discrepancy | null;
	}

	let mergedRows = $derived.by<MergedRow[]>(() => {
		const discMap = new Map<string, Discrepancy>();
		for (const d of discrepancies ?? []) {
			discMap.set(d.raw_speaker_label, d);
		}
		return resolveRows.map((r) => ({
			...r,
			discrepancy: discMap.get(r.raw_speaker_label) ?? null,
		}));
	});

	// ──────────────────────────────────────────────────────────────────────────
	// Side/descriptor inline save (saveResolveRow) — per-row hidden form, submitted
	// programmatically via requestSubmit() so the select/input controls (which
	// live in different <td> cells) can share one form via the HTML `form=`
	// attribute rather than nesting a <form> inside table cells.
	// ──────────────────────────────────────────────────────────────────────────

	let formRefs: Record<number, HTMLFormElement> = {};
	let saveState = $state<Record<number, { saving: boolean; error: string | null }>>({});
	let pendingSideOverrides = $state<Record<number, string>>({});
	let sideGateConfirmed = $state<Record<number, boolean>>({});
	// Task 3 checkpoint remediation (44-05, data-loss fix): `side` is the single
	// stored column for both the Bench/Advocate toggle AND the specific advocate
	// role (PETITIONER/RESPONDENT/AMICUS) — there is no separate argument-role
	// column. Before this fix, toggleSide's Advocate branch hardcoded 'UNKNOWN'
	// on every click, so a Bench→Advocate round trip silently discarded whatever
	// specific role the operator had already chosen. This map remembers the last
	// specific advocate role picked per row so the toggle can restore it instead.
	let lastAdvocateRole = $state<Record<number, string>>({});

	// Task 4 checkpoint remediation (44-09, item 9 — confirmed data-loss bug):
	// `list_resolve_rows_for_job` correctly reports descriptor: null while a
	// row is on BENCH (44-06, by design — "hidden, not shown"). Without this
	// memory, toggling Advocate -> Bench -> Advocate destroys an already-saved
	// descriptor: the moment the Advocate branch re-renders, the descriptor
	// `<input>` reappears bound to the now-null row.descriptor prop (''), and
	// because toggleSide's own submitRow() fires synchronously in the same
	// click (flushSync() then requestSubmit(), same pattern as
	// lastAdvocateRole above), that empty string is submitted in the SAME
	// request as the side change — and since side is no longer BENCH, the
	// server writes descriptor="". This mirrors lastAdvocateRole exactly: a
	// per-participant client-side memory that survives the row's own prop
	// going null while hidden.
	let lastDescriptorValue = $state<Record<number, string>>({});

	// Plan 44-09 tenure-preview follow-up (operator-approved during Task 4
	// remediation): benchRoleState/argumentRoleCell key on row.person_id, the
	// COMMITTED database value — but a person picked in the Resolved As
	// dropdown lives only in client-side rowMatchStates until the batch
	// ?/resolve submit commits it, so a freshly-picked bench candidate's
	// tenure-derived role was stuck showing the unresolved-bench copy below
	// until commit. Keyed by participant_id, each entry also carries the personId
	// it was computed for — read alongside rowMatchStates[label].personId
	// wherever this is consulted, so a slow response for a candidate the
	// operator has since moved away from is never mistaken for the current
	// pick's role (44-06's prohibition: a tenure-derived role must never be
	// older than the request that rendered it).
	let benchRolePreview = $state<
		Record<number, { personId: number; bench_role: string | null; missing_tenure: boolean }>
	>({});
	// Dedup cache so the effect below issues at most one fetch per distinct
	// (participant, personId) pair, even though it re-runs (and re-scans every
	// row) whenever any row's rowMatchStates entry changes.
	let benchRolePreviewFetched = $state<Record<string, boolean>>({});

	async function fetchBenchRolePreview(participantId: number, personId: number) {
		try {
			const res = await fetch(`/admin/pipeline/${jobId}/bench-role-preview?person_id=${personId}`);
			if (!res.ok) return;
			const data = await res.json();
			benchRolePreview[participantId] = {
				personId,
				bench_role: data?.bench_role ?? null,
				missing_tenure: data?.missing_tenure === true,
			};
		} catch {
			// Best-effort only — the committed value still lands correctly once
			// the batch ?/resolve submit runs; a failed preview just leaves the
			// row in its unresolved-bench state until then.
		}
	}

	function rowFormId(participantId: number): string {
		return `resolve-row-form-${participantId}`;
	}

	function submitRow(participantId: number) {
		// Svelte 5 batches $state writes into a microtask — flushing here forces the
		// just-set pendingSideOverrides/descriptor state into the DOM before
		// requestSubmit() serializes the form, so the hidden `side` input (and any
		// other data-carrying input) reflects the value just chosen, not the
		// previous render's value (Task 1, 44-03).
		flushSync();
		formRefs[participantId]?.requestSubmit();
	}

	function effectiveSide(row: MergedRow): string {
		return pendingSideOverrides[row.participant_id] ?? row.side;
	}

	// D-11/PJOB-18: rows needing intervention (no auto-resolved match while paused)
	// must have Bench/Advocate confirmed before the person typeahead activates.
	// Auto-matched rows stay complete and skip this gating.
	function needsSideGate(row: MergedRow): boolean {
		if (!isPaused) return false;
		if (!row.discrepancy) return false;
		if (row.discrepancy.auto_resolved === true) return false;
		return !sideGateConfirmed[row.participant_id];
	}

	// Task 4 checkpoint remediation (44-09, item 6): a person matched under
	// one side must not silently remain selected once the operator switches
	// the row to the other side — the two candidate pools are disjoint
	// (sideScopedCandidates, RESOLVE-09), so a carried-over personId could
	// point at a person the new side's dropdown would never itself have
	// offered. Keyed on the BENCH/non-BENCH bucket, not the raw side value,
	// so switching among the three specific advocate roles
	// (PETITIONER/RESPONDENT/AMICUS) never clears the pick — only a real
	// Bench<->Advocate flip does.
	let lastSideBucket = $state<Record<number, 'BENCH' | 'ADVOCATE'>>({});

	// Clears the row's own person selection only when the bucket recorded
	// for this participant differs from the new one — never on the first
	// bucket ever recorded for a participant, so initial load/seeding (see
	// the seeding $effect below) is never mistaken for an operator-driven
	// switch. The `previousBucket !== undefined` guard stays visible here
	// (rather than living only inside the imported crossesSideBoundary)
	// because a contract assertion targets this literal directly; the
	// actual bucket-changed comparison is delegated to the shared predicate
	// (plan 49-10, G-49-3/D-35) so both cards agree on what a boundary
	// crossing is.
	function clearPersonOnSideBucketChange(row: MergedRow, newSide: string): void {
		const previousBucket = lastSideBucket[row.participant_id];
		if (previousBucket !== undefined && crossesSideBoundary(previousBucket, newSide)) {
			const s = rowMatchStates[row.raw_speaker_label];
			if (s) {
				s.personId = null;
				s.comboQuery = '';
			}
		}
		lastSideBucket[row.participant_id] = sideBucket(newSide);
	}

	function confirmSide(row: MergedRow, choice: 'BENCH' | 'ADVOCATE') {
		const value = choice === 'BENCH' ? 'BENCH' : 'UNKNOWN';
		clearPersonOnSideBucketChange(row, value);
		pendingSideOverrides[row.participant_id] = value;
		sideGateConfirmed[row.participant_id] = true;
		submitRow(row.participant_id);
	}

	function onSideChange(row: MergedRow, value: string) {
		clearPersonOnSideBucketChange(row, value);
		pendingSideOverrides[row.participant_id] = value;
		submitRow(row.participant_id);
	}

	// Task 1 (RESOLVE-02): the segmented toggle's click handler. Both segments call
	// this; it is the only new handler — confirmSide/onSideChange are extended, not
	// replaced (44-CONTEXT.md "Established Patterns").
	function toggleSide(row: MergedRow, choice: 'BENCH' | 'ADVOCATE') {
		const gated = needsSideGate(row);
		const current = effectiveSide(row);
		const alreadyActive = !gated && (choice === 'BENCH' ? current === 'BENCH' : current !== 'BENCH');
		if (alreadyActive) {
			// No-op: clicking the already-active segment must not write state or
			// submit, or a second Advocate click would reset a stored PETITIONER
			// back to UNKNOWN.
			return;
		}
		if (gated) {
			confirmSide(row, choice);
			return;
		}
		if (choice === 'BENCH') {
			onSideChange(row, 'BENCH');
			return;
		}
		// Task 3 checkpoint remediation: restore the last specific advocate role
		// chosen this session, falling back to the row's own already-committed
		// side if it was already a specific role (e.g. loaded from the server
		// still set to RESPONDENT) and only defaulting to the generic placeholder
		// when neither is known — never destroy a role the operator already set.
		const restored =
			lastAdvocateRole[row.participant_id] ?? specificAdvocateRole(row.side) ?? 'UNKNOWN';
		onSideChange(row, restored);
	}

	// Task 2 (RESOLVE-03): the Argument Role dropdown's onchange handler. Picking a
	// role while the side gate is still open (D-07 delta #1) satisfies the gate the
	// same way choosing Bench/Advocate on the toggle would — an operator picking
	// "Petitioner's Counsel" has unambiguously chosen Advocate, so it would be a
	// pointless extra step to force the toggle click first.
	function chooseArgumentRole(row: MergedRow, value: string) {
		const specific = specificAdvocateRole(value);
		if (specific) {
			// Task 3 checkpoint remediation: remember it so a later Bench→Advocate
			// toggle restores this instead of resetting to UNKNOWN.
			lastAdvocateRole[row.participant_id] = specific;
		}
		if (needsSideGate(row)) {
			clearPersonOnSideBucketChange(row, value);
			pendingSideOverrides[row.participant_id] = value;
			sideGateConfirmed[row.participant_id] = true;
			submitRow(row.participant_id);
			return;
		}
		onSideChange(row, value);
	}

	// Task 2 (RESOLVE-05, D-08/D-09): hint-value helpers for the four `Imported:`
	// hints rendered below each hinted column's control. Each takes the same
	// row/side/gate inputs the control above it already derives, so the hint can
	// never drift from what is displayed there. D-08 confirmed no separate stored
	// originally-extracted value exists for side or argument role — these
	// necessarily redisplay the row's own current value under the honest
	// "Imported:" wording rather than a fabricated per-field extraction event.
	// Real per-row provenance detection is explicitly deferred (Deferred Ideas).
	function resolvedAsHintValue(row: MergedRow): string | null {
		return row.full_name != null ? row.raw_speaker_label : null;
	}

	function sideHintValue(side: string, gated: boolean): string | null {
		if (gated) return null;
		return side === 'BENCH' ? 'Bench' : 'Advocate';
	}

	// Task 4 checkpoint remediation (44-09, item 5, confirmed via Figma): the
	// Resolved As cell's Bench/Advocate hint and Name hint merge into a single
	// line — "{SideLabel} · {NameOrN/A}", or bare "N/A" while the side gate is
	// still open. Reuses sideHintValue's own gated/label logic and
	// resolvedAsHintValue's own raw-label-or-null logic unchanged; only the
	// combination is new.
	//
	// Checkpoint remediation (44-09, live testing): the side fed into
	// sideHintValue is `row.discrepancy?.extracted_side` — the side as it
	// stood right after parse/import, frozen into the discrepancy blob
	// before any operator edit could overwrite it (see the pipeline's
	// discrepancy-building steps) — not the live `side` prop. A hint whose
	// text changes every time the operator toggles
	// Bench/Advocate cannot answer the one question it exists to answer:
	// "what did the source document actually say," so it must stay frozen
	// regardless of the current toggle. Falls back to the live `side` only
	// for discrepancies created before this fix shipped, which never
	// captured extracted_side — better than showing nothing for old jobs,
	// though it still won't be frozen for those.
	function combinedResolvedAsHintValue(row: MergedRow, side: string, gated: boolean): string | null {
		const extractedSide = row.discrepancy?.extracted_side ?? side;
		const sideLabel = sideHintValue(extractedSide, gated);
		if (sideLabel == null) return null;
		return `${sideLabel} · ${resolvedAsHintValue(row) ?? 'N/A'}`;
	}

	function argumentRoleHintValue(row: MergedRow, side: string, gated: boolean): string | null {
		if (gated) return null;
		// Plan 44-08 (RESOLVE-12): the bench fork moved out of the hint layer and
		// into argumentRoleCell/benchRoleState — the bench role was never an
		// ingested value, so it never had an "Imported:"/"Extracted:" hint to
		// begin with. This helper now only ever answers for the three advocate
		// sides.
		if (side === 'PETITIONER' || side === 'RESPONDENT' || side === 'AMICUS') {
			return SIDE_LABEL[side];
		}
		return null;
	}

	// Plan 44-08 (RESOLVE-12/14): the three mutually-exclusive bench Argument
	// Role states, extracted into a named predicate so the ordering rule lives
	// in one place and the contract test can assert the fork directly instead
	// of scraping markup. Keys only on side, person_id and missing_tenure —
	// never on rowEditable/gated — so the read-only card renders identically
	// (RESOLVE-11, canonical point 10).
	//
	// Order matters: an unresolved bench row (row.person_id == null) reports
	// missing_tenure === false from the service (api/services/admin_people.py
	// -- `if participant.person_id is not None else (None, False)`), so the
	// unresolved check must run before the calculated check or an unresolved
	// row would fall into the locked box with nothing to show.
	function benchRoleState(
		row: MergedRow,
		side: string,
	): 'unresolved' | 'calculated' | 'missing-tenure' | null {
		if (side !== 'BENCH') return null;
		if (row.person_id == null) {
			// Plan 44-09 tenure-preview follow-up: prefer a live preview over the
			// unresolved state, but only while it was computed for the exact
			// personId currently picked — a stale preview for a candidate the
			// operator has since moved away from must never render (44-06).
			const personId = rowMatchStates[row.raw_speaker_label]?.personId;
			const preview = benchRolePreview[row.participant_id];
			if (personId != null && preview?.personId === personId) {
				return preview.missing_tenure ? 'missing-tenure' : 'calculated';
			}
			return 'unresolved';
		}
		if (!row.missing_tenure) return 'calculated';
		return 'missing-tenure';
	}

	// ──────────────────────────────────────────────────────────────────────────
	// Person-matching flow (only while isPaused) — adapted from the pre-Phase-25
	// discrepancy review table, relocated into the "Resolved as"/Action columns.
	// ──────────────────────────────────────────────────────────────────────────

	interface RowMatchState {
		personId: number | null;
		extraCandidates: Candidate[];
		comboQuery: string;
		comboOpen: boolean;
		comboHighlight: number;
	}

	let rowMatchStates = $state<Record<string, RowMatchState>>({});

	$effect(() => {
		if (!isPaused) return;
		const disc = discrepancies ?? [];
		const incomingKeys = new Set(disc.map((d) => d.raw_speaker_label));
		for (const key of Object.keys(rowMatchStates)) {
			if (!incomingKeys.has(key)) {
				delete rowMatchStates[key];
			}
		}
		// RESOLVE-08 delta 4: join against resolveRows (the prop, never mergedRows) so a
		// row that already carries a committed person_id/full_name seeds as reviewed
		// rather than un-reviewed, even if it still appears in the discrepancy list —
		// otherwise allDispositioned/matchesJson would disagree with what the table
		// visibly shows.
		const rowsByLabel = new Map<string, ResolveRow>();
		for (const r of resolveRows) {
			rowsByLabel.set(r.raw_speaker_label, r);
		}
		const peopleIsJusticeById = new Map<number, boolean>();
		for (const p of people) {
			if (p.is_justice != null) peopleIsJusticeById.set(p.id, p.is_justice);
		}
		for (const d of disc) {
			if (!(d.raw_speaker_label in rowMatchStates)) {
				// D-03/D-04: any row with an auto-match candidate (or an already-committed
				// person_id) seeds pre-filled — the dropdown opens already showing that
				// name, and an untouched pre-fill still counts as accepted on submit since
				// personId is seeded non-null (no Confirm button exists, no disposition
				// field to track separately any more).
				const committedRow = rowsByLabel.get(d.raw_speaker_label);
				const candidateId = d.auto_match_id ?? committedRow?.person_id ?? null;
				// Checkpoint remediation (44-09): a bare fallback here ignores which
				// side the candidate actually belongs to. On a fresh page load the
				// row's own `side` already reflects any switch made in a prior
				// session (side changes save immediately via ?/saveResolveRow), but
				// this seed used to re-fill the dropdown from the pipeline's original
				// auto-match / a stale committed person_id regardless — so a person
				// cleared by switching sides silently reappeared on refresh, still
				// attached to the side they no longer belong to. Fail open (RESOLVE-09
				// convention): only drop the candidate when we can positively confirm
				// its side doesn't match; an unknown is_justice still seeds normally.
				const currentBucket = sideBucket(committedRow?.side ?? 'UNKNOWN');
				const candidateIsJustice =
					candidateId != null ? peopleIsJusticeById.get(candidateId) : undefined;
				const sideMismatch =
					candidateIsJustice != null &&
					((currentBucket === 'BENCH') !== candidateIsJustice);
				const seededPersonId = sideMismatch ? null : candidateId;
				rowMatchStates[d.raw_speaker_label] = {
					personId: seededPersonId,
					extraCandidates: [],
					comboQuery: sideMismatch
						? ''
						: (d.auto_match_name ?? committedRow?.full_name ?? ''),
					comboOpen: false,
					comboHighlight: -1,
				};
				// Task 4 checkpoint remediation (item 6): seed the baseline bucket
				// from the row's own already-committed side, if any — this is
				// recorded, never cleared against, so the operator's first
				// explicit switch this session (even away from a side that was
				// only ever known from the server, not chosen in this session)
				// is still detected as a real switch.
				if (committedRow) {
					lastSideBucket[committedRow.participant_id] = sideBucket(committedRow.side);
					// Checkpoint remediation (44-09, corrected): sideGateConfirmed is
					// otherwise pure client memory that resets to "locked" on every
					// page load, even for a row explicitly confirmed in a past
					// session — the toggle then had to fight the fields below it for
					// which side to display (see sideToggle's comment). Seed it true
					// from unambiguous server-side evidence a side was already dealt
					// with: a specific advocate role was saved (side !== 'UNKNOWN'),
					// or a person is already committed (proves the full resolve flow,
					// which requires a side, already ran for this row). A row saved
					// as bare generic Advocate with no role picked yet (side stays
					// 'UNKNOWN', the same value a truly untouched row has) is
					// genuinely indistinguishable from untouched — it re-locks after
					// a refresh, which costs one extra click, rather than guessing
					// and risking a misleading always-unlocked dropdown.
					if (
						committedRow.side !== 'UNKNOWN' ||
						committedRow.person_id != null
					) {
						sideGateConfirmed[committedRow.participant_id] = true;
					}
				}
			}
		}
	});

	// Code review finding CR-01/CR-02 (44-09, confirmed real bug): lastDescriptorValue
	// and lastAdvocateRole were only ever WRITTEN from their own input/select's
	// oninput/onchange handler, never seeded from the row's already-committed server
	// value. A row that already has a correct descriptor or specific advocate role
	// from a PRIOR session — one the operator never retypes/repicks in the current
	// session — silently lost it on an Advocate->Bench->Advocate round trip: the
	// first toggle's own save triggers a page reload (submitRow -> ?/saveResolveRow
	// -> use:enhance's update() -> invalidateAll), after which row.descriptor is
	// null (RESOLVE-13, hidden while BENCH) and row.side is 'BENCH' — so by the time
	// the second toggle restores Advocate, both fallbacks (`row.descriptor`,
	// `specificAdvocateRole(row.side)`) read the POST-TOGGLE server state, not the
	// pre-toggle value that needed preserving. Unlike the gated seeding effect above
	// (rowMatchStates/lastSideBucket/sideGateConfirmed, isPaused-only), this must run
	// for every editable row regardless of pause state — the toggle/descriptor input
	// are not gated on isPaused. Seeds at most once per participant (never
	// overwrites), so a real in-session edit via the input/select always wins.
	$effect(() => {
		for (const row of mergedRows) {
			if (lastDescriptorValue[row.participant_id] === undefined && row.descriptor != null) {
				lastDescriptorValue[row.participant_id] = row.descriptor;
			}
			if (lastAdvocateRole[row.participant_id] === undefined) {
				const specific = specificAdvocateRole(row.side);
				if (specific) {
					lastAdvocateRole[row.participant_id] = specific;
				}
			}
		}
	});

	// Plan 44-09 tenure-preview follow-up: fetch a live preview for every BENCH
	// row that has an uncommitted person pick — covers a manual dropdown pick
	// (handleSelectPerson), a freshly created bench person
	// (handlePersonCreated), and a pipeline auto-match the seeding effect
	// above pre-filled but the operator has not yet reached the batch commit
	// for. Runs once per distinct (participant, personId) pair via the
	// benchRolePreviewFetched cache — this effect itself re-runs whenever any
	// row's rowMatchStates entry changes, which would otherwise re-fetch every
	// still-unchanged row on every unrelated edit.
	$effect(() => {
		for (const row of mergedRows) {
			if (effectiveSide(row) !== 'BENCH') continue;
			if (row.person_id != null) continue; // already committed; the service's own value is authoritative
			const personId = rowMatchStates[row.raw_speaker_label]?.personId;
			if (personId == null) continue;
			const key = `${row.participant_id}:${personId}`;
			if (benchRolePreviewFetched[key]) continue;
			benchRolePreviewFetched[key] = true;
			fetchBenchRolePreview(row.participant_id, personId);
		}
	});

	let allDispositioned = $derived.by(() => {
		if (!isPaused) return false;
		const disc = discrepancies ?? [];
		// WR-04: an empty discrepancy list while paused means every speaker was
		// already resolved (auto-match or inline saveResolveRow) — there is
		// nothing left for the operator to review, so the primary CTA must
		// still render rather than being permanently stuck behind a vacuously-
		// false check.
		if (disc.length === 0) return true;
		// RESOLVE-08: the confirm/correct state machine is gone — the gate is a
		// single personId predicate now.
		return disc.every((d) => rowMatchStates[d.raw_speaker_label]?.personId != null);
	});

	// Plan 44-09 (RESOLVE-15): reviewProgress and allDispositioned must read
	// the same personId predicate — the header count and the Continue gate
	// both derive their N from this one value, so a header saying nothing
	// remains can never coexist with a still-disabled button, or the reverse.
	let reviewProgress = $derived.by(() => {
		const disc = discrepancies ?? [];
		const total = disc.length;
		const remaining = disc.filter(
			(d) => rowMatchStates[d.raw_speaker_label]?.personId == null,
		).length;
		return { total, remaining };
	});

	let matchesJson = $derived.by(() => {
		const disc = discrepancies ?? [];
		const arr = disc
			.map((d) => {
				const s = rowMatchStates[d.raw_speaker_label];
				if (!s || s.personId == null) return null;
				return { raw_speaker_label: d.raw_speaker_label, person_id: s.personId };
			})
			.filter(Boolean);
		return JSON.stringify(arr);
	});

	let continueSubmitting = $state(false);

	function getRowCandidates(discrepancy: Discrepancy, label: string): Candidate[] {
		const extra = rowMatchStates[label]?.extraCandidates ?? [];
		const all = [...(people ?? []), ...discrepancy.candidates, ...extra];
		const seen = new Set<number>();
		return all.filter((c) => {
			if (seen.has(c.id)) return false;
			seen.add(c.id);
			return true;
		});
	}

	// Phase 44 Plan 07 (RESOLVE-09): scope the merged candidate list to the row's
	// currently-selected side. Fail-open, not fail-closed: a candidate whose
	// is_justice is unknown (null/undefined) — present only in a stale
	// discrepancies snapshot and absent from the live people list — is kept on
	// BOTH sides rather than hidden from both, because an over-inclusive list
	// costs the operator one extra glance while an under-inclusive one makes a
	// real person unreachable and pushes them toward creating a duplicate
	// record. Filters on is_justice only — never role_name or SIDE_LABEL — the
	// same field the People directory's own Bench/Advocate tabs use.
	function sideScopedCandidates(
		discrepancy: Discrepancy,
		label: string,
		side: string,
		gated: boolean,
	): Candidate[] {
		const merged = getRowCandidates(discrepancy, label);
		if (gated) {
			// No side has been chosen yet — the control is inert in this state, so
			// filtering it would be filtering nothing.
			return merged;
		}
		const wantBench = side === 'BENCH';
		return merged.filter((c) => c.is_justice == null || c.is_justice === wantBench);
	}

	// RESOLVE-08/T-44-17: the review-set predicate — only rows with an active discrepancy
	// entry (and therefore a wire path through matchesJson/?/resolve) get an editable
	// dropdown; every other row (already resolved outside the discrepancy list, or the
	// read-only card) keeps the plain name display via personDisplay.
	function personControlEditable(row: MergedRow, s: RowMatchState | undefined): boolean {
		return interactive && row.discrepancy != null && s != null;
	}

	// Plan 44-09 (RESOLVE-16): the row cue tag predicate — a row outside the
	// review set, and every row on the read-only card, has nothing to review
	// and no suggestion to disclose, so it carries no tag. The needs-attention
	// case is checked first so a suggested-but-still-gated row reads as
	// needing the operator, not as already handled — that ordering is what
	// makes the two tags mutually exclusive. An operator-chosen match falls
	// through to the final `null`: labelling it as auto-matched would claim
	// the machine identified a person when a human did (T-44-35). No explicit
	// return-type annotation: TypeScript infers the two-literal union from
	// the return statements below, so each tag string is written exactly
	// once in this file rather than twice (once in a union annotation, once
	// on its own return).
	function rowCueTag(row: MergedRow, s: RowMatchState | undefined) {
		if (!interactive) return null;
		if (!row.discrepancy) return null;
		if (!s) return null;
		if (s.personId == null || needsSideGate(row)) return 'NEEDS YOU';
		if (row.discrepancy.auto_match_id != null && s.personId === row.discrepancy.auto_match_id) return 'AUTO-MATCHED';
		// Task 4 checkpoint remediation (44-09, RESOLVE-16 supersession): the
		// operator asked mid-review for a third, explicit tag distinguishing
		// "a human decided this" from "the machine suggested this and it was
		// left untouched" — provenance disclosure, not derived insight. Any row
		// that reaches this branch already has a chosen person (s.personId is
		// non-null per the check above) and is not side-gated and is not the
		// untouched auto-match, so it is, by construction, an operator pick.
		return 'MANUALLY MATCHED';
	}

	function handleSelectPerson(label: string, personId: number) {
		const s = rowMatchStates[label];
		if (!s) return;
		s.personId = personId;
	}

	function handlePersonCreated(label: string, participantId: number, person: Candidate, side: string) {
		const s = rowMatchStates[label];
		if (!s) return;
		// Phase 44 Plan 07 (RESOLVE-09): enrich the created candidate with the side
		// already known at creation time, so the newly created person appears
		// immediately in the filtered list for the side they were created on — no
		// refetch, no backend schema change, since `side` is already this handler's
		// own parameter.
		const enriched: Candidate = { ...person, is_justice: side === 'BENCH' };
		s.extraCandidates = [...s.extraCandidates, enriched];
		s.personId = enriched.id;
		// Mirrors the existing-person pick path in personDropdown (click/Enter
		// handlers set s.comboQuery before calling handleSelectPerson) — without
		// this, the row is internally resolved but the Resolved As box still
		// shows whatever text was typed (or blank) before the popover opened.
		s.comboQuery = enriched.full_name;
		// Task 4 checkpoint remediation (item 6): record the baseline bucket for
		// the side the person was just created on, so a later genuine switch
		// away from it is still detected (clearPersonOnSideBucketChange is not
		// called here — this action creates and selects the person for `side`
		// on purpose, it must not immediately clear its own selection).
		lastSideBucket[participantId] = sideBucket(side);
		pendingSideOverrides[participantId] = side;
		submitRow(participantId);
	}

	// Svelte action — close the combobox dropdown on outside click.
	function comboOutsideClick(container: HTMLElement, rowKey: string) {
		function handleClick(e: MouseEvent) {
			const target = e.target as Node;
			if (container.contains(target)) return;
			// CreatePersonPopover (rendered inside this combobox's own open
			// dropdown) uses bits-ui's Popover.Portal, which mounts its content
			// to document.body by default (bits-ui's resolvePortalToProp default,
			// confirmed in node_modules/bits-ui/dist/.../prop-resolvers.js) — NOT
			// as a DOM descendant of `container`. Without this guard, any click
			// inside that nested popover (the name field, the Bench/Advocate
			// toggle, the Create person button itself) reads as "outside the
			// combobox", closing `comboOpen` — which unmounts the entire
			// `{#if s.comboOpen}` block, destroying the create-person popover
			// (and its in-flight submit) mid-interaction.
			if (target instanceof Element && target.closest('[data-popover-content]')) return;
			const s = rowMatchStates[rowKey];
			if (s) {
				s.comboOpen = false;
			}
		}
		// Code review finding WR-02: a Svelte action's own body already runs once
		// per node mount and its returned destroy() already runs once per unmount —
		// wrapping the listener in a nested $effect (removed here) registered a
		// second, redundant teardown path for the same listener. Harmless (removing
		// an already-removed listener is a no-op) but dead code that could hide a
		// real leak if only one path were edited in the future.
		document.addEventListener('click', handleClick);
		return {
			destroy() {
				document.removeEventListener('click', handleClick);
			},
		};
	}

	function getInitials(name: string): string {
		const parts = name.trim().split(/\s+/).filter(Boolean);
		if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
		if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
		return '?';
	}
</script>

{#snippet rawLabelBadge(label: string)}
	<span
		style="
			background-color: var(--color-bg);
			border: 1px solid var(--color-border);
			border-radius: 4px;
			padding: var(--space-xs) 10px;
			font-size: var(--font-size-caption);
			font-weight: var(--font-weight-regular);
			color: var(--color-text-primary);
			text-transform: uppercase;
			letter-spacing: 0.02em;
			display: inline-block;
			white-space: normal;
		"
	>
		{label}
	</span>
{/snippet}

{#snippet descriptorCell(row: MergedRow, side: string, rowEditable: boolean, saving: boolean, sourcePrefix: string)}
	{#if side === 'BENCH'}
		<span style="color: var(--color-text-secondary);">–</span>
	{:else if rowEditable}
		<input
			form={rowFormId(row.participant_id)}
			name="descriptor"
			type="text"
			value={lastDescriptorValue[row.participant_id] ?? row.descriptor ?? ''}
			oninput={(e) => {
				lastDescriptorValue[row.participant_id] = (e.target as HTMLInputElement).value;
			}}
			onblur={() => submitRow(row.participant_id)}
			placeholder="e.g. Attorney, Location, or Affiliation"
			disabled={saving}
			style="
				background-color: var(--color-bg);
				border: 1px solid var(--color-border);
				border-radius: 6px;
				padding: var(--space-sm) var(--space-md);
				font-size: var(--font-size-body);
				color: var(--color-text-primary);
				min-height: var(--touch-target-dense);
				width: 100%;
				box-sizing: border-box;
				overflow: hidden;
				text-overflow: ellipsis;
				white-space: nowrap;
			"
		/>
	{:else}
		<span>{row.descriptor ?? '–'}</span>
	{/if}
	<!-- Phase 44 (RESOLVE-05, D-08/D-09): supersedes the Phase 38 two-line stacked
	     hint (the old call passed a medium confidence band and mirrored the hint
	     value into the raw prop) for this file only — the UI-SPEC locks Descriptor
	     to the same single-line "Imported: …" treatment as the other 3 hinted
	     columns.
	     Plan 44-08 (RESOLVE-13): suppressed on bench rows, wrapped rather than
	     deleted. The shared hint component's `{#if isStacked}` branch renders
	     its prefix span and copy button unconditionally, even when value is
	     null — there is no early-return for a null value inside that shared
	     component — so suppressing the hint has to be a call-site condition, not
	     a component change. This is a render condition only: the stored
	     ArgumentParticipant.descriptor is preserved untouched by 44-06's
	     write-path fix; nothing here clears or blanks the value, it is simply
	     not rendered while side is BENCH. -->
	{#if side !== 'BENCH'}
		<div style="margin-top: var(--space-sm);">
			<CopyableExtractedValue
				value={row.descriptor_hint}
				copyLabel="Copy descriptor"
				prefixLabel={sourcePrefix}
				raw={null}
			/>
		</div>
	{/if}
{/snippet}

{#snippet sideToggle(row: MergedRow, side: string, gated: boolean, rowEditable: boolean, saving: boolean)}
	<!-- Checkpoint remediation (44-09, corrected): the highlight IS gated —
	     removing that check (a prior attempt) made an untouched row's UNKNOWN
	     side read as "Advocate active" (side !== 'BENCH'), so the toggle
	     looked decided while the person dropdown correctly stayed locked
	     behind an explicit click. The real bug was that `gated` itself
	     (needsSideGate/sideGateConfirmed) was untrustworthy on a fresh page
	     load — see the seeding effect below, which now seeds
	     sideGateConfirmed from unambiguous server-side evidence of a prior
	     confirmation, so `gated` is correct here without reintroducing the
	     refresh-disagreement bug this round started from. -->
	{@const benchActive = !gated && side === 'BENCH'}
	{@const advocateActive = !gated && side !== 'BENCH'}
	{@const disabled = !rowEditable || saving}
	<div
		role="group"
		aria-label={`Bench or Advocate for ${row.raw_speaker_label}`}
		style="
			display: inline-flex;
			border: 1px solid var(--color-border);
			border-radius: 6px;
			overflow: hidden;
			min-height: var(--touch-target-dense);
		"
	>
		<button
			type="button"
			aria-pressed={benchActive}
			disabled={disabled}
			onclick={() => toggleSide(row, 'BENCH')}
			style="
				font-size: var(--font-size-caption);
				padding: 6px 14px;
				border: none;
				border-right: 1px solid var(--color-border);
				line-height: 1.4;
				background-color: {benchActive ? 'var(--color-status-published)' : 'transparent'};
				color: {benchActive ? 'var(--color-bg)' : 'var(--color-text-secondary)'};
				font-weight: {benchActive ? 600 : 400};
				cursor: {disabled ? 'default' : 'pointer'};
				opacity: {disabled ? 0.6 : 1};
			"
		>Bench</button>
		<button
			type="button"
			aria-pressed={advocateActive}
			disabled={disabled}
			onclick={() => toggleSide(row, 'ADVOCATE')}
			style="
				font-size: var(--font-size-caption);
				padding: 6px 14px;
				border: none;
				line-height: 1.4;
				background-color: {advocateActive ? 'var(--color-accent)' : 'transparent'};
				color: {advocateActive ? 'var(--color-bg)' : 'var(--color-text-secondary)'};
				font-weight: {advocateActive ? 600 : 400};
				cursor: {disabled ? 'default' : 'pointer'};
				opacity: {disabled ? 0.6 : 1};
			"
		>Advocate</button>
	</div>
{/snippet}

{#snippet argumentRoleCell(row: MergedRow, side: string, gated: boolean, rowEditable: boolean, saving: boolean)}
	{@const benchState = benchRoleState(row, side)}
	<!-- Plan 44-09 tenure-preview follow-up: row.bench_role/row.person_edit_href
	     stay null until the batch ?/resolve commit; while benchState reads
	     'calculated'/'missing-tenure' from an uncommitted preview (see
	     benchRoleState above), these two fall back to the preview's own
	     bench_role and to the not-yet-committed personId respectively. Once
	     row.person_id is non-null (committed), row.bench_role/person_edit_href
	     are always the service's own value and these fallbacks are unused. -->
	{@const previewedBenchRole = benchRolePreview[row.participant_id]?.bench_role}
	{@const previewedPersonId = rowMatchStates[row.raw_speaker_label]?.personId}
	{#if benchState === 'unresolved'}
		<!-- Plan 44-08 (RESOLVE-14): no person resolved yet, so the role cannot be
		     computed at all — this is checked before the calculated branch below
		     because the service reports missing_tenure=false for an unresolved
		     bench row, which would otherwise fall into the empty locked box. No
		     bordered box, no lock icon, no en dash, and no hint line beneath. -->
		<span style="font-size: var(--font-size-caption); color: var(--color-text-secondary);">(resolve person first)</span>
	{:else if benchState === 'calculated'}
		<!-- RESOLVE-06 lock affordance: a resolved bench row with valid tenure is
		     never editable here — the role is fully derived from court_tenures. -->
		<div
			style="
				display: inline-flex;
				align-items: center;
				gap: 6px;
				background-color: var(--color-surface);
				border: 1px solid var(--color-border);
				border-radius: 6px;
				padding: var(--space-sm) var(--space-md);
				min-height: var(--touch-target-dense);
				box-sizing: border-box;
			"
		>
			<svg
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				width="14"
				height="14"
				aria-hidden="true"
				style="color: var(--color-text-secondary); flex-shrink: 0;"
			>
				<rect x="5" y="11" width="14" height="9" rx="2"></rect>
				<path d="M8 11V7a4 4 0 0 1 8 0v4"></path>
			</svg>
			<span style="font-size: var(--font-size-body); color: var(--color-text-primary);">{row.bench_role ?? previewedBenchRole ?? row.argument_role}</span>
			<span style="position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%);">
				Set from tenure, not editable
			</span>
		</div>
		<!-- Plan 44-08 (RESOLVE-12): the role was never an ingested value, so this
		     is not an "Imported:"/"Extracted:" hint — it says what is actually
		     true about the value. -->
		<div style="margin-top: var(--space-sm);">
			<span style="font-size: var(--font-size-caption); color: var(--color-text-secondary);">Calculated from tenure</span>
		</div>
	{:else if benchState === 'missing-tenure'}
		<!-- Missing-tenure warning — preserved verbatim (RESOLVE-06): NO lock icon,
		     NO bordered box, so this state shares no markup with the locked state
		     above and reads as a real data gap, not a deliberate system value. -->
		<span style="color: var(--color-status-warning); font-size: var(--font-size-caption);">⚠ Missing tenure</span>
		<!-- Plan 44-08 (RESOLVE-12): a tenure gap must never read as a derived
		     value, so this shares no wording with the calculated branch above. -->
		<div style="margin-top: var(--space-sm);">
			<span style="font-size: var(--font-size-caption); color: var(--color-text-secondary);">Tenure not found</span>
		</div>
		{#if row.person_edit_href || previewedPersonId != null}
			<!-- Plan 44-08 (RESOLVE-11): opens in a new tab so the operator can fix
			     tenure in one tab and return to this still-loaded Resolve card in
			     the other, where the role recomputes live on next read. The
			     noopener rel severs the opened tab's window.opener handle back to
			     this admin page (T-44-31, reverse tabnabbing). The arrow glyph sits
			     in its own aria-hidden span so the accessible name stays exactly
			     "Edit person", matching how the warning glyph above is handled.
			     Plan 44-09 tenure-preview follow-up: row.person_edit_href is null
			     until commit even when this branch was reached via an uncommitted
			     preview — previewedPersonId is guaranteed non-null here (benchState
			     only reads 'missing-tenure' from a preview when a personId is
			     picked), so the same /admin/people/{id} link the service would
			     construct is built client-side from a value already in hand,
			     rather than duplicating any tenure derivation. -->
			<a
				href={row.person_edit_href ?? `/admin/people/${previewedPersonId}`}
				target="_blank"
				rel="noopener"
				style="margin-left: var(--space-sm); font-size: var(--font-size-caption); color: var(--color-accent); text-decoration: underline;"
			>Edit person<span aria-hidden="true"> ↗</span></a>
		{/if}
	{:else if rowEditable}
		<!-- RESOLVE-03 writable dropdown — covers advocate rows and gated rows
		     (D-07 delta #1). No name/form attribute: the hidden `side` input added
		     in Task 1 is the sole submitting element. -->
		{@const displayValue = side === 'ADVOCATE' ? 'UNKNOWN' : side}
		<select
			value={displayValue}
			disabled={saving}
			aria-label={`Argument role for ${row.raw_speaker_label}`}
			onchange={(e) => chooseArgumentRole(row, (e.target as HTMLSelectElement).value)}
			style="
				background-color: var(--color-bg);
				border: 1px solid var(--color-border);
				border-radius: 6px;
				padding: var(--space-sm) var(--space-md);
				font-size: var(--font-size-body);
				color: var(--color-text-primary);
				min-height: var(--touch-target-dense);
				width: 100%;
				box-sizing: border-box;
				cursor: pointer;
			"
		>
			<option value="UNKNOWN">Select case role</option>
			<option value="PETITIONER">{SIDE_LABEL.PETITIONER}</option>
			<option value="RESPONDENT">{SIDE_LABEL.RESPONDENT}</option>
			<option value="AMICUS">{SIDE_LABEL.AMICUS}</option>
		</select>
	{:else}
		<span style="font-size: var(--font-size-body); color: var(--color-text-primary);">{row.argument_role ?? '—'}</span>
	{/if}
{/snippet}

<!-- Phase 44 Plan 05 (RESOLVE-08): the single always-rendered person-matching entry
     point — replaces the retired Change link / Select-person link / confirm-correct
     combobox branches. Renders personDisplay for rows outside the review set (no
     discrepancy entry, no persistence path — T-44-17); otherwise renders the
     combobox unconditionally, gated (never removed from the DOM) via disabled +
     aria-disabled when the row's side has not yet been chosen (T-44-18, Pitfall 4). -->
{#snippet personDropdown(row: MergedRow, label: string, s: RowMatchState | undefined, gated: boolean, side: string)}
	{#if !personControlEditable(row, s)}
		{@render personDisplay(row.full_name, row.photo_url, row.argument_role)}
	{:else}
		{@const comboId = `listbox-${label.replace(/\s+/g, '-')}`}
		{@const candidates = sideScopedCandidates(row.discrepancy!, label, side, gated)}
		{@const filteredCandidates = candidates.filter((c) => {
			const text = c.role_name ? `${c.full_name} ${c.role_name}` : c.full_name;
			return text.toLowerCase().includes((s!.comboQuery ?? '').toLowerCase());
		})}
		<div style="position: relative; width: 100%;" use:comboOutsideClick={label}>
			<input
				type="text"
				role="combobox"
				aria-expanded={s!.comboOpen}
				aria-haspopup="listbox"
				aria-controls={comboId}
				aria-autocomplete="list"
				aria-label="Search for speaker"
				placeholder={gated
					? 'Select person…'
					: side === 'BENCH'
						? 'Select bench…'
						: 'Select advocate…'}
				value={s!.comboQuery}
				disabled={gated}
				aria-disabled={gated ? 'true' : 'false'}
				style="
					background-color: var(--color-bg);
					border: 1px solid var(--color-accent);
					border-radius: 6px;
					padding: 6px var(--space-2xl) 6px 10px;
					font-size: var(--font-size-body);
					color: var(--color-text-primary);
					width: 100%;
					box-sizing: border-box;
					opacity: {gated ? 0.6 : 1};
					cursor: {gated ? 'default' : 'text'};
				"
				onfocus={() => {
					s!.comboOpen = true;
					s!.comboHighlight = -1;
				}}
				oninput={(e) => {
					s!.comboQuery = (e.target as HTMLInputElement).value;
					s!.comboOpen = true;
					s!.comboHighlight = -1;
				}}
				onkeydown={(e) => {
					if (e.key === 'ArrowDown') {
						e.preventDefault();
						s!.comboHighlight = Math.min(s!.comboHighlight + 1, filteredCandidates.length - 1);
					} else if (e.key === 'ArrowUp') {
						e.preventDefault();
						s!.comboHighlight = Math.max(s!.comboHighlight - 1, -1);
					} else if (e.key === 'Enter') {
						e.preventDefault();
						if (s!.comboHighlight >= 0 && s!.comboHighlight < filteredCandidates.length) {
							const picked = filteredCandidates[s!.comboHighlight];
							s!.comboQuery = picked.full_name;
							handleSelectPerson(label, picked.id);
							s!.comboOpen = false;
						}
					} else if (e.key === 'Escape') {
						s!.comboQuery = '';
						s!.comboOpen = false;
						s!.comboHighlight = -1;
					}
				}}
			/>
			<!-- Task 3 checkpoint remediation: a decorative chevron so the always-
			     rendered input reads as a combobox with a popup, not a plain text
			     box — the operator's checkpoint feedback flagged the missing
			     affordance against Figma node 4205:81. Purely visual: it carries no
			     click handler of its own and is aria-hidden so it never enters the
			     input's accessible name. -->
			<svg
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				width="16"
				height="16"
				aria-hidden="true"
				style="
					position: absolute;
					right: 10px;
					top: 50%;
					transform: translateY(-50%);
					color: var(--color-text-secondary);
					pointer-events: none;
				"
			>
				<polyline points="6 9 12 15 18 9"></polyline>
			</svg>
			{#if gated}
				<span style="position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%);">
					Choose Bench or Advocate before selecting a person.
				</span>
			{/if}
			{#if s!.comboOpen}
				<div
					style="
						position: absolute;
						top: 100%;
						left: 0;
						width: 100%;
						margin: var(--space-xs) 0 0 0;
						background-color: var(--color-surface);
						border: 1px solid var(--color-border);
						border-radius: 6px;
						z-index: 10;
					"
				>
					<ul
						id={comboId}
						role="listbox"
						style="
							padding: var(--space-xs) 0;
							margin: 0;
							max-height: 240px;
							overflow-y: auto;
							list-style: none;
						"
					>
						{#each filteredCandidates as candidate, idx (candidate.id)}
							<li
								role="option"
								aria-selected={false}
								style="
									padding: var(--space-sm) var(--space-md);
									font-size: var(--font-size-body);
									color: var(--color-text-primary);
									cursor: pointer;
									background-color: {s!.comboHighlight === idx ? 'var(--color-border)' : 'var(--color-surface)'};
								"
								onmouseenter={() => {
									s!.comboHighlight = idx;
								}}
								onclick={() => {
									s!.comboQuery = candidate.full_name;
									handleSelectPerson(label, candidate.id);
									s!.comboOpen = false;
								}}
							>
								{candidate.full_name}{#if candidate.role_name}<span style="font-size: var(--font-size-caption); color: var(--color-text-secondary); margin-left: var(--space-xs);">({candidate.role_name})</span>{/if}
								{#if row.discrepancy?.auto_match_id === candidate.id}
									<span style="font-size: var(--font-size-caption); color: var(--color-accent); text-transform: uppercase; letter-spacing: 0.04em; margin-left: 6px;">Suggested</span>
								{/if}
							</li>
						{/each}
					</ul>
					<!-- Task 3 checkpoint remediation: create-person now lives inside
					     the open popup (Figma 4205:81 shows it as part of the
					     combobox's own popup affordance), not as a standalone element
					     that was always visible beneath the input regardless of
					     whether the popup was open. -->
					<div style="border-top: 1px solid var(--color-border); padding: var(--space-sm);">
						<CreatePersonPopover
							rawSpeakerLabel={label}
							triggerLabel={side === 'BENCH' ? 'Create new bench person' : 'Create new advocate'}
							defaultAdvocateSide={side !== 'BENCH' ? side : 'UNKNOWN'}
							initialSide={side === 'BENCH' ? 'BENCH' : 'ADVOCATE'}
							onCreated={(person, createdSide) =>
								handlePersonCreated(label, row.participant_id, person, createdSide)}
						/>
					</div>
				</div>
			{/if}
		</div>
	{/if}
{/snippet}

{#snippet personDisplay(fullName: string | null, photoUrl: string | null, roleLabel: string | null)}
	{#if fullName}
		<span style="display: inline-flex; align-items: center; gap: var(--space-sm);">
			<span
				style="
					width: 28px;
					height: 28px;
					border-radius: 50%;
					background-color: var(--color-border);
					display: inline-flex;
					align-items: center;
					justify-content: center;
					font-size: var(--font-size-caption);
					color: var(--color-text-primary);
					overflow: hidden;
					flex-shrink: 0;
				"
			>
				{#if photoUrl}
					<img src={photoUrl} alt="" style="width: 100%; height: 100%; object-fit: cover;" />
				{:else}
					{getInitials(fullName)}
				{/if}
			</span>
			<span style="font-size: var(--font-size-body); color: var(--color-text-primary);">
				{fullName}{#if roleLabel}<span style="color: var(--color-text-secondary); font-size: var(--font-size-caption); margin-left: var(--space-xs);">({roleLabel})</span>{/if}
			</span>
		</span>
	{:else}
		<span style="color: var(--color-text-secondary);">—</span>
	{/if}
{/snippet}

<div
	style="
		background-color: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: 8px;
		padding: var(--space-xl);
		margin-bottom: var(--space-xl);
	"
>
	<!-- Task 4 checkpoint remediation (44-09, item 4, confirmed via Figma
	     node 4207:116): the heading and the progress indicator share one
	     flex row, heading left, pill right. -->
	<div style="display: flex; align-items: center; justify-content: space-between; gap: var(--space-md); margin-bottom: var(--space-lg);">
		<h2 style="font-size: var(--font-size-heading); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); margin: 0; line-height: 1.2;">
			Resolve
		</h2>

		<!-- Plan 44-09 (RESOLVE-15): a persistent progress line — visible before,
		     during and after the operator works, never a transient message.
		     Renders only while the job is paused and the review set is
		     non-empty; an empty review set has nothing to count (delta #2 above).
		     Task 4 checkpoint remediation: restyled as a pill with a
		     status-colored dot (amber while rows remain, green once all are
		     reviewed) rather than a bare paragraph. -->
		{#if isPaused && reviewProgress.total > 0}
			<div
				id="resolve-progress"
				style="
					display: inline-flex;
					align-items: center;
					gap: var(--space-sm);
					background-color: var(--color-bg);
					border: 1px solid var(--color-border);
					border-radius: 12px;
					padding: var(--space-xs) var(--space-md) var(--space-xs) 10px;
				"
			>
				<span
					aria-hidden="true"
					style="
						display: inline-block;
						width: 6px;
						height: 6px;
						border-radius: 50%;
						background-color: {reviewProgress.remaining > 0 ? 'var(--color-status-warning)' : 'var(--color-status-published)'};
					"
				></span>
				<span style="color: var(--color-text-primary); font-size: var(--font-size-caption); font-weight: var(--font-weight-semibold);">
					{reviewProgress.remaining > 0
						? `${reviewProgress.remaining} of ${reviewProgress.total} speakers still need review`
						: `All ${reviewProgress.total} speakers reviewed`}
				</span>
			</div>
		{/if}
	</div>

	{#if peopleLoadError}
		<p role="alert" style="margin-bottom: var(--space-md); font-size: var(--font-size-caption); color: var(--color-status-warning); font-family: monospace;">
			Warning: could not load people list — typeahead may be incomplete. ({peopleLoadError})
		</p>
	{/if}

	<!-- Hidden per-row save forms — inputs elsewhere in the table reference these via form="..." -->
	{#each mergedRows as row (row.participant_id)}
		<form
			id={rowFormId(row.participant_id)}
			bind:this={formRefs[row.participant_id]}
			method="POST"
			action="?/saveResolveRow"
			style="display: none;"
			use:enhance={() => {
				saveState[row.participant_id] = { saving: true, error: null };
				return async ({ result, update }) => {
					if (result.type === 'failure') {
						saveState[row.participant_id] = {
							saving: false,
							error: (result.data as { resolveRowError?: string })?.resolveRowError ?? 'Could not save.',
						};
					} else {
						saveState[row.participant_id] = { saving: false, error: null };
						await update({ reset: false });
					}
				};
			}}
		>
			<input type="hidden" name="participant_id" value={row.participant_id} />
			<!-- Task 1 (RESOLVE-02, Phase 27 CR-01/CR-02): the ONLY element in this form
			     carrying the `side` field name. The segmented toggle and the Argument
			     Role select (Task 2) are pure state mutators with no `name`/`form` of
			     their own; this always-present hidden input is what actually submits. -->
			<input type="hidden" name="side" value={effectiveSide(row)} />
		</form>
	{/each}

	<!-- Responsive contract: horizontally scrollable wrapper avoids overflow/overlap at 860px (T-25-13) -->
	<div style="overflow-x: auto;">
		<table style="width: 100%; border-collapse: collapse; min-width: 720px;">
			<thead>
				<tr>
					<th scope="col" style="font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); border-bottom: 1px solid var(--color-border); padding: var(--space-sm) 0; padding-right: var(--space-md); text-align: left; text-transform: uppercase; letter-spacing: 0.04em;">Raw Label</th>
					<th scope="col" style="font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); border-bottom: 1px solid var(--color-border); padding: var(--space-sm) 0; padding-right: var(--space-md); text-align: left; text-transform: uppercase; letter-spacing: 0.04em;">Resolved As</th>
					<th scope="col" style="font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); border-bottom: 1px solid var(--color-border); padding: var(--space-sm) 0; padding-right: var(--space-md); text-align: left; text-transform: uppercase; letter-spacing: 0.04em;">Argument Role</th>
					<th scope="col" style="font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); border-bottom: 1px solid var(--color-border); padding: var(--space-sm) 0; text-align: left; text-transform: uppercase; letter-spacing: 0.04em;">Descriptor</th>
				</tr>
			</thead>
			<tbody>
				{#each mergedRows as row (row.participant_id)}
					{@const label = row.raw_speaker_label}
					{@const s = rowMatchStates[label]}
					{@const gated = needsSideGate(row)}
					{@const side = effectiveSide(row)}
					{@const rowEditable = interactive && row.editable}
					{@const cueTag = rowCueTag(row, s)}
					<!-- Mirrors rowCueTag's own branch conditions (reusing the already-
					     declared `gated`), so the tag's color can be picked without a
					     second comparison against any of rowCueTag's three return
					     values — those must each appear exactly once in this file.
					     Third state added by Task 4 checkpoint remediation (44-09,
					     RESOLVE-16 supersession): a truthy cueTag that is neither the
					     needs-attention nor the auto-matched case is, by construction,
					     the manually-matched case — no separate boolean needed. -->
					{@const cueTagIsWarning = s?.personId == null || gated}
					{@const cueTagIsAutoMatched = row.discrepancy?.auto_match_id != null && s?.personId === row.discrepancy?.auto_match_id}

					<tr>
						<!-- Column 1: Raw Label -->
						<td style="font-size: var(--font-size-body); color: var(--color-text-primary); border-bottom: 1px solid var(--color-border); padding: var(--space-md) 0; padding-right: var(--space-md);">
							{@render rawLabelBadge(row.raw_speaker_label)}
						</td>

						<!-- Column 2: Resolved As — the Bench/Advocate toggle and the person control
						     are stacked in this single cell (RESOLVE-07); the person control is a
						     single always-rendered dropdown, never a click-to-reveal link (RESOLVE-08). -->
						<td style="font-size: var(--font-size-body); color: var(--color-text-primary); border-bottom: 1px solid var(--color-border); padding: var(--space-md) 0; padding-right: var(--space-md);">
							<!-- Task 4 checkpoint remediation (44-09, items 2 and 5, confirmed via
							     Figma nodes 4183:23/4183:25/4205:81/4205:111): corrected order is
							     (1) toggle, (2) person control, (3) the tag, (4) one combined hint
							     line — the tag used to render above the toggle; it now renders after
							     the person control and before the hint. The Bench/Advocate hint and
							     the Name hint (previously two separate call sites) are merged into
							     one combined hint below. -->
							{@render sideToggle(row, side, gated, rowEditable, saveState[row.participant_id]?.saving === true)}
							{#if saveState[row.participant_id]?.error}
								<p role="alert" style="margin: var(--space-sm) 0 0 0; font-size: var(--font-size-caption); color: var(--color-destructive);">
									{saveState[row.participant_id]?.error}
								</p>
							{/if}
							<div style="margin-top: var(--space-md);">
								{@render personDropdown(row, label, s, gated, side)}
							</div>
							<!-- Plan 44-09 (RESOLVE-16): the row cue tag — a pill (border only, no
							     background fill), per Figma nodes 4183:23/4183:25/4205:111. The
							     auto-matched state uses the approved Success/Bench-active token
							     (--color-status-published, UI-SPEC "Success (Bench-active)" row) — the prior plain-
							     text treatment wrongly used the muted token (--color-text-secondary) for this
							     state; the needs-attention state keeps the warning token
							     (--color-status-warning).
							     Third state (Task 4 checkpoint remediation, RESOLVE-16
							     supersession): the manually-matched tag — a row where the operator
							     picked the person themselves, as opposed to an untouched machine
							     suggestion (the auto-matched tag) or a row still awaiting input
							     (the needs-attention tag). This deliberately reverses 44-05's
							     original rule that an operator-picked row "carries neither tag" —
							     the operator determined in testing that provenance ("a human
							     decided this" vs. "the machine suggested this") is itself worth
							     disclosing, not
							     omitting. Uses the muted token (--color-text-secondary, same token used
							     elsewhere for neutral/non-signal text) since this state is neither
							     a warning nor a success signal — the accent token is reserved for
							     interactive elements per UI-SPEC. -->
							{#if cueTag}
								<span
									style="
										display: inline-block;
										margin-top: var(--space-sm);
										border: 1px solid {cueTagIsWarning ? 'var(--color-status-warning)' : cueTagIsAutoMatched ? 'var(--color-status-published)' : 'var(--color-text-secondary)'};
										border-radius: 4px;
										padding: 2px var(--space-sm);
										font-size: var(--font-size-caption);
										font-weight: var(--font-weight-semibold);
										letter-spacing: 0.22px;
										color: {cueTagIsWarning ? 'var(--color-status-warning)' : cueTagIsAutoMatched ? 'var(--color-status-published)' : 'var(--color-text-secondary)'};
									"
								>{cueTag}</span>
							{/if}
							<!-- Phase 44 (RESOLVE-05, D-08/D-09), merged by Task 4 checkpoint
							     remediation (item 5): the Bench/Advocate hint and the Resolved As
							     (name) hint are now one combined line —
							     "{SideLabel} · {NameOrN/A}", or bare "N/A" while the side gate is
							     still open. -->
							<div style="margin-top: var(--space-sm);">
								<CopyableExtractedValue
									value={combinedResolvedAsHintValue(row, side, gated)}
									copyLabel="Copy resolved as"
									prefixLabel={sourcePrefix}
									raw={null}
								/>
							</div>
						</td>

						<!-- Column 3: Argument Role — bench lock / Missing tenure, or advocate dropdown -->
						<td style="font-size: var(--font-size-body); color: var(--color-text-primary); border-bottom: 1px solid var(--color-border); padding: var(--space-md) 0; padding-right: var(--space-md);">
							{@render argumentRoleCell(row, side, gated, rowEditable, saveState[row.participant_id]?.saving === true)}
							<!-- Phase 44 (RESOLVE-05, D-08/D-09): Argument Role hint — state-dependent,
							     never a flat echo of side; forks on the same side/missing_tenure/gated
							     inputs the control above it uses.
							     Plan 44-08 (RESOLVE-12): wrapped rather than deleted — the bench role
							     was never an ingested value, so it never had an ingestion-prefixed hint
							     to begin with; the three bench states above render their own copy
							     directly. Advocate rows keep this hint unchanged. -->
							{#if side !== 'BENCH'}
								<div style="margin-top: var(--space-sm);">
									<CopyableExtractedValue
										value={argumentRoleHintValue(row, side, gated)}
										copyLabel="Copy argument role"
										prefixLabel={sourcePrefix}
										raw={null}
									/>
								</div>
							{/if}
						</td>

						<!-- Column 4: Descriptor (renamed from Title, Phase 44 RESOLVE-04) — always renders -->
						<td style="font-size: var(--font-size-body); color: var(--color-text-primary); border-bottom: 1px solid var(--color-border); padding: var(--space-md) 0;">
							{@render descriptorCell(row, side, rowEditable, saveState[row.participant_id]?.saving === true, sourcePrefix)}
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>

	<!-- The primary CTA footer — moved into the Resolve card footer (PJOB-21).
	     Plan 44-09 (RESOLVE-15): the form now renders whenever the job is
	     paused, not only once every row is dispositioned — the button itself
	     carries the completeness gate via `disabled`.
	     Task 4 checkpoint remediation (44-09, item 3, confirmed via Figma
	     nodes 4207:119/4210:218): the reason is the button's own visible text
	     while disabled, replacing the label entirely — there is no longer a
	     separate reason paragraph, so it needs no aria-describedby wiring;
	     the reason is already part of the button's own accessible name. -->
	{#if isPaused}
		<form
			method="POST"
			action="?/resolve"
			use:enhance={() => {
				continueSubmitting = true;
				return async ({ result, update }) => {
					if (result.type === 'failure') {
						continueSubmitting = false;
						await update();
					} else {
						continueSubmitting = false;
						await update({ reset: false });
					}
				};
			}}
			style="margin-top: var(--space-xl);"
		>
			<input type="hidden" name="matches" value={matchesJson} />
			<button
				type="submit"
				disabled={!allDispositioned || continueSubmitting}
				style="
					width: 100%;
					min-height: var(--touch-target);
					font-size: var(--font-size-body);
					font-weight: var(--font-weight-semibold);
					color: {(reviewProgress.remaining > 0 || continueSubmitting) ? 'var(--color-text-secondary)' : 'var(--color-text-primary)'};
					background: transparent;
					border: 1px solid {(reviewProgress.remaining > 0 || continueSubmitting) ? 'var(--color-border)' : 'var(--color-accent)'};
					border-radius: 6px;
					padding: var(--space-md) var(--space-xl);
					cursor: {(reviewProgress.remaining > 0 || continueSubmitting) ? 'default' : 'pointer'};
				"
			>
				{continueSubmitting
					? 'Submitting…'
					: reviewProgress.remaining > 0
						? `Resolve ${reviewProgress.remaining} more to continue`
						: 'Continue Resolve'}
			</button>
		</form>
		{#if resolveFormError}
			<p role="alert" style="margin-top: var(--space-sm); color: var(--color-destructive); font-size: var(--font-size-caption);">
				{resolveFormError}
			</p>
		{/if}
	{/if}
</div>
