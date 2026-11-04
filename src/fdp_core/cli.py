import argparse
import sys

from fdp_core import runner
from fdp_core.config import Config, repo_root


def main(argv: list[str] | None = None) -> int:
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

    results = runner.run(cfg)
    for r in results:
        print(f"{r.status}\t{r.name}\t{len(r.violations)} violating rows")
    print(f"{len(results)} gates run")
    return runner.exit_code(results)


if __name__ == "__main__":
    sys.exit(main())
