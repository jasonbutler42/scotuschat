import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		host: true, // listen on all interfaces (0.0.0.0) so the Windows-side browser can reach the WSL-native dev server
		port: 5173,
		strictPort: true // fail loudly instead of silently drifting to another port
	}
});
