"""Lector local de RSR tabulada amb identitat, release i dates explícites."""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import re
from datetime import date
from pathlib import Path
from typing import Any

from terralab3d.domain.light_pollution.dnb_measurement import ViirsSpectralResponse


class RsrUnavailableError(Exception):
    """No hi ha una RSR de la procedència i data demanades."""


class RsrQuarantineError(Exception):
    """La taula o el manifest no compleixen el contracte declarat."""


class LocalViirsSpectralResponseRepository:
    def __init__(self, manifest_path: Path) -> None:
        self.manifest_path = Path(manifest_path)

    def _entries(self) -> list[dict[str, Any]]:
        try:
            payload = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            if payload["schemaVersion"] not in (1, 2):
                raise ValueError("Versió de manifest RSR no admesa")
            entries = payload["responses"]
            if not isinstance(entries, list):
                raise TypeError("responses no és una llista")
            return entries
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise RsrQuarantineError(f"Manifest RSR invàlid: {exc}") from exc

    def resolve(
        self,
        *,
        platform: str,
        product_id: str,
        collection: str,
        release_id: str,
        gain_stage: str,
        acquisition_date: date,
        application: str,
    ) -> ViirsSpectralResponse:
        matches = []
        try:
            for entry in self._entries():
                if not isinstance(entry, dict):
                    raise TypeError("Entrada RSR no és un objecte")
                if all(entry[key] == value for key, value in (
                    ("platform", platform), ("productId", product_id),
                    ("collection", collection), ("releaseId", release_id),
                    ("gainStage", gain_stage),
                    ("application", application),
                )) and date.fromisoformat(entry["validFrom"]) <= acquisition_date <= date.fromisoformat(entry["validThrough"]):
                    matches.append(entry)
        except (KeyError, TypeError, ValueError) as exc:
            raise RsrQuarantineError(f"Selector RSR invàlid: {exc}") from exc
        if len(matches) != 1:
            raise RsrUnavailableError("No hi ha una única RSR compatible amb producte, release i data")
        return self._load(matches[0])

    def _load(self, entry: dict[str, Any]) -> ViirsSpectralResponse:
        try:
            filename = str(entry["fileName"])
            if Path(filename).name != filename:
                raise ValueError("fileName ha de ser un nom de fitxer local")
            path = self.manifest_path.parent / filename
            expected = str(entry["localSha256"]).lower()
            if not re.fullmatch(r"[0-9a-f]{64}", expected):
                raise ValueError("SHA-256 local invàlid")
            raw = path.read_bytes()
            if not hmac.compare_digest(hashlib.sha256(raw).hexdigest(), expected):
                raise ValueError("SHA-256 local incompatible")
            wavelengths: list[float] = []
            values: list[float] = []
            for line in raw.decode("utf-8").splitlines():
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                parts = line.split()
                if len(parts) != 2:
                    raise ValueError("Fila RSR sense dues columnes")
                x, y = map(float, parts)
                if not (math.isfinite(x) and math.isfinite(y)):
                    raise ValueError("Fila RSR no finita")
                wavelengths.append(x)
                values.append(y)
            if entry["wavelengthUnit"] != "nm" or entry["responseUnit"] != "dimensionless":
                raise ValueError("Unitats RSR incompatibles")
            evidence_class = str(entry.get("evidenceClass", "diagnostic_historical"))
            l3_link_status = str(entry.get("l3LinkStatus", "unverified"))
            uncertainty_status = str(entry.get("spectralUncertaintyStatus", "unquantified"))
            gain_mapping_evidence = entry.get("gainMappingEvidence")
            if self._schema_version() == 2 and not entry.get("evidenceReference"):
                raise ValueError("Manca la referència d'evidència de la RSR")
            if l3_link_status == "verified" and not entry.get("l3LinkEvidence"):
                raise ValueError("El vincle L3 verificat necessita evidència")
            if uncertainty_status == "quantified" and not entry.get("spectralUncertaintyEvidence"):
                raise ValueError("La incertesa quantificada necessita evidència")
            return ViirsSpectralResponse(
                platform=str(entry["platform"]),
                product_id=str(entry["productId"]),
                collection=str(entry["collection"]),
                release_id=str(entry["releaseId"]),
                gain_stage=str(entry["gainStage"]),
                application=str(entry["application"]),
                valid_from=date.fromisoformat(entry["validFrom"]),
                valid_through=date.fromisoformat(entry["validThrough"]),
                wavelengths_nm=tuple(wavelengths),
                relative_response=tuple(values),
                source_url=str(entry["sourceUrl"]),
                retrieved_at=str(entry["retrievedAt"]),
                local_sha256=expected,
                redistribution_status=str(entry["redistributionStatus"]),
                evidence_class=evidence_class,
                l3_link_status=l3_link_status,
                spectral_uncertainty_status=uncertainty_status,
                gain_mapping_evidence=str(gain_mapping_evidence) if gain_mapping_evidence else None,
                source_checksum=str(entry["sourceChecksum"]) if entry.get("sourceChecksum") else None,
                source_archive_sha256=str(entry["sourceArchiveSha256"]) if entry.get("sourceArchiveSha256") else None,
                source_member=str(entry["sourceMember"]) if entry.get("sourceMember") else None,
                source_member_sha256=str(entry["sourceMemberSha256"]) if entry.get("sourceMemberSha256") else None,
                evidence_reference=str(entry["evidenceReference"]) if entry.get("evidenceReference") else None,
                l3_link_evidence=str(entry["l3LinkEvidence"]) if entry.get("l3LinkEvidence") else None,
                spectral_uncertainty_evidence=(
                    str(entry["spectralUncertaintyEvidence"])
                    if entry.get("spectralUncertaintyEvidence") else None
                ),
            )
        except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
            raise RsrQuarantineError(f"RSR incompatible: {exc}") from exc

    def _schema_version(self) -> int:
        try:
            return int(json.loads(self.manifest_path.read_text(encoding="utf-8"))["schemaVersion"])
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise RsrQuarantineError(f"Versió del manifest invàlida: {exc}") from exc
