"""
Structural leak-ban contract: trust must never surface on any public response.

Phase 48 (D-23) turns the apolitical hard constraint — "trust is
operator-facing only; the public site sees published-or-not and nothing
more" (CLAUDE.md; .planning/notes/provenance-and-trust-model.md principle
3) — into an asserted, permanent, non-negotiable gate rather than a
convention someone has to remember. Every public Pydantic response model,
and every model reachable from one through nested field annotations, is
proven here to never declare a `trust_tier` field. A single `model_config`
change or a copy-pasted admin field would otherwise breach the constraint
silently.

Pure module: no DB, no fixtures, no skip markers — modeled on
api/tests/test_phase45_popover_boxmodel_contract.py's static-contract
shape. The model set under test is DERIVED from the `response_model=` of
every route registered on the public routers (api.routers.arguments,
api.routers.people), so a newly added public route that is not covered
fails this module rather than passing silently (T-48-LEAKFUTURE).

Phase 51 (plan 51-04): the term-grouped public listing models
(`api/schemas/arguments.py` — `TermSummary`, `TermIndexResponse`,
`ArgumentListItem`, `TermArgumentsResponse`) joined the covered set. No new
banned key was needed — the new models expose identification fields only
(term year, case name, docket, date, a published-record count).

Phase 51 (plan 51-08): the flat-listing cases router and its schema
module retired — their last consumer (the transitional `/arguments` flat
listing plan 51-02 shipped) was replaced by the term-grouped listing
above. The old list-response model is gone;
`test_public_model_derivation_is_non_empty`'s required-name check now
names `TermIndexResponse` instead. `PUBLIC_FRONTEND_PATHS` below points
at this phase's surviving public routes rather than the six deleted
files under the retired cases route directory.

Phase 53 (plan 53-04, D-07/PLUMBING-07): `PUBLIC_FRONTEND_PATHS` gains
five `app/src/lib/public/` component files — `UndeterminedBubble.svelte`
and `UndeterminedSpeakerCard.svelte` (new, Treatment D and its D-14
explanation card) plus `ChatBubble.svelte`, `StageDirection.svelte` and
`SpeakerPopover.svelte` (modified by this phase's earlier plans, and
never previously registered here — this module's frontend coverage had
only ever tracked route/page files and `TermRow.svelte`, not every
component under `app/src/lib/public/`). Two new tests close a real gap
the two path-based sweeps above shared: both `continue` silently past a
missing path, so a typo in `PUBLIC_FRONTEND_PATHS` would have passed
every sweep vacuously. `test_public_frontend_paths_all_exist` fails
loudly on exactly that condition, and
`test_public_frontend_pages_never_reference_trust_vocabulary` is the
Testing Policy's one permitted static-source-text exception — a
case-insensitive structural sweep proving `trust_tier`/`review_state`/
`provisional` reach no registered public file, which absence across a
computed file set can legitimately prove.
"""

from __future__ import annotations

import ast
import importlib
import typing
from pathlib import Path

import pytest
from pydantic import BaseModel

ROOT = Path(__file__).parents[2]

PUBLIC_ROUTER_MODULE_NAMES = [
    "api.routers.arguments",
    "api.routers.people",
]

PUBLIC_SCHEMA_MODULE_PATHS = [
    ROOT / "api" / "schemas" / "people.py",
    ROOT / "api" / "schemas" / "utterance.py",
    ROOT / "api" / "schemas" / "speakers.py",
    # Phase 51 plan 51-04: term-grouped public listing models.
    ROOT / "api" / "schemas" / "arguments.py",
]

# D-34 (plan 49-04): the ban widens from a single key to the whole Phase 49
# review-model vocabulary — trust tier, review state, provenance, and every
# value_discrepancy field name. A public response must never carry any of
# these; review state records an internal transcription-attribution
# workflow, never a public credibility judgment about a speaker.
#
# Phase 50 (plan 50-07, Task 2): widened again for this phase's own new
# vocabulary. "source"/"method" already banned every field literally named
# `source`/`method` — this widening is about PROVING that generic ban also
# covers the phase's new Argument.source/Argument.method/Case.source/
# Case.method columns specifically (they share the exact same field names
# as the Phase 49 ArgumentParticipant columns the ban was originally
# written for, so no NEW key is required for them — see
# test_argument_and_case_level_source_and_method_columns_exist_at_the_orm_layer
# below for the explicit non-vacuity proof). `content_digest` (ImportRun,
# D-13) and `oyez_speaker_id` (ArgumentParticipant/Person, D-04) are
# genuinely new keys. `argument_discrepancies` (ReviewQueueArgumentItem,
# plan 50-04) is the argument-scoped sibling of the constituent-scoped
# `discrepancies` field the value_discrepancy-field bans above already
# protect transitively (DiscrepancyDetail is reachable through it) — but
# the LIST field name itself must also never appear on a public model, so
# it is banned directly here too.
BANNED_KEYS = (
    "trust_tier",
    "review_state",
    "source",
    "method",
    "incoming_value",
    "existing_value",
    "resolved_at",
    "content_digest",
    "oyez_speaker_id",
    "argument_discrepancies",
)

