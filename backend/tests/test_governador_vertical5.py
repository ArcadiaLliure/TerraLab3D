from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from terralab3d.domain.datasets.models import FontTerritorial, SourceRole
from terralab3d.domain.observer.models import GeoLocation
from terralab3d.domain.surface.governador import (
    GovernadorEspacial,
    SenseBaseCategoricaActivaError,
    validar_inici_arbre_tlst,
)
from terralab3d.domain.surface.tlst import (
    ClassificationStatus,
    ObservationState,
    SampleValidity,
    SingleSurface,
    SourceClassification,
    SurfaceObservation,
)
from terralab3d.infrastructure.resources.data_sources import DataSourceRepository


POSICIO = GeoLocation(latitude_deg=41.3874, longitude_deg=2.1686)


class MostrejadorMemoria:
    def __init__(self, observacions: dict[str, SurfaceObservation]) -> None:
        self._observacions = observacions
        self.consultes: list[str] = []

    def cobreix(self, font: FontTerritorial, posicio: GeoLocation) -> bool:
        return font.stable_id in self._observacions

    def observar(
        self,
        font: FontTerritorial,
        posicio: GeoLocation,
    ) -> SurfaceObservation:
        self.consultes.append(font.stable_id)
        return self._observacions[font.stable_id]


def _font(
    stable_id: str,
    resolucio_m: float,
    *,
    enabled: bool = True,
    priority: int = 0,
    source_role: SourceRole = SourceRole.BASE_CATEGORICAL,
) -> FontTerritorial:
    return FontTerritorial(
        stable_id=stable_id,
        source_role=source_role,
        installed=True,
        enabled=enabled,
        priority=priority,
        spatial_resolution_m=resolucio_m,
    )


def _observacio_valida(stable_id: str, categoria: str) -> SurfaceObservation:
    return SurfaceObservation(
        source=SourceClassification(
            scheme_key="fixture",
            scheme_version="1",
            source_code=1,
            source_label=stable_id,
        ),
        validity=SampleValidity.VALID,
        translation=SingleSurface(categoria),
    )


def _observacio_nodata(stable_id: str) -> SurfaceObservation:
    return SurfaceObservation(
        source=SourceClassification(
            scheme_key="fixture",
            scheme_version="1",
            source_code=0,
            source_label=stable_id,
        ),
        validity=SampleValidity.NODATA,
        translation=None,
    )


def test_un_metre_valid_governa_sobre_deu_metres_valid() -> None:
    fina = _font("base-1m", 1.0)
    grossa = _font("base-10m", 10.0)
    mostrejador = MostrejadorMemoria({
        fina.stable_id: _observacio_valida(fina.stable_id, "artificial.unspecified"),
        grossa.stable_id: _observacio_valida(
            grossa.stable_id,
            "agriculture.cropland.unspecified",
        ),
    })

    resultat = GovernadorEspacial(mostrejador).seleccionar(POSICIO, (grossa, fina))

    assert resultat is not None
    assert resultat.font.stable_id == fina.stable_id
    assert mostrejador.consultes == [fina.stable_id]


def test_un_metre_nodata_fa_fallback_a_deu_metres_valid() -> None:
    fina = _font("base-1m", 1.0)
    grossa = _font("base-10m", 10.0)
    mostrejador = MostrejadorMemoria({
        fina.stable_id: _observacio_nodata(fina.stable_id),
        grossa.stable_id: _observacio_valida(
            grossa.stable_id,
            "agriculture.cropland.unspecified",
        ),
    })

    resultat = GovernadorEspacial(mostrejador).seleccionar(POSICIO, (grossa, fina))

    assert resultat is not None
    assert resultat.font.stable_id == grossa.stable_id
    assert mostrejador.consultes == [fina.stable_id, grossa.stable_id]


def test_un_metre_ignorat_no_participa_i_governa_deu_metres_actiu() -> None:
    fina_ignorada = _font("base-1m", 1.0, enabled=False)
    grossa = _font("base-10m", 10.0)
    mostrejador = MostrejadorMemoria({
        fina_ignorada.stable_id: _observacio_valida(
            fina_ignorada.stable_id,
            "artificial.unspecified",
        ),
        grossa.stable_id: _observacio_valida(
            grossa.stable_id,
            "agriculture.cropland.unspecified",
        ),
    })

    resultat = GovernadorEspacial(mostrejador).seleccionar(
        POSICIO,
        (fina_ignorada, grossa),
    )

    assert resultat is not None
    assert resultat.font.stable_id == grossa.stable_id
    assert mostrejador.consultes == [grossa.stable_id]


