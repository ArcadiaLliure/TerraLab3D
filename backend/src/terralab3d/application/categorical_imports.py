"""Categorical scheme detection, confirmation and TLST audit models."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from terralab3d.domain.surface.categorical import (
    CategoricalEncoding,
    CategoricalRasterAnalysis,
    rgba_source_value,
)
from terralab3d.domain.surface.tlst import (
    ClassificationStatus,
    CompositeSurface,
    ObservationState,
    SampleValidity,
    SingleSurface,
    SourceClassDefinition,
    SourceScheme,
    SourceValue,
    TlstValidationError,
)
from terralab3d.application.ports.classification_schemes import (
    ClassificationSchemeRegistryPort,
)


_SLUG = re.compile(r"[^a-z0-9_]+")


@dataclass(frozen=True, slots=True)
class SchemeMatch:
    scheme_key: str
    scheme_version: str
    mapping_revision: str
    display_name: str
    matched_values: int
    total_values: int
    value_codes: Mapping[SourceValue, int]

    @property
    def exact(self) -> bool:
        return self.matched_values == self.total_values


def analyse_scheme_matches(
    analysis: CategoricalRasterAnalysis,
    registry: ClassificationSchemeRegistryPort,
) -> tuple[SchemeMatch, ...]:
    matches: list[SchemeMatch] = []
    for scheme in registry.all_schemes():
        value_codes: dict[SourceValue, int] = {}
        for observed in analysis.values:
            definition = _matching_definition(
                scheme,
                observed.source_value,
                analysis.encoding,
            )
            if definition is not None:
                value_codes[observed.source_value] = definition.source_code
        if not value_codes:
            continue
        matches.append(SchemeMatch(
            scheme_key=scheme.scheme_key,
            scheme_version=scheme.scheme_version,
            mapping_revision=scheme.mapping_revision,
            display_name=scheme.display_name,
            matched_values=len(value_codes),
            total_values=len(analysis.values),
            value_codes=value_codes,
        ))
    return tuple(sorted(
        matches,
        key=lambda value: (
            not value.exact,
            -value.matched_values,
            value.display_name,
            value.scheme_version,
        ),
    ))


def confirmed_scheme_and_codes(
    analysis: CategoricalRasterAnalysis,
    confirmation: Mapping[str, Any],
    registry: ClassificationSchemeRegistryPort,
) -> tuple[SourceScheme, dict[SourceValue, int], bool]:
    if confirmation.get("mappingConfirmed") is not True:
        raise TlstValidationError("The categorical mapping must be reviewed and confirmed")
    custom = confirmation.get("customScheme")
    created = isinstance(custom, dict)
    scheme = (
        _build_custom_scheme(analysis, custom, registry)
        if created else registry.get(
            str(confirmation.get("schemeKey", "")),
            str(confirmation.get("schemeVersion", "")),
            str(confirmation.get("mappingRevision", "")) or None,
        )
    )
    codes: dict[SourceValue, int] = {}
    for observed in analysis.values:
        definition = _matching_definition(
            scheme,
            observed.source_value,
            analysis.encoding,
        )
        if definition is None:
            raise TlstValidationError(
                f"Scheme {scheme.scheme_key}@{scheme.scheme_version} does not define "
                f"source value {observed.source_value!r}"
            )
        codes[observed.source_value] = definition.source_code
    return scheme, codes, created


def categorical_analysis_payload(
    analysis: CategoricalRasterAnalysis,
    registry: ClassificationSchemeRegistryPort,
) -> dict[str, Any]:
    matches = analyse_scheme_matches(analysis, registry)
    return {
        "encoding": analysis.encoding.value,
        "bandIndices": list(analysis.band_indices),
        "sourceDtype": analysis.source_dtype,
        "validPixels": analysis.valid_pixels,
        "invalidPixels": analysis.invalid_pixels,
        "values": [
            {
                "sourceValue": value.source_value,
                "pixelCount": value.pixel_count,
                "colorRgba": list(value.color_rgba) if value.color_rgba else None,
            }
            for value in analysis.values
        ],
        "schemeCandidates": [
            {
                "schemeKey": match.scheme_key,
                "schemeVersion": match.scheme_version,
                "mappingRevision": match.mapping_revision,
                "displayName": match.display_name,
                "matchedValues": match.matched_values,
                "totalValues": match.total_values,
                "exact": match.exact,
                "valueCodes": {
                    str(key): value for key, value in match.value_codes.items()
                },
            }
            for match in matches
        ],
    }


def scheme_catalog_payload(registry: ClassificationSchemeRegistryPort) -> dict[str, Any]:
    taxonomy = registry.taxonomy
    return {
        "taxonomyKey": taxonomy.taxonomy_key,
        "taxonomyVersion": taxonomy.taxonomy_version,
        "categories": [
            {
                "categoryKey": category.key,
                "parentKey": category.parent_key,
                "categoryLabelKey": registry.category_presentation(category.key).label_key,
                "categoryLabel": registry.category_presentation(category.key).label,
            }
            for category in taxonomy.categories
        ],
        "schemes": [scheme_audit_payload(scheme, registry) for scheme in registry.all_schemes()],
    }


def scheme_audit_payload(
    scheme: SourceScheme,
    registry: ClassificationSchemeRegistryPort,
) -> dict[str, Any]:
    return {
        "schemeKey": scheme.scheme_key,
        "schemeVersion": scheme.scheme_version,
        "mappingRevision": scheme.mapping_revision,
        "displayName": scheme.display_name,
        "sourceSemantics": scheme.source_semantics,
        "classCount": len(scheme.classes),
        "classes": [
            _class_audit_payload(definition, registry)
            for definition in scheme.classes
        ],
    }


def _class_audit_payload(
    definition: SourceClassDefinition,
    registry: ClassificationSchemeRegistryPort,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "sourceCode": definition.source_code,
        "sourceValue": definition.source_value,
        "sourceLabel": definition.source_label,
        "colorRgba": list(definition.color_rgba),
        "sampleValidity": (
            definition.sample_validity.name.lower()
            if definition.sample_validity is not None else None
        ),
        "mappingKind": "observation_state",
    }
    translation = definition.translation
    if isinstance(translation, SingleSurface):
        coverage = registry.taxonomy.hierarchy_coverage(translation.category_key)
        payload.update({
            "mappingKind": "single",
            "categoryKey": translation.category_key,
            "categoryLabel": registry.category_presentation(translation.category_key).label,
            "resolvedPath": list(coverage.resolved_path),
            "semanticDepth": coverage.semantic_depth,
            "unresolvedChildren": list(coverage.unresolved_children),
        })
    elif isinstance(translation, CompositeSurface):
        payload.update({
            "mappingKind": "composite",
            "components": [
                {
                    "categoryKey": component.surface.category_key,
                    "minimum": str(component.weight.minimum),
                    "maximum": str(component.weight.maximum),
                }
                for component in translation.components
            ],
        })
    elif isinstance(translation, ObservationState):
        payload["classificationStatus"] = translation.status.value
    return payload


def _build_custom_scheme(
    analysis: CategoricalRasterAnalysis,
    raw: Mapping[str, Any],
    registry: ClassificationSchemeRegistryPort,
) -> SourceScheme:
    display_name = str(raw.get("displayName", "")).strip()
    version = str(raw.get("schemeVersion", "")).strip()
    if not display_name or not version:
        raise TlstValidationError("A custom scheme needs a display name and version")
    requested_key = str(raw.get("schemeKey", "")).strip()
    scheme_key = requested_key or f"user.{_slug(display_name)}"
    mappings = raw.get("classes")
    if not isinstance(mappings, list):
        raise TlstValidationError("A custom scheme needs one mapping per source value")
    by_value = {
        _normalise_source_value(item.get("sourceValue")): item
        for item in mappings
        if isinstance(item, dict)
    }
    observed_values = {value.source_value for value in analysis.values}
    if set(by_value) != observed_values:
        raise TlstValidationError(
            "Custom mappings must cover every observed value exactly once"
        )

    execution_codes = _allocate_execution_codes(observed_values)
    classes = []
    for analysed in analysis.values:
        mapping = by_value[analysed.source_value]
        item: dict[str, Any] = {
            "source_code": execution_codes[analysed.source_value],
            "source_value": analysed.source_value,
            "source_label": str(
                mapping.get("sourceLabel") or analysed.source_value
            ),
            "color_rgba": list(
                analysed.color_rgba or _fallback_color(execution_codes[analysed.source_value])
            ),
        }
        for source_name, target_name in (
            ("categoryKey", "category_key"),
            ("classificationStatus", "classification_status"),
            ("sampleValidity", "sample_validity"),
        ):
            if mapping.get(source_name) is not None:
                item[target_name] = mapping[source_name]
        if sum(key in item for key in ("category_key", "classification_status", "sample_validity")) != 1:
            raise TlstValidationError(
                f"Custom value {analysed.source_value!r} needs exactly one outcome"
            )
        classes.append(item)

    revision_source = json.dumps(classes, sort_keys=True, separators=(",", ":"))
    mapping_revision = hashlib.sha256(revision_source.encode("utf-8")).hexdigest()[:16]
    definitions: list[SourceClassDefinition] = []
    for item in classes:
        translation = None
        sample_validity = None
        if "category_key" in item:
            translation = SingleSurface(str(item["category_key"]))
        elif "classification_status" in item:
            translation = ObservationState(
                ClassificationStatus(str(item["classification_status"])),
            )
        else:
            sample_validity = SampleValidity[str(item["sample_validity"]).upper()]
        definition = SourceClassDefinition(
            source_code=int(item["source_code"]),
            source_value=item["source_value"],
            source_label=str(item["source_label"]),
            color_rgba=tuple(item["color_rgba"]),
            sample_validity=sample_validity,
            translation=translation,
        )
        if translation is not None:
            registry.taxonomy.validate_translation(translation)
        definitions.append(definition)
    return SourceScheme(
        scheme_key=scheme_key,
        scheme_version=version,
        display_name=display_name,
        source_semantics="land_cover",
        mapping_revision=mapping_revision,
        taxonomy_key=registry.taxonomy.taxonomy_key,
        taxonomy_version=registry.taxonomy.taxonomy_version,
        classes=tuple(definitions),
    )


def _matching_definition(
    scheme: SourceScheme,
    source_value: SourceValue,
    encoding: CategoricalEncoding,
) -> SourceClassDefinition | None:
    try:
        return scheme.class_definition_for_value(source_value)
    except TlstValidationError:
        pass
    if encoding not in {CategoricalEncoding.RGB, CategoricalEncoding.RGBA}:
        return None
    for definition in scheme.classes:
        channels = definition.color_rgba if encoding is CategoricalEncoding.RGBA else definition.color_rgba[:3]
        if rgba_source_value(channels) == source_value:
            return definition
    return None


def _allocate_execution_codes(values: Iterable[SourceValue]) -> dict[SourceValue, int]:
    ordered = sorted(values, key=lambda value: (0, value) if isinstance(value, int) else (1, value))
    direct = {
        value: value
        for value in ordered
        if isinstance(value, int) and 0 <= value <= 0xFFFF
    }
    if len(direct) == len(ordered):
        return direct
    used = set(direct.values())
    result = dict(direct)
    candidate = 0
    for value in ordered:
        if value in result:
            continue
        while candidate in used:
            candidate += 1
        if candidate > 0xFFFF:
            raise TlstValidationError("Custom scheme has too many execution codes")
        result[value] = candidate
        used.add(candidate)
    return result


def _normalise_source_value(value: Any) -> SourceValue:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise TlstValidationError("Custom source values must be integers or strings")
    return value.strip().upper() if isinstance(value, str) else value


def _slug(value: str) -> str:
    slug = _SLUG.sub("_", value.lower()).strip("_")
    if not slug:
        raise TlstValidationError("Custom scheme name cannot produce an empty key")
    return slug


def _fallback_color(code: int) -> tuple[int, int, int, int]:
    digest = hashlib.sha256(str(code).encode("ascii")).digest()
    return (digest[0], digest[1], digest[2], 255)
