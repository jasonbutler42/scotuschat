<script lang="ts">
	interface TenureRow {
		// Canonical "chief"/"associate" storage value (Phase 37 D-15/D-17).
		office: string | null;
		start_date: string | null;
		end_date: string | null;
		// Canonical "retired"/"died"/"promoted" storage value, or null when the
		// tenure has no recorded reason (open tenure, or unknown historical row —
		// Phase 39 D-01/D-02).
		reason_left: string | null;
		// Phase 39 (D-13, promote not add-alongside): per-tenure appointing
		// president, replacing the retired top-level appointing_president field.
		appointed_by: string | null;
		// Phase 39 (D-11/D-12, reverses T-14-02): factual historical record about
		// the appointing president, not the Justice. Rendered identically for
		// every tenure entry — never styled or ordered by its value.
		appointing_president_party: string | null;
	}

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

	let { speaker } = $props<{ speaker: SpeakerDetail }>();

	const isBench = speaker.is_bench;
	const avatarBg = isBench ? '#94a3b8' : '#93c5fd';
	// Bench-vs-advocate side accent — pre-existing avatar distinction, reused
	// for the role pill. This is a side distinction, never a party/value one.
	const sideColor = isBench ? '#94a3b8' : '#93c5fd';

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
				style="width:60px;height:60px;border-radius:50%;background-color:{avatarBg};
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
		<p style="font-size:13px;font-weight:400;color:#94a3b8;line-height:1.5;margin-top:16px;margin-bottom:0;border-top:1px solid #334155;padding-top:16px;">{#if speaker.birthdate}b. {formatShort(speaker.birthdate)}{/if}{#if speaker.birthdate && speaker.death_date}{@render separator(8)}{/if}{#if speaker.death_date}d. {formatShort(speaker.death_date)}{/if}</p>
	{/if}

	<!-- Advocate descriptor slot (D-16): unconditional placeholder text, no real
	     per-advocate data exists yet — do not invent plausible-looking data. -->
	{#if !isBench}
		<p style="font-size:13px;font-weight:400;font-style:italic;color:#94a3b8;margin-top:16px;margin-bottom:0;border-top:1px solid #334155;padding-top:16px;">Coming soon</p>
	{/if}

	<!-- Bio paragraph: bench and advocate alike, full width. Omitted entirely
	     when there is no bio text on file — no "No bio available" filler. -->
	{#if speaker.bio_text}
		<div style="margin-top:16px;border-top:1px solid #334155;padding-top:16px;">
			<p
				bind:this={bioEl}
				style="font-size:14px;font-weight:400;line-height:1.5;color:#94a3b8;margin:0;{bioExpanded ? '' : 'display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:3;overflow:hidden;'}"
			>{speaker.bio_text}</p>
			{#if bioOverflows}
				<button
					type="button"
					onclick={toggleBio}
					aria-expanded={bioExpanded}
					style="font-size:13px;font-weight:400;color:#93c5fd;text-decoration:underline;
					       background:none;border:none;padding:0;margin-top:4px;cursor:pointer;"
				>{bioExpanded ? 'Show less' : 'Read more'}</button>
			{/if}
		</div>
	{/if}

	<!-- Tenure list: bench only, full width, below the bio. API order preserved
	     — no client-side re-sort. One block per tenure, up to 3 lines each. -->
	{#if isBench && speaker.tenure.length > 0}
		<div style="border-top:1px solid #334155;margin-top:16px;padding-top:16px;">
			{#each speaker.tenure as t}
				<div style="margin-bottom:16px;">
					<p style="font-size:13px;font-weight:400;line-height:1.5;color:#94a3b8;margin:0;">{officeTitle(t.office)} — {t.start_date ? t.start_date.slice(0, 4) : '?'}–{t.end_date ? t.end_date.slice(0, 4) : 'present'}</p>
					<!-- Only rendered when appointed_by is non-null; the party half is
					     appended only when it is also non-null. Never render a
					     placeholder for the missing half. -->
					{#if t.appointed_by}
						<p style="font-size:13px;font-weight:400;line-height:1.5;color:#94a3b8;margin:0;">{t.appointed_by}{#if t.appointing_president_party}{@render separator(4)}{t.appointing_president_party}{/if}</p>
					{/if}
					{#if t.reason_left}
						<p style="font-size:13px;font-weight:400;line-height:1.5;color:#94a3b8;margin:0;">{reasonLeftTitle(t.reason_left)}</p>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
</div>

<style>
	.popover-card {
		background-color: #1e293b;
		border: 1px solid #334155;
		border-radius: 8px;
		padding: 24px;
		min-width: 300px;
		max-width: 400px;
		display: block;
	}
</style>
