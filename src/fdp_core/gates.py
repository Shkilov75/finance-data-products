from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import duckdb

PASS = "PASS"
FAIL = "FAIL"


@dataclass
class GateResult:
    name: str
    status: str
    violations: list = field(default_factory=list)


def run_sql_gate(con: duckdb.DuckDBPyConnection, path: Path) -> GateResult:
    """A SQL gate passes when its query returns zero rows."""
    rows = con.execute(path.read_text()).fetchall()
    return GateResult(path.stem, PASS if not rows else FAIL, rows)


def run_python_gate(name: str, check: Callable[[duckdb.DuckDBPyConnection], list],
                    con: duckdb.DuckDBPyConnection) -> GateResult:
    """A Python gate returns the violating rows; empty means PASS."""
    rows = check(con)
    return GateResult(name, PASS if not rows else FAIL, rows)
