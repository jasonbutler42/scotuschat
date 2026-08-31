import { test } from 'node:test';
import assert from 'node:assert/strict';
import { transform } from './tokenize-styles.mjs';

/** Run the transform and discard the report; most cases only care about output. */
function t(src, file = 'src/routes/admin/x.svelte') {
	return transform(src, file, { rewrites: 0, residuals: [], weight500: [], touchTargets: 0 });
}
function withReport(src, file = 'src/routes/admin/x.svelte') {
	const report = { rewrites: 0, residuals: [], weight500: [], touchTargets: 0 };
	return { out: transform(src, file, report), report };
}

test('colour: a mapped hex becomes its semantic token', () => {
	assert.equal(
		t('<div style="color: #e2e8f0; border: 1px solid #334155;"></div>'),
		'<div style="color: var(--color-text-primary); border: 1px solid var(--color-border);"></div>'
	);
});

test('colour: the 3-digit form is matched case-insensitively', () => {
	// #EF4444 and #ef4444 are the same colour; so are #FFF and #ffffff.
	assert.match(t('<i style="color: #EF4444;"></i>'), /var\(--color-destructive\)/);
});

test('colour: the ambiguous hexes resolve by path — public gets the side token', () => {
	const pub = t('<i style="color: #94a3b8;"></i>', 'src/lib/public/ChatBubble.svelte');
	const adm = t('<i style="color: #94a3b8;"></i>', 'src/routes/admin/+page.svelte');
	assert.match(pub, /var\(--color-side-bench\)/);
	assert.match(adm, /var\(--color-text-secondary\)/);
});

test('colour: the advocate hex resolves by path in both directions', () => {
	assert.match(
		t('<i style="color: #93c5fd;"></i>', 'src/lib/public/SpeakerPopover.svelte'),
		/var\(--color-side-advocate\)/
	);
	assert.match(t('<i style="color: #93c5fd;"></i>'), /var\(--color-accent\)/);
});

test('type: a font-size is rewritten but the same number in a width is not', () => {
	const out = t('<div style="font-size: 16px; width: 16px;"></div>');
	assert.equal(out, '<div style="font-size: var(--font-size-body); width: 16px;"></div>');
});

test('type: font-weight 400/600 map, and 500 maps while being flagged', () => {
	const { out, report } = withReport(
		'<b style="font-weight: 500;"></b><i style="font-weight: 400;"></i>'
	);
	assert.match(out, /var\(--font-weight-semibold\)/);
	assert.match(out, /var\(--font-weight-regular\)/);
	assert.equal(report.weight500.length, 1);
});

test('spacing: a four-component shorthand is mapped component by component', () => {
	assert.equal(
		t('<div style="padding: 4px 8px 16px 24px;"></div>'),
		'<div style="padding: var(--space-xs) var(--space-sm) var(--space-md) var(--space-lg);"></div>'
	);
});

test('spacing: an off-scale value is reported, never rounded', () => {
	const { out, report } = withReport('<div style="gap: 12px;"></div>');
	assert.equal(out, '<div style="gap: 12px;"></div>', '12px must survive byte-identical');
	assert.equal(report.residuals.filter((r) => r.value === '12px').length, 1, 'reported exactly once');
});

test('numerals inside a Svelte expression are JS, not CSS, and are left alone', () => {
	// The regression this pins: `font-weight: {a ? 600 : 400}` is a JavaScript
	// conditional. Rewriting its numerals produced `{a ? var(--x) : var(--y)}`,
	// which is not valid JS and failed the build.
	const src = `<b style="font-weight: {mode === 'url' ? 600 : 400}; padding: 8px;"></b>`;
	const out = t(src);
	assert.match(out, /font-weight: \{mode === 'url' \? 600 : 400\}/, 'expression untouched');
	assert.match(out, /padding: var\(--space-sm\)/, 'real CSS beside it still converts');
});

test('a quoted hex inside a Svelte expression still converts — it stays a string', () => {
	const src = `<b style="color: {a ? '#4ade80' : '#ef4444'};"></b>`;
	const out = t(src);
	assert.match(out, /'var\(--color-status-published\)'/);
	assert.match(out, /'var\(--color-destructive\)'/);
});

test('layout: border-radius and grid-template-columns are never touched', () => {
	const src = '<div style="border-radius: 8px; grid-template-columns: 16px 32px;"></div>';
	assert.equal(t(src), src);
});

test('calc(): everything inside is left byte-identical', () => {
	const src = '<div style="padding: calc(8px + 16px); margin: 8px;"></div>';
	assert.equal(t(src), '<div style="padding: calc(8px + 16px); margin: var(--space-sm);"></div>');
});

