---
status: Accepted
owner: "maksym.shkilov@gmail.com"
reviewers: []
updated_at: "2026-11-04"
feature_size: "n/a (repo foundation)"
ticket: ""
---

# 0004 — Share dialect-neutral SQL between the local and Databricks paths via a thin adapter

- **Status:** Accepted
- **Date:** 2026-11-04
- **Deciders:** Owner + Architect (survey session)

## Context

The owner chose to deliver both a local run and a separate Databricks path, against the interviewer's recommendation of local only (idea-brief §6, §7). Two independent implementations would double the work in a tight budget and could diverge.

## Decision drivers

- One source of truth for transformation and gate logic.
- A Databricks claim in the README must rest on a real run (idea-brief §6 risk 2).
- Time budget.

## Considered options

1. **Shared SQL plus a thin adapter** — product SQL lives in `products/<p>/sql/`, kept dialect-neutral; `databricks/` only submits it to Databricks.
2. **Separate PySpark implementation** — native-looking, independent of the local code.
3. **Placeholder only for the Databricks path** — folder and plan, implementation postponed.

## Decision outcome

**Chosen:** Option 1. One logic, two engines. If Databricks access cannot be confirmed, the adapter stays in place but the README makes no compatibility claim, which degrades to Option 3 without rework.

## Consequences

**Positive**
- Gate logic is written once and runs on both engines.
- The Databricks path can be cut without damaging the local path.

**Negative**
- Product SQL cannot use engine-specific functions; a needed difference must go into the adapter.
- Unverified until a real Databricks run happens.

**Neutral**
- Hiring-side tooling (Power BI) is not covered by this decision.

## Links

- Brief: [[../idea-brief.md]] §6, §7
- Map: [[../architecture-map.md]] Stack, Constraints
- Related ADR: [[0001-use-python-duckdb-with-sql-files]]