# Phase 50 (plan 50-05/PD-17): the five reconcile-pass batch counters plus
# arguments_reconciled — operator-facing stdout only (D-29), never a
# public response field or a public page's rendered/referenced text.
BANNED_COUNTER_NAMES = (
    "arguments_reconciled",
    "arguments_unchanged",
    "values_accepted",
    "values_rejected",
    "discrepancies_recorded",
    "utterance_sets_replaced",
)

# The genuinely public (non-admin) SvelteKit route files — every page and
# server load function a public visitor's browser ever reaches. Mirrors
# PUBLIC_SCHEMA_MODULE_PATHS's convention of an explicit, reviewable list
# rather than a directory glob, so a new admin route added under
# app/src/routes/admin/ is never accidentally swept in.
PUBLIC_FRONTEND_PATHS = [
    ROOT / "app" / "src" / "routes" / "+layout.svelte",
    ROOT / "app" / "src" / "routes" / "attributions" / "+page.svelte",
    # Phase 51 plan 51-08: the six deleted routes-cases-family entries this
    # list used to carry are replaced by this phase's surviving public
    # surfaces (D-10/D-14 term-grouped listing + slug transcript route).
    ROOT / "app" / "src" / "routes/arguments/+page.svelte",
    ROOT / "app" / "src" / "routes/arguments/+page.server.ts",
    ROOT / "app" / "src" / "routes/arguments/term/[year]/+page.svelte",
    ROOT / "app" / "src" / "routes/arguments/term/[year]/+page.server.ts",
    ROOT / "app" / "src" / "routes/arguments/[slug]/+page.svelte",
    ROOT / "app" / "src" / "routes/arguments/[slug]/+page.server.ts",
    ROOT / "app" / "src" / "lib/public/TermRow.svelte",
    # Phase 53 (plan 53-04, D-07): the five public components this phase
    # added or touched for Treatment D and the D-14 explanation card. Two
    # are new (UndeterminedBubble.svelte, UndeterminedSpeakerCard.svelte);
    # three were modified by this phase's earlier plans (ChatBubble,
    # StageDirection, SpeakerPopover) and had never previously been
    # registered here — this module's coverage predates Phase 53 and only
    # tracked route/page files and TermRow.svelte, not every component
    # under app/src/lib/public/.
    ROOT / "app" / "src" / "lib/public/UndeterminedBubble.svelte",
    ROOT / "app" / "src" / "lib/public/UndeterminedSpeakerCard.svelte",
    ROOT / "app" / "src" / "lib/public/ChatBubble.svelte",
    ROOT / "app" / "src" / "lib/public/StageDirection.svelte",
    ROOT / "app" / "src" / "lib/public/SpeakerPopover.svelte",
]

# Phase 53 (plan 53-04, D-07): the trust vocabulary a public frontend file
# may never reference, case-insensitively. Distinct from BANNED_KEYS above
# (a Pydantic model_fields check) — this is a structural sweep of raw file
# text, the Testing Policy's one permitted "absence across a computed file
# set" exception (CLAUDE.md Testing Policy).
BANNED_TRUST_VOCABULARY_CASE_INSENSITIVE = ("trust_tier", "review_state", "provisional")


def _unwrap_annotation_types(annotation):
    """
    Yield every candidate type reachable from a type annotation, unwrapping
    list / dict / tuple / set / Optional / Union generics recursively.

    `list[CaseItem]` -> yields CaseItem. `Optional[str]` -> yields str.
    `SpeakerPopoverEntry` -> yields SpeakerPopoverEntry (no origin).
    """
    if annotation is None:
        return
    origin = typing.get_origin(annotation)
    if origin is None:
        yield annotation
        return
    args = typing.get_args(annotation)
    for arg in args:
        if arg is type(None):
            continue
        yield from _unwrap_annotation_types(arg)


