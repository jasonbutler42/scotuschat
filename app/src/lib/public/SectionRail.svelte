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

<nav aria-label="Argument sections" style="position: sticky; top: 0; padding: var(--space-lg) var(--space-md); align-self: start;">
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
				display: block;
				width: 100%;
				text-align: left;
				padding: var(--space-sm) var(--space-md);
				margin-bottom: var(--space-xs);
				border: none;
				cursor: pointer;
				border-radius: 4px;
				font-size: var(--font-size-caption);
				background-color: {activeSection === sec.hint ? 'var(--color-surface)' : 'transparent'};
				color: {activeSection === sec.hint ? 'var(--color-text-primary)' : 'var(--color-text-secondary)'};
				border-left: 3px solid {activeSection === sec.hint ? 'var(--color-accent)' : 'transparent'};
				font-weight: {activeSection === sec.hint ? 'var(--font-weight-semibold)' : 'var(--font-weight-regular)'};
			"
		>
			{sec.label}
		</button>
	{/each}
</nav>
