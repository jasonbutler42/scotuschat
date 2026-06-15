<script lang="ts">
	import { browser } from '$app/environment';

	type SectionAnchor = { hint: string; label: string; anchorId: string };
	let { sections }: { sections: SectionAnchor[] } = $props();

	let activeSection = $state<string | null>(null);

	$effect(() => {
		if (!browser || sections.length === 0) return;

		const observers: IntersectionObserver[] = [];

		for (const sec of sections) {
			const el = document.getElementById(sec.anchorId);
			if (!el) continue;
			const obs = new IntersectionObserver(
				([entry]) => {
					if (entry.isIntersecting) {
						activeSection = sec.hint;
					}
				},
				{ rootMargin: '-40% 0px -55% 0px', threshold: 0 }
			);
			obs.observe(el);
			observers.push(obs);
		}

		return () => observers.forEach((o) => o.disconnect());
	});
</script>

{#if sections.length > 0}
	<nav
		aria-label="Argument sections"
		style="
			position: fixed;
			bottom: 0;
			left: 0;
			right: 0;
			background-color: #1e293b;
			border-top: 1px solid #334155;
			display: flex;
			flex-direction: row;
			overflow-x: auto;
			gap: 8px;
			padding: 8px 16px;
			min-height: 44px;
			align-items: center;
		"
	>
		{#each sections as sec (sec.hint)}
			<button
				onclick={() => document.getElementById(sec.anchorId)?.scrollIntoView({ behavior: 'smooth' })}
				style="
					border-radius: 20px;
					padding: 6px 14px;
					font-size: 13px;
					cursor: pointer;
					white-space: nowrap;
					background-color: transparent;
					color: {activeSection === sec.hint ? '#e2e8f0' : '#94a3b8'};
					border: 1px solid {activeSection === sec.hint ? '#93c5fd' : '#334155'};
					font-weight: {activeSection === sec.hint ? 600 : 400};
				"
			>
				{sec.label}
			</button>
		{/each}
	</nav>
{/if}

<style>
	nav {
		display: none;
	}
	@media (max-width: 768px) {
		nav {
			display: flex;
		}
	}
</style>
