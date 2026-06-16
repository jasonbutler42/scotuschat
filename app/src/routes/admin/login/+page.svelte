<svelte:head>
	<title>Log in — SCOTUS Chat Admin</title>
</svelte:head>

<script lang="ts">
	let { form } = $props();
</script>

<!-- Full-bleed dark background, vertically/horizontally centered -->
<main
	style="
		background-color: #0f1117;
		min-height: 100vh;
		display: flex;
		align-items: center;
		justify-content: center;
	"
>
	<!-- Login card -->
	<div
		style="
			background-color: #1e293b;
			border: 1px solid #334155;
			border-radius: 8px;
			padding: 32px;
			width: 100%;
			max-width: 400px;
		"
	>
		<!-- Heading: 20px/600/#e2e8f0, margin-bottom 24px -->
		<h1
			style="
				font-size: 20px;
				font-weight: 600;
				color: #e2e8f0;
				margin: 0 0 24px 0;
				line-height: 1.2;
			"
		>
			Admin Login
		</h1>

		<form method="POST">
			<!-- Username field -->
			<div style="margin-bottom: 16px;">
				<label
					for="username"
					style="
						display: block;
						font-size: 14px;
						font-weight: 400;
						color: #94a3b8;
						margin-bottom: 8px;
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
						background-color: #0f1117;
						border: 1px solid #334155;
						border-radius: 6px;
						padding: 8px 12px;
						font-size: 16px;
						color: #e2e8f0;
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
						font-size: 14px;
						font-weight: 400;
						color: #94a3b8;
						margin-bottom: 8px;
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
						background-color: #0f1117;
						border: 1px solid #334155;
						border-radius: 6px;
						padding: 8px 12px;
						font-size: 16px;
						color: #e2e8f0;
						box-sizing: border-box;
					"
				/>
			</div>

			<!-- Inline error: only rendered when form has an error (D-13) -->
			{#if form?.error}
				<p
					role="alert"
					style="
						color: #ef4444;
						font-size: 16px;
						font-weight: 400;
						line-height: 1.5;
						margin: 12px 0 0 0;
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
					min-height: 44px;
					background-color: #1e293b;
					border: 1px solid #334155;
					border-radius: 6px;
					font-size: 16px;
					font-weight: 600;
					color: #e2e8f0;
					cursor: pointer;
					margin-top: 24px;
				"
			>
				Log in
			</button>
		</form>
	</div>
</main>
