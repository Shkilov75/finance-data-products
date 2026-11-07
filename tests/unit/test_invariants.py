import shutil

import duckdb
import pytest

from fdp_core import runner
from fdp_core.config import Config, repo_root
from fdp_core.errors import InvariantViolation

REPO = repo_root()
MANIFEST = """name = "unified_gl"
status = "active"
sql = [
  "adapters/{engine}/01_create_raw_inputs.sql",
  "adapters/{engine}/02_create_typed_views.sql",
  "adapters/{engine}/03_create_control_views.sql",
  "sql/staging/04_create_staging_ledger_entry.sql",
]
invariants = [
  "invariants/01_unique_document_and_line.sql",
  "invariants/02_unambiguous_mapping.sql",
  "invariants/03_unique_entry_id.sql",
]
gates = []
"""


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    """A throw-away copy of the product so the committed inputs are never touched."""
    target = tmp_path / "products/unified_gl"
    shutil.copytree(REPO / "products/unified_gl", target, ignore=shutil.ignore_patterns("__pycache__"))
    (target / "product.toml").write_text(MANIFEST)
    monkeypatch.chdir(tmp_path)  # adapter paths are relative to the repository root
    return Config(root=tmp_path)


def data(cfg, name):
    return cfg.root / "products/unified_gl/data" / name


def append(path, text):
    with path.open("a", encoding="utf-8", newline="") as fh:
        fh.write(text)


def expect_violation(cfg):
    with pytest.raises(InvariantViolation) as exc:
        runner.run(cfg)
    return exc.value


# Order matters: a repeated mapping row fans out the join into staging and would otherwise be
# reported as a repeated entry_id, so the mapping check runs before the entry-id check.


def test_clean_data_returns_zero_rows_for_all_three(cfg):
    runner.run(cfg)  # no exception: same account 4710 in both systems is not an error


def test_repeated_document_and_line_names_source_document_line(cfg):
    append(data(cfg, "erp_a_export_synthetic.csv"),
           "BA-2026-0001;01;06.01.2026;4660;1,00;;EUR;dup\n")
    err = expect_violation(cfg)
    assert err.label == "unique document and line"
    assert any("ERP_A" in str(r) and "BA-2026-0001" in str(r) and "1" in str(r) for r in err.rows)


def test_line_01_and_1_count_as_the_same_line(cfg):
    append(data(cfg, "erp_a_export_synthetic.csv"),
           "BA-2026-0001;1;06.01.2026;4660;1,00;;EUR;dup\n")
    assert expect_violation(cfg).label == "unique document and line"


def test_unreadable_duplicate_also_stops_the_run(cfg):
    append(data(cfg, "erp_a_export_synthetic.csv"),
           "BA-2026-0001;02;31.02.2026;4660;abc;;EUR;dup\n")
    err = expect_violation(cfg)
    assert err.label == "unique document and line"
    assert any("BA-2026-0001" in str(r) for r in err.rows)


def test_repeated_document_and_line_in_erp_b(cfg):
    path = data(cfg, "erp_b_export_synthetic.json")
    text = path.read_text(encoding="utf-8").rstrip()
    assert text.endswith("]")
    path.write_text(text[:-1].rstrip() + ',\n{"doc_id": "B000001", "posting_date": "01/06/2026", '
                    '"currency": "USD", "lines": [{"line_no": "1", "account": "4710", '
                    '"amount": "1.00", "memo": "x"}]}\n]\n', encoding="utf-8")
    err = expect_violation(cfg)
    assert err.label == "unique document and line"
    assert any("ERP_B" in str(r) and "B000001" in str(r) for r in err.rows)


def test_same_document_number_in_both_systems_is_fine(cfg):
    append(data(cfg, "erp_a_export_synthetic.csv"),
           "B000001;01;06.01.2026;4660;1,00;;EUR;ok\nB000001;02;06.01.2026;1200;;1,00;EUR;ok\n")
    runner.run(cfg)


@pytest.mark.parametrize("extra", [
    "ERP_B,4710,7000\n",   # repeated identical row
    "ERP_B,4710,6300\n",   # same account, different group account
])
def test_ambiguous_mapping_names_source_system_and_account(cfg, extra):
    append(data(cfg, "account_mapping_synthetic.csv"), extra)
    err = expect_violation(cfg)
    assert err.label == "unambiguous mapping"
    assert any("ERP_B" in str(r) and "4710" in str(r) for r in err.rows)
    assert not any("ERP_A" in str(r) for r in err.rows)


def test_repeated_entry_id_names_each_entry(cfg):
    runner.run(cfg)
    con = duckdb.connect(str(cfg.db_path))
    con.execute("INSERT INTO staging.ledger_entry SELECT entry_id, source_system, 'COPY', 9, "
                "entry_date, signed_amount, transaction_currency, local_account, group_account, "
                "description, original_description FROM staging.ledger_entry "
                "WHERE source_system = 'ERP_B' LIMIT 1")
    rows = con.execute((cfg.root / "products/unified_gl/invariants/03_unique_entry_id.sql")
                       .read_text()).fetchall()
    con.close()
    assert len(rows) == 2
    assert any("COPY" in str(r) and "9" in str(r) for r in rows)
    assert all("ERP_B" in str(r) for r in rows)


def test_identifiers_identical_in_two_runs_and_unique(cfg):
    def ids():
        runner.run(cfg)
        con = duckdb.connect(str(cfg.db_path), read_only=True)
        try:
            return [r[0] for r in con.execute(
                "SELECT entry_id FROM staging.ledger_entry ORDER BY source_system, "
                "source_document, source_line").fetchall()]
        finally:
            con.close()

    first, second = ids(), ids()
    assert first == second and len(set(first)) == len(first) > 0


def test_invariants_are_neutral_sql_without_engine_constructs():
    for path in (REPO / "products/unified_gl/invariants").glob("*.sql"):
        code = "\n".join(line.split("--", 1)[0] for line in path.read_text().splitlines()).lower()
        assert "read_" not in code and "strptime" not in code, path.name
