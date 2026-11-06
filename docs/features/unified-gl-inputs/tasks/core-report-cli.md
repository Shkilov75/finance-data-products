---
id: T2
title: "Add report.py and extend the CLI: summary table, violating rows, exceptions line, reserved products, exit codes 2 and 3"
layer: "ports"
deps: ["T1"]
blocks: ["T11"]
acs: ["AC-01", "AC-08", "AC-13"]
files_hint: ["src/fdp_core/report.py", "src/fdp_core/cli.py", "src/fdp_core/runner.py", "tests/unit/test_report_cli.py"]
owner: "maksym.shkilov@gmail.com"
estimate: "M"
context_budget: "M"
status: "todo"
step: ""
---

<!-- Self-contained task. Inlined chunks carry a provenance signature; the source always wins.
To the executing agent: work from what is inlined here. If a slice is insufficient, ambiguous, or contradicts the code in front of you, open the named file for the full text and follow that. Do not invent the missing part. -->

# T2 — Add report.py and extend the CLI: summary table, violating rows, exceptions line, reserved products, exit codes 2 and 3

## Place in the sequence

- **Blocked by:** T1 — Extend the runner with manifest keys, clean start, invariant phase and InvariantViolation · **Blocks:** T11 — Activate unified_gl: product.toml manifest, smoke-test update, timed CI run · **Wave:** 2, needs the manifest keys and phases of T1.
- **Lane:** Shares `src/fdp_core/runner.py` with T1 — serialized (after T1).

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

Delivers what the Reviewer sees on screen: the summary, the violating rows of a failed gate, the reserved products and the exit code.

## Inlined context

> **ADR-0004 (feature), decision:** Option 1. What to show stays visible as SQL in the product; how to show it (table layout, CSV writing, build folder) exists once in the core and does not depend on the engine. Option 2 puts file writing into engine-specific code, so each engine needs its own export and the summary has no shared home. A per-product Python report module was ruled out at the start, because `CLAUDE.md` forbids copying shared behaviour into a product.
>
> — `adr/0004-let-products-declare-report-queries-that-the-core-renders.md, Decision outcome, verbatim` · full text: [adr/0004-let-products-declare-report-queries-that-the-core-renders.md](../adr/0004-let-products-declare-report-queries-that-the-core-renders.md)

> 5. Run the `summary` query and the `exports`; write the files; print the output.
> 6. Exit with 0 or 1.
>
> — `cli.md §3.1 Phases 5–6, verbatim` · full text: [cli.md](../contracts/cli.md)

