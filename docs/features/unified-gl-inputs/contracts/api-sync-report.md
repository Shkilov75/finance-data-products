---
status: Draft
updated_at: "2026-11-06"
contract: cli.md
surface: cli
size: "M (from .size), route standard (from .route)"
---

# API sync report — unified-gl-inputs (CLI contract)

`target_surfaces: [cli]` was read from `sad.md`, not re-derived. Form chosen: `contracts/cli.md`. No OpenAPI and no `events.md`: there is no HTTP surface and no async flow (no message bus or external async actor in §6).

`data-model.md` is present, so fields are derived from it. `sad.md` §6 (7 flows) and `spec.md` §4/§5 found. `CONTEXT.md` read (feature and root).

## Section A — field-origins

| schema_path | origin | confidence |
|---|---|---|
| `fdp run` (command, phases) | sad.md §6 Flow 1, ADR-0003, ADR-0004; existing `src/fdp_core/cli.py` | high |
| `fdp run --bad` | existing `cli.py` (`--bad`); no spec text for this feature | medium |
| `fdp products` | existing `cli.py` | high |
| exit code 0 / 1 | sad.md §7, §8; existing `runner.exit_code` | high |
| exit code 2 | sad.md §7, §8, ADR-0003 (`InvariantViolation`, not yet in `errors.py`) | high |
| exit code 3 | sad.md §7, §8 (`FdpError` incl. existing `LayerBuildError`, `ManifestError`) | high |
| summary columns `source_system`, `transaction_currency` | data-model.md → `staging.ledger_entry` | high |
| summary columns `entries`, `debit_total`, `credit_total` | spec AC-01; derived from `signed_amount` (positive sum, negated negative sum) | high |
| gate lines `<STATUS>\t<name>\t<n> violating rows` | existing `cli.py` | high |
| completeness violating rows (system, currency, difference; system, document, line) | spec AC-08; data-model.md → `control_erp_*` | high |
| mapping violating rows (system, local account) | spec AC-10; data-model.md → `staging.ledger_entry.group_account` | high |
| `exceptions_report.csv` path `build/unified_gl/` | ADR-0004 (`build/<product>/`) | high |
| `exceptions_report.csv` columns `source_system,document,line,original_description` | spec AC-02 lists the four values; header spelling is this contract's proposal | medium |
| `exceptions_report.csv: <n> records` line | spec AC-01 («next to the report name») | high |
| reserved product lines | spec AC-13; sad.md Flow 1 | high |
| `build/report.json` entries `{gate, status, violations}` | existing `runner.run`; sad.md §7 | high |
| invariant messages (system, document, line / local account) | spec AC-06, AC-11; data-model.md access patterns | high |
| manifest keys `invariants`, `summary`, `exports`, `{engine}` | ADR-0003, ADR-0004, sad.md §5 | high |
| generator: no arguments, fixed seed | spec AC-05; sad.md Flow 3; finding F3 | high |
| generator stdout `<file>: <n> entries` | sad.md Flow 3 («number of entries per export») | medium |
| generator exit 3 on write failure | convention of exit codes (§2); not stated in sources | low |
| generated file names | data-model.md (entities), spec AC-05, AC-12 | high |
| `staging.ledger_entry` attributes | data-model.md (all 11 columns) | high |

Two `low`/`medium` rows are declared incompleteness: the generator write-failure exit and the CSV header spelling. Both are tightened by `--reconcile` or by `tasks`.

## Section B — drift findings

**Forward (contract derived correctly)**

1. **Command ↔ data-model** *(core)* — ✓. Every command either reads or writes an entity of `data-model.md` (`fdp run` builds all `raw.*` and `staging.ledger_entry`; the generator writes the five input files described by the entities). `fdp products` touches no entity by design.
2. **Exit/error code ↔ repo error definitions** *(core)* — ✓ with a note. Repo form: classes in `src/fdp_core/errors.py`. `FdpError`, `ManifestError`, `LayerBuildError` exist. `InvariantViolation` does not yet exist; it is proposed by feature ADR-0003 and is a task for `implement`, not a defect of the contract.
3. **Validation ↔ constraint** *(core)* — ✓. The contract adds no field limits of its own; amount scale, `NOT NULL` and `group_account NULL` are taken from `data-model.md`; invariant wording follows AC-06 and AC-11.
4. **CLI ↔ sequence** *(supporting)* — ✓. Exit 2 branch and exit 0 branch of Flow 1, exit 1 of Flow 2, the report files of Flow 4, the generator of Flow 3 are all in the contract. Flows 5, 6, 7 are internal to `fdp run` and appear as phases and error scenarios.

