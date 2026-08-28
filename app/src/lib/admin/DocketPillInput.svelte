<script lang="ts">
	// Phase 38 (38-FIGMA.md component set 3:140 / review sheet 3:2): pills may
	// optionally carry provenance (confidence + raw source text) alongside the
	// existing plain-string editable contract. Plain string entries render with
	// byte-identical markup/behavior to before this phase — this is an additive,
	// backward-compatible extension, not a replacement of the editable-input role.
	import CopyableExtractedValue from '$lib/admin/CopyableExtractedValue.svelte';
	// Phase 38 gap closure (G-38-6, item 3): opt-in client-side shape feedback,
	// mirroring api/domain/docket_values.py. The backend (plan 38-07 at the
	// FastAPI boundary, plan 38-08 inside the pipeline) remains the sole
	// enforcement authority — this only gives the operator immediate,
	// specific feedback at the control instead of a crashed job later.
	import { normalizeDocketValue, DocketValueError, docketValueErrorMessage } from '$lib/docketValues';
	// Phase 51 (D-17): the free-text entry field below adopts the shared
	// Input primitive instead of a raw <input>, picking up its touch-target
	// and token-based styling. See the adoption note above the markup.
	import Input from '$lib/primitives/Input.svelte';

	type ConfidenceBand = 'High' | 'Medium' | 'Low';
	interface DocketProvenance {
		value: string;
		confidence?: ConfidenceBand | null;
		raw?: string | null;
	}
	type DocketPillValue = string | DocketProvenance;

	interface DocketPillInputProps {
		initialValues?: DocketPillValue[];
		name?: string;
		readonly?: boolean;
		id?: string;
		invalid?: boolean;
		descriptionId?: string;
		// Opt-in shape validation on newly typed values (never on initialValues
		// or already-rendered pills). Required on the job-creation path
		// (Pipeline Runner) because those values become filesystem paths;
		// the post-ingest metadata editor (ArgumentDetailsCard) has no
		// equivalent constraint in its API contract and stays opted out.
		enforceShape?: boolean;
	}

	let {
		initialValues = [],
		name = 'docket[]',
		readonly = false,
		id = 'docket-input',
		invalid = false,
		descriptionId,
		enforceShape = false
	}: DocketPillInputProps = $props();

	function normalizeEntry(entry: DocketPillValue): DocketProvenance {
		return typeof entry === 'string' ? { value: entry } : entry;
	}

	// Captured once at mount, mirroring `pills`' own non-reactive initialization —
	// callers that need to reseed provenance alongside new values already force a
	// remount via `{#key ...}` (see ArgumentDetailsCard.svelte), same as today.
	const normalizedInitial = initialValues.map(normalizeEntry);
	const provenanceMap = new Map<string, DocketProvenance>(
		normalizedInitial
			.filter((p) => p.confidence !== undefined || p.raw !== undefined)
			.map((p) => [p.value, p])
	);

	let pills = $state<string[]>(normalizedInitial.map((p) => p.value));
	let docketInput = $state('');
	let inputElement: HTMLInputElement | null = $state(null);
	// Shape-error state (enforceShape only) — cleared on every input change and
	// on the next successful add; never set for initialValues/existing pills.
	let shapeError = $state<string | null>(null);
	const shapeErrorId = `${id}-shape-error`;

	export function focus() {
		inputElement?.focus();
	}

	export function hasPills() {
		return pills.length > 0;
	}

	function addPill() {
		const v = docketInput.trim();
		if (enforceShape) {
			// Silently reject empty and duplicate values, same as the D-04
			// semantics below — the shape check only applies to genuinely new,
			// non-duplicate values.
			if (!v || pills.includes(v)) {
				docketInput = '';
				return;
			}
			try {
				const normalized = normalizeDocketValue(v);
				pills = [...pills, normalized];
				docketInput = '';
				shapeError = null;
			} catch (err) {
				if (!(err instanceof DocketValueError)) throw err;
				// Leave docketInput (and pills) untouched so the operator can
				// correct the value in place rather than retype it.
				shapeError = docketValueErrorMessage(err.code);
			}
			return;
		}
		// Silently reject empty and duplicate values (D-04)
		if (v && !pills.includes(v)) {
			pills = [...pills, v];
		}
		docketInput = '';
	}

	function removePill(value: string) {
		pills = pills.filter((p) => p !== value);
	}

	// Compose with — do not replace — the existing caller-driven invalid/
	// descriptionId contract: when both the caller's `invalid` and this
	// component's own shapeError are active, both ids are referenced. Their
	// composition now happens inside the Input primitive (describedBy for the
	// caller-owned id, errorMessage/errorId for this component's own).
	let hasError = $derived(!readonly && (invalid || Boolean(shapeError)));
