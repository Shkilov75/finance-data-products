---
status: Draft
owner: "maksym.shkilov@gmail.com"
reviewers: []
updated_at: "2026-11-06"
feature_size: "M"
surface: cli
contract_version: "0.1.0"
derived_from: [spec.md, sad.md, data-model.md, adr/0001..0005]
---

# CLI contract — unified-gl-inputs

> Derived, not hand-written: `data-model.md` (typed shape) + `sad.md` §6 flows (branches, exit codes) + `spec.md` §4/§5 (observable outcomes). Origins and drift result: `api-sync-report.md`. All data in examples is synthetic placeholder data.

## 1. Surface overview

The feature adds no new command. It makes the existing `fdp run` do real work for the product `unified_gl` and adds one stand-alone script, the data generator.

| # | Command | Owner | Serves |
|---|---|---|---|
| C1 | `fdp run [--bad]` (`make run`, `make demo-bad`) | `fdp_core` (extended) | US-02, US-05, US-06, US-07; AC-01, AC-06..AC-11, AC-13, AC-14 |
| C2 | `fdp products` | `fdp_core` (unchanged) | AC-13 (lists reserved products) |
| C3 | `python products/unified_gl/data/generate.py` | `unified_gl` | US-01; AC-05, AC-12 |

No command takes credentials or a network address (spec §6.1, AC-12). Every command is non-interactive.

## 2. Exit codes (shared by C1 and C2)

| Code | Meaning | Raised by | Source |
|---|---|---|---|
| 0 | The run finished and every gate of every active product passed | `runner.exit_code` | AC-01, AC-13 |
| 1 | At least one gate failed. A failed gate is a **result**, not an exception | `runner.exit_code` | AC-08, AC-10, AC-13; Flow 2 |
| 2 | An invariant check returned rows: `InvariantViolation` (subclass of `FdpError`). No gate, summary or export has run | `cli.main` | AC-06, AC-11; feature ADR-0003; Flow 1 |
| 3 | Any other `FdpError` (`LayerBuildError`, `ManifestError`): message printed, run stopped. Any other unexpected exception also gives 3: `cli.main` catches it, so it is never mistaken for a failed gate (code 1) | `cli.main` | SAD §7, §8; report N1, OQ-2 |

**Known collision (accepted).** `argparse` also exits with 2 on a usage error (unknown command or flag). The two are told apart by the first line on stderr: `usage:` for argparse, `invariant violation:` for code 2. Code is not changed (decision of the `api` run, 2026-11-06; see report finding F1).

## 3. C1 — `fdp run`

```
fdp run [--bad]
```

| Element | Type | Default | Notes |
|---|---|---|---|
| `--bad` | flag | off | Exists today. Selects deliberately corrupted data. **Not implemented for `unified_gl` in this feature** (roadmap step 4); with this feature `--bad` behaves as today and must not be claimed as a gate demonstration (report note N2) |

Environment: none. Working directory: any inside the repository (root is found from the package location, `config.repo_root`).

### 3.1 Phases (order is part of the contract)

1. Start clean, then rebuild. Delete `build/fdp.duckdb`, `build/report.json` and the folder `build/<product>/` of every active product (repo ADR-0003 for the database file); other files in `build/` are not touched. Then create `build/fdp.duckdb` with the empty layers `raw`, `staging`, `mart`.
2. For each active product: execute the engine files (`adapters/duckdb/`, `{engine}` in manifest paths is replaced by the engine name, default `duckdb`), then the neutral `sql` files. A failing file → exit 3.
3. Run the product's `invariants` in the order of the manifest list (zero-row convention). The first invariant that returns rows stops the run with exit 2; the invariants after it are not executed.
4. Run the product's `gates` (zero-row convention). A failed gate does not stop the run.
5. Run the `summary` query and the `exports`; write the files; print the output.
6. Exit with 0 or 1.

### 3.2 Reads and writes (AC-12)

| Direction | Path | Rule |
|---|---|---|
| Reads | `products/unified_gl/data/erp_a_export_synthetic.csv`, `erp_b_export_synthetic.json`, `account_mapping_synthetic.csv`, `description_translation_synthetic.csv`, `rates_synthetic.csv` | Opened read-only; never changed by a run |
| Writes | `build/fdp.duckdb` | Rebuilt on every run |
| Writes | `build/report.json` | Array of `{gate, status, violations}`; also written after a failed gate |
| Writes | `build/unified_gl/exceptions_report.csv` | Header `source_system,source_document,source_line,original_description`; **always** written, header only when no record (AC-02); also written after a failed gate (SAD §1 override) |
| Writes | nothing else | In particular nothing under `products/` |

