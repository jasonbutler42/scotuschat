<script lang="ts">
	import { Popover } from 'bits-ui';
	import ChatBubble from '$lib/components/ChatBubble.svelte';
	import StageDirection from '$lib/components/StageDirection.svelte';
	import SectionRail from '$lib/components/SectionRail.svelte';
	import MobileNavBar from '$lib/components/MobileNavBar.svelte';
	import SpeakerPopover from '$lib/components/SpeakerPopover.svelte';

	interface TenureRow {
		// Canonical "chief"/"associate" storage value (Phase 37 D-15/D-17) — formal
		// title projection happens in SpeakerPopover.svelte, not here.
		office: string | null;
		start_date: string | null;
		end_date: string | null;
		// Canonical "retired"/"died"/"promoted" storage value, or null when the
		// tenure has no recorded reason (Phase 39 D-01/D-02) — formal title
		// projection happens in SpeakerPopover.svelte, not here.
		reason_left: string | null;
		// Phase 39 (D-13, promote not add-alongside): per-tenure appointing
		// president, replacing the retired top-level appointing_president field.
		appointed_by: string | null;
		// Phase 39 (D-11/D-12, reverses T-14-02): factual historical record about
		// the appointing president, not the Justice.
		appointing_president_party: string | null;
	}

	interface SpeakerDetail {
		person_id: number;
		full_name: string;
		role_name: string | null;
		photo_url_full: string | null;
		is_bench: boolean;
		tenure: TenureRow[];
		// Phase 39 (D-13): the top-level appointing_president field retired here
		// — the concept moved onto each TenureRow as appointed_by (see above).
		birthdate: string | null;
		death_date: string | null;
		bio_text: string | null;
	}

	let { data } = $props();

	// Popover state
	let isPopoverOpen = $state(false);
	let currentSpeaker = $state<SpeakerDetail | null>(null);
	let currentAnchor = $state<HTMLElement | null>(null);

	// Build O(1) lookup map from server-loaded speakers array (Pitfall 2: not returned as Map)
	// Cast via unknown because RawSpeaker uses an index signature in +page.server.ts
	const speakersMap = $derived(
		new Map<number, SpeakerDetail>(
			(data.speakers as unknown as SpeakerDetail[]).map((s) => [s.person_id, s])
		)
	);

	function onAvatarClick(personId: number, anchor: HTMLElement): void {
		const speaker = speakersMap.get(personId) ?? null;
		currentSpeaker = speaker;
		currentAnchor = anchor;
		isPopoverOpen = speaker !== null;
	}

	/**
	 * Format an argued_date string (e.g. "2015-04-28") as "April 28, 2015".
	 * Uses Intl.DateTimeFormat per the UI-SPEC Copywriting Contract.
	 * The date comes from the API as a date string (YYYY-MM-DD).
	 * We append T00:00:00 to force local-date parsing and avoid UTC midnight
	 * roll-back on systems west of UTC.
	 */
	function formatDate(dateStr: string | null | undefined): string {
		if (!dateStr) return 'Date unknown';
		const date = new Date(dateStr + 'T00:00:00');
		return new Intl.DateTimeFormat('en-US', {
			month: 'long',
			day: 'numeric',
			year: 'numeric'
		}).format(date);
	}

	// D-12: Roster derived client-side from utterances (no new API endpoint needed)
	// Extended to carry person_id alongside name and role (Pitfall 4 fix)
	const roster = $derived.by(() => {
		const seen = new Set<string>();
		const bench: { name: string; role: string | null; person_id: number | null }[] = [];
		const advocates: { name: string; role: string | null; person_id: number | null }[] = [];
		for (const u of data.utterances) {
			if (u.is_stage_direction) continue;
			const key = u.speaker_name ?? u.raw_speaker_label ?? '';
			if (!key || seen.has(key)) continue;
			seen.add(key);
			const entry = { name: key, role: u.speaker_role ?? null, person_id: u.person_id ?? null };
			if (u.side === 'BENCH') bench.push(entry);
			else advocates.push(entry);
		}
		return { bench, advocates };
	});

	// D-04: Section anchors derived from section_hint — lowercase values confirmed in RESEARCH.md Pitfall 1
	const sectionAnchors = $derived(
		data.utterances
			.filter(
				(u: { section_hint: string | null; is_stage_direction: boolean }) =>
					u.section_hint !== null && !u.is_stage_direction
			)
			.reduce(
				(
					acc: { hint: string; label: string; anchorId: string }[],
					u: { section_hint: string; sequence: number }
				) => {
					// Only take the first utterance of each section (first occurrence of each hint)
					if (!acc.some((a) => a.hint === u.section_hint)) {
						acc.push({
							hint: u.section_hint,
							label: u.section_hint.charAt(0).toUpperCase() + u.section_hint.slice(1),
							anchorId: `section-${u.section_hint}-${u.sequence}`
						});
					}
					return acc;
				},
				[]
			)
	);

	// Helper: derive initials from a display name
	function getInitials(name: string): string {
		const parts = name.trim().split(/\s+/).filter(Boolean);
		if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
		if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
		return '?';
	}
