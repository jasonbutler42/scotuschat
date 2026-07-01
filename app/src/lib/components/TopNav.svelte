<script lang="ts">
	let { variant }: { variant: 'public' } = $props();
</script>

<header>
	<nav
		aria-label="Site navigation"
		style="
			background-color: #0f1117;
			border-bottom: 1px solid #334155;
			padding: 12px 24px;
			display: flex;
			align-items: center;
			gap: 16px;
		"
	>
		<!-- Wordmark — plain span in both variants (not a link); matches existing nav pattern -->
		<span style="font-size: 14px; font-weight: 600; color: #94a3b8; letter-spacing: 0.05em;">
			SCOTUS CHAT
		</span>

		<!-- Public variant: Cases link (accent) + Admin link (muted, right-aligned) -->
		<a
			href="/cases"
			style="font-size: 14px; color: #93c5fd; text-decoration: none;"
		>
			Cases
		</a>
		<a
			href="/admin"
			style="font-size: 14px; color: #94a3b8; text-decoration: none; margin-left: auto;"
		>
			Admin
		</a>
	</nav>
</header>
