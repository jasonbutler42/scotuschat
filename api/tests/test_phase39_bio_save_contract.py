"""
Phase 39 Plan 07 (gap closure) — Bio save contract.

Closes 39-UAT.md gap 1 / test 10: an operator typed a bio into the
Biography card and clicked Save Person, but nothing was saved. The bug
was a submit-path ownership problem, not an API problem — bio_text was
submitted only by the ``photo`` action (whose only button is "Upload
photo"), never by the ``save`` action behind the page's primary "Save
Person" button. The ``photo`` action's own bio PATCH was also unchecked
and its rejection discarded, and the Biography textarea's stored value
was rendered as child text content, so the browser's dirty-value flag
kept the typed string on screen after reload — masking the silent loss.

No frontend test harness exists in app/package.json (39-RESEARCH.md
§Validation Architecture), and this WSL session cannot reach the real
dev database, so this whole module is a pure static source-contract
check — no database, no `_db_configured` gate, no `node` subprocess.
Follows test_phase38_people_ui_contract.py's `ROOT` + `_source(path)`
shape exactly.
"""

from pathlib import Path

ROOT = Path(__file__).parents[2]
ID_PAGE_SERVER_PATH = ROOT / "app" / "src" / "routes" / "admin" / "people" / "[id]" / "+page.server.ts"
ID_PAGE_SVELTE_PATH = ROOT / "app" / "src" / "routes" / "admin" / "people" / "[id]" / "+page.svelte"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _save_action_slice(source: str) -> str:
    """The `save` action's source text, from `save: async` up to `photo: async`."""
    start = source.index("save: async")
    end = source.index("photo: async")
    return source[start:end]


def _photo_action_slice(source: str) -> str:
    """The `photo` action's source text, from `photo: async` up to `merge: async`."""
    start = source.index("photo: async")
    end = source.index("merge: async")
    return source[start:end]


# ─────────────────────────────────────────────────────────────────────────────
# Task 1 — bio_text moves onto the Save Person path, end to end.
# ─────────────────────────────────────────────────────────────────────────────


def test_bio_textarea_is_associated_with_save_form():
    """The bio <textarea> carries name="bio_text" and form="save-form" on the
    same opening tag, so it submits into the save action's FormData even
    though the Biography card sits outside <form id="save-form">."""
    svelte_source = _source(ID_PAGE_SVELTE_PATH)
    bio_text_idx = svelte_source.index('name="bio_text"')
    tag_start = svelte_source.rindex("<textarea", 0, bio_text_idx)
    tag_end = svelte_source.index(">", bio_text_idx)
    textarea_tag = svelte_source[tag_start:tag_end]
    assert 'name="bio_text"' in textarea_tag
    assert 'form="save-form"' in textarea_tag


def test_biography_card_sits_outside_the_photo_form():
    """The Biography card (its bio_text field) sits after the photo form's
    closing </form>, not inside it — a sibling, not a child."""
    svelte_source = _source(ID_PAGE_SVELTE_PATH)
    photo_form_idx = svelte_source.index('action="?/photo"')
    first_close_after_photo_form = svelte_source.index("</form>", photo_form_idx)
    bio_text_idx = svelte_source.index('name="bio_text"')
    assert bio_text_idx > first_close_after_photo_form


def test_save_action_forwards_the_bio():
    """The save action reads bio_text and presence-checks it before use."""
    server_source = _source(ID_PAGE_SERVER_PATH)
    save_slice = _save_action_slice(server_source)
    assert "bio_text" in save_slice
    assert "formData.has('bio_text')" in save_slice or "formData.has(\"bio_text\")" in save_slice


def test_save_action_bio_is_a_conditional_spread():
    """The save action's PATCH body places bio_text with a conditional
    spread, not an unconditional property — an absent field must never
    reach the request body as a present (and therefore blanking) key."""
    server_source = _source(ID_PAGE_SERVER_PATH)
    save_slice = _save_action_slice(server_source)
    assert "...(" in save_slice
    assert "bio_text" in save_slice.split("body: JSON.stringify({", 1)[-1].split("}),", 1)[0]


def test_photo_action_performs_no_person_patch():
    """The photo action no longer PATCHes the person at all — no request,
    no discarded rejection."""
    server_source = _source(ID_PAGE_SERVER_PATH)
    photo_slice = _photo_action_slice(server_source)
    assert "'PATCH'" not in photo_slice
    assert ".catch(" not in photo_slice


def test_photo_action_still_uploads_photos():
    """The photo action still forwards photo_file/photo_url to /photo."""
    server_source = _source(ID_PAGE_SERVER_PATH)
    photo_slice = _photo_action_slice(server_source)
    assert "photo_file" in photo_slice
    assert "photo_url" in photo_slice
    assert "/photo" in photo_slice


def test_no_stale_bio_ownership_language_in_server_file():
    """The comments asserting the old (wrong) bio ownership are gone."""
    server_source = _source(ID_PAGE_SERVER_PATH)
    assert "bio_text intentionally omitted" not in server_source
    assert "bio_text omitted intentionally" not in server_source
    assert "Pitfall 7 extended" not in server_source
