<script lang="ts">
	import { Popover } from 'bits-ui';
	import ChatBubble from '$lib/public/ChatBubble.svelte';
	import StageDirection from '$lib/public/StageDirection.svelte';
	import UndeterminedBubble from '$lib/public/UndeterminedBubble.svelte';
	import SectionRail from '$lib/public/SectionRail.svelte';
	import MobileNavBar from '$lib/public/MobileNavBar.svelte';
	import SpeakerPopover from '$lib/public/SpeakerPopover.svelte';
	import VariantSwitcher from '$lib/public/VariantSwitcher.svelte';
	import type { SpeakerDetail } from '$lib/types/speaker';

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
	// Extended to carry person_id alongside name and role (Pitfall 4 fix).
	// Phase 52-02 (D-12): also carries the server-computed speaker_initials —
	// the client no longer derives initials from `name`.
	const roster = $derived.by(() => {
		const seen = new Set<string>();
		const bench: { name: string; role: string | null; person_id: number | null; initials: string | null }[] = [];
		const advocates: { name: string; role: string | null; person_id: number | null; initials: string | null }[] = [];
		for (const u of data.utterances) {
			if (u.is_stage_direction) continue;
			// D-05/SPEAKER-01: a sentinel-speaker row never contributes a roster
			// name — defensive as well as by construction, since the stored fact
			// (never raw_speaker_label content) is what the render loop below
			// keys off to skip it entirely.
			if (u.speaker_undetermined) continue;
			const key = u.speaker_name ?? u.raw_speaker_label ?? '';
			if (!key || seen.has(key)) continue;
			seen.add(key);
			const entry = {
				name: key,
				role: u.speaker_role ?? null,
				person_id: u.person_id ?? null,
				initials: u.speaker_initials ?? null
			};
			if (u.side === 'BENCH') bench.push(entry);
			else advocates.push(entry);
		}
		return { bench, advocates };
	});

	// Per-speaker colour (P-03). Side is NOT the axis here: every speaker in an
	// argument gets their own hue from the L* 78 ramp, so no speaker — justice or
	// advocate — reads as louder than any other. Side stays encoded where it has
	// always been encoded, in position: which half of the row the bubble occupies
	// and which side the rail sits on.
	//
	// Assignment is by INDEX IN FIRST-APPEARANCE ORDER, deliberately not by a
	// hash of the name and emphatically not at random. `ChatBubble` is keyed by
	// `u.sequence` and reused across navigation, so a value that is not a pure
	// function of the argument's own roster would survive into the next argument
	// — the same defect class as the prop-capture bug. An index is stable within
	// a page load, stable across re-render, varied within an argument, and free
	// to differ between arguments, which is exactly the requirement.
	//
	// The ramp has 11 slots and wraps. Wrapping is acceptable because hue is a
	// redundant accelerator, never the identifier: the initials are inside every
	// avatar and the name is on the first bubble of every run.
	const SPEAKER_SLOT_COUNT = 11;
	const BENCH_SLOT_COUNT = 6;
	const ADVOCATE_SLOT_COUNT = 4;
	const UNRESOLVED = 'var(--color-speaker-unresolved)';

	/**
	 * The three candidate colours for one speaker, one per colour variant. All
	 * three are emitted onto the DOM together and CSS picks which one paints —
	 * that is what makes the switcher a CSS-only swap (see .speaker-fill in
	 * app.css). Computing them here rather than in CSS is unavoidable: two of
	 * the three depend on the speaker's index within THIS argument's roster,
	 * which is data only the route has.
	 */
	type SpeakerPalette = { speaker: string; family: string; side: string };

	const speakerSlots = $derived.by(() => {
		// Keyed both ways on purpose: the transcript and roster know a speaker by
		// display name, while the popover only ever has a person_id. Both must
		// resolve to the SAME hue or tapping an avatar would recolour the person.
		const byName = new Map<string, SpeakerPalette>();
		const byPersonId = new Map<number, SpeakerPalette>();
		// Unresolved speakers consume no slot in any of the three scales, so one
		// missing person does not shift every later speaker's hue.
		let all = 0;
		let bench = 0;
		let advocate = 0;
		for (const u of data.utterances) {
			if (u.is_stage_direction) continue;
			// Same D-05 skip as `roster` above: an undetermined row consumes no
			// colour slot, so one sentinel row does not shift every later
			// speaker's hue.
			if (u.speaker_undetermined) continue;
			const key = u.speaker_name ?? u.raw_speaker_label ?? '';
			if (!key || byName.has(key)) continue;
			const isBenchSide = u.side === 'BENCH';
			let palette: SpeakerPalette;
			if (u.person_id == null) {
				palette = { speaker: UNRESOLVED, family: UNRESOLVED, side: UNRESOLVED };
			} else {
				palette = {
					speaker: `var(--color-speaker-${(all++ % SPEAKER_SLOT_COUNT) + 1})`,
					family: isBenchSide
						? `var(--color-bench-${(bench++ % BENCH_SLOT_COUNT) + 1})`
						: `var(--color-advocate-${(advocate++ % ADVOCATE_SLOT_COUNT) + 1})`,
					side: isBenchSide ? 'var(--color-side-bench)' : 'var(--color-side-advocate)'
				};
			}
			byName.set(key, palette);
			if (u.person_id != null) byPersonId.set(u.person_id, palette);
		}
		return { byName, byPersonId };
	});

	const UNRESOLVED_PALETTE: SpeakerPalette = {
		speaker: UNRESOLVED,
		family: UNRESOLVED,
		side: UNRESOLVED
	};

	/** The custom-property declarations to drop on any element that contains a
	 *  speaker's avatar or name. They inherit, so one declaration site covers a
	 *  whole row. */
	function paletteVars(p: SpeakerPalette): string {
		return `--speaker-color:${p.speaker};--family-color:${p.family};--side-color:${p.side};`;
	}
	function speakerVars(name: string): string {
		return paletteVars(speakerSlots.byName.get(name) ?? UNRESOLVED_PALETTE);
	}
	function speakerVarsForPerson(personId: number | null | undefined): string {
		if (personId == null) return paletteVars(UNRESOLVED_PALETTE);
		return paletteVars(speakerSlots.byPersonId.get(personId) ?? UNRESOLVED_PALETTE);
	}

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

	// D-19 (Style B2): run grouping is the structural unit and MUST happen
	// before layout, separate from presentation. A run is a maximal sequence
	// of consecutive non-stage-direction utterances sharing the same
	// raw_speaker_label — the same equality this route always used for its
	// pre-D-19 "same speaker" turn-gap check. A stage direction always
	// terminates the run it interrupts and is never itself part of one; it
	// belongs to neither side (D-19/P-01/P-03).
	//
	// $derived.by keeps this in the same safe-reactivity family as `roster`
	// and `sectionAnchors` above — no top-level `data` capture is introduced
	// (see the landmine audit note below the template).
	type TranscriptUtterance = (typeof data)['utterances'][number];
	type RenderItem =
		| { kind: 'stage'; utterance: TranscriptUtterance }
		| { kind: 'undetermined'; utterance: TranscriptUtterance }
		| { kind: 'run'; utterances: TranscriptUtterance[] };

	const renderItems = $derived.by(() => {
		const items: RenderItem[] = [];
		for (const u of data.utterances) {
			if (u.is_stage_direction) {
				items.push({ kind: 'stage', utterance: u });
				continue;
			}
			// D-05/S5: classified BEFORE the run-continuation check below, keyed
			// only off the stored sentinel fact — never off raw_speaker_label
			// content. This is also what stops two consecutive undetermined rows
			// merging: both carry raw_speaker_label === null today, and the old
			// run-continuation equality check treated that shared null as "same
			// speaker" (the S5 defect this fixes as a side effect).
			if (u.speaker_undetermined === true) {
				items.push({ kind: 'undetermined', utterance: u });
				continue;
			}
			const last = items[items.length - 1];
			if (
				last?.kind === 'run' &&
				last.utterances[last.utterances.length - 1].raw_speaker_label === u.raw_speaker_label
			) {
				last.utterances.push(u);
			} else {
				items.push({ kind: 'run', utterances: [u] });
			}
		}
		return items;
	});

	// D-19 corner-rounding table position — 'single' run of one utterance keeps
	// all four corners at 6px; 'first'/'middle'/'last' soften the corners
	// facing the adjacent bubble in the same run to 2px. ChatBubble.svelte owns
	// the actual radius values; this only classifies index within the run.
	function runPosition(runLength: number, index: number): 'single' | 'first' | 'middle' | 'last' {
		if (runLength === 1) return 'single';
		if (index === 0) return 'first';
		if (index === runLength - 1) return 'last';
		return 'middle';
	}

	function anchorId(u: { section_hint: string | null; sequence: number }): string | undefined {
		return u.section_hint ? `section-${u.section_hint}-${u.sequence}` : undefined;
	}
