"""Typed errors for the land-cover surface capability.

Domain errors are raised at port boundaries and never expose infrastructure
details (Rasterio, GDAL, pyproj).  Adapter code catches low-level exceptions
and re-raises the appropriate typed error before crossing the port boundary.
"""


class LandCoverError(Exception):
    """Base for all land-cover surface errors."""


class LandCoverUnavailable(LandCoverError):
    """No land-cover source could be opened or resolved."""


class LandCoverInvalidSource(LandCoverError):
    """A configured source exists but is structurally unusable."""


class LandCoverInvalidCrs(LandCoverError):
    """The source CRS is missing or cannot be transformed."""


class LandCoverUnsupportedRaster(LandCoverError):
    """The raster file exists but its format/dtype is not categorical."""


class LandCoverLegendMissing(LandCoverError):
    """The source requires a legend that is not available."""


class LandCoverSamplingCancelled(LandCoverError):
    """The sampling operation was cancelled by the caller."""


class LandCoverVersionMismatch(LandCoverError):
    """The surface resource references a terrain version that is no longer current."""
