/** Phase 37 Wave 0 executable/static Office interaction contract. */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import test from 'node:test';

const pagePath = path.resolve('app/src/routes/admin/people/[id]/+page.svelte');
const serverPath = path.resolve('app/src/routes/admin/people/[id]/+page.server.ts');
const page = readFileSync(pagePath, 'utf8');
const server = readFileSync(serverPath, 'utf8');

function officeMarkup(source = page) {
	// Anchor on the actual Office fieldset/radiogroup element rather than the
	// bare word "Office" — a naive substring search would match the very
	// first mention of "office" anywhere in the file (e.g. a TypeScript type
	// comment or an "invalidOfficeOriginal" identifier declared earlier in
	// <script>), landing the extraction window nowhere near the real markup.
	const start = /<fieldset|role=["']radiogroup["']/.test(source)
		? source.search(/<fieldset|role=["']radiogroup["']/)
		: -1;
	assert.notEqual(start, -1, 'people editor must render an Office field');
	return source.slice(Math.max(0, start - 1000), start + 7000);
}

test('Office is a native one-of-two radio group ordered Chief then Associate', () => {
	const markup = officeMarkup();
	assert.match(markup, /<fieldset|role=["']radiogroup["']/);
	assert.match(markup, /<legend[^>]*>\s*Office\s*<\/legend>|aria-label=["']Office["']/s);
	assert.equal((markup.match(/type=["']radio["']/g) ?? []).length, 2);
	assert.ok(markup.indexOf('Chief') < markup.indexOf('Associate'));
	assert.match(markup, /value=["']chief["']/);
	assert.match(markup, /value=["']associate["']/);
});

test('native radio semantics provide idempotent click and arrow/space keyboard behavior', () => {
	const markup = officeMarkup();
	const names = [...markup.matchAll(/type=["']radio["'][\s\S]{0,500}?name=["']([^"']+)["']/g)].map((m) => m[1]);
	assert.equal(names.length, 2, 'both segments must be native radios');
	assert.equal(names[0], names[1], 'same-name radios enforce exactly one selected value');
	assert.doesNotMatch(markup, /onclick[^\n]*(?:undefined|null|''|""|toggle)/i);
});

test('Office segments meet the 44px target and locked selected/focus styling', () => {
	const markup = officeMarkup();
	assert.match(markup, /min-height:\s*44px/);
	assert.match(markup, /padding:\s*8px\s+16px/);
	assert.match(markup, /#93c5fd/i);
	assert.match(page, /focus-visible/);
	assert.match(page, /outline:\s*(?:2px|3px)[^;]*#93c5fd|outline-color:\s*#93c5fd/i);
});

test('a newly added tenure row defaults locally to Associate', () => {
	const addRow = page.slice(page.indexOf('function addTenureRow'), page.indexOf('function removeTenureRow'));
	assert.match(addRow, /office:\s*['"]associate['"]/);
	assert.doesNotMatch(addRow, /seat\s*:/);
});

test('invalid legacy Office leaves neither option selected and preserves the original', () => {
	assert.match(page, /invalidOfficeOriginal/);
	assert.match(page, /office:\s*(?:null|['"]['"])/);
	assert.match(page, /Unrecognized office:\s*[“"]\{[^}]+\}[”"]\. Select Chief or Associate before saving\./);
	assert.match(page, /No office was recorded\. Select Chief or Associate before saving\./);
});

test('invalid Office error is an associated alert and selecting a radio clears it', () => {
	const markup = officeMarkup();
	assert.match(markup, /role=["']alert["']/);
	assert.match(markup, /aria-describedby=/);
	assert.match(markup, /aria-invalid=/);
	assert.match(page, /invalidOfficeOriginal\s*=\s*null|delete\s+row\.invalidOfficeOriginal/);
});

test('save blocks every unresolved row and focuses the first invalid Office group', () => {
	assert.match(page, /Select Chief or Associate for every tenure period before saving\./);
	assert.match(page, /focus\(\)/);
	assert.match(page, /find(?:Index)?\([^)]*invalidOfficeOriginal|firstInvalidOffice/);
	assert.match(page, /preventDefault\(\)/);
});

test('hidden office JSON serializes local selections through the existing save form', () => {
	assert.match(page, /type=["']hidden["'][\s\S]{0,300}?name=["']tenures["']/);
	assert.match(page, /JSON\.stringify\(tenureRows\)/);
	assert.match(page, /form=["']save-form["']/);
	assert.doesNotMatch(officeMarkup(), /name=["']seat["']/);
});

test('server action allowlists office and rejects unresolved payload before PATCH', () => {
	assert.match(server, /office:\s*string/);
	assert.match(server, /\{\s*office,\s*start_date,\s*end_date/);
	assert.match(server, /office\s*!==\s*['"]chief['"][\s\S]*office\s*!==\s*['"]associate['"]/);
	const invalid = server.indexOf('Select Chief or Associate for every tenure period before saving.');
	const patch = server.indexOf("method: 'PATCH'");
	assert.ok(invalid !== -1 && patch !== -1 && invalid < patch);
});

test('failed save rehydrates all submitted profile and tenure edits', () => {
	const failureReturns = [...server.matchAll(/return fail\([^;]+;/gs)].map((m) => m[0]).join('\n');
	assert.match(failureReturns, /tenures/);
	assert.match(failureReturns, /full_name/);
	assert.match(failureReturns, /first_name/);
	assert.match(failureReturns, /birthdate/);
	assert.match(page, /form\?\.tenures/);
	assert.match(page, /form\?\.full_name/);
});

test('server-failure restoration keeps Office selection and unrelated edits local', () => {
	assert.match(page, /form\?\.tenures[\s\S]{0,1000}tenureRows\s*=/);
	assert.match(page, /form\?\.(?:full_name|values)/);
	assert.doesNotMatch(page, /location\.reload|window\.location/);
});
