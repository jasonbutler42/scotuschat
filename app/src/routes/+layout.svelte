<script lang="ts">
	import '../app.css';
	let { children } = $props();
</script>

<nav
	style="
		background-color: #0f1117;
		border-bottom: 1px solid #334155;
		padding: 12px 24px;
		display: flex;
		align-items: center;
		gap: 16px;
	"
>
	<span style="font-size: 14px; font-weight: 600; color: #94a3b8; letter-spacing: 0.05em;">
		SCOTUS CHAT
	</span>
	<a
		href="/cases/obergefell-v-hodges/arguments/3"
		style="
			font-size: 13px;
			color: #93c5fd;
			text-decoration: none;
		"
	>
		Obergefell v. Hodges
	</a>
</nav>

{@render children()}
