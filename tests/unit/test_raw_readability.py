"""Review F1 (AC-06, AC-08, AC-09): unreadable raw values go through the real CSV load path."""

import shutil

import pytest

from fdp_core import runner
from fdp_core.config import Config, repo_root
from fdp_core.errors import InvariantViolation
from fdp_core.gates import FAIL

REPO = repo_root()
MANIFEST = """name = "unified_gl"
status = "active"
sql = [
  "adapters/{engine}/01_create_raw_inputs.sql",
  "adapters/{engine}/02_create_typed_views.sql",
  "adapters/{engine}/03_create_control_views.sql",
  "sql/staging/04_create_staging_ledger_entry.sql",
]
invariants = ["invariants/01_unique_document_and_line.sql"]
gates = ["gates/01_completeness.sql"]
"""


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    target = tmp_path / "products/unified_gl"
    shutil.copytree(REPO / "products/unified_gl", target, ignore=shutil.ignore_patterns("__pycache__"))
    (target / "product.toml").write_text(MANIFEST)
    monkeypatch.chdir(tmp_path)
    return Config(root=tmp_path)


def add_rows(cfg, *rows):
    path = cfg.root / "products/unified_gl/data/erp_a_export_synthetic.csv"
    with path.open("a", encoding="utf-8", newline="") as fh:
        fh.write("".join(row + "\n" for row in rows))


def add_b_documents(cfg, *documents):
    import json
    path = cfg.root / "products/unified_gl/data/erp_b_export_synthetic.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data.extend(documents)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def b_doc(doc_id="B9", line_no="1", currency="USD", amount="5.00"):
    return {"doc_id": doc_id, "posting_date": "01/06/2026", "currency": currency,
            "lines": [{"line_no": line_no, "account": "4710", "amount": amount, "memo": "x"}]}


@pytest.mark.parametrize("row, missing", [
    ("BA-9;1.5;06.01.2026;4660;5,00;;EUR;x", "ERP_A BA-9 line 1.5: missing in aligned entries"),
    (";01;06.01.2026;4660;5,00;;EUR;x", "ERP_A ? line 1: missing in aligned entries"),
    ("BA-9;1;6.1.2026;4660;5,00;;EUR;x", "ERP_A BA-9 line 1: missing in aligned entries"),
    ("BA-9;1;06.01.26;4660;5,00;;EUR;x", "ERP_A BA-9 line 1: missing in aligned entries"),
    ("BA-9;1;06.01.2026;4660;12.5;;EUR;x", "ERP_A BA-9 line 1: missing in aligned entries"),
    ("BA-9;1;06.01.2026;4660;1.23,45;;EUR;x", "ERP_A BA-9 line 1: missing in aligned entries"),
])
def test_unreadable_value_is_a_named_missing_entry_and_adds_no_raw_total(cfg, row, missing):
    add_rows(cfg, row)
    result = runner.run(cfg).gates[0]
    messages = [r[0] for r in result.violations]
    assert result.status == FAIL
    assert missing in messages
    assert not any("total: raw" in m for m in messages)
    assert all(m for m in messages)  # no blank message


def test_two_unreadable_lines_of_one_document_are_told_apart(cfg):
    add_rows(cfg, "BA-9;1.5;06.01.2026;4660;5,00;;EUR;a", "BA-9;+1;06.01.2026;4660;5,00;;EUR;b")
    messages = [r[0] for r in runner.run(cfg).gates[0].violations]
    assert "ERP_A BA-9 line 1.5: missing in aligned entries" in messages
    assert "ERP_A BA-9 line +1: missing in aligned entries" in messages
    assert not any("line ?" in m for m in messages)


def test_duplicate_with_unreadable_line_stops_the_run(cfg):
    add_rows(cfg, "BA-9;x;06.01.2026;4660;5,00;;EUR;a", "BA-9;x;06.01.2026;4660;5,00;;EUR;b")
    with pytest.raises(InvariantViolation) as exc:
        runner.run(cfg)
    assert exc.value.label == "unique document and line"
    assert any("ERP_A BA-9 line x appears 2 times" in str(r) for r in exc.value.rows)


def test_duplicate_with_empty_document_stops_the_run_and_names_the_offender(cfg):
    add_rows(cfg, ";01;06.01.2026;4660;5,00;;EUR;a", ";01;06.01.2026;4660;5,00;;EUR;b")
    with pytest.raises(InvariantViolation) as exc:
        runner.run(cfg)
    assert any("ERP_A ? line 1 appears 2 times" in str(r) for r in exc.value.rows)


# --- review round 2, G2: ERP B and currency through the real load path -----------------------

def test_erp_b_empty_document_is_not_in_the_raw_totals_and_is_named(cfg):
    add_b_documents(cfg, b_doc(doc_id="", amount="5.00"))
    messages = [r[0] for r in runner.run(cfg).gates[0].violations]
    assert "ERP_B ? line 1: missing in aligned entries" in messages
    assert not any("total: raw" in m for m in messages)
    assert all(m for m in messages)


def test_erp_b_duplicate_with_unreadable_line_stops_the_run(cfg):
    add_b_documents(cfg, b_doc(line_no="x"), b_doc(line_no="x"))
    with pytest.raises(InvariantViolation) as exc:
        runner.run(cfg)
    assert exc.value.label == "unique document and line"
    assert any("ERP_B B9 line x appears 2 times" in str(r) for r in exc.value.rows)


def test_erp_b_duplicate_with_empty_document_stops_the_run(cfg):
    add_b_documents(cfg, b_doc(doc_id=""), b_doc(doc_id=""))
    with pytest.raises(InvariantViolation) as exc:
        runner.run(cfg)
    assert any("ERP_B ? line 1 appears 2 times" in str(r) for r in exc.value.rows)


def test_empty_currency_is_a_gate_finding_with_a_readable_message_not_an_engine_error(cfg):
    add_rows(cfg, "BA-9;1;06.01.2026;4660;5,00;;;x")
    result = runner.run(cfg).gates[0]
    messages = [r[0] for r in result.violations]
    assert result.status == FAIL
    assert "ERP_A UNKNOWN entries: raw 1, aligned 0" in messages
    assert "ERP_A BA-9 line 1: missing in aligned entries" in messages
    assert all(m for m in messages)
