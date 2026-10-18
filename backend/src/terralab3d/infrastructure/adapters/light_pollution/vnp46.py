"""Lectura estricta i cancel·lable d'observacions VNP46A2.002 HDF-EOS5."""

from __future__ import annotations

import hashlib
import hmac
import math
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Callable, Iterator

import h5py
import numpy as np

from terralab3d.domain.light_pollution.vnp46 import (
    Vnp46Observation,
    Vnp46Policy,
    Vnp46Provenance,
)


class Vnp46UnavailableError(Exception):
    """No hi ha observació del dia sol·licitat; no se n'interpola cap."""


class Vnp46QuarantineError(Exception):
    """El fitxer existeix, però el contracte no en permet la interpretació."""


class Vnp46CancelledError(Exception):
    """La lectura s'ha interromput i el fitxer es tanca."""


_GRANULE_NAME = re.compile(
    r"^(?P<product>VNP46A2|VJ146A2)\.A(?P<year>\d{4})(?P<doy>\d{3})\.h\d{2}v\d{2}\."
    r"(?P<collection>\d{3})\.\d+\.h5$"
)
_FIELDS = "HDFEOS/GRIDS/VIIRS_Grid_DNB_2d/Data Fields"
_FILE_ATTRIBUTES = "HDFEOS/ADDITIONAL/FILE_ATTRIBUTES"


