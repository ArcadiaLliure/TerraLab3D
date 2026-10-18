"""Gate d'admissibilitat de la base de mesura del futur SourceModel.

Una observació L3 i una RSR de diagnòstic no determinen cap SPD ni cap emissió
angular. Aquesta frontera impedeix crear fonts físiques a partir d'evidència
incompleta; els priors i la inversió L3→font continuen pendents al Pas 7.5.
"""

from __future__ import annotations

import math
from bisect import bisect_right
from dataclasses import dataclass
from typing import Literal

from .dnb_measurement import RADIANCE_UNIT, MeasurementTarget, ViirsSpectralResponse
from .vnp46 import Vnp46Observation


@dataclass(frozen=True, slots=True)
class AngularEmissionProfile:
    """Forma axial tabulada; cap perfil ni llei Lambertiana per defecte.

    `relative_intensity` descriu intensitat radiant relativa per direcció,
    no radiància superficial observada. La densitat es normalitza sobre
    l'hemisferi ascendent: 2π∫₀^(π/2) p(θ) sin(θ)dθ = 1.
    """

    profile_id: str
    evidence_reference: str
    zenith_deg: tuple[float, ...]
    relative_intensity: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.profile_id or not self.evidence_reference:
            raise ValueError("Cal identitat i procedència del perfil angular")
        if len(self.zenith_deg) < 2 or len(self.zenith_deg) != len(self.relative_intensity):
            raise ValueError("Calen nusos i intensitats angulars aparellats")
        if self.zenith_deg[0] != 0 or self.zenith_deg[-1] != 90:
            raise ValueError("El perfil ha de cobrir l'hemisferi ascendent 0–90°")
        if any(not math.isfinite(x) for x in (*self.zenith_deg, *self.relative_intensity)):
            raise ValueError("El perfil angular conté valors no finits")
        if any(b <= a for a, b in zip(self.zenith_deg, self.zenith_deg[1:])):
            raise ValueError("Els angles han de ser estrictament creixents")
        if any(x < 0 for x in self.relative_intensity) or not any(x > 0 for x in self.relative_intensity):
            raise ValueError("La intensitat relativa ha de ser no negativa i no nul·la")
        if not math.isfinite(self.solid_angle_integral) or self.solid_angle_integral <= 0:
            raise ValueError("La integral angular ha de ser positiva i finita")

    @property
    def solid_angle_integral(self) -> float:
        """Integral analítica del perfil lineal a trossos, en estereoradians."""
        terms: list[float] = []
        for left_deg, right_deg, left_value, right_value in zip(
            self.zenith_deg, self.zenith_deg[1:],
            self.relative_intensity, self.relative_intensity[1:],
        ):
            left = math.radians(left_deg)
            right = math.radians(right_deg)
            slope = (right_value - left_value) / (right - left)
            intercept = left_value - slope * left
            def antiderivative(theta: float) -> float:
                return -intercept * math.cos(theta) + slope * (-theta * math.cos(theta) + math.sin(theta))
            terms.append(antiderivative(right) - antiderivative(left))
        return 2 * math.pi * math.fsum(terms)

    def density_per_sr(self, zenith_deg: float) -> float:
        """Intensitat angular normalitzada; només per al perfil declarat."""
        if not math.isfinite(zenith_deg) or not 0 <= zenith_deg <= 90:
            raise ValueError("Angle zenital fora de l'hemisferi ascendent")
        index = min(bisect_right(self.zenith_deg, zenith_deg) - 1, len(self.zenith_deg) - 2)
        left, right = self.zenith_deg[index:index + 2]
        first, second = self.relative_intensity[index:index + 2]
        value = first + (second - first) * (zenith_deg - left) / (right - left)
        return value / self.solid_angle_integral


@dataclass(frozen=True, slots=True)
class SourceMeasurementAssessment:
    """Avaluació de condicions necessàries, mai una homologació de SourceModel."""

    status: Literal["measurement_basis_admissible", "unavailable_for_physical_inference"]
    reasons: tuple[str, ...]
    product_id: str
    collection: str
    acquisition_date: str
    granule_id: str
    granule_sha256: str
    rsr_sha256: str | None
    rsr_release_id: str | None
    rsr_gain_stage: str | None
    rsr_application: str | None
    rsr_evidence_class: str | None
    rsr_l3_link_status: str | None
    rsr_spectral_uncertainty_status: str | None

    @property
    def measurement_basis_admissible(self) -> bool:
        return self.status == "measurement_basis_admissible"


def assess_vnp46_measurement_basis(
    observation: Vnp46Observation,
    response: ViirsSpectralResponse | None,
) -> SourceMeasurementAssessment:
    """Comprova QA i vincle RSR/L3 sense aplicar la integral TOA al valor L3.

    Fins i tot un resultat admissible només satisfà la base de mesura: calen
    priors SPD, model angular, operador invers L3 i incertesa estructural abans
    de construir una font física.
    """

    reasons: list[str] = []
    if observation.product_id != "VNP46A2" or observation.collection != "002":
        reasons.append("unsupported_product_or_collection")
    if observation.provenance.version_id not in (None, observation.collection):
        reasons.append("granule_collection_mismatch")
    if observation.classification != "candidate" or observation.is_fill:
        reasons.append("quality_not_source_candidate")
    if observation.radiance_unit != RADIANCE_UNIT:
        reasons.append("l3_radiance_unit_mismatch")
    if not math.isfinite(observation.raw_radiance) or observation.raw_radiance <= 0:
        reasons.append("no_positive_l3_constraint")
    if response is None:
        reasons.append("operational_rsr_unavailable")
    else:
        target = MeasurementTarget(
            platform="Suomi-NPP",
            product_id=observation.product_id,
            collection=observation.collection,
            acquisition_date=observation.acquisition_date,
        )
        if not target.matches(response):
            reasons.append("rsr_product_or_date_mismatch")
        if not response.source_model_candidate:
            reasons.append("rsr_l3_gain_chain_not_accredited")
    return SourceMeasurementAssessment(
        status="unavailable_for_physical_inference" if reasons else "measurement_basis_admissible",
        reasons=tuple(reasons),
        product_id=observation.product_id,
        collection=observation.collection,
        acquisition_date=observation.acquisition_date.isoformat(),
        granule_id=observation.provenance.granule_id,
        granule_sha256=observation.provenance.sha256,
        rsr_sha256=response.local_sha256 if response else None,
        rsr_release_id=response.release_id if response else None,
        rsr_gain_stage=response.gain_stage if response else None,
        rsr_application=response.application if response else None,
        rsr_evidence_class=response.evidence_class if response else None,
        rsr_l3_link_status=response.l3_link_status if response else None,
        rsr_spectral_uncertainty_status=response.spectral_uncertainty_status if response else None,
    )
