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
	// Person Type — Bench/Advocate segmented toggle (D-13, replaces "Is Justice"
	// checkbox) + Bench-only Birth Date. The Role field and its inline-creation
	// machinery (select, "+ Add new role" sentinel, createRole action) are
	// fully removed per D-10 — none of it is carried forward into this card.
	// ──────────────────────────────────────────────────────────────────────────

	let isJustice = $state<boolean>(data.person.is_justice ?? false);
	let birthdate = $state<string>(data.person.birthdate ?? '');

	// ──────────────────────────────────────────────────────────────────────────
	// Tenure rows state (Pattern 1 — $state<TenureRow[]>, in-place mutation)
	// Each row gets a stable _key for the keyed {#each} block (Pitfall 2).
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

<main style="background-color: #0f1117; min-height: 100vh;">
	<header style="background-color: #1e293b; border-bottom: 1px solid #334155; padding: 16px 24px;">
		<nav aria-label="Breadcrumb" style="font-size: 14px; font-weight: 400; line-height: 1.4;">
			<a href={'/admin/people?tab=' + backTab} style="color: #93c5fd; text-decoration: none;">People</a>
			<span style="color: #94a3b8;"> &gt; </span>
			<span style="color: #94a3b8;">{data.person.full_name}</span>
		</nav>
		<h1 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 4px 0 0 0; line-height: 1.2;">
			{data.person.full_name}
		</h1>
	</header>

	<div style="max-width: 640px; margin: 0 auto; padding: 48px 24px;">

		<!-- ══════════════════════════════════════════════════════════════════════
		     Main save form — covers Identity + Person Type (is_justice/birthdate/
		     tenures). Bio & Photo are managed by a separate form below (Pitfall 7
		     extended). IMPORTANT: no enctype on this form (Pitfall 1). The form
		     closes right after the Identity card — the Person Type card's inputs
		     live outside this element but associate via the `form="save-form"`
		     attribute (same cross-form idiom already used for the standalone
		     Save Person button, Gap E fix).
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

		<!-- ── Photo card + Biography card: single form (bio_text + photo widget), SEPARATE
		     form outside save-form (Pitfall 1). Bio saves together with photo on every
		     photo action submit (Pitfall 7 extended) — unchanged behavior, just split
		     into two visually distinct cards per the UI-SPEC card order. ── -->
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
				style="background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px; margin-bottom: 24px;"
			>
				<h2
					style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 16px 0; line-height: 1.2;"
				>
					Photo
				</h2>

				<!-- Photo preview: 80×80 circle — image or initials fallback -->
				<div style="margin-bottom: 16px;">
					{#if data.person.photo_url_full}
						<img
							src={data.person.photo_url_full}
							alt="{data.person.full_name} profile photo"
							style="width: 80px; height: 80px; border-radius: 50%; object-fit: cover; border: 1px solid #334155;"
						/>
					{:else}
						<div
							aria-hidden="true"
							style="width: 80px; height: 80px; border-radius: 50%; background-color: #334155; color: #94a3b8; font-size: 28px; font-weight: 600; display: flex; align-items: center; justify-content: center; user-select: none;"
						>
							{(data.person.full_name ?? '').charAt(0).toUpperCase()}
						</div>
					{/if}
				</div>

				<!-- Tab bar -->
				<div style="display: flex; gap: 0; margin-bottom: 16px; border-bottom: 1px solid #334155;">
					<button
						type="button"
						onclick={() => (photoTab = 'upload')}
						style="padding: 8px 16px; font-size: 14px; font-weight: 400; background: transparent; border: none; border-bottom: {photoTab === 'upload' ? '2px solid #93c5fd' : '2px solid transparent'}; color: {photoTab === 'upload' ? '#e2e8f0' : '#94a3b8'}; cursor: pointer; margin-bottom: -1px;"
					>
						Upload file
					</button>
					<button
						type="button"
						onclick={() => (photoTab = 'url')}
						style="padding: 8px 16px; font-size: 14px; font-weight: 400; background: transparent; border: none; border-bottom: {photoTab === 'url' ? '2px solid #93c5fd' : '2px solid transparent'}; color: {photoTab === 'url' ? '#e2e8f0' : '#94a3b8'}; cursor: pointer; margin-bottom: -1px;"
					>
						Enter URL
					</button>
				</div>

				<!-- Tab panel -->
				{#if photoTab === 'upload'}
					<div style="margin-bottom: 16px;">
						<input
							type="file"
							name="photo_file"
							accept="image/*"
							style="display: block; width: 100%; min-height: 44px; background-color: #0f1117; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #e2e8f0; box-sizing: border-box; cursor: pointer;"
						/>
					</div>
				{:else}
					<div style="margin-bottom: 16px;">
						<input
							type="text"
							name="photo_url"
							placeholder="https://…"
							style="display: block; width: 100%; background-color: #0f1117; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #e2e8f0; box-sizing: border-box;"
						/>
					</div>
				{/if}

				{#if form?.photoError}
					<p role="alert" style="color: #ef4444; font-size: 14px; margin: 0 0 8px 0;">
						{form.photoError}
					</p>
				{/if}

				<button
					type="submit"
					disabled={photoSubmitting}
					style="display: block; width: 100%; min-height: 44px; background: transparent; border: 1px solid #93c5fd; border-radius: 6px; font-size: 16px; font-weight: 600; color: #e2e8f0; cursor: pointer; opacity: {photoSubmitting ? 0.7 : 1};"
				>
					{photoSubmitting ? 'Uploading…' : 'Upload photo'}
				</button>
			</div>

			<!-- ── Biography card ── -->
			<div
				style="background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px; margin-bottom: 24px;"
			>
				<h2
					style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 16px 0; line-height: 1.2;"
				>
					Biography
				</h2>

				<!-- bio_text submitted via this form; excluded from the save action (Pitfall 7 extended) -->
				<div>
					<label
						for="bio_text"
						style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;"
					>
						Bio
					</label>
					<textarea
						id="bio_text"
						name="bio_text"
						placeholder="Enter a short biography…"
						style="display: block; width: 100%; background-color: #0f1117; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #e2e8f0; box-sizing: border-box; min-height: 120px; resize: vertical; font-family: inherit;"
					>{data.person.bio_text ?? ''}</textarea>
				</div>
			</div>
		</form>

		<!-- ── Person Type card (new, D-13) — Bench/Advocate segmented toggle replaces the
		     old "Is Justice" checkbox; Bench-only fields slide-reveal (D-11). The Role
		     field and its inline-creation machinery are fully removed (D-10) — not
		     carried into this card at all. Inputs associate with save-form via the
		     `form` attribute since this card sits outside that <form> element. ── -->
		<div
			style="background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px; margin-bottom: 24px;"
		>
			<h2
				style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 16px 0; line-height: 1.2;"
			>
				Person Type
			</h2>

			<!-- Bench/Advocate segmented toggle (D-13) — same visual idiom as the list-page tab toggle -->
			<div style="display: flex; gap: 0; margin-bottom: 16px;">
				<button
					type="button"
					aria-pressed={isJustice}
					aria-label="Bench"
					onclick={() => (isJustice = true)}
					style="
						min-height: 44px;
						padding: 8px 16px;
						border: 1px solid {isJustice ? '#93c5fd' : '#334155'};
						border-radius: 6px 0 0 6px;
						background-color: {isJustice ? '#93c5fd' : '#1e293b'};
						color: {isJustice ? '#0f1117' : '#e2e8f0'};
						font-size: 16px;
						font-weight: 600;
						cursor: pointer;
					"
				>Bench</button>
				<button
					type="button"
					aria-pressed={!isJustice}
					aria-label="Advocate"
					onclick={() => (isJustice = false)}
					style="
						min-height: 44px;
						padding: 8px 16px;
						border: 1px solid {!isJustice ? '#93c5fd' : '#334155'};
						border-left: none;
						border-radius: 0 6px 6px 0;
						background-color: {!isJustice ? '#93c5fd' : '#1e293b'};
						color: {!isJustice ? '#0f1117' : '#e2e8f0'};
						font-size: 16px;
						font-weight: 600;
						cursor: pointer;
					"
				>Advocate</button>
			</div>

			<!-- Carries the toggle's boolean value into the save-form; always present
			     regardless of which segment is selected (a segmented toggle always
			     submits a value, unlike the old checkbox which was absent when unchecked). -->
			<input type="hidden" name="is_justice" form="save-form" value={isJustice ? 'true' : 'false'} />

			{#if isJustice}
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
							form="save-form"
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
						<!-- Seat (PEDIT-09) — carried through state since Plan 27-05 but never
						     rendered; D-18's mockup-derived field list omitted it with no stated
						     reason, silently narrowing the locked PEDIT-09 wording. Restored per
						     phase 27 verification gap closure. -->
						<div style="margin-bottom: 16px;">
							<label
								for="tenure-seat-{row._key}"
								style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;"
							>
								Seat
							</label>
							<input
								id="tenure-seat-{row._key}"
								type="text"
								bind:value={row.seat}
								style="display: block; width: 100%; background-color: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #e2e8f0; box-sizing: border-box;"
							/>
						</div>

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

				<!-- Hidden field carrying the serialized tenure array (Pattern 1 / Pitfall 3) -->
				<input type="hidden" name="tenures" form="save-form" value={JSON.stringify(tenureRows)} />
			</div>
			{/if}
		</div>

		<!-- Form-level error (from save action) -->
		{#if form?.error}
			<p role="alert" style="color: #ef4444; font-size: 14px; margin: 0 0 8px 0;">
				{form.error}
			</p>
		{/if}

		<!-- ── Merge (PADM-03/PADM-04) — outside the save form; hidden on the create route (D-07 shared template) ── -->
		{#if data.person.id}
		<div
			style="background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px; margin-bottom: 24px;"
		>
			<h2
				style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 16px 0; line-height: 1.2;"
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
				<div style="margin-bottom: 16px;">
					<label
						for="merge_target_id"
						style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;"
					>
						Merge this person into
					</label>
					<select
						id="merge_target_id"
						bind:value={mergeTargetId}
						onchange={(e) => fetchMergePreview((e.target as HTMLSelectElement).value)}
						style="display: block; width: 100%; background-color: #0f1117; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #e2e8f0; box-sizing: border-box;"
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
						style="background-color: #0f1117; border: 1px solid #334155; border-radius: 6px; padding: 16px; margin-bottom: 16px;"
					>
						{#if mergeLoading}
							<p style="font-size: 14px; color: #94a3b8; margin: 0;">Loading…</p>
						{:else if mergeError}
							<p role="alert" style="font-size: 14px; color: #ef4444; margin: 0;">{mergeError}</p>
						{:else if mergePreview}
							{@const targetPerson = (data.people ?? []).find((p: { id: number }) => String(p.id) === mergeTargetId)}
							<p style="font-size: 14px; color: #94a3b8; margin: 0 0 8px 0;">
								This will transfer from <strong style="color: #e2e8f0;">{data.person.full_name}</strong> to <strong style="color: #e2e8f0;">{targetPerson?.full_name ?? targetPerson?.last_name ?? 'selected person'}</strong>:
							</p>
							{#if mergePreview.utterances === 0 && mergePreview.aliases === 0 && mergePreview.appearances === 0 && mergePreview.argument_participants === 0}
								<p style="font-size: 14px; color: #94a3b8; margin: 0;">
									No records to transfer. This person has no associated data.
								</p>
							{:else}
								<p style="font-size: 14px; color: #e2e8f0; margin: 0;">
									{mergePreview.utterances} utterance(s) · {mergePreview.aliases} alias(es) · {mergePreview.appearances} appearance(s) · {mergePreview.argument_participants} argument participant(s)
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
						style="display: block; width: 100%; min-height: 44px; background: transparent; border: 1px solid #93c5fd; border-radius: 6px; font-size: 16px; font-weight: 600; color: #e2e8f0; cursor: pointer; opacity: {mergeSubmitting ? 0.7 : 1};"
					>
						{mergeSubmitting ? 'Merging…' : `Merge ${data.person.full_name} into ${confirmTargetPerson?.full_name ?? confirmTargetPerson?.last_name ?? 'selected person'}`}
					</button>
				{/if}

				{#if form?.mergeError}
					<p role="alert" style="color: #ef4444; font-size: 14px; margin: 8px 0 0 0;">
						{form.mergeError}
					</p>
				{/if}
			</form>
		</div>
		{/if}

		<!-- ── Delete (PADM-02) — outside the save form; hidden on the create route (D-07 shared template) ── -->
		{#if data.person.id}
		<div
			style="background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px; margin-bottom: 24px;"
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
						style="display: block; width: 100%; min-height: 44px; background: transparent; border: 1px solid #ef4444; border-radius: 6px; font-size: 16px; font-weight: 600; color: #ef4444; cursor: pointer; opacity: {deleteSubmitting ? 0.7 : 1};"
					>
						{deleteSubmitting ? 'Deleting…' : 'Delete person'}
					</button>
				{:else}
					<button
						type="submit"
						disabled
						aria-describedby="delete-tip"
						style="display: block; width: 100%; min-height: 44px; background: transparent; border: 1px solid #334155; border-radius: 6px; font-size: 16px; font-weight: 600; color: #94a3b8; cursor: not-allowed; opacity: 0.7;"
					>
						Delete person
					</button>
					<p
						id="delete-tip"
						style="font-size: 14px; color: #94a3b8; margin-top: 8px; text-align: center;"
					>
						Cannot delete — this person has associated records and cannot be removed.
					</p>
				{/if}

				{#if form?.deleteError}
					<p role="alert" style="color: #ef4444; font-size: 14px; margin: 8px 0 0 0;">
						{form.deleteError}
					</p>
				{/if}
			</form>
		</div>
		{/if}

		<!-- ── Form-level action row: Save Person + Cancel ── -->
		<div style="display: flex; gap: 8px;">
			<button
				type="submit"
				form="save-form"
				disabled={saveSubmitting}
				style="flex: 1; min-height: 44px; background: transparent; border: 1px solid #93c5fd; border-radius: 6px; font-size: 16px; font-weight: 600; color: #e2e8f0; cursor: pointer; opacity: {saveSubmitting ? 0.7 : 1};"
			>
				{saveSubmitting ? 'Saving…' : 'Save Person'}
			</button>
			<a
				href={'/admin/people?tab=' + backTab}
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
