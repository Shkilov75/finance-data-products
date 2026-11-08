import contextlib
import hashlib
import io

import duckdb
import pytest

from fdp_core import cli
from fdp_core.config import Config, repo_root

ROOT = repo_root()
INPUT_DIR = ROOT / "products/unified_gl/data"


def tree_snapshot():
    """Hash of every tracked-looking file outside build/ and caches."""
    skip = {"build", ".venv", ".git", "__pycache__", ".pytest_cache", ".ruff_cache", ".claude"}
    snap = {}
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and not skip & set(path.relative_to(ROOT).parts):
            if "egg-info" in str(path):
                continue
            snap[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return snap


@pytest.fixture(scope="session")
def run_once():
    """One real `fdp run` from the repository root; files before and after are compared."""
    before = tree_snapshot()
    out = io.StringIO()
    with contextlib.chdir(ROOT), contextlib.redirect_stdout(out):
        code = cli.main(["run"])
    after = tree_snapshot()
    return {"code": code, "lines": out.getvalue().splitlines(), "before": before, "after": after}


@pytest.fixture(scope="module")
def db(run_once):  # module scope: the file is rebuilt by tests that run after this module
    con = duckdb.connect(str(Config(root=ROOT).db_path), read_only=True)
    yield con
    con.close()
