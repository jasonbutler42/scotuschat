# API Coverage — Phase 38 (full-name-vs-name-parts-rethink)

No external API integration: this phase is a UI/data-model rethink of the Person
name fields (Full Name vs. name-part fields) — a shared internal domain module
(`api.domain.person_names`), an Alembic migration, existing FastAPI/SvelteKit
admin routes, and pipeline import writers. It integrates no third-party
service, SDK, or external API surface. The detector's "surface"/"api" signal is
a false positive on internal phrasing (e.g. "surfaces via the shared API
enforcement", referring to this project's own first-party FastAPI backend, not
an external vendor).