def collect_model_graph(
    model: type[BaseModel], _seen: set[type[BaseModel]] | None = None
) -> set[type[BaseModel]]:
    """
    Return `model` plus every BaseModel subclass reachable through its
    field annotations, recursively, guarding against cycles with a
    seen-set so a self-referential or mutually-referential schema cannot
    cause infinite recursion.
    """
    if _seen is None:
        _seen = set()
    if model in _seen:
        return set()
    _seen.add(model)

    result = {model}
    for field in model.model_fields.values():
        for candidate in _unwrap_annotation_types(field.annotation):
            if isinstance(candidate, type) and issubclass(candidate, BaseModel):
                result |= collect_model_graph(candidate, _seen)
    return result


def _load_public_routers():
    return [importlib.import_module(name) for name in PUBLIC_ROUTER_MODULE_NAMES]


def _derive_public_response_models() -> set[type[BaseModel]]:
    """
    Walk every route on every public router and collect the concrete
    BaseModel subclass(es) named by its `response_model=`, unwrapping
    `list[...]` / `Optional[...]` generics to reach the concrete model.

    This is the authoritative "what does 'public' mean" derivation — it
    reads the live routers rather than a hardcoded list, so an uncovered
    new public route fails test_public_model_derivation_is_non_empty or
    silently expands the parametrized set (never shrinks unnoticed).
    """
    models: set[type[BaseModel]] = set()
    for module in _load_public_routers():
        router = module.router
        for route in router.routes:
            response_model = getattr(route, "response_model", None)
            if response_model is None:
                continue
            for candidate in _unwrap_annotation_types(response_model):
                if isinstance(candidate, type) and issubclass(candidate, BaseModel):
                    models.add(candidate)
    return models


PUBLIC_RESPONSE_MODELS: list[type[BaseModel]] = sorted(
    _derive_public_response_models(), key=lambda m: m.__name__
)


# ---------------------------------------------------------------------------
# Test 1: the structural ban, parametrized over every derived public model
# ---------------------------------------------------------------------------


def _model_graph_cases():
    """
    Build (root_model, reachable_model, banned_key) triples for
    parametrization — one case per banned key per reachable model — so a
    leak one level down names both the offending model, the public route
    it is reachable from, and the specific banned key.
    """
    cases = []
    for root_model in PUBLIC_RESPONSE_MODELS:
        for reachable in sorted(collect_model_graph(root_model), key=lambda m: m.__name__):
            for banned_key in BANNED_KEYS:
                cases.append((root_model, reachable, banned_key))
    return cases


_MODEL_GRAPH_CASES = _model_graph_cases()


@pytest.mark.parametrize(
    "root_model,reachable_model,banned_key",
    _MODEL_GRAPH_CASES,
    ids=[
        f"{reachable.__name__}-{banned_key}"
        for _root, reachable, banned_key in _MODEL_GRAPH_CASES
    ],
)
def test_public_response_model_never_declares_trust_tier(
    root_model: type[BaseModel], reachable_model: type[BaseModel], banned_key: str
) -> None:
    """
    For every public response model, and every model reachable from it
    through nested field annotations, none of BANNED_KEYS may be present
    in `model_fields`. Trust and review-state are operator-facing only
    (CLAUDE.md apolitical hard constraint; D-23/D-34) — a public response
    carrying any of them is an information disclosure, not a cosmetic
    slip. The assertion message names the offending model, the public
    route (root response model) it is reachable from, and the specific
    banned key.
    """
    assert banned_key not in reachable_model.model_fields, (
        f"{reachable_model.__name__} (reachable from public response model "
        f"{root_model.__name__}) declares '{banned_key}' — trust/review-state "
        "data is operator-facing only and must never reach a public response "
        "(CLAUDE.md apolitical hard constraint; D-23/D-34)."
    )


# ---------------------------------------------------------------------------
# Test 2: derivation guard — the model set must be non-empty and complete
# ---------------------------------------------------------------------------


