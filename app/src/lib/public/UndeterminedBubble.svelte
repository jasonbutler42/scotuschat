<script lang="ts">
	// Treatment D (D-01/SPEAKER-01): a turn the source never attributed to any
	// person — the sentinel-speaker fact stored at import (D-05), never
	// re-derived from raw_speaker_label text. Rendered as a bubble centred
	// between two reserved 40px rails, neither filled at rest (D-01 rejects
	// every treatment that guesses a side). S5: this is ALWAYS a singleton —
	// two consecutive undetermined turns are always two separate bubbles, so
	// unlike ChatBubble there is no run/position concept here at all.
	//
	// Every prop-derived value below is $derived, NOT const — same stale-prop
	// discipline ChatBubble.svelte documents. A plain `const` off a prop is
	// captured once at component init and frozen; this component is reused
	// across renders the same way ChatBubble is (keyed by sequence in the
	// route's {#each}), so a frozen value would survive into a different
	// utterance after navigation.
	let { utterance, onAvatarActivate } = $props<{
		utterance: {
			id: number | string;
			text: string;
			is_inaudible_marker?: boolean;
		};
		/** D-14/D-15: called with the activated avatar's own element (so the
		 *  route can anchor the shared popover to whichever side — left or
		 *  right — was clicked, never told which side in words) and the
		 *  turn's own stored is_inaudible_marker fact (so the card's first
		 *  paragraph can key off it, never off matching body text). */
		onAvatarActivate: (anchor: HTMLElement, inaudibleBody: boolean) => void;
	}>();

	// D-12/D-13: the identical derivation ChatBubble.svelte carries — one rule
	// for a whole-turn inaudible body, not a second copy, so a Treatment D
	// bubble whose body is also a lost-words marker reads the same as an
	// attributed bubble's.
	const lostWordsBody = $derived(utterance.is_inaudible_marker === true);

	function activateAvatar(anchor: HTMLElement): void {
		onAvatarActivate(anchor, lostWordsBody);
	}

	// D-16 touch: this Treatment D instance's own revealed/not-revealed state
	// — not a page-level flag, so tapping one undetermined bubble never
	// reveals another's avatars. Reset by an $effect keyed on utterance.id,
	// mirroring SpeakerPopover's showInitials reset: the route's {#each} keys
	// this component by sequence, so an existing instance can be handed a
	// DIFFERENT utterance when the render list changes, and a stale `true`
	// here would leave a new turn's avatars looking already-revealed.
	let revealed = $state(false);
	$effect(() => {
		utterance.id;
		revealed = false;
	});

	// D-16 touch: a first tap anywhere on the row reveals both avatars and
	// opens nothing — the hidden avatars ignore pointer events at that point,
	// so the tap necessarily lands on the rail or bubble. A second, separate
	// tap then reaches a now-visible avatar button, which activates it via
	// its own onclick like any other pointer. Checking event.pointerType
	// (not a media query read at tap time) means a hybrid touch laptop still
	// behaves correctly, and keyboard users get the same reveal through
	// :focus-within below, independent of this handler.
	function handleRowPointerUp(event: PointerEvent): void {
		if (event.pointerType === 'touch') {
			revealed = true;
		}
	}
</script>

<!-- No speaker-identity colour class or per-speaker/side custom property
     anywhere in this component — an undetermined turn is deliberately
     assigned to neither a speaker nor a side (D-01). No `position: sticky`
     either: a Treatment D item is always exactly one utterance (S5), so
     there is no run for a rail avatar to track scroll through. D-16/D-01:
     the dashed `?` avatar below is revealed by ONE row-level CSS rule
     (`.undetermined-row:hover .undetermined-avatar` etc.) that targets BOTH
     rails at once — a one-sided reveal is structurally impossible, not just
     avoided by care. -->
<div
	role="article"
	aria-label="Undetermined speaker"
	class="undetermined-row"
	data-revealed={revealed}
	onpointerup={handleRowPointerUp}
	style="
		display: flex;
		justify-content: center;
		align-items: center;
		gap: var(--transcript-rail-gap);
	"
