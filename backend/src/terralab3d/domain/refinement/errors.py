"""Stable domain errors raised by the refinement capability."""


class RefinementError(Exception):
    """Base error for refinement operations."""


class RefinementValidationError(RefinementError, ValueError):
    """A refinement value violates a domain invariant."""


class GridAlignmentError(RefinementValidationError):
    """Two raster grids cannot participate in the same derived mosaic."""


class LicenseRejectedError(RefinementError):
    """A product cannot be used under the configured commercial policy."""


class RefinementPersistenceError(RefinementError):
    """Persistent refinement state could not be read or written safely."""
