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

<nav aria-label="Argument sections" style="position: sticky; top: 0; padding: 24px 16px; align-self: start;">
	{#each sections as sec (sec.hint)}
		<button
			aria-current={activeSection === sec.hint ? 'true' : undefined}
			onclick={() => document.getElementById(sec.anchorId)?.scrollIntoView({ behavior: 'smooth' })}
			style="
				display: block;
				width: 100%;
				text-align: left;
				padding: 8px 12px;
				margin-bottom: 4px;
				border: none;
				cursor: pointer;
				border-radius: 4px;
				font-size: 13px;
				background-color: {activeSection === sec.hint ? '#1e293b' : 'transparent'};
				color: {activeSection === sec.hint ? '#e2e8f0' : '#94a3b8'};
				border-left: 3px solid {activeSection === sec.hint ? '#93c5fd' : 'transparent'};
				font-weight: {activeSection === sec.hint ? 600 : 400};
			"
		>
			{sec.label}
		</button>
	{/each}
</nav>