>
	<div class="undetermined-rail undetermined-rail-left" style="width: 40px; flex-shrink: 0; display: flex; align-items: center; justify-content: flex-end;">
		<!-- Pushed to this rail's END (the edge nearest the bubble) — the right
		     rail below mirrors this with justify-content: flex-start, so the
		     avatar-to-bubble gap reads equal on both sides. -->
		<button
			type="button"
			class="undetermined-avatar"
			aria-label="Undetermined speaker details"
			onclick={(e) => activateAvatar(e.currentTarget as HTMLElement)}
			style="background:none;border:none;padding:0;cursor:pointer;border-radius:50%;
			       display:flex;align-items:center;justify-content:center;"
		>
			<div aria-hidden="true" style="
					width: 32px; height: 32px; border-radius: 50%;
					border: 1px dashed var(--color-text-secondary);
					background: transparent;
					display: flex; align-items: center; justify-content: center;
					font-size: var(--font-size-caption); font-weight: var(--font-weight-semibold);
					color: var(--color-text-secondary);
				">?</div>
		</button>
	</div>

	<div style="
			max-width: min(var(--bubble-max-width-undetermined), 63ch);
			min-width: 0;
			background-color: var(--color-surface);
			border: 1px solid var(--color-border);
			border-radius: 6px 6px 6px 6px;
			padding: var(--space-sm) var(--bubble-pad-x);
		">
		<!-- Label row — shown on EVERY Treatment D bubble, never suppressed as
		     a "continuation" the way ChatBubble suppresses its name row: S5
		     guarantees there is never a continuation here to suppress it for. -->
		<div style="margin-bottom: var(--space-sm);">
			<span style="
					font-size: var(--font-size-caption);
					font-weight: var(--font-weight-regular);
					font-style: var(--font-style-italic);
					opacity: var(--opacity-muted);
					color: var(--color-text-secondary);
				">undetermined speaker</span>
		</div>

		<!-- Body text — ChatBubble's own Lead size/weight/line-height/zero
		     margin; ink and italics driven by the same `utterance-body`
		     class pair ChatBubble uses (D-13: one rule, not a second copy). -->
		<p
			class="utterance-body"
			class:is-inaudible-marker={lostWordsBody}
			style="
				font-size: var(--font-size-lead);
				font-weight: var(--font-weight-regular);
				line-height: var(--line-height-lead);
				margin: 0;
			"
		>{utterance.text}</p>
	</div>

	<div class="undetermined-rail undetermined-rail-right" style="width: 40px; flex-shrink: 0; display: flex; align-items: center; justify-content: flex-start;">
		<!-- Pushed to this rail's START (the edge nearest the bubble) — mirrors
		     the left rail's flex-end above. -->
		<button
			type="button"
			class="undetermined-avatar"
			aria-label="Undetermined speaker details"
			onclick={(e) => activateAvatar(e.currentTarget as HTMLElement)}
			style="background:none;border:none;padding:0;cursor:pointer;border-radius:50%;
			       display:flex;align-items:center;justify-content:center;"
		>
			<div aria-hidden="true" style="
					width: 32px; height: 32px; border-radius: 50%;
					border: 1px dashed var(--color-text-secondary);
					background: transparent;
					display: flex; align-items: center; justify-content: center;
					font-size: var(--font-size-caption); font-weight: var(--font-weight-semibold);
					color: var(--color-text-secondary);
				">?</div>
		</button>
	</div>
</div>

<!-- Component-scoped style — the codebase's one exception to "everything is
     inline" (DESIGN-SYSTEM.md Styling mechanism). `:hover`/`:focus-within`/a
     hover-media gate cannot be expressed as an inline style attribute; the
     120ms transition is likewise an inline VALUE here because no motion
     token exists elsewhere in this codebase to reuse. Never display:none or
     aria-hidden on .undetermined-avatar — both buttons stay in the DOM and
     in tab order always; only opacity/pointer-events change (D-16, WCAG). -->
<style>
	.undetermined-avatar {
		opacity: 0;
		pointer-events: none;
		transition: opacity 120ms ease;
	}

	@media (hover: hover) {
		.undetermined-row:hover .undetermined-avatar {
			opacity: 1;
			pointer-events: auto;
		}
	}

	/* D-16 keyboard: focusing either avatar reveals both, matching the hover
	   behavior exactly — outside the hover media query, so a keyboard user
	   on a touch-only device still gets the reveal. */
	.undetermined-row:focus-within .undetermined-avatar {
		opacity: 1;
		pointer-events: auto;
	}

	/* D-16 touch: the row's own per-instance revealed state (see
	   handleRowPointerUp above), not a media query — this is what lets a
	   first tap reveal without opening, independent of hover/focus. */
	.undetermined-row[data-revealed='true'] .undetermined-avatar {
		opacity: 1;
		pointer-events: auto;
	}
</style>