> In this order:
> 1. **Summary table** from the manifest `summary` query: one row per source system and transaction currency, columns `source_system`, `transaction_currency`, `entries`, `debit_total`, `credit_total` (AC-01). The currencies are exactly those found in `staging.ledger_entry`, never taken from the rates file (AC-14).
> 2. **Gate lines**, one per gate: `<STATUS>\t<gate name>\t<n> violating rows` (format of today's `cli.py`, kept).
> 3. **Violating rows** of every failed gate, each row printed in full (AC-08, AC-10): completeness rows name source system, transaction currency and the difference in entry count, debit total or credit total, and source system, document and line of each entry that is missing or differs; mapping rows name source system and local account.
> 4. **Exceptions line**: `exceptions_report.csv: <n> records` — always printed, `0` included (AC-01).
> 5. **Reserved products**: one line per product with status `reserved`, e.g. `reserved: cost_center_model` (AC-13). They do not affect the exit code.
> 6. **Final line**: `<n> gates run` (kept) and, on exit 0, a sentence that both gates of the product passed (rendered by the core from the gate list, feature ADR-0004).
>
> — `cli.md §3.3 Standard output, verbatim` · full text: [cli.md](../contracts/cli.md)

> | 0 | The run finished and every gate of every active product passed |
> | 1 | At least one gate failed. A failed gate is a **result**, not an exception |
> | 2 | An invariant check returned rows: `InvariantViolation` (subclass of `FdpError`). No gate, summary or export has run |
> | 3 | Any other `FdpError` (`LayerBuildError`, `ManifestError`): message printed, run stopped. Any other unexpected exception also gives 3 |
>
> — `cli.md §2 Exit codes, abridged` · full text: [cli.md](../contracts/cli.md)

> | 2, repeated key | `invariant violation: unique document and line` | one line per offender: source system, document, line (AC-06) |
> | 2, repeated entry id | `invariant violation: unique entry id` | source system, document, line of each entry sharing the id (AC-06) |
> | 2, ambiguous mapping | `invariant violation: unambiguous mapping` | source system and local account (AC-11) |
> | 3 | `error: <message>` | file and cause |
> After exit 2 or exit 3 no report file exists: neither `build/report.json` nor `build/<product>/exceptions_report.csv`.
>
> — `cli.md §3.4 Standard error, abridged` · full text: [cli.md](../contracts/cli.md)

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

Internal — no API surface. The CLI contract is [cli.md §2–§3](../contracts/cli.md); this task implements C1 output (`fdp run`) and keeps C2 (`fdp products`) unchanged.

## Acceptance criteria

### AC-01 (US-02) — happy path

> **Given** the Reviewer has a fresh clone of the repository, has done the one-time setup, and the product's exports are present  
> **When** the Reviewer starts the single run command  
> **Then** the run finishes successfully and prints, for each source system and each transaction currency, the number of entries loaded and their debit total and credit total, and states that both gates of the product passed; the summary also shows one number, the count of records in the exceptions report, always shown (0 included) next to the report name
>
> — `spec.md §5, AC-01, verbatim` · full text: [spec.md](../spec.md)

### AC-08 (US-06) — error

> **Given** an entry is missing from the aligned entries, or its amount differs from the raw data  
> **When** the completeness gate runs  
> **Then** it fails, names the source system, the transaction currency and the difference in entry count, debit total or credit total, and names the source system, document and line of every entry that is missing or whose date, amount or local account differs (including two entries that exchanged amounts, which leave the totals unchanged), and the run ends as not successful; the completeness gate is one gate, and its result lists both kinds of difference (counts and totals per source system and transaction currency, and individual entries)
>
> — `spec.md §5, AC-08, verbatim` · full text: [spec.md](../spec.md)

### AC-13 (US-06) — cross-context

> **Given** the product is declared active and the other three products are declared reserved (no gates yet), as defined in the glossary  
> **When** the Reviewer runs the whole repository  
> **Then** the failure of either gate of this product makes the overall run end as not successful, while the reserved products are listed as reserved in the run output and do not affect the result
>
> — `spec.md §5, AC-13, verbatim` · full text: [spec.md](../spec.md)


## Checklist

- [ ] Create `report.py`: `render_table(columns, rows)`, `write_csv(path, columns, rows)` (Python `csv`, LF endings, header always written), `format_gate_lines(results)` — `src/fdp_core/report.py`
- [ ] Runner phase 5: execute the manifest `summary` query and every `exports` query on the connection, write each export into `build/<product>/` (create folder), write `build/report.json`; also on a failed gate — `src/fdp_core/runner.py`
- [ ] Return a richer run result (gate results, summary columns/rows, export row counts, reserved product names) instead of the bare gate list — `src/fdp_core/runner.py`
- [ ] CLI `run`: print in the order of cli.md §3.3 (summary, gate lines, violating rows of failed gates, `exceptions_report.csv: <n> records`, reserved products, final line) — `src/fdp_core/cli.py`
- [ ] CLI error handling: `InvariantViolation` → stderr `invariant violation: <name>` plus one line per row, exit 2; other `FdpError` and any unexpected exception → `error: <message>`, exit 3 — `src/fdp_core/cli.py`
- [ ] Exit 0 sentence «both gates of <product> passed» rendered from the gate list — `src/fdp_core/cli.py`
- [ ] Unit tests with a throw-away product: output order, `0 records` line, violating rows printed in full, reserved products listed and not affecting the exit code, exit codes 0/1/2/3, no report files after exit 2/3 — `tests/unit/test_report_cli.py`

## Edge cases

| Case | Behaviour |
|---|---|
| Export query returns no rows | CSV with header only is written; CLI prints `exceptions_report.csv: 0 records` |
| A gate fails | summary, exports and `build/report.json` are still written; exit 1 |
| Invariant violation | stderr first line `invariant violation: <name>`, exit 2, no summary, no report files |
| Unexpected exception inside the run | `error: ...` and exit 3, never code 1 |
| Only reserved products | no summary table, `0 gates run`, reserved products listed, exit 0 |
| argparse usage error | also exits 2 (accepted collision, told apart by the `usage:` first line) |

## Definition of Done

- [ ] Unit tests for output order, violating rows and exit codes 0/1/2/3 pass (AC-01, AC-08, AC-13 core side)
- [ ] No report file exists after exit 2 and exit 3
- [ ] The reserved products never change the exit code
- [ ] every Hard Rule inlined above still holds
- [ ] lint + vet clean
