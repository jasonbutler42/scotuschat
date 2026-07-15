import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

const root = fileURLToPath(new URL('.', import.meta.url));
const appRoot = fileURLToPath(new URL('../..', import.meta.url));

export default defineConfig({
	root,
	plugins: [svelte()],
	server: {
		fs: { allow: [appRoot] }
	}
});