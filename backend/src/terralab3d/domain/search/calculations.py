"""Contractes i implementació de càlculs científics purs per a cerca astronòmica."""

import re
import unicodedata
from typing import Protocol
from terralab3d.domain.geometry import EquatorialCoordinate

class SearchNormalizationCalculator(Protocol):
    """Defineix els càlculs purs de cerca astronòmica sense I/O ni renderitzat."""
    def normalize_query(self, text: str) -> str: ...
    def coordinate_query(self, text: str) -> EquatorialCoordinate | None: ...

class DefaultSearchNormalizationCalculator(SearchNormalizationCalculator):
    def __init__(self) -> None:
        # Regex per a coordenades: "RA 05:35:17.3 DEC -05:23:28", "05h35m17.3s -05d23m28s", "ra=83.8 dec=-5.3"
        self._coord_pattern = re.compile(
            r"^(?:ra\s*=?\s*)?"
            r"(?:(?P<ra_h>\d{1,2})[h:]\s*(?P<ra_m>\d{1,2})[m:]\s*(?P<ra_s>\d{1,2}(?:\.\d+)?)[s]?|"
            r"(?P<ra_deg>\d{1,3}(?:\.\d+)?)(?:deg|°)?"
            r")"
            r"[\s,]+(?:dec\s*=?\s*)?"
            r"(?:(?P<dec_sign>[+\-])?(?P<dec_d>\d{1,2})[d°:]\s*(?P<dec_m>\d{1,2})['m:]\s*(?P<dec_s>\d{1,2}(?:\.\d+)?)[\"s]?|"
            r"(?P<dec_deg>[+\-]?\d{1,2}(?:\.\d+)?)(?:deg|°)?"
            r")$",
            re.IGNORECASE,
        )

    def normalize_query(self, text: str) -> str:
        if not text:
            return ""
        lowered = text.strip().lower()
        folded = unicodedata.normalize("NFKD", lowered)
        stripped = "".join(ch for ch in folded if not unicodedata.combining(ch))
        # Treure espais innecessaris per aliases com "NGC 1976" -> "ngc1976"
        return stripped.replace(" ", "")

    def coordinate_query(self, text: str) -> EquatorialCoordinate | None:
        if not text:
            return None
        match = self._coord_pattern.match(text.strip())
        if not match:
            return None

        d = match.groupdict()
        try:
            if d.get("ra_h") is not None:
                ra_h = float(d["ra_h"])
                ra_m = float(d["ra_m"])
                ra_s = float(d["ra_s"])
                ra_deg = (ra_h + ra_m / 60.0 + ra_s / 3600.0) * 15.0
            else:
                ra_deg = float(d["ra_deg"])

            if d.get("dec_d") is not None:
                dec_d = float(d["dec_d"])
                dec_m = float(d["dec_m"])
                dec_s = float(d["dec_s"])
                sign = -1.0 if d.get("dec_sign") == "-" else 1.0
                dec_deg = sign * (dec_d + dec_m / 60.0 + dec_s / 3600.0)
            else:
                dec_deg = float(d["dec_deg"])
                
            if not (0.0 <= ra_deg < 360.0):
                return None
            if not (-90.0 <= dec_deg <= 90.0):
                return None
                
            return EquatorialCoordinate(right_ascension_deg=ra_deg, declination_deg=dec_deg)
        except (ValueError, TypeError):
            return None
