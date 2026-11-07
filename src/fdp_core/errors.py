class FdpError(Exception):
    """Base class for unexpected faults (a failed gate is a result, not an error)."""


class ManifestError(FdpError):
    """A product.toml is missing a field or has a wrong shape."""


class LayerBuildError(FdpError):
    """A layer SQL file failed to execute."""


class InvariantViolation(FdpError):
    """An invariant SQL check returned rows: the run must stop (not a gate result)."""

    def __init__(self, invariant: str, rows: list):
        self.invariant = invariant
        self.rows = rows
        listing = "\n".join(f"  {row}" for row in rows)
        super().__init__(f"invariant {invariant} violated by {len(rows)} row(s):\n{listing}")