def test_public_model_derivation_is_non_empty() -> None:
    """
    Guard against the derivation in _derive_public_response_models()
    silently returning nothing (which would make Test 1 vacuously pass on
    every future public route, defeating T-48-LEAKFUTURE's purpose).
    """
    assert PUBLIC_RESPONSE_MODELS, (
        "PUBLIC_RESPONSE_MODELS derivation returned an empty set — the "
        "structural leak-ban would pass vacuously. Check that "
        "api.routers.arguments/people import cleanly and declare "
        "response_model= on their routes."
    )
    derived_names = {m.__name__ for m in PUBLIC_RESPONSE_MODELS}
    for required_name in (
        "TermIndexResponse",
        "TermArgumentsResponse",
        "ArgumentUtterancesResponse",
        "SpeakerPopoverEntry",
        "PersonResponse",
    ):
        assert required_name in derived_names, (
            f"{required_name} is expected to be derived from the public routers' "
            f"response_model= declarations but was not found. Derived set: "
            f"{sorted(derived_names)}"
        )


# ---------------------------------------------------------------------------
# Test 3: the false-green guard — the admin contract DOES carry the field
# ---------------------------------------------------------------------------


def test_admin_detail_contract_does_declare_trust_tier() -> None:
    """
    Proves Test 1 is a BAN, not an ABSENCE. If `trust_tier` did not exist
    anywhere in api/schemas/, Test 1 would pass for the wrong reason —
    there would be nothing to leak in the first place. `ArgumentDetail`
    (the admin-only detail contract) is D-20's designated carrier of
    `trust_tier`.

    NOTE for plan 48-03 executor / verifier: this test is expected to FAIL
    until plan 48-07 lands `trust_tier` on `ArgumentDetail` (D-20). Both
    plans ship in Phase 48; per 48-03-PLAN.md's explicit instruction this
    failure is left visible (not xfail'd) and recorded in
    48-03-SUMMARY.md. Re-run this module once 48-07 closes — it should
    turn green with no further changes needed here.
    """
    from api.schemas.admin_arguments import ArgumentDetail
    from api.schemas.admin_review import ReviewQueueConstituent

    assert "trust_tier" in ArgumentDetail.model_fields, (
        "ArgumentDetail (admin-only) is expected to carry 'trust_tier' per D-20 — "
        "if this assertion fails, plan 48-07 has not yet landed the field. This "
        "is a known, tracked, currently-expected failure (see 48-03-SUMMARY.md); "
        "it does not indicate the public leak-ban itself is broken."
    )
    # D-34 (plan 49-04): the same false-green guard for the widened
    # vocabulary — ReviewQueueConstituent (admin-only) is expected to carry
    # 'review_state'. If it did not, Test 1's review_state cases would pass
    # for the wrong reason (nothing to leak in the first place).
    assert "review_state" in ReviewQueueConstituent.model_fields, (
        "ReviewQueueConstituent (admin-only) is expected to carry "
        "'review_state' — if this assertion fails, the D-34 leak-ban "
        "extension is vacuous for that key."
    )


def test_review_queue_argument_item_does_declare_argument_discrepancies() -> None:
    """
    Phase 50 (plan 50-07) false-green guard for `argument_discrepancies`:
    `ReviewQueueArgumentItem` (admin-only, plan 50-04) is the designated
    carrier. If it did not declare this field, Test 1's
    `argument_discrepancies` cases would pass for the wrong reason —
    nothing to leak in the first place.
    """
    from api.schemas.admin_review import ReviewQueueArgumentItem

    assert "argument_discrepancies" in ReviewQueueArgumentItem.model_fields, (
        "ReviewQueueArgumentItem (admin-only) is expected to carry "
        "'argument_discrepancies' per plan 50-04 — if this assertion fails, "
        "the Phase 50 leak-ban extension is vacuous for that key."
    )


def test_argument_and_case_level_source_and_method_columns_exist_at_the_orm_layer() -> None:
    """
    Phase 50's Argument.source/Argument.method/Case.source/Case.method
    columns (migration 0030) are not yet exposed on ANY Pydantic schema,
    admin or public — grep across api/schemas/ confirms this at authoring
    time. The generic 'source'/'method' bans in BANNED_KEYS (D-34) already
    cover them by field-name match the moment any schema ever adds them,
    so no NEW banned key is needed — but this test proves those columns
    are real, named vocabulary at the ORM layer (not a typo that would
    make the ban meaningless), matching this module's own established
    "prove it's a ban, not an absence" discipline.
    """
    from api.models.models import Argument, Case

    assert "source" in Argument.__table__.columns
    assert "method" in Argument.__table__.columns
    assert "source" in Case.__table__.columns
    assert "method" in Case.__table__.columns


