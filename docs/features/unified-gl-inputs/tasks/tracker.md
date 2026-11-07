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
| T7 | Create staging.ledger_entry: the aligned entry set (neutral SQL) | migration | maksym.shkilov@gmail.com | M | T5 | todo | — |
| T8 | Write the three invariant SQL checks: unique document and line, unique entry id, unambiguous mapping | domain | maksym.shkilov@gmail.com | S | T1, T6, T7 | todo | — |
| T9 | Write the completeness gate and the mapping gate | domain | maksym.shkilov@gmail.com | M | T6, T7 | todo | — |
| T10 | Write the summary query and the exceptions report query | app | maksym.shkilov@gmail.com | S | T7 | todo | — |
| T11 | Activate unified_gl: product.toml manifest, smoke-test update, timed CI run | wiring | maksym.shkilov@gmail.com | S | T2, T5, T6, T7, T8, T9, T10 | todo | — |
| T12 | Document the aligned entry attributes and the synthetic-data notice in the product README | docs | maksym.shkilov@gmail.com | S | T7 | todo | — |
| T13 | End-to-end tests: five source differences, known values, traceability, exceptions report, exit codes | tests | maksym.shkilov@gmail.com | M | T11, T12, T4 | todo | — |

**Total:** 13 tasks, ~10.5 person-days.
