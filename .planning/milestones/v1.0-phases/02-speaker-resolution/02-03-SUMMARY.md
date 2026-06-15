---
plan: 02-03
phase: 02-speaker-resolution
status: complete
completed_at: 2026-06-12
---

# Plan 02-03 Summary: GET /people/{id} API + utterances JOIN extension

## What was built

Three-layer GET /people/{id} endpoint: `api/schemas/people.py` (PersonResponse with id, full_name, role_name — no photo_url per D-11), `api/services/people.py` (get_person_by_id doing a LEFT JOIN to roles, returning dict), and `api/routers/people.py` (APIRouter prefix=/people, person_id: int annotation as T-03-01 SQL injection mitigation). The router was wired into `api/main.py` alongside the existing arguments router.

The utterances query in `api/services/arguments.py` was extended with LEFT JOINs to `people` and `roles` to embed `speaker_name` and `speaker_role` in every UtteranceResponse. `UtteranceResponse` in `api/schemas/utterance.py` gained two new `Optional[str] = None` fields. Dict assembly via `__table__.columns` introspection was used throughout (Pitfall 6 guard — `from_attributes=True` cannot pull labeled columns from SQLAlchemy Row tuples).

Wave 0 test stubs were created in `api/tests/test_people.py` (test_get_person, test_get_person_404) and `api/tests/test_arguments.py` (test_utterances_have_speaker_name_after_resolve), then replaced with real test implementations using the requires_db skipif pattern from test_arguments.py.

## Key decisions / deviations

- **Pitfall 6 (from_attributes on Row tuples):** After the JOIN query returns Row tuples, dicts are assembled explicitly with `{**{c.key: getattr(utterance, c.key) for c in utterance.__table__.columns}, "speaker_name": ..., "speaker_role": ...}` rather than relying on Pydantic's `from_attributes=True`. This is required because labeled columns from SQLAlchemy Row tuples are not accessible via attribute lookup on the ORM object.
- **No photo_url in PersonResponse:** D-11 defers this to Phase 3. The field is absent from `api/schemas/people.py`.
- **Pre-existing test failure:** `test_get_utterances_returns_404_for_unknown_argument` was already failing before this plan (RuntimeError from no DB bubbles up rather than returning 500). No regression introduced.

## Verification results

```
# Test collection
pytest api/tests/test_people.py --collect-only -q
→ 2 tests collected

# Stubs and implementations
pytest api/tests/test_people.py -v -q
→ 2 skipped (no DATABASE_URL — correct behavior in no-DB environment)

# Router prefix check
python -c "from api.routers.people import router; print('router prefix:', router.prefix)"
→ router prefix: /people

# Acceptance criterion checks
grep person_id: int api/routers/people.py → match (T-03-01 satisfied)
grep photo_url api/schemas/people.py → 0 matches (D-11 satisfied)
grep outerjoin(Person api/services/arguments.py → match (D-10 JOIN present)
grep __table__.columns api/services/arguments.py → match (Pitfall 6 guard present)
```

## Files modified

- `api/schemas/people.py` — created: PersonResponse with id, full_name, role_name
- `api/services/people.py` — created: get_person_by_id with LEFT JOIN to Role
- `api/routers/people.py` — created: GET /{person_id} with person_id: int annotation
- `api/main.py` — people_router import + app.include_router added
- `api/schemas/utterance.py` — speaker_name + speaker_role Optional[str] fields added
- `api/services/arguments.py` — Step 4 utterances query extended with Person/Role JOINs; dict assembly via __table__.columns
- `api/tests/test_people.py` — created with test_get_person + test_get_person_404 (requires_db skipif pattern)
- `api/tests/test_arguments.py` — test_utterances_have_speaker_name_after_resolve added (requires_db skipif pattern)
