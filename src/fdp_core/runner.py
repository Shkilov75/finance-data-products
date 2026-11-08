import contextlib
import json
import re
import shutil
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import duckdb

from fdp_core.config import LAYERS, Config
from fdp_core.errors import FdpError, InvariantViolation, LayerBuildError, ManifestError
from fdp_core.gates import FAIL, GateResult, run_sql_gate
from fdp_core.report import write_csv

NAME_PATTERN = re.compile(r"[a-z0-9_]+")
EXPORT_FILE_PATTERN = re.compile(r"[A-Za-z0-9_.-]+")
STATUSES = ("active", "reserved")
MANIFEST_KEYS = {"name", "status", "sql", "gates", "invariants", "summary", "exports"}
EXPORT_KEYS = {"query", "file"}


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


def _check_inside(manifest: Path, product: Product, rel: object, what: str) -> None:
    """A manifest path must stay in its own product folder (products never share SQL)."""
    if not isinstance(rel, str) or not rel:
        raise ManifestError(f"{manifest}: {what} must be a non-empty path")
    folder = product.path.resolve()
    try:
        inside = (folder / rel.replace("{engine}", "engine")).resolve().is_relative_to(folder)
    except (OSError, ValueError, RuntimeError) as exc:  # a NUL in the text, a symlink loop
        raise ManifestError(f"{manifest}: {what} {rel!r}: {exc}") from exc
    if not inside:
        raise ManifestError(f"{manifest}: {what} {rel!r} must stay inside the product folder")


def _parse_manifest(manifest: Path) -> Product:
    try:
        data = tomllib.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise ManifestError(f"{manifest}: {exc}") from exc
    unknown = sorted(set(data) - MANIFEST_KEYS)
    if unknown:  # a misspelled key would silently switch a phase off
        raise ManifestError(f"{manifest}: unknown key {', '.join(map(repr, unknown))}")
    try:
        product = Product(
            name=data["name"],
            status=data["status"],
            path=manifest.parent,
            sql=data.get("sql", []),
            gates=data.get("gates", []),
            invariants=data.get("invariants", []),
            summary=data.get("summary"),
            exports=data.get("exports", []),
        )
    except KeyError as exc:
        raise ManifestError(f"{manifest}: missing field {exc}") from exc
    if not isinstance(product.name, str) or not NAME_PATTERN.fullmatch(product.name):
        raise ManifestError(f"{manifest}: name {product.name!r} must match [a-z0-9_]+")
    if product.status not in STATUSES:
        raise ManifestError(
            f"{manifest}: status {product.status!r} must be one of {', '.join(STATUSES)}")
    for key in ("sql", "gates", "invariants"):
        files = getattr(product, key)
        if not isinstance(files, list) or not all(isinstance(f, str) for f in files):
            raise ManifestError(f"{manifest}: {key} must be a list of file paths")
        for rel in files:
            _check_inside(manifest, product, rel, key)
    if product.summary is not None:
        _check_inside(manifest, product, product.summary, "summary")
    if not isinstance(product.exports, list) or not all(isinstance(e, dict) for e in product.exports):
        raise ManifestError(f"{manifest}: exports must be a list of tables")
    files_seen: set[str] = set()
    for export in product.exports:
        for key in ("query", "file"):
            if key not in export:
                raise ManifestError(f"{manifest}: export without {key!r}")
        unknown = sorted(set(export) - EXPORT_KEYS)
        if unknown:
            raise ManifestError(f"{manifest}: unknown key {', '.join(map(repr, unknown))} in exports")
        _check_inside(manifest, product, export["query"], "export query")
        name = export["file"]
        if (not isinstance(name, str) or not EXPORT_FILE_PATTERN.fullmatch(name)
                or name in (".", "..")):
            raise ManifestError(
                f"{manifest}: export file {name!r} must be a plain file name "
                f"(letters, digits, _ . -), written into build/{product.name}")
        if name.casefold() in files_seen:  # two names of one file on a case-insensitive file system
            raise ManifestError(f"{manifest}: export file {name!r} is listed twice")
        files_seen.add(name.casefold())
    return product


def discover_products(cfg: Config) -> list[Product]:
    return [_parse_manifest(m) for m in sorted(cfg.products_dir.glob("*/product.toml"))]


