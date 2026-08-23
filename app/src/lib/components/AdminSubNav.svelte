<script lang="ts">
	// No props needed — links are hardcoded (same as TopNav admin variant)
</script>

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
	<a href="/admin/pipeline" style="font-size: 14px; font-weight: 400; color: #94a3b8; text-decoration: none;">
		Pipeline Runner
	</a>
	<a href="/admin/arguments" style="font-size: 14px; font-weight: 400; color: #94a3b8; text-decoration: none;">
		Arguments
	</a>
	<a href="/admin/people" style="font-size: 14px; font-weight: 400; color: #94a3b8; text-decoration: none;">
		People Editor
	</a>
	<a href="/admin/help" style="font-size: 14px; font-weight: 400; color: #94a3b8; text-decoration: none;">
		Help
	</a>

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
