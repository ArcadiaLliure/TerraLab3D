"""Load the immutable TLST catalog and built-in categorical source schemes."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
from importlib.resources import files
from types import MappingProxyType
from typing import Any, Mapping

from terralab3d.domain.surface.tlst import (
    CategoryDefinition,
    ClassificationStatus,
    CompositeSurface,
    ObservationState,
    QualifierAssignment,
    QualifierDefinition,
    SampleValidity,
    SingleSurface,
    SourceClassDefinition,
    SourceScheme,
    SurfaceComponent,
    TaxonomyCatalog,
    TlstValidationError,
    validate_catalog_stability,
)


log = logging.getLogger("terralab3d.tlst_catalog")

_RESOURCE_DIRECTORY = "data/tlst"
_SCHEME_FILES = (
    "s2glc-europe-2017-v1.2.json",
    "worldcover-2020-v100.json",
    "worldcover-2021-v200.json",
    "copernicus-lcm10-2020-v100.json",
    "corine-land-cover-2018-v2020_20u1.json",
)
_LEGACY_SCHEME_ALIASES: Mapping[str, tuple[str, str]] = MappingProxyType(
    {"s2glc_europe_2017": ("s2glc_europe", "2017-v1.2")}
)


@dataclass(frozen=True, slots=True)
class SchemeReference:
    scheme_key: str
    scheme_version: str
    mapping_revision: str
    used_legacy_alias: str | None = None


@dataclass(frozen=True, slots=True)
class CategoryPresentation:
    label_key: str
    label: str


@dataclass(slots=True)
class LandCoverSchemeRegistry:
    taxonomy: TaxonomyCatalog
    schemes: Mapping[tuple[str, str, str], SourceScheme]
    category_presentations_ca: Mapping[str, CategoryPresentation]

    def get(
        self,
        scheme_key: str,
        scheme_version: str,
        mapping_revision: str | None = None,
    ) -> SourceScheme:
        if mapping_revision is not None:
            scheme = self.schemes.get((scheme_key, scheme_version, mapping_revision))
        else:
            matches = [
                value
                for identity, value in self.schemes.items()
                if identity[:2] == (scheme_key, scheme_version)
            ]
            scheme = matches[0] if len(matches) == 1 else None
        if scheme is None:
            raise TlstValidationError(
                "Unknown or ambiguous categorical scheme "
                f"{scheme_key!r}@{scheme_version!r} revision={mapping_revision!r}"
            )
        return scheme

    def register(self, scheme: SourceScheme) -> None:
        if (scheme.taxonomy_key, scheme.taxonomy_version) != (
            self.taxonomy.taxonomy_key,
            self.taxonomy.taxonomy_version,
        ):
            raise TlstValidationError("Source scheme references another TLST catalog")
        for definition in scheme.classes:
            if definition.translation is not None:
                self.taxonomy.validate_translation(definition.translation)
        identity = (
            scheme.scheme_key,
            scheme.scheme_version,
            scheme.mapping_revision,
        )
        mutable = dict(self.schemes)
        existing = mutable.get(identity)
        if existing is not None and existing != scheme:
            raise TlstValidationError(
                f"Mapping revision {identity!r} cannot be changed silently"
            )
        mutable[identity] = scheme
        self.schemes = MappingProxyType(mutable)

    def all_schemes(self) -> tuple[SourceScheme, ...]:
        return tuple(
            self.schemes[key]
            for key in sorted(self.schemes)
        )

    def category_presentation(self, category_key: str) -> CategoryPresentation:
        canonical = self.taxonomy.canonical_category_key(category_key)
        presentation = self.category_presentations_ca.get(canonical)
        if presentation is None:
            raise TlstValidationError(
                f"TLST category {canonical!r} has no Catalan presentation"
            )
        return presentation

    def resolve_reference(
        self,
        *,
        scheme_key: str | None,
        scheme_version: str | None,
        mapping_revision: str | None = None,
        legacy_legend_id: str | None = None,
    ) -> SchemeReference:
        key = (scheme_key or "").strip()
        version = (scheme_version or "").strip()
        legacy = (legacy_legend_id or "").strip()

        if key or version:
            if not key or not version:
                raise TlstValidationError(
                    "Categorical sources require both scheme_key and scheme_version"
                )
            scheme = self.get(key, version, mapping_revision)
            return SchemeReference(key, version, scheme.mapping_revision)

        target = _LEGACY_SCHEME_ALIASES.get(legacy)
        if target is None:
            raise TlstValidationError(
                "Categorical source has no explicit scheme_key + scheme_version"
            )
        scheme = self.get(*target)
        log.warning(
            "Deprecated categorical legend alias %s resolved to %s@%s; "
            "persist explicit scheme metadata instead",
            legacy,
            target[0],
            target[1],
        )
        return SchemeReference(
            target[0],
            target[1],
            scheme.mapping_revision,
            used_legacy_alias=legacy,
        )


@lru_cache(maxsize=1)
def load_builtin_land_cover_registry() -> LandCoverSchemeRegistry:
    taxonomy_payload = _load_json("tlst-1.0.json")
    catalog = _parse_taxonomy(taxonomy_payload)

    manifest = _load_json("published-keys-tlst-1.0.json")
    if manifest.get("taxonomy_key") != catalog.taxonomy_key:
        raise TlstValidationError("Published-key manifest belongs to another taxonomy")
    if manifest.get("taxonomy_version") != catalog.taxonomy_version:
        raise TlstValidationError("Published-key manifest version does not match the catalog")
    published_keys = frozenset(_string_list(manifest.get("category_keys"), "category_keys"))
    validate_catalog_stability(catalog, published_keys)
    if published_keys != catalog.category_keys:
        unexpected = sorted(catalog.category_keys - published_keys)
        raise TlstValidationError(
            f"TLST 1.0 contains keys missing from its published manifest: {unexpected!r}"
        )

    presentations = _parse_category_presentations(
        _load_json("tlst-labels-ca-1.0.json"), catalog,
    )

    schemes: dict[tuple[str, str, str], SourceScheme] = {}
    for filename in _SCHEME_FILES:
        scheme = _parse_scheme(_load_json(filename), catalog)
        identity = (scheme.scheme_key, scheme.scheme_version, scheme.mapping_revision)
        if identity in schemes:
            raise TlstValidationError(f"Duplicate source scheme: {identity!r}")
        schemes[identity] = scheme
    return LandCoverSchemeRegistry(
        catalog,
        MappingProxyType(schemes),
        MappingProxyType(presentations),
    )


def _parse_category_presentations(
    payload: Mapping[str, Any],
    catalog: TaxonomyCatalog,
) -> dict[str, CategoryPresentation]:
    if payload.get("taxonomy_key") != catalog.taxonomy_key:
        raise TlstValidationError("TLST presentation belongs to another taxonomy")
    if payload.get("taxonomy_version") != catalog.taxonomy_version:
        raise TlstValidationError("TLST presentation version does not match the catalog")
    if payload.get("locale") != "ca":
        raise TlstValidationError("The bundled TLST presentation must use locale 'ca'")
    raw_labels = payload.get("labels")
    if not isinstance(raw_labels, dict):
        raise TlstValidationError("TLST presentation labels must be a JSON object")

    presentations: dict[str, CategoryPresentation] = {}
    for key, label in raw_labels.items():
        if not isinstance(key, str) or not isinstance(label, str) or not label.strip():
            raise TlstValidationError("TLST presentation labels must be non-empty strings")
        canonical = catalog.canonical_category_key(key)
        if canonical != key:
            raise TlstValidationError("TLST presentations cannot be attached to aliases")
        presentations[key] = CategoryPresentation(
            label_key=f"tlst.category.{key}",
            label=label.strip(),
        )

    missing = catalog.category_keys - presentations.keys()
    unexpected = presentations.keys() - catalog.category_keys
    if missing or unexpected:
        raise TlstValidationError(
            "TLST Catalan presentation must cover the published catalog exactly: "
            f"missing={sorted(missing)!r}, unexpected={sorted(unexpected)!r}"
        )
    return presentations


def _load_json(filename: str) -> Mapping[str, Any]:
    resource = files("terralab3d").joinpath(_RESOURCE_DIRECTORY, filename)
    with resource.open("r", encoding="utf-8") as stream:
        payload = json.load(stream, object_pairs_hook=_unique_json_object)
    if not isinstance(payload, dict):
        raise TlstValidationError(f"TLST resource {filename!r} must contain a JSON object")
    return payload


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise TlstValidationError(f"Duplicate JSON key in TLST resource: {key!r}")
        result[key] = value
    return result


def _parse_taxonomy(payload: Mapping[str, Any]) -> TaxonomyCatalog:
    categories_payload = _mapping_list(payload.get("categories"), "categories")
    categories = tuple(
        CategoryDefinition(
            key=_required_string(item, "key"),
            parent_key=_optional_string(item.get("parent_key")),
            derived_qualifiers=_parse_qualifier_assignments(item.get("derived_qualifiers", {})),
        )
        for item in categories_payload
    )
    qualifiers = tuple(
        QualifierDefinition(
            key=_required_string(item, "key"),
            value_type=_required_string(item, "type"),
            applicable_categories=tuple(_string_list(item.get("applies_to"), "applies_to")),
            values=tuple(_string_list(item.get("values", []), "values")),
            minimum=_optional_decimal(item.get("minimum")),
            maximum=_optional_decimal(item.get("maximum")),
            unit=_optional_string(item.get("unit")),
        )
        for item in _mapping_list(payload.get("qualifiers"), "qualifiers")
    )
    aliases_payload = payload.get("aliases", {})
    if not isinstance(aliases_payload, dict):
        raise TlstValidationError("aliases must be a JSON object")
    aliases = {str(alias): str(target) for alias, target in aliases_payload.items()}
    return TaxonomyCatalog(
        taxonomy_key=_required_string(payload, "taxonomy_key"),
        taxonomy_version=_required_string(payload, "taxonomy_version"),
        categories=categories,
        qualifiers=qualifiers,
        aliases=aliases,
    )


def _parse_scheme(payload: Mapping[str, Any], catalog: TaxonomyCatalog) -> SourceScheme:
    taxonomy_key = _required_string(payload, "taxonomy_key")
    taxonomy_version = _required_string(payload, "taxonomy_version")
    if (taxonomy_key, taxonomy_version) != (
        catalog.taxonomy_key,
        catalog.taxonomy_version,
    ):
        raise TlstValidationError("Source scheme references an unavailable taxonomy version")

    classes: list[SourceClassDefinition] = []
    for item in _mapping_list(payload.get("classes"), "classes"):
        invalidity = item.get("sample_validity")
        translation = None
        sample_validity = None
        if invalidity is not None:
            sample_validity = _sample_validity(str(invalidity))
        else:
            translation = _parse_translation(item)
            catalog.validate_translation(translation)
        color = item.get("color_rgba")
        if not isinstance(color, list) or len(color) != 4:
            raise TlstValidationError("color_rgba must contain four channels")
        classes.append(
            SourceClassDefinition(
                source_code=_required_int(item, "source_code"),
                source_label=_required_string(item, "source_label"),
                source_label_key=_optional_string(item.get("source_label_key")),
                color_rgba=tuple(int(channel) for channel in color),  # type: ignore[arg-type]
                sample_validity=sample_validity,
                translation=translation,
                source_value=_source_value(item.get("source_value")),
            )
        )

    return SourceScheme(
        scheme_key=_required_string(payload, "scheme_key"),
        scheme_version=_required_string(payload, "scheme_version"),
        display_name=_required_string(payload, "display_name"),
        taxonomy_key=taxonomy_key,
        taxonomy_version=taxonomy_version,
        classes=tuple(classes),
        mapping_revision=str(payload.get("mapping_revision", "1")).strip(),
        source_semantics=str(payload.get("source_semantics", "land_cover")).strip(),
    )


def parse_source_scheme(
    payload: Mapping[str, Any],
    catalog: TaxonomyCatalog,
) -> SourceScheme:
    """Public parser shared by the immutable bundle and user-scheme repository."""

    return _parse_scheme(payload, catalog)


def source_scheme_to_payload(scheme: SourceScheme) -> dict[str, Any]:
    """Serialize one validated scheme without losing mapping semantics."""

    return {
        "scheme_key": scheme.scheme_key,
        "scheme_version": scheme.scheme_version,
        "display_name": scheme.display_name,
        "source_semantics": scheme.source_semantics,
        "mapping_revision": scheme.mapping_revision,
        "taxonomy_key": scheme.taxonomy_key,
        "taxonomy_version": scheme.taxonomy_version,
        "classes": [_source_class_payload(value) for value in scheme.classes],
    }


def _parse_translation(item: Mapping[str, Any]):
    status = item.get("classification_status")
    if status is not None:
        return ObservationState(ClassificationStatus(str(status)))
    components = item.get("components")
    if components is not None:
        parsed_components = []
        for component in _mapping_list(components, "components"):
            minimum = Decimal(str(component.get("minimum", component.get("weight"))))
            maximum = Decimal(str(component.get("maximum", component.get("weight"))))
            from terralab3d.domain.surface.tlst import ComponentWeight

            parsed_components.append(
                SurfaceComponent(
                    surface=SingleSurface(
                        category_key=_required_string(component, "category_key"),
                        qualifiers=_parse_qualifier_assignments(component.get("qualifiers", {})),
                    ),
                    weight=ComponentWeight(minimum, maximum),
                )
            )
        return CompositeSurface(tuple(parsed_components))
    return SingleSurface(
        category_key=_required_string(item, "category_key"),
        qualifiers=_parse_qualifier_assignments(item.get("qualifiers", {})),
    )


def _parse_qualifier_assignments(raw: Any) -> tuple[QualifierAssignment, ...]:
    if not isinstance(raw, dict):
        raise TlstValidationError("qualifiers must be a JSON object")
    assignments = []
    for key, value in raw.items():
        scalar = Decimal(str(value)) if isinstance(value, (int, float)) else str(value)
        assignments.append(QualifierAssignment(str(key), scalar))
    return tuple(assignments)


def _sample_validity(value: str) -> SampleValidity:
    normalized = value.strip().lower()
    by_name = {
        "valid": SampleValidity.VALID,
        "nodata": SampleValidity.NODATA,
        "masked": SampleValidity.MASKED,
        "outside_coverage": SampleValidity.OUTSIDE_COVERAGE,
    }
    try:
        return by_name[normalized]
    except KeyError as exc:
        raise TlstValidationError(f"Unknown SampleValidity: {value!r}") from exc


def _required_string(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise TlstValidationError(f"{key} must be a non-empty string")
    return value.strip()


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise TlstValidationError("Optional strings must be non-empty when present")
    return value.strip()


def _required_int(payload: Mapping[str, Any], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise TlstValidationError(f"{key} must be an integer")
    return value


def _optional_decimal(value: Any) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def _source_value(value: Any) -> int | str | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise TlstValidationError("source_value must be an integer or stable string")
    if isinstance(value, str) and not value.strip():
        raise TlstValidationError("source_value strings cannot be empty")
    return value.strip() if isinstance(value, str) else value


def _source_class_payload(definition: SourceClassDefinition) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source_code": definition.source_code,
        "source_value": definition.source_value,
        "source_label": definition.source_label,
        "color_rgba": list(definition.color_rgba),
    }
    if definition.source_label_key is not None:
        payload["source_label_key"] = definition.source_label_key
    if definition.sample_validity is not None:
        payload["sample_validity"] = definition.sample_validity.name.lower()
        return payload
    translation = definition.translation
    if isinstance(translation, SingleSurface):
        payload["category_key"] = translation.category_key
        if translation.qualifiers:
            payload["qualifiers"] = {
                value.key: _json_scalar(value.value)
                for value in translation.qualifiers
            }
        return payload
    if isinstance(translation, ObservationState):
        payload["classification_status"] = translation.status.value
        return payload
    if isinstance(translation, CompositeSurface):
        payload["components"] = [
            {
                "category_key": component.surface.category_key,
                "minimum": str(component.weight.minimum),
                "maximum": str(component.weight.maximum),
                **(
                    {
                        "qualifiers": {
                            value.key: _json_scalar(value.value)
                            for value in component.surface.qualifiers
                        }
                    }
                    if component.surface.qualifiers else {}
                ),
            }
            for component in translation.components
        ]
        return payload
    raise TlstValidationError("Source class has no serializable outcome")


def _json_scalar(value: Any) -> Any:
    return str(value) if isinstance(value, Decimal) else value


def _mapping_list(value: Any, name: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise TlstValidationError(f"{name} must be an array of objects")
    return value


def _string_list(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise TlstValidationError(f"{name} must be an array of non-empty strings")
    return value
