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
		onCreated: (person: CreatedPerson, side: string) => void;
	}

	let {
		rawSpeakerLabel,
		triggerLabel = 'Create new person',
		disabled = false,
		defaultAdvocateSide = 'UNKNOWN',
		onCreated,
	}: CreatePersonPopoverProps = $props();

	let open = $state(false);
	let name = $state('');
	let side = $state<'BENCH' | 'ADVOCATE'>('ADVOCATE');
	let submitting = $state(false);
	let errorMessage = $state<string | null>(null);

	function resolvedSide(): string {
		return side === 'BENCH' ? 'BENCH' : defaultAdvocateSide;
	}

	function resetForm() {
		name = '';
		side = 'ADVOCATE';
		errorMessage = null;
	}
</script>

<Popover.Root
	bind:open
	onOpenChange={(next) => {
		if (!next) resetForm();
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
			min-height: 32px;
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

				<div style="margin-bottom: 12px;">
					<label
						for="cp-name-{rawSpeakerLabel}"
						style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 4px;"
					>
						Name
					</label>
					<input
						id="cp-name-{rawSpeakerLabel}"
						name="full_name"
						type="text"
						bind:value={name}
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
						disabled={submitting || !name.trim()}
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
