import csv
import shutil
from decimal import Decimal

import duckdb
import pytest

from fdp_core import runner
from fdp_core.config import Config, repo_root

REPO = repo_root()
REPORTS = REPO / "products/unified_gl/reports"
MANIFEST = """name = "unified_gl"
status = "active"
sql = [
  "adapters/{engine}/01_create_raw_inputs.sql",
  "adapters/{engine}/02_create_typed_views.sql",
  "adapters/{engine}/03_create_control_views.sql",
  "sql/staging/04_create_staging_ledger_entry.sql",
]
"""


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    target = tmp_path / "products/unified_gl"
    shutil.copytree(REPO / "products/unified_gl", target, ignore=shutil.ignore_patterns("__pycache__"))
    (target / "product.toml").write_text(MANIFEST)
    monkeypatch.chdir(tmp_path)
    return Config(root=tmp_path)


def query(cfg, name):
    runner.run(cfg)
    con = duckdb.connect(str(cfg.db_path), read_only=True)
    try:
        cur = con.execute((REPORTS / name).read_text())
        return [d[0] for d in cur.description], cur.fetchall(), con
    finally:
        con.close()


def test_summary_columns_and_one_row_per_system_and_currency(cfg):
    columns, rows, _ = query(cfg, "summary.sql")
    assert columns == ["source_system", "transaction_currency", "entries", "debit_total",
                       "credit_total"]
    keys = [(r[0], r[1]) for r in rows]
    assert keys == sorted(keys) and len(keys) == len(set(keys))
    assert {k[0] for k in keys} == {"ERP_A", "ERP_B"}


def test_summary_currencies_equal_those_in_the_entries(cfg):
    _, rows, _ = query(cfg, "summary.sql")
    con = duckdb.connect(str(cfg.db_path), read_only=True)
    entry_keys = set(con.execute("SELECT DISTINCT source_system, transaction_currency "
                                 "FROM staging.ledger_entry").fetchall())
    con.close()
    assert {(r[0], r[1]) for r in rows} == entry_keys
    assert {r[1] for r in rows} >= {"EUR", "GBP", "USD"}


def test_summary_totals_are_exact_and_balanced(cfg):
    _, rows, _ = query(cfg, "summary.sql")
    con = duckdb.connect(str(cfg.db_path), read_only=True)
    for system, currency, entries, debit, credit in rows:
        n, d, c = con.execute(
            "SELECT count(*), coalesce(sum(signed_amount) FILTER (WHERE signed_amount > 0), 0), "
            "coalesce(-sum(signed_amount) FILTER (WHERE signed_amount < 0), 0) "
            "FROM staging.ledger_entry WHERE source_system = ? AND transaction_currency = ?",
            [system, currency]).fetchone()
        assert (entries, debit, credit) == (n, d, c)
        assert isinstance(debit, Decimal) and debit == credit  # documents balance per currency
    con.close()


def test_summary_ignores_the_rates_file(cfg):
    path = cfg.root / "products/unified_gl/data/rates_synthetic.csv"
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join(x for x in lines if ",GBP," not in x) + "\n", encoding="utf-8")
    _, rows, _ = query(cfg, "summary.sql")
    assert "GBP" in {r[1] for r in rows}  # GBP is in the entries, not taken from the rates
    path.write_text(lines[0] + "\n" + "\n".join(x for x in lines[1:] if ",USD," in x) + "\n",
                    encoding="utf-8")
    _, rows, _ = query(cfg, "summary.sql")
    assert {r[1] for r in rows} >= {"EUR", "GBP", "USD"}


def test_currency_in_rates_but_not_in_entries_is_not_listed(cfg):
    path = cfg.root / "products/unified_gl/data/rates_synthetic.csv"
    with path.open("a", encoding="utf-8", newline="") as fh:
        fh.write("2026-01-01,JPY,0.0067\n")
    _, rows, _ = query(cfg, "summary.sql")
    assert "JPY" not in {r[1] for r in rows}


def test_exceptions_columns_and_untranslated_erp_a_descriptions(cfg):
    columns, rows, _ = query(cfg, "exceptions_report.sql")
    assert columns == ["source_system", "source_document", "source_line", "original_description"]
    assert {r[3] for r in rows} == {"Bewirtung Kundentermin", "Wartungsvertrag Aufzug",
                                    "Sonderabschreibung Fuhrpark", "Rückstellung Rechtsstreit"}
    assert {r[0] for r in rows} == {"ERP_A"}
    keys = [(r[0], r[1], r[2]) for r in rows]
    assert keys == sorted(keys)


def test_exceptions_one_record_per_untranslated_entry(cfg):
    _, rows, _ = query(cfg, "exceptions_report.sql")
    con = duckdb.connect(str(cfg.db_path), read_only=True)
    n = con.execute("SELECT count(*) FROM staging.ledger_entry "
                    "WHERE description = original_description AND source_system = 'ERP_A'").fetchone()[0]
    con.close()
    assert len(rows) == n > 0


def test_exceptions_empty_when_everything_is_translated(cfg):
    path = cfg.root / "products/unified_gl/data/description_translation_synthetic.csv"
    with path.open("a", encoding="utf-8", newline="") as fh:
        for text in ("Bewirtung Kundentermin", "Wartungsvertrag Aufzug",
                     "Sonderabschreibung Fuhrpark", "Rückstellung Rechtsstreit"):
            fh.write(f"ERP_A,{text},{text} (en)\n")
    _, rows, _ = query(cfg, "exceptions_report.sql")
    assert rows == []


def test_translation_differing_only_in_case_is_untranslated(cfg):
    path = cfg.root / "products/unified_gl/data/erp_a_export_synthetic.csv"
    with path.open("a", encoding="utf-8", newline="") as fh:
        fh.write("BA-9;1;06.01.2026;4660;5,00;;EUR;MIETE BÜROGEBÄUDE\n"
                 "BA-9;2;06.01.2026;1200;;5,00;EUR;Miete Bürogebäude\n")
    _, rows, _ = query(cfg, "exceptions_report.sql")
    flagged = [r for r in rows if r[1] == "BA-9"]
    assert [(r[2], r[3]) for r in flagged] == [(1, "MIETE BÜROGEBÄUDE")]


def test_exceptions_csv_round_trip_through_the_core_writer(cfg, tmp_path):
    from fdp_core.report import write_csv
    columns, rows, _ = query(cfg, "exceptions_report.sql")
    out = tmp_path / "x.csv"
    write_csv(out, columns, rows)
    with out.open(encoding="utf-8", newline="") as fh:
        assert len(list(csv.reader(fh))) == len(rows) + 1


def test_report_queries_are_neutral_sql():
    for path in REPORTS.glob("*.sql"):
        code = "\n".join(line.split("--", 1)[0] for line in path.read_text().splitlines()).lower()
        for forbidden in ("read_csv", "read_json", "strptime", "typed_", "raw.description"):
            if path.name == "exceptions_report.sql" and forbidden == "raw.description":
                continue
            assert forbidden not in code, (path.name, forbidden)


def test_empty_translation_target_stays_untranslated_and_in_the_report(cfg):
    path = cfg.root / "products/unified_gl/data/description_translation_synthetic.csv"
    with path.open("a", encoding="utf-8", newline="") as fh:
        fh.write("ERP_A,Bewirtung Kundentermin,\n")
    _, rows, _ = query(cfg, "exceptions_report.sql")
    assert "Bewirtung Kundentermin" in {r[3] for r in rows}
    assert len(rows) == 9  # same as without the empty row: nothing disappears from the report