def test_content_digest_and_oyez_speaker_id_exist_at_the_orm_layer_not_yet_any_schema() -> None:
    """
    `content_digest` (ImportRun, D-13) and `oyez_speaker_id`
    (ArgumentParticipant/Person, D-04) are Phase 50 columns that exist
    ONLY at the SQLAlchemy ORM layer as of this plan — no Pydantic schema,
    admin or public, exposes either one yet (grep across api/schemas/
    confirms this at authoring time). The usual "assert the ADMIN schema
    DOES carry it" false-green guard is therefore not honestly
    satisfiable for these two keys: there is nothing admin-facing to
    point at, and fabricating one just to satisfy this test would be
    scope creep no plan asked for.

    This test proves the next-best non-vacuity fact instead: the columns
    are real, named Phase 50 vocabulary at the ORM layer, not typo'd
    strings banning nothing. Test 1's coverage of these two keys is
    therefore currently, correctly, VACUOUS for every existing public
    model (no schema anywhere carries them to leak) — documented here
    explicitly rather than silently — while remaining a real, permanent
    ban: the moment either column is ever surfaced through a NEW admin
    schema, Test 1 already covers it with no further edit to this module.
    """
    from api.models.models import ArgumentParticipant, ImportRun, Person

    assert "content_digest" in ImportRun.__table__.columns
    assert "oyez_speaker_id" in ArgumentParticipant.__table__.columns
    assert "oyez_speaker_id" in Person.__table__.columns


def test_banned_keys_include_phase_50_vocabulary() -> None:
    """
    Direct membership check on the ban list itself: shrinking BANNED_KEYS
    to drop any of this phase's new vocabulary fails this test
    immediately, independent of which (if any) public model happens to
    declare the field today.
    """
    for key in ("content_digest", "oyez_speaker_id", "argument_discrepancies"):
        assert key in BANNED_KEYS, (
            f"{key!r} was removed from BANNED_KEYS — Phase 50's leak-ban "
            "extension (plan 50-07) requires this key to stay banned."
        )


# ---------------------------------------------------------------------------
# Test: reconcile batch counters (PD-17) are operator-facing stdout only
# ---------------------------------------------------------------------------


def test_public_response_models_never_declare_reconcile_counter_names() -> None:
    """
    None of PD-17's five reconcile-pass batch counters (plus
    arguments_reconciled) may ever be a field name on a public response
    model or anything reachable from one — they are operator-facing
    stdout only (D-29), never persisted to a row a public route could
    serialize.
    """
    for root_model in PUBLIC_RESPONSE_MODELS:
        for reachable in collect_model_graph(root_model):
            for counter_name in BANNED_COUNTER_NAMES:
                assert counter_name not in reachable.model_fields, (
                    f"{reachable.__name__} (reachable from public response "
                    f"model {root_model.__name__}) declares '{counter_name}' "
                    "— reconcile batch counters are operator-facing stdout "
                    "only (D-29) and must never reach a public response."
                )


def test_public_frontend_pages_never_reference_reconcile_counter_names() -> None:
    """
    No genuinely public (non-admin) SvelteKit page or server load function
    references any of PD-17's batch counter names — they are printed to
    the operator's own terminal by the pipeline CLI (D-29), never wired
    into a public page's data or markup.
    """
    violations = []
    for path in PUBLIC_FRONTEND_PATHS:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for counter_name in BANNED_COUNTER_NAMES:
            if counter_name in text:
                violations.append(
                    f"{path.name} references reconcile batch counter "
                    f"'{counter_name}' — batch counters are operator-facing "
                    "stdout only (D-29) and must never reach a public page."
                )
    assert not violations, "\n".join(violations)


def test_public_frontend_pages_never_use_public_fastapi_base_url() -> None:
    """
    No genuinely public (non-admin) SvelteKit server load file imports
    `PUBLIC_FASTAPI_BASE_URL` — `FASTAPI_BASE_URL` must always come from
    `$env/static/private`, never a `PUBLIC_`-prefixed env var (CLAUDE.md
    hard constraint), which would ship the FastAPI base URL into the
    client bundle.

    Migrated from the retired tests/test_cases_api.py's
    test_no_public_fastapi_base_url_in_cases_pages (Phase 51 plan 51-08) —
    that test scoped narrowly to the retired cases route directory under
    app/src/routes, which plan 51-02 already deleted. Retargeted onto
    PUBLIC_FRONTEND_PATHS, the same reviewable file list the two tests
    above already sweep, rather than a
    fresh directory glob.
    """
    violations = []
    for path in PUBLIC_FRONTEND_PATHS:
        if path.suffix != ".ts" or not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "PUBLIC_FASTAPI_BASE_URL" in text:
            violations.append(
                f"{path.name} references 'PUBLIC_FASTAPI_BASE_URL' — "
                "FASTAPI_BASE_URL must be imported from $env/static/private "
                "only (CLAUDE.md hard constraint)."
            )
    assert not violations, "\n".join(violations)