def _remove(path: Path) -> None:
    """Remove a file, a symlink (never followed) or a folder; a real failure is not hidden."""
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def _is_reserved(folder: Path) -> bool:
    """True only when the manifest is readable and says reserved; anything else is cleaned."""
    try:
        return _parse_manifest(folder / "product.toml").status == "reserved"
    except (OSError, tomllib.TOMLDecodeError, FdpError):
        return False


def _clear_earlier_run(cfg: Config) -> None:
    """Phase 0: nothing of an earlier run survives, whatever happens next (cli.md 3.1, 3.4).

    The build folder of a reserved product is not touched (cli.md 3.1)."""
    cfg.db_path.unlink(missing_ok=True)
    cfg.report_path.unlink(missing_ok=True)
    if cfg.products_dir.is_dir():
        for folder in cfg.products_dir.iterdir():
            if folder.is_dir() and not _is_reserved(folder):
                _remove(cfg.product_build_dir(folder.name))


def build_layers(cfg: Config, products: list[Product] | None = None) -> duckdb.DuckDBPyConnection:
    """Phase 1: start clean (database, report, per-product build folders), create empty layers."""
    cfg.db_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.db_path.unlink(missing_ok=True)
    cfg.report_path.unlink(missing_ok=True)
    for product in products or []:
        if product.status == "active":
            _remove(cfg.product_build_dir(product.name))
    con = duckdb.connect(str(cfg.db_path))
    for layer in LAYERS:
        con.execute(f"CREATE SCHEMA {layer}")
    return con


def _resolve(cfg: Config, product: Product, rel: str) -> Path:
    """The file a manifest path names for the real engine, checked again after {engine} is filled in
    (a symlinked engine folder must not lead out of the product)."""
    path = product.path / rel.replace("{engine}", cfg.engine)
    if not path.resolve().is_relative_to(product.path.resolve()):
        raise ManifestError(
            f"{product.path / 'product.toml'}: {rel!r} must stay inside the product folder")
    return path


def _read(cfg: Config, product: Product, rel: str) -> str:
    return _resolve(cfg, product, rel).read_text()


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


@contextlib.contextmanager
def _in_file(product: Product, rel: str):
    """An engine error while running one SQL file is reported with product and file name (exit 3)."""
    try:
        yield
    except duckdb.Error as exc:
        raise LayerBuildError(f"{product.name}/{rel}: {exc}") from exc


def _export_target(cfg: Config, product: Product, export: dict) -> Path:
    build = (cfg.root / "build").resolve()
    folder = cfg.product_build_dir(product.name).resolve()
    target = (folder / export["file"]).resolve()
    if folder.parent != build or target.parent != folder:
        raise ManifestError(
            f"{product.path / 'product.toml'}: export file {export['file']!r} "
            f"must stay inside build/{product.name}")
    return target


def run(cfg: Config) -> RunResult:
    # Engine files read inputs by paths relative to the repository root.
    with contextlib.chdir(cfg.root):
        return _run(cfg)


def _run(cfg: Config) -> RunResult:
    _clear_earlier_run(cfg)
    products = discover_products(cfg)
    con = build_layers(cfg, products)
    result = RunResult(reserved=sorted(p.name for p in products if p.status == "reserved"))
    active = [p for p in products if p.status == "active"]
    try:
        for product in active:
            for rel in product.sql:
                with _in_file(product, rel):
                    con.execute(_read(cfg, product, rel))
            for rel in product.invariants:
                with _in_file(product, rel):
                    rows = con.execute(_read(cfg, product, rel)).fetchall()
                if rows:
                    raise InvariantViolation(f"{product.name}/{rel}", rows)
            for rel in product.gates:
                with _in_file(product, rel):
                    result.gates.append(run_sql_gate(con, _resolve(cfg, product, rel)))
            if product.gates:
                result.gated_products.append(product.name)
        pending = []  # phase 5: run every query first, write files only when all succeeded
        for product in active:
            if product.summary:
                with _in_file(product, product.summary):
                    result.summaries.append(_query(con, _read(cfg, product, product.summary)))
            for export in product.exports:
                target = _export_target(cfg, product, export)
                with _in_file(product, export["query"]):
                    columns, rows = _query(con, _read(cfg, product, export["query"]))
                pending.append((target, columns, rows, export["file"]))
        for target, columns, rows, file in pending:
            write_csv(target, columns, rows)
            result.exports.append((file, len(rows)))
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
