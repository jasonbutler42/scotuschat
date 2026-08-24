<script lang="ts">
	import { Popover } from 'bits-ui';
	import { enhance } from '$app/forms';

	// Phase 25 — Mini create-person popover (D-12, D-13, PJOB-19).
	// Captures name plus a Bench/Advocate choice only; full profile completion
	// (bio/photo/tenure) happens later in People Admin (Phase 27), never here.
	// Submits to the parent page's existing ?/addPerson action.

	interface CreatedPerson {
		id: number;
		full_name: string;
		role_name: string | null;
	}

	interface CreatePersonPopoverProps {
		rawSpeakerLabel: string;
		triggerLabel?: string;
		disabled?: boolean;
		/** Side sent to the backend when the operator picks "Advocate" (defaults to Counsel/UNKNOWN). */
		defaultAdvocateSide?: string;
		/** Sets the popover's *initial* Bench/Advocate selection only — the operator can still change it inside the popover. */
		initialSide?: 'BENCH' | 'ADVOCATE';
		onCreated: (person: CreatedPerson, side: string) => void;
	}

	let {
		rawSpeakerLabel,
		triggerLabel = 'Create new person',
		disabled = false,
		defaultAdvocateSide = 'UNKNOWN',
		initialSide = 'ADVOCATE',
		onCreated,
	}: CreatePersonPopoverProps = $props();

	let open = $state(false);
	// Phase 38 (D-01/D-03/D-09) removed full_name from PersonCreate entirely —
	// the backend derives it from structured parts via prepare_person_name,
	// which requires at least one of first/last non-blank. This popover never
	// migrated off its original single "Name" field, so every submit sent a
	// now-forbidden `full_name` key and was rejected with a 422 (found live,
	// 2026-08-10). Mirrors the People-directory's own create-person fields
	// (app/src/routes/admin/people/new/+page.svelte) minus middle/suffix —
	// this popover stays intentionally minimal; full profile completion still
	// happens later in People Admin.
	let firstName = $state('');
	let lastName = $state('');
	let side = $state<'BENCH' | 'ADVOCATE'>(initialSide);
	let submitting = $state(false);
	let errorMessage = $state<string | null>(null);

	function resolvedSide(): string {
		return side === 'BENCH' ? 'BENCH' : defaultAdvocateSide;
	}

	function resetForm() {
		firstName = '';
		lastName = '';
		side = initialSide;
		errorMessage = null;
	}
</script>

<Popover.Root
	bind:open
	onOpenChange={(next) => {
		// WR-01 (49-REVIEW.md:297): `let side = $state(initialSide)` above is a
		// Svelte 5 state initializer — it reads `initialSide` exactly once at
		// mount and is NOT reactive to later prop changes. ResolveCard.svelte
		// passes `initialSide` to an always-rendered instance of this
		// component (never conditionally mounted/destroyed), so without this
		// branch the radio pre-selection could silently contradict the
		// trigger label if the row's side changed while this popover was
		// closed and never reopened afterward via resetForm(). The resync is
		// deliberately on OPEN, not via an $effect tracking the prop: an
		// effect would re-fire on every prop change and discard a radio
		// choice the operator deliberately made while the popover was
		// already open — a worse defect than the one this fixes.
		// resetForm()'s own `side = initialSide` reassignment on CLOSE is
		// retained unchanged, so behavior on close is unaffected.
		if (next) side = initialSide;
		else resetForm();
	}}
