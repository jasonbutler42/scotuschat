<script lang="ts">
	import '../app.css';
	import { page } from '$app/state';
	import TopNav from '$lib/components/TopNav.svelte';
	let { children } = $props();
</script>

{#if !page.url.pathname.startsWith('/admin')}
<TopNav variant="public" />
{/if}

{@render children()}
