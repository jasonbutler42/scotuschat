<script lang="ts">
	let { variant }: { variant: 'public' } = $props();
</script>

<header>
	<nav
		aria-label="Site navigation"
		style="
			background-color: var(--color-bg);
			border-bottom: 1px solid var(--color-border);
			padding: 12px var(--space-lg);
			display: flex;
			flex-wrap: wrap;
			align-items: center;
			gap: var(--space-md);
		"
	>
		<!-- Wordmark — plain span in both variants (not a link); matches existing nav pattern -->
		<span style="font-size: var(--font-size-caption); font-weight: var(--font-weight-semibold); color: var(--color-text-secondary); letter-spacing: 0.05em;">
			SCOTUS CHAT
		</span>

		<!-- Public variant: Arguments link (accent) + Admin link (muted, right-aligned) -->
		<a
			href="/arguments"
			style="font-size: var(--font-size-caption); color: var(--color-accent); text-decoration: none;"
		>
			Arguments
		</a>
		<a
			href="/attributions"
			style="font-size: var(--font-size-caption); color: var(--color-accent); text-decoration: none;"
		>
			Attributions
		</a>
		<a
			href="/admin"
			style="font-size: var(--font-size-caption); color: var(--color-text-secondary); text-decoration: none; margin-left: auto;"
		>
			Admin
		</a>
	</nav>
</header>
