<script lang="ts">
	import { enhance } from '$app/forms';
	import { tick } from 'svelte';
	import { previewFullName } from '$lib/personNames';

	let { data, form } = $props();

	// ──────────────────────────────────────────────────────────────────────────
	// Person Type — Bench/Advocate segmented toggle (D-13), adapted from the
	// [id] editor template (D-07) with one difference: `isJustice` is a
	// three-state boolean|null so NEITHER segment is pre-selected on first
	// render (D-08 — an explicit choice is required before create can submit).
	// The Role field and its inline-creation machinery are not carried into
	// this card at all (D-10, matches the [id] template).
	// ──────────────────────────────────────────────────────────────────────────

	let isJustice = $state<boolean | null>(data.person.is_justice);

	// ──────────────────────────────────────────────────────────────────────────
	// Name parts — $state so the generated Full Name preview (D-01, D-02)
	// updates live as the operator types. This route is always a blank form
	// (data.person has no name parts), so a failed create's returned `form`
	// state is the only source of "what the operator already typed" — restore
	// it below rather than silently discarding it on a validation error.
	// ──────────────────────────────────────────────────────────────────────────

	let firstName = $state<string>(form?.first_name ?? '');
	let middleName = $state<string>(form?.middle_name ?? '');
	let lastName = $state<string>(form?.last_name ?? '');
	let nameSuffix = $state<string>(form?.name_suffix ?? '');

	let fullNamePreview = $derived(
		previewFullName({ first: firstName, middle: middleName, last: lastName, suffix: nameSuffix })
	);

	const MIN_NAME_ERROR = 'Enter at least a first or last name.';

	// Restores attempted name-part values after a failed create submit and
	// moves focus to First Name when the failure is specifically the shared
	// minimum-name error (D-12, D-16 — never silently clear unsaved input).
	$effect(() => {
		if (form?.first_name !== undefined) firstName = form.first_name ?? '';
		if (form?.middle_name !== undefined) middleName = form.middle_name ?? '';
		if (form?.last_name !== undefined) lastName = form.last_name ?? '';
		if (form?.name_suffix !== undefined) nameSuffix = form.name_suffix ?? '';
		if (form?.error === MIN_NAME_ERROR) {
			tick().then(() => document.getElementById('first_name')?.focus());
		}
	});

	// ──────────────────────────────────────────────────────────────────────────
	// Create button submitting state
	// ──────────────────────────────────────────────────────────────────────────

	let saveSubmitting = $state(false);

	// Merge/Delete are not rendered on this route at all (Claude's Discretion
	// item 3, PEDIT-11/PEDIT-12) — there is nothing to merge or delete before
	// the person exists, and this route has no `merge`/`delete` actions for
	// such a form to submit to (unlike the [id] editor, which reuses this
	// exact card structure once a person record is present).
</script>