</script>

<!-- Page background -->
<main style="background-color: var(--color-bg); min-height: 100vh;">

	<!-- Shared Popover.Root at page level — single instance for all avatar triggers -->
	<Popover.Root bind:open={isPopoverOpen} onOpenChange={(open) => { if (!open) currentSpeaker = null; }}>
		<Popover.Portal>
			<Popover.Content
				customAnchor={currentAnchor}
				sideOffset={8}
				trapFocus={true}
				escapeKeydownBehavior="close"
				interactOutsideBehavior="close"
				style="z-index: 50;
				       background-color: var(--color-surface); border: 1px solid var(--color-border); border-radius: 8px;
				       min-width: 300px; max-width: 400px;"
			>
				{#if currentSpeaker}
					<SpeakerPopover
						speaker={currentSpeaker}
						paletteVars={speakerVarsForPerson(currentSpeaker.person_id)}
					/>
				{/if}
			</Popover.Content>
		</Popover.Portal>

	<!-- Argument heading bar: full-width, surface background, border-bottom divider -->
	<header
		style="
			background-color: var(--color-surface);
			border-bottom: 1px solid var(--color-border);
			padding: var(--space-lg) var(--space-xl);
		"
	>
		<div style="max-width: 1200px; margin: 0 auto;">
			<!-- Case name: Display step (32px/600) — page-level titles only (D-09/UI-SPEC). -->
			<h1
				style="
					font-size: var(--font-size-display);
					font-weight: var(--font-weight-semibold);
					color: var(--color-text-primary);
					margin: 0 0 var(--space-xs) 0;
					line-height: var(--line-height-display);
				"
			>
				{data.argument.case_name}
			</h1>
			<!-- Subline: "No. {docket} · Argued {date} · Question {n}" -->
			<p
				style="
					font-size: var(--font-size-caption);
					font-weight: var(--font-weight-regular);
					color: var(--color-text-secondary);
					margin: 0;
					line-height: var(--line-height-caption);
				"
			>
				No. {data.argument.docket_number} · Argued {formatDate(data.argument.argued_date)} · Question {data.argument.question_number}
			</p>

			<!-- Speaker roster: two-column grid, Bench left, Advocates right — D-11 -->
			<!-- Both columns use --color-text-secondary for speaker names — apolitical framing
			     constraint (only the avatar fill differs by side); this note is load-bearing,
			     not decorative — do not "fix" it into a side-varying name colour. -->
			<div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-lg); margin-top: var(--space-lg);">
				<!-- Bench column -->
				<div>
					<p
						style="
							font-size: var(--font-size-caption);
							font-weight: var(--font-weight-semibold);
							color: var(--color-text-secondary);
							margin: 0 0 var(--space-sm) 0;
						"
					>
						Bench
					</p>
					{#each roster.bench as speaker (speaker.name)}
						<div style="display:flex;align-items:center;gap:var(--space-sm);margin:0 0 var(--space-xs) 0;{speakerVars(speaker.name)}">
							{#if speaker.person_id != null}
								<button
									type="button"
									onclick={(e) => onAvatarClick(speaker.person_id!, e.currentTarget as HTMLElement)}
									style="background:none;border:none;padding:var(--space-xs);cursor:pointer;border-radius:50%;display:flex;align-items:center;justify-content:center;"
									aria-label="View {speaker.name} details"
								>
									<div aria-hidden="true" class="speaker-fill" style="width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:var(--font-size-caption);font-weight:var(--font-weight-semibold);color:var(--color-bg);flex-shrink:0;">
										{speaker.initials ?? '?'}
									</div>
								</button>
							{:else}
								<div aria-hidden="true" class="speaker-fill" style="width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:var(--font-size-caption);font-weight:var(--font-weight-semibold);color:var(--color-bg);flex-shrink:0;margin:var(--space-xs);">
									{speaker.initials ?? '?'}
								</div>
							{/if}
							<p style="font-size:var(--font-size-body);font-weight:var(--font-weight-regular);color:var(--color-text-secondary);margin:0;">{speaker.name}</p>
						</div>
					{/each}
				</div>
				<!-- Advocates column -->
				<div>
					<p
						style="
							font-size: var(--font-size-caption);
							font-weight: var(--font-weight-semibold);
							color: var(--color-text-secondary);
							margin: 0 0 var(--space-sm) 0;
						"
					>
						Advocates
					</p>
					{#each roster.advocates as speaker (speaker.name)}
						<div style="display:flex;align-items:center;gap:var(--space-sm);margin:0 0 var(--space-xs) 0;{speakerVars(speaker.name)}">
							{#if speaker.person_id != null}
								<button
									type="button"
									onclick={(e) => onAvatarClick(speaker.person_id!, e.currentTarget as HTMLElement)}
									style="background:none;border:none;padding:var(--space-xs);cursor:pointer;border-radius:50%;display:flex;align-items:center;justify-content:center;"
									aria-label="View {speaker.name} details"
								>
									<div aria-hidden="true" class="speaker-fill" style="width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:var(--font-size-caption);font-weight:var(--font-weight-semibold);color:var(--color-bg);flex-shrink:0;">
										{speaker.initials ?? '?'}
									</div>
								</button>
							{:else}
								<div aria-hidden="true" class="speaker-fill" style="width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:var(--font-size-caption);font-weight:var(--font-weight-semibold);color:var(--color-bg);flex-shrink:0;margin:var(--space-xs);">
									{speaker.initials ?? '?'}
								</div>
							{/if}
							<p style="font-size:var(--font-size-body);font-weight:var(--font-weight-regular);color:var(--color-text-secondary);margin:0;">{speaker.name}</p>
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
						font-size: var(--font-size-caption);
						font-weight: var(--font-weight-regular);
						color: var(--color-text-secondary);
						line-height: var(--line-height-caption);
						margin: var(--space-sm) 0 0 0;
					"
				>
					Historical transcript imported from Oyez.org via Cornell ConvoKit (CC BY-NC 4.0).
					<a href="/attributions" style="color: var(--color-accent); text-decoration: underline;">
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

		<!-- Chat column: utterance stream, grouped into runs (D-19). No `overflow`
		     property is set on this element or any ancestor between here and the
		     document scroll root — see the sticky-avatar ancestor audit below. -->
		<div style="padding: var(--space-3xl) var(--transcript-pad-x);">
			{#if !data.utterances || data.utterances.length === 0}
				<!-- Empty state -->
				<p
					style="
						text-align: center;
						color: var(--color-text-secondary);
						font-size: var(--font-size-body);
					"
				>
					No utterances found for this argument.
				</p>
			{:else}
				<!-- Turn-gap logic: every top-level render item (a run, or a stage
				     direction) is itself a speaker change or a neutral interruption —
				     runs already absorb same-speaker continuation, so the gap between
				     adjacent top-level items is always the larger step (D-19/D-09
				     "vertical rhythm": a larger step at a speaker change than between a
				     continued speaker's turns). Within a run, the smaller step lives on
				     the bubble-stack column's own gap, set once below. -->
				{#each renderItems as item, i (i)}
					<div style="margin-top: {i === 0 ? '0' : 'var(--space-2xl)'};">
						{#if item.kind === 'stage'}
							<div id={anchorId(item.utterance)}>
								<StageDirection utterance={item.utterance} />
							</div>
						{:else if item.kind === 'undetermined'}
							<div id={anchorId(item.utterance)}>
								<UndeterminedBubble utterance={item.utterance} />
							</div>
						{:else}
							{@const first = item.utterances[0]}
							{@const isBench = first.side === 'BENCH'}
							{@const displayName = first.speaker_name ?? first.raw_speaker_label ?? ''}
							{@const displayInitials = first.speaker_initials ?? '?'}
							<!-- D-19 Style B2: one rail slot (sticky avatar) per run, spanning
							     the run's full rendered height via `align-items: stretch` on
							     this row plus the rail column stretching to match. Order is
							     controlled via CSS `order` (not row-reverse + duplicated
							     markup) so the avatar always sits on the run's own side —
							     left/outside for bench, right/outside for advocate (D-05). -->
							<div
								role="article"
								aria-label="{isBench ? 'Bench' : 'Advocate'}: {displayName}"
								style="
									display: flex;
									justify-content: {isBench ? 'flex-start' : 'flex-end'};
									align-items: stretch;
									gap: var(--transcript-rail-gap);
									{speakerVars(displayName)}
								"
							>
								<!-- Rail column: 40px gutter, stretched to run height by the
								     row's align-items:stretch. The 32px avatar leaves 8px of slack
								     in that gutter, and `align-items` decides which edge it lands
								     on. It must land on the OUTER edge for both sides, so the
								     avatar-to-bubble gap is `--transcript-rail-gap` alone and reads
								     identically for bench and advocate. Without it the avatar
								     defaults to the rail's inline-start on both sides — a `<button>`
								     resolves `width:auto` to fit-content rather than filling its
								     block container — which put the slack inside the gap for bench
								     (12px) and outside it for advocate (4px).
								     `justify-content:flex-end` pushes
								     the (single, run-level) avatar to the bottom of the column
								     when the column is taller than the avatar — the "short run,
								     avatar rests at the bottom" case. `position:sticky;bottom` on
								     the avatar wrapper is what produces every other scroll state
								     in the D-19 amendment table. No `overflow` on this column. -->
								<div
									style="
										order: {isBench ? 0 : 1};
										width: 40px;
										flex-shrink: 0;
										align-self: stretch;
										display: flex;
										flex-direction: column;
										align-items: {isBench ? 'flex-end' : 'flex-start'};
									"
								>
									<!-- `margin-top:auto` — NOT `justify-content:flex-end` on the
									     column — is what parks the avatar at the run's bottom.
									     Both are equivalent in Chromium (measured: the avatar holds
									     y=804..836 at every scroll offset through a 5,225px run at
									     390x844). WebKit is the reason for the difference: sticky
									     descendants of a flex container whose position comes from
									     `justify-content` are a long-standing iOS Safari weak spot,
									     whereas an auto margin resolves during flex layout and
									     leaves the sticky offset to apply cleanly afterwards.
									     `align-self:stretch` is stated explicitly rather than
									     inherited, so the column keeps a definite height — a rail
									     that hugs the 32px avatar has no travel range and sticky
									     silently does nothing. -->
									<div style="margin-top: auto; position: sticky; bottom: var(--sticky-bottom-inset);">
										{#if first.person_id != null}
											<button
												type="button"
												aria-label="View {displayName} details"
												onclick={(e) => onAvatarClick(first.person_id!, e.currentTarget as HTMLElement)}
												style="background:none;border:none;padding:0;cursor:pointer;border-radius:50%;
												       display:flex;align-items:center;justify-content:center;"
											>
												<div aria-hidden="true" class="speaker-fill" style="
													width: 32px; height: 32px; border-radius: 50%;
													display: flex; align-items: center; justify-content: center;
													font-size: var(--font-size-caption); font-weight: var(--font-weight-semibold);
													color: var(--color-bg); flex-shrink: 0;
												">{displayInitials}</div>
											</button>
										{:else}
											<div aria-hidden="true" class="speaker-fill" style="
												width: 32px; height: 32px; border-radius: 50%;
												display: flex; align-items: center; justify-content: center;
												font-size: var(--font-size-caption); font-weight: var(--font-weight-semibold);
												color: var(--color-bg); flex-shrink: 0;
											">{displayInitials}</div>
										{/if}
									</div>
								</div>

								<!-- Bubble stack: one ChatBubble per utterance in the run, tight
								     gap between them (the smaller vertical-rhythm step — D-19
								     corners already read as one grouped shape). flex:1 gives this
								     column a definite width so each ChatBubble's own
								     max-width:min(var(--bubble-max-width), 68ch) resolves against it, not against an
								     auto/content-based width. -->
								<div
									style="
										order: {isBench ? 1 : 0};
										display: flex;
										flex-direction: column;
										gap: var(--space-xs);
										align-items: {isBench ? 'flex-start' : 'flex-end'};
										flex: 1 1 auto;
										min-width: 0;
									"
								>
									{#each item.utterances as u, idx (u.sequence)}
										<!-- The section-anchor wrapper MUST carry the side alignment
										     itself. It is a plain block otherwise, and a plain block
										     spans the stack's full width — so the stack's
										     `align-items` aligns THIS wrapper (already full width, so
										     a no-op) while the bubble inside it falls back to the
										     block default and hugs the LEFT edge. That put advocate
										     bubbles ~86px away from their own right-hand avatar.
										     `width:100%` keeps the bubble's max-width:min(--bubble-max-width,68ch)
										     resolving against the stack, and `justify-content` puts
										     the bubble on the speaker's own side. -->
										<div
											id={anchorId(u)}
											style="
												width: 100%;
												display: flex;
												justify-content: {isBench ? 'flex-start' : 'flex-end'};
											"
										>
											<ChatBubble
												utterance={u}
												position={runPosition(item.utterances.length, idx)}
												showSpeakerName={idx === 0}
											/>
										</div>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				{/each}
			{/if}
		</div>
	</div>
	<MobileNavBar sections={sectionAnchors} />
	<VariantSwitcher />

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
