<svelte:head>
	<title>Log in — SCOTUS Chat Admin</title>
</svelte:head>

<script lang="ts">
	let { form } = $props();
</script>

<!-- Full-bleed dark background, vertically/horizontally centered -->
<main
	style="
		background-color: var(--color-bg);
		min-height: 100vh;
		display: flex;
		align-items: center;
		justify-content: center;
	"
>
	<!-- Login card -->
	<div
		style="
			background-color: var(--color-surface);
			border: 1px solid var(--color-border);
			border-radius: 8px;
			padding: var(--space-2xl);
			width: 100%;
			max-width: 400px;
		"
	>
		<!-- Heading: 20px/600/--color-text-primary, margin-bottom 24px -->
		<h1
			style="
				font-size: var(--font-size-heading);
				font-weight: var(--font-weight-semibold);
				color: var(--color-text-primary);
				margin: 0 0 var(--space-xl) 0;
				line-height: 1.2;
			"
		>
			Admin Login
		</h1>

		<form method="POST">
			<!-- Username field -->
			<div style="margin-bottom: var(--space-lg);">
				<label
					for="username"
					style="
						display: block;
						font-size: var(--font-size-caption);
						font-weight: var(--font-weight-regular);
						color: var(--color-text-secondary);
						margin-bottom: var(--space-sm);
					"
				>
					Username
				</label>
				<input
					type="text"
					name="username"
					id="username"
					required
					autofocus
					style="
						display: block;
						width: 100%;
						background-color: var(--color-bg);
						border: 1px solid var(--color-border);
						border-radius: 6px;
						padding: var(--space-sm) var(--space-md);
						font-size: var(--font-size-body);
						color: var(--color-text-primary);
						box-sizing: border-box;
					"
				/>
			</div>

			<!-- Password field -->
			<div style="margin-bottom: 0;">
				<label
					for="password"
					style="
						display: block;
						font-size: var(--font-size-caption);
						font-weight: var(--font-weight-regular);
						color: var(--color-text-secondary);
						margin-bottom: var(--space-sm);
					"
				>
					Password
				</label>
				<input
					type="password"
					name="password"
					id="password"
					required
					style="
						display: block;
						width: 100%;
						background-color: var(--color-bg);
						border: 1px solid var(--color-border);
						border-radius: 6px;
						padding: var(--space-sm) var(--space-md);
						font-size: var(--font-size-body);
						color: var(--color-text-primary);
						box-sizing: border-box;
					"
				/>
			</div>

			<!-- Inline error: only rendered when form has an error (D-13) -->
			{#if form?.error}
				<p
					role="alert"
					style="
						color: var(--color-destructive);
						font-size: var(--font-size-body);
						font-weight: var(--font-weight-regular);
						line-height: 1.5;
						margin: var(--space-md) 0 0 0;
					"
				>
					{form.error}
				</p>
			{/if}

			<!-- Submit button: full-width, min-height 44px (WCAG 2.5.5) -->
			<button
				type="submit"
				style="
					display: block;
					width: 100%;
					min-height: var(--touch-target);
					background-color: var(--color-surface);
					border: 1px solid var(--color-border);
					border-radius: 6px;
					font-size: var(--font-size-body);
					font-weight: var(--font-weight-semibold);
					color: var(--color-text-primary);
					cursor: pointer;
					margin-top: var(--space-xl);
				"
			>
				Log in
			</button>
		</form>
	</div>
</main>
