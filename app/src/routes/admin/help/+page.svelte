<script lang="ts">
	// Phase 49 Plan 03 — Admin Help page (REVIEW-01's vocabulary settled by
	// migration 0029's fold, plus the trust-tier and publish-gate vocabulary
	// from Phase 48). Deliberately scheduled after 49-02 so this page
	// documents the shipped three-axis model (status x trust tier x review
	// state) rather than a pre-fold shape that would need a revision pass
	// immediately.
	//
	// Static, server-data-free operator reference (D-29: no component
	// library, no new abstraction). Every badge formula below is copied
	// verbatim from its source of truth rather than re-invented:
	//   - status badge (14px): app/src/routes/admin/arguments/[id]/+page.svelte
	//     badgeStyle/badgeLabel — the version that already handles `candidate`
	//     (Phase 48 D-01), not the list page's stale fallback.
	//   - trust-tier badge (12px): app/src/routes/admin/arguments/+page.svelte
	//     tierBadgeStyle/tierLabel, byte-identical.
	//   - review-state badge: colors and labels from
	//     .planning/phases/49-review-model/49-UI-SPEC.md § Color (the queue
	//     screen that will render these for real is plan 49-05's scope, not
	//     this one's — the formula here is this page's own presentational
	//     choice, sized like the status badge since review_state is a primary
	//     row-state axis, not a passive info badge like trust tier).
	//
	// Apolitical hard constraint (CLAUDE.md): this page describes
	// transcription/attribution states, identically for every speaker role.
	// It contains no ranking, scoring, or comparison between Justices and
	// advocates, and no example below names a real Justice or advocate.

	function statusBadgeStyle(status: string): string {
		let color: string;
		if (status === 'published') {
			color = 'var(--color-status-published)';
		} else if (status === 'draft') {
			color = 'var(--color-status-draft)';
		} else if (status === 'unpublished') {
			color = 'var(--color-status-unpublished)';
		} else {
			// candidate (Phase 48 D-01) — the born state that replaced the
			// retired `pipeline` value.
			color = 'var(--color-text-secondary)';
		}
		return `border: 1px solid ${color}; border-radius: 4px; padding: var(--space-xs) var(--space-sm); font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); background-color: var(--color-surface); color: ${color}; display: inline-block;`;
	}

	function statusBadgeLabel(status: string): string {
		if (status === 'published') return 'Published';
		if (status === 'draft') return 'Draft';
		if (status === 'unpublished') return 'Unpublished';
		return 'Candidate';
	}

	// Copied verbatim from admin/arguments/+page.svelte's tierBadgeStyle/
	// tierLabel (Phase 48 plan 10, D-19/D-20) — passive/informational sizing.
	function tierBadgeStyle(tier: string): string {
		let color: string;
		if (tier === 'verified') {
			color = 'var(--color-tier-verified)';
		} else if (tier === 'trusted') {
			color = 'var(--color-tier-trusted)';
		} else if (tier === 'provisional') {
			color = 'var(--color-tier-provisional)';
		} else {
			color = 'var(--color-tier-uncertain)';
		}
		return `border: 1px solid ${color}; border-radius: 4px; padding: var(--space-xs) var(--space-sm); font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); background-color: var(--color-bg); color: ${color}; display: inline-block;`;
	}

	function tierBadgeLabel(tier: string): string {
		if (tier === 'verified') return 'Verified';
		if (tier === 'trusted') return 'Trusted';
		if (tier === 'provisional') return 'Provisional';
		return 'Uncertain';
	}

	// review_state badge colors/labels — .planning/phases/49-review-model/
	// 49-UI-SPEC.md § Color. Sized like the 14px status badge (this is a
	// primary row-state axis an operator acts on, not a passive info badge).
	function reviewBadgeStyle(state: string): string {
		let color: string;
		if (state === 'operator_confirmed') {
			color = 'var(--color-review-confirmed)';
		} else if (state === 'operator_edited') {
			color = 'var(--color-review-edited)';
		} else if (state === 'needs_review') {
			color = 'var(--color-status-warning)';
		} else {
			color = 'var(--color-review-unreviewed)';
		}
		return `border: 1px solid ${color}; border-radius: 4px; padding: var(--space-xs) var(--space-sm); font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); background-color: var(--color-surface); color: ${color}; display: inline-block;`;
	}

	function reviewBadgeLabel(state: string): string {
		if (state === 'operator_confirmed') return 'Confirmed';
		if (state === 'operator_edited') return 'Edited';
		if (state === 'needs_review') return 'Needs review';
		return 'Unreviewed';
	}

	const cardStyle =
		'background-color: var(--color-surface); border: 1px solid var(--color-border); border-radius: 8px; padding: var(--space-xl); margin-bottom: var(--space-lg);';
	const cardHeadingStyle = 'font-size: var(--font-size-heading); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); margin: 0 0 var(--space-lg) 0;';
	const bodyTextStyle = 'font-size: var(--font-size-body); color: var(--color-status-archived); margin: 0 0 var(--space-sm) 0; line-height: 1.5;';
