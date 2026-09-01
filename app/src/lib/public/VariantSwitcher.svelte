<script lang="ts">
	// Reading-layer variant switcher — a testing instrument, not a product
	// feature. It exists so people other than the operator can flip between
	// candidate presentations of the same transcript and say which one they
	// prefer, which is the only way the two hypotheses behind the deferred
	// reader-facing style switcher get tested (see
	// .planning/todos/pending/2026-08-28-transcript-style-switcher.md).
	//
	// It writes nothing but `data-*` attributes on <html>. Every axis is a pure
	// token redefinition in app.css, so this component can never be the reason a
	// variant looks the way it does — if an axis ever needed markup to change,
	// it would not belong in here.
	//
	// State lives in the URL (`?c=…&w=…`) rather than in a store or in
	// localStorage, because the unit a tester is given is a LINK. A shareable URL
	// means "look at this exact one" is expressible, a reload is stable, and two
	// testers can be sent deliberately different starting points.

	type Axis = {
		key: string;
		param: string;
		attr: string;
		label: string;
		options: { value: string; label: string; hint: string }[];
	};

	const AXES: Axis[] = [
		{
			key: 'colour',
			param: 'c',
			attr: 'data-colour',
			label: 'Colour',
			options: [
				{ value: 'speaker', label: 'Per speaker', hint: 'Every speaker their own hue; side shown by position only' },
				{ value: 'family', label: 'Warm / cool', hint: 'Per speaker, but the bench and advocates draw from opposite arcs' },
				{ value: 'side', label: 'Two colours', hint: 'One colour for the bench, one for the advocates' }
			]
		},
		{
			key: 'width',
			param: 'w',
			attr: 'data-width',
			label: 'Width',
			options: [
				{ value: '100', label: '100%', hint: 'Widest line; sides separated by the full rail' },
				{ value: '94', label: '94%', hint: 'Between the two' },
				{ value: '88', label: '88%', hint: 'Narrowest line' }
			]
		}
	];

	// The value each axis takes when the URL says nothing — the shipped default,
	// so an unparameterised link and a link that names the defaults render
	// identically.
	const DEFAULTS: Record<string, string> = { colour: 'speaker', width: '100' };

	let selected = $state<Record<string, string>>({ ...DEFAULTS });
	let open = $state(false);
	let mounted = $state(false);

	function apply(): void {
		const url = new URL(window.location.href);
		for (const axis of AXES) {
			document.documentElement.setAttribute(axis.attr, selected[axis.key]);
			if (selected[axis.key] === DEFAULTS[axis.key]) url.searchParams.delete(axis.param);
			else url.searchParams.set(axis.param, selected[axis.key]);
		}
		// replaceState, not SvelteKit navigation: changing a variant must not run
		// the route's load function, remount the transcript, or lose scroll
		// position — a tester comparing two widths needs to stay on the same
		// sentence while they switch.
		history.replaceState(history.state, '', url);
	}

	function choose(axisKey: string, value: string): void {
		selected[axisKey] = value;
		apply();
	}

	$effect(() => {
		const params = new URLSearchParams(window.location.search);
		for (const axis of AXES) {
			const raw = params.get(axis.param);
			if (raw && axis.options.some((o) => o.value === raw)) selected[axis.key] = raw;
		}
		apply();
		mounted = true;
		return () => {
			for (const axis of AXES) document.documentElement.removeAttribute(axis.attr);
		};
	});
</script>

<!-- Hidden until mounted so the collapsed pill does not flash in a position the
     attributes have not been applied to yet. -->
{#if mounted}
	<div
		style="position: fixed; top: var(--space-sm); right: var(--space-sm); z-index: 60;
		       display: flex; flex-direction: column; align-items: flex-end; gap: var(--space-xs);"
	>
		<button
			type="button"
			onclick={() => (open = !open)}
			aria-expanded={open}
			aria-controls="variant-switcher-panel"
			style="min-width: var(--touch-target); min-height: var(--touch-target);
			       border-radius: 9999px; cursor: pointer;
			       background-color: var(--color-surface); color: var(--color-text-primary);
			       border: 1px solid var(--color-border);
			       font-size: var(--font-size-caption); font-weight: var(--font-weight-semibold);
			       padding: 0 var(--space-sm);"
		>
			{open ? 'Close' : 'Style'}
		</button>

		{#if open}
			<div
				id="variant-switcher-panel"
				style="background-color: var(--color-surface); border: 1px solid var(--color-border);
				       border-radius: 6px; padding: var(--space-lg);
				       display: flex; flex-direction: column; gap: var(--space-lg);
				       max-width: min(280px, calc(100vw - var(--space-xl)));
				       max-height: calc(100vh - var(--touch-target) - var(--space-2xl));
				       overflow-y: auto;"
			>
				{#each AXES as axis (axis.key)}
					<fieldset style="border: none; padding: 0; margin: 0;">
						<legend
							style="font-size: var(--font-size-caption); font-weight: var(--font-weight-semibold);
							       color: var(--color-text-secondary); padding: 0 0 var(--space-xs) 0;"
						>
							{axis.label}
						</legend>
						<div style="display: flex; flex-direction: column; gap: var(--space-xs);">
							{#each axis.options as option (option.value)}
								{@const isActive = selected[axis.key] === option.value}
								<button
									type="button"
									onclick={() => choose(axis.key, option.value)}
									aria-pressed={isActive}
									style="text-align: left; cursor: pointer; border-radius: 4px;
									       padding: var(--space-sm);
									       background-color: {isActive ? 'var(--color-border)' : 'transparent'};
									       border: 1px solid {isActive ? 'var(--color-text-secondary)' : 'var(--color-border)'};
									       color: var(--color-text-primary);"
								>
									<span
										style="display: block; font-size: var(--font-size-body);
										       font-weight: var(--font-weight-regular);"
									>
										{option.label}
									</span>
									<span
										style="display: block; font-size: var(--font-size-caption);
										       color: var(--color-text-secondary); margin-top: var(--space-xs);"
									>
										{option.hint}
									</span>
								</button>
							{/each}
						</div>
					</fieldset>
				{/each}
			</div>
		{/if}
	</div>
{/if}
