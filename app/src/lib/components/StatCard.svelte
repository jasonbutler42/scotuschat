<script lang="ts">
	// Shared admin stat-card container (Phase 28, DASH-01/02/05).
	// First shared card component in the codebase — every other admin page
	// previously rolled its own inline card markup (28-PATTERNS.md).
	//
	// D-10: the container style below is a FIXED literal — never conditional
	// on counts/urgency. Do not branch on card type inside this component;
	// each card's differently-shaped breakdown body is composed by the caller
	// via the `children` snippet.
	let { title, children } = $props();
</script>

<div
	style="
		background-color: #1e293b;
		border: 1px solid #334155;
		border-radius: 8px;
		padding: 24px;
	"
>
	<h2
		style="
			font-size: 20px;
			font-weight: 600;
			color: #e2e8f0;
			margin: 0 0 16px 0;
		"
	>
		{title}
	</h2>
	{@render children()}
</div>