# ---------------------------------------------------------------------------
# Phase 53 (plan 53-04, D-07): every registered path exists, and no
# registered public file carries trust vocabulary
# ---------------------------------------------------------------------------


def test_public_frontend_paths_all_exist() -> None:
    """
    Every path in PUBLIC_FRONTEND_PATHS must exist on disk. The two sweeps
    above (`test_public_frontend_pages_never_reference_reconcile_counter_names`,
    `test_public_frontend_pages_never_use_public_fastapi_base_url`) both
    `continue` silently on a missing path — deliberately, so a renamed or
    deleted file doesn't fail an unrelated sweep — but that same silence
    means a TYPO'd path (e.g. a missing `[slug]` segment, or a misspelled
    filename) passes both sweeps VACUOUSLY: nothing was ever read, so
    nothing was ever found to violate. This test is the guard against that:
    it fails loudly on exactly the condition the other two sweeps must
    tolerate silently.
    """
    missing = [str(path) for path in PUBLIC_FRONTEND_PATHS if not path.exists()]
    assert not missing, (
        "PUBLIC_FRONTEND_PATHS lists a path that does not exist on disk — "
        f"a typo here makes every path-based sweep in this module vacuous "
        f"for that entry: {missing}"
    )


def test_public_frontend_pages_never_reference_trust_vocabulary() -> None:
    """
    D-07 / PLUMBING-07: no registered public frontend file may reference
    `trust_tier`, `review_state` or `provisional`, case-insensitively.
    Unlike the parametrized Pydantic-model sweep above (Test 1), this is a
    raw source-text sweep over a COMPUTED file set — the Testing Policy's
    one permitted exception to "no static source-text contract tests for
    frontend behavior" (CLAUDE.md), because proving an identifier's absence
    across a reviewable, explicit file list is exactly what source text
    can prove, unlike a rendered-page behavior claim.
    """
    violations = []
    for path in PUBLIC_FRONTEND_PATHS:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8").lower()
        for banned in BANNED_TRUST_VOCABULARY_CASE_INSENSITIVE:
            if banned in text:
                violations.append(
                    f"{path.name} references trust vocabulary '{banned}' — "
                    "PROVISIONAL/trust never reaches a public response or a "
                    "public frontend file (D-07/D-23)."
                )
    assert not violations, "\n".join(violations)


# ---------------------------------------------------------------------------
# Test 4: executable reminder — public schema modules never import TrustTier
# ---------------------------------------------------------------------------


# D-34 (plan 49-04): a public schema module must also never import the
# authority-ladder domain module or the admin_review schema module — both
# carry the review-model vocabulary this ban exists to keep off public
# responses.
_BANNED_IMPORT_MODULES = ("api.domain.trust", "api.domain.authority", "api.schemas.admin_review")


def test_public_schema_modules_never_import_trust_tier() -> None:
    """
    The prohibition's second half, encoded as an executable check rather
    than a comment someone has to remember: no module under api/schemas/
    OTHER THAN the admin_* modules may import from api.domain.trust,
    api.domain.authority, or api.schemas.admin_review. Uses `ast` over
    the schema files rather than grepping, so a `# TrustTier` comment
    cannot produce a false positive.
    """
    violations = []
    for path in PUBLIC_SCHEMA_MODULE_PATHS:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module in _BANNED_IMPORT_MODULES:
                imported_names = {alias.name for alias in node.names}
                if imported_names:
                    violations.append(
                        f"{path.name} imports {sorted(imported_names)} from "
                        f"{node.module} — public schema modules must never "
                        "reference the trust/review-model vocabulary (D-23/D-34)."
                    )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in _BANNED_IMPORT_MODULES or any(
                        alias.name.startswith(f"{banned}.") for banned in _BANNED_IMPORT_MODULES
                    ):
                        violations.append(
                            f"{path.name} imports {alias.name} directly — "
                            "banned on public schemas (D-23/D-34)."
                        )
    assert not violations, "\n".join(violations)
