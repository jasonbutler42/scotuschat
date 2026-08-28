<script lang="ts">
	import type { TenureRow, SpeakerDetail } from '$lib/types/speaker';

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

	let { speaker } = $props<{ speaker: SpeakerDetail }>();

	const isBench = speaker.is_bench;

	// Single side-colour computation site (IN-02 closure — was two identically
	// computed variables, avatarBg and sideColor, used interchangeably). Every
	// site that needs the bench/advocate side colour calls this one function,
	// so the collapsed duplicate cannot silently reappear as a renamed copy of
	// the same expression shape. A plain function (not a quoted-string
	// ternary) computed once into a `const` — never reassigned, so no `$state`
	// is needed for this per-mount-fixed value.
	function resolveSideColor(bench: boolean): string {
		if (bench) return 'var(--color-side-bench)';
		return 'var(--color-side-advocate)';
	}
	const sideColor = resolveSideColor(isBench);

	const initials = (() => {
		const parts = speaker.full_name.trim().split(/\s+/).filter(Boolean);
		if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
		if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
		return '?';
	})();

	let showInitials = $state(false);

	// Bio clamp + expand (39-UI-SPEC.md "Bio text clamp + expand"). The toggle
	// only renders when the text is genuinely clamped — a short bio must never
	// show "Read more" with nothing to expand.
	let bioExpanded = $state(false);
	let bioOverflows = $state(false);
	let bioEl: HTMLParagraphElement | null = $state(null);

	$effect(() => {
		if (!bioEl || bioExpanded) return;
		bioOverflows = bioEl.scrollHeight > bioEl.clientHeight + 1;
	});

	function toggleBio(): void {
		bioExpanded = !bioExpanded;
	}

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

{#snippet separator(pad: number)}<span style="padding:0 {pad}px;">·</span>{/snippet}
<div class="popover-card">
	<!-- Header row: avatar + name/pill stack. Stays horizontal at every width —
	     a 60px avatar never needs to drop below a short name/pill stack. -->
	<div style="display:flex;flex-direction:row;align-items:flex-start;gap:16px;">
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
				style="width:60px;height:60px;border-radius:50%;background-color:{sideColor};
				       display:flex;align-items:center;justify-content:center;
				       font-size:18px;font-weight:600;color:#0f1117;flex-shrink:0;"
			>{initials}</div>
		{/if}

		<div>
			<p style="font-size:16px;font-weight:600;color:#e2e8f0;margin:0;">{speaker.full_name}</p>
			<!-- Role pill — only rendered when role_name is non-null, exactly as today -->
			{#if speaker.role_name}
				<span
					style="display:inline-block;border:1px solid {sideColor};border-radius:9999px;
					       padding:2px 10px;font-size:12px;font-weight:600;line-height:1.2;
					       color:{sideColor};margin-top:4px;"
				>{speaker.role_name}</span>
			{/if}
		</div>
	</div>

	<!-- Birth/death line: bench only, full width. Omitted entirely when both
	     dates are null; each half omitted independently otherwise. -->
	{#if isBench && (speaker.birthdate || speaker.death_date)}
		<p style="font-size:13px;font-weight:400;color:var(--color-text-secondary);line-height:1.5;margin-top:16px;margin-bottom:0;border-top:1px solid #334155;padding-top:16px;">{#if speaker.birthdate}b. {formatShort(speaker.birthdate)}{/if}{#if speaker.birthdate && speaker.death_date}{@render separator(8)}{/if}{#if speaker.death_date}d. {formatShort(speaker.death_date)}{/if}</p>
	{/if}

	<!-- Advocate descriptor slot (D-16): unconditional placeholder text, no real
	     per-advocate data exists yet — do not invent plausible-looking data. -->
	{#if !isBench}
		<p style="font-size:13px;font-weight:400;font-style:italic;color:var(--color-text-secondary);margin-top:16px;margin-bottom:0;border-top:1px solid #334155;padding-top:16px;">Coming soon</p>
	{/if}

	<!-- Bio paragraph: bench and advocate alike, full width. Omitted entirely
	     when there is no bio text on file — no "No bio available" filler. -->
	{#if speaker.bio_text}
		<div style="margin-top:16px;border-top:1px solid #334155;padding-top:16px;">
			<p
				bind:this={bioEl}
				class={bioExpanded ? 'bio-scroll' : ''}
				style="font-size:14px;font-weight:400;line-height:1.5;color:var(--color-text-secondary);margin:0;{bioExpanded ? 'max-height:150px;overflow-y:auto;' : 'display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:3;overflow:hidden;'}"
			>{speaker.bio_text}</p>
			{#if bioOverflows}
				<button
					type="button"
					onclick={toggleBio}
					aria-expanded={bioExpanded}
					style="font-size:13px;font-weight:400;color:var(--color-accent);text-decoration:underline;
					       background:none;border:none;padding:0;margin-top:4px;cursor:pointer;"
				>{bioExpanded ? 'Show less' : 'Read more'}</button>
			{/if}
		</div>
	{/if}

	<!-- Tenure list: bench only, full width, below the bio. API order preserved
	     — no client-side re-sort. One block per tenure, up to 3 lines each. -->
	{#if isBench && speaker.tenure.length > 0}
		<div style="border-top:1px solid #334155;margin-top:16px;padding-top:16px;">
			{#each speaker.tenure as t, i}
				<div style="margin-top:{i === 0 ? '0' : '8px'};">
					<!-- Row 1, always rendered: office title (left, semibold, the only
					     promoted element) and its month-and-year range (right-aligned,
					     never wraps). -->
					<div style="display:flex;justify-content:space-between;align-items:baseline;gap:8px;">
						<span style="font-size:13px;font-weight:600;line-height:1.5;color:#e2e8f0;min-width:0;">{officeTitle(t.office)}</span>
						<span style="font-size:13px;font-weight:400;line-height:1.5;color:var(--color-text-secondary);text-align:right;flex-shrink:0;white-space:nowrap;">{tenureRange(t.start_date, t.end_date)}</span>
					</div>
					<!-- Row 2, rendered only when appointed_by or reason_left is
					     non-null. Left cell renders appointed_by alone, or
					     appointed_by + party when the party is also non-null; right
					     cell renders reason_left alone. Never a placeholder for the
					     missing half of either cell. -->
					{#if t.appointed_by || t.reason_left}
						<div style="display:flex;justify-content:space-between;align-items:baseline;gap:8px;">
							<span style="font-size:13px;font-weight:400;line-height:1.5;color:var(--color-text-secondary);min-width:0;">{#if t.appointed_by}{t.appointed_by}{#if t.appointing_president_party}{@render separator(4)}{t.appointing_president_party}{/if}{/if}</span>
							<span style="font-size:13px;font-weight:400;line-height:1.5;color:var(--color-text-secondary);text-align:right;flex-shrink:0;">{#if t.reason_left}{reasonLeftTitle(t.reason_left)}{/if}</span>
						</div>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
</div>

<style>
	.popover-card {
		padding: 24px;
		display: block;
	}

	/* Bio-scoped scroll (BUG-02 revision, Figma "person popover with bio
	   examples" frame): only the expanded bio paragraph scrolls internally,
	   capped at 150px — the card itself no longer owns any scroll or height
	   ceiling. Thin custom scrollbar per explicit operator direction at the
	   Phase 45 checkpoint; thumb reuses the existing #334155 divider color
	   rather than introducing a new one. */
	.bio-scroll {
		scrollbar-width: thin;
		scrollbar-color: #334155 transparent;
	}
	.bio-scroll::-webkit-scrollbar {
		width: 3px;
	}
	.bio-scroll::-webkit-scrollbar-track {
		background: transparent;
	}
	.bio-scroll::-webkit-scrollbar-thumb {
		background: #334155;
		border-radius: 2px;
	}
</style>
