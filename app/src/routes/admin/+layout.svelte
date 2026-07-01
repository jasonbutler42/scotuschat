<script lang="ts">
	import '../../app.css';
	import { page } from '$app/state';
	import AdminSubNav from '$lib/components/AdminSubNav.svelte';
	import TopNav from '$lib/components/TopNav.svelte';
	let { children } = $props();
</script>

{#if page.route.id !== '/admin/login'}
<TopNav variant="public" />
<AdminSubNav />
{/if}

{@render children()}
