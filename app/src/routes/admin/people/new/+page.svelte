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

<main style="background-color: var(--color-bg); min-height: 100vh;">
	<header style="background-color: var(--color-surface); border-bottom: 1px solid var(--color-border); padding: var(--space-md) var(--space-lg);">
		<nav aria-label="Breadcrumb" style="font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); line-height: 1.4;">
			<a href="/admin/people" style="color: var(--color-accent); text-decoration: none;">People</a>
			<span style="color: var(--color-text-secondary);"> &gt; </span>
			<span style="color: var(--color-text-secondary);">Create Person</span>
		</nav>
		<h1 style="font-size: var(--font-size-heading); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); margin: var(--space-xs) 0 0 0; line-height: 1.2;">
			Create Person
		</h1>
	</header>

	<div style="max-width: 640px; margin: 0 auto; padding: var(--space-2xl) var(--space-lg);">

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
				     than marking both fields individually required. -->
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
			style="background-color: var(--color-surface); border: 1px solid var(--color-border); border-radius: 8px; padding: var(--space-lg); margin-bottom: var(--space-lg);"
		>
			<h2
				style="font-size: var(--font-size-heading); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); margin: 0 0 var(--space-md) 0; line-height: 1.2;"
			>
				Person Type
			</h2>

			<!-- Bench/Advocate segmented toggle (D-13) — same visual idiom as the list-page tab toggle.
			     Neither button reads as selected while isJustice is null. -->
			<div style="display: flex; gap: 0; margin-bottom: var(--space-md);">
				<button
					type="button"
					aria-pressed={isJustice === true}
					aria-label="Bench"
					onclick={() => (isJustice = true)}
					style="
						min-height: var(--touch-target);
						padding: var(--space-sm) var(--space-md);
						border: 1px solid {isJustice === true ? 'var(--color-accent)' : 'var(--color-border)'};
						border-radius: 6px 0 0 6px;
						background-color: {isJustice === true ? 'var(--color-accent)' : 'var(--color-surface)'};
						color: {isJustice === true ? 'var(--color-bg)' : 'var(--color-text-primary)'};
						font-size: var(--font-size-body);
						font-weight: var(--font-weight-semibold);
						cursor: pointer;
					"
				>Bench</button>
				<button
					type="button"
					aria-pressed={isJustice === false}
					aria-label="Advocate"
					onclick={() => (isJustice = false)}
					style="
						min-height: var(--touch-target);
						padding: var(--space-sm) var(--space-md);
						border: 1px solid {isJustice === false ? 'var(--color-accent)' : 'var(--color-border)'};
						border-left: none;
						border-radius: 0 6px 6px 0;
						background-color: {isJustice === false ? 'var(--color-accent)' : 'var(--color-surface)'};
						color: {isJustice === false ? 'var(--color-bg)' : 'var(--color-text-primary)'};
						font-size: var(--font-size-body);
						font-weight: var(--font-weight-semibold);
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
			<p role="alert" style="color: var(--color-destructive); font-size: var(--font-size-caption); margin: 0 0 var(--space-sm) 0;">
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
		<div style="display: flex; gap: var(--space-sm);">
			<button
				type="submit"
				form="create-form"
				disabled={saveSubmitting}
				style="flex: 1; min-height: var(--touch-target); background: transparent; border: 1px solid var(--color-accent); border-radius: 6px; font-size: var(--font-size-body); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); cursor: pointer; opacity: {saveSubmitting ? 0.7 : 1};"
			>
				{saveSubmitting ? 'Saving…' : 'Save Person'}
			</button>
			<a
				href="/admin/people"
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
</style>
