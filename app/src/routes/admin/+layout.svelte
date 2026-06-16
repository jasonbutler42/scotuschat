<script lang="ts">
	import '../../app.css';
	import { page } from '$app/state';
	let { children } = $props();
</script>

{#if page.url.pathname !== '/admin/login'}
<header>
	<nav
		aria-label="Admin navigation"
		style="
			background-color: #1e293b;
			border-bottom: 1px solid #334155;
			padding: 12px 24px;
			display: flex;
			align-items: center;
			gap: 16px;
		"
	>
		<!-- Wordmark — matches public nav exactly (14px/600/#94a3b8) -->
		<span style="font-size: 14px; font-weight: 600; color: #94a3b8; letter-spacing: 0.05em;">
			SCOTUS CHAT
		</span>

		<!-- Disabled placeholder nav items — rendered as <span> not <a> to prevent
		     navigation to unbuilt routes (D-09, T-06-13). aria-disabled + aria-label
		     for screen-reader clarity (Accessibility Notes). -->
		<span
			aria-disabled="true"
			aria-label="Pipeline Runner (coming soon)"
			style="font-size: 14px; font-weight: 400; color: #94a3b8; opacity: 0.5; cursor: default;"
		>
			Pipeline Runner
		</span>
		<span
			aria-disabled="true"
			aria-label="People Editor (coming soon)"
			style="font-size: 14px; font-weight: 400; color: #94a3b8; opacity: 0.5; cursor: default;"
		>
			People Editor
		</span>

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
	</nav>
</header>
{/if}

{@render children()}
