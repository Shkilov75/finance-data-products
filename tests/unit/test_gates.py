import csv
import json
import shutil

import duckdb
import pytest

from fdp_core import runner
from fdp_core.config import Config, repo_root
from fdp_core.gates import FAIL, PASS, run_sql_gate

REPO = repo_root()
MANIFEST = """name = "unified_gl"
status = "active"
sql = [
  "adapters/{engine}/01_create_raw_inputs.sql",
  "adapters/{engine}/02_create_typed_views.sql",
  "adapters/{engine}/03_create_control_views.sql",
  "sql/staging/04_create_staging_ledger_entry.sql",
]
invariants = []
gates = ["gates/01_completeness.sql", "gates/02_mapping.sql"]
"""


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    target = tmp_path / "products/unified_gl"
    shutil.copytree(REPO / "products/unified_gl", target, ignore=shutil.ignore_patterns("__pycache__"))
    (target / "product.toml").write_text(MANIFEST)
    monkeypatch.chdir(tmp_path)
    return Config(root=tmp_path)


def data(cfg, name):
    return cfg.root / "products/unified_gl/data" / name


def gate(cfg, name):
    return cfg.root / "products/unified_gl/gates" / name


def messages(result):
    return [row[0] for row in result.violations]


def mutate_and_gate(cfg, sql, name="01_completeness.sql"):
    """Run clean, then change the built database with ``sql`` and run one gate on it."""
    runner.run(cfg)
    con = duckdb.connect(str(cfg.db_path))
    try:
        con.execute(sql)
        return run_sql_gate(con, gate(cfg, name))
    finally:
        con.close()


def test_both_gates_pass_on_clean_data(cfg):
    results = runner.run(cfg).gates
    assert [(r.name, r.status) for r in results] == [("01_completeness", PASS), ("02_mapping", PASS)]


def test_missing_entry_gives_count_and_total_rows_and_a_missing_row(cfg):
    result = mutate_and_gate(cfg, "DELETE FROM staging.ledger_entry WHERE entry_id = ("
                                  "SELECT entry_id FROM staging.ledger_entry "
                                  "WHERE source_system = 'ERP_A' AND signed_amount > 0 "
                                  "ORDER BY source_document, source_line LIMIT 1)")
    assert result.status == FAIL
    text = "\n".join(messages(result))
    one = next(m for m in messages(result) if "missing in aligned entries" in m)
    assert one.startswith("ERP_A BA-2026-") and " line " in one
    assert "ERP_A" in text and "entries: raw" in text and "debit_total: raw" in text
    assert "credit_total" not in text  # only a debit was removed


def test_changed_amount_is_listed_with_totals(cfg):
    result = mutate_and_gate(cfg, "UPDATE staging.ledger_entry SET signed_amount = signed_amount + 1 "
                                  "WHERE entry_id = (SELECT min(entry_id) FROM staging.ledger_entry "
                                  "WHERE source_system = 'ERP_B' AND signed_amount > 0)")
    assert result.status == FAIL
    text = "\n".join(messages(result))
    assert "signed_amount differs: raw" in text and "debit_total: raw" in text
    assert "ERP_B B0" in text


def test_swapped_amounts_keep_totals_but_both_entries_are_reported(cfg):
    runner.run(cfg)
    con = duckdb.connect(str(cfg.db_path))
    try:
        (id1, amt1), (id2, amt2) = con.execute(
            "SELECT entry_id, signed_amount FROM staging.ledger_entry WHERE source_system = 'ERP_A' "
            "AND signed_amount > 0 AND transaction_currency = 'EUR' "
            "AND signed_amount IN (SELECT signed_amount FROM staging.ledger_entry "
            "GROUP BY 1 HAVING count(*) = 1) ORDER BY entry_id LIMIT 2").fetchall()
        assert amt1 != amt2
        con.execute("UPDATE staging.ledger_entry SET signed_amount = ? WHERE entry_id = ?", [amt2, id1])
        con.execute("UPDATE staging.ledger_entry SET signed_amount = ? WHERE entry_id = ?", [amt1, id2])
        result = run_sql_gate(con, gate(cfg, "01_completeness.sql"))
    finally:
        con.close()
    msgs = messages(result)
    assert len([m for m in msgs if "signed_amount differs" in m]) == 2, msgs
    assert not any("entries: raw" in m or "total: raw" in m for m in msgs)


