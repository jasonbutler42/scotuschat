<script lang="ts">
	import '../../app.css';
	import { page } from '$app/state';
	import AdminSubNav from '$lib/components/AdminSubNav.svelte';
	let { children } = $props();
</script>

{#if page.route.id !== '/admin/login'}
<AdminSubNav />
{/if}

{@render children()}
