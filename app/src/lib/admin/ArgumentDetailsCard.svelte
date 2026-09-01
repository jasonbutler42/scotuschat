<script lang="ts">
	import { enhance } from '$app/forms';
	import { tick } from 'svelte';
	import CopyableExtractedValue from '$lib/admin/CopyableExtractedValue.svelte';
	import DocketPillInput from '$lib/admin/DocketPillInput.svelte';

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

	function formatExtractedDate(iso: string | null | undefined): string | null {
		if (!iso) return null;
		const match = iso.match(/^(\d{4})-(\d{2})-(\d{2})/);
		if (!match) return iso;
		return match[2] + '/' + match[3] + '/' + match[1];
	}

	function extractedIsoDate(value: string | null | undefined): string | null {
		if (!value) return null;
		const match = value.match(/^(\d{4})-(\d{2})-(\d{2})/);
		if (!match) return null;
		const year = Number(match[1]);
		const month = Number(match[2]);
		const day = Number(match[3]);
		const parsed = new Date(Date.UTC(year, month - 1, day));
		if (
			parsed.getUTCFullYear() !== year ||
			parsed.getUTCMonth() !== month - 1 ||
			parsed.getUTCDate() !== day
		) return null;
		return match[1] + '-' + match[2] + '-' + match[3];
	}
	// D-04/D-05: docket initial-value source for DocketPillInput, seeded from savedValues.dockets
	let effectiveDockets = $state<string[]>(savedValues.dockets ?? []);
	let saving = $state(false);
	let alertElement: HTMLParagraphElement | null = $state(null);
	let arguedDateInput: HTMLInputElement | null = $state(null);
	let docketControl: { focus: () => void; hasPills: () => boolean } | null = $state(null);
	let clientDocketRequired = $state(false);
	let docketRequired = $derived(clientDocketRequired || form?.docketRequired === true);
	let validExtractedArguedDate = $derived(extractedIsoDate(hints.argued_date));

	function useExtractedArguedDate() {
		if (readonly || !validExtractedArguedDate || !arguedDateInput) return;
		arguedDateInput.value = validExtractedArguedDate;
		arguedDateInput.dispatchEvent(new Event('input', { bubbles: true }));
	}

	// D-06: on failed save, re-seed DocketPillInput from form.dockets (not from savedValues)
	$effect(() => {
		if (form && 'dockets' in form) {
			effectiveDockets = form.dockets ?? [];
		}
	});
</script>

<div
	style="
		background-color: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: 8px;
		padding: var(--space-xl);
		margin-bottom: var(--space-xl);
	"
>
	<h2
		style="
			font-size: var(--font-size-heading);
			font-weight: var(--font-weight-semibold);
			color: var(--color-text-primary);
			margin: 0 0 var(--space-xl) 0;
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
		<div style="margin-bottom: var(--space-lg);">
			<label
				for="docket-input"
				style="display: block; font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); margin-bottom: var(--space-sm);"
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
			<div style="margin-top: var(--space-xs); display: flex; align-items: center; flex-wrap: wrap; gap: var(--space-xs);">
				<span
					style="font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary);"
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
		<div style="margin-bottom: var(--space-lg);">
			<label
				for="question-number-input"
				style="display: block; font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); margin-bottom: var(--space-sm);"
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
					background-color: var(--color-bg);
					border: 1px solid var(--color-border);
					border-radius: 6px;
					padding: var(--space-sm) var(--space-md);
					font-size: var(--font-size-body);
					color: var(--color-text-primary);
					box-sizing: border-box;
					font-family: inherit;
				"
			/>
			<!-- Question number hint row: always visible (D-07/D-08/PJOB-04) -->
			<div style="font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); margin-top: var(--space-xs); margin-bottom: 0; display: flex; align-items: center; flex-wrap: wrap;">
				<span>Extracted:</span>
				<CopyableExtractedValue value={hints.question_number} copyLabel="Copy question number" />
			</div>
		</div>

		<!-- Argued date field -->
		<div style="margin-bottom: var(--space-xl);">
			<label
				for="argued-date-input"
				style="display: block; font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); margin-bottom: var(--space-sm);"
			>
				Argued date
			</label>
			<input
				bind:this={arguedDateInput}
				id="argued-date-input"
				type="date"
				name="argued_date"
				value={form && 'argued_date' in form ? (form.argued_date ?? '') : (savedValues.argued_date ?? '')}
				disabled={readonly}
				style="
					width: 100%;
					background-color: var(--color-bg);
					border: 1px solid var(--color-border);
					border-radius: 6px;
					padding: var(--space-sm) var(--space-md);
					font-size: var(--font-size-body);
					color: var(--color-text-primary);
					box-sizing: border-box;
					font-family: inherit;
				"
			/>
			<!-- Argued date hint row: always visible (D-07/D-08/PJOB-04) -->
			<div style="font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); margin-top: var(--space-xs); margin-bottom: 0; display: flex; align-items: center; flex-wrap: wrap; gap: var(--space-xs);">
				<span>Extracted:</span>
				<CopyableExtractedValue value={formatExtractedDate(hints.argued_date)} copyLabel="Copy argued date" />
				{#if !readonly && validExtractedArguedDate}
					<button
						type="button"
						onclick={useExtractedArguedDate}
						title="Fill argued date with the extracted value"
						style="
							min-height: var(--touch-target-dense);
							background: transparent;
							border: 1px solid var(--color-border);
							border-radius: 4px;
							padding: var(--space-xs) var(--space-sm);
							color: var(--color-accent);
							font: inherit;
							cursor: pointer;
						"
					>Use extracted</button>
				{/if}
			</div>
		</div>

		<!-- Success / error messages -->
		{#if form?.saved}
			<p
				style="
					font-size: var(--font-size-caption);
					color: var(--color-status-published);
					margin-bottom: var(--space-lg);
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
					font-size: var(--font-size-caption);
					color: var(--color-destructive);
					margin-bottom: var(--space-lg);
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
					min-height: var(--touch-target);
					background-color: var(--color-surface);
					border: 1px solid var(--color-accent);
					border-radius: 6px;
					padding: var(--space-sm) var(--space-lg);
					font-size: var(--font-size-body);
					font-weight: var(--font-weight-semibold);
					color: var(--color-text-primary);
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
