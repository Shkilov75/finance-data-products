---
status: Accepted
owner: "maksym.shkilov@gmail.com"
reviewers: []
updated_at: "2026-11-04"
feature_size: "n/a (repo foundation)"
ticket: ""
---

# 0002 — Organize the repo as products/<name>/ folders plus a shared fdp_core

- **Status:** Accepted
- **Date:** 2026-11-04
- **Deciders:** Owner + Architect (survey session)

## Context

Four products are planned (Unified GL, Cost center model, Functional operating model, EPM); only the first is built fully now, and the roadmap must reserve space for all four from the start (idea-brief §1, §7). EPM depends on products 1-3.

## Decision drivers

- Roadmap steps map directly to folders a reader can see.
- Each product can be cut or finished independently (2 and 3 are cut first, idea-brief §6).
- Shared behaviour (gate runner, reporting, FX) must not be copied between products.

## Considered options

1. **`products/<name>/` plus `src/fdp_core/`** — each product self-contained (SQL, gates, data, README); shared engine in one package.
2. **Flat layered folders (`sql/`, `gates/`, `data/`)** — files separated by product prefix.
3. **Separate installable packages, one pyproject each** — strongest isolation.

## Decision outcome

**Chosen:** Option 1. The tree reads like the roadmap, a product can be dropped or finished without touching the others, and the shared engine lives in exactly one place. Option 3 is unnecessary ceremony for a one-week demo; Option 2 mixes four products in shared folders.

## Consequences

**Positive**
- Reserved products appear as placeholder folders with a status README, so the roadmap is visible in the tree.
- A new product copies the shape of `products/unified_gl/`.

**Negative**
- Placeholder folders for unbuilt products can look unfinished unless each states its status clearly.
- Products must communicate through published tables, not imports.

**Neutral**
- Splitting into separate packages later is a mechanical move.

## Links

- Brief: [[../idea-brief.md]] §1, §6, §7
- Map: [[../architecture-map.md]] Module inventory
- Related ADR: [[0001-use-python-duckdb-with-sql-files]]
