"""
Source-invariant guard for the Dev Tools frontend gate (Phase 43, Plan 43-03).

Closes 43-VALIDATION.md's third Wave 0 item ("does a frontend test harness exist
for /admin at all?"). It does — app/tests/*.browser.test.mjs, run via `node --test`,
driving a real Edge instance over CDP against a Vite dev server. That harness is
genuinely capable but is the wrong instrument for THIS gate specifically: proving
"absent outside development" through it would require standing up a second server
process with a different ENVIRONMENT value, and the value's whole purpose is to be
a per-deployment constant, not something a single test run flips mid-session. So
the automated coverage here is a source-invariant guard (read the two frontend
files as plain text and assert structural/textual invariants) plus `npm run check`
(svelte-check, run separately per the plan's own <verify> steps) — the rendered-HTML
confirmation of the production case stays a manual UAT step in Plan 43-04, per
43-VALIDATION.md's accepted fallback.

These tests open no database connection, start no server, and need no environment
variable — they read app/src/routes/admin/+page.svelte and +page.server.ts as plain
text and assert against source-file structure, mirroring tests/test_admin_router.py's
established read-the-source-text style.
"""

import os
import pathlib
import re


# ---------------------------------------------------------------------------
# Helper: resolve project root from this file's location (matches
# tests/test_admin_router.py::_project_root exactly, so these tests pass
# regardless of the working directory pytest is invoked from).
# ---------------------------------------------------------------------------


def _project_root() -> pathlib.Path:
    """Return the absolute path to the project root directory."""
    return pathlib.Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _read(rel_path: str) -> str:
    """Read a project-relative file as UTF-8 text."""
    return (_project_root() / rel_path).read_text(encoding="utf-8")


PAGE_SVELTE = "app/src/routes/admin/+page.svelte"
PAGE_SERVER_TS = "app/src/routes/admin/+page.server.ts"

# SvelteKit's client-visible env prefix — written as a module-level constant so
# the forbidden literal exists in exactly one place in this test module.
CLIENT_ENV_PREFIX = "PUBLIC_"

# The two locked error copies from 43-UI-SPEC.md's Copywriting Contract.
RESET_ENV_ERROR = "Reset failed: this action is not available in this environment."
RESET_MID_ERROR = (
    "Reset failed partway through — the database may be in an inconsistent state. "
    "Check server logs before retrying."
)


# ---------------------------------------------------------------------------
# Test 1: Dev Tools section is server-gated, not CSS-hidden, no dialog/modal.
# ---------------------------------------------------------------------------


def test_dev_tools_section_is_server_gated():
    svelte = _read(PAGE_SVELTE)

    # (a) The heading string appears exactly once.
    heading = "Dev Tools"
    heading_count = svelte.count(heading)
    assert heading_count == 1, (
        f"Expected the 'Dev Tools' heading to appear exactly once, found {heading_count} — "
        "a duplicate heading suggests the section was copy-pasted rather than gated once."
    )

    # (b) The heading sits after the {#if data.isDevelopment} opener and before the
    # matching close. Asserted by substring-index comparison (not a Svelte parse):
    # the gate opener must appear before the heading, and the heading must appear
    # before the file's final {/if} (the last one before the page's single closing
    # </main> tag, which this outer conditional wraps).
    gate_open = "{#if data.isDevelopment}"
    assert gate_open in svelte, (
        "Expected the Dev Tools section to be wrapped in {#if data.isDevelopment} — "
        "the client-side complement of the server-decided gate."
    )
    gate_idx = svelte.index(gate_open)
    heading_idx = svelte.index(heading)
    assert gate_idx < heading_idx, (
        "The {#if data.isDevelopment} gate must open BEFORE the Dev Tools heading — "
        "found the heading is not preceded by its gating conditional."
    )

    main_close_idx = svelte.rindex("</main>")
    last_if_close_idx = svelte.rindex("{/if}", 0, main_close_idx)
    assert heading_idx < last_if_close_idx < main_close_idx, (
        "Expected the Dev Tools heading to sit inside the {#if data.isDevelopment} "
        "block, whose matching close must land before the page's closing </main> tag."
    )

    # (c) Neither CSS-hiding mechanism appears anywhere in the file — the section
    # must be server-omitted, never rendered-then-hidden.
    assert re.search(r"display:\s*none", svelte) is None, (
        "Found a 'display: none' rule — the Dev Tools section's absence outside "
        "development must be a server omission, never a CSS hiding mechanism (D-07)."
    )
    assert re.search(r"visibility:\s*hidden", svelte) is None, (
        "Found a 'visibility: hidden' rule — same D-07 constraint as above."
    )

    # (d) No <dialog> element and no dialog/popover component import.
    assert "<dialog" not in svelte, (
        "Found a <dialog> element — the UI-SPEC locks a two-step inline confirm, "
        "not a modal/dialog element."
    )
    for line in svelte.splitlines():
        stripped = line.strip()
        if stripped.startswith("import ") and (
            "bits-ui" in stripped or "Popover" in stripped or "Dialog" in stripped
        ):
            raise AssertionError(
                f"Found a dialog/popover component import in +page.svelte: {stripped!r} — "
                "bits-ui is present in this project but the UI-SPEC explicitly does not "
                "use it for the Dev Tools section."
            )

    # isDevelopment must be genuinely produced server-side, not an undefined
    # property that silently evaluates falsy in the {#if}.
    server_ts = _read(PAGE_SERVER_TS)
    assert "isDevelopment" in server_ts, (
        "Expected 'isDevelopment' to be defined in +page.server.ts's load return — "
        "the {#if} in +page.svelte must read a value genuinely produced server-side."
    )


