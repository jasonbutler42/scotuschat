<script lang="ts">
	import { enhance } from '$app/forms';

	let { data, form } = $props();

	// Submitting state per named action.
	let savingState = $state(false);
	let publishingState = $state(false);
	let unpublishingState = $state(false);

	// Format ISO date string for display — identical to list page formatDate.
	function formatDate(iso: string): string {
		try {
			return new Date(iso).toLocaleDateString('en-US', {
				year: 'numeric',
				month: 'short',
				day: 'numeric',
			});
		} catch {
			return iso;
		}
	}

	// StatusBadge helpers — same logic as list page.
	function badgeStyle(resolved_at: string | null, published_at: string | null): string {
		let color: string;
		if (published_at) {
			color = '#4ade80';
		} else if (resolved_at) {
			color = '#a78bfa';
		} else {
			color = '#94a3b8';
		}
		return `border: 1px solid ${color}; border-radius: 4px; padding: 2px 8px; font-size: 14px; font-weight: 400; background-color: #1e293b; color: ${color}; display: inline-block;`;
	}

	function badgeLabel(resolved_at: string | null, published_at: string | null): string {
		if (published_at) return 'Published';
		if (resolved_at) return 'Resolved';
		return 'Pending';
	}

	// Convert ISO timestamp or date string to value compatible with <input type="date"> (YYYY-MM-DD).
	function toDateInputValue(iso: string | null): string {
		if (!iso) return '';
		// Take only the date portion (first 10 chars of ISO 8601)
		return iso.slice(0, 10);
	}
</script>

<svelte:head>
	<title>{data.argument.case_name} — SCOTUS Chat Admin</title>
</svelte:head>

