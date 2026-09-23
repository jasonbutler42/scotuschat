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
			background-color: var(--color-surface);
			border-top: 1px solid var(--color-border);
			flex-direction: row;
			overflow-x: auto;
			gap: var(--space-sm);
			padding: var(--space-sm) var(--space-lg);
			min-height: var(--touch-target);
			align-items: center;
		"
	>
		{#each sections as sec (sec.hint)}
			<button
				aria-current={activeSection === sec.hint ? 'true' : undefined}
				onclick={() => {
					const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
					document.getElementById(sec.anchorId)?.scrollIntoView({
						behavior: reducedMotion ? 'instant' : 'smooth'
					});
				}}
				style="
					border-radius: 20px;
					padding: var(--space-xs) var(--space-sm);
					font-size: var(--font-size-caption);
					cursor: pointer;
					white-space: nowrap;
					background-color: transparent;
					color: {activeSection === sec.hint ? 'var(--color-text-primary)' : 'var(--color-text-secondary)'};
					border: 1px solid {activeSection === sec.hint ? 'var(--color-accent)' : 'var(--color-border)'};
					font-weight: {activeSection === sec.hint ? 'var(--font-weight-semibold)' : 'var(--font-weight-regular)'};
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