def _text(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if isinstance(value, np.ndarray):
        if value.size != 1:
            raise Vnp46QuarantineError("Atribut escalar amb cardinalitat inesperada")
        return _text(value.reshape(-1)[0])
    return str(value)


def _text_list(value: object) -> tuple[str, ...]:
    if isinstance(value, np.ndarray):
        parts = (_text(item) for item in value.reshape(-1))
    else:
        parts = (_text(value),)
    return tuple(item.strip() for part in parts for item in part.split(",") if item.strip())


class Vnp46GranuleAdapter:
    """Llegeix píxels o finestres sense copiar tot el ràster a memòria.

    La descàrrega/cache és responsabilitat d'un proveïdor de recursos. Cal
    passar-ne el SHA-256 esperat abans de llegir cap píxel, i usar ``with`` per
    garantir el tancament del fitxer HDF5.
    """

    def __init__(
        self,
        path: Path,
        *,
        policy: Vnp46Policy,
        expected_sha256: str,
        source_url: str | None = None,
        cancelled: Callable[[], bool] | None = None,
    ) -> None:
        self.path = Path(path)
        self.policy = policy
        self.expected_sha256 = expected_sha256.lower()
        self.source_url = source_url
        self.cancelled = cancelled
        self._file: h5py.File | None = None
        self._acquisition_date: date | None = None
        self._provenance: Vnp46Provenance | None = None
        self._fill_value: float | None = None

    def _check_cancelled(self) -> None:
        if self.cancelled is not None and self.cancelled():
            raise Vnp46CancelledError("Lectura VNP46 cancel·lada")

    def _verify_sha256(self) -> None:
        if not re.fullmatch(r"[0-9a-f]{64}", self.expected_sha256):
            raise Vnp46QuarantineError("Falta una suma SHA-256 esperada vàlida")
        digest = hashlib.sha256()
        with self.path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                self._check_cancelled()
                digest.update(chunk)
        self._check_cancelled()
        if not hmac.compare_digest(digest.hexdigest(), self.expected_sha256):
            raise Vnp46QuarantineError("SHA-256 del grànul incompatible")

    def _global_attribute(self, name: str, *, required: bool = False) -> str | None:
        assert self._file is not None
        stores = [self._file.attrs]
        if _FILE_ATTRIBUTES in self._file:
            stores.append(self._file[_FILE_ATTRIBUTES].attrs)
        values = [_text(store[name]).strip() for store in stores if name in store]
        if not values:
            if required:
                raise Vnp46QuarantineError(f"Falta l'atribut global {name}")
            return None
        if not values[0] or any(value != values[0] for value in values[1:]):
            raise Vnp46QuarantineError(f"Atribut global incompatible: {name}")
        return values[0]

    def _global_list_attribute(self, name: str) -> tuple[str, ...]:
        assert self._file is not None
        stores = [self._file.attrs]
        if _FILE_ATTRIBUTES in self._file:
            stores.append(self._file[_FILE_ATTRIBUTES].attrs)
        values = [_text_list(store[name]) for store in stores if name in store]
        if any(value != values[0] for value in values[1:]):
            raise Vnp46QuarantineError(f"Atribut global incompatible: {name}")
        return values[0] if values else ()

    def _dataset(self, name: str) -> h5py.Dataset:
        assert self._file is not None
        path = f"{_FIELDS}/{name}"
        if path not in self._file:
            raise Vnp46QuarantineError(f"Falta la capa obligatòria {name}")
        node = self._file[path]
        if not isinstance(node, h5py.Dataset):
            raise Vnp46QuarantineError(f"La capa {name} no és un dataset")
        return node

    def _validate(self) -> None:
        assert self._file is not None
        name = _GRANULE_NAME.fullmatch(self.path.name)
        if name is None or name.group("collection") != self.policy.collection or name.group("product") != self.policy.product_id:
            raise Vnp46QuarantineError("Producte o col·lecció incompatibles al nom del grànul")
        year = int(name.group("year"))
        day_of_year = int(name.group("doy"))
        acquisition = date(year, 1, 1) + timedelta(days=day_of_year - 1)
        if acquisition.year != year or day_of_year < 1:
            raise Vnp46QuarantineError("Dia julià invàlid al nom del grànul")
        self._acquisition_date = acquisition

        for attribute in self.policy.required_granule_attributes:
            self._global_attribute(attribute, required=True)
        if self._global_attribute("LocalGranuleID") != self.path.name:
            raise Vnp46QuarantineError("LocalGranuleID no coincideix amb el fitxer")
        if self._global_attribute("RangeBeginningDate") != acquisition.isoformat():
            raise Vnp46QuarantineError("La data d'adquisició no coincideix amb el grànul")
        if self._global_attribute("RangeEndingDate") != acquisition.isoformat():
            raise Vnp46QuarantineError("El període del grànul no és un dia exacte")
        short_name = self._global_attribute("ShortName")
        if short_name is not None and short_name != self.policy.product_id:
            raise Vnp46QuarantineError("ShortName incompatible")
        platform = self._global_attribute("PlatformShortName")
        expected_platforms = {"VNP46A2": {"SUOMI-NPP"}, "VJ146A2": {"JPSS-1", "NOAA-20"}}
        if platform is not None and platform.upper() not in expected_platforms.get(self.policy.product_id, set()):
            raise Vnp46QuarantineError("Plataforma incompatible")
        doi = self._global_attribute("identifier_product_doi")
        if doi is not None and doi != self.policy.doi:
            raise Vnp46QuarantineError("DOI del producte incompatible")

        radiance = self._dataset(self.policy.layer)
        quality = self._dataset(self.policy.quality_layer)
        if radiance.ndim != 2 or radiance.dtype.kind != "f" or radiance.dtype.itemsize != 4:
            raise Vnp46QuarantineError("La radiància Collection 2 ha de ser float32 bidimensional")
        if quality.shape != radiance.shape or quality.dtype.kind != "u" or quality.dtype.itemsize != 1:
            raise Vnp46QuarantineError("Forma o tipus de Mandatory_Quality_Flag incompatible")
        for ancillary in self.policy.ancillary_layers:
            if self._dataset(ancillary).shape != radiance.shape:
                raise Vnp46QuarantineError(f"Forma incompatible de {ancillary}")
        latitude = self._dataset("lat")
        longitude = self._dataset("lon")
        if latitude.shape != (radiance.shape[0],) or longitude.shape != (radiance.shape[1],):
            raise Vnp46QuarantineError("La georeferència lat/lon no coincideix amb el ràster")

        attrs = radiance.attrs
        for required in ("units", "_FillValue", "valid_range"):
            if required not in attrs:
                raise Vnp46QuarantineError(f"Falta l'atribut de capa {required}")
        source_unit = _text(attrs["units"])
        if source_unit.strip() not in ("nWatts/(cm^2 sr)", self.policy.radiance_unit):
            raise Vnp46QuarantineError("Unitat de radiància incompatible")
        source_range = _text(attrs["valid_range"])
        if source_range.strip() != ">=0.0" or self.policy.valid_minimum != 0:
            raise Vnp46QuarantineError("Rang vàlid de radiància incompatible")
        fill = float(_text(attrs["_FillValue"]))
        if np.float32(fill) != np.float32(self.policy.fill_value):
            raise Vnp46QuarantineError("_FillValue incompatible")
        self._fill_value = float(np.float32(fill))
        scale = float(_text(attrs["scale_factor"])) if "scale_factor" in attrs else None
        offset = float(_text(attrs["offset"])) if "offset" in attrs else None
        if scale not in (None, 1.0) or offset not in (None, 0.0):
            raise Vnp46QuarantineError("Escala o offset no identitaris: conversió prohibida")
        if "_FillValue" not in quality.attrs or int(_text(quality.attrs["_FillValue"])) != self.policy.no_retrieval_quality:
            raise Vnp46QuarantineError("Fill de qualitat incompatible")

        self._provenance = Vnp46Provenance(
            granule_id=self.path.name,
            sha256=self.expected_sha256,
            source_url=self.source_url,
            product_url=self.policy.product_url,
            doi=self.policy.doi,
            algorithm_version=self._global_attribute("AlgorithmVersion", required=True) or "",
            pge_version=self._global_attribute("PGEVersion", required=True) or "",
            production_time=self._global_attribute("ProductionTime", required=True) or "",
            range_beginning_date=acquisition.isoformat(),
            range_ending_date=acquisition.isoformat(),
            processing_center=self._global_attribute("ProcessingCenter"),
            version_id=self._global_attribute("VersionID"),
            tile_id=self._global_attribute("TileID"),
            horizontal_tile=self._global_attribute("HorizontalTileNumber"),
            vertical_tile=self._global_attribute("VerticalTileNumber"),
            input_pointers=self._global_list_attribute("InputPointer"),
            radiance_dataset_path=f"{_FIELDS}/{self.policy.layer}",
            source_radiance_unit=source_unit,
            source_fill_value=self._fill_value,
            source_valid_range=source_range,
            source_scale_factor=scale,
            source_offset=offset,
        )

    def __enter__(self) -> Vnp46GranuleAdapter:
        self._check_cancelled()
        if not self.path.is_file():
            raise Vnp46UnavailableError("No hi ha cap grànul local disponible")
        self._verify_sha256()
        try:
            self._file = h5py.File(self.path, "r")
            self._validate()
        except Exception:
            self.close()
            raise
        return self

    def close(self) -> None:
        if self._file is not None:
            self._file.close()
            self._file = None

    def __exit__(self, _type: object, _value: object, _traceback: object) -> None:
        self.close()

    def read_pixel(self, acquisition_date: date, row: int, column: int) -> Vnp46Observation:
        """Llegeix una mostra exacta; qualsevol altre dia és indisponible."""

        if self._file is None or self._acquisition_date is None or self._provenance is None:
            raise RuntimeError("Cal obrir l'adaptador amb 'with'")
        self._check_cancelled()
        if acquisition_date != self._acquisition_date:
            raise Vnp46UnavailableError("No hi ha observació per al dia exacte sol·licitat")
        radiance = self._dataset(self.policy.layer)
        if not (0 <= row < radiance.shape[0] and 0 <= column < radiance.shape[1]):
            raise IndexError("Píxel fora del grànul")
        raw = float(radiance[row, column])
        if not math.isfinite(raw):
            raise Vnp46QuarantineError("Radiància no finita")
        quality = int(self._dataset(self.policy.quality_layer)[row, column])
        self._check_cancelled()
        lat = float(self._dataset("lat")[row])
        lon = float(self._dataset("lon")[column])
        if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
            raise Vnp46QuarantineError("Georeferència invàlida")
        assert self._fill_value is not None
        is_fill = raw == self._fill_value
        observation = Vnp46Observation(
            schema_version=1,
            profile_id=self.policy.profile_id,
            product_id=self.policy.product_id,
            collection=self.policy.collection,
            acquisition_date=acquisition_date,
            row=row,
            column=column,
            latitude_deg=lat,
            longitude_deg=lon,
            raw_radiance=raw,
            radiance_unit=self.policy.radiance_unit,
            quality_flag=quality,
            qf_cloud_mask=int(self._dataset("QF_Cloud_Mask")[row, column]),
            snow_flag=int(self._dataset("Snow_Flag")[row, column]),
            latest_high_quality_retrieval=int(
                self._dataset("Latest_High_Quality_Retrieval")[row, column]
            ),
            is_fill=is_fill,
            classification=self.policy.classify(raw, quality, is_fill=is_fill),
            provenance=self._provenance,
        )
        self._check_cancelled()
        return observation

    def iter_window(
        self, acquisition_date: date, row_start: int, row_stop: int, column_start: int, column_stop: int
    ) -> Iterator[Vnp46Observation]:
        """Itera una finestra sense materialitzar el grànul sencer."""

        for row in range(row_start, row_stop):
            self._check_cancelled()
            for column in range(column_start, column_stop):
                yield self.read_pixel(acquisition_date, row, column)