@pytest.mark.parametrize(
    "estat",
    (ClassificationStatus.UNKNOWN, ClassificationStatus.UNCLASSIFIED),
)
def test_unknown_i_unclassified_tambe_activen_fallback(
    estat: ClassificationStatus,
) -> None:
    primera = _font("base-a", 1.0)
    segona = _font("base-b", 10.0)
    sense_classe = SurfaceObservation(
        source=SourceClassification("fixture", "1", 1, primera.stable_id),
        validity=SampleValidity.VALID,
        translation=ObservationState(estat),
    )
    mostrejador = MostrejadorMemoria({
        primera.stable_id: sense_classe,
        segona.stable_id: _observacio_valida(segona.stable_id, "water.unspecified"),
    })

    resultat = GovernadorEspacial(mostrejador).seleccionar(
        POSICIO,
        (primera, segona),
    )

    assert resultat is not None
    assert resultat.font.stable_id == segona.stable_id


def test_empat_de_resolucio_usa_prioritat_i_despres_stable_id() -> None:
    baixa = _font("base-z", 10.0, priority=1)
    alta_b = _font("base-b", 10.0, priority=5)
    alta_a = _font("base-a", 10.0, priority=5)
    mostrejador = MostrejadorMemoria({
        font.stable_id: _observacio_valida(font.stable_id, "water.unspecified")
        for font in (baixa, alta_b, alta_a)
    })

    resultat = GovernadorEspacial(mostrejador).seleccionar(
        POSICIO,
        (baixa, alta_b, alta_a),
    )

    assert resultat is not None
    assert resultat.font.stable_id == alta_a.stable_id
    assert mostrejador.consultes == [alta_a.stable_id]


def test_un_refinament_mes_precis_no_pot_ser_governador() -> None:
    refinament = _font(
        "refinament-1m",
        1.0,
        source_role=SourceRole.SEMANTIC_REFINEMENT,
    )
    base = _font("base-10m", 10.0)
    mostrejador = MostrejadorMemoria({
        refinament.stable_id: _observacio_valida(
            refinament.stable_id,
            "agriculture.cropland.vineyard",
        ),
        base.stable_id: _observacio_valida(
            base.stable_id,
            "agriculture.cropland.unspecified",
        ),
    })

    resultat = GovernadorEspacial(mostrejador).seleccionar(
        POSICIO,
        (refinament, base),
    )

    assert resultat is not None
    assert resultat.font.stable_id == base.stable_id
    assert mostrejador.consultes == [base.stable_id]


def test_refinament_orfe_no_pot_iniciar_arbre_tlst() -> None:
    refinament = _font(
        "crop-types",
        10.0,
        source_role=SourceRole.SEMANTIC_REFINEMENT,
    )

    with pytest.raises(SenseBaseCategoricaActivaError):
        validar_inici_arbre_tlst((refinament,))


def test_source_role_enabled_i_priority_persisteixen_despres_de_reiniciar(
    tmp_path: Path,
) -> None:
    path = tmp_path / "data_sources.json"
    repository = DataSourceRepository(path)
    repository.activate_land_cover({
        "id": "base-local",
        "display_name": "Base local",
        "path": str(tmp_path / "base.tif"),
        "resolution_m": 1.0,
    })

    repository.configure_semantic_source(
        "base-local",
        source_role=SourceRole.BASE_CATEGORICAL,
        enabled=False,
        priority=17,
    )

    restarted = DataSourceRepository(path)
    record = restarted.land_cover_records()[0]
    assert record["source_role"] == SourceRole.BASE_CATEGORICAL.value
    assert record["enabled"] is False
    assert record["priority"] == 17
    assert restarted.territorial_sources() == (
        FontTerritorial(
            stable_id="base-local",
            source_role=SourceRole.BASE_CATEGORICAL,
            installed=True,
            enabled=False,
            priority=17,
            spatial_resolution_m=1.0,
        ),
    )


def test_migracio_legacy_assigna_rol_base_sense_perdre_camps(tmp_path: Path) -> None:
    path = tmp_path / "data_sources.json"
    path.write_text(
        json.dumps({
            "schemaVersion": 5,
            "sources": [{
                "id": "legacy",
                "layer_type": "land_cover_categorical",
                "resolution_m": 10,
                "futureField": "kept",
            }],
            "selections": {},
        }),
        encoding="utf-8",
    )

    repository = DataSourceRepository(path)
    record = repository.land_cover_records()[0]

    assert repository.snapshot()["schemaVersion"] == 6
    assert record["source_role"] == SourceRole.BASE_CATEGORICAL.value
    assert record["enabled"] is True
    assert record["priority"] == 0
    assert record["futureField"] == "kept"


def test_font_territorial_rebutja_rols_no_tipats() -> None:
    with pytest.raises(ValueError, match="SourceRole"):
        replace(_font("base", 1.0), source_role="BASE_CATEGORICAL")  # type: ignore[arg-type]