Report files are deleted in phase 1 and written in phase 5. So after exit 0 and exit 1 the files are fresh from this run; after exit 2 and exit 3 (the run stops before phase 5) none exist, and no file of an earlier run is left.

`rates_synthetic.csv` is loaded into `raw.exchange_rate` and not read further in this step.

### 3.3 Standard output (exit 0 and exit 1)

In this order:

1. **Summary table** from the manifest `summary` query: one row per source system and transaction currency, columns `source_system`, `transaction_currency`, `entries`, `debit_total`, `credit_total` (AC-01). The currencies are exactly those found in `staging.ledger_entry`, never taken from the rates file (AC-14).
2. **Gate lines**, one per gate: `<STATUS>\t<gate name>\t<n> violating rows` (format of today's `cli.py`, kept).
3. **Violating rows** of every failed gate, each row printed in full (AC-08, AC-10): completeness rows name source system, transaction currency and the difference in entry count, debit total or credit total, and source system, document and line of each entry that is missing or differs; mapping rows name source system and local account.
4. **Exceptions line**: `exceptions_report.csv: <n> records` — always printed, `0` included (AC-01).
5. **Reserved products**: one line per product with status `reserved`, e.g. `reserved: cost_center_model` (AC-13). They do not affect the exit code.
6. **Final line**: `<n> gates run` (kept) and, on exit 0, a sentence that both gates of the product passed (rendered by the core from the gate list, feature ADR-0004).

Example (exit 0, placeholder values):

```
source_system  transaction_currency  entries  debit_total  credit_total
ERP_A          EUR                       61     48210.40      48210.40
ERP_A          GBP                       52     30118.00      30118.00
ERP_B          USD                       70     55290.15      55290.15
PASS	01_completeness	0 violating rows
PASS	02_mapping	0 violating rows
exceptions_report.csv: 4 records
reserved: cost_center_model
reserved: epm
reserved: functional_model
2 gates run; both gates of unified_gl passed
```

Example (exit 1, placeholder values; one ERP_A EUR debit of 100.00 is missing from the aligned entries, so the summary, which reads the aligned entries, shows 60 entries where the raw data has 61):

```
source_system  transaction_currency  entries  debit_total  credit_total
ERP_A          EUR                       60     48110.40      48210.40
ERP_A          GBP                       52     30118.00      30118.00
ERP_B          USD                       70     55290.15      55290.15
FAIL	01_completeness	3 violating rows
PASS	02_mapping	0 violating rows
  ERP_A EUR entries: raw 61, aligned 60
  ERP_A EUR debit_total: raw 48210.40, aligned 48110.40
  ERP_A DOC-0007 line 2: missing in aligned entries
exceptions_report.csv: 4 records
reserved: cost_center_model
reserved: epm
reserved: functional_model
2 gates run
```

### 3.4 Standard error (exit 2 and exit 3)

| Exit | First line | Names |
|---|---|---|
| 2, repeated key | `invariant violation: unique document and line` | one line per offender: source system, document, line (AC-06) |
| 2, ambiguous translation | `invariant violation: unambiguous translation` | source system and original description of a translation row that appears more than once (AC-02, AC-06); runs before the entry-id check, so it is never reported as a repeated entry id |
| 2, repeated entry id | `invariant violation: unique entry id` | source system, document, line of each entry sharing the id (AC-06) |
| 2, ambiguous mapping | `invariant violation: unambiguous mapping` | source system and local account (AC-11), whether the group accounts differ or repeat |
| 3 | `error: <message>` | file and cause, e.g. `unified_gl/sql/staging/04_create_staging_ledger_entry.sql: ...` |

Example (exit 2, placeholder values):

```
invariant violation: unambiguous mapping
  ERP_B 4710 appears 2 times in account_mapping_synthetic.csv
```

After exit 2 or exit 3 no report file exists: neither `build/report.json` nor `build/<product>/exceptions_report.csv`, from this run or from an earlier one (§3.1 phase 1).

### 3.5 Error scenarios

| Scenario | Exit | Spec | Flow |
|---|---|---|---|
| Clean data, both gates pass | 0 | AC-01, AC-07, AC-13 | 1, 4, 6 |
| Entry lost or amount differs between raw and aligned | 1 | AC-08 | 2, 6 |
| Unreadable entry (date, amount, both/neither side filled, zero, too many decimals) | 1 (shows as a missing entry) | AC-09 | 5, 6 |
| Local account without a mapping row | 1 (mapping gate) | AC-10 | 2, 5 |
| Description without translation | 0 (entry stays; one record in the exceptions report) | AC-02 | 4, 5 |
| Same source system, document and line twice in one export (checked on raw records) | 2 | AC-06 | 1, 7 |
| Same original description twice in the translation list | 2 | AC-02, AC-06 | 1 |
| Same `entry_id` twice | 2 | AC-06 | 1, 7 |
| Same local account twice in the mapping (same or different group account) | 2 | AC-11 | 1 |
| Layer SQL file fails, manifest key missing or malformed (the message names `product.toml`), a path that leaves the product folder, an export `file` that is not a plain file name | 3 | SAD §8, AC-12 | 1 |

### 3.6 Idempotency

Two runs on the same inputs give identical `entry_id` values and identical exit codes (AC-06). Nothing carries over between runs: the database file, `build/report.json` and `build/<product>/` are deleted first (§3.1 phase 1).

## 4. C2 — `fdp products`

Unchanged. Prints `<name>\t<status>` per discovered product, exit 0. After this feature `unified_gl` shows `active`; the other three show `reserved`. A malformed `product.toml` → exit 3.

## 5. C3 — data generator

```
python products/unified_gl/data/generate.py
```

| Element | Value |
|---|---|
| Arguments | none. The seed is fixed in the script (AC-05) |
| Writes | the five input files named in §3.2, into `products/unified_gl/data/`; every file name contains `synthetic` (AC-12) |
| Output on stdout | `erp_a_export_synthetic.csv: <n> entries` and `erp_b_export_synthetic.json: <n> entries` |
| Exit | 0 files written; 3 a file could not be written |
| Determinism | byte-identical files on every call: amounts from integer cents, no timestamps, fixed row and key order, LF endings (spec §6) |
| Python API | also returns the list of expected aligned entries (`entry_id`, signed amount, group account, common description) for tests (data-model «Test fixtures») |

The generator does **not** check its own output. Size (100 to 250 entries per export), the first quarter, explicit document and line numbers, balanced documents, currencies and one rate per currency per day are checked by the test suite (decision of the `api` run, 2026-11-06; report finding F3).

Only the generator writes the input files; a product run opens them read-only (AC-12).

## 6. Product manifest keys (interface between a product and `fdp_core`)

`products/unified_gl/product.toml` after this feature (feature ADR-0003, feature ADR-0004):

| Key | Type | Meaning |
|---|---|---|
| `name`, `status` | string | `status = "active"` for `unified_gl` |
| `sql` | list of paths | engine files first (with `{engine}`), then neutral SQL, in execution order |
| `invariants` | list of paths | zero-row checks; a returned row → exit 2 |
| `gates` | list of paths | `01_completeness.sql`, `02_mapping.sql`; zero rows = PASS |
| `summary` | path | one query printed as the summary table |
| `exports` | list of `{query, file}` | each query written by the core as CSV into `build/<product>/`; `file` is a plain file name (letters, digits, `_`, `.`, `-`), never a path |

Every path in `sql`, `invariants`, `gates`, `summary` and `exports[].query` stays inside the product's own folder (products never share SQL); `sql`, `gates` and `invariants` are lists of strings. A violation is a manifest error: exit 3, the message names the `product.toml`. The clean start (§3.1 phase 1) removes `build/<product>/` of every product except one whose manifest says `reserved`; a file or symlink in its place is removed, never followed.

## 7. Data contract — the aligned entry set

The Reviewer sees the aligned entries by opening `build/fdp.duckdb` and reading the table `staging.ledger_entry` (for example with the `duckdb` command line client). There is no command and no CSV export for it in this step (decision of the `api` run, 2026-11-06; report finding F2). Sample output for the reader belongs to roadmap step 5.

The table is the stable contract for roadmap step 3. Types and constraints are those of `data-model.md` and are not repeated here:

`entry_id`, `source_system` (`ERP_A` or `ERP_B`), `source_document`, `source_line`, `entry_date`, `signed_amount` (debit positive, credit negative, scale 2), `transaction_currency`, `local_account`, `group_account` (NULL when unmapped), `description` (English), `original_description`.

Traceability (AC-03): the raw record is found by `source_system`, `source_document`, `source_line` in `raw.erp_a_export` (`belegnummer`, `zeile`) or `raw.erp_b_export` (`doc_id`, nested `lines[].line_no`).

## 8. Compatibility

- Output line formats in §3.3 and §3.4 are the contract for tests and for the README sample of roadmap step 5; the column widths are not.
- Adding a gate or a summary column is compatible; changing an exit code or a file name is a breaking change and needs a new `contract_version` and a CHANGELOG line (never bumped silently by `api`).