<main style="background-color: #0f1117; min-height: 100vh;">
	<header
		style="background-color: #1e293b; border-bottom: 1px solid #334155; padding: 16px 24px;"
	>
		<!-- Back navigation per UI-SPEC -->
		<a
			href="/admin/arguments"
			style="font-size: 14px; font-weight: 400; color: #94a3b8; text-decoration: none; display: block; margin-bottom: 8px;"
		>← Arguments</a>
		<h1 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0;">
			{data.argument.case_name}
		</h1>
	</header>

	<div style="max-width: 640px; margin: 0 auto; padding: 48px 24px;">

		<!-- Card 1: Argument Details — save form -->
		<div
			style="
				background-color: #1e293b;
				border: 1px solid #334155;
				border-radius: 8px;
				padding: 24px;
				margin-bottom: 16px;
			"
		>
			<h2 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 24px 0;">
				Argument Details
			</h2>

			<form
				method="POST"
				action="?/save"
				use:enhance={() => {
					savingState = true;
					return async ({ update }) => {
						savingState = false;
						await update();
					};
				}}
			>
				<!-- Case title field -->
				<div style="margin-bottom: 16px;">
					<label
						for="case_name"
						style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;"
					>Case title</label>
					<input
						type="text"
						id="case_name"
						name="case_name"
						value={data.argument.case_name}
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

				<!-- Docket number field — plain text per Date Format Contract (NOT a date input) -->
				<div style="margin-bottom: 16px;">
					<label
						for="docket_number"
						style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;"
					>Docket number</label>
					<input
						type="text"
						id="docket_number"
						name="docket_number"
						value={data.argument.docket_number}
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

				<!-- Argued date field — date input per Date Format Contract -->
				<div style="margin-bottom: {data.argument.consolidated_dockets.length > 0 ? '16px' : '0'};">
					<label
						for="argued_date"
						style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;"
					>Argued date</label>
					<input
						type="date"
						id="argued_date"
						name="argued_date"
						value={toDateInputValue(data.argument.argued_date)}
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

				<!-- Consolidated dockets — read-only, shown only when more than one case (D-10) -->
				{#if data.argument.consolidated_dockets.length > 0}
					<div style="margin-bottom: 0;">
						<p
							style="font-size: 14px; font-weight: 400; color: #94a3b8; margin: 0 0 8px 0;"
						>Consolidated dockets</p>
						<ul style="margin: 0; padding-left: 20px;">
							{#each data.argument.consolidated_dockets as docket}
								<li style="font-size: 14px; color: #94a3b8; padding: 2px 0;">
									{docket.docket_number}
								</li>
							{/each}
						</ul>
					</div>
				{/if}

				<!-- Form-level error slot — role=alert for screen reader announcement (WCAG) -->
				{#if form?.error}
					<p
						role="alert"
						style="
							color: #ef4444;
							font-size: 16px;
							font-weight: 400;
							line-height: 1.5;
							margin: 16px 0 0 0;
						"
					>{form.error}</p>
				{/if}

				<!-- Save changes button — full-width, accent border, 44px min-height -->
				<button
					type="submit"
					disabled={savingState}
					style="
						display: block;
						width: 100%;
						min-height: 44px;
						background-color: #1e293b;
						border: 1px solid #93c5fd;
						border-radius: 6px;
						font-size: 16px;
						font-weight: 600;
						color: #e2e8f0;
						cursor: {savingState ? 'not-allowed' : 'pointer'};
						margin-top: 24px;
						opacity: {savingState ? 0.7 : 1};
					"
				>
					{savingState ? 'Saving…' : 'Save changes'}
				</button>
			</form>
		</div>

		<!-- Card 2: Status — current badge + resolved/published dates + slug preview -->
		<div
			style="
				background-color: #1e293b;
				border: 1px solid #334155;
				border-radius: 8px;
				padding: 24px;
				margin-bottom: 16px;
			"
		>
			<h2 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 16px 0;">
				Status
			</h2>

			<div style="margin-bottom: 12px;">
				<span style={badgeStyle(data.argument.resolved_at, data.argument.published_at)}>
					{badgeLabel(data.argument.resolved_at, data.argument.published_at)}
				</span>
			</div>

			{#if data.argument.resolved_at}
				<p style="font-size: 14px; color: #94a3b8; margin: 0 0 8px 0;">
					Resolved {formatDate(data.argument.resolved_at)}
				</p>
			{/if}

			{#if data.argument.published_at}
				<p style="font-size: 14px; color: #94a3b8; margin: 0 0 8px 0;">
					Published {formatDate(data.argument.published_at)}
				</p>
			{/if}

			<p style="font-size: 14px; color: #94a3b8; margin: 0;">
				Slug: {data.argument.slug}
			</p>
		</div>

		<!-- Publish button — only when resolved and not yet published (D-07) -->
		{#if data.argument.resolved_at && !data.argument.published_at}
			<form
				method="POST"
				action="?/publish"
				use:enhance={() => {
					publishingState = true;
					return async ({ update }) => {
						publishingState = false;
						await update();
					};
				}}
				style="margin-bottom: 12px;"
			>
				<button
					type="submit"
					disabled={publishingState}
					style="
						display: block;
						width: 100%;
						min-height: 44px;
						background-color: #1e293b;
						border: 1px solid #93c5fd;
						border-radius: 6px;
						font-size: 16px;
						font-weight: 600;
						color: #e2e8f0;
						cursor: {publishingState ? 'not-allowed' : 'pointer'};
						opacity: {publishingState ? 0.7 : 1};
					"
				>
					{publishingState ? 'Publishing…' : 'Publish'}
				</button>
			</form>
		{/if}

		<!-- Unpublish button — only when already published (D-07) -->
		{#if data.argument.published_at}
			<form
				method="POST"
				action="?/unpublish"
				use:enhance={() => {
					unpublishingState = true;
					return async ({ update }) => {
						unpublishingState = false;
						await update();
					};
				}}
			>
				<button
					type="submit"
					disabled={unpublishingState}
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
						cursor: {unpublishingState ? 'not-allowed' : 'pointer'};
						opacity: {unpublishingState ? 0.7 : 1};
					"
				>
					{unpublishingState ? 'Unpublishing…' : 'Unpublish'}
				</button>
			</form>
		{/if}

	</div>
</main>
