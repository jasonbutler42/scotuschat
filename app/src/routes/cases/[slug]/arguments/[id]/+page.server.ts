import { FASTAPI_BASE_URL } from '$env/static/private';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

interface RawSpeaker {
	photo_url?: string | null;
	tenure?: Array<{ seat?: string | null; start_date?: string | null; end_date?: string | null }>;
	[key: string]: unknown;
}

export const load: PageServerLoad = async ({ params, fetch }) => {
	const res = await fetch(`${FASTAPI_BASE_URL}/arguments/${params.id}/utterances`);
	if (!res.ok) throw error(res.status, 'Failed to load argument');
	const data = await res.json();

	// Fetch speakers for the popover card — degrade gracefully on non-OK (must not break argument page)
	let speakers: Array<RawSpeaker & { photo_url_full: string | null; is_bench: boolean }> = [];
	try {
		const speakersRes = await fetch(`${FASTAPI_BASE_URL}/arguments/${params.id}/speakers`);
		if (speakersRes.ok) {
			const raw: RawSpeaker[] = await speakersRes.json();
			speakers = raw.map((s) => {
				// Reconstruct photo_url_full server-side — FASTAPI_BASE_URL must never reach the client
				let photo_url_full: string | null;
				if (s.photo_url && s.photo_url.startsWith('/')) {
					photo_url_full = FASTAPI_BASE_URL + s.photo_url;
				} else if (s.photo_url) {
					// Already an absolute URL (e.g. https://...)
					photo_url_full = s.photo_url;
				} else {
					photo_url_full = null;
				}
				// is_bench: true when the speaker has at least one court tenure entry
				const is_bench = (s.tenure?.length ?? 0) > 0;
				return { ...s, photo_url_full, is_bench };
			});
		}
		// Non-OK response: leave speakers as [] — argument page still loads
	} catch {
		// Network or parse error: leave speakers as []
	}

	return {
		utterances: data.utterances,
		argument: data.argument, // includes case_name, docket_number, argued_date, question_number
		argument_id: parseInt(params.id),
		speakers, // plain array — SvelteKit serializes Map as {} (Pitfall 2); +page.svelte builds Map via $derived
		// D-22/T-29-11: visibility decided server-side from oyez_transcript_id — never
		// fetch/decide in browser code (Architecture Rule 2: FASTAPI_BASE_URL server-only)
		is_corpus_sourced: data.argument.oyez_transcript_id != null
	};
};
