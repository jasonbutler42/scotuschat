<script lang="ts">
	import '../../app.css';
	import { page } from '$app/state';
	import TopNav from '$lib/components/TopNav.svelte';
	import AdminSubNav from '$lib/components/AdminSubNav.svelte';
	let { children } = $props();
</script>

{#if page.url.pathname !== '/admin/login'}
<TopNav variant="public" />
<AdminSubNav />
{/if}

{@render children()}
