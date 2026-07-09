<script lang="ts">
	import { enhance } from '$app/forms';
	import { slide } from 'svelte/transition';

	let { data, form } = $props();

	// ──────────────────────────────────────────────────────────────────────────
	// Types
	// ──────────────────────────────────────────────────────────────────────────

	interface TenureRow {
		_key: number;
		id?: number;
		seat: string;
		start_date: string;
		end_date: string;
		appointed_by: string;
		appointing_president_party: string;
	}

	// ──────────────────────────────────────────────────────────────────────────
	// Person Type — Bench/Advocate segmented toggle (D-13), adapted from the
	// [id] editor template (D-07) with one difference: `isJustice` is a
	// three-state boolean|null so NEITHER segment is pre-selected on first
	// render (D-08 — an explicit choice is required before create can submit).
	// The Role field and its inline-creation machinery are not carried into
	// this card at all (D-10, matches the [id] template).
	// ──────────────────────────────────────────────────────────────────────────

	let isJustice = $state<boolean | null>(data.person.is_justice);
	let birthdate = $state<string>(data.person.birthdate ?? '');

	// ──────────────────────────────────────────────────────────────────────────
	// Tenure rows state (Pattern 1 — $state<TenureRow[]>, in-place mutation).
	// Starts empty on create; matches the [id] template's mapping shape so the
	// same tenure sub-card markup renders identically once Bench is selected.
	// Per D-08, this array is NOT sent by the create action — an operator who
	// adds rows here before the first save fills them in again on the editor
	// after redirect (see "Decisions Made" in the plan 27-06 SUMMARY).
	// ──────────────────────────────────────────────────────────────────────────

	let nextKey = $state(1);

	let tenureRows = $state<TenureRow[]>(
		(data.person.tenures ?? []).map(
			(t: {
				seat: string | null;
				start_date: string | null;
				end_date: string | null;
				appointed_by: string | null;
				appointing_president_party: string | null;
			}) => ({
				_key: nextKey++,
				seat: t.seat ?? '',
				start_date: t.start_date ?? '',
				end_date: t.end_date ?? '',
				appointed_by: t.appointed_by ?? '',
				appointing_president_party: t.appointing_president_party ?? '',
			})
		)
	);

	function addTenureRow() {
		tenureRows.push({
			_key: nextKey++,
			seat: '',
			start_date: '',
			end_date: '',
			appointed_by: '',
			appointing_president_party: '',
		});
	}

	function removeTenureRow(index: number) {
		tenureRows.splice(index, 1);
	}

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

				<!-- Full name -->
				<div style="margin-bottom: 16px;">
					<label
						for="full_name"
						style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;"
					>
						Full name
					</label>
					<input
						id="full_name"
						name="full_name"
						type="text"
						value={data.person.full_name}
						style="display: block; width: 100%; background-color: #0f1117; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #e2e8f0; box-sizing: border-box;"
					/>
				</div>

				<!-- Name parts — 4-column on desktop, 2-column on mobile -->
				<div>
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
								value={data.person.first_name ?? ''}
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
								value={data.person.middle_name ?? ''}
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
								value={data.person.last_name ?? ''}
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
								value={data.person.name_suffix ?? ''}
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

			{#if isJustice === true}
			<div transition:slide>
				<!-- Birth Date + disabled Death Date (D-15, D-19) -->
				<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
					<div>
						<label
							for="birthdate"
							style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;"
						>
							Birth Date
						</label>
						<input
							id="birthdate"
							type="date"
							name="birthdate"
							form="create-form"
							bind:value={birthdate}
							style="display: block; width: 100%; background-color: #0f1117; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #e2e8f0; box-sizing: border-box;"
						/>
					</div>
					<div style="opacity: 0.6;">
						<label
							for="death_date"
							style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;"
						>
							Death Date
						</label>
						<input
							id="death_date"
							type="date"
							disabled
							placeholder="Coming soon"
							title="Tracked in a future update"
							style="display: block; width: 100%; background-color: #0f1117; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #94a3b8; box-sizing: border-box;"
						/>
					</div>
				</div>

				<h3 style="font-size: 16px; font-weight: 400; color: #e2e8f0; margin: 0 0 16px 0; line-height: 1.2;">
					Tenure Periods
				</h3>

				<!-- Tenure Period sub-cards (D-18): bordered, inset background -->
				{#each tenureRows as row, i (row._key)}
					<div
						style="background-color: #0f1117; border: 1px solid #334155; border-radius: 6px; padding: 24px; margin-bottom: 16px;"
					>
						<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
							<div>
								<label
									for="tenure-start-{row._key}"
									style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;"
								>
									Start Date
								</label>
								<input
									id="tenure-start-{row._key}"
									type="date"
									bind:value={row.start_date}
									style="display: block; width: 100%; background-color: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #e2e8f0; box-sizing: border-box;"
								/>
							</div>
							<div>
								<label
									for="tenure-end-{row._key}"
									style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;"
								>
									End Date
								</label>
								<input
									id="tenure-end-{row._key}"
									type="date"
									bind:value={row.end_date}
									style="display: block; width: 100%; background-color: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #e2e8f0; box-sizing: border-box;"
								/>
							</div>
						</div>

						<div style="margin-bottom: 16px;">
							<label
								for="tenure-appointed-{row._key}"
								style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;"
							>
								Appointing President
							</label>
							<input
								id="tenure-appointed-{row._key}"
								type="text"
								bind:value={row.appointed_by}
								style="display: block; width: 100%; background-color: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #e2e8f0; box-sizing: border-box;"
							/>
						</div>

						<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
							<div>
								<label
									for="tenure-party-{row._key}"
									style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;"
								>
									President's Party
								</label>
								<input
									id="tenure-party-{row._key}"
									type="text"
									bind:value={row.appointing_president_party}
									style="display: block; width: 100%; background-color: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #e2e8f0; box-sizing: border-box;"
								/>
							</div>
							<div style="opacity: 0.6;">
								<label
									for="tenure-reason-{row._key}"
									style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;"
								>
									Reason Left
								</label>
								<input
									id="tenure-reason-{row._key}"
									type="text"
									disabled
									placeholder="Coming soon"
									title="Tracked in a future update"
									style="display: block; width: 100%; background-color: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #94a3b8; box-sizing: border-box;"
								/>
							</div>
						</div>

						<div style="text-align: right;">
							<button
								type="button"
								onclick={() => removeTenureRow(i)}
								style="color: #ef4444; background: transparent; border: 1px solid #ef4444; border-radius: 6px; font-size: 14px; font-weight: 400; min-height: 36px; padding: 4px 16px; cursor: pointer;"
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
					style="display: inline-block; font-size: 14px; font-weight: 400; color: #93c5fd; background: transparent; border: none; padding: 0; cursor: pointer;"
				>
					+ Add Tenure Period
				</button>

				<!-- Hidden field carrying the serialized tenure array (Pattern 1 / Pitfall 3) —
				     not read by the create action (D-08); kept for structural parity with the
				     [id] template so switching this card between Bench/Advocate never loses
				     in-progress rows before the operator saves. -->
				<input type="hidden" name="tenures" form="create-form" value={JSON.stringify(tenureRows)} />
			</div>
			{/if}
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
