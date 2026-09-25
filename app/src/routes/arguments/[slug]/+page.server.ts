import { FASTAPI_BASE_URL } from '$env/static/private';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

interface RawSpeaker {
	photo_url?: string | null;
	// office carries the canonical "chief"/"associate" storage value (Phase 37
	// D-15/D-17) — formal title projection happens in SpeakerPopover.svelte, not here.
	tenure?: Array<{ office?: string | null; start_date?: string | null; end_date?: string | null }>;
	// D-12 (Phase 52-02): server-computed avatar-initials glyph. Typed here
	// rather than relying only on the index signature below; the existing
	// spread (`...s`) already carries it into the mapped object.
	initials?: string | null;
	[key: string]: unknown;
}

// D-10/D-12 (Phase 51 plan 51-02): params.slug replaces params.id — resolves
// via the new by-slug endpoints, which apply the SAME published gate
// get_argument_with_utterances always has. Primary fetch fails closed
// (throw error); the secondary speakers fetch degrades to [] inside
// try/catch, unchanged from the pre-existing pattern.
export const load: PageServerLoad = async ({ params, fetch }) => {
	const res = await fetch(`${FASTAPI_BASE_URL}/arguments/by-slug/${params.slug}/utterances`);
	if (!res.ok) throw error(res.status, 'Failed to load argument');
	const data = await res.json();

	// Fetch speakers for the popover card — degrade gracefully on non-OK (must not break argument page)
	let speakers: Array<RawSpeaker & { photo_url_full: string | null; is_bench: boolean }> = [];
	try {
		const speakersRes = await fetch(`${FASTAPI_BASE_URL}/arguments/by-slug/${params.slug}/speakers`);
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
		argument_id: data.argument.argument_id,
		speakers, // plain array — SvelteKit serializes Map as {} (Pitfall 2); +page.svelte builds Map via $derived
		// D-22/T-29-11: visibility decided server-side from oyez_transcript_id — never
		// fetch/decide in browser code (Architecture Rule 2: FASTAPI_BASE_URL server-only)
		is_corpus_sourced: data.argument.oyez_transcript_id != null
	};
};
