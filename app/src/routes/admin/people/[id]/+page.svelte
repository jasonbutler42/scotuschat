<script lang="ts">
	import { enhance } from '$app/forms';
	import { slide } from 'svelte/transition';
	import { tick } from 'svelte';
	import { previewFullName } from '$lib/personNames';
	import CopyableExtractedValue from '$lib/admin/CopyableExtractedValue.svelte';

	let { data, form } = $props();

	// ──────────────────────────────────────────────────────────────────────────
	// Curated President's Party options (D-16 amendment, 2026-07-09 — UAT Gap 2
	// closure). appointing_president_party is now a dropdown; appointed_by
	// stays free-text per the original D-16 decision. Every U.S. president who
	// has appointed a Justice belonged to one of these six parties, so no
	// free-text "Other" escape hatch is offered — a legacy-value guard below
	// covers any pre-existing out-of-list stored value instead.
	// ──────────────────────────────────────────────────────────────────────────

	const PARTY_OPTIONS = [
		'Federalist',
		'Democratic-Republican',
		'Democratic',
		'Whig',
		'Republican',
		'Independent',
	];

	// ──────────────────────────────────────────────────────────────────────────
	// Types
	// ──────────────────────────────────────────────────────────────────────────

	interface TenureRow {
		_key: number;
		id?: number;
		// The office field (D-01..D-17, Phase 37) replaces the old free-text
		// seat field. A valid row always holds exactly one canonical value;
		// `null` means the row is either new (see addTenureRow) or its
		// original stored value did not resolve to a canonical office and has
		// NOT been coerced (D-11).
		office: 'chief' | 'associate' | null;
		// The original stored office value ('' for blank/null) when office is
		// null, so the operator sees exactly what was recorded (D-11).
		// Cleared once a valid selection is made.
		invalidOfficeOriginal?: string | null;
		start_date: string;
		end_date: string;
		appointed_by: string;
		appointing_president_party: string;
		// '' means no reason selected (D-02: most tenures have none). Unlike
		// office, this is a genuinely constrained enum (TenureWrite.reason_left
		// is a strict Literal) — see the Reason Left <select>'s escape-hatch
		// comment below for why a non-canonical stored value is still shown.
		reason_left: string;
	}

	interface RawTenure {
		office: string | null;
		start_date: string | null;
		end_date: string | null;
		appointed_by: string | null;
		appointing_president_party: string | null;
		reason_left: string | null;
	}

	// Converts a server-provided tenure row (canonical, legacy-invalid, or
	// blank office) into local editable form state. Never guesses/coerces an
	// invalid or blank original value into a canonical default (D-11) — only
	// exactly 'chief'/'associate' is accepted as valid.
	function toTenureRow(t: RawTenure, key: number): TenureRow {
		if (t.office === 'chief' || t.office === 'associate') {
			return {
				_key: key,
				office: t.office,
				invalidOfficeOriginal: null,
				start_date: t.start_date ?? '',
				end_date: t.end_date ?? '',
				appointed_by: t.appointed_by ?? '',
				appointing_president_party: t.appointing_president_party ?? '',
				reason_left: t.reason_left ?? '',
			};
		}
		return {
			_key: key,
			office: null,
			invalidOfficeOriginal: t.office ?? '',
			start_date: t.start_date ?? '',
			end_date: t.end_date ?? '',
			appointed_by: t.appointed_by ?? '',
			appointing_president_party: t.appointing_president_party ?? '',
			reason_left: t.reason_left ?? '',
		};
	}

	// ──────────────────────────────────────────────────────────────────────────
	// Person Type — Bench/Advocate segmented toggle (D-13, replaces "Is Justice"
	// checkbox) + Bench-only Birth Date. The Role field and its inline-creation
	// machinery (select, "+ Add new role" sentinel, createRole action) are
	// fully removed per D-10 — none of it is carried forward into this card.
	// ──────────────────────────────────────────────────────────────────────────

	let isJustice = $state<boolean>(form?.is_justice ?? data.person.is_justice ?? false);
	let birthdate = $state<string>(form?.birthdate ?? data.person.birthdate ?? '');
	let deathDate = $state<string>(form?.death_date ?? data.person.death_date ?? '');
	// bio_text (Phase 39 gap closure, 39-UAT.md gap 1/test 10) — a failed save's
	// attempted bio always takes priority over the loaded record, same precedence
	// as birthdate/deathDate above. Bound (not seeded as child text content) so
	// the textarea always reflects this state and never keeps a stale dirty value.
	let bioText = $state<string>(form?.bio_text ?? data.person.bio_text ?? '');

	// ──────────────────────────────────────────────────────────────────────────
	// Name parts — $state so the generated Full Name preview (D-01, D-02)
	// updates live as the operator types. A prior failed save (form?.first_name
	// present, etc.) always takes priority over the loaded person record —
	// mirrors the tenureRows restore precedent below (D-12, D-16, D-17).
	// ──────────────────────────────────────────────────────────────────────────

	let firstName = $state<string>(form?.first_name ?? data.person.first_name ?? '');
	let middleName = $state<string>(form?.middle_name ?? data.person.middle_name ?? '');
	let lastName = $state<string>(form?.last_name ?? data.person.last_name ?? '');
	let nameSuffix = $state<string>(form?.name_suffix ?? data.person.name_suffix ?? '');

	let fullNamePreview = $derived(
		previewFullName({ first: firstName, middle: middleName, last: lastName, suffix: nameSuffix })
	);

	const MIN_NAME_ERROR = 'Enter at least a first or last name.';

	// ──────────────────────────────────────────────────────────────────────────
	// Tenure rows state (Pattern 1 — $state<TenureRow[]>, in-place mutation)
	// Each row gets a stable _key for the keyed {#each} block (Pitfall 2).
	// ──────────────────────────────────────────────────────────────────────────

	let nextKey = $state(1);

	// A prior failed save (form?.tenures present) always takes priority over
	// the loaded person record — the operator's unsaved edits (including any
	// still-invalid office selections) must be restored, never silently
	// dropped in favor of stale server data (D-12, D-16, D-17).
	let tenureRows = $state<TenureRow[]>(buildTenureRows(form?.tenures ?? data.person.tenures));

	function buildTenureRows(source: RawTenure[] | undefined | null): TenureRow[] {
		let key = 1;
		const rows = (source ?? []).map((t) => toTenureRow(t, key++));
		nextKey = key;
		return rows;
	}

	function addTenureRow() {
		tenureRows.push({
			_key: nextKey++,
			office: 'associate',
			invalidOfficeOriginal: null,
			start_date: '',
			end_date: '',
			appointed_by: '',
			appointing_president_party: '',
			reason_left: '',
		});
	}

	function removeTenureRow(index: number) {
		tenureRows.splice(index, 1);
	}

	// ──────────────────────────────────────────────────────────────────────────
	// office validation — client-side preflight only (T-37-10/T-37-11). The
	// server action and API/DB layers independently re-validate every row;
	// this is operator feedback, not the source of truth.
	// ──────────────────────────────────────────────────────────────────────────

	let officeSaveFormError = $state<string | null>(null);

	function firstInvalidOfficeIndex(): number {
		return tenureRows.findIndex((r) => r.office === null);
	}

	async function focusFirstInvalidOffice(index: number) {
		if (index < 0 || index >= tenureRows.length) return;
		await tick();
		const key = tenureRows[index]._key;
		const el = document.getElementById(`office-chief-${key}`);
		el?.focus();
	}

	// Guards the shared Save Person submit button (form="save-form", Gap E
	// idiom). Calling preventDefault() in a submit button's click handler
	// cancels the browser's implicit form-submission activation behavior —
	// no `submit` event ever reaches the form's use:enhance action, so an
	// unresolved office group blocks the request atomically (D-12/D-13/D-16).
	function handleSaveClick(event: MouseEvent) {
		const invalidIndex = firstInvalidOfficeIndex();
		if (invalidIndex !== -1) {
			event.preventDefault();
			officeSaveFormError = 'Select Chief or Associate for every tenure period before saving.';
			focusFirstInvalidOffice(invalidIndex);
			return;
		}
		officeSaveFormError = null;
	}

	// Rehydrates every submitted tenure row (including any still-unresolved
	// office selection) from a failed save action's returned form state, then
	// focuses the first unresolved office group (UI-SPEC "Server error").
	// Unrelated in-progress edits on this page are untouched (D-16).
	$effect(() => {
		if (form?.tenures) {
			tenureRows = buildTenureRows(form.tenures);
			const invalidIndex = firstInvalidOfficeIndex();
			if (invalidIndex !== -1) {
				officeSaveFormError = 'Select Chief or Associate for every tenure period before saving.';
				focusFirstInvalidOffice(invalidIndex);
			}
		}
		if (form?.birthdate !== undefined) {
			birthdate = form.birthdate ?? '';
		}
		if (form?.death_date !== undefined) {
			deathDate = form.death_date ?? '';
		}
		// Phase 39 gap closure (39-UAT.md gap 1/test 10) — !== undefined (not
		// truthiness) is required: an intentionally cleared bio comes back as
		// null and must restore as an empty box, not the stale stored text.
		if (form?.bio_text !== undefined) {
			bioText = form.bio_text ?? '';
		}
		if (form?.is_justice !== undefined) {
			isJustice = form.is_justice;
		}
		// Phase 38 (D-01, D-02, D-09, D-12, D-16): restore attempted name parts
		// after a failed save and focus First Name when the failure is
		// specifically the shared minimum-name error — never silently clear
		// unsaved name-part edits elsewhere on the form.
		if (form?.first_name !== undefined) firstName = form.first_name ?? '';
		if (form?.middle_name !== undefined) middleName = form.middle_name ?? '';
		if (form?.last_name !== undefined) lastName = form.last_name ?? '';
		if (form?.name_suffix !== undefined) nameSuffix = form.name_suffix ?? '';
		if (form?.error === MIN_NAME_ERROR) {
			tick().then(() => document.getElementById('first_name')?.focus());
		}
	});

	// ──────────────────────────────────────────────────────────────────────────
	// Save button submitting state
	// ──────────────────────────────────────────────────────────────────────────

	let saveSubmitting = $state(false);

	// Breadcrumb / Cancel target — preserves the tab the operator arrived from
	// (the person's persisted type at load time, not the live in-progress toggle).
	let backTab = $derived(data.person.is_justice ? 'bench' : 'advocate');

	// ──────────────────────────────────────────────────────────────────────────
	// Photo widget state (Phase 12 — PADM-01)
	// ──────────────────────────────────────────────────────────────────────────

	let photoTab = $state<'upload' | 'url'>('upload');
	let photoSubmitting = $state(false);

	// ──────────────────────────────────────────────────────────────────────────
	// Merge section state (Phase 12 — PADM-03/PADM-04)
	// ──────────────────────────────────────────────────────────────────────────

	let mergeTargetId = $state<string>('');
	let mergePreview = $state<{
		utterances: number;
		aliases: number;
		appearances: number;
		argument_participants: number;
		tenures: number;
	} | null>(null);
	let mergeLoading = $state(false);
	let mergeError = $state<string | null>(null);
	let mergeSubmitting = $state(false);

	// Reset merge/type state when navigating to a different person (SvelteKit soft
	// navigation reuses the component — $state variables must be reset manually
	// when person.id changes).
	$effect(() => {
		data.person.id;
		mergeTargetId = '';
		mergePreview = null;
		mergeError = null;
		mergeLoading = false;
		isJustice = data.person.is_justice ?? false;
		birthdate = data.person.birthdate ?? '';
		deathDate = data.person.death_date ?? '';
		bioText = data.person.bio_text ?? '';
		officeSaveFormError = null;
		tenureRows = buildTenureRows(data.person.tenures);
		firstName = data.person.first_name ?? '';
		middleName = data.person.middle_name ?? '';
		lastName = data.person.last_name ?? '';
		nameSuffix = data.person.name_suffix ?? '';
	});

	async function fetchMergePreview(targetId: string) {
		mergePreview = null;
		mergeError = null;
		if (!targetId) return;
		mergeLoading = true;
		try {
			const res = await fetch(
				`/admin/people/${data.person.id}/merge-preview?target_id=${targetId}`
			);
			if (res.ok) {
				mergePreview = await res.json();
			} else {
				mergeError = 'Could not load counts. Try again.';
			}
		} catch {
			mergeError = 'Could not load counts. Try again.';
		} finally {
			mergeLoading = false;
		}
	}

	// ──────────────────────────────────────────────────────────────────────────
	// Delete section state (Phase 12 — PADM-02)
	// ──────────────────────────────────────────────────────────────────────────

	let deleteSubmitting = $state(false);
