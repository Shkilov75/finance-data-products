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