</script>

<!-- Page background (#0f1117) -->
<main style="background-color: #0f1117; min-height: 100vh;">

	<!-- Shared Popover.Root at page level — single instance for all avatar triggers -->
	<Popover.Root bind:open={isPopoverOpen} onOpenChange={(open) => { if (!open) currentSpeaker = null; }}>
		<Popover.Portal>
			<Popover.Content
				customAnchor={currentAnchor}
				sideOffset={8}
				trapFocus={true}
				escapeKeydownBehavior="close"
				interactOutsideBehavior="close"
				style="z-index: 50; max-height: min(560px, 80vh); overflow-y: auto;
				       background-color: #1e293b; border: 1px solid #334155; border-radius: 8px;
				       min-width: 300px; max-width: 400px;"
			>
				{#if currentSpeaker}
					<SpeakerPopover speaker={currentSpeaker} />
				{/if}
			</Popover.Content>
		</Popover.Portal>

	<!-- Argument heading bar: full-width, #1e293b, border-bottom #334155 -->
	<header
		style="
			background-color: #1e293b;
			border-bottom: 1px solid #334155;
			padding: 16px 24px;
		"
	>
		<div style="max-width: 1200px; margin: 0 auto;">
			<!-- Case name: 20px, weight 600, #e2e8f0 -->
			<h1
				style="
					font-size: 20px;
					font-weight: 600;
					color: #e2e8f0;
					margin: 0 0 4px 0;
					line-height: 1.2;
				"
			>
				{data.argument.case_name}
			</h1>
			<!-- Subline: "No. {docket} · Argued {date} · Question {n}" — 14px, #94a3b8 -->
			<p
				style="
					font-size: 14px;
					font-weight: 400;
					color: #94a3b8;
					margin: 0;
					line-height: 1.4;
				"
			>
				No. {data.argument.docket_number} · Argued {formatDate(data.argument.argued_date)} · Question {data.argument.question_number}
			</p>

			<!-- Speaker roster: two-column grid, Bench left, Advocates right — D-11 -->
			<!-- Both columns use #94a3b8 for speaker names — apolitical framing constraint -->
			<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 16px;">
				<!-- Bench column -->
				<div>
					<p
						style="
							font-size: 13px;
							font-weight: 600;
							color: #94a3b8;
							margin: 0 0 8px 0;
						"
					>
						Bench
					</p>
					{#each roster.bench as speaker (speaker.name)}
						<div style="display:flex;align-items:center;gap:8px;margin:0 0 4px 0;">
							{#if speaker.person_id != null}
								<button
									type="button"
									onclick={(e) => onAvatarClick(speaker.person_id!, e.currentTarget as HTMLElement)}
									style="background:none;border:none;padding:6px;cursor:pointer;border-radius:50%;display:flex;align-items:center;justify-content:center;"
									aria-label="View {speaker.name} details"
								>
									<div aria-hidden="true" style="width:32px;height:32px;border-radius:50%;background-color:#94a3b8;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:600;color:#0f1117;flex-shrink:0;">
										{getInitials(speaker.name)}
									</div>
								</button>
							{:else}
								<div aria-hidden="true" style="width:32px;height:32px;border-radius:50%;background-color:#94a3b8;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:600;color:#0f1117;flex-shrink:0;">
									{getInitials(speaker.name)}
								</div>
							{/if}
							<p style="font-size:14px;font-weight:400;color:#94a3b8;margin:0;">{speaker.name}</p>
						</div>
					{/each}
				</div>
				<!-- Advocates column -->
				<div>
					<p
						style="
							font-size: 13px;
							font-weight: 600;
							color: #94a3b8;
							margin: 0 0 8px 0;
						"
					>
						Advocates
					</p>
					{#each roster.advocates as speaker (speaker.name)}
						<div style="display:flex;align-items:center;gap:8px;margin:0 0 4px 0;">
							{#if speaker.person_id != null}
								<button
									type="button"
									onclick={(e) => onAvatarClick(speaker.person_id!, e.currentTarget as HTMLElement)}
									style="background:none;border:none;padding:6px;cursor:pointer;border-radius:50%;display:flex;align-items:center;justify-content:center;"
									aria-label="View {speaker.name} details"
								>
									<div aria-hidden="true" style="width:32px;height:32px;border-radius:50%;background-color:#93c5fd;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:600;color:#0f1117;flex-shrink:0;">
										{getInitials(speaker.name)}
									</div>
								</button>
							{:else}
								<div aria-hidden="true" style="width:32px;height:32px;border-radius:50%;background-color:#93c5fd;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:600;color:#0f1117;flex-shrink:0;">
									{getInitials(speaker.name)}
								</div>
							{/if}
							<p style="font-size:14px;font-weight:400;color:#94a3b8;margin:0;">{speaker.name}</p>
						</div>
					{/each}
				</div>
			</div>

			<!-- Per-argument attribution note — D-22/T-29-11: gated server-side via
				 is_corpus_sourced (derived from oyez_transcript_id in +page.server.ts).
				 Quiet caption styling, no badge/icon (apolitical house tone). -->
			{#if data.is_corpus_sourced}
				<p
					style="
						font-size: 13px;
						font-weight: 400;
						color: #94a3b8;
						line-height: 1.4;
						margin: 8px 0 0 0;
					"
				>
					Historical transcript imported from Oyez.org via Cornell ConvoKit (CC BY-NC 4.0).
					<a href="/attributions" style="color: #93c5fd; text-decoration: underline;">
						View attributions &rarr;
					</a>
				</p>
			{/if}
		</div>
	</header>

	<!-- Two-column content grid: nav rail (180px) + chat column (1fr) — D-01 -->
	<div
		class="content-grid"
		style="display: grid; grid-template-columns: 180px 1fr; max-width: 1200px; margin: 0 auto;"
	>
		<!-- Nav rail column: sticky sidebar with section navigation -->
		<div class="nav-rail">
			{#if sectionAnchors.length > 0}
				<SectionRail sections={sectionAnchors} />
			{/if}
		</div>

		<!-- Chat column: utterance stream -->
		<div style="padding: 48px 24px 60px 24px;">
			{#if !data.utterances || data.utterances.length === 0}
				<!-- Empty state -->
				<p
					style="
						text-align: center;
						color: #94a3b8;
						font-size: 16px;
					"
				>
					No utterances found for this argument.
				</p>
			{:else}
				<!-- Utterance stream with turn-gap logic:
					 same speaker → lg gap (24px); different speaker → xl gap (32px) -->
				{#each data.utterances as utterance, i (utterance.sequence)}
					{@const prevUtterance = i > 0 ? data.utterances[i - 1] : null}
					{@const sameSpeaker =
						prevUtterance !== null &&
						prevUtterance.raw_speaker_label === utterance.raw_speaker_label}
					<!-- Section anchor id on first utterance of each section — id omitted (undefined) when section_hint is null -->
					<div
						id={utterance.section_hint
							? `section-${utterance.section_hint}-${utterance.sequence}`
							: undefined}
						style={i === 0 ? '' : sameSpeaker ? 'margin-top: 24px;' : 'margin-top: 32px;'}
					>
						{#if utterance.is_stage_direction}
							<StageDirection {utterance} />
						{:else}
							<ChatBubble {utterance} {onAvatarClick} />
						{/if}
					</div>
				{/each}
			{/if}
		</div>
	</div>
	<MobileNavBar sections={sectionAnchors} />

	</Popover.Root>
</main>

<!-- D-03: Mobile breakpoint — hide nav rail below 768px; chat spans full width -->
<style>
	@media (max-width: 768px) {
		.content-grid {
			grid-template-columns: 1fr !important;
		}
		.nav-rail {
			display: none !important;
		}
	}
</style>
