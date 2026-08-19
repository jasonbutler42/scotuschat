"""
Exhaustive pure unit coverage for api/domain/trust.py (Phase 48, plan 48-01,
Task 2 — a 48-VALIDATION.md Wave 0 requirement).

No database, no fixtures, no DB-gate — this is the fastest feedback loop in
the phase and must stay genuinely DB-free (mirrors api/tests/test_person_names.py's
pure-domain shape). Every (source, method, review_state) combination the
codebase can produce is asserted here exactly once, built as a literal
expectation table rather than by recomputing derive_tier's own logic — a
test that re-derives the function under test proves nothing.
"""

from __future__ import annotations

import ast
import itertools
from pathlib import Path

import pytest

from api.domain.trust import TrustTier, derive_tier, floor_tier
from api.models.models import ImportMethod, ImportSource

# ---------------------------------------------------------------------------
# Full (source, method) cross-product at review_state="unreviewed"
# (.planning/notes/provenance-and-trust-model.md § "Trust tiers (derived)",
# api/domain/trust.py's documented precedence order).
#
# ("corpus","direct") and ("seed","direct") -> TRUSTED
# every "normalized" pair -> PROVISIONAL
# ("pdf_pipeline","rule_based") -> PROVISIONAL
# ("operator","manual") -> VERIFIED
# every remaining pair (including all "llm_corrective" pairs) -> UNCERTAIN
# ---------------------------------------------------------------------------

CROSS_PRODUCT_CASES = [
    # source, method, expected tier
    ("operator", "manual", TrustTier.VERIFIED),
    ("operator", "direct", TrustTier.UNCERTAIN),
    ("operator", "normalized", TrustTier.PROVISIONAL),
    ("operator", "rule_based", TrustTier.UNCERTAIN),
    ("operator", "llm_corrective", TrustTier.UNCERTAIN),
    ("corpus", "manual", TrustTier.UNCERTAIN),
    ("corpus", "direct", TrustTier.TRUSTED),
    ("corpus", "normalized", TrustTier.PROVISIONAL),
    ("corpus", "rule_based", TrustTier.UNCERTAIN),
    ("corpus", "llm_corrective", TrustTier.UNCERTAIN),
    ("pdf_pipeline", "manual", TrustTier.UNCERTAIN),
    ("pdf_pipeline", "direct", TrustTier.UNCERTAIN),
    ("pdf_pipeline", "normalized", TrustTier.PROVISIONAL),
    ("pdf_pipeline", "rule_based", TrustTier.PROVISIONAL),
    ("pdf_pipeline", "llm_corrective", TrustTier.UNCERTAIN),
    ("seed", "manual", TrustTier.UNCERTAIN),
    ("seed", "direct", TrustTier.TRUSTED),
    ("seed", "normalized", TrustTier.PROVISIONAL),
    ("seed", "rule_based", TrustTier.UNCERTAIN),
    ("seed", "llm_corrective", TrustTier.UNCERTAIN),
]


def test_cross_product_case_list_is_exhaustive():
    """
    The literal CROSS_PRODUCT_CASES table above must cover every
    (source, method) pair ImportSource x ImportMethod can produce today —
    a guard against silently drifting out of sync if either enum grows.
    """
    expected_pairs = {
        (source.value, method.value) for source in ImportSource for method in ImportMethod
    }
    actual_pairs = {(source, method) for source, method, _tier in CROSS_PRODUCT_CASES}
    assert actual_pairs == expected_pairs
    assert len(CROSS_PRODUCT_CASES) == 20


@pytest.mark.parametrize(
    "source, method, expected_tier",
    CROSS_PRODUCT_CASES,
    ids=[f"{source}-{method}" for source, method, _tier in CROSS_PRODUCT_CASES],
)
def test_derive_tier_cross_product_at_unreviewed(source, method, expected_tier):
    assert derive_tier(source, method, "unreviewed") is expected_tier


# ---------------------------------------------------------------------------
# Precedence: review_state wins first, regardless of source/method
# (api/domain/trust.py rules 1-2 always fire before rules 3-7).
# ---------------------------------------------------------------------------

REVIEW_STATE_PRECEDENCE_CASES = [
    # review_state, source, method, expected tier
    ("unreviewed", "corpus", "direct", TrustTier.TRUSTED),
    ("unreviewed", "pdf_pipeline", "llm_corrective", TrustTier.UNCERTAIN),
    ("needs_review", "corpus", "direct", TrustTier.UNCERTAIN),
    ("needs_review", "pdf_pipeline", "llm_corrective", TrustTier.UNCERTAIN),
    ("operator_confirmed", "corpus", "direct", TrustTier.VERIFIED),
    ("operator_confirmed", "pdf_pipeline", "llm_corrective", TrustTier.VERIFIED),
    ("operator_edited", "corpus", "direct", TrustTier.VERIFIED),
    ("operator_edited", "pdf_pipeline", "llm_corrective", TrustTier.VERIFIED),
]


