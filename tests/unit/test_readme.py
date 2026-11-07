import re

import duckdb

from fdp_core import runner
from fdp_core.config import Config, repo_root

ROOT = repo_root()
README = ROOT / "products/unified_gl/README.md"
INPUTS = [
    "erp_a_export_synthetic.csv",
    "erp_b_export_synthetic.json",
    "account_mapping_synthetic.csv",
    "description_translation_synthetic.csv",
    "rates_synthetic.csv",
]


def text():
    return README.read_text(encoding="utf-8")


def test_readme_documents_every_attribute_of_the_aligned_entry():
    cfg = Config(root=ROOT)
    runner.run(cfg)
    con = duckdb.connect(str(cfg.db_path), read_only=True)
    columns = [r[0] for r in con.execute("DESCRIBE staging.ledger_entry").fetchall()]
    con.close()
    assert len(columns) == 11
    section = text().split("## Aligned entries", 1)[1].split("\n## ", 1)[0]
    rows = {m.group(1) for m in re.finditer(r"^\|\s*`(\w+)`\s*\|", section, re.MULTILINE)}
    assert rows == set(columns)
    for line in section.splitlines():  # every attribute row has a meaning, not just a name
        if re.match(r"^\|\s*`\w+`", line):
            assert len(line.split("|")[-3].strip()) > 10, line


def test_readme_states_the_data_is_synthetic_and_names_the_five_files():
    top = text().split("\n## ", 1)[0].lower()
    assert "synthetic" in top and "fictitious" in top
    for name in INPUTS:
        assert name in text()


def test_readme_explains_checks_exit_codes_and_reports():
    body = text()
    for needle in ("invariant", "gate", "exceptions report", "build/", "0", "1", "2", "3",
                   "also written after a failed gate", "no CSV", "staging.ledger_entry",
                   "raw.erp_a_export", "raw.erp_b_export", "adapters/"):
        assert needle in body, needle
    assert re.search(r"exit code[s]?", body, re.IGNORECASE)


def test_readme_makes_no_databricks_compatibility_claim():
    for line in text().splitlines():
        if "databricks" in line.lower():
            assert re.search(r"not (yet )?(written|verified|implemented)|planned|unverified",
                             line, re.IGNORECASE), line


def test_readme_lists_the_five_source_differences():
    body = text().lower()
    for needle in ("date", "number", "debit", "column names", "nested"):
        assert needle in body, needle


def test_markdown_links_resolve():
    for target in re.findall(r"\]\((?!https?://|#)([^)#]+)", text()):
        assert (README.parent / target).exists(), target
