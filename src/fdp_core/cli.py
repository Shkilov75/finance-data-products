import argparse
import sys

from fdp_core import report, runner
from fdp_core.config import Config, repo_root
from fdp_core.errors import InvariantViolation


def _final_line(result: runner.RunResult, code: int) -> str:
    line = f"{len(result.gates)} gates run"
    if code == 0 and result.gates:
        names = ", ".join(result.gated_products)
        n = len(result.gates)
        wording = {1: "the gate", 2: "both gates"}.get(n, f"all {n} gates")
        line += f"; {wording} of {names} passed"
    return line


def _print_run(result: runner.RunResult) -> int:
    code = runner.exit_code(result)
    for columns, rows in result.summaries:
        print(report.render_table(columns, rows))
    for line in report.format_gate_lines(result.gates):
        print(line)
    for line in report.format_violations(result.gates):
        print(line)
    for file, count in result.exports:
        print(f"{file}: {count} records")
    for name in result.reserved:
        print(f"reserved: {name}")
    print(_final_line(result, code))
    return code


def _run(argv: list[str] | None) -> int:
    parser = argparse.ArgumentParser(prog="fdp", description="Finance data products runner")
    sub = parser.add_subparsers(dest="command", required=True)
    run_p = sub.add_parser("run", help="build the DuckDB layers and run all gates")
    run_p.add_argument("--bad", action="store_true", help="use deliberately corrupted data")
    sub.add_parser("products", help="list discovered products")
    args = parser.parse_args(argv)

    cfg = Config(root=repo_root(), bad=getattr(args, "bad", False))
    if args.command == "products":
        for p in runner.discover_products(cfg):
            print(f"{p.name}\t{p.status}")
        return 0
    return _print_run(runner.run(cfg))


def main(argv: list[str] | None = None) -> int:
    try:
        return _run(argv)
    except InvariantViolation as exc:
        print(f"invariant violation: {exc.label}", file=sys.stderr)
        for row in exc.rows:
            print("  " + " ".join("" if v is None else str(v) for v in row), file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - FdpError and anything unexpected give 3, never 1
        print(f"error: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
