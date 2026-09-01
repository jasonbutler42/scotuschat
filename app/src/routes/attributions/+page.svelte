<!--
	Static Attributions & Licensing page (D-26, CORPUS-09/CORPUS-10).

	Fully static — no +page.server.ts needed (Architectural Responsibility Map,
	29-RESEARCH.md). Credits Oyez.org, Cornell ConvoKit, and SCDB (D-23) and
	states the Oyez CC BY-NC 4.0 license fact (D-24). Copy is exact per
	29-UI-SPEC.md's Copywriting Contract — do not paraphrase.
-->

<!-- Page background (--color-bg) -->
<main style="background-color: var(--color-bg); min-height: 100vh;">
	<!-- Header bar: full-width, --color-surface, border-bottom --color-border -->
	<header
		style="
			background-color: var(--color-surface);
			border-bottom: 1px solid var(--color-border);
			padding: var(--space-lg) var(--space-xl);
		"
	>
		<h1
			style="
				font-size: var(--font-size-heading);
				font-weight: var(--font-weight-semibold);
				color: var(--color-text-primary);
				margin: 0;
				line-height: 1.2;
			"
		>
			Attributions &amp; Licensing
		</h1>
	</header>

	<!-- Content area: max-width 860px, centered, top padding 48px (2xl) -->
	<div
		style="
			max-width: 860px;
			margin: 0 auto;
			padding: var(--space-3xl) var(--space-xl) 60px var(--space-xl);
		"
	>
		<!-- Intro paragraph -->
		<p
			style="
				font-size: var(--font-size-body);
				font-weight: var(--font-weight-regular);
				color: var(--color-text-primary);
				line-height: 1.6;
				margin: 0 0 var(--space-2xl) 0;
			"
		>
			Some oral arguments on this site come from a historical bulk import
			rather than direct PDF ingestion. This page credits the sources that
			made that import possible.
		</p>

		<!-- Oyez.org credit block -->
		<section style="margin-bottom: var(--space-2xl);">
			<p
				style="
					font-size: var(--font-size-caption);
					font-weight: var(--font-weight-regular);
					color: var(--color-text-primary);
					line-height: 1.4;
					margin: 0 0 var(--space-lg) 0;
				"
			>
				Historical oral argument transcripts and audio are sourced from
				<strong style="font-weight: var(--font-weight-semibold);">Oyez.org</strong>, a project of
				Justia and the Chicago-Kent College of Law.
			</p>

			<!-- Oyez license callout card -->
			<div
				style="
					background-color: var(--color-surface);
					border: 1px solid var(--color-border);
					border-radius: 4px;
					padding: var(--space-lg);
				"
			>
				<p
					style="
						font-size: var(--font-size-body);
						font-weight: var(--font-weight-regular);
						color: var(--color-text-primary);
						line-height: 1.6;
						margin: 0;
					"
				>
					Oyez.org's oral argument transcripts and audio are licensed under
					<strong style="font-weight: var(--font-weight-semibold);">
						<a
							href="https://creativecommons.org/licenses/by-nc/4.0/"
							target="_blank"
							rel="noopener noreferrer"
							style="color: var(--color-accent);"
						>
							Creative Commons Attribution-NonCommercial 4.0 (CC BY-NC 4.0)
						</a>
					</strong>.
				</p>
			</div>
		</section>

		<!-- Cornell ConvoKit credit block -->
		<section style="margin-bottom: var(--space-2xl);">
			<p
				style="
					font-size: var(--font-size-caption);
					font-weight: var(--font-weight-regular);
					color: var(--color-text-primary);
					line-height: 1.4;
					margin: 0 0 var(--space-xs) 0;
				"
			>
				Historical transcript data is drawn from Cornell's
				<strong style="font-weight: var(--font-weight-semibold);">ConvoKit Supreme Court Corpus</strong>,
				a research dataset built for conversational analysis.
			</p>
			<!-- ConvoKit academic-citation caption (13px muted) -->
			<p
				style="
					font-size: var(--font-size-caption);
					font-weight: var(--font-weight-regular);
					color: var(--color-text-secondary);
					line-height: 1.4;
					margin: var(--space-xs) 0 0 0;
				"
			>
				If you use this data for research, ConvoKit asks that you cite:
				Danescu-Niculescu-Mizil et al., "Echoes of Power", WWW 2012; and
				Chang et al., "ConvoKit", SIGDIAL 2020.
			</p>
		</section>

		<!-- SCDB credit block -->
		<section style="margin-bottom: 0;">
			<p
				style="
					font-size: var(--font-size-caption);
					font-weight: var(--font-weight-regular);
					color: var(--color-text-primary);
					line-height: 1.4;
					margin: 0;
				"
			>
				This project also credits the
				<strong style="font-weight: var(--font-weight-semibold);">Supreme Court Database (SCDB)</strong>
				for the broader data lineage this import relies on. SCDB's case-outcome
				and voting data is not imported or displayed on this site.
			</p>
		</section>
	</div>
</main>
