"""Rendering shared by every product: tables, CSV files, gate lines."""

import csv
from pathlib import Path

from fdp_core.gates import GateResult


def _cell(value) -> str:
    return "" if value is None else str(value)


def render_table(columns: list[str], rows: list[tuple]) -> str:
    """Text table: text left-aligned, numbers right-aligned, two spaces between columns."""
    cells = [[_cell(v) for v in row] for row in rows]
    widths = [max(len(c), *(len(r[i]) for r in cells)) if cells else len(c)
              for i, c in enumerate(columns)]
    numeric = [bool(rows) and all(isinstance(r[i], (int, float)) or hasattr(r[i], "as_tuple")
                                  for r in rows) for i in range(len(columns))]

    def line(values):
        return "  ".join(v.rjust(w) if numeric[i] and values is not columns else v.ljust(w)
                         for i, (v, w) in enumerate(zip(values, widths, strict=True))).rstrip()

    return "\n".join([line(columns), *(line(r) for r in cells)])


def write_csv(path: Path, columns: list[str], rows: list[tuple]) -> None:
    """CSV with LF endings; the header is always written, even for zero rows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(columns)
        writer.writerows([[_cell(v) for v in row] for row in rows])


def format_gate_lines(results: list[GateResult]) -> list[str]:
    return [f"{r.status}\t{r.name}\t{len(r.violations)} violating rows" for r in results]


def format_violations(results: list[GateResult]) -> list[str]:
    """Every violating row of every failed gate, printed in full."""
    return ["  " + " ".join(_cell(v) for v in row)
            for r in results if r.violations for row in r.violations]
