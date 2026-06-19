<script lang="ts">
	import { enhance } from '$app/forms';

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
	}

	interface RoleItem {
		id: number;
		name: string;
	}

	// ──────────────────────────────────────────────────────────────────────────
	// Role select state (Pattern 3 — inline role creation via use:enhance)
	// ──────────────────────────────────────────────────────────────────────────

	// Sentinel value for the "add new role" option
	const ADD_NEW_ROLE_SENTINEL = '__add_new_role__';

	// Local roles list — seeded from server data; new roles appended on createRole success
	let localRoles = $state<RoleItem[]>([...(data.roles ?? [])]);

	// Currently selected role id (as string for the <select> value binding)
	let selectedRoleId = $state<string>(
		data.person.role_id !== null ? String(data.person.role_id) : ''
	);

	// Whether the inline add-role form is visible
	let showAddRoleForm = $state(false);

	// The role id that was selected before the sentinel was chosen; restored on cancel
	let roleIdBeforeSentinel = $state<string>('');

	// Error from the createRole action
	let roleError = $state<string | null>(null);

	// Whether the createRole form is submitting
	let creatingRole = $state(false);

	function handleRoleChange(e: Event) {
		const val = (e.target as HTMLSelectElement).value;
		if (val === ADD_NEW_ROLE_SENTINEL) {
			// Record the previously-selected value so it can be restored on cancel
			roleIdBeforeSentinel = selectedRoleId;
			showAddRoleForm = true;
		} else {
			selectedRoleId = val;
			showAddRoleForm = false;
		}
	}

	function cancelAddRole() {
		// Restore the previously-selected role and hide the inline form
		selectedRoleId = roleIdBeforeSentinel;
		showAddRoleForm = false;
	}

	// ──────────────────────────────────────────────────────────────────────────
	// Tenure rows state (Pattern 1 — $state<TenureRow[]>, in-place mutation)
	// Each row gets a stable _key for the keyed {#each} block (Pitfall 2)
	// ──────────────────────────────────────────────────────────────────────────

	let nextKey = $state(1);

	// Initialise from server data — map existing tenures to add _key
	let tenureRows = $state<TenureRow[]>(
		(data.person.tenures ?? []).map(
			(t: { seat: string | null; start_date: string | null; end_date: string | null }) => ({
				_key: nextKey++,
				seat: t.seat ?? '',
				start_date: t.start_date ?? '',
				end_date: t.end_date ?? '',
			})
		)
	);

	function addTenureRow() {
		tenureRows.push({ _key: nextKey++, seat: '', start_date: '', end_date: '' });
	}

	function removeTenureRow(index: number) {
		tenureRows.splice(index, 1);
	}

	// ──────────────────────────────────────────────────────────────────────────
	// Save button submitting state
	// ──────────────────────────────────────────────────────────────────────────

	let saveSubmitting = $state(false);
</script>