<main style="background-color: #0f1117; min-height: 100vh;">
	<header style="background-color: #1e293b; border-bottom: 1px solid #334155; padding: 16px 24px;">
		<nav aria-label="Breadcrumb" style="font-size: 14px; font-weight: 400; line-height: 1.4;">
			<a href="/admin/people" style="color: #93c5fd; text-decoration: none;">People</a>
			<span style="color: #94a3b8;"> &gt; </span>
			<span style="color: #94a3b8;">Create Person</span>
		</nav>
		<h1 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 4px 0 0 0; line-height: 1.2;">
			Create Person
		</h1>
	</header>

	<div style="max-width: 640px; margin: 0 auto; padding: 48px 24px;">

		<!-- ══════════════════════════════════════════════════════════════════════
		     Create form — covers Identity + Person Type (is_justice/birthdate/
		     tenures form fields render for structural parity with the [id]
		     template, but the create action only reads full_name + is_justice —
		     D-08). No Photo/Biography form on this route (see note below the
		     Person Type card). IMPORTANT: no enctype on this form (Pitfall 1).
		     ══════════════════════════════════════════════════════════════════════ -->
		<form
			id="create-form"
			method="POST"
			action="?/create"
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
				style="background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px; margin-bottom: 24px;"
			>
				<h2
					style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 16px 0; line-height: 1.2;"
				>
					Identity
				</h2>

				<!-- Full name — generated, read-only preview (D-01, D-02). Never an
				     editable input and never submitted as client data; an <output>
				     is used (not a disabled/readonly input) so it stays a plain
				     readout programmatically associated with its label/explanation. -->
				<div style="margin-bottom: 16px;">
					<div style="display: flex; align-items: baseline; gap: 8px; margin-bottom: 8px; flex-wrap: wrap;">
						<span id="full_name_label" style="font-size: 14px; font-weight: 400; color: #94a3b8;">
							Full Name
						</span>
						<span id="full_name_explanation" style="font-size: 14px; font-weight: 400; color: #94a3b8;">
							Generated from name parts.
						</span>
					</div>
					<output
						id="full_name_preview"
						aria-labelledby="full_name_label full_name_explanation"
						aria-live="polite"
						style="display: block; width: 100%; background-color: #0f1117; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; box-sizing: border-box; color: {fullNamePreview === 'N/A' ? '#94a3b8' : '#e2e8f0'}; font-style: {fullNamePreview === 'N/A' ? 'italic' : 'normal'};"
					>{fullNamePreview}</output>
				</div>

				<!-- Name parts — 4-column on desktop, 2-column on mobile. First-or-last
				     shared invariant (D-09) communicated once above the group rather
				     than marking both fields individually required. -->
				<div>
					<p style="font-size: 14px; font-weight: 400; color: #94a3b8; margin: 0 0 8px 0;">
						{MIN_NAME_ERROR}
					</p>
					<div class="name-parts-grid" style="display: grid; grid-template-columns: 1fr 1fr 1fr 80px; gap: 16px;">
						<div>
							<label
								for="first_name"
								style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;"
							>
								First name
							</label>
							<input
								id="first_name"
								name="first_name"
								type="text"
								bind:value={firstName}
								style="display: block; width: 100%; background-color: #0f1117; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #e2e8f0; box-sizing: border-box;"
							/>
						</div>
						<div>
							<label
								for="middle_name"
								style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;"
							>
								Middle name
							</label>
							<input
								id="middle_name"
								name="middle_name"
								type="text"
								bind:value={middleName}
								style="display: block; width: 100%; background-color: #0f1117; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #e2e8f0; box-sizing: border-box;"
							/>
						</div>
						<div>
							<label
								for="last_name"
								style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;"
							>
								Last name
							</label>
							<input
								id="last_name"
								name="last_name"
								type="text"
								bind:value={lastName}
								style="display: block; width: 100%; background-color: #0f1117; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #e2e8f0; box-sizing: border-box;"
							/>
						</div>
						<div>
							<label
								for="name_suffix"
								style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;"
							>
								Suffix
							</label>
							<input
								id="name_suffix"
								name="name_suffix"
								type="text"
								bind:value={nameSuffix}
								style="display: block; width: 100%; background-color: #0f1117; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #e2e8f0; box-sizing: border-box;"
							/>
						</div>
					</div>
				</div>
			</div>
		</form>

		<!-- ── Photo/Biography: intentionally omitted on the create route.
		     Both cards share a single `?/photo` form/action on [id] (Pitfall 7
		     extended) — that action needs a person id to attach an upload to
		     and does not exist on this route, and D-08 explicitly excludes
		     bio_text/photo_url from the create payload ("filled in on the
		     editor after redirect"). Rendering either card here would either
		     submit to a non-existent action or silently discard input, so both
		     are hidden until the person exists (choice documented in the plan
		     27-06 SUMMARY). ── -->

		<!-- ── Person Type card (new, D-13) — Bench/Advocate segmented toggle replaces the
		     old "Is Justice" checkbox; Bench-only fields slide-reveal (D-11). Unlike the
		     [id] template, `isJustice` starts as null so NEITHER segment is
		     pre-selected (D-08 requires an explicit choice before create can submit).
		     The Role field and its inline-creation machinery are fully removed (D-10) —
		     not carried into this card at all. Inputs associate with create-form via
		     the `form` attribute since this card sits outside that <form> element. ── -->
		<div
			style="background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px; margin-bottom: 24px;"
		>
			<h2
				style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 16px 0; line-height: 1.2;"
			>
				Person Type
			</h2>

			<!-- Bench/Advocate segmented toggle (D-13) — same visual idiom as the list-page tab toggle.
			     Neither button reads as selected while isJustice is null. -->
			<div style="display: flex; gap: 0; margin-bottom: 16px;">
				<button
					type="button"
					aria-pressed={isJustice === true}
					aria-label="Bench"
					onclick={() => (isJustice = true)}
					style="
						min-height: 44px;
						padding: 8px 16px;
						border: 1px solid {isJustice === true ? '#93c5fd' : '#334155'};
						border-radius: 6px 0 0 6px;
						background-color: {isJustice === true ? '#93c5fd' : '#1e293b'};
						color: {isJustice === true ? '#0f1117' : '#e2e8f0'};
						font-size: 16px;
						font-weight: 600;
						cursor: pointer;
					"
				>Bench</button>
				<button
					type="button"
					aria-pressed={isJustice === false}
					aria-label="Advocate"
					onclick={() => (isJustice = false)}
					style="
						min-height: 44px;
						padding: 8px 16px;
						border: 1px solid {isJustice === false ? '#93c5fd' : '#334155'};
						border-left: none;
						border-radius: 0 6px 6px 0;
						background-color: {isJustice === false ? '#93c5fd' : '#1e293b'};
						color: {isJustice === false ? '#0f1117' : '#e2e8f0'};
						font-size: 16px;
						font-weight: 600;
						cursor: pointer;
					"
				>Advocate</button>
			</div>

			<!-- Carries the toggle's value into create-form. Submits '' (neither) when
			     isJustice is still null, so the server's explicit-choice guard (D-08,
			     "Choose Bench or Advocate to continue.") can distinguish "not chosen yet"
			     from a real true/false value. -->
			<input
				type="hidden"
				name="is_justice"
				form="create-form"
				value={isJustice === null ? '' : isJustice ? 'true' : 'false'}
			/>

			<!-- ── Birth Date + Tenure Periods: intentionally omitted on the create
			     route (WR-03 fix) — same reasoning as Photo/Biography above. The
			     create action only sends full_name + is_justice (D-08); Birth Date
			     and Tenure Period rows need a person id to attach to
			     (_replace_tenures writes FK rows) and would otherwise render as
			     live, interactive inputs whose values are silently discarded on
			     submit with no warning. Filled in on the editor after redirect. ── -->
		</div>

		<!-- Form-level error (from create action) -->
		{#if form?.error}
			<p role="alert" style="color: #ef4444; font-size: 14px; margin: 0 0 8px 0;">
				{form.error}
			</p>
		{/if}

		<!-- ── Merge (PADM-03/PADM-04) and Delete (PADM-02): intentionally absent
		     from this route (Claude's Discretion item 3, PEDIT-11/PEDIT-12) —
		     there is nothing to merge or delete before the person exists, and
		     this route has no `merge`/`delete` actions for such a form to
		     submit to. The [id] editor reuses this same card structure with a
		     `{#if data.person.id}` guard once a person record is present. ── -->

		<!-- ── Form-level action row: Save Person + Cancel ── -->
		<div style="display: flex; gap: 8px;">
			<button
				type="submit"
				form="create-form"
				disabled={saveSubmitting}
				style="flex: 1; min-height: 44px; background: transparent; border: 1px solid #93c5fd; border-radius: 6px; font-size: 16px; font-weight: 600; color: #e2e8f0; cursor: pointer; opacity: {saveSubmitting ? 0.7 : 1};"
			>
				{saveSubmitting ? 'Saving…' : 'Save Person'}
			</button>
			<a
				href="/admin/people"
				style="flex: 1; display: inline-flex; align-items: center; justify-content: center; min-height: 44px; background: transparent; border: 1px solid #334155; border-radius: 6px; font-size: 16px; font-weight: 400; color: #94a3b8; text-decoration: none; box-sizing: border-box;"
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
</style>
