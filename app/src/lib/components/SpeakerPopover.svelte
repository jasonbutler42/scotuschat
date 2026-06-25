<script lang="ts">
	interface TenureRow {
		seat: string | null;
		start_date: string | null;
		end_date: string | null;
	}

	interface SpeakerDetail {
		person_id: number;
		full_name: string;
		role_name: string | null;
		photo_url_full: string | null;
		is_bench: boolean;
		tenure: TenureRow[];
		appointing_president: string | null;
	}

	let { speaker } = $props<{ speaker: SpeakerDetail }>();

	const isBench = speaker.is_bench;
	const avatarBg = isBench ? '#94a3b8' : '#93c5fd';

	const initials = (() => {
		const parts = speaker.full_name.trim().split(/\s+/).filter(Boolean);
		if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
		if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
		return '?';
	})();

	let showInitials = $state(false);
</script>

<div class="popover-card">
	<!-- Photo / initials circle (60px) -->
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

	<!-- Text block -->
	<div style="flex-shrink:1;">
		<!-- Speaker name -->
		<p style="font-size:16px;font-weight:600;color:#e2e8f0;margin:0 0 2px 0;">{speaker.full_name}</p>

		<!-- Role name — only when non-null -->
		{#if speaker.role_name}
			<p style="font-size:13px;font-weight:400;color:#94a3b8;margin:0;">{speaker.role_name}</p>
		{/if}

		<!-- Bench-only block: tenure rows + appointing president -->
		{#if isBench}
			<div style="border-top:1px solid #334155;margin-top:8px;padding-top:8px;">
				{#each speaker.tenure as t}
					<p style="font-size:13px;color:#94a3b8;margin:0 0 4px 0;">
						{t.seat ?? 'Justice'} — {t.start_date ? t.start_date.slice(0, 4) : '?'}–{t.end_date ? t.end_date.slice(0, 4) : 'present'}
					</p>
				{/each}
				{#if speaker.appointing_president}
					<p style="font-size:13px;color:#94a3b8;margin:4px 0 0 0;">
						Appointed by {speaker.appointing_president}
					</p>
				{/if}
			</div>
		{/if}
	</div>
</div>

<style>
	.popover-card {
		background-color: #1e293b;
		border: 1px solid #334155;
		border-radius: 8px;
		padding: 24px;
		min-width: 280px;
		max-width: 360px;
		display: flex;
		flex-direction: row;
		align-items: flex-start;
		gap: 16px;
	}

	@media (max-width: 767px) {
		.popover-card {
			flex-direction: column;
			align-items: center;
			text-align: center;
		}
	}
</style>
