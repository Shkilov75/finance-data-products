---
status: Accepted
owner: "maksym.shkilov@gmail.com"
reviewers: []
updated_at: "2026-11-04"
feature_size: "n/a (repo foundation)"
ticket: ""
---

# 0001 — Use Python 3.12 with DuckDB executing SQL files

- **Status:** Accepted
- **Date:** 2026-11-04
- **Deciders:** Owner + Architect (survey session)

## Context

The repo is a portfolio of finance data products with built-in quality gates, synthetic data, and a hard requirement of a one-command run without accounts (idea-brief §2). A second path must run on Databricks, which the hiring side uses. About 10 hours of budget, one week.

## Decision drivers

- One-command local run with no accounts or servers (idea-brief §2).
- Transformation logic must be reusable on Databricks without a rewrite (idea-brief §7).
- A reader without the author must understand the repo from the code and README (idea-brief §2).
- Tight time budget (idea-brief §4, §6).

## Considered options

1. **Python + DuckDB + SQL files** — Python orchestrates, DuckDB executes the SQL models, gates are checks over tables.
2. **dbt + DuckDB (dbt-databricks for the second path)** — models and tests in dbt; one project for both engines.
3. **PySpark locally + Delta** — closest to Databricks code, needs Java and Spark.

## Decision outcome

**Chosen:** Option 1. DuckDB installs through pip and needs no accounts, SQL files are portable to Spark SQL, and the Python runner keeps the gates visible and easy to extend (cycle detection, Mermaid output). It is the fastest to build within the budget.

## Consequences

**Positive**
- `make setup && make run` works on any machine with Python 3.12.
- The SQL is readable by a finance reader and by a Databricks engineer.

**Negative**
- No dbt lineage or docs for free; the reader sees a custom runner instead of a known tool.
- Dialect differences between DuckDB and Spark SQL must be kept out of product SQL by discipline.

**Neutral**
- Moving to dbt later is possible: the SQL files and the gate queries port over.

## Links

- Brief: [[../idea-brief.md]] §2, §7
- Map: [[../architecture-map.md]] Stack
- Related ADR: [[0004-share-sql-across-local-and-databricks]]
