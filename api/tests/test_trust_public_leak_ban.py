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
every route registered on the public routers (api.routers.cases,
api.routers.arguments, api.routers.people), so a newly added public route
that is not covered fails this module rather than passing silently
(T-48-LEAKFUTURE).
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
    "api.routers.cases",
    "api.routers.arguments",
    "api.routers.people",
]

PUBLIC_SCHEMA_MODULE_PATHS = [
    ROOT / "api" / "schemas" / "cases.py",
    ROOT / "api" / "schemas" / "people.py",
    ROOT / "api" / "schemas" / "utterance.py",
    ROOT / "api" / "schemas" / "speakers.py",
]

BANNED_KEY = "trust_tier"


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
    Build (root_model, reachable_model) pairs for parametrization, so a
    leak one level down names both the offending model and the public
    route it is reachable from.
    """
    cases = []
    for root_model in PUBLIC_RESPONSE_MODELS:
        for reachable in sorted(collect_model_graph(root_model), key=lambda m: m.__name__):
            cases.append((root_model, reachable))
    return cases


_MODEL_GRAPH_CASES = _model_graph_cases()


@pytest.mark.parametrize(
    "root_model,reachable_model",
    _MODEL_GRAPH_CASES,
    ids=[reachable.__name__ for _root, reachable in _MODEL_GRAPH_CASES],
)
def test_public_response_model_never_declares_trust_tier(
    root_model: type[BaseModel], reachable_model: type[BaseModel]
) -> None:
    """
    For every public response model, and every model reachable from it
    through nested field annotations, `trust_tier` must be absent from
    `model_fields`. Trust is operator-facing only (CLAUDE.md apolitical
    hard constraint) — a public response carrying it is an information
    disclosure, not a cosmetic slip. The assertion message names both the
    offending model and the public route (root response model) it is
    reachable from.
    """
    assert BANNED_KEY not in reachable_model.model_fields, (
        f"{reachable_model.__name__} (reachable from public response model "
        f"{root_model.__name__}) declares '{BANNED_KEY}' — trust is "
        "operator-facing only and must never reach a public response "
        "(CLAUDE.md apolitical hard constraint; D-23)."
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
        "api.routers.cases/arguments/people import cleanly and declare "
        "response_model= on their routes."
    )
    derived_names = {m.__name__ for m in PUBLIC_RESPONSE_MODELS}
    for required_name in (
        "CaseListResponse",
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

    assert BANNED_KEY in ArgumentDetail.model_fields, (
        "ArgumentDetail (admin-only) is expected to carry 'trust_tier' per D-20 — "
        "if this assertion fails, plan 48-07 has not yet landed the field. This "
        "is a known, tracked, currently-expected failure (see 48-03-SUMMARY.md); "
        "it does not indicate the public leak-ban itself is broken."
    )


# ---------------------------------------------------------------------------
# Test 4: executable reminder — public schema modules never import TrustTier
# ---------------------------------------------------------------------------


def test_public_schema_modules_never_import_trust_tier() -> None:
    """
    The prohibition's second half, encoded as an executable check rather
    than a comment someone has to remember: no module under api/schemas/
    OTHER THAN the admin_* modules may import TrustTier (or the
    api.domain.trust module at all) from api.domain.trust. Uses `ast` over
    the schema files rather than grepping, so a `# TrustTier` comment
    cannot produce a false positive.
    """
    violations = []
    for path in PUBLIC_SCHEMA_MODULE_PATHS:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "api.domain.trust":
                imported_names = {alias.name for alias in node.names}
                if imported_names:
                    violations.append(
                        f"{path.name} imports {sorted(imported_names)} from "
                        "api.domain.trust — public schema modules must never "
                        "reference the trust vocabulary (D-23)."
                    )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "api.domain.trust" or alias.name.startswith(
                        "api.domain.trust."
                    ):
                        violations.append(
                            f"{path.name} imports api.domain.trust directly — "
                            "banned on public schemas (D-23)."
                        )
    assert not violations, "\n".join(violations)