def test_date_and_account_differences_are_reported(cfg):
    result = mutate_and_gate(
        cfg, "UPDATE staging.ledger_entry SET entry_date = entry_date + 1, local_account = '9999' "
             "WHERE entry_id = (SELECT min(entry_id) FROM staging.ledger_entry)")
    text = "\n".join(messages(result))
    assert "entry_date differs: raw" in text and "local_account differs: raw" in text


def test_aligned_entry_without_raw_counterpart_is_a_difference(cfg):
    result = mutate_and_gate(
        cfg, "INSERT INTO staging.ledger_entry SELECT md5('x'), 'ERP_A', 'NOPE-1', 1, entry_date, "
             "signed_amount, transaction_currency, local_account, group_account, description, "
             "original_description FROM staging.ledger_entry LIMIT 1")
    text = "\n".join(messages(result))
    assert "ERP_A NOPE-1 line 1: in aligned entries but not in raw data" in text
    assert "entries: raw" in text


@pytest.mark.parametrize("bad_row", [
    "BA-9;1;31.02.2026;4660;5,00;;EUR;x",       # bad date
    "BA-9;1;06.01.2026;4660;5,00;5,00;EUR;x",   # both filled
    "BA-9;1;06.01.2026;4660;;;EUR;x",           # both empty
    "BA-9;1;06.01.2026;4660;-5,00;;EUR;x",      # negative
    "BA-9;1;06.01.2026;4660;0,00;;EUR;x",       # zero
    "BA-9;1;06.01.2026;4660;5,001;;EUR;x",      # three decimals
])
def test_unreadable_raw_entry_shows_as_missing_and_adds_no_total(cfg, bad_row):
    with data(cfg, "erp_a_export_synthetic.csv").open("a", encoding="utf-8", newline="") as fh:
        fh.write(bad_row + "\n")
    result = runner.run(cfg).gates[0]
    msgs = messages(result)
    assert result.status == FAIL
    assert "ERP_A BA-9 line 1: missing in aligned entries" in msgs
    assert any(m.startswith("ERP_A EUR entries: raw") for m in msgs)
    assert not any("total: raw" in m for m in msgs)  # nothing reached the raw totals


def test_unmapped_account_names_source_system_and_account_once(cfg):
    with data(cfg, "erp_a_export_synthetic.csv").open("a", encoding="utf-8", newline="") as fh:
        fh.write("BA-9;1;06.01.2026;7777;5,00;;EUR;x\nBA-9;2;06.01.2026;7777;;5,00;EUR;x\n")
    results = {r.name: r for r in runner.run(cfg).gates}
    assert results["01_completeness"].status == PASS  # the entry stays aligned
    mapping = results["02_mapping"]
    assert mapping.status == FAIL
    assert len(mapping.violations) == 1
    assert "ERP_A" in mapping.violations[0][0] and "7777" in mapping.violations[0][0]


def load_count_problems(con, folder):
    """Records in each committed file vs records loaded (the AC-07 load-count check)."""
    with (folder / "erp_a_export_synthetic.csv").open(encoding="utf-8", newline="") as fh:
        a_file = len(list(csv.DictReader(fh, delimiter=";")))
    docs = json.loads((folder / "erp_b_export_synthetic.json").read_text(encoding="utf-8"))
    problems = []
    if con.execute("SELECT count(*) FROM raw.erp_a_export").fetchone()[0] != a_file:
        problems.append("erp_a")
    if con.execute("SELECT count(*) FROM raw.erp_b_export").fetchone()[0] != len(docs):
        problems.append("erp_b documents")
    if con.execute("SELECT coalesce(sum(len(lines)), 0) FROM raw.erp_b_export").fetchone()[0] != sum(
            len(d["lines"]) for d in docs):
        problems.append("erp_b lines")
    return problems


def test_load_count_check_passes_on_clean_load_and_catches_a_lost_record(cfg):
    runner.run(cfg)
    con = duckdb.connect(str(cfg.db_path))
    try:
        folder = cfg.root / "products/unified_gl/data"
        assert load_count_problems(con, folder) == []
        con.execute("DELETE FROM raw.erp_a_export WHERE rowid = 0")  # a record lost while loading
        assert load_count_problems(con, folder) == ["erp_a"]
    finally:
        con.close()


def test_gate_files_are_neutral_sql():
    for path in (REPO / "products/unified_gl/gates").glob("*.sql"):
        code = "\n".join(line.split("--", 1)[0] for line in path.read_text().splitlines()).lower()
        for forbidden in ("read_csv", "read_json", "strptime", "typed_"):
            assert forbidden not in code, (path.name, forbidden)
