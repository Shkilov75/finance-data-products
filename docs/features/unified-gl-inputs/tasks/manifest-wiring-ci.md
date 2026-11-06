---
id: T11
title: "Activate unified_gl: product.toml manifest, smoke-test update, timed CI run"
layer: "wiring"
deps: ["T2", "T5", "T6", "T7", "T8", "T9", "T10"]
blocks: ["T13"]
acs: ["AC-01", "AC-13"]
files_hint: ["products/unified_gl/product.toml", "tests/unit/test_smoke.py", ".github/workflows/ci.yml", "products/unified_gl/gates/.gitkeep", "products/unified_gl/sql/.gitkeep", "products/unified_gl/data/.gitkeep"]
owner: "maksym.shkilov@gmail.com"
estimate: "S"
context_budget: "M"
status: "todo"
step: ""
---

<!-- Self-contained task. Inlined chunks carry a provenance signature; the source always wins.
To the executing agent: work from what is inlined here. If a slice is insufficient, ambiguous, or contradicts the code in front of you, open the named file for the full text and follow that. Do not invent the missing part. -->

# T11 — Activate unified_gl: product.toml manifest, smoke-test update, timed CI run

## Place in the sequence

- **Blocked by:** T2 — Add report.py and extend the CLI: summary table, violating rows, exceptions line, reserved products, exit codes 2 and 3, T5 — Create the DuckDB adapter files: raw load of the five inputs and the typed views, T6 — Create the control views (independent raw side of the completeness gate), T7 — Create staging.ledger_entry: the aligned entry set (neutral SQL), T8 — Write the three invariant SQL checks: unique document and line, unique entry id, unambiguous mapping, T9 — Write the completeness gate and the mapping gate, T10 — Write the summary query and the exceptions report query · **Blocks:** T13 — End-to-end tests: five source differences, known values, traceability, exceptions report, exit codes · **Wave:** 5, needs every piece it lists in the manifest.
- **Lane:** Own lane; last wiring step before the end-to-end tests.

## Why (user story)

> **As a** Reviewer  
> **I want** to run one command and see how many entries each source system delivered in each transaction currency  
> **So that** I can tell at a glance that the data arrived
>
> — `spec.md §4, US-02, verbatim` · full text: [spec.md](../spec.md)

> **As a** Reviewer  
> **I want** to see a gate that fails when an entry or an amount is lost between the raw files and the aligned entries  
> **So that** I can trust the alignment
>
> — `spec.md §4, US-06, verbatim` · full text: [spec.md](../spec.md)

Connects everything: one `make run` works end to end and the other three products stay reserved.

## Inlined context

> | `name`, `status` | string | `status = "active"` for `unified_gl` |
> | `sql` | list of paths | engine files first (with `{engine}`), then neutral SQL, in execution order |
> | `invariants` | list of paths | zero-row checks; a returned row → exit 2 |
> | `gates` | list of paths | `01_completeness.sql`, `02_mapping.sql`; zero rows = PASS |
> | `summary` | path | one query printed as the summary table |
> | `exports` | list of `{query, file}` | each query written by the core as CSV into `build/<product>/` |
>
> — `cli.md §6 manifest keys, verbatim` · full text: [cli.md](../contracts/cli.md)

> Run time of the whole-repository run command (after the one-time setup): ≤ 30 s on the CI runner, measured by a timed step in the CI log. Today `.github/workflows/ci.yml` runs only setup, lint and test, so a timed run step is added by this feature.
>
> — `spec.md §6 + sad.md §7 Monitoring, abridged` · full text: [spec.md](../spec.md)

> `tests/unit/test_smoke.py` ~ drops the «0 gates run» expectation once unified_gl is active.
>
> — `sad.md §5 Internal decomposition, verbatim` · full text: [sad.md](../sad.md)

> `products/unified_gl/product.toml` — `status = "active"` (currently `reserved`, `sql = []`, `gates = []`); the other three products stay `reserved`.
>
> — `products/unified_gl/product.toml + AC-13 Given, abridged` · full text: [spec.md](../spec.md)

> Shared behaviour lives in `src/fdp_core/`, never copied into a product. Products never import each other. IDs are deterministic hashes of business keys, never random UUIDs.
>
> — `CLAUDE.md §Conventions, abridged` · full text: [../../../CLAUDE.md](../../../../CLAUDE.md)

**Fallback:** insufficient or contradicted by the code → read the named file in full ([spec.md](../spec.md) · [sad.md](../sad.md) · [data-model.md](../data-model.md) · [cli.md](../contracts/cli.md) · [adr/](../adr/)) and follow it. Do not guess.

## Data delta

No DB changes.

## API contract

Internal — no API surface (the manifest keys above are the only interface).

## Acceptance criteria

### AC-01 (US-02) — happy path

> **Given** the Reviewer has a fresh clone of the repository, has done the one-time setup, and the product's exports are present  
> **When** the Reviewer starts the single run command  
> **Then** the run finishes successfully and prints, for each source system and each transaction currency, the number of entries loaded and their debit total and credit total, and states that both gates of the product passed; the summary also shows one number, the count of records in the exceptions report, always shown (0 included) next to the report name
>
> — `spec.md §5, AC-01, verbatim` · full text: [spec.md](../spec.md)

### AC-13 (US-06) — cross-context

> **Given** the product is declared active and the other three products are declared reserved (no gates yet), as defined in the glossary  
> **When** the Reviewer runs the whole repository  
> **Then** the failure of either gate of this product makes the overall run end as not successful, while the reserved products are listed as reserved in the run output and do not affect the result
>
> — `spec.md §5, AC-13, verbatim` · full text: [spec.md](../spec.md)


## Checklist

- [ ] Set `status = "active"`; fill `sql` (`adapters/{engine}/01…03`, then `sql/staging/04…`), `invariants` (3 files, order: document+line, entry id, mapping), `gates` (2 files), `summary`, `exports` (exceptions report → `exceptions_report.csv`) — `products/unified_gl/product.toml`
- [ ] Remove the now empty `.gitkeep` files in folders that got real content — `products/unified_gl/`
- [ ] Update `test_cli_boots_and_runs_empty_product_set`: expect exit 0, `2 gates run`, the four reserved lines minus unified_gl (three `reserved:` lines) — `tests/unit/test_smoke.py`
- [ ] CI: add a timed step `time make run` after the tests; fail the job over 30 s (simple `timeout 30` wrapper or `time` + check) — `.github/workflows/ci.yml`
- [ ] Run `make run` locally; check exit 0, the summary table, both gates PASS, `build/unified_gl/exceptions_report.csv` non-empty, `build/report.json` — whole repo

## Edge cases

| Case | Behaviour |
|---|---|
| Another product is `reserved` | listed as `reserved: <name>`, never affects the exit code (AC-13) |
| A gate of unified_gl fails | overall run exits 1 (AC-13) |
| `make run` > 30 s on CI | the CI step fails (spec §6) |
| `make demo-bad` | behaves as today for unified_gl; not claimed as a gate demonstration (roadmap step 4) |

## Definition of Done

- [ ] `make run` exits 0 on a fresh clone with the committed data; the output matches the contract order (AC-01)
- [ ] `fdp products` shows `unified_gl active` and three `reserved`; smoke tests pass (AC-13)
- [ ] CI workflow has the timed `make run` step
- [ ] `make test` and `make lint` clean
- [ ] every Hard Rule inlined above still holds
- [ ] lint + vet clean
