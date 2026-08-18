# API Coverage — Phase 47: Provenance Foundation

No external API integration: this phase changes the PostgreSQL schema and the
internal write/read paths only — a new `import_run` table (Alembic migration
0026), provenance stamping in the corpus and PDF-pipeline writers, and the
project's own FastAPI read layer plus its Pydantic schemas. No external API,
SDK, or third-party service surface is added or widened. The `verify:pre`
detector fired on the prose phrase "API read layer" referring to this project's
own internal FastAPI, not an external provider. The one external SDK in the
neighbourhood (Anthropic, via `parse_with_llm`) is not integrated here — it is
monkeypatched out in every test leg, and `grep -c anthropic
pipeline/tests/test_import_run_provenance.py` returns 0 (see 47-02-SUMMARY.md).
