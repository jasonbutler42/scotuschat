<script lang="ts">
	let { variant }: { variant: 'public' | 'admin' } = $props();

	const bgColor = variant === 'admin' ? '#1e293b' : '#0f1117';
</script>

<header>
	<nav
		aria-label={variant === 'admin' ? 'Admin navigation' : 'Site navigation'}
		style="
			background-color: {bgColor};
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

		{#if variant === 'public'}
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
		{:else}
			<!-- Admin variant: Pipeline Runner + People Editor + logout form (right-aligned) -->
			<a
				href="/admin/pipeline"
				style="font-size: 14px; font-weight: 400; color: #94a3b8; text-decoration: none;"
			>
				Pipeline Runner
			</a>
			<a
				href="/admin/arguments"
				style="font-size: 14px; font-weight: 400; color: #94a3b8; text-decoration: none;"
			>
				Arguments
			</a>
			<a
				href="/admin/people"
				style="font-size: 14px; font-weight: 400; color: #94a3b8; text-decoration: none;"
			>
				People Editor
			</a>

			<!-- Logout form — pushed to the right with margin-left: auto.
			     Targets the logout named action on /admin (admin/+page.server.ts).
			     No JavaScript required — standard form POST. -->
			<form method="POST" action="/admin?/logout" style="margin-left: auto;">
				<button
					type="submit"
					style="
						min-height: 44px;
						font-size: 14px;
						font-weight: 400;
						color: #94a3b8;
						background: transparent;
						border: 1px solid #334155;
						border-radius: 6px;
						padding: 8px 16px;
						cursor: pointer;
					"
					onmouseenter={(e) => {
						const btn = e.currentTarget as HTMLButtonElement;
						btn.style.color = '#e2e8f0';
						btn.style.borderColor = '#e2e8f0';
					}}
					onmouseleave={(e) => {
						const btn = e.currentTarget as HTMLButtonElement;
						btn.style.color = '#94a3b8';
						btn.style.borderColor = '#334155';
					}}
				>
					Log out
				</button>
			</form>
		{/if}
	</nav>
</header>
