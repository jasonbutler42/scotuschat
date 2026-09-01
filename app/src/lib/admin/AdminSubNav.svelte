<script lang="ts">
	// No props needed — links are hardcoded (same as TopNav admin variant)
</script>

<nav
	aria-label="Admin navigation"
	style="
		background-color: var(--color-surface);
		border-bottom: 1px solid var(--color-border);
		padding: var(--space-md) var(--space-xl);
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--space-lg);
	"
>
	<a href="/admin/pipeline" style="font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); text-decoration: none;">
		Pipeline Runner
	</a>
	<a href="/admin/arguments" style="font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); text-decoration: none;">
		Arguments
	</a>
	<a href="/admin/review" style="font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); text-decoration: none;">
		Review
	</a>
	<a href="/admin/people" style="font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); text-decoration: none;">
		People Editor
	</a>
	<a href="/admin/help" style="font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); text-decoration: none;">
		Help
	</a>

	<form method="POST" action="/admin?/logout" style="margin-left: auto;">
		<button
			type="submit"
			style="
				min-height: var(--touch-target);
				font-size: var(--font-size-caption);
				font-weight: var(--font-weight-regular);
				color: var(--color-text-secondary);
				background: transparent;
				border: 1px solid var(--color-border);
				border-radius: 6px;
				padding: var(--space-sm) var(--space-lg);
				cursor: pointer;
			"
			onmouseenter={(e) => {
				const btn = e.currentTarget as HTMLButtonElement;
				btn.style.color = 'var(--color-text-primary)';
				btn.style.borderColor = 'var(--color-text-primary)';
			}}
			onmouseleave={(e) => {
				const btn = e.currentTarget as HTMLButtonElement;
				btn.style.color = 'var(--color-text-secondary)';
				btn.style.borderColor = 'var(--color-border)';
			}}
		>
			Log out
		</button>
	</form>
</nav>
