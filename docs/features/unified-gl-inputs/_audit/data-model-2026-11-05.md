---
status: Draft
updated_at: "2026-11-05"
---

# Data-model audit — unified-gl-inputs (2026-11-05)

**Migrations are staged — not yet in any live tree; `implement` promotes them.** The repo has no `migrations/` folder and no migration tool, so there is no live tree and no number to assign: `implement` moves the `up` text into the places listed in `data-model.md` («Staged DDL»).

## Staged files

| Pair | Path |
|---|---|
| 01 | `docs/features/unified-gl-inputs/migrations/01_create_raw_inputs.{up,down}.sql` |
| 02 | `docs/features/unified-gl-inputs/migrations/02_create_typed_views.{up,down}.sql` |
| 03 | `docs/features/unified-gl-inputs/migrations/03_create_control_views.{up,down}.sql` |
| 04 | `docs/features/unified-gl-inputs/migrations/04_create_staging_ledger_entry.{up,down}.sql` |

**Promote-time hint:** no numbering (repo ADR-0003, `migration_tool: ""`); pairs 01–03 become DuckDB adapter files, pair 04 becomes `sql/staging/` neutral SQL, 01–03 are repeated in Spark SQL at roadmap step 6.

## Verification done

- All four `up` files ran in order on DuckDB 2.0.0 (repo `.venv`) against a 10-row ERP A and 6-row ERP B edge-case file set; all four `down` files ran in reverse order and left zero tables in `raw` and `staging`.
- Covered cases: German and US number and date formats, thousands separators, both debit and credit filled, both empty, negative, zero, three decimals, impossible date (31.02 and 13/45), untranslated description, local account without mapping row, same local code `4000` in both charts with different group accounts.
- One defect found and fixed by the run: the first control view counted the amount of an entry with an unreadable date in the raw totals, which contradicts AC-09; `signed_amount` is now NULL for every unreadable entry.
- Not run: Spark SQL (adapter is written at roadmap step 6); the mermaid CLI is not installed, so the `erDiagram` was checked by the structural lint only (valid cardinality glyphs, `type name` attribute lines).

## Self-check

| Check | Result |
|---|---|
| Naming matches the repo | Pass: snake_case, schemas `raw`/`staging`, `<layer>.<table>`; source-file column names keep the source's own names (German for ERP A) on purpose |
| Down reversibility | Pass: every CREATE has a DROP, verified by execution |
| FK indexes | N/A: no foreign keys are declared (see divergence 2) |
| Convention adherence | Pass with the flagged divergences below |

## Convention deviations (flagged, not silent)

1. **Staged pairs with no migration tool.** The skill asks for staged `.up/.down` pairs; the repo has no migration tool. Confirmed with the Owner: pairs are design DDL.
2. **No PK/FK/UNIQUE and no physical indexes.** An engine constraint would raise before the typed `InvariantViolation` of feature ADR-0003 (AC-06, AC-11); Spark has no secondary indexes (repo ADR-0004); at 100–250 rows an index adds nothing. Access paths are documented instead.
3. **`original_description` added to `staging.ledger_entry`.** The exceptions report needs it; adds one attribute to the contract for step 3.
4. **Open acceptance rule.** Empty document, line, currency or local account is treated as unreadable (AC-09 says «including»).
5. **Identity rows for ERP B in the translation list.** Keeps the neutral SQL uniform (see `data-model.md`).

## Open points (`<!-- TBD -->`)

- <!-- TBD --> **`rates.csv` vs «synthetic» in file names.** AC-05 fixes the name `rates.csv`, AC-12 requires the committed file names to state that the data is synthetic. `data-model.md` keeps `rates.csv` (spec-literal); recommendation: amend AC-05 to `rates_synthetic.csv` (via `clarify`). All other files already carry `_synthetic`.
- <!-- TBD --> **Owner of the generator input checks** (size, quarter, keys, balance, one rate per day), already flagged in SAD §6. Not a schema question; decide in `tasks`.
- <!-- TBD --> **Over-precision for other currencies.** The adapters hard-code «at most 2 decimals», correct for EUR, GBP and USD (AC-09). A currency with a different number of decimals (for example JPY) would need a small currency table; out of scope.
- <!-- TBD --> **Duplicate identical rows in `account_mapping`** pass the ambiguity invariant (same group account twice) but would double an entry; they are caught later by the unique entry id invariant, with a less precise message.

## Drift

No domain layer exists yet (greenfield skeleton, no product SQL, adapter or generator), so there is nothing to compare: no drift findings, no `_drift/` files.

## Next stage

`/sdd:api unified-gl-inputs` — the feature has no HTTP or event contract (surface `cli`); `api`'s N/A condition («no contract change») holds, so the skip target is `/sdd:tasks unified-gl-inputs`.
