import contextlib
import json
import shutil
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import duckdb

from fdp_core.config import LAYERS, Config
from fdp_core.errors import InvariantViolation, LayerBuildError, ManifestError
from fdp_core.gates import FAIL, GateResult, run_sql_gate
from fdp_core.report import write_csv


@dataclass
class Product:
    name: str
    status: str
    path: Path
    sql: list[str] = field(default_factory=list)
    gates: list[str] = field(default_factory=list)
    invariants: list[str] = field(default_factory=list)
    summary: str | None = None
    exports: list[dict] = field(default_factory=list)


def discover_products(cfg: Config) -> list[Product]:
    products = []
    for manifest in sorted(cfg.products_dir.glob("*/product.toml")):
        data = tomllib.loads(manifest.read_text())
        try:
            products.append(Product(
                name=data["name"],
                status=data["status"],
                path=manifest.parent,
                sql=data.get("sql", []),
                gates=data.get("gates", []),
                invariants=data.get("invariants", []),
                summary=data.get("summary"),
                exports=data.get("exports", []),
            ))
        except KeyError as exc:
            raise ManifestError(f"{manifest}: missing field {exc}") from exc
    return products


def build_layers(cfg: Config, products: list[Product] | None = None) -> duckdb.DuckDBPyConnection:
    """Phase 1: start clean (database, report, per-product build folders), create empty layers."""
    cfg.db_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.db_path.unlink(missing_ok=True)
    cfg.report_path.unlink(missing_ok=True)
    for product in products or []:
        if product.status == "active":
            shutil.rmtree(cfg.product_build_dir(product.name), ignore_errors=True)
    con = duckdb.connect(str(cfg.db_path))
    for layer in LAYERS:
        con.execute(f"CREATE SCHEMA {layer}")
    return con


def _read(cfg: Config, product: Product, rel: str) -> str:
    return (product.path / rel.replace("{engine}", cfg.engine)).read_text()


@dataclass
class RunResult:
    gates: list[GateResult] = field(default_factory=list)
    summaries: list[tuple[list[str], list[tuple]]] = field(default_factory=list)
    exports: list[tuple[str, int]] = field(default_factory=list)  # (file name, record count)
    reserved: list[str] = field(default_factory=list)
    gated_products: list[str] = field(default_factory=list)


def _query(con: duckdb.DuckDBPyConnection, sql: str) -> tuple[list[str], list[tuple]]:
    cur = con.execute(sql)
    return [d[0] for d in cur.description], cur.fetchall()


def run(cfg: Config) -> RunResult:
    # Engine files read inputs by paths relative to the repository root.
    with contextlib.chdir(cfg.root):
        return _run(cfg)


def _run(cfg: Config) -> RunResult:
    products = discover_products(cfg)
    con = build_layers(cfg, products)
    result = RunResult(reserved=sorted(p.name for p in products if p.status == "reserved"))
    active = [p for p in products if p.status == "active"]
    try:
        for product in active:
            for rel in product.sql:
                try:
                    con.execute(_read(cfg, product, rel))
                except duckdb.Error as exc:
                    raise LayerBuildError(f"{product.name}/{rel}: {exc}") from exc
            for rel in product.invariants:
                rows = con.execute(_read(cfg, product, rel)).fetchall()
                if rows:
                    raise InvariantViolation(f"{product.name}/{rel}", rows)
            result.gates += [
                run_sql_gate(con, product.path / rel.replace("{engine}", cfg.engine))
                for rel in product.gates
            ]
            if product.gates:
                result.gated_products.append(product.name)
        for product in active:  # phase 5: summary and exports
            if product.summary:
                result.summaries.append(_query(con, _read(cfg, product, product.summary)))
            for export in product.exports:
                columns, rows = _query(con, _read(cfg, product, export["query"]))
                write_csv(cfg.product_build_dir(product.name) / export["file"], columns, rows)
                result.exports.append((export["file"], len(rows)))
    finally:
        con.close()
    cfg.report_path.write_text(json.dumps(
        [{"gate": r.name, "status": r.status, "violations": len(r.violations)}
         for r in result.gates],
        indent=2))
    return result


def exit_code(results: "RunResult | list[GateResult]") -> int:
    gates = results.gates if isinstance(results, RunResult) else results
    return 1 if any(r.status == FAIL for r in gates) else 0
