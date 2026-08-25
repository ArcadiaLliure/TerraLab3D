"""Application boundaries for versioned categorical scheme lookup and storage."""

from __future__ import annotations

from typing import Any, Protocol

from terralab3d.domain.surface.tlst import SourceScheme, TaxonomyCatalog


class ClassificationSchemeRegistryPort(Protocol):
    taxonomy: TaxonomyCatalog

    def get(
        self,
        scheme_key: str,
        scheme_version: str,
        mapping_revision: str | None = None,
    ) -> SourceScheme: ...
    def all_schemes(self) -> tuple[SourceScheme, ...]: ...
    def category_presentation(self, category_key: str) -> Any: ...


class UserClassificationSchemeWriterPort(Protocol):
    def upsert(self, scheme: SourceScheme) -> None: ...