# ---------------------------------------------------------------------------
# Test 2: The environment value never crosses the server/client boundary.
# ---------------------------------------------------------------------------


def test_environment_not_client_exposed():
    svelte = _read(PAGE_SVELTE)
    assert "ENVIRONMENT" not in svelte, (
        "The raw ENVIRONMENT value must never appear in a client-side Svelte module — "
        "only the derived isDevelopment boolean may cross the server/client boundary."
    )

    server_ts = _read(PAGE_SERVER_TS)
    assert CLIENT_ENV_PREFIX not in server_ts, (
        f"Found SvelteKit's client-visible env prefix ({CLIENT_ENV_PREFIX!r}) in "
        "+page.server.ts — ENVIRONMENT must only ever be read through the server-only "
        "dynamic-private env module, never re-exposed as a PUBLIC_ variable."
    )


# ---------------------------------------------------------------------------
# Test 3: resetToFixture posts no operator-supplied input.
# ---------------------------------------------------------------------------


def test_reset_action_posts_no_operator_input():
    server_ts = _read(PAGE_SERVER_TS)
    assert "resetToFixture" in server_ts, (
        "Expected a 'resetToFixture' action in +page.server.ts's actions object."
    )

    # Isolate the resetToFixture action's own body so a formData() call elsewhere
    # in this file (a different action) cannot produce a false pass.
    start = server_ts.index("resetToFixture:")
    action_body = server_ts[start:]

    assert "request.formData()" not in action_body, (
        "resetToFixture must not call request.formData() — the backend endpoint has "
        "no request surface and this action must not invent one."
    )
    assert "corpus_dir" not in action_body, (
        "resetToFixture must not reference a corpus path — the fixture set is a "
        "hardcoded backend constant, never reachable from the frontend."
    )


# ---------------------------------------------------------------------------
# Test 4: exactly the two locked error copies exist, verbatim, no third variant.
# ---------------------------------------------------------------------------


def test_error_copies_match_ui_spec():
    server_ts = _read(PAGE_SERVER_TS)

    assert RESET_ENV_ERROR in server_ts, (
        "Expected the UI-SPEC's environment-refusal error copy verbatim in "
        "+page.server.ts."
    )
    assert RESET_MID_ERROR in server_ts, (
        "Expected the UI-SPEC's mid-reset-failure error copy verbatim in "
        "+page.server.ts."
    )

    # No third "Reset failed" variant exists — every quoted string starting with
    # this prefix must be one of the two locked copies above.
    occurrences = re.findall(r"'([^']*Reset failed[^']*)'", server_ts)
    assert len(occurrences) >= 2, (
        "Expected at least the two locked 'Reset failed' error copies as quoted "
        f"string literals in +page.server.ts, found {len(occurrences)}."
    )
    allowed = {RESET_ENV_ERROR, RESET_MID_ERROR}
    for occurrence in occurrences:
        assert occurrence in allowed, (
            f"Found an unexpected 'Reset failed' copy variant: {occurrence!r} — "
            "exactly two error copies are locked by the UI-SPEC; no third may exist."
        )
