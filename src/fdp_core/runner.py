import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import duckdb

from fdp_core.config import LAYERS, Config
from fdp_core.errors import LayerBuildError, ManifestError
from fdp_core.gates import FAIL, GateResult, run_sql_gate


@dataclass
class Product:
    name: str
    status: str
    path: Path
    sql: list[str] = field(default_factory=list)
    gates: list[str] = field(default_factory=list)


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
            ))
        except KeyError as exc:
            raise ManifestError(f"{manifest}: missing field {exc}") from exc
    return products


def build_layers(cfg: Config) -> duckdb.DuckDBPyConnection:
    cfg.db_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.db_path.unlink(missing_ok=True)
    con = duckdb.connect(str(cfg.db_path))
    for layer in LAYERS:
        con.execute(f"CREATE SCHEMA {layer}")
    return con


def run(cfg: Config) -> list[GateResult]:
    con = build_layers(cfg)
    results: list[GateResult] = []
    for product in discover_products(cfg):
        if product.status != "active":
            continue
        for rel in product.sql:
            try:
                con.execute((product.path / rel).read_text())
            except duckdb.Error as exc:
                raise LayerBuildError(f"{product.name}/{rel}: {exc}") from exc
        results += [run_sql_gate(con, product.path / rel) for rel in product.gates]
    con.close()
    cfg.report_path.write_text(json.dumps(
        [{"gate": r.name, "status": r.status, "violations": len(r.violations)} for r in results],
        indent=2))
    return results


def exit_code(results: list[GateResult]) -> int:
    return 1 if any(r.status == FAIL for r in results) else 0
