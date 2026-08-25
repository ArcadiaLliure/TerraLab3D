"""Pure TLST 1.x domain contracts and validation rules.

This module deliberately knows nothing about JSON files, Rasterio, the bridge or
Three.js.  Infrastructure may construct these immutable definitions from any
versioned source, while the rules below remain deterministic and testable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum, IntEnum
from types import MappingProxyType
from typing import Mapping, TypeAlias


_PUBLIC_KEY = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*$")


class TlstValidationError(ValueError):
    """Raised when a published taxonomy or semantic value breaks its contract."""


class UnknownSourceCodeError(TlstValidationError):
    """Raised when a valid raster sample uses a code absent from its scheme."""


class SampleValidity(IntEnum):
    """Physical availability of one categorical source sample.

    Numeric values are the TLST 2-bit wire encoding only. They are not semantic
    priority values; mosaics must use ``SAMPLE_VALIDITY_MOSAIC_PRIORITY``.
    """

    OUTSIDE_COVERAGE = 0
    VALID = 1
    NODATA = 2
    MASKED = 3


SAMPLE_VALIDITY_MOSAIC_PRIORITY: Mapping[SampleValidity, int] = MappingProxyType(
    {
        SampleValidity.OUTSIDE_COVERAGE: 0,
        SampleValidity.NODATA: 1,
        SampleValidity.MASKED: 2,
        SampleValidity.VALID: 3,
    }
)


class ClassificationStatus(str, Enum):
    CLASSIFIED = "classified"
    UNKNOWN = "unknown"
    UNCLASSIFIED = "unclassified"


QualifierScalar: TypeAlias = str | Decimal
SourceValue: TypeAlias = int | str


@dataclass(frozen=True, slots=True)
class QualifierAssignment:
    key: str
    value: QualifierScalar

    def __post_init__(self) -> None:
        if not _PUBLIC_KEY.fullmatch(self.key):
            raise TlstValidationError(f"Invalid qualifier key: {self.key!r}")


@dataclass(frozen=True, slots=True)
class SingleSurface:
    category_key: str
    qualifiers: tuple[QualifierAssignment, ...] = ()

    def __post_init__(self) -> None:
        if not _PUBLIC_KEY.fullmatch(self.category_key):
            raise TlstValidationError(f"Invalid category key: {self.category_key!r}")
        keys = [qualifier.key for qualifier in self.qualifiers]
        if len(keys) != len(set(keys)):
            raise TlstValidationError("A qualifier may only be assigned once")


@dataclass(frozen=True, slots=True)
class ComponentWeight:
    minimum: Decimal
    maximum: Decimal

    def __post_init__(self) -> None:
        if self.minimum < 0 or self.maximum > 1 or self.minimum > self.maximum:
            raise TlstValidationError("Component weights must satisfy 0 <= min <= max <= 1")

    @classmethod
    def exact(cls, value: Decimal | str) -> ComponentWeight:
        decimal = value if isinstance(value, Decimal) else Decimal(value)
        return cls(decimal, decimal)


@dataclass(frozen=True, slots=True)
class SurfaceComponent:
    surface: SingleSurface
    weight: ComponentWeight


@dataclass(frozen=True, slots=True)
class CompositeSurface:
    components: tuple[SurfaceComponent, ...]

    def __post_init__(self) -> None:
        if len(self.components) < 2:
            raise TlstValidationError("A composite surface requires at least two components")
        minimum = sum((component.weight.minimum for component in self.components), Decimal(0))
        maximum = sum((component.weight.maximum for component in self.components), Decimal(0))
        if minimum > 1 or maximum < 1:
            raise TlstValidationError(
                "Composite intervals must admit a combination summing to one"
            )


@dataclass(frozen=True, slots=True)
class ObservationState:
    status: ClassificationStatus

    def __post_init__(self) -> None:
        if not isinstance(self.status, ClassificationStatus):
            raise TlstValidationError("ObservationState requires a ClassificationStatus")
        if self.status not in (
            ClassificationStatus.UNKNOWN,
            ClassificationStatus.UNCLASSIFIED,
        ):
            raise TlstValidationError(
                "ObservationState only represents unknown or unclassified samples"
            )


TranslationResult: TypeAlias = SingleSurface | CompositeSurface | ObservationState


@dataclass(frozen=True, slots=True)
class SourceClassification:
    scheme_key: str
    scheme_version: str
    source_code: int
    source_label: str
    source_label_key: str | None = None
    source_value: SourceValue | None = None

    def __post_init__(self) -> None:
        if not _PUBLIC_KEY.fullmatch(self.scheme_key):
            raise TlstValidationError(f"Invalid scheme key: {self.scheme_key!r}")
        if not self.scheme_version.strip():
            raise TlstValidationError("Scheme version is required")
        if self.source_code < 0:
            raise TlstValidationError("Source codes must be non-negative")
        if not self.source_label:
            raise TlstValidationError("The official source label is required")
        if self.source_value is not None and not isinstance(self.source_value, (int, str)):
            raise TlstValidationError("Source values must be integers or stable strings")


@dataclass(frozen=True, slots=True)
class SurfaceObservation:
    source: SourceClassification
    validity: SampleValidity
    translation: TranslationResult | None

    def __post_init__(self) -> None:
        if not isinstance(self.validity, SampleValidity):
            raise TlstValidationError("SurfaceObservation requires a SampleValidity")
        if self.validity is SampleValidity.VALID and self.translation is None:
            raise TlstValidationError("A valid sample requires a semantic translation")
        if self.validity is not SampleValidity.VALID and self.translation is not None:
            raise TlstValidationError("An invalid sample cannot carry a semantic translation")

    @property
    def classification_status(self) -> ClassificationStatus | None:
        if self.validity is not SampleValidity.VALID:
            return None
        if isinstance(self.translation, ObservationState):
            return self.translation.status
        return ClassificationStatus.CLASSIFIED


@dataclass(frozen=True, slots=True)
class QualifierDefinition:
    key: str
    value_type: str
    applicable_categories: tuple[str, ...]
    values: tuple[str, ...] = ()
    minimum: Decimal | None = None
    maximum: Decimal | None = None
    unit: str | None = None

    def __post_init__(self) -> None:
        if not _PUBLIC_KEY.fullmatch(self.key):
            raise TlstValidationError(f"Invalid qualifier definition: {self.key!r}")
        if self.value_type not in {"enum", "number", "string"}:
            raise TlstValidationError(f"Unsupported qualifier type: {self.value_type!r}")
        if self.value_type == "enum" and not self.values:
            raise TlstValidationError(f"Enum qualifier {self.key!r} has no values")
        if self.value_type == "number" and (
            self.minimum is None or self.maximum is None or self.minimum > self.maximum
        ):
            raise TlstValidationError(f"Numeric qualifier {self.key!r} needs a valid range")


@dataclass(frozen=True, slots=True)
class CategoryDefinition:
    key: str
    parent_key: str | None
    derived_qualifiers: tuple[QualifierAssignment, ...] = ()

    def __post_init__(self) -> None:
        if not _PUBLIC_KEY.fullmatch(self.key):
            raise TlstValidationError(f"Invalid category key: {self.key!r}")
        if self.parent_key is not None and not _PUBLIC_KEY.fullmatch(self.parent_key):
            raise TlstValidationError(f"Invalid parent category key: {self.parent_key!r}")


@dataclass(frozen=True, slots=True)
class TaxonomyCatalog:
    taxonomy_key: str
    taxonomy_version: str
    categories: tuple[CategoryDefinition, ...]
    qualifiers: tuple[QualifierDefinition, ...]
    aliases: Mapping[str, str] = field(default_factory=dict)
    _categories_by_key: Mapping[str, CategoryDefinition] = field(init=False, repr=False)
    _qualifiers_by_key: Mapping[str, QualifierDefinition] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.taxonomy_key != "TLST":
            raise TlstValidationError("The canonical taxonomy key must be 'TLST'")
        if not self.taxonomy_version.strip():
            raise TlstValidationError("Taxonomy version is required")

        categories_by_key = _unique_by_key(self.categories, "category")
        qualifiers_by_key = _unique_by_key(self.qualifiers, "qualifier")
        aliases = dict(self.aliases)

        for category in self.categories:
            if category.parent_key is None:
                if "." in category.key:
                    raise TlstValidationError(f"Root category {category.key!r} cannot contain dots")
                continue
            if category.parent_key not in categories_by_key:
                raise TlstValidationError(
                    f"Category {category.key!r} references missing parent {category.parent_key!r}"
                )
            if not category.key.startswith(f"{category.parent_key}."):
                raise TlstValidationError(
                    f"Category {category.key!r} is not below parent {category.parent_key!r}"
                )
            if category.key.rsplit(".", 1)[0] != category.parent_key:
                raise TlstValidationError(
                    f"Category {category.key!r} does not reference its direct parent"
                )

        self._validate_acyclic(categories_by_key)

        for qualifier in self.qualifiers:
            for category_key in qualifier.applicable_categories:
                if category_key not in categories_by_key:
                    raise TlstValidationError(
                        f"Qualifier {qualifier.key!r} references missing category {category_key!r}"
                    )

        for category in self.categories:
            for assignment in category.derived_qualifiers:
                definition = qualifiers_by_key.get(assignment.key)
                if definition is None:
                    raise TlstValidationError(
                        f"Category {category.key!r} derives unknown qualifier {assignment.key!r}"
                    )
                self._validate_qualifier_value(definition, assignment.value)

        for alias, target in aliases.items():
            if not _PUBLIC_KEY.fullmatch(alias):
                raise TlstValidationError(f"Invalid category alias: {alias!r}")
            if alias in categories_by_key:
                raise TlstValidationError(f"Alias {alias!r} reuses a published category key")
            if target not in categories_by_key:
                raise TlstValidationError(f"Alias {alias!r} targets unknown category {target!r}")

        object.__setattr__(self, "aliases", MappingProxyType(aliases))
        object.__setattr__(self, "_categories_by_key", MappingProxyType(categories_by_key))
        object.__setattr__(self, "_qualifiers_by_key", MappingProxyType(qualifiers_by_key))

    @property
    def category_keys(self) -> frozenset[str]:
        return frozenset(self._categories_by_key)

    def canonical_category_key(self, key: str) -> str:
        if key in self._categories_by_key:
            return key
        target = self.aliases.get(key)
        if target is None:
            raise TlstValidationError(f"Unknown TLST category: {key!r}")
        return target

    def validate_translation(self, translation: TranslationResult) -> None:
        if isinstance(translation, SingleSurface):
            self.validate_single_surface(translation)
            return
        if isinstance(translation, CompositeSurface):
            for component in translation.components:
                self.validate_single_surface(component.surface)
            return
        if not isinstance(translation, ObservationState):
            raise TlstValidationError(f"Unsupported translation result: {type(translation)!r}")

    def validate_single_surface(self, surface: SingleSurface) -> None:
        category_key = self.canonical_category_key(surface.category_key)
        derived = self.derived_qualifiers(category_key)
        for assignment in surface.qualifiers:
            definition = self._qualifiers_by_key.get(assignment.key)
            if definition is None:
                raise TlstValidationError(f"Unknown qualifier: {assignment.key!r}")
            if assignment.key in derived:
                relation = "redundant" if derived[assignment.key] == assignment.value else "contradictory"
                raise TlstValidationError(
                    f"Qualifier {assignment.key!r} is {relation} for category {category_key!r}"
                )
            if not any(
                category_key == prefix or category_key.startswith(f"{prefix}.")
                for prefix in definition.applicable_categories
            ):
                raise TlstValidationError(
                    f"Qualifier {assignment.key!r} does not apply to {category_key!r}"
                )
            self._validate_qualifier_value(definition, assignment.value)

    def derived_qualifiers(self, category_key: str) -> Mapping[str, QualifierScalar]:
        canonical = self.canonical_category_key(category_key)
        lineage: list[CategoryDefinition] = []
        current = self._categories_by_key[canonical]
        while True:
            lineage.append(current)
            if current.parent_key is None:
                break
            current = self._categories_by_key[current.parent_key]
        result: dict[str, QualifierScalar] = {}
        for category in reversed(lineage):
            for assignment in category.derived_qualifiers:
                result[assignment.key] = assignment.value
        return MappingProxyType(result)

    def category_lineage(self, category_key: str) -> tuple[str, ...]:
        """Return the canonical root-to-node path used by scientific audit."""

        canonical = self.canonical_category_key(category_key)
        lineage: list[str] = []
        current = self._categories_by_key[canonical]
        while True:
            lineage.append(current.key)
            if current.parent_key is None:
                break
            current = self._categories_by_key[current.parent_key]
        return tuple(reversed(lineage))

    def direct_children(self, category_key: str) -> tuple[str, ...]:
        canonical = self.canonical_category_key(category_key)
        return tuple(
            sorted(
                category.key
                for category in self.categories
                if category.parent_key == canonical
            )
        )

    def hierarchy_coverage(self, category_key: str) -> MappingHierarchyCoverage:
        """Describe exactly which TLST branch a mapping resolves.

        ``<parent>.unspecified`` remains the public TLST result, but semantically
        leaves the parent's concrete siblings unresolved.  This distinction is
        what later refinement verticals consume; it never invents a descendant.
        """

        canonical = self.canonical_category_key(category_key)
        category = self._categories_by_key[canonical]
        anchor = (
            category.parent_key
            if canonical.endswith(".unspecified") and category.parent_key is not None
            else canonical
        )
        unresolved = tuple(
            child
            for child in self.direct_children(anchor)
            if not child.endswith(".unspecified")
        )
        lineage = self.category_lineage(canonical)
        anchor_lineage = self.category_lineage(anchor)
        return MappingHierarchyCoverage(
            category_key=canonical,
            resolved_path=lineage,
            semantic_depth=len(anchor_lineage),
            unresolved_children=unresolved,
        )

    @staticmethod
    def _validate_acyclic(categories: Mapping[str, CategoryDefinition]) -> None:
        for key in categories:
            seen: set[str] = set()
            current: str | None = key
            while current is not None:
                if current in seen:
                    raise TlstValidationError(f"Category cycle detected at {current!r}")
                seen.add(current)
                current = categories[current].parent_key

    @staticmethod
    def _validate_qualifier_value(
        definition: QualifierDefinition,
        value: QualifierScalar,
    ) -> None:
        if definition.value_type == "enum":
            if not isinstance(value, str) or value not in definition.values:
                raise TlstValidationError(
                    f"Invalid value {value!r} for enum qualifier {definition.key!r}"
                )
            return
        if definition.value_type == "string":
            if not isinstance(value, str) or not value:
                raise TlstValidationError(
                    f"Qualifier {definition.key!r} requires a non-empty string"
                )
            return
        if not isinstance(value, Decimal):
            raise TlstValidationError(f"Qualifier {definition.key!r} requires a Decimal")
        assert definition.minimum is not None and definition.maximum is not None
        if value < definition.minimum or value > definition.maximum:
            raise TlstValidationError(
                f"Qualifier {definition.key!r} is outside its published range"
            )


@dataclass(frozen=True, slots=True)
class SourceClassDefinition:
    source_code: int
    source_label: str
    color_rgba: tuple[int, int, int, int]
    source_label_key: str | None = None
    sample_validity: SampleValidity | None = None
    translation: TranslationResult | None = None
    source_value: SourceValue | None = None

    def __post_init__(self) -> None:
        if self.source_code < 0:
            raise TlstValidationError("Source codes must be non-negative")
        if not self.source_label:
            raise TlstValidationError("Official source labels cannot be empty")
        if len(self.color_rgba) != 4 or any(channel < 0 or channel > 255 for channel in self.color_rgba):
            raise TlstValidationError("Source colors must be four bytes")
        has_invalidity = self.sample_validity is not None
        has_translation = self.translation is not None
        if has_invalidity == has_translation:
            raise TlstValidationError(
                "A source class must declare either invalidity or semantic translation"
            )
        if self.sample_validity is SampleValidity.VALID:
            raise TlstValidationError("Source class invalidity cannot be 'valid'")
        if self.sample_validity is not None and not isinstance(
            self.sample_validity,
            SampleValidity,
        ):
            raise TlstValidationError("Source class invalidity requires a SampleValidity")
        if self.source_value is None:
            object.__setattr__(self, "source_value", self.source_code)
        elif not isinstance(self.source_value, (int, str)):
            raise TlstValidationError("Source values must be integers or stable strings")


@dataclass(frozen=True, slots=True)
class MappingHierarchyCoverage:
    category_key: str
    resolved_path: tuple[str, ...]
    semantic_depth: int
    unresolved_children: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SourceScheme:
    scheme_key: str
    scheme_version: str
    display_name: str
    taxonomy_key: str
    taxonomy_version: str
    classes: tuple[SourceClassDefinition, ...]
    mapping_revision: str = "1"
    source_semantics: str = "land_cover"
    _classes_by_code: Mapping[int, SourceClassDefinition] = field(init=False, repr=False)
    _classes_by_value: Mapping[SourceValue, SourceClassDefinition] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not _PUBLIC_KEY.fullmatch(self.scheme_key):
            raise TlstValidationError(f"Invalid scheme key: {self.scheme_key!r}")
        if not self.scheme_version.strip() or not self.display_name.strip():
            raise TlstValidationError("Scheme version and display name are required")
        if not self.mapping_revision.strip():
            raise TlstValidationError("A source scheme mapping revision is required")
        if self.source_semantics != "land_cover":
            raise TlstValidationError("TLST source schemes must declare land_cover semantics")
        by_code: dict[int, SourceClassDefinition] = {}
        by_value: dict[SourceValue, SourceClassDefinition] = {}
        for definition in self.classes:
            if definition.source_code in by_code:
                raise TlstValidationError(
                    f"Duplicate source code {definition.source_code} in {self.scheme_key}"
                )
            by_code[definition.source_code] = definition
            assert definition.source_value is not None
            if definition.source_value in by_value:
                raise TlstValidationError(
                    f"Duplicate source value {definition.source_value!r} in {self.scheme_key}"
                )
            by_value[definition.source_value] = definition
        object.__setattr__(self, "_classes_by_code", MappingProxyType(by_code))
        object.__setattr__(self, "_classes_by_value", MappingProxyType(by_value))

    def class_definition(self, source_code: int) -> SourceClassDefinition:
        definition = self._classes_by_code.get(source_code)
        if definition is None:
            raise UnknownSourceCodeError(
                f"Code {source_code} is absent from {self.scheme_key}@{self.scheme_version}"
            )
        return definition

    def class_definition_for_value(self, source_value: SourceValue) -> SourceClassDefinition:
        definition = self._classes_by_value.get(source_value)
        if definition is None:
            raise UnknownSourceCodeError(
                f"Value {source_value!r} is absent from {self.scheme_key}@{self.scheme_version}"
            )
        return definition

    def resolve_observation(
        self,
        source_code: int,
        physical_validity: SampleValidity = SampleValidity.VALID,
    ) -> SurfaceObservation:
        definition = self.class_definition(source_code)
        source = SourceClassification(
            scheme_key=self.scheme_key,
            scheme_version=self.scheme_version,
            source_code=source_code,
            source_label=definition.source_label,
            source_label_key=definition.source_label_key,
            source_value=definition.source_value,
        )
        if physical_validity is not SampleValidity.VALID:
            return SurfaceObservation(source, physical_validity, None)
        if definition.sample_validity is not None:
            return SurfaceObservation(source, definition.sample_validity, None)
        return SurfaceObservation(source, SampleValidity.VALID, definition.translation)


def validate_catalog_stability(
    catalog: TaxonomyCatalog,
    published_keys: frozenset[str],
) -> None:
    """Protect the public 1.x key manifest from silent deletion or reuse."""

    missing = published_keys - catalog.category_keys
    if missing:
        raise TlstValidationError(
            f"Published TLST keys disappeared from {catalog.taxonomy_version}: {sorted(missing)!r}"
        )
    reused_aliases = published_keys.intersection(catalog.aliases)
    if reused_aliases:
        raise TlstValidationError(
            f"Published keys were reused as aliases: {sorted(reused_aliases)!r}"
        )


def pack_sample_validity(
    values: bytes | bytearray | memoryview,
    width: int,
    height: int,
) -> bytes:
    """Pack row-major validity values as four 2-bit samples per byte."""

    if width <= 0 or height <= 0 or len(values) != width * height:
        raise TlstValidationError("Validity dimensions do not match the sample count")
    row_bytes = (width + 3) // 4
    packed = bytearray(row_bytes * height)
    for row in range(height):
        row_offset = row * width
        packed_offset = row * row_bytes
        for column in range(width):
            raw_value = int(values[row_offset + column])
            if raw_value < 0 or raw_value > 3:
                raise TlstValidationError(f"Invalid 2-bit SampleValidity value: {raw_value}")
            packed[packed_offset + column // 4] |= raw_value << ((column % 4) * 2)
    return bytes(packed)


def unpack_sample_validity(packed: bytes, width: int, height: int) -> bytes:
    """Decode a row-aligned TLST SampleValidity buffer."""

    if width <= 0 or height <= 0:
        raise TlstValidationError("Validity dimensions must be positive")
    row_bytes = (width + 3) // 4
    if len(packed) != row_bytes * height:
        raise TlstValidationError("Packed validity length does not match its dimensions")
    result = bytearray(width * height)
    for row in range(height):
        row_offset = row * width
        packed_offset = row * row_bytes
        for column in range(width):
            result[row_offset + column] = (
                packed[packed_offset + column // 4] >> ((column % 4) * 2)
            ) & 0b11
    return bytes(result)


def _unique_by_key(values: tuple[object, ...], kind: str) -> dict[str, object]:
    result: dict[str, object] = {}
    for value in values:
        key = getattr(value, "key")
        if key in result:
            raise TlstValidationError(f"Duplicate {kind} key: {key!r}")
        result[key] = value
    return result
