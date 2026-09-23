<script lang="ts">
	import type { SpeakerDetail } from '$lib/types/speaker';

	// Single formal-title mapping (mirrors api/models/models.py's OFFICE_TITLES /
	// office_title(), D-15). Exhaustive over the two canonical values only — an
	// unrecognized/blank office renders no title rather than a generic "Justice"
	// fallback or the raw canonical string, since the DB CHECK + NOT NULL
	// constraint (migrations 0020/0021) guarantees every stored office is valid.
	const OFFICE_TITLES: Record<string, string> = {
		chief: 'Chief Justice',
		associate: 'Associate Justice'
	};

	function officeTitle(office: string | null): string {
		return office ? (OFFICE_TITLES[office] ?? '') : '';
	}

	// Mirrors api/models/models.py's REASON_LEFT_TITLES / reason_left_title()
	// (Phase 39 D-01/D-15). The `?? ''` degrade-to-empty is the frontend half
	// of the Phase 37 CR-01 never-crash-on-a-non-canonical-value convention —
	// backend stays exhaustive-and-raises; this side never throws.
	const REASON_LEFT_TITLES: Record<string, string> = {
		retired: 'Retired',
		died: 'Died in office',
		promoted: 'Promoted'
	};

	function reasonLeftTitle(reason: string | null): string {
		return reason ? (REASON_LEFT_TITLES[reason] ?? '') : '';
	}

	let { speaker, paletteVars = '' } = $props<{
		speaker: SpeakerDetail;
		/** The route's --speaker-color/--family-color/--side-color declarations for
		 *  this person, so the popover paints the same hue as the avatar that
		 *  opened it under whichever colour variant is active. */
		paletteVars?: string;
	}>();

	// $derived, NOT const — same rule ChatBubble.svelte states at its own prop
	// block. This component is a single long-lived instance: the route holds one
	// <SpeakerPopover> inside a page-level Popover.Root and reassigns `speaker`
	// when a different avatar is picked, so a plain `const` off the prop keeps
	// the FIRST speaker's value and misclassifies every later one.
	const isBench = $derived(speaker.is_bench);

	// No side-colour computation here any more (this is where IN-02's collapsed
	// avatarBg/sideColor pair used to live). The avatar and the role pill paint
	// from the `.speaker-*` rules in app.css, driven by the route's palette
	// declarations on .popover-card, so the person keeps the same colour as the
	// avatar that opened the popover under every colour variant — and the
	// duplicate cannot reappear because there is no local colour value left to
	// copy.

	// $derived for the same reason as isBench above: a const IIFE would keep the
	// first speaker's initials on the fallback avatar after the prop changes.
	const initials = $derived.by(() => {
		const parts = speaker.full_name.trim().split(/\s+/).filter(Boolean);
		if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
		if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
		return '?';
	});

	// Per-photo state, so it must reset when the photo does. Without the $effect
	// a failed load on speaker A leaves showInitials true, and speaker B renders
	// initials even though B's photo is fine.
	let showInitials = $state(false);
	$effect(() => {
		speaker.photo_url_full;
		showInitials = false;
	});

	// Compact date formatting for the popover's birth/death line — deliberately
	// distinct from the argument page's full-month formatDate() helper; the
	// compact form exists for the tighter popover card only.
	// timeZone: 'UTC' is mandatory: every date here is a date-only DB value with
	// no time component, and pinning the zone keeps the rendered calendar day
	// identical regardless of the browser's local UTC offset.
	function formatShort(iso: string): string {
		return new Intl.DateTimeFormat('en-US', {
			month: 'short',
			day: 'numeric',
			year: 'numeric',
			timeZone: 'UTC'
		}).format(new Date(iso));
	}

	// Month-and-year formatting for the tenure date range — deliberately no
	// day component (39-UI-SPEC.md's copywriting row froze year-only as
	// "unchanged from current code"; this plan follows the mockup instead,
	// since mockup fidelity is the gap being closed here).
	// timeZone: 'UTC' is mandatory for the same reason as formatShort(): these
	// are date-only DB values, and formatting in a negative-offset local zone
	// would render the previous calendar day, which at a month boundary
	// changes the rendered month.
	function formatMonthYear(iso: string): string {
		return new Intl.DateTimeFormat('en-US', {
			month: 'short',
			year: 'numeric',
			timeZone: 'UTC'
		}).format(new Date(iso));
	}

	// Joins the two formatted tenure endpoints with a spaced en dash, keeping
	// the component's pre-existing fallbacks unchanged: a null start keeps
	// today's "?" and a null end keeps today's "present".
	function tenureRange(start: string | null, end: string | null): string {
		const startLabel = start ? formatMonthYear(start) : '?';
		const endLabel = end ? formatMonthYear(end) : 'present';
		return `${startLabel} – ${endLabel}`;
	}
</script>