</script>

<main style="background-color: var(--color-bg); min-height: 100vh;">
	<header style="background-color: var(--color-surface); border-bottom: 1px solid var(--color-border); padding: var(--space-md) var(--space-lg);">
		<nav aria-label="Breadcrumb" style="font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); line-height: 1.4;">
			<a href={'/admin/people?tab=' + backTab} style="color: var(--color-accent); text-decoration: none;">People</a>
			<span style="color: var(--color-text-secondary);"> &gt; </span>
			<span style="color: var(--color-text-secondary);">{data.person.full_name}</span>
		</nav>
		<h1 style="font-size: var(--font-size-heading); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); margin: var(--space-xs) 0 0 0; line-height: 1.2;">
			{data.person.full_name}
		</h1>
	</header>

	<div style="max-width: 640px; margin: 0 auto; padding: var(--space-2xl) var(--space-lg);">

		<!-- ══════════════════════════════════════════════════════════════════════
		     Main save form — covers Identity + Person Type (is_justice/birthdate/
		     tenures) plus the Biography card's bio_text (Phase 39 gap closure,
		     39-UAT.md gap 1/test 10). Only the Photo card's own upload lives in a
		     separate form below. IMPORTANT: no enctype on this form (Pitfall 1).
		     The form closes right after the Identity card — the Person Type and
		     Biography cards' inputs live outside this element but associate via
		     the `form="save-form"` attribute (same cross-form idiom already used
		     for the standalone Save Person button, Gap E fix).
		     ══════════════════════════════════════════════════════════════════════ -->
		<form
			id="save-form"
			method="POST"
			action="?/save"
			use:enhance={() => {
				saveSubmitting = true;
				return async ({ update }) => {
					saveSubmitting = false;
					await update();
				};
			}}
		>
			<!-- ── Identity card (renamed from "Basic Info", D-13 — no Is Justice checkbox) ── -->
			<div
				style="background-color: var(--color-surface); border: 1px solid var(--color-border); border-radius: 8px; padding: var(--space-lg); margin-bottom: var(--space-lg);"
			>
				<h2
					style="font-size: var(--font-size-heading); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); margin: 0 0 var(--space-md) 0; line-height: 1.2;"
				>
					Identity
				</h2>

				<!-- Full name — generated, read-only preview (D-01, D-02). Never an
				     editable input and never submitted as client data; an <output>
				     is used (not a disabled/readonly input) so it stays a plain
				     readout programmatically associated with its label/explanation. -->
				<div style="margin-bottom: var(--space-md);">
					<div style="display: flex; align-items: baseline; gap: var(--space-sm); margin-bottom: var(--space-sm); flex-wrap: wrap;">
						<span id="full_name_label" style="font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary);">
							Full Name
						</span>
						<span id="full_name_explanation" style="font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary);">
							Generated from name parts.
						</span>
					</div>
					<output
						id="full_name_preview"
						aria-labelledby="full_name_label full_name_explanation"
						aria-live="polite"
						style="display: block; width: 100%; background-color: var(--color-bg); border: 1px solid var(--color-border); border-radius: 6px; padding: var(--space-sm) 12px; font-size: var(--font-size-body); box-sizing: border-box; color: {fullNamePreview === 'N/A' ? 'var(--color-text-secondary)' : 'var(--color-text-primary)'}; font-style: {fullNamePreview === 'N/A' ? 'italic' : 'normal'};"
					>{fullNamePreview}</output>
				</div>

				<!-- Name parts — 4-column on desktop, 2-column on mobile. First-or-last
				     shared invariant (D-09) communicated once above the group rather
				     than marking both fields individually required. Each field's
				     independent extracted-value stack (D-14, D-15, D-19) renders below
				     its own input, sharing the person's single provenance_metadata
				     envelope (confidence + raw source text) — the backend persists one
				     whole-record provenance decision, not a separate guess per part, so
				     every populated field's own current value is what "was extracted"
				     for that field; a still-blank field (an ambiguous legacy split that
				     never applied) shows the disabled N/A state with the shared raw/
				     confidence per the Phase 36 contract. -->
				<div>
					<p style="font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); margin: 0 0 var(--space-sm) 0;">
						{MIN_NAME_ERROR}
					</p>
					<div class="name-parts-grid" style="display: grid; grid-template-columns: 1fr 1fr 1fr 80px; gap: var(--space-md);">
						<div>
							<label
								for="first_name"
								style="display: block; font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); margin-bottom: var(--space-sm);"
							>
								First name
							</label>
							<input
								id="first_name"
								name="first_name"
								type="text"
								bind:value={firstName}
								style="display: block; width: 100%; background-color: var(--color-bg); border: 1px solid var(--color-border); border-radius: 6px; padding: var(--space-sm) 12px; font-size: var(--font-size-body); color: var(--color-text-primary); box-sizing: border-box;"
							/>
							{#if data.person.provenance_metadata}
								<div style="margin-top: var(--space-sm);">
									<CopyableExtractedValue
										value={data.person.first_name}
										copyLabel="Copy extracted first name"
										confidence={data.person.provenance_metadata.confidence}
										raw={data.person.provenance_metadata.raw}
									/>
								</div>
							{/if}
						</div>
						<div>
							<label
								for="middle_name"
								style="display: block; font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); margin-bottom: var(--space-sm);"
							>
								Middle name
							</label>
							<input
								id="middle_name"
								name="middle_name"
								type="text"
								bind:value={middleName}
								style="display: block; width: 100%; background-color: var(--color-bg); border: 1px solid var(--color-border); border-radius: 6px; padding: var(--space-sm) 12px; font-size: var(--font-size-body); color: var(--color-text-primary); box-sizing: border-box;"
							/>
							{#if data.person.provenance_metadata}
								<div style="margin-top: var(--space-sm);">
									<CopyableExtractedValue
										value={data.person.middle_name}
										copyLabel="Copy extracted middle name"
										confidence={data.person.provenance_metadata.confidence}
										raw={data.person.provenance_metadata.raw}
									/>
								</div>
							{/if}
						</div>
						<div>
							<label
								for="last_name"
								style="display: block; font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); margin-bottom: var(--space-sm);"
							>
								Last name
							</label>
							<input
								id="last_name"
								name="last_name"
								type="text"
								bind:value={lastName}
								style="display: block; width: 100%; background-color: var(--color-bg); border: 1px solid var(--color-border); border-radius: 6px; padding: var(--space-sm) 12px; font-size: var(--font-size-body); color: var(--color-text-primary); box-sizing: border-box;"
							/>
							{#if data.person.provenance_metadata}
								<div style="margin-top: var(--space-sm);">
									<CopyableExtractedValue
										value={data.person.last_name}
										copyLabel="Copy extracted last name"
										confidence={data.person.provenance_metadata.confidence}
										raw={data.person.provenance_metadata.raw}
									/>
								</div>
							{/if}
						</div>
						<div>
							<label
								for="name_suffix"
								style="display: block; font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); margin-bottom: var(--space-sm);"
							>
								Suffix
							</label>
							<input
								id="name_suffix"
								name="name_suffix"
								type="text"
								bind:value={nameSuffix}
								style="display: block; width: 100%; background-color: var(--color-bg); border: 1px solid var(--color-border); border-radius: 6px; padding: var(--space-sm) 12px; font-size: var(--font-size-body); color: var(--color-text-primary); box-sizing: border-box;"
							/>
							{#if data.person.provenance_metadata}
								<div style="margin-top: var(--space-sm);">
									<CopyableExtractedValue
										value={data.person.name_suffix}
										copyLabel="Copy extracted suffix"
										confidence={data.person.provenance_metadata.confidence}
										raw={data.person.provenance_metadata.raw}
									/>
								</div>
							{/if}
						</div>
					</div>
				</div>
			</div>
		</form>

		<!-- ── Photo card: its own form, SEPARATE from save-form (Pitfall 1). Forwards
		     only the photo upload — bio_text moved onto the save-form (Phase 39 gap
		     closure, 39-UAT.md gap 1/test 10): the operator's primary Save Person
		     affordance now owns the whole person, including the bio. ── -->
		<form
			method="POST"
			action="?/photo"
			enctype="multipart/form-data"
			use:enhance={() => {
				photoSubmitting = true;
				return async ({ update }) => {
					photoSubmitting = false;
					await update();
				};
			}}
		>
			<!-- ── Photo card ── -->
			<div
				style="background-color: var(--color-surface); border: 1px solid var(--color-border); border-radius: 8px; padding: var(--space-lg); margin-bottom: var(--space-lg);"
			>
				<h2
					style="font-size: var(--font-size-heading); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); margin: 0 0 var(--space-md) 0; line-height: 1.2;"
				>
					Photo
				</h2>

				<!-- Photo preview: 80×80 circle — image or initials fallback -->
				<div style="margin-bottom: var(--space-md);">
					{#if data.person.photo_url_full}
						<img
							src={data.person.photo_url_full}
							alt="{data.person.full_name} profile photo"
							style="width: 80px; height: 80px; border-radius: 50%; object-fit: cover; border: 1px solid var(--color-border);"
						/>
					{:else}
						<div
							aria-hidden="true"
							style="width: 80px; height: 80px; border-radius: 50%; background-color: var(--color-border); color: var(--color-text-secondary); font-size: var(--font-size-display); font-weight: var(--font-weight-semibold); display: flex; align-items: center; justify-content: center; user-select: none;"
						>
							{(data.person.full_name ?? '').charAt(0).toUpperCase()}
						</div>
					{/if}
				</div>

				<!-- Tab bar -->
				<div style="display: flex; gap: 0; margin-bottom: var(--space-md); border-bottom: 1px solid var(--color-border);">
					<button
						type="button"
						onclick={() => (photoTab = 'upload')}
						style="padding: var(--space-sm) var(--space-md); font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); background: transparent; border: none; border-bottom: {photoTab === 'upload' ? '2px solid var(--color-accent)' : '2px solid transparent'}; color: {photoTab === 'upload' ? 'var(--color-text-primary)' : 'var(--color-text-secondary)'}; cursor: pointer; margin-bottom: -1px;"
					>
						Upload file
					</button>
					<button
						type="button"
						onclick={() => (photoTab = 'url')}
						style="padding: var(--space-sm) var(--space-md); font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); background: transparent; border: none; border-bottom: {photoTab === 'url' ? '2px solid var(--color-accent)' : '2px solid transparent'}; color: {photoTab === 'url' ? 'var(--color-text-primary)' : 'var(--color-text-secondary)'}; cursor: pointer; margin-bottom: -1px;"
					>
						Enter URL
					</button>
				</div>

				<!-- Tab panel -->
				{#if photoTab === 'upload'}
					<div style="margin-bottom: var(--space-md);">
						<input
							type="file"
							name="photo_file"
							accept="image/*"
							style="display: block; width: 100%; min-height: var(--touch-target); background-color: var(--color-bg); border: 1px solid var(--color-border); border-radius: 6px; padding: var(--space-sm) 12px; font-size: var(--font-size-body); color: var(--color-text-primary); box-sizing: border-box; cursor: pointer;"
						/>
					</div>
				{:else}
					<div style="margin-bottom: var(--space-md);">
						<input
							type="text"
							name="photo_url"
							placeholder="https://…"
							style="display: block; width: 100%; background-color: var(--color-bg); border: 1px solid var(--color-border); border-radius: 6px; padding: var(--space-sm) 12px; font-size: var(--font-size-body); color: var(--color-text-primary); box-sizing: border-box;"
						/>
					</div>
				{/if}

				{#if form?.photoError}
					<p role="alert" style="color: var(--color-destructive); font-size: var(--font-size-caption); margin: 0 0 var(--space-sm) 0;">
						{form.photoError}
					</p>
				{/if}

				<button
					type="submit"
					disabled={photoSubmitting}
					style="display: block; width: 100%; min-height: var(--touch-target); background: transparent; border: 1px solid var(--color-accent); border-radius: 6px; font-size: var(--font-size-body); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); cursor: pointer; opacity: {photoSubmitting ? 0.7 : 1};"
				>
					{photoSubmitting ? 'Uploading…' : 'Upload photo'}
				</button>
			</div>
		</form>

		<!-- ── Biography card (Phase 39 gap closure, 39-UAT.md gap 1/test 10) — sits
		     outside the photo form. Its textarea associates with save-form via the
		     `form` attribute, the same cross-form idiom the Person Type card's
		     hidden inputs already use, so the bio saves atomically with the rest of
		     the person on Save Person, not with the photo upload. ── -->
		<div
			style="background-color: var(--color-surface); border: 1px solid var(--color-border); border-radius: 8px; padding: var(--space-lg); margin-bottom: var(--space-lg);"
		>
			<h2
				style="font-size: var(--font-size-heading); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); margin: 0 0 var(--space-md) 0; line-height: 1.2;"
			>
				Biography
			</h2>

			<div>
				<label
					for="bio_text"
					style="display: block; font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); margin-bottom: var(--space-sm);"
				>
					Bio
				</label>
				<p style="font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); margin: 0 0 var(--space-sm) 0;">
					Saved with Save Person.
				</p>
				<textarea
					id="bio_text"
					name="bio_text"
					form="save-form"
					bind:value={bioText}
					placeholder="Enter a short biography…"
					style="display: block; width: 100%; background-color: var(--color-bg); border: 1px solid var(--color-border); border-radius: 6px; padding: var(--space-sm) 12px; font-size: var(--font-size-body); color: var(--color-text-primary); box-sizing: border-box; min-height: 120px; resize: vertical; font-family: inherit;"
				></textarea>
			</div>
		</div>

		<!-- ── Person Type card (new, D-13) — Bench/Advocate segmented toggle replaces the
		     old "Is Justice" checkbox; Bench-only fields slide-reveal (D-11). The Role
		     field and its inline-creation machinery are fully removed (D-10) — not
		     carried into this card at all. Inputs associate with save-form via the
		     `form` attribute since this card sits outside that <form> element. ── -->
		<div
			style="background-color: var(--color-surface); border: 1px solid var(--color-border); border-radius: 8px; padding: var(--space-lg); margin-bottom: var(--space-lg);"
		>
			<h2
				style="font-size: var(--font-size-heading); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); margin: 0 0 var(--space-md) 0; line-height: 1.2;"
			>
				Person Type
			</h2>

			<!-- Bench/Advocate segmented toggle (D-13) — same visual idiom as the list-page tab toggle -->
			<div style="display: flex; gap: 0; margin-bottom: var(--space-md);">
				<button
					type="button"
					aria-pressed={isJustice}
					aria-label="Bench"
					onclick={() => (isJustice = true)}
					style="
						min-height: var(--touch-target);
						padding: var(--space-sm) var(--space-md);
						border: 1px solid {isJustice ? 'var(--color-accent)' : 'var(--color-border)'};
						border-radius: 6px 0 0 6px;
						background-color: {isJustice ? 'var(--color-accent)' : 'var(--color-surface)'};
						color: {isJustice ? 'var(--color-bg)' : 'var(--color-text-primary)'};
						font-size: var(--font-size-body);
						font-weight: var(--font-weight-semibold);
						cursor: pointer;
					"
				>Bench</button>
				<button
					type="button"
					aria-pressed={!isJustice}
					aria-label="Advocate"
					onclick={() => (isJustice = false)}
					style="
						min-height: var(--touch-target);
						padding: var(--space-sm) var(--space-md);
						border: 1px solid {!isJustice ? 'var(--color-accent)' : 'var(--color-border)'};
						border-left: none;
						border-radius: 0 6px 6px 0;
						background-color: {!isJustice ? 'var(--color-accent)' : 'var(--color-surface)'};
						color: {!isJustice ? 'var(--color-bg)' : 'var(--color-text-primary)'};
						font-size: var(--font-size-body);
						font-weight: var(--font-weight-semibold);
						cursor: pointer;
					"
				>Advocate</button>
			</div>

			<!-- Carries the toggle's boolean value into the save-form; always present
			     regardless of which segment is selected (a segmented toggle always
			     submits a value, unlike the old checkbox which was absent when unchecked). -->
			<input type="hidden" name="is_justice" form="save-form" value={isJustice ? 'true' : 'false'} />

			<!-- Always present, independent of the Bench/Advocate toggle (CR-01 gap-closure
			     fix, 27-10) — so the save action always receives the true current
			     birthdate/tenure state, regardless of whether the Bench-only UI below
			     is currently mounted. -->
			<input type="hidden" name="birthdate" form="save-form" value={birthdate} />
			<input type="hidden" name="death_date" form="save-form" value={deathDate} />
			<input type="hidden" name="tenures" form="save-form" value={JSON.stringify(tenureRows)} />

			{#if isJustice}
			<div transition:slide>
				<!-- Birth Date + Death Date (D-08, D-10) -->
				<div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-md); margin-bottom: var(--space-md);">
					<div>
						<label
							for="birthdate"
							style="display: block; font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); margin-bottom: var(--space-sm);"
						>
							Birth Date
						</label>
						<input
							id="birthdate"
							type="date"
							bind:value={birthdate}
							style="display: block; width: 100%; background-color: var(--color-bg); border: 1px solid var(--color-border); border-radius: 6px; padding: var(--space-sm) 12px; font-size: var(--font-size-body); color: var(--color-text-primary); box-sizing: border-box;"
						/>
					</div>
					<div>
						<label
							for="death_date"
							style="display: block; font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); margin-bottom: var(--space-sm);"
						>
							Death Date
						</label>
						<input
							id="death_date"
							type="date"
							bind:value={deathDate}
							style="display: block; width: 100%; background-color: var(--color-bg); border: 1px solid var(--color-border); border-radius: 6px; padding: var(--space-sm) 12px; font-size: var(--font-size-body); color: var(--color-text-primary); box-sizing: border-box;"
						/>
					</div>
				</div>

				<h3 style="font-size: var(--font-size-body); font-weight: var(--font-weight-regular); color: var(--color-text-primary); margin: 0 0 var(--space-md) 0; line-height: 1.2;">
					Tenure Periods
				</h3>

				<!-- Tenure Period sub-cards (D-18): bordered, inset background -->
				{#each tenureRows as row, i (row._key)}
					<div
						style="background-color: var(--color-bg); border: 1px solid var(--color-border); border-radius: 6px; padding: var(--space-lg); margin-bottom: var(--space-md);"
					>
						<!-- office (D-01..D-17, Phase 37) — segmented native-radio control
						     replacing the free-text seat field. Exactly one of the two
						     canonical values may be selected; an invalid/blank legacy
						     original is never coerced and stays visible until the operator
						     explicitly corrects it (D-11). Native same-name radios provide
						     idempotent one-of-two selection and standard arrow/space/tab
						     keyboard semantics; aria-invalid/aria-describedby live on the
						     radiogroup (role="radiogroup" is the only role in this markup
						     that ARIA permits aria-invalid on — not the fieldset's implicit
						     "group" role, and not the individual radios' "radio" role). -->
						<fieldset style="border: none; margin: 0 0 var(--space-md) 0; padding: 0;">
							<legend style="display: block; font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); margin-bottom: var(--space-sm); padding: 0;">Office</legend>
							<div
								role="radiogroup"
								aria-describedby={row.office === null ? `office-error-${row._key}` : undefined}
								aria-invalid={row.office === null ? 'true' : 'false'}
								style="display: flex; gap: 0;"
							>
								<label
									for="office-chief-{row._key}"
									class="office-segment"
									style="
										position: relative;
										flex: 1;
										min-height: var(--touch-target);
										padding: var(--space-sm) var(--space-md);
										display: flex;
										align-items: center;
										justify-content: center;
										box-sizing: border-box;
										border: 1px solid {row.office === 'chief' ? 'var(--color-accent)' : 'var(--color-border)'};
										border-radius: 6px 0 0 6px;
										background-color: {row.office === 'chief' ? 'var(--color-accent)' : 'var(--color-surface)'};
										color: {row.office === 'chief' ? 'var(--color-bg)' : 'var(--color-text-primary)'};
										font-size: var(--font-size-body);
										font-weight: var(--font-weight-semibold);
										cursor: pointer;
									"
								>
									<input
										id="office-chief-{row._key}"
										class="office-radio-input"
										type="radio"
										name="office-{row._key}"
										value="chief"
										bind:group={row.office}
										onchange={() => (row.invalidOfficeOriginal = null)}
									/>
									Chief
								</label>
								<label
									for="office-associate-{row._key}"
									class="office-segment"
									style="
										position: relative;
										flex: 1;
										min-height: var(--touch-target);
										padding: var(--space-sm) var(--space-md);
										display: flex;
										align-items: center;
										justify-content: center;
										box-sizing: border-box;
										border: 1px solid {row.office === 'associate' ? 'var(--color-accent)' : 'var(--color-border)'};
										border-left: none;
										border-radius: 0 6px 6px 0;
										background-color: {row.office === 'associate' ? 'var(--color-accent)' : 'var(--color-surface)'};
										color: {row.office === 'associate' ? 'var(--color-bg)' : 'var(--color-text-primary)'};
										font-size: var(--font-size-body);
										font-weight: var(--font-weight-semibold);
										cursor: pointer;
									"
								>
									<input
										id="office-associate-{row._key}"
										class="office-radio-input"
										type="radio"
										name="office-{row._key}"
										value="associate"
										bind:group={row.office}
										onchange={() => (row.invalidOfficeOriginal = null)}
									/>
									Associate
								</label>
							</div>
							{#if row.office === null}
								<p
									id="office-error-{row._key}"
									role="alert"
									style="color: var(--color-destructive); font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); line-height: 1.4; margin: var(--space-sm) 0 0 0;"
								>
									{#if row.invalidOfficeOriginal === ''}
										No office was recorded. Select Chief or Associate before saving.
									{:else}
										Unrecognized office: "{row.invalidOfficeOriginal}". Select Chief or Associate before saving.
									{/if}
								</p>
							{/if}
						</fieldset>

						<div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-md); margin-bottom: var(--space-md);">
							<div>
								<label
									for="tenure-start-{row._key}"
									style="display: block; font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); margin-bottom: var(--space-sm);"
								>
									Start Date
								</label>
								<input
									id="tenure-start-{row._key}"
									type="date"
									bind:value={row.start_date}
									style="display: block; width: 100%; background-color: var(--color-surface); border: 1px solid var(--color-border); border-radius: 6px; padding: var(--space-sm) 12px; font-size: var(--font-size-body); color: var(--color-text-primary); box-sizing: border-box;"
								/>
							</div>
							<div>
								<label
									for="tenure-end-{row._key}"
									style="display: block; font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); margin-bottom: var(--space-sm);"
								>
									End Date
								</label>
								<input
									id="tenure-end-{row._key}"
									type="date"
									bind:value={row.end_date}
									style="display: block; width: 100%; background-color: var(--color-surface); border: 1px solid var(--color-border); border-radius: 6px; padding: var(--space-sm) 12px; font-size: var(--font-size-body); color: var(--color-text-primary); box-sizing: border-box;"
								/>
							</div>
						</div>

						<div style="margin-bottom: var(--space-md);">
							<label
								for="tenure-appointed-{row._key}"
								style="display: block; font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); margin-bottom: var(--space-sm);"
							>
								Appointing President
							</label>
							<input
								id="tenure-appointed-{row._key}"
								type="text"
								bind:value={row.appointed_by}
								style="display: block; width: 100%; background-color: var(--color-surface); border: 1px solid var(--color-border); border-radius: 6px; padding: var(--space-sm) 12px; font-size: var(--font-size-body); color: var(--color-text-primary); box-sizing: border-box;"
							/>
						</div>

						<div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-md); margin-bottom: var(--space-md);">
							<div>
								<label
									for="tenure-party-{row._key}"
									style="display: block; font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); margin-bottom: var(--space-sm);"
								>
									President's Party
								</label>
								<select
									id="tenure-party-{row._key}"
									bind:value={row.appointing_president_party}
									style="display: block; width: 100%; background-color: var(--color-surface); border: 1px solid var(--color-border); border-radius: 6px; padding: var(--space-sm) 12px; font-size: var(--font-size-body); color: var(--color-text-primary); box-sizing: border-box;"
								>
									<option value="">— None —</option>
									{#each PARTY_OPTIONS as party (party)}
										<option value={party}>{party}</option>
									{/each}
									{#if row.appointing_president_party && !PARTY_OPTIONS.includes(row.appointing_president_party)}
										<option value={row.appointing_president_party}
											>{row.appointing_president_party}</option
										>
									{/if}
								</select>
							</div>
							<div>
								<label
									for="tenure-reason-{row._key}"
									style="display: block; font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); margin-bottom: var(--space-sm);"
								>
									Reason Left
								</label>
								<!-- reason_left (D-01, D-09) is a genuinely constrained enum
								     (TenureWrite.reason_left is a strict Literal, enforced again
								     by the DB CHECK constraint) — unlike President's Party above,
								     this is NOT an open vocabulary. The escape-hatch option below
								     exists only so a pre-existing non-canonical stored value stays
								     visible and correctable; it is never a value the operator can
								     freshly submit, since selecting it just re-submits the same
								     already-invalid string. -->
								<select
									id="tenure-reason-{row._key}"
									bind:value={row.reason_left}
									style="display: block; width: 100%; background-color: var(--color-surface); border: 1px solid var(--color-border); border-radius: 6px; padding: var(--space-sm) 12px; font-size: var(--font-size-body); color: var(--color-text-primary); box-sizing: border-box;"
								>
									<option value="">— None —</option>
									<option value="retired">Retired</option>
									<option value="died">Died in office</option>
									<option value="promoted">Promoted</option>
									{#if row.reason_left && !['retired', 'died', 'promoted'].includes(row.reason_left)}
										<option value={row.reason_left}>{row.reason_left}</option>
									{/if}
								</select>
							</div>
						</div>

						<div style="text-align: right;">
							<button
								type="button"
								onclick={() => removeTenureRow(i)}
								style="color: var(--color-destructive); background: transparent; border: 1px solid var(--color-destructive); border-radius: 6px; font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); min-height: var(--touch-target-dense); padding: var(--space-xs) var(--space-md); cursor: pointer;"
							>
								Remove
							</button>
						</div>
					</div>
				{/each}

				<!-- Add tenure link (D-18) -->
				<button
					type="button"
					onclick={addTenureRow}
					style="display: inline-block; font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-accent); background: transparent; border: none; padding: 0; cursor: pointer;"
				>
					+ Add Tenure Period
				</button>
			</div>
			{/if}
		</div>

		<!-- Form-level error (from save action, or client-side office preflight) -->
		{#if form?.error}
			<p role="alert" style="color: var(--color-destructive); font-size: var(--font-size-caption); margin: 0 0 var(--space-sm) 0;">
				{form.error}
			</p>
		{/if}
		{#if officeSaveFormError}
			<p role="alert" style="color: var(--color-destructive); font-size: var(--font-size-caption); margin: 0 0 var(--space-sm) 0;">
				{officeSaveFormError}
			</p>
		{/if}

		<!-- ── Merge (PADM-03/PADM-04) — outside the save form; hidden on the create route (D-07 shared template) ── -->
		{#if data.person.id}
		<div
			style="background-color: var(--color-surface); border: 1px solid var(--color-border); border-radius: 8px; padding: var(--space-lg); margin-bottom: var(--space-lg);"
		>
			<h2
				style="font-size: var(--font-size-heading); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); margin: 0 0 var(--space-md) 0; line-height: 1.2;"
			>
				Merge into another person
			</h2>

			<form
				method="POST"
				action="?/merge"
				use:enhance={() => {
					mergeSubmitting = true;
					return async ({ update }) => {
						mergeSubmitting = false;
						await update();
					};
				}}
			>
				<!-- Target picker -->
				<div style="margin-bottom: var(--space-md);">
					<label
						for="merge_target_id"
						style="display: block; font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); margin-bottom: var(--space-sm);"
					>
						Merge this person into
					</label>
					<select
						id="merge_target_id"
						bind:value={mergeTargetId}
						onchange={(e) => fetchMergePreview((e.target as HTMLSelectElement).value)}
						style="display: block; width: 100%; background-color: var(--color-bg); border: 1px solid var(--color-border); border-radius: 6px; padding: var(--space-sm) 12px; font-size: var(--font-size-body); color: var(--color-text-primary); box-sizing: border-box;"
					>
						<option value="">— Select a person —</option>
						{#each data.people ?? [] as p (p.id)}
							<option value={String(p.id)}>
								{p.last_name ? `${p.last_name}, ${p.first_name ?? ''}` : p.full_name}
							</option>
						{/each}
					</select>
					<!-- Hidden input carries the value to the form action -->
					<input type="hidden" name="target_id" value={mergeTargetId} />
				</div>

				<!-- Preview panel — shown when a target is selected -->
				{#if mergeTargetId}
					<div
						style="background-color: var(--color-bg); border: 1px solid var(--color-border); border-radius: 6px; padding: var(--space-md); margin-bottom: var(--space-md);"
					>
						{#if mergeLoading}
							<p style="font-size: var(--font-size-caption); color: var(--color-text-secondary); margin: 0;">Loading…</p>
						{:else if mergeError}
							<p role="alert" style="font-size: var(--font-size-caption); color: var(--color-destructive); margin: 0;">{mergeError}</p>
						{:else if mergePreview}
							{@const targetPerson = (data.people ?? []).find((p: { id: number }) => String(p.id) === mergeTargetId)}
							<p style="font-size: var(--font-size-caption); color: var(--color-text-secondary); margin: 0 0 var(--space-sm) 0;">
								This will transfer from <strong style="color: var(--color-text-primary);">{data.person.full_name}</strong> to <strong style="color: var(--color-text-primary);">{targetPerson?.full_name ?? targetPerson?.last_name ?? 'selected person'}</strong>:
							</p>
							{#if mergePreview.utterances === 0 && mergePreview.aliases === 0 && mergePreview.appearances === 0 && mergePreview.argument_participants === 0 && mergePreview.tenures === 0}
								<p style="font-size: var(--font-size-caption); color: var(--color-text-secondary); margin: 0;">
									No records to transfer. This person has no associated data.
								</p>
							{:else}
								<p style="font-size: var(--font-size-caption); color: var(--color-text-primary); margin: 0;">
									{mergePreview.utterances} utterance(s) · {mergePreview.aliases} alias(es) · {mergePreview.appearances} appearance(s) · {mergePreview.argument_participants} argument participant(s) · {mergePreview.tenures} tenure(s)
								</p>
							{/if}
						{/if}
					</div>
				{/if}

				<!-- Confirm merge button — shown when target selected and preview loaded -->
				{#if mergeTargetId && mergePreview}
					{@const confirmTargetPerson = (data.people ?? []).find((p: { id: number }) => String(p.id) === mergeTargetId)}
					<button
						type="submit"
						disabled={mergeSubmitting}
						style="display: block; width: 100%; min-height: var(--touch-target); background: transparent; border: 1px solid var(--color-accent); border-radius: 6px; font-size: var(--font-size-body); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); cursor: pointer; opacity: {mergeSubmitting ? 0.7 : 1};"
					>
						{mergeSubmitting ? 'Merging…' : `Merge ${data.person.full_name} into ${confirmTargetPerson?.full_name ?? confirmTargetPerson?.last_name ?? 'selected person'}`}
					</button>
				{/if}

				{#if form?.mergeError}
					<p role="alert" style="color: var(--color-destructive); font-size: var(--font-size-caption); margin: var(--space-sm) 0 0 0;">
						{form.mergeError}
					</p>
				{/if}
			</form>
		</div>
		{/if}

		<!-- ── Delete (PADM-02) — outside the save form; hidden on the create route (D-07 shared template) ── -->
		{#if data.person.id}
		<div
			style="background-color: var(--color-surface); border: 1px solid var(--color-border); border-radius: 8px; padding: var(--space-lg); margin-bottom: var(--space-lg);"
		>
			<form
				method="POST"
				action="?/delete"
				use:enhance={() => {
					deleteSubmitting = true;
					return async ({ update }) => {
						deleteSubmitting = false;
						await update();
					};
				}}
			>
				{#if data.can_delete}
					<button
						type="submit"
						disabled={deleteSubmitting}
						style="display: block; width: 100%; min-height: var(--touch-target); background: transparent; border: 1px solid var(--color-destructive); border-radius: 6px; font-size: var(--font-size-body); font-weight: var(--font-weight-semibold); color: var(--color-destructive); cursor: pointer; opacity: {deleteSubmitting ? 0.7 : 1};"
					>
						{deleteSubmitting ? 'Deleting…' : 'Delete person'}
					</button>
				{:else}
					<button
						type="submit"
						disabled
						aria-describedby="delete-tip"
						style="display: block; width: 100%; min-height: var(--touch-target); background: transparent; border: 1px solid var(--color-border); border-radius: 6px; font-size: var(--font-size-body); font-weight: var(--font-weight-semibold); color: var(--color-text-secondary); cursor: not-allowed; opacity: 0.7;"
					>
						Delete person
					</button>
					<p
						id="delete-tip"
						style="font-size: var(--font-size-caption); color: var(--color-text-secondary); margin-top: var(--space-sm); text-align: center;"
					>
						Cannot delete — this person has associated records and cannot be removed.
					</p>
				{/if}

				{#if form?.deleteError}
					<p role="alert" style="color: var(--color-destructive); font-size: var(--font-size-caption); margin: var(--space-sm) 0 0 0;">
						{form.deleteError}
					</p>
				{/if}
			</form>
		</div>
		{/if}

		<!-- ── Form-level action row: Save Person + Cancel ── -->
		<div style="display: flex; gap: var(--space-sm);">
			<button
				type="submit"
				form="save-form"
				disabled={saveSubmitting}
				onclick={handleSaveClick}
				style="flex: 1; min-height: var(--touch-target); background: transparent; border: 1px solid var(--color-accent); border-radius: 6px; font-size: var(--font-size-body); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); cursor: pointer; opacity: {saveSubmitting ? 0.7 : 1};"
			>
				{saveSubmitting ? 'Saving…' : 'Save Person'}
			</button>
			<a
				href={'/admin/people?tab=' + backTab}
				style="flex: 1; display: inline-flex; align-items: center; justify-content: center; min-height: var(--touch-target); background: transparent; border: 1px solid var(--color-border); border-radius: 6px; font-size: var(--font-size-body); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); text-decoration: none; box-sizing: border-box;"
			>
				Cancel
			</a>
		</div>
	</div>
</main>

<style>
	@media (max-width: 640px) {
		.name-parts-grid {
			grid-template-columns: 1fr 1fr !important;
		}
	}

	/* office segmented control (Phase 37) — the native radio input itself is
	   visually hidden (but remains in the tab order and focusable) so its
	   wrapping label can render the segmented pill; the label shows a clearly
	   visible focus ring whenever its radio has keyboard focus. */
	.office-radio-input {
		position: absolute;
		width: 1px;
		height: 1px;
		padding: 0;
		margin: -1px;
		overflow: hidden;
		clip: rect(0, 0, 0, 0);
		white-space: nowrap;
		border: 0;
	}

	.office-segment:has(.office-radio-input:focus-visible) {
		outline: 2px solid var(--color-accent);
		outline-offset: 2px;
	}
</style>