</script>

<!-- Hidden inputs: one per pill — server reads FormData.getAll(name) -->
{#each pills as pill}
	<input type="hidden" {name} value={pill} />
{/each}

<!-- Editable pill list -->
{#if pills.length > 0}
	<div
		style="
			display: flex;
			flex-wrap: wrap;
			gap: 8px;
			margin-bottom: 8px;
		"
	>
		{#each pills as pill}
			{@const provenance = provenanceMap.get(pill)}
			{#if provenance}
				<!-- Phase 38 provenance pill: interpreted value stays primary; confidence
				     and exact raw source render via the shared stacked component so
				     long raw text wraps without hiding provenance (38-FIGMA.md). -->
				<span
					style="
						display: inline-flex;
						align-items: flex-start;
						gap: 6px;
						background-color: #1e293b;
						border: 1px solid #334155;
						border-radius: 4px;
						padding: 8px;
						font-size: 14px;
						font-weight: 400;
						color: #e2e8f0;
						max-width: 100%;
					"
				>
					<CopyableExtractedValue
						value={provenance.value}
						copyLabel="Copy docket"
						confidence={provenance.confidence}
						raw={provenance.raw}
					/>
					{#if !readonly}
						<button
							type="button"
							aria-label="Remove docket {pill}"
							onclick={() => removePill(pill)}
							style="
								display: inline-flex;
								align-items: center;
								justify-content: center;
								min-width: 28px;
								min-height: 28px;
								background: transparent;
								border: none;
								padding: 0;
								cursor: pointer;
								font-size: 14px;
								color: #94a3b8;
								line-height: 1;
								flex: 0 0 auto;
							"
							onmouseenter={(e) => {
								(e.currentTarget as HTMLButtonElement).style.color = '#ef4444';
							}}
							onmouseleave={(e) => {
								(e.currentTarget as HTMLButtonElement).style.color = '#94a3b8';
							}}
						>
							×
						</button>
					{/if}
				</span>
			{:else}
				<span
					style="
						display: inline-flex;
						align-items: center;
						gap: 6px;
						background-color: #1e293b;
						border: 1px solid #334155;
						border-radius: 4px;
						padding: 4px 8px;
						font-size: 14px;
						font-weight: 400;
						color: #e2e8f0;
					"
				>
					{pill}
					{#if !readonly}
						<button
							type="button"
							aria-label="Remove docket {pill}"
							onclick={() => removePill(pill)}
							style="
								display: inline-flex;
								align-items: center;
								justify-content: center;
								min-width: 28px;
								min-height: 28px;
								background: transparent;
								border: none;
								padding: 0;
								cursor: pointer;
								font-size: 14px;
								color: #94a3b8;
								line-height: 1;
							"
							onmouseenter={(e) => {
								(e.currentTarget as HTMLButtonElement).style.color = '#ef4444';
							}}
							onmouseleave={(e) => {
								(e.currentTarget as HTMLButtonElement).style.color = '#94a3b8';
							}}
						>
							×
						</button>
					{/if}
				</span>
			{/if}
		{/each}
	</div>
{/if}

<!-- Docket text input (Pitfall 3 guard: Enter must call e.preventDefault() before addPill).
     Phase 51 (D-17): renders through the shared Input primitive, adopting
     its touch-target and token-based styling. DocketPillInput's external
     prop shape (invalid, descriptionId) and behavior are unchanged — Input's
     `describedBy` carries the caller-owned external alert id (rendered by
     the caller, unchanged), and `errorMessage`/`errorId` carry this
     component's own internal shapeError alert (now rendered by Input
     itself instead of a local <p>, same id, same role="alert", same
     var(--color-destructive) styling). -->
<p style="font-size: 13px; font-weight: 400; color: #64748b; margin: 0 0 4px 0;">
	Type a docket number and press Enter to add it.
</p>
<Input
	bind:ref={inputElement}
	{id}
	type="text"
	bind:value={docketInput}
	disabled={readonly}
	invalid={hasError}
	describedBy={!readonly && invalid && descriptionId ? descriptionId : undefined}
	errorMessage={!readonly ? shapeError : null}
	errorId={shapeErrorId}
	oninput={() => {
		// Clear the shape error as soon as the operator starts correcting the
		// value — never clears the caller-driven `invalid` state, which is
		// owned by the caller.
		if (shapeError) shapeError = null;
	}}
	onkeydown={(e) => {
		if (e.key === 'Enter') {
			e.preventDefault();
			if (!readonly) addPill();
		}
	}}
/>