</script>

<svelte:head>
	<title>Help — SCOTUS Chat Admin</title>
</svelte:head>

<main style="background-color: var(--color-bg); min-height: 100vh;">
	<header style="background-color: var(--color-surface); border-bottom: 1px solid var(--color-border); padding: var(--space-lg) var(--space-xl);">
		<h1 style="font-size: var(--font-size-heading); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); margin: 0;">Help</h1>
	</header>

	<div style="max-width: 860px; margin: 0 auto; padding: var(--space-3xl) var(--space-xl);">
		<p style="font-size: var(--font-size-body); color: var(--color-text-secondary); margin: 0 0 var(--space-xl) 0; line-height: 1.5;">
			This page explains the vocabulary the admin UI uses to describe an argument's
			transcription and attribution state: its lifecycle status, its trust tier, the
			review state of each speaker it attributes, and the two gates that decide
			whether it can go public. Every speaker role — Justice and advocate alike — is
			described with identical depth and vocabulary below; none of this ranks, scores,
			or compares one speaker's contributions against another's.
		</p>

		<!-- Card 1: Lifecycle statuses -->
		<div style={cardStyle}>
			<h2 style={cardHeadingStyle}>Lifecycle statuses</h2>
			<p style={bodyTextStyle}>
				An argument's <code>status</code> tracks where it sits in the pipeline-to-public
				lifecycle. It is a separate axis from trust tier and review state below — a
				<code>published</code> argument can still carry an <code>uncertain</code> trust
				tier if it was published with an override.
			</p>

			<div style="display: flex; flex-direction: column; gap: var(--space-md); margin-top: var(--space-lg);">
				<div style="display: flex; align-items: baseline; gap: var(--space-md); flex-wrap: wrap;">
					<span style={statusBadgeStyle('candidate')}>{statusBadgeLabel('candidate')}</span>
					<span style="font-size: var(--font-size-body); color: var(--color-status-archived);">
						Just resolved from a pipeline run, not yet reviewed by an operator. The born
						state every newly resolved argument starts in.
					</span>
				</div>
				<div style="display: flex; align-items: baseline; gap: var(--space-md); flex-wrap: wrap;">
					<span style={statusBadgeStyle('draft')}>{statusBadgeLabel('draft')}</span>
					<span style="font-size: var(--font-size-body); color: var(--color-status-archived);">
						An operator has started editing the argument (case metadata, participant
						links, etc.) but has not yet published it.
					</span>
				</div>
				<div style="display: flex; align-items: baseline; gap: var(--space-md); flex-wrap: wrap;">
					<span style={statusBadgeStyle('published')}>{statusBadgeLabel('published')}</span>
					<span style="font-size: var(--font-size-body); color: var(--color-status-archived);">
						Publicly visible on the site. An operator moves an argument here by
						publishing it, subject to the two gates below.
					</span>
				</div>
				<div style="display: flex; align-items: baseline; gap: var(--space-md); flex-wrap: wrap;">
					<span style={statusBadgeStyle('unpublished')}>{statusBadgeLabel('unpublished')}</span>
					<span style="font-size: var(--font-size-body); color: var(--color-status-archived);">
						An operator took a previously published argument back down. It keeps its
						publish history for the audit trail and can be republished later.
					</span>
				</div>
			</div>

			<p style="font-size: var(--font-size-caption); color: var(--color-text-secondary); margin: var(--space-lg) 0 0 0; line-height: 1.5;">
				A fifth enum value, <code>pipeline</code>, was retired by migration 0027 and
				replaced by <code>candidate</code> above. PostgreSQL cannot drop an enum value
				once minted, so <code>pipeline</code> remains in the database as a dead-but-
				permanent value; no argument in normal operation ever carries it.
			</p>
		</div>

		<!-- Card 2: Trust tiers -->
		<div style={cardStyle}>
			<h2 style={cardHeadingStyle}>Trust tiers</h2>
			<p style={bodyTextStyle}>
				A trust tier is <strong>derived</strong>, never typed in by hand. It is computed
				from each speaker attribution's <code>(source, method, review_state)</code> — where
				the data came from, how it was matched, and whether an operator has looked at it —
				and an argument's own tier is the <strong>floor</strong> (the least-trusted value)
				across every one of its speaker attributions. An argument with
				no utterances and no participants at all reads <code>uncertain</code> — the maximal-risk case,
				not a free pass.
			</p>

			<div style="display: flex; flex-direction: column; gap: var(--space-md); margin: var(--space-lg) 0;">
				<div style="display: flex; align-items: baseline; gap: var(--space-md); flex-wrap: wrap;">
					<span style={tierBadgeStyle('verified')}>{tierBadgeLabel('verified')}</span>
					<span style="font-size: var(--font-size-body); color: var(--color-status-archived);">
						A human has explicitly confirmed or edited this attribution, or it was
						entered directly by an operator.
					</span>
				</div>
				<div style="display: flex; align-items: baseline; gap: var(--space-md); flex-wrap: wrap;">
					<span style={tierBadgeStyle('trusted')}>{tierBadgeLabel('trusted')}</span>
					<span style="font-size: var(--font-size-body); color: var(--color-status-archived);">
						Matched directly against an authoritative identifier from the corpus or a
						seed dataset — no operator review yet, but a strong automatic match.
					</span>
				</div>
				<div style="display: flex; align-items: baseline; gap: var(--space-md); flex-wrap: wrap;">
					<span style={tierBadgeStyle('provisional')}>{tierBadgeLabel('provisional')}</span>
					<span style="font-size: var(--font-size-body); color: var(--color-status-archived);">
						Matched through a normalization or rule-based step — a weaker, heuristic
						match than a direct identifier lookup.
					</span>
				</div>
				<div style="display: flex; align-items: baseline; gap: var(--space-md); flex-wrap: wrap;">
					<span style={tierBadgeStyle('uncertain')}>{tierBadgeLabel('uncertain')}</span>
					<span style="font-size: var(--font-size-body); color: var(--color-status-archived);">
						Flagged for operator attention, unresolved, or matched by a method with no
						stronger tier rule — the fail-closed default for anything not otherwise
						accounted for.
					</span>
				</div>
			</div>

			<p style="font-size: var(--font-size-body); color: var(--color-status-archived); margin: var(--space-lg) 0 var(--space-sm) 0;">
				<code>derive_tier</code> evaluates these seven rules in order — the first one that
				matches wins:
			</p>
			<ol style="font-size: var(--font-size-body); color: var(--color-status-archived); margin: 0; padding-left: var(--space-xl); line-height: 1.6;">
				<li>Review state is Confirmed or Edited &rarr; Verified.</li>
				<li>Review state is Needs review &rarr; Uncertain.</li>
				<li>Source is <code>operator</code> and method is <code>manual</code> &rarr; Verified.</li>
				<li>
					Source/method is <code>(corpus, direct)</code> or <code>(seed, direct)</code>
					&rarr; Trusted.
				</li>
				<li>Method is <code>normalized</code> &rarr; Provisional.</li>
				<li>Source/method is <code>(pdf_pipeline, rule_based)</code> &rarr; Provisional.</li>
				<li>
					Anything else — including <code>(pdf_pipeline, llm_corrective)</code> and any
					unrecognised combination — &rarr; Uncertain (fail-closed).
				</li>
			</ol>
		</div>

		<!-- Card 3: Review states -->
		<div style={cardStyle}>
			<h2 style={cardHeadingStyle}>Review states</h2>
			<p style={bodyTextStyle}>
				A <code>review_state</code> records whether, and how, an operator has looked at a
				single attributed value — a speaker link on an argument, or a person's name. It is
				one of the three inputs to trust-tier derivation above, but it is its own fact:
				a record of human attention, not a score.
			</p>

			<div style="display: flex; flex-direction: column; gap: var(--space-md); margin: var(--space-lg) 0;">
				<div style="display: flex; align-items: baseline; gap: var(--space-md); flex-wrap: wrap;">
					<span style={reviewBadgeStyle('unreviewed')}>{reviewBadgeLabel('unreviewed')}</span>
					<span style="font-size: var(--font-size-body); color: var(--color-status-archived);">
						The default state. No operator has acted on this value yet.
					</span>
				</div>
				<div style="display: flex; align-items: baseline; gap: var(--space-md); flex-wrap: wrap;">
					<span style={reviewBadgeStyle('needs_review')}>{reviewBadgeLabel('needs_review')}</span>
					<span style="font-size: var(--font-size-body); color: var(--color-status-archived);">
						Flagged for operator attention — either by an importer that could not
						confidently resolve the value, or by an operator re-flagging a previous
						decision.
					</span>
				</div>
				<div style="display: flex; align-items: baseline; gap: var(--space-md); flex-wrap: wrap;">
					<span style={reviewBadgeStyle('operator_confirmed')}>{reviewBadgeLabel('operator_confirmed')}</span>
					<span style="font-size: var(--font-size-body); color: var(--color-status-archived);">
						An operator looked at this specific value and confirmed it is correct, with
						no change needed.
					</span>
				</div>
				<div style="display: flex; align-items: baseline; gap: var(--space-md); flex-wrap: wrap;">
					<span style={reviewBadgeStyle('operator_edited')}>{reviewBadgeLabel('operator_edited')}</span>
					<span style="font-size: var(--font-size-body); color: var(--color-status-archived);">
						An operator changed this value directly (for example, correcting a name or
						re-linking a speaker).
					</span>
				</div>
			</div>

			<p style="font-size: var(--font-size-body); color: var(--color-status-archived); margin: var(--space-lg) 0 var(--space-sm) 0;">
				Two transition rules are easy to get wrong:
			</p>
			<ul style="font-size: var(--font-size-body); color: var(--color-status-archived); margin: 0; padding-left: var(--space-xl); line-height: 1.6;">
				<li>
					An operator can push an already-reviewed value back to Needs review — but
					nothing ever returns a value to Unreviewed. Once a human has touched a value,
					that fact is permanent; a mistaken confirm is corrected by re-flagging it, not
					by erasing the record that a human looked at it.
				</li>
				<li>
					Confirmed is produced only by a per-item, explicit human action — never in
					bulk, and never by an importer. A bulk "confirm everything" control would make
					the claim behind the Verified tier cheap and unfalsifiable, so it does not
					exist.
				</li>
			</ul>
		</div>

		<!-- Card 4: Publish gates -->
		<div style={cardStyle}>
			<h2 style={cardHeadingStyle}>Publish gates</h2>
			<p style={bodyTextStyle}>
				Publishing an argument checks two gates, always in this order:
			</p>
			<ol style="font-size: var(--font-size-body); color: var(--color-status-archived); margin: 0 0 var(--space-lg) 0; padding-left: var(--space-xl); line-height: 1.6;">
				<li>
					<strong>Resolve-completeness gate</strong> — non-overridable. An argument whose
					resolve pipeline step never completed cannot be published at all; this is a
					completeness precondition, not a trust judgment, and it is checked before any
					override reason is even read.
				</li>
				<li>
					<strong>Trust gate</strong> — overridable. An argument whose current trust tier
					is Uncertain is blocked from publishing unless the operator supplies a
					non-blank reason. Supplying a reason authorizes exactly that one publish
					attempt — the override is never sticky. If the argument is later unpublished
					and republished while still Uncertain, it is blocked again and needs a fresh
					reason.
				</li>
			</ol>
			<p style="font-size: var(--font-size-caption); color: var(--color-text-secondary); margin: 0; line-height: 1.5;">
				The trust tier used by the second gate is always recomputed fresh at publish time,
				so the gate reflects the argument's current participants and utterances rather than a possibly
				stale stored value.
			</p>
		</div>
	</div>
</main>
