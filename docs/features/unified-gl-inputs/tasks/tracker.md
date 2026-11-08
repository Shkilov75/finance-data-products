# Tracker — unified-gl-inputs

> Status of every task in the epic. `implement` updates **Status** and **Step** after every
> subagent it runs (and commits them with the task), so this table shows where the run is right now.
> Status: `todo` · `in_progress` · `blocked` · `review` · `done`.
> Step: `SELECT` · `RED` · `GREEN` · `REFACTOR` · `GATE` · `REVIEW` · `COMMIT` (`—` before the task starts).
> A `blocked` row carries its reason in Step, e.g. `GATE — lint red after 3 retries`.

| # | Task | Layer | Owner | Estimate | Blocked by | Status | Step |
|---|---|---|---|---|---|---|---|
| T1 | Extend the runner with manifest keys, clean start, invariant phase and InvariantViolation | app | maksym.shkilov@gmail.com | M | — | done | COMMIT |
| T2 | Add report.py and extend the CLI: summary table, violating rows, exceptions line, reserved products, exit codes 2 and 3 | ports | maksym.shkilov@gmail.com | M | T1 | done | COMMIT |
| T3 | Write the seeded data generator and commit the five synthetic input files | infra | maksym.shkilov@gmail.com | L | — | done | COMMIT |
| T4 | Test the committed inputs: reproducibility hash, size, quarter, keys, balance, currencies, daily rates, synthetic names | tests | maksym.shkilov@gmail.com | S | T3 | done | COMMIT |
| T5 | Create the DuckDB adapter files: raw load of the five inputs and the typed views | migration | maksym.shkilov@gmail.com | M | T3 | done | COMMIT |
| T6 | Create the control views (independent raw side of the completeness gate) | migration | maksym.shkilov@gmail.com | S | T5 | done | COMMIT |
| T7 | Create staging.ledger_entry: the aligned entry set (neutral SQL) | migration | maksym.shkilov@gmail.com | M | T5 | done | COMMIT |
| T8 | Write the three invariant SQL checks: unique document and line, unique entry id, unambiguous mapping | domain | maksym.shkilov@gmail.com | S | T1, T6, T7 | done | COMMIT |
| T9 | Write the completeness gate and the mapping gate | domain | maksym.shkilov@gmail.com | M | T6, T7 | done | COMMIT |
| T10 | Write the summary query and the exceptions report query | app | maksym.shkilov@gmail.com | S | T7 | done | COMMIT |
| T11 | Activate unified_gl: product.toml manifest, smoke-test update, timed CI run | wiring | maksym.shkilov@gmail.com | S | T2, T5, T6, T7, T8, T9, T10 | done | COMMIT |
| T12 | Document the aligned entry attributes and the synthetic-data notice in the product README | docs | maksym.shkilov@gmail.com | S | T7 | done | COMMIT |
| T13 | End-to-end tests: five source differences, known values, traceability, exceptions report, exit codes | tests | maksym.shkilov@gmail.com | M | T11, T12, T4 | done | COMMIT |
| T14 | Review F1: strict raw readability (line digits only, empty document, unreadable-line duplicates, independent format checks in control views) | domain | maksym.shkilov@gmail.com | M | T13 | done | COMMIT |
| T15 | Review F2: translate on exact untrimmed text, keep original_description as written | domain | maksym.shkilov@gmail.com | S | T14 | done | COMMIT |
| T16 | Review F3: empty translation target counts as untranslated; invariant for a repeated translation row | domain | maksym.shkilov@gmail.com | S | T15 | done | COMMIT |
| T17 | Review F4: runner contract — stale files after exit 3, unknown status, file-named errors, manifest path validation | app | maksym.shkilov@gmail.com | M | T16 | done | COMMIT |
| T18 | Review F5 a-c: AC-06 equal-attribute pair, real-manifest test, stronger weak tests | tests | maksym.shkilov@gmail.com | S | T16 | done | COMMIT |
| T19 | Review F6: STRING instead of bare VARCHAR in neutral SQL | domain | maksym.shkilov@gmail.com | S | T16 | done | COMMIT |
| T20 | Review F7: remove unused down scripts and 'Staged DDL' headers from products/ | docs | maksym.shkilov@gmail.com | S | T19 | done | COMMIT |
| T21 | Review G1: export file must be a non-empty bare name; clean start removes a file or symlink in place of build/<product> | app | maksym.shkilov@gmail.com | S | T20 | done | COMMIT |
| T22 | Review G6: clean start leaves build folders of reserved products alone | app | maksym.shkilov@gmail.com | S | T21 | done | COMMIT |
| T23 | Review G7: manifest errors name the file; list types validated; SQL paths confined to the product folder | app | maksym.shkilov@gmail.com | S | T22 | done | COMMIT |
| T24 | Review G3: blank translation target counts as untranslated | domain | maksym.shkilov@gmail.com | S | T20 | done | COMMIT |
| T25 | Review G4: completeness gate prints an unreadable line as written | domain | maksym.shkilov@gmail.com | S | T24 | done | COMMIT |
| T26 | Review G5: invariant messages survive an empty key | domain | maksym.shkilov@gmail.com | S | T25 | done | COMMIT |
| T27 | Review G9: invariant file numbers follow the execution order | domain | maksym.shkilov@gmail.com | S | T26 | done | COMMIT |
| T28 | Review G2: ERP B and credit-side test coverage for the F1-F3 fixes | tests | maksym.shkilov@gmail.com | M | T27, T23 | done | COMMIT |
| T29 | Review G8: update README, cli.md, data-model.md and sad.md for the fourth invariant and STRING | docs | maksym.shkilov@gmail.com | S | T28 | done | COMMIT |
| T30 | Review H2: invariant messages survive an empty source_system | domain | maksym.shkilov@gmail.com | S | T29 | done | COMMIT |
| T31 | Review H3: whitespace-only line number prints as ? in gate and invariant messages | domain | maksym.shkilov@gmail.com | S | T30 | done | COMMIT |
| T32 | Review H6: non-UTF-8 manifest is a named ManifestError and cannot leave stale outputs | app | maksym.shkilov@gmail.com | S | T31 | done | COMMIT |
| T33 | Review H7: reject unknown manifest keys and repeated export file names | app | maksym.shkilov@gmail.com | S | T32 | done | COMMIT |
| T34 | Review H5: path confinement checks the path that is read when {engine} is used | app | maksym.shkilov@gmail.com | S | T33 | done | COMMIT |
| T35 | Review H8: exports are written only after every summary and export query succeeded | app | maksym.shkilov@gmail.com | S | T34 | done | COMMIT |
| T36 | Review H1: close the surviving test mutants of the F1-F3/G2 fixes | tests | maksym.shkilov@gmail.com | S | T35 | done | COMMIT |
| T37 | Review H4: align cli.md, data-model.md, README and spec OQ-2 with the code | docs | maksym.shkilov@gmail.com | S | T36 | done | COMMIT |
| T38 | Review I1: space-only source system or local account prints as ? in invariants 02/03 | domain | maksym.shkilov@gmail.com | S | T37 | done | COMMIT |
| T39 | Review I2: export file names are unique ignoring case | app | maksym.shkilov@gmail.com | S | T38 | done | COMMIT |
| T40 | Review I4: a path with a NUL or an unresolvable path is a named ManifestError | app | maksym.shkilov@gmail.com | S | T39 | done | COMMIT |
| T41 | Review I5: product name equals its folder name | app | maksym.shkilov@gmail.com | S | T40 | done | COMMIT |
| T42 | Review I6: a failing export write removes the files already written | app | maksym.shkilov@gmail.com | S | T41 | done | COMMIT |
| T43 | Review I7: drop the dead export-target check, test an unreadable manifest | app | maksym.shkilov@gmail.com | S | T42 | todo | SELECT |
| T44 | Review I3: data-model.md describes line_text as NULL when blank | docs | maksym.shkilov@gmail.com | S | T43 | todo | SELECT |

**Total:** 13 tasks, ~10.5 person-days.
