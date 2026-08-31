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
	assert.equal(report.residuals.filter((r) => r.value === '12px').length, 1);
});

test('layout: border-radius and grid-template-columns are never touched', () => {
	const src = '<div style="border-radius: 8px; grid-template-columns: 16px 32px;"></div>';
	assert.equal(t(src), src);
});

test('calc(): everything inside is left byte-identical', () => {
	const src = '<div style="padding: calc(8px + 16px); margin: 8px;"></div>';
	assert.equal(t(src), '<div style="padding: calc(8px + 16px); margin: var(--space-sm);"></div>');
});

test('script blocks are never rewritten, even when they contain a hex', () => {
	const src = `<script>const BADGE = { ok: '#4ade80' };<\/script>\n<div style="color: #4ade80;"></div>`;
	const out = t(src);
	assert.match(out, /const BADGE = \{ ok: '#4ade80' \};/, 'script literal must survive');
	assert.match(out, /style="color: var\(--color-status-published\);"/);
});

test('text content and non-style attributes are never rewritten', () => {
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
	assert.equal(report.residuals.filter((r) => r.value === '#64748b').length, 1);
});

test('idempotent: a second pass over converted output changes nothing', () => {
	const src =
		'<div style="color: #e2e8f0; font-size: 14px; padding: 8px 12px; min-height: 44px;"></div>';
	const once = t(src);
	const twice = t(once);
	assert.equal(twice, once);
});
