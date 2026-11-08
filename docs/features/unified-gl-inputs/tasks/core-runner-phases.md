---
id: T1
title: "Extend the runner with manifest keys, clean start, invariant phase and InvariantViolation"
layer: "app"
deps: []
blocks: ["T2", "T8"]
acs: ["AC-06", "AC-11"]
files_hint: ["src/fdp_core/errors.py", "src/fdp_core/config.py", "src/fdp_core/runner.py", "tests/unit/test_runner_phases.py"]
owner: "maksym.shkilov@gmail.com"
estimate: "M"
context_budget: "M"
status: "done"
step: "COMMIT"
---

<!-- Self-contained task. Inlined chunks carry a provenance signature; the source always wins.
To the executing agent: work from what is inlined here. If a slice is insufficient, ambiguous, or contradicts the code in front of you, open the named file for the full text and follow that. Do not invent the missing part. -->

# T1 — Extend the runner with manifest keys, clean start, invariant phase and InvariantViolation

## Place in the sequence

- **Blocked by:** — · **Blocks:** T2 — Add report.py and extend the CLI: summary table, violating rows, exceptions line, reserved products, exit codes 2 and 3, T8 — Write the three invariant SQL checks: unique document and line, unique entry id, unambiguous mapping · **Wave:** 1, no upstream dependency; first task on the critical path.
- **Lane:** Shares `src/fdp_core/runner.py` with T2 — serialized (T2 depends on T1).

## Why (user story)

> **As an** Owner  
> **I want** the aligned entry set to have a documented, stable shape and identifiers that do not change between runs  
> **So that** the USD conversion step can build on it without rework
>
> — `spec.md §4, US-07, verbatim` · full text: [spec.md](../spec.md)

> **As a** Reviewer  
> **I want** to see every entry carry the group account its local account maps to, and see any entry whose local account has no mapping  
> **So that** no entry silently disappears or lands in a blank account
>
> — `spec.md §4, US-05, verbatim` · full text: [spec.md](../spec.md)

Delivers the engine part of «a repeated key or an ambiguous mapping stops the run»: the invariants phase and the typed error.

## Inlined context

> The current runner knows only layers and gates; a failed gate is a normal result and the run goes on. … An `invariants` list in `product.toml` — SQL files with the zero-row convention. `fdp_core` runs them after the layers are built and before the gates; any returned row raises a typed `InvariantViolation` (in `errors.py`) whose message lists the rows; the CLI prints it and exits with code 2 (a failed gate exits with 1).
>
> — `adr/0003-stop-the-run-on-sql-invariant-checks-declared-in-the-manifest.md, Context + Considered options 1, abridged` · full text: [adr/0003-stop-the-run-on-sql-invariant-checks-declared-in-the-manifest.md](../adr/0003-stop-the-run-on-sql-invariant-checks-declared-in-the-manifest.md)

> **ADR-0003 (feature), decision:** Option 1. It keeps the check in neutral SQL that runs on both engines and names the offending business keys in the message. Engine constraints (`PRIMARY KEY`, `UNIQUE`) were set aside from the start: Delta tables on Databricks do not enforce them (ADR-0004 of the repository), and they cannot name source system, document and line as AC-06 requires. Option 2 makes the core import product code and moves the logic out of SQL.
>
> — `adr/0003-stop-the-run-on-sql-invariant-checks-declared-in-the-manifest.md, Decision outcome, verbatim` · full text: [adr/0003-stop-the-run-on-sql-invariant-checks-declared-in-the-manifest.md](../adr/0003-stop-the-run-on-sql-invariant-checks-declared-in-the-manifest.md)

> `product.toml` paths contain an `{engine}` placeholder that `fdp_core` replaces with the engine name; `Config` gains an `engine` value, default `duckdb`.
>
> — `adr/0001-expose-typed-flat-views-from-per-engine-adapters.md, Consequences, verbatim` · full text: [adr/0001-expose-typed-flat-views-from-per-engine-adapters.md](../adr/0001-expose-typed-flat-views-from-per-engine-adapters.md)

> 1. Start clean, then rebuild. Delete `build/fdp.duckdb`, `build/report.json` and the folder `build/<product>/` of every active product (repo ADR-0003 for the database file); other files in `build/` are not touched. Then create `build/fdp.duckdb` with the empty layers `raw`, `staging`, `mart`.
> 2. For each active product: execute the engine files (`adapters/duckdb/`, `{engine}` in manifest paths is replaced by the engine name, default `duckdb`), then the neutral `sql` files. A failing file → exit 3.
> 3. Run the product's `invariants` in the order of the manifest list (zero-row convention). The first invariant that returns rows stops the run with exit 2; the invariants after it are not executed.
> 4. Run the product's `gates` (zero-row convention). A failed gate does not stop the run.
>
> — `cli.md §3.1 Phases 1–4, verbatim` · full text: [cli.md](../contracts/cli.md)

