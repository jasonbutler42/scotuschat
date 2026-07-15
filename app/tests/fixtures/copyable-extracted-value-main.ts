import { createClassComponent } from 'svelte/legacy';
import CopyableExtractedValue from '../../src/lib/components/CopyableExtractedValue.svelte';

type Deferred = { resolve: () => void; reject: (reason?: unknown) => void };
const writes: Deferred[] = [];
Object.defineProperty(navigator, 'clipboard', { configurable: true, value: {
	writeText: () => new Promise<void>((resolve, reject) => writes.push({ resolve, reject }))
} });
let component = createClassComponent({ component: CopyableExtractedValue, target: document.querySelector('#fixture')!, props: { value: 'Alpha', copyLabel: 'Copy Alpha' } });

Object.assign(window, {
	copyFixture: {
		settle(index: number, succeeds = true) { const write = writes[index]; succeeds ? write.resolve() : write.reject(new Error('secret browser error')); },
		set(value: string, copyLabel: string) { component.$set({ value, copyLabel }); },
		destroy() { component.$destroy(); },
		get writeCount() { return writes.length; }
	}
});