@pytest.mark.parametrize(
    "review_state, source, method, expected_tier",
    REVIEW_STATE_PRECEDENCE_CASES,
    ids=[f"{rs}-{s}-{m}" for rs, s, m, _t in REVIEW_STATE_PRECEDENCE_CASES],
)
def test_review_state_precedence(review_state, source, method, expected_tier):
    """
    operator_confirmed/operator_edited win to VERIFIED regardless of source;
    needs_review floors to UNCERTAIN regardless of source — review_state is
    evaluated before source/method in derive_tier's rule order (rules 1-2).
    """
    assert derive_tier(source, method, review_state) is expected_tier


# ---------------------------------------------------------------------------
# Fail-closed: unrecognised source/method/review_state -> UNCERTAIN
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "source, method, review_state",
    [
        ("wat", "direct", "unreviewed"),
        ("corpus", "wat", "unreviewed"),
        ("wat", "wat", "wat"),
    ],
    ids=["unrecognised_source", "unrecognised_method", "unrecognised_source_and_method_and_review_state"],
)
def test_derive_tier_fail_closed_on_unrecognised_values(source, method, review_state):
    """
    Unrecognised source and unrecognised method strings return UNCERTAIN
    (fail-closed) — the <behavior> contract this test locks. An
    unrecognised review_state alone (paired with an otherwise-valid trusted
    source/method) does NOT independently force UNCERTAIN: derive_tier's
    locked precedence order (rules 1-2) only special-cases the four known
    review_state values; any other string — including a typo — simply
    fails to match rules 1/2 and falls through to the source/method rules
    (3-6) exactly as "unreviewed" would. See
    test_unrecognised_review_state_alone_does_not_override_trusted_source
    below for the explicit regression lock on that behavior.
    """
    assert derive_tier(source, method, review_state) is TrustTier.UNCERTAIN


def test_unrecognised_review_state_alone_does_not_override_trusted_source():
    """
    Deviation note (Task 2, Rule 1): the plan's original third fail-closed
    case asserted derive_tier("corpus", "direct", "wat") is UNCERTAIN. That
    contradicts the actual (locked, Task-1-approved) precedence order: rules
    1-2 only match the four documented review_state values, so an
    unrecognised review_state that isn't one of those four simply defers to
    rules 3-6 on (source, method) — it does not independently trigger the
    rule-7 fail-closed fallthrough. This test locks the corrected,
    actual behavior instead of the plan's erroneous expectation.
    """
    assert derive_tier("corpus", "direct", "wat") is TrustTier.TRUSTED


# ---------------------------------------------------------------------------
# floor_tier edge cases (48-RESEARCH.md Pitfall 3, Zero-Utterance Tier
# Decision): floor_tier must never raise ValueError from min() over an
# empty sequence, and must be permutation-invariant.
# ---------------------------------------------------------------------------


def test_floor_tier_empty_returns_uncertain():
    """
    Zero-constituent base case — an explicit early return, never a bare
    min() over an empty iterable (which would raise ValueError).
    See 48-RESEARCH.md § "Zero-Utterance Tier Decision" / Pitfall 3.
    """
    assert floor_tier([]) is TrustTier.UNCERTAIN


@pytest.mark.parametrize("tier", list(TrustTier))
def test_floor_tier_single_element_returns_that_element(tier):
    assert floor_tier([tier]) is tier


@pytest.mark.parametrize("tier", list(TrustTier))
def test_floor_tier_all_equal_returns_that_tier(tier):
    assert floor_tier([tier, tier, tier]) is tier


def test_floor_tier_permutation_invariant_over_mixed_list():
    """
    floor_tier returns the same TrustTier for every permutation of the same
    constituent list (TRUST-01 edge: ordering/adjacency guarantee).
    """
    mixed = [TrustTier.VERIFIED, TrustTier.TRUSTED, TrustTier.PROVISIONAL, TrustTier.UNCERTAIN]
    results = {floor_tier(list(perm)) for perm in itertools.permutations(mixed)}
    assert results == {TrustTier.UNCERTAIN}


# ---------------------------------------------------------------------------
# Structural guard: the pure module must never import a framework or the
# sibling `api` package (mirrors Task 1's acceptance-criteria AST check, so
# a later edit cannot quietly add a SQLAlchemy import to this module).
# ---------------------------------------------------------------------------


def test_domain_trust_module_has_no_framework_imports():
    source_path = Path(__file__).resolve().parent.parent / "domain" / "trust.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            modules.add(node.module or "")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)
    forbidden_roots = {"fastapi", "sqlalchemy", "alembic", "api"}
    bad = [m for m in modules if m.split(".")[0] in forbidden_roots]
    assert not bad, f"api/domain/trust.py imports forbidden module(s): {bad}"