**Back-feed (coverage cross-check)**

| Check | Result |
|---|---|
| Every AC maps to ≥1 command, output or data contract | ✓ AC-01 → C1 §3.3; AC-02 → §3.2, §3.5, §7; AC-03, AC-04 → §7; AC-05 → C3; AC-06 → §3.4; AC-07, AC-08 → §3.3, §3.5; AC-09, AC-10, AC-11 → §3.5; AC-12 → §3.2, §5; AC-13 → §3.3 item 5, C2; AC-14 → §3.3 item 1, §7 |
| Every command maps to a §4 user story | ✓ C1 → US-02, 05, 06, 07; C2 → AC-13 (US-06); C3 → US-01 |
| Every §6 `alt`-branch has a response | ✓ (Flow 1 two branches, Flow 3 two nested branches, Flow 4 two, Flow 5 two + two `opt`, Flow 6 two, Flow 7 two) |
| Branch needed by the contract but absent from §6 | 2 gaps, see F2 and N1 |

## Findings and resolutions

Four flags were raised (≥3 pauses the run); three were resolved with the owner on 2026-11-06, no source file was edited.

| # | Finding | Kind | Resolution |
|---|---|---|---|
| F1 | Exit code 2 of an invariant violation collides with the `argparse` usage-error code 2 | contract vs tooling | **Accept**. Kept as in SAD §7/§8; documented in `cli.md` §2, told apart by the first stderr line |
| F2 | US-03/US-04 and AC-02/03/04 say the Reviewer «sees» aligned entries, but no command or export shows them (back-feed gap: observation channel) | back-feed | **Accept as data contract**. The Reviewer reads `staging.ledger_entry` in `build/fdp.duckdb`; stated in `cli.md` §7. A printed sample belongs to roadmap step 5. If a CSV export is wanted later it is one `exports` entry and an edit of AC-12/ADR-0004 |
| F3 | The owner of the Flow 3 input checks was left open in sad.md §6 «Flagged for design» | sequence gap | **Resolved: test suite**. Generator has no checks and no arguments (`cli.md` §5). `tasks` and `plan-tests` own the input-check tests (size, quarter, keys, balance, currencies, one rate per currency per day, file hashes) |
| N1 | Uncaught exceptions that are not `FdpError` (for example a missing input file raised outside a layer SQL file) end the process with Python's default code 1, which equals «gate failed» | supporting follow-up | Not resolved here. Recommend `implement` wraps file-reading failures in `LayerBuildError` (exit 3), as `runner.run` already does for `duckdb.Error`; verify by a test with a missing input file |
| N2 | `fdp run --bad` and `make demo-bad` exist, but corrupted data for `unified_gl` is roadmap step 4 | supporting follow-up | Contract says `--bad` is unchanged and not a gate demonstration in this feature. Owner: roadmap step 4 |

## Open questions (none blocking the contract)

| # | Question | Owner | Due |
|---|---|---|---|
| OQ-1 | Confirm the CSV header spelling of `exceptions_report.csv` (`source_system,document,line,original_description`) | `tasks` | before the exceptions-report task starts |
| OQ-2 | Wrap non-`FdpError` file-reading failures into exit 3 (N1) | `implement` | with the runner task |

## Requirements for `tasks` and `implement` (stale reports, 2026-11-06)

Found by reading `runner.py:41`: only `build/fdp.duckdb` was deleted at the start of a run, so `report.json` and `exceptions_report.csv` of an earlier run could survive an exit 2 or 3 and look current (SAD §11 risk). `cli.md` §3.1, §3.2, §3.4 and §3.6 now fix the rule (draft 0.1.0 clarified, version not bumped).

- **implement:** do the cleaning next to `cfg.db_path.unlink(...)` in `build_layers` (`runner.py:41`): delete `build/report.json` and `build/<product>/` of every active product; leave other files in `build/`.
- **tasks / plan-tests:** one test: a successful run, then a run with an ambiguous mapping (exit 2); assert that `report.json` and `exceptions_report.csv` are gone. A run ending in exit 1 must still leave fresh reports (SAD §1 override).

## Lint

`spectral` does not apply (no OpenAPI). Suggested checks instead, to be written by `plan-tests`: one test per exit code of §2, one test that the stdout of §3.3 contains the exceptions line with 0 and with n records, one test that a run leaves every committed input file byte-identical (AC-12).
