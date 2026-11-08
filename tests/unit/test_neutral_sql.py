"""Review F6: neutral SQL must run on Spark SQL too, which rejects VARCHAR without a length."""

import re

from fdp_core.config import repo_root

PRODUCT = repo_root() / "products/unified_gl"
NEUTRAL = [p for folder in ("sql", "gates", "invariants", "reports")
           for p in (PRODUCT / folder).rglob("*.sql")]


def test_neutral_sql_has_no_bare_varchar():
    assert NEUTRAL
    for path in NEUTRAL:
        code = "\n".join(line.split("--", 1)[0] for line in path.read_text().splitlines())
        assert not re.search(r"\bvarchar\b(?!\s*\()", code, re.IGNORECASE), path.name


def test_product_folder_has_no_rollback_scripts_or_pipeline_headers():
    """Review F7: the database is rebuilt from scratch, there is no migration tool (CLAUDE.md)."""
    assert not list(PRODUCT.rglob("*.down.sql"))
    for path in PRODUCT.rglob("*.sql"):
        text = path.read_text()
        assert "Staged DDL" not in text and "Promoted by" not in text, path.name
