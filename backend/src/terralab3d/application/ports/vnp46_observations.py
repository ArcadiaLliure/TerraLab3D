"""Port de lectura d'observacions VNP46 sense inferència de font."""

from __future__ import annotations

from datetime import date
from typing import Iterator, Protocol

from terralab3d.domain.light_pollution.vnp46 import Vnp46Observation


class Vnp46ObservationPort(Protocol):
    def read_pixel(self, acquisition_date: date, row: int, column: int) -> Vnp46Observation: ...

    def iter_window(
        self, acquisition_date: date, row_start: int, row_stop: int, column_start: int, column_stop: int
    ) -> Iterator[Vnp46Observation]: ...

    def close(self) -> None: ...