>
	<Popover.Trigger
		type="button"
		{disabled}
		style="
			font-size: 14px;
			font-weight: 400;
			color: #93c5fd;
			background: transparent;
			border: 1px solid #334155;
			border-radius: 4px;
			padding: 6px 12px;
			cursor: {disabled ? 'not-allowed' : 'pointer'};
			min-height: 36px;
			opacity: {disabled ? 0.6 : 1};
		"
	>
		{triggerLabel}
	</Popover.Trigger>
	<Popover.Portal>
		<Popover.Content
			trapFocus={true}
			escapeKeydownBehavior="close"
			interactOutsideBehavior="close"
			sideOffset={8}
			style="
				z-index: 50;
				width: min(420px, calc(100vw - 32px));
				background-color: #1e293b;
				border: 1px solid #334155;
				border-radius: 8px;
				padding: 16px;
				box-sizing: border-box;
			"
		>
			<h3 style="font-size: 16px; font-weight: 600; color: #e2e8f0; margin: 0 0 4px 0;">
				Create person
			</h3>
			<p style="font-size: 14px; font-weight: 400; color: #94a3b8; margin: 0 0 16px 0;">
				Add the minimum details needed to finish resolve. Complete the profile later in People.
			</p>

			<form
				method="POST"
				action="?/addPerson"
				use:enhance={() => {
					submitting = true;
					errorMessage = null;
					return async ({ result }) => {
						submitting = false;
						if (result.type === 'failure') {
							errorMessage =
								(result.data as { error?: string })?.error ??
								'Could not create person. Please try again.';
						} else if (result.type === 'success') {
							const person = (result.data as { person?: CreatedPerson })?.person;
							if (person) {
								onCreated(person, resolvedSide());
							}
							open = false;
							resetForm();
						}
					};
				}}
			>
				<input type="hidden" name="raw_speaker_label" value={rawSpeakerLabel} />
				<input type="hidden" name="side" value={resolvedSide()} />

				<div style="display: flex; gap: 8px; margin-bottom: 12px;">
					<div style="flex: 1;">
						<label
							for="cp-first-{rawSpeakerLabel}"
							style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 4px;"
						>
							First name
						</label>
						<input
							id="cp-first-{rawSpeakerLabel}"
							name="first_name"
							type="text"
							bind:value={firstName}
							style="
								width: 100%;
								background-color: #0f1117;
								border: 1px solid #334155;
								border-radius: 6px;
								padding: 8px 12px;
								font-size: 16px;
								color: #e2e8f0;
								box-sizing: border-box;
								font-family: inherit;
							"
						/>
					</div>
					<div style="flex: 1;">
						<label
							for="cp-last-{rawSpeakerLabel}"
							style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 4px;"
						>
							Last name
						</label>
						<input
							id="cp-last-{rawSpeakerLabel}"
							name="last_name"
							type="text"
							bind:value={lastName}
							style="
								width: 100%;
								background-color: #0f1117;
								border: 1px solid #334155;
								border-radius: 6px;
								padding: 8px 12px;
								font-size: 16px;
								color: #e2e8f0;
								box-sizing: border-box;
								font-family: inherit;
							"
						/>
					</div>
				</div>

				<div style="margin-bottom: 16px;">
					<span style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;">
						Bench / Advocate
					</span>
					<div role="radiogroup" aria-label="Bench or Advocate" style="display: flex; gap: 8px;">
						<button
							type="button"
							role="radio"
							aria-checked={side === 'BENCH'}
							onclick={() => {
								side = 'BENCH';
							}}
							style="
								flex: 1;
								min-height: 36px;
								font-size: 14px;
								font-weight: 400;
								color: {side === 'BENCH' ? '#e2e8f0' : '#94a3b8'};
								background: transparent;
								border: 1px solid {side === 'BENCH' ? '#93c5fd' : '#334155'};
								border-radius: 6px;
								cursor: pointer;
							"
						>
							Bench
						</button>
						<button
							type="button"
							role="radio"
							aria-checked={side === 'ADVOCATE'}
							onclick={() => {
								side = 'ADVOCATE';
							}}
							style="
								flex: 1;
								min-height: 36px;
								font-size: 14px;
								font-weight: 400;
								color: {side === 'ADVOCATE' ? '#e2e8f0' : '#94a3b8'};
								background: transparent;
								border: 1px solid {side === 'ADVOCATE' ? '#93c5fd' : '#334155'};
								border-radius: 6px;
								cursor: pointer;
							"
						>
							Advocate
						</button>
					</div>
				</div>

				{#if errorMessage}
					<p role="alert" style="color: #ef4444; font-size: 14px; margin: 0 0 12px 0;">
						{errorMessage}
					</p>
				{/if}

				<div style="display: flex; gap: 8px;">
					<button
						type="submit"
						disabled={submitting || (!firstName.trim() && !lastName.trim())}
						style="
							flex: 1;
							min-height: 44px;
							font-size: 14px;
							font-weight: 600;
							color: #e2e8f0;
							background: transparent;
							border: 1px solid #93c5fd;
							border-radius: 6px;
							cursor: {submitting ? 'not-allowed' : 'pointer'};
						"
					>
						{submitting ? 'Saving…' : 'Create person'}
					</button>
					<button
						type="button"
						onclick={() => {
							open = false;
							resetForm();
						}}
						style="
							flex: 1;
							min-height: 44px;
							font-size: 14px;
							font-weight: 400;
							color: #94a3b8;
							background: transparent;
							border: 1px solid #334155;
							border-radius: 6px;
							cursor: pointer;
						"
					>
						Cancel
					</button>
				</div>
			</form>
		</Popover.Content>
	</Popover.Portal>
</Popover.Root>
