# unified_gl

Two ERP exports in different formats become one aligned set of ledger entries, checked by two
gates and four invariant checks. This step ends with the aligned entries; USD conversion is the
next roadmap step.

> **All data here is synthetic.** Every input file below, and every name and amount in it, is
> fictitious. It is written by `data/generate.py` from a fixed seed, so the files are identical
> on every generation. The file names say `synthetic` on purpose.

| Input file in `data/` | What it is |
|---|---|
| `erp_a_export_synthetic.csv` | ERP A export: flat text, `;` delimiter, German column names |
| `erp_b_export_synthetic.json` | ERP B export: one JSON array of documents with nested lines, English names |
| `account_mapping_synthetic.csv` | local account of a source system → account of the common chart |
| `description_translation_synthetic.csv` | German descriptions → English (ERP B rows map to themselves) |
| `rates_synthetic.csv` | one rate to USD per currency and calendar day for 2026-01-01 to 2026-03-31 (loaded, not read in this step) |

A run only reads these files; it never changes them. Only `python products/unified_gl/data/generate.py`
writes them.

## Run it

```
make setup     # one time
make run       # builds build/fdp.duckdb, runs the checks and gates, prints the summary
```

## The five deliberate source differences

The two exports differ in the ways real systems do, so the alignment has real work to do:

1. **Date format**: ERP A writes `DD.MM.YYYY`, ERP B writes `MM/DD/YYYY`.
2. **Number format**: ERP A writes `1.234,56`, ERP B writes `1,234.56`.
3. **Debit and credit**: ERP A has two columns and exactly one is filled; ERP B has one signed amount (negative = credit).
4. **Column names and language**: German in ERP A, English in ERP B; descriptions are German and English.
5. **Record shape**: ERP A is flat, ERP B is nested (a document holds its lines).

A value that cannot be read in its source format becomes empty and is never guessed. Such an entry
is not accepted as aligned, and the completeness gate reports it as missing.

## Aligned entries

The aligned entries are the table `staging.ledger_entry`. There is no command and no CSV export of
it in this step. To look at it, open the build database after a run, for example with the `duckdb`
command line client: `duckdb build/fdp.duckdb "SELECT * FROM staging.ledger_entry LIMIT 10"`.

| Attribute | Type | Meaning | Empty allowed |
|---|---|---|---|
| `entry_id` | STRING | Stable identifier: `md5` of source system, document and line joined with `\|`; the line counts as a whole number, so `01` and `1` give the same id | no |
| `source_system` | STRING | `ERP_A` or `ERP_B`: which export the entry came from | no |
| `source_document` | STRING | Document number as written in the source (spaces trimmed) | no |
| `source_line` | INTEGER | Line number within the document | no |
| `entry_date` | DATE | The posting date as a real calendar date | no |
| `signed_amount` | DECIMAL(18,2) | One amount for both sources: debit positive, credit negative, never zero, two decimals, never rounded | no |
| `transaction_currency` | STRING | Currency of the document (EUR, GBP or USD in the data); the run summary lists exactly the currencies found here | no |
| `local_account` | STRING | Account in the source's own chart of accounts | no |
| `group_account` | STRING | Account of the common chart that the local account maps to | yes: empty means no mapping row, and the mapping gate fails |
| `description` | STRING | Description in English; the original text when the translation list has no exact match or its translation is empty or only spaces | no |
| `original_description` | STRING | Description exactly as the source wrote it (needed by the exceptions report) | no |

### Trace an entry back to its raw record

Raw data is kept as it arrived. Find the record by `source_system`, `source_document`, `source_line`:

- ERP A: table `raw.erp_a_export`, columns `belegnummer` and `zeile`.
- ERP B: table `raw.erp_b_export`, column `doc_id` and the nested `lines[].line_no`.

## Checks, gates and the exceptions report

| Kind | What it does | Result |
|---|---|---|
| Invariant check (`invariants/`) | Stops the run when a key is broken: a document and line repeated in one export, an ambiguous account mapping, an ambiguous translation row (the same original description twice), or a repeated `entry_id`. They run in that order, so a repeated mapping or translation row is reported as itself and not as a repeated `entry_id`. Names the source system, document and line (or local account, or description) | Error, exit code 2 |
| Gate (`gates/`) | `01_completeness.sql` compares the raw side with the aligned entries (counts and debit and credit totals per source system and currency, and every single entry); `02_mapping.sql` lists entries without a group account | A failed gate is a result: the run goes on and ends with exit code 1 |
| Exceptions report | One record per aligned entry whose description has no translation (exact whole-text match; an empty or space-only translation counts as none), kept with its original text | `build/unified_gl/exceptions_report.csv`, always written, header only when empty |

Every check is one SQL file; zero returned rows means the check passes.

The four invariant checks, in the order they run (the order matters, see above):

1. `unique document and line`
2. `unambiguous mapping`
3. `unambiguous translation`
4. `unique entry id`

### Exit codes of `fdp run`

| Exit code | Meaning |
|---|---|
| 0 | The run finished and every gate passed |
| 1 | At least one gate failed |
| 2 | An invariant check returned rows |
| 3 | Any other error, for example a layer SQL file that does not run |

The reports are also written after a failed gate (exit code 1); after exit code 2 or 3 no report
file exists. `build/` holds diagnostics only and is rebuilt on every run. The other three products
are `reserved` and appear in the output as `reserved: <name>`; they do not change the exit code.

## Folder layout

```
products/unified_gl/
  data/          the five synthetic input files and generate.py
  adapters/duckdb/   engine-specific SQL: file readers and the typed views (dates, numbers)
  sql/staging/   neutral SQL: staging.ledger_entry
  invariants/    zero-row checks that stop the run
  gates/         zero-row gates
  reports/       the summary query and the exceptions report query
  product.toml   the manifest read by fdp_core
```

`adapters/databricks/` is planned and not yet written or verified, so this README makes no Databricks claim.

Design and decisions: [spec](../../docs/features/unified-gl-inputs/spec.md),
[data model](../../docs/features/unified-gl-inputs/data-model.md),
[CLI contract](../../docs/features/unified-gl-inputs/contracts/cli.md).
