"""Throw-away product folders for runner and CLI tests."""

from fdp_core.config import Config

DEFAULT_FILES = {
    "sql/a.sql": "CREATE TABLE staging.t AS SELECT 1 AS x;",
    "gates/01_g.sql": "SELECT * FROM staging.t WHERE x = 0;",
    "invariants/ok.sql": "SELECT * FROM staging.t WHERE x = 0;",
    "invariants/bad.sql": "SELECT 'DOC1' AS document, 3 AS line FROM staging.t;",
    "invariants/bad2.sql": "CREATE TABLE staging.second_ran AS SELECT 1 AS x;"
                           " SELECT 'x' AS y FROM staging.t;",
    "adapters/duckdb/load.sql": "CREATE TABLE raw.loaded AS SELECT 7 AS v;",
    "reports/summary.sql": (
        "SELECT 'ERP_A' AS source_system, 'EUR' AS transaction_currency, 61 AS entries, "
        "CAST(48210.40 AS DECIMAL(18,2)) AS debit_total, "
        "CAST(48210.40 AS DECIMAL(18,2)) AS credit_total"
    ),
    "reports/exceptions.sql": (
        "SELECT 'ERP_A' AS source_system, 'D1' AS source_document, 1 AS source_line, "
        "'x' AS original_description WHERE 1 = 0"
    ),
}


def toml_list(items):
    return "[" + ", ".join(f'"{x}"' for x in items) + "]"


def make_product(root, *, name="demo", status="active", invariants=(), gates=("gates/01_g.sql",),
                 sql=("sql/a.sql",), files=None, summary=None, exports=(), manifest_extra=""):
    prod = root / "products" / name
    prod.mkdir(parents=True, exist_ok=True)
    defaults = dict(DEFAULT_FILES)
    defaults.update(files or {})
    for rel, text in defaults.items():
        target = prod / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    lines = [f'name = "{name}"', f'status = "{status}"', f"sql = {toml_list(sql)}",
             f"invariants = {toml_list(invariants)}", f"gates = {toml_list(gates)}"]
    if summary:
        lines.append(f'summary = "{summary}"')
    for query, file in exports:
        lines.append(f'[[exports]]\nquery = "{query}"\nfile = "{file}"')
    (prod / "product.toml").write_text("\n".join(lines) + "\n" + manifest_extra)
    return Config(root=root)


def make_reserved(root, name):
    prod = root / "products" / name
    prod.mkdir(parents=True, exist_ok=True)
    (prod / "product.toml").write_text(f'name = "{name}"\nstatus = "reserved"\n')
