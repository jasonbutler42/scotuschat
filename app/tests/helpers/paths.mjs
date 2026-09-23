/**
 * Directories resolved from this file's own location, never from cwd.
 *
 * The harnesses used to build their vite paths with `path.resolve('app/...')`
 * or `path.resolve('...')` depending on the file, so three of them only ran
 * from the repo root and one only from `app/`. There was no directory from
 * which `node --test tests/*.browser.test.mjs` could pass — the same
 * invocation-shape trap CLAUDE.md documents for pytest's conftest, where a
 * path-dependent assumption silently changed what ran.
 *
 * Anchoring on import.meta.url makes every harness runnable from anywhere.
 */
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url)); // app/tests/helpers

export const APP_DIR = path.resolve(here, '..', '..');
export const REPO_ROOT = path.resolve(APP_DIR, '..');
export const VITE_BIN = path.join(APP_DIR, 'node_modules', 'vite', 'bin', 'vite.js');
export const TESTS_DIR = path.resolve(here, '..');
