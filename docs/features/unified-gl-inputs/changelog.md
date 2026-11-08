# Changelog — unified-gl-inputs

## unified-gl-inputs — two ERP exports aligned into one ledger, with completeness and mapping gates

**What:** `make run` now loads two synthetic ERP exports in different formats and currencies (ERP A: German CSV; ERP B: nested JSON; EUR, GBP, USD) through `raw` and `staging` into one set of aligned entries: same attribute names, English descriptions, real dates, numeric amounts, one signed amount, a deterministic entry identifier and a group account. The run prints entries and debit/credit totals per source system and currency, the size of the exceptions report (`exceptions_report.csv`, descriptions without a translation), and the result of two gates: completeness (an independent raw-side reading must match the aligned entries) and account mapping. The other three products are listed as reserved. The generator, account mapping, translation list and rate file are committed and reproducible from a fixed seed.

**Why:** Step 2 of the [roadmap](../../roadmap.md): the first half of the Unified GL product, so that step 3 (USD conversion and ledger) starts from trustworthy aligned entries. See [spec](spec.md) §1/§2. Key decisions: [ADR-0001](adr/0001-expose-typed-flat-views-from-per-engine-adapters.md) typed flat views from per-engine adapters, [ADR-0002](adr/0002-compute-completeness-controls-on-an-independent-path.md) completeness controls on an independent path, [ADR-0003](adr/0003-stop-the-run-on-sql-invariant-checks-declared-in-the-manifest.md) invariant checks stop the run, [ADR-0004](adr/0004-let-products-declare-report-queries-that-the-core-renders.md) report queries declared by the product, [ADR-0005](adr/0005-store-the-nested-erp-export-as-a-json-array-of-documents.md) nested ERP B export kept as a JSON array.

**How to use:**

```
make setup && make run     # exit 0: both gates pass; exit 1: a gate failed; exit 2: invariant violation; exit 3: export error
```

Exit codes, output and manifest keys: [contracts/cli.md](contracts/cli.md). Aligned entry attributes: [data-model.md](data-model.md).

**Operational notes:**
- Migration: <!-- none --> The repo has no migration tool ([ADR-0003 of the repo](../../adr/0003-rebuild-layered-duckdb-no-migration-tool.md)); `build/fdp.duckdb` is rebuilt from scratch on every run. The staged DDL in `data-model.md` is design DDL already moved into the product's SQL and adapter folders.
- Feature flag / config: <!-- none --> The product is declared in `products/unified_gl/product.toml`.
- Known gap: `make demo-bad` still exits 0 because the `--bad` flag is not wired yet (roadmap step 4).
- Rollback: revert the merge commit; there is no persistent state to undo.
- Deferred review items (low severity, owner maksym.shkilov@gmail.com, due 2026-11-10): [spec](spec.md) §8 OQ-1…OQ-7.

**Acceptance criteria delivered:** AC-01…AC-14: one-command run with a summary; aligned entries with the same attributes from both sources; traceability to the raw record; group account per source system; reproducible synthetic data; deterministic unique identifiers; completeness gate passing on clean data and failing on a missing or changed entry; unreadable values never guessed; mapping gate; an ambiguous mapping stops the run; no credentials needed and inputs untouched; reserved products do not affect the result; documented attributes and currency list for step 3.
