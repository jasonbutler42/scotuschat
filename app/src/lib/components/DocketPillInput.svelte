<script lang="ts">
	interface DocketPillInputProps {
		initialValues?: string[];
		name?: string;
		readonly?: boolean;
		id?: string;
	}

	let {
		initialValues = [],
		name = 'docket[]',
		readonly = false,
		id = 'docket-input'
	}: DocketPillInputProps = $props();

	let pills = $state<string[]>(initialValues);
	let docketInput = $state('');

	function addPill() {
		const v = docketInput.trim();
		// Silently reject empty and duplicate values (D-04)
		if (v && !pills.includes(v)) {
			pills = [...pills, v];
		}
		docketInput = '';
	}

	function removePill(value: string) {
		pills = pills.filter((p) => p !== value);
	}
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
		{/each}
	</div>
{/if}

<!-- Docket text input (Pitfall 3 guard: Enter must call e.preventDefault() before addPill) -->
<p style="font-size: 13px; font-weight: 400; color: #64748b; margin: 0 0 4px 0;">
	Type a docket number and press Enter to add it.
</p>
<input
	{id}
	type="text"
	bind:value={docketInput}
	disabled={readonly}
	onkeydown={(e) => {
		if (e.key === 'Enter') {
			e.preventDefault();
			if (!readonly) addPill();
		}
	}}
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
