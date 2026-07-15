<script lang="ts">
	import { enhance } from '$app/forms';
	import { tick } from 'svelte';
	import CopyableExtractedValue from '$lib/components/CopyableExtractedValue.svelte';
	import DocketPillInput from '$lib/components/DocketPillInput.svelte';

	type DuplicateArgumentConflict = {
		code: 'duplicate_argument';
		message: string;
		conflicting_argument_id: number;
	};

	interface ArgumentDetailsCardProps {
		savedValues: {
			dockets: string[];
			question_number: string;
			argued_date: string | null;
		};
		hints: {
			dockets: string[];
			question_number: string | null;
			argued_date: string | null;
			case_name: string | null;
		};
		action: string;
		readonly?: boolean;
		form?: {
			dockets?: string[];
			question_number?: string;
			argued_date?: string | null;
			conflict?: DuplicateArgumentConflict;
			saveError?: string;
			docketRequired?: boolean;
			saved?: boolean;
		} | null;
	}

	let {
		savedValues,
		hints,
		action,
		readonly = false,
		form = null
	}: ArgumentDetailsCardProps = $props();

	// D-04/D-05: docket initial-value source for DocketPillInput, seeded from savedValues.dockets
	let effectiveDockets = $state<string[]>(savedValues.dockets ?? []);
	let saving = $state(false);
	let alertElement: HTMLParagraphElement | null = $state(null);
	let docketControl: { focus: () => void; hasPills: () => boolean } | null = $state(null);
	let clientDocketRequired = $state(false);
	let docketRequired = $derived(clientDocketRequired || form?.docketRequired === true);

	// D-06: on failed save, re-seed DocketPillInput from form.dockets (not from savedValues)
	$effect(() => {
		if (form && 'dockets' in form) {
			effectiveDockets = form.dockets ?? [];
		}
	});
</script>

<div
	style="
		background-color: #1e293b;
		border: 1px solid #334155;
		border-radius: 8px;
		padding: 24px;
		margin-bottom: 24px;
	"
>
	<h2
		style="
			font-size: 20px;
			font-weight: 600;
			color: #e2e8f0;
			margin: 0 0 24px 0;
			line-height: 1.2;
		"
	>
		Argument Details
	</h2>

	<form
		method="POST"
		{action}
		use:enhance={({ cancel }) => {
			if (!readonly && !docketControl?.hasPills()) {
				cancel();
				clientDocketRequired = true;
				void tick().then(() => docketControl?.focus());
				return;
			}
			clientDocketRequired = false;
			saving = true;
			return async ({ result, update }) => {
				saving = false;
				if (result.type === 'failure') {
					// Pitfall 4 guard: reset:true would wipe pill $state — use default update() on failure
					await update();
					await tick();
					if (form?.docketRequired) docketControl?.focus();
					else alertElement?.focus();
				} else {
					// Pitfall 4 guard: reset:false is mandatory — reset:true wipes pill $state on success
					await update({ reset: false });
				}
			};
		}}
	>
		<!-- Docket field -->
		<div style="margin-bottom: 16px;">
			<label
				for="docket-input"
				style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;"
			>
				Docket
			</label>

			{#key effectiveDockets.join('')}
				<DocketPillInput
					bind:this={docketControl}
					initialValues={effectiveDockets}
					name="docket[]"
					id="docket-input"
					{readonly}
					invalid={docketRequired}
					descriptionId="argument-details-alert"
				/>
			{/key}
			<!-- Docket hint row: always visible (D-07/PJOB-04); read-only pills (D-09) -->
			<div style="margin-top: 4px; display: flex; align-items: center; flex-wrap: wrap; gap: 4px;">
				<span
					style="font-size: 14px; font-weight: 400; color: #94a3b8;"
				>Extracted:</span>
				{#if hints.dockets.length > 0}
					{#each hints.dockets as hintDocket}
						<CopyableExtractedValue value={hintDocket} copyLabel="Copy docket" variant="pill" />
					{/each}
				{:else}
					<CopyableExtractedValue value={null} copyLabel="Copy docket" variant="pill" />
				{/if}
			</div>
		</div>

		<!-- Question number field -->
		<div style="margin-bottom: 16px;">
			<label
				for="question-number-input"
				style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;"
			>
				Question number
			</label>
			<input
				id="question-number-input"
				type="text"
				name="question_number"
				value={form?.question_number ?? savedValues.question_number}
				disabled={readonly}
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
			<!-- Question number hint row: always visible (D-07/D-08/PJOB-04) -->
			<div style="font-size: 14px; font-weight: 400; color: #94a3b8; margin-top: 4px; margin-bottom: 0; display: flex; align-items: center; flex-wrap: wrap;">
				<span>Extracted:</span>
				<CopyableExtractedValue value={hints.question_number} copyLabel="Copy question number" />
			</div>
		</div>

		<!-- Argued date field -->
		<div style="margin-bottom: 24px;">
			<label
				for="argued-date-input"
				style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;"
			>
				Argued date
			</label>
			<input
				id="argued-date-input"
				type="date"
				name="argued_date"
				value={form && 'argued_date' in form ? (form.argued_date ?? '') : (savedValues.argued_date ?? '')}
				disabled={readonly}
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
			<!-- Argued date hint row: always visible (D-07/D-08/PJOB-04) -->
			<div style="font-size: 14px; font-weight: 400; color: #94a3b8; margin-top: 4px; margin-bottom: 0; display: flex; align-items: center; flex-wrap: wrap;">
				<span>Extracted:</span>
				<CopyableExtractedValue value={hints.argued_date} copyLabel="Copy argued date" />
			</div>
		</div>

		<!-- Success / error messages -->
		{#if form?.saved}
			<p
				style="
					font-size: 14px;
					color: #4ade80;
					margin-bottom: 16px;
				"
			>
				Saved.
			</p>
		{/if}
		{#if docketRequired || form?.saveError || form?.conflict}
			<p
				id="argument-details-alert"
				bind:this={alertElement}
				role="alert"
				tabindex="-1"
				style="
					font-size: 14px;
					color: #ef4444;
					margin-bottom: 16px;
				"
			>
				{#if docketRequired}
					Add at least one docket.
				{:else if form?.conflict}
					{form.conflict.message}
					<a
						href={`/admin/arguments/${form.conflict.conflicting_argument_id}`}
						target="_blank"
						rel="noopener noreferrer"
					>Open conflicting argument</a>.
				{:else}
					{form?.saveError}
				{/if}
			</p>
		{/if}

		<!-- Save button — not rendered in readonly mode -->
		{#if !readonly}
			<button
				type="submit"
				disabled={saving}
				style="
					width: 100%;
					min-height: 44px;
					background-color: #1e293b;
					border: 1px solid #93c5fd;
					border-radius: 6px;
					padding: 8px 16px;
					font-size: 16px;
					font-weight: 600;
					color: #e2e8f0;
					cursor: {saving ? 'not-allowed' : 'pointer'};
					opacity: {saving ? '0.7' : '1'};
					font-family: inherit;
				"
			>
				{saving ? 'Saving…' : 'Save Argument Details'}
			</button>
		{/if}
	</form>
</div>