<main style="background-color: #0f1117; min-height: 100vh;">
	<header style="background-color: #1e293b; border-bottom: 1px solid #334155; padding: 16px 24px;">
		<a
			href="/admin/people"
			style="font-size: 14px; color: #94a3b8; text-decoration: none;"
		>
			← People
		</a>
		<h1 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 4px 0 0 0; line-height: 1.2;">
			{data.person.full_name}
		</h1>
	</header>

	<div style="max-width: 640px; margin: 0 auto; padding: 48px 24px;">
		<form
			method="POST"
			action="?/save"
			use:enhance={() => {
				saveSubmitting = true;
				return async ({ result, update }) => {
					saveSubmitting = false;
					if (result.type === 'redirect') {
						await update();
					} else {
						await update();
					}
				};
			}}
		>
			<!-- ── Section 1: Basic Info ── -->
			<div
				style="background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px; margin-bottom: 24px;"
			>
				<h2
					style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 16px 0; line-height: 1.2;"
				>
					Basic Info
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
				<div style="margin-bottom: 16px;">
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

				<!-- Role select -->
				<div style="margin-bottom: 0;">
					<label
						for="role_id"
						style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;"
					>
						Role
					</label>
					<select
						id="role_id"
						name="role_id"
						bind:value={selectedRoleId}
						aria-expanded={showAddRoleForm}
						onchange={handleRoleChange}
						style="display: block; width: 100%; background-color: #0f1117; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #e2e8f0; box-sizing: border-box;"
					>
						<option value="">— No role —</option>
						{#each localRoles as role (role.id)}
							<option value={String(role.id)}>
								{role.name}
							</option>
						{/each}
						<option value={ADD_NEW_ROLE_SENTINEL}>＋ Add new role</option>
					</select>

					<!-- AddRoleInlineForm: shown when "＋ Add new role" is selected -->
					{#if showAddRoleForm}
						<div
							style="margin-top: 8px; padding: 12px; background-color: #0f1117; border: 1px solid #334155; border-radius: 6px;"
						>
							<form
								method="POST"
								action="?/createRole"
								use:enhance={() => {
									creatingRole = true;
									roleError = null;
									return async ({ result }) => {
										creatingRole = false;
										if (result.type === 'success') {
											const data = result.data as {
												roleCreated?: boolean;
												role?: { id: number; name: string };
											};
											if (data?.roleCreated && data.role) {
												// Add new role to local list, select it, collapse form
												localRoles.push(data.role);
												selectedRoleId = String(data.role.id);
												showAddRoleForm = false;
											}
										} else if (result.type === 'failure') {
											const errData = result.data as { roleError?: string };
											roleError = errData?.roleError ?? 'Could not create role. Try again.';
										}
									};
								}}
							>
								<div style="margin-bottom: 8px;">
									<label
										for="role_name"
										style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;"
									>
										Role name
									</label>
									<input
										id="role_name"
										name="role_name"
										type="text"
										style="display: block; width: 100%; background-color: #0f1117; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #e2e8f0; box-sizing: border-box;"
									/>
								</div>

								{#if roleError}
									<p role="alert" style="color: #ef4444; font-size: 14px; margin: 0 0 8px 0;">
										{roleError}
									</p>
								{/if}

								<div style="display: flex; gap: 8px; margin-top: 8px;">
									<button
										type="submit"
										disabled={creatingRole}
										style="font-size: 14px; font-weight: 600; color: #e2e8f0; background: transparent; border: 1px solid #93c5fd; border-radius: 6px; padding: 8px 16px; min-height: 36px; cursor: pointer;"
									>
										{creatingRole ? 'Creating…' : 'Create role'}
									</button>
									<button
										type="button"
										onclick={cancelAddRole}
										style="font-size: 14px; font-weight: 400; color: #94a3b8; background: transparent; border: 1px solid #334155; border-radius: 6px; padding: 8px 16px; min-height: 36px; cursor: pointer;"
									>
										Cancel
									</button>
								</div>
							</form>
						</div>
					{/if}
				</div>
			</div>

			<!-- ── Section 2: Bio & Photo ── -->
			<div
				style="background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px; margin-bottom: 24px;"
			>
				<h2
					style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 16px 0; line-height: 1.2;"
				>
					Bio &amp; Photo
				</h2>

				<!-- Bio text -->
				<div style="margin-bottom: 16px;">
					<label
						for="bio_text"
						style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;"
					>
						Bio
					</label>
					<textarea
						id="bio_text"
						name="bio_text"
						style="display: block; width: 100%; background-color: #0f1117; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #e2e8f0; box-sizing: border-box; min-height: 120px; resize: vertical; font-family: inherit;"
					>{data.person.bio_text ?? ''}</textarea>
				</div>

				<!-- Photo URL -->
				<div style="margin-bottom: 0;">
					<label
						for="photo_url"
						style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;"
					>
						Photo URL
					</label>
					<input
						id="photo_url"
						name="photo_url"
						type="text"
						value={data.person.photo_url ?? ''}
						placeholder="https://…"
						style="display: block; width: 100%; background-color: #0f1117; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #e2e8f0; box-sizing: border-box;"
					/>
				</div>
			</div>

			<!-- ── Section 3: Court Tenure ── -->
			<div
				style="background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px; margin-bottom: 24px;"
			>
				<h2
					style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 16px 0; line-height: 1.2;"
				>
					Court Tenure
				</h2>

				<!-- TenureRowList (D-08): all rows shown; keyed by _key (Pitfall 2) -->
				{#each tenureRows as row, i (row._key)}
					<div
						style="display: flex; gap: 16px; align-items: flex-start; margin-bottom: 16px;"
					>
						<!-- Seat -->
						<div style="flex: 40%;">
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
								style="display: block; width: 100%; background-color: #0f1117; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #e2e8f0; box-sizing: border-box;"
							/>
						</div>

						<!-- Start date -->
						<div style="flex: 25%;">
							<label
								for="tenure-start-{row._key}"
								style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;"
							>
								Start date
							</label>
							<input
								id="tenure-start-{row._key}"
								type="date"
								bind:value={row.start_date}
								style="display: block; width: 100%; background-color: #0f1117; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #e2e8f0; box-sizing: border-box;"
							/>
						</div>

						<!-- End date -->
						<div style="flex: 25%;">
							<label
								for="tenure-end-{row._key}"
								style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;"
							>
								End date
							</label>
							<input
								id="tenure-end-{row._key}"
								type="date"
								bind:value={row.end_date}
								style="display: block; width: 100%; background-color: #0f1117; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #e2e8f0; box-sizing: border-box;"
							/>
						</div>

						<!-- Trash button (D-09): removes row from $state; no server call -->
						<div style="flex: 10%; align-self: flex-end; padding-bottom: 2px;">
							<button
								type="button"
								aria-label="Remove tenure row"
								onclick={() => removeTenureRow(i)}
								style="color: #ef4444; background: transparent; border: none; cursor: pointer; font-size: 18px; min-height: 32px; padding: 4px 8px;"
							>
								✕
							</button>
						</div>
					</div>
				{/each}

				<!-- Add tenure button (D-09) -->
				<button
					type="button"
					onclick={addTenureRow}
					style="display: block; width: 100%; margin-top: 8px; font-size: 14px; font-weight: 400; color: #94a3b8; background: transparent; border: 1px solid #334155; border-radius: 6px; padding: 8px 16px; min-height: 44px; cursor: pointer; text-align: center;"
				>
					Add tenure
				</button>

				<!-- Hidden field carrying the serialized tenure array (Pattern 1 / Pitfall 3) -->
				<input type="hidden" name="tenures" value={JSON.stringify(tenureRows)} />
			</div>

			<!-- ── Section 4: Appointment ── -->
			<div
				style="background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px; margin-bottom: 24px;"
			>
				<h2
					style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 16px 0; line-height: 1.2;"
				>
					Appointment
				</h2>

				<!-- Appointed by -->
				<div style="margin-bottom: 16px;">
					<label
						for="appointing_president"
						style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;"
					>
						Appointed by
					</label>
					<input
						id="appointing_president"
						name="appointing_president"
						type="text"
						value={data.person.appointing_president ?? ''}
						style="display: block; width: 100%; background-color: #0f1117; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #e2e8f0; box-sizing: border-box;"
					/>
				</div>

				<!-- Appointing president's party -->
				<div style="margin-bottom: 0;">
					<label
						for="appointing_president_party"
						style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;"
					>
						Appointing president's party
					</label>
					<select
						id="appointing_president_party"
						name="appointing_president_party"
						style="display: block; width: 100%; background-color: #0f1117; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #e2e8f0; box-sizing: border-box;"
					>
						<option value="" selected={!data.person.appointing_president_party}>— No party —</option>
						<option value="Democratic" selected={data.person.appointing_president_party === 'Democratic'}>Democratic</option>
						<option value="Democratic-Republican" selected={data.person.appointing_president_party === 'Democratic-Republican'}>Democratic-Republican</option>
						<option value="Federalist" selected={data.person.appointing_president_party === 'Federalist'}>Federalist</option>
						<option value="Independent" selected={data.person.appointing_president_party === 'Independent'}>Independent</option>
						<option value="Republican" selected={data.person.appointing_president_party === 'Republican'}>Republican</option>
						<option value="Whig" selected={data.person.appointing_president_party === 'Whig'}>Whig</option>
					</select>
				</div>
			</div>

			<!-- Form-level error (from save action) -->
			{#if form?.error}
				<p role="alert" style="color: #ef4444; font-size: 14px; margin: 0 0 8px 0;">
					{form.error}
				</p>
			{/if}

			<!-- SaveChangesButton (UI-SPEC): full-width, accent border, disabled while submitting -->
			<button
				type="submit"
				disabled={saveSubmitting}
				style="display: block; width: 100%; min-height: 44px; background: transparent; border: 1px solid #93c5fd; border-radius: 6px; font-size: 16px; font-weight: 600; color: #e2e8f0; cursor: pointer; margin-top: 8px; opacity: {saveSubmitting ? 0.7 : 1};"
			>
				{saveSubmitting ? 'Saving…' : 'Save changes'}
			</button>
		</form>
	</div>
</main>

<style>
	@media (max-width: 640px) {
		.name-parts-grid {
			grid-template-columns: 1fr 1fr !important;
		}
	}
</style>