test('script blocks: a bare-hex string literal IS converted, the code around it is not', () => {
	// Admin screens hold status colours in lookup maps and interpolate them into
	// style strings. That is styling; it just lives in a script block.
	const src = `<script>const BADGE = { ok: '#4ade80' };\nlet n = 4;<\/script>`;
	const out = t(src);
	assert.match(out, /ok: 'var\(--color-status-published\)'/);
	assert.match(out, /let n = 4;/, 'surrounding code must be untouched');
});

test('script blocks: a CSS-shaped string literal gets the full declaration treatment', () => {
	const src = `<script>const card = 'background-color: #1e293b; padding: 24px; font-size: 16px;';<\/script>`;
	assert.match(
		t(src),
		/'background-color: var\(--color-surface\); padding: var\(--space-lg\); font-size: var\(--font-size-body\);'/
	);
});

test('script blocks: a string with no CSS in it is left alone even if it looks numeric', () => {
	const src = `<script>const msg = 'Deleted 16 rows'; const url = '/admin/people/16';<\/script>`;
	assert.equal(t(src), src);
});

test('script blocks: an apostrophe in a comment does not desync the string scanner', () => {
	// The regression that made a regex-based scan unusable: the apostrophe in
	// "0029's" paired with the next quote in real code and every span after it
	// was misaligned, silently skipping the rest of the file.
	const src =
		`<script>\n// migration 0029's fold, plus the list page's fallback\nconst c = '#4ade80';\nconst d = 'plain';<\/script>`;
	const out = t(src);
	assert.match(out, /const c = 'var\(--color-status-published\)'/, 'the real string still converts');
	assert.match(out, /0029's fold, plus the list page's fallback/, 'the comment is untouched');
	assert.match(out, /const d = 'plain'/);
});

test('script blocks: a multi-line template literal with holes is one span', () => {
	const src =
		'<script>\nconst s = `\n\tborder: 1px solid ${active ? sel : \'#334155\'};\n\tfont-size: 16px;\n`;\n<\/script>';
	const out = t(src);
	assert.match(out, /var\(--color-border\)/, 'a hex inside a ${} hole still maps');
	assert.match(out, /font-size: var\(--font-size-body\)/);
});

test('markup: a bare hex in an inline event handler is converted', () => {
	const src = `<button onmouseenter={(e) => { e.currentTarget.style.color = '#e2e8f0'; }}>x</button>`;
	assert.match(t(src), /style.color = 'var\(--color-text-primary\)'/);
});

test('comments: a hex named in prose becomes the token name, not a var() reference', () => {
	const src = '<!-- Header bar: #1e293b bg, border-bottom #334155 -->';
	assert.equal(t(src), '<!-- Header bar: --color-surface bg, border-bottom --color-border -->');
});

test('comments: an unmapped hex in prose is left alone', () => {
	const src = '<!-- the odd one out is #64748b -->';
	assert.equal(t(src), src);
});

test('text content and non-style attributes are never rewritten', () => {
	// The bare-hex rule is confined to Svelte {...} expression spans precisely so
	// that an ordinary attribute value and page copy stay untouched.
	const src = '<p title="#334155">the colour #334155 is a border</p>';
	assert.equal(t(src), src);
});

test('component <style> blocks are rewritten, but selectors are not', () => {
	const src = '<style>\n.a { color: #e2e8f0; padding: 8px; }\n</style>';
	assert.equal(t(src), '<style>\n.a { color: var(--color-text-primary); padding: var(--space-sm); }\n</style>');
});

test('min-height 44/36 become the touch-target tokens; other values do not', () => {
	const out = t('<a style="min-height: 44px;"></a><b style="min-height: 36px;"></b><c style="min-height: 120px;"></c>');
	assert.match(out, /var\(--touch-target\)/);
	assert.match(out, /var\(--touch-target-dense\)/);
	assert.match(out, /min-height: 120px/);
});

test('a semicolon inside a Svelte interpolation does not split the declaration', () => {
	const src = `<div style="color: {ok ? '#4ade80' : '#ef4444'}; padding: 8px;"></div>`;
	const out = t(src);
	assert.match(out, /padding: var\(--space-sm\)/);
	// The interpolation is still one declaration and its hexes still map.
	assert.match(out, /var\(--color-status-published\)/);
	assert.match(out, /var\(--color-destructive\)/);
});

test('an unmapped hex is reported and left byte-identical', () => {
	const { out, report } = withReport('<div style="color: #64748b;"></div>');
	assert.equal(out, '<div style="color: #64748b;"></div>');
	assert.equal(report.residuals.filter((r) => r.value === '#64748b').length, 1, 'reported exactly once');
});

test('idempotent: a second pass over converted output changes nothing', () => {
	const src =
		'<div style="color: #e2e8f0; font-size: 14px; padding: 8px 12px; min-height: 44px;"></div>';
	const once = t(src);
	const twice = t(once);
	assert.equal(twice, once);
});
