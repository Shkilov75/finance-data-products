class FdpError(Exception):
    """Base class for unexpected faults (a failed gate is a result, not an error)."""


class ManifestError(FdpError):
    """A product.toml is missing a field or has a wrong shape."""


class LayerBuildError(FdpError):
    """A layer SQL file failed to execute."""
