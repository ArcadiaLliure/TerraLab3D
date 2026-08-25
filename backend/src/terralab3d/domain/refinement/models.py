"""Semantic models for TLST refinements.

The canonical category hierarchy remains owned by ``domain.surface.tlst`` and
its versioned JSON source.  This module only models what a refinement says
about that hierarchy; it never republishes category keys.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from terralab3d.domain.surface.tlst import (
    CompositeSurface,
    SingleSurface,
    TaxonomyCatalog,
)

from .errors import RefinementValidationError


class ObservationStatus(str, Enum):
    """Observation/validity state kept outside the categorical TLST value."""

    VALID = "valid"
    NODATA = "nodata"
    UNKNOWN = "unknown"
    UNCLASSIFIED = "unclassified"
    READ_ERROR = "read_error"
    OUTSIDE_COVERAGE = "outside_coverage"


class TranslationKind(str, Enum):
    SINGLE = "single"
    COMPOSITE = "composite"


@dataclass(frozen=True, slots=True)
class TlstTranslation:
    """Exclusive translation of one source class into canonical TLST.

    ``single`` stores the deepest authoritative node justified by the source.
    ``composite`` stores weighted components for a genuinely mixed source
    class.  The two representations are mutually exclusive by construction.
    """

    single: SingleSurface | None = None
    composite: CompositeSurface | None = None

    def __post_init__(self) -> None:
        if (self.single is None) == (self.composite is None):
            raise RefinementValidationError(
                "A TLST translation requires exactly one of single or composite"
            )

    @classmethod
    def from_single(cls, surface: SingleSurface) -> TlstTranslation:
        return cls(single=surface)

    @classmethod
    def from_composite(cls, surface: CompositeSurface) -> TlstTranslation:
        return cls(composite=surface)

    @property
    def kind(self) -> TranslationKind:
        return (
            TranslationKind.SINGLE
            if self.single is not None
            else TranslationKind.COMPOSITE
        )

    @property
    def category_keys(self) -> tuple[str, ...]:
        if self.single is not None:
            return (self.single.category_key,)
        assert self.composite is not None
        return tuple(component.surface.category_key for component in self.composite.components)

    def validate_against(self, taxonomy: TaxonomyCatalog) -> None:
        if self.single is not None:
            taxonomy.validate_translation(self.single)
            return
        assert self.composite is not None
        taxonomy.validate_translation(self.composite)