> | `sql` | list of paths | engine files first (with `{engine}`), then neutral SQL, in execution order |
> | `invariants` | list of paths | zero-row checks; a returned row → exit 2 |
> | `gates` | list of paths | `01_completeness.sql`, `02_mapping.sql`; zero rows = PASS |
> | `summary` | path | one query printed as the summary table |
> | `exports` | list of `{query, file}` | each query written by the core as CSV into `build/<product>/` |
>
> — `cli.md §6 manifest keys, verbatim` · full text: [cli.md](../contracts/cli.md)

> Shared behaviour lives in `src/fdp_core/`, never copied into a product. Products never import each other. IDs are deterministic hashes of business keys, never random UUIDs.
>
> — `CLAUDE.md §Conventions, abridged` · full text: [../../../CLAUDE.md](../../../../CLAUDE.md)

> A gate is one SQL file `products/<p>/gates/NN_<name>.sql`; zero returned rows means PASS. A failed gate is a result, not an exception; the runner exits non-zero on any FAIL.
>
> — `CLAUDE.md §Conventions, abridged` · full text: [../../../CLAUDE.md](../../../../CLAUDE.md)

**Fallback:** insufficient or contradicted by the code → read the named file in full ([spec.md](../spec.md) · [sad.md](../sad.md) · [data-model.md](../data-model.md) · [cli.md](../contracts/cli.md) · [adr/](../adr/)) and follow it. Do not guess.

## Data delta

No DB changes.

## API contract

Internal — no API surface (the manifest keys above are the only interface; the CLI output belongs to T2).

## Acceptance criteria

### AC-06 (US-07) — domain invariant violation

> **Given** aligned entries from both source systems, including two entries of one document that share date, account and amount, and both exports carry an explicit document number and line number for every entry  
> **When** the Owner runs the product twice  
> **Then** every entry has an identifier derived from source system, document and line (the three values in this order, as written in the source apart from trimmed spaces, joined by a fixed separator; the line takes part as a whole number, so «01» and «1» give the same identifier, while the document is taken as written in the source with trimmed spaces only), the identifiers are unique across both source systems, each entry keeps the same identifier in both runs, and if two entries ever shared an identifier, or one export held the same document and line twice (checked on the raw records of each export before any readability rule is applied, so an unreadable duplicate also stops the run), the run would stop with an error that names the source system, document and line (an error, not a gate result)
>
> — `spec.md §5, AC-06, verbatim` · full text: [spec.md](../spec.md)

### AC-11 (US-05) — domain invariant violation

> **Given** the account mapping lists the same local account of the same source system more than once, either with two different group accounts or with the same group account repeated  
> **When** the product is run  
> **Then** the run stops with an error (not a gate result) that tells the Reviewer which source system and local account are ambiguous, because each local account of a source system has exactly one row in the account mapping
>
> — `spec.md §5, AC-11, verbatim` · full text: [spec.md](../spec.md)


## Checklist

- [ ] Add `InvariantViolation(FdpError)` carrying the violating rows and the invariant name — `src/fdp_core/errors.py`
- [ ] Add `engine: str = "duckdb"` to `Config`; add `build_dir` helper for `build/<product>/` — `src/fdp_core/config.py`
- [ ] Extend `Product` and `discover_products` with `invariants`, `summary`, `exports` (all optional, default empty/None) — `src/fdp_core/runner.py`
- [ ] Phase 1: delete `build/fdp.duckdb`, `build/report.json`, `build/<product>/` of every active product, then create the empty layers — `src/fdp_core/runner.py`
- [ ] Replace `{engine}` in every manifest path with `cfg.engine` before reading the file — `src/fdp_core/runner.py`
- [ ] Phase 3: run `invariants` in manifest order with `run_sql_gate`-style zero-row check; the first one that returns rows raises `InvariantViolation` and later ones do not run — `src/fdp_core/runner.py`
- [ ] Keep phase 4 (gates) as is; keep writing `build/report.json` after phase 4 — `src/fdp_core/runner.py`
- [ ] Unit tests on a throw-away product folder under `tmp_path` (a `Config(root=tmp_path)`): invariant with rows → `InvariantViolation` and later invariants not executed; zero rows → gates run; `{engine}` replaced; stale `build/report.json` and `build/<product>/` removed — `tests/unit/test_runner_phases.py`

## Edge cases

| Case | Behaviour |
|---|---|
| Invariant returns rows | `InvariantViolation` raised before any gate runs; message lists each row; no `build/report.json` written |
| Two invariants, first one returns rows | second one is not executed (phase 3 wording) |
| Manifest has no `invariants` key | phase 3 is skipped, behaviour as today (the three reserved products keep working) |
| Layer SQL file fails | `LayerBuildError` (exit 3 at the CLI, T2) |
| Stale `build/report.json` from an earlier run | deleted in phase 1, never survives into this run |

## Definition of Done

- [ ] Unit tests for phases 1, 3, 4 and `{engine}` replacement pass (AC-06, AC-11 engine side)
- [ ] `InvariantViolation` is a subclass of `FdpError`
- [ ] A product without the new keys still runs unchanged
- [ ] every Hard Rule inlined above still holds
- [ ] lint + vet clean