{#snippet separator(pad: string)}<span style="padding:0 {pad};">·</span>{/snippet}
<div class="popover-card" style={paletteVars}>
	<!-- Header row: avatar + name/pill stack. Stays horizontal at every width —
	     a 60px avatar never needs to drop below a short name/pill stack. -->
	<div style="display:flex;flex-direction:row;align-items:flex-start;gap:var(--space-lg);">
		{#if speaker.photo_url_full && !showInitials}
			<img
				src={speaker.photo_url_full}
				alt={speaker.full_name}
				style="width:60px;height:60px;border-radius:50%;object-fit:cover;flex-shrink:0;"
				onerror={() => { showInitials = true; }}
			/>
		{:else}
			<div
				aria-hidden="true"
				class="speaker-fill"
				style="width:60px;height:60px;border-radius:50%;
				       display:flex;align-items:center;justify-content:center;
				       font-size:var(--font-size-lead);font-weight:var(--font-weight-semibold);
				       color:var(--color-bg);flex-shrink:0;"
			>{initials}</div>
		{/if}

		<div>
			<p style="font-size:var(--font-size-body);font-weight:var(--font-weight-semibold);color:var(--color-text-primary);margin:0;">{speaker.full_name}</p>
			<!-- Role pill — only rendered when role_name is non-null, exactly as today -->
			{#if speaker.role_name}
				<span
					class="speaker-ink speaker-stroke"
					style="display:inline-block;border-width:1px;border-style:solid;border-radius:9999px;
					       padding:var(--space-xs) var(--space-sm);font-size:var(--font-size-caption);
					       font-weight:var(--font-weight-semibold);line-height:1.2;
					       margin-top:var(--space-xs);"
				>{speaker.role_name}</span>
			{/if}
		</div>
	</div>

	<!-- Birth/death line: bench only, full width. Omitted entirely when both
	     dates are null; each half omitted independently otherwise. -->
	{#if isBench && (speaker.birthdate || speaker.death_date)}
		<p style="font-size:var(--font-size-caption);font-weight:var(--font-weight-regular);color:var(--color-text-secondary);line-height:var(--line-height-body);margin-top:var(--space-lg);margin-bottom:0;border-top:1px solid var(--color-border);padding-top:var(--space-lg);">{#if speaker.birthdate}b. {formatShort(speaker.birthdate)}{/if}{#if speaker.birthdate && speaker.death_date}{@render separator('var(--space-sm)')}{/if}{#if speaker.death_date}d. {formatShort(speaker.death_date)}{/if}</p>
	{/if}

	<!-- Advocate descriptor slot (D-16): unconditional placeholder text, no real
	     per-advocate data exists yet — do not invent plausible-looking data. -->
	{#if !isBench}
		<p style="font-size:var(--font-size-caption);font-weight:var(--font-weight-regular);font-style:italic;color:var(--color-text-secondary);margin-top:var(--space-lg);margin-bottom:0;border-top:1px solid var(--color-border);padding-top:var(--space-lg);">Coming soon</p>
	{/if}

	<!-- Bio paragraph: bench and advocate alike, full width. Omitted entirely
	     when there is no bio text on file — no "No bio available" filler.
	     P-06: renders in full, always — no clamp, no truncation, no internal
	     scroll cap. The Phase 45 BUG-02 clamp-and-expand affordance (a
	     3-line vendor box-clamp collapsed state with a "Read more" toggle)
	     is removed here: it is exactly the pattern P-06 bans for popover
	     content. Long bios simply make the popover taller; nothing is ever
	     hidden. -->
	{#if speaker.bio_text}
		<div style="margin-top:var(--space-lg);border-top:1px solid var(--color-border);padding-top:var(--space-lg);">
			<p style="font-size:var(--font-size-caption);font-weight:var(--font-weight-regular);line-height:var(--line-height-body);color:var(--color-text-secondary);margin:0;">{speaker.bio_text}</p>
		</div>
	{/if}

	<!-- Tenure list: bench only, full width, below the bio. API order preserved
	     — no client-side re-sort. One block per tenure, up to 3 lines each. -->
	{#if isBench && speaker.tenure.length > 0}
		<div style="border-top:1px solid var(--color-border);margin-top:var(--space-lg);padding-top:var(--space-lg);">
			{#each speaker.tenure as t, i}
				<div style="margin-top:{i === 0 ? '0' : 'var(--space-sm)'};">
					<!-- Row 1, always rendered: office title (left, semibold, the only
					     promoted element) and its month-and-year range (right-aligned,
					     never wraps). -->
					<div style="display:flex;justify-content:space-between;align-items:baseline;gap:var(--space-sm);">
						<span style="font-size:var(--font-size-caption);font-weight:var(--font-weight-semibold);line-height:var(--line-height-body);color:var(--color-text-primary);min-width:0;">{officeTitle(t.office)}</span>
						<span style="font-size:var(--font-size-caption);font-weight:var(--font-weight-regular);line-height:var(--line-height-body);color:var(--color-text-secondary);text-align:right;flex-shrink:0;white-space:nowrap;">{tenureRange(t.start_date, t.end_date)}</span>
					</div>
					<!-- Row 2, rendered only when appointed_by or reason_left is
					     non-null. Left cell renders appointed_by alone, or
					     appointed_by + party when the party is also non-null; right
					     cell renders reason_left alone. Never a placeholder for the
					     missing half of either cell. -->
					{#if t.appointed_by || t.reason_left}
						<div style="display:flex;justify-content:space-between;align-items:baseline;gap:var(--space-sm);">
							<span style="font-size:var(--font-size-caption);font-weight:var(--font-weight-regular);line-height:var(--line-height-body);color:var(--color-text-secondary);min-width:0;">{#if t.appointed_by}{t.appointed_by}{#if t.appointing_president_party}{@render separator('var(--space-xs)')}{t.appointing_president_party}{/if}{/if}</span>
							<span style="font-size:var(--font-size-caption);font-weight:var(--font-weight-regular);line-height:var(--line-height-body);color:var(--color-text-secondary);text-align:right;flex-shrink:0;">{#if t.reason_left}{reasonLeftTitle(t.reason_left)}{/if}</span>
						</div>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
</div>

<style>
	.popover-card {
		padding: var(--space-xl);
		display: block;
	}
</style>
