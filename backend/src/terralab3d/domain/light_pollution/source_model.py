"""Font física definida S i gate observacional separat de Black Marble C/H.

Una font S té espectre, geometria, amplitud i emissió angular explícits. Cap
observació L3 ni RSR no és necessària per construir-la. El gate C/H preserva
la frontera: una observació pancromàtica no identifica una font física única.
"""

from __future__ import annotations

import math
from bisect import bisect_right
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from .dnb_measurement import ViirsSpectralResponse
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

    def density_per_sr(self, zenith_deg: float, azimuth_deg: float = 0.0) -> float:
        """Intensitat angular normalitzada; només per al perfil declarat."""
        if not math.isfinite(zenith_deg) or not 0 <= zenith_deg <= 90:
            raise ValueError("Angle zenital fora de l'hemisferi ascendent")
        if not math.isfinite(azimuth_deg):
            raise ValueError("Azimut no finit")
        index = min(bisect_right(self.zenith_deg, zenith_deg) - 1, len(self.zenith_deg) - 2)
        left, right = self.zenith_deg[index:index + 2]
        first, second = self.relative_intensity[index:index + 2]
        value = first + (second - first) * (zenith_deg - left) / (right - left)
        return value / self.solid_angle_integral


@dataclass(frozen=True, slots=True)
class AzimuthalAngularEmissionProfile:
    """Distribució separable axial×azimutal amb azimut geodèsic 0°=nord.

    La modulació periòdica té mitjana angular u; dividir-la per u conserva
    exactament la normalització hemisfèrica del perfil axial.
    """

    profile_id: str
    evidence_reference: str
    axial: AngularEmissionProfile
    azimuth_deg: tuple[float, ...]
    relative_azimuth: tuple[float, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.axial, AngularEmissionProfile):
            raise ValueError("Cal un perfil axial validat")
        if not self.profile_id or not self.evidence_reference:
            raise ValueError("Cal identitat i procedència del perfil azimutal")
        if len(self.azimuth_deg) < 2 or len(self.azimuth_deg) != len(self.relative_azimuth):
            raise ValueError("Calen nusos azimutals aparellats")
        if self.azimuth_deg[0] != 0 or self.azimuth_deg[-1] != 360:
            raise ValueError("El perfil azimutal ha de cobrir 0–360°")
        if any(not math.isfinite(x) for x in (*self.azimuth_deg, *self.relative_azimuth)):
            raise ValueError("El perfil azimutal conté valors no finits")
        if any(b <= a for a, b in zip(self.azimuth_deg, self.azimuth_deg[1:])):
            raise ValueError("Els azimuts han de ser estrictament creixents")
        if self.relative_azimuth[0] != self.relative_azimuth[-1]:
            raise ValueError("El perfil azimutal ha de ser periòdic")
        if any(x < 0 for x in self.relative_azimuth) or not math.isfinite(self.azimuth_mean) or self.azimuth_mean <= 0:
            raise ValueError("La modulació azimutal ha de ser no negativa i no nul·la")

    @property
    def azimuth_mean(self) -> float:
        return math.fsum(
            (right - left) * (first + second) / 2
            for left, right, first, second in zip(
                self.azimuth_deg, self.azimuth_deg[1:],
                self.relative_azimuth, self.relative_azimuth[1:],
            )
        ) / 360

    def density_per_sr(self, zenith_deg: float, azimuth_deg: float = 0.0) -> float:
        if not math.isfinite(azimuth_deg):
            raise ValueError("Azimut no finit")
        azimuth = azimuth_deg % 360
        index = min(bisect_right(self.azimuth_deg, azimuth) - 1, len(self.azimuth_deg) - 2)
        left, right = self.azimuth_deg[index:index + 2]
        first, second = self.relative_azimuth[index:index + 2]
        modulation = first + (second - first) * (azimuth - left) / (right - left)
        return self.axial.density_per_sr(zenith_deg) * modulation / self.azimuth_mean


@dataclass(frozen=True, slots=True)
class DefinedSpectrum:
    """Forma espectral no negativa normalitzada a ∫s(λ)dλ=1.

    `relative_power` es tracta com a interpolació lineal entre nusos i zero
    fora del suport; no reconstrueix estructura espectral no tabulada.
    """

    spectrum_id: str
    evidence_reference: str
    license: str
    wavelengths_nm: tuple[float, ...]
    relative_power: tuple[float, ...]
    asset_sha256: str | None = None
    components: tuple[tuple[str, str | None, float], ...] = ()
    origin_kind: Literal["defined_input", "published_table", "derived_mixture"] = "defined_input"

    def __post_init__(self) -> None:
        if not self.spectrum_id or not self.evidence_reference or not self.license:
            raise ValueError("Cal identitat, procedència i llicència de l'espectre")
        if len(self.wavelengths_nm) < 2 or len(self.wavelengths_nm) != len(self.relative_power):
            raise ValueError("L'espectre requereix almenys dos nusos aparellats")
        if any(not math.isfinite(x) for x in (*self.wavelengths_nm, *self.relative_power)):
            raise ValueError("L'espectre conté valors no finits")
        if self.wavelengths_nm[0] <= 0 or any(b <= a for a, b in zip(self.wavelengths_nm, self.wavelengths_nm[1:])):
            raise ValueError("Les longituds d'ona han de ser positives i creixents")
        if any(x < 0 for x in self.relative_power) or not math.isfinite(self.raw_integral_nm) or self.raw_integral_nm <= 0:
            raise ValueError("L'espectre ha de ser no negatiu i no nul")
        if self.asset_sha256 is not None and (
            len(self.asset_sha256) != 64 or any(ch not in "0123456789abcdef" for ch in self.asset_sha256)
        ):
            raise ValueError("SHA-256 espectral invàlid")
        if any(not source_id or not math.isfinite(weight) or weight <= 0 for source_id, _, weight in self.components):
            raise ValueError("La procedència dels components espectrals és invàlida")
        if self.origin_kind == "published_table" and self.asset_sha256 is None:
            raise ValueError("Una taula publicada requereix SHA-256 de l'asset")
        if self.origin_kind == "derived_mixture" and not self.components:
            raise ValueError("Una mescla requereix procedència dels components")
        if self.origin_kind not in {"defined_input", "published_table", "derived_mixture"}:
            raise ValueError("Origen espectral desconegut")

    @property
    def raw_integral_nm(self) -> float:
        return math.fsum(
            (right - left) * (first + second) / 2
            for left, right, first, second in zip(
                self.wavelengths_nm, self.wavelengths_nm[1:],
                self.relative_power, self.relative_power[1:],
            )
        )

    def density_per_nm(self, wavelength_nm: float) -> float:
        if not math.isfinite(wavelength_nm):
            raise ValueError("Longitud d'ona no finita")
        if wavelength_nm < self.wavelengths_nm[0] or wavelength_nm > self.wavelengths_nm[-1]:
            return 0.0
        index = min(bisect_right(self.wavelengths_nm, wavelength_nm) - 1, len(self.wavelengths_nm) - 2)
        left, right = self.wavelengths_nm[index:index + 2]
        first, second = self.relative_power[index:index + 2]
        return (first + (second - first) * (wavelength_nm - left) / (right - left)) / self.raw_integral_nm


def mix_defined_spectra(
    spectrum_id: str,
    components: tuple[tuple[DefinedSpectrum, float], ...],
    evidence_reference: str,
) -> DefinedSpectrum:
    """Mescla convexa d'espectres normalitzats sense perdre nusos estrets."""
    if not components or any(not math.isfinite(weight) or weight < 0 for _, weight in components):
        raise ValueError("Els pesos espectrals han de ser finits i no negatius")
    total_weight = math.fsum(weight for _, weight in components)
    if total_weight <= 0:
        raise ValueError("La mescla requereix pes total positiu")
    support = (components[0][0].wavelengths_nm[0], components[0][0].wavelengths_nm[-1])
    if any((spectrum.wavelengths_nm[0], spectrum.wavelengths_nm[-1]) != support for spectrum, _ in components):
        raise ValueError("La mescla tabulada requereix el mateix suport; cal explicitar els límits")
    knots = tuple(sorted({wavelength for spectrum, _ in components for wavelength in spectrum.wavelengths_nm}))
    values = tuple(math.fsum(
        weight / total_weight * spectrum.density_per_nm(wavelength)
        for spectrum, weight in components
    ) for wavelength in knots)
    licenses = {spectrum.license for spectrum, _ in components}
    return DefinedSpectrum(
        spectrum_id, evidence_reference,
        next(iter(licenses)) if len(licenses) == 1 else "multiple; see components",
        knots, values,
        components=tuple(
            (spectrum.spectrum_id, spectrum.asset_sha256, weight / total_weight)
            for spectrum, weight in components if weight > 0
        ),
        origin_kind="derived_mixture",
    )


@dataclass(frozen=True, slots=True)
class GeodeticPosition:
    latitude_deg: float
    longitude_deg: float
    altitude_m: float

    def __post_init__(self) -> None:
        if any(not math.isfinite(x) for x in (self.latitude_deg, self.longitude_deg, self.altitude_m)):
            raise ValueError("La posició conté valors no finits")
        if not -90 <= self.latitude_deg <= 90 or not -180 <= self.longitude_deg <= 180:
            raise ValueError("Latitud o longitud fora de rang")


@dataclass(frozen=True, slots=True)
class PointSourceGeometry:
    position: GeodeticPosition

    def __post_init__(self) -> None:
        if not isinstance(self.position, GeodeticPosition):
            raise ValueError("Una font puntual requereix posició geodèsica")


@dataclass(frozen=True, slots=True)
class RectangularAreaGeometry:
    """Rectangle uniforme al pla tangent local; orientació des del nord."""

    center: GeodeticPosition
    east_width_m: float
    north_height_m: float
    orientation_deg: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.center, GeodeticPosition):
            raise ValueError("Una àrea requereix centre geodèsic")
        if any(not math.isfinite(x) for x in (self.east_width_m, self.north_height_m, self.orientation_deg)):
            raise ValueError("La geometria d'àrea conté valors no finits")
        if self.east_width_m <= 0 or self.north_height_m <= 0:
            raise ValueError("L'àrea ha de tenir costats positius")
        if not 0 <= self.orientation_deg < 360:
            raise ValueError("L'orientació ha de ser en [0, 360)")
        if abs(self.center.latitude_deg) == 90:
            raise ValueError("El pla est/nord no està definit al pol")
        if not math.isfinite(self.area_m2):
            raise ValueError("Àrea no finita")

    @property
    def area_m2(self) -> float:
        return self.east_width_m * self.north_height_m


@dataclass(frozen=True, slots=True)
class EmissionAmplitude:
    value: float
    unit: Literal["W", "relative"]
    absolute_calibration_status: Literal["defined_absolute", "measured_absolute", "parametric"]
    evidence_reference: str
    parameter_name: str | None = None

    def __post_init__(self) -> None:
        if not math.isfinite(self.value) or self.value <= 0 or not self.evidence_reference:
            raise ValueError("L'amplitud ha de ser positiva, finita i documentada")
        if self.unit == "W" and self.absolute_calibration_status not in {"defined_absolute", "measured_absolute"}:
            raise ValueError("Els watts requereixen escala absoluta definida o mesurada")
        if self.unit == "relative" and (
            self.absolute_calibration_status != "parametric" or not self.parameter_name
        ):
            raise ValueError("L'escala relativa requereix un paràmetre identificat")
        if self.unit not in {"W", "relative"}:
            raise ValueError("Unitat d'amplitud desconeguda")


@dataclass(frozen=True, slots=True)
class SpectralEmissionValue:
    value: float
    unit: str

    def __post_init__(self) -> None:
        if not math.isfinite(self.value) or self.value < 0 or not self.unit:
            raise ValueError("La magnitud espectral ha de ser finita, no negativa i tenir unitat")


@dataclass(frozen=True, slots=True)
class SourceModel:
    """Contracte de transport compartit S/C; Pλ=P·s(λ), Iλ=Pλ·a(θ,φ).

    Per a una àrea A uniforme, Mλ=Pλ/A i Lλ=Mλ·a/cosθ per θ<90°.
    Una font puntual no té radiància superficial. Els watts d'una fixture
    definida no es presenten com a mesura de cap ciutat.
    """

    source_model_id: str
    revision: str
    definition_reference: str
    geometry: PointSourceGeometry | RectangularAreaGeometry
    spectrum: DefinedSpectrum
    angular: AngularEmissionProfile | AzimuthalAngularEmissionProfile
    amplitude: EmissionAmplitude
    source_mode: Literal["DEFINED_SOURCE", "CONDITIONAL_L3"] = "DEFINED_SOURCE"
    schema_version: int = 1
    uncertainty_status: Literal["not_quantified"] = "not_quantified"

    def __post_init__(self) -> None:
        if not self.source_model_id or not self.revision or not self.definition_reference:
            raise ValueError("Cal identitat, revisió i procedència del SourceModel")
        if self.source_mode not in {"DEFINED_SOURCE", "CONDITIONAL_L3"} or self.schema_version != 1 or self.uncertainty_status != "not_quantified":
            raise ValueError("Mode, versió o estat d'incertesa de SourceModel desconegut")
        if not isinstance(self.geometry, (PointSourceGeometry, RectangularAreaGeometry)):
            raise ValueError("Geometria de font desconeguda")
        if not isinstance(self.spectrum, DefinedSpectrum) or not isinstance(
            self.angular, (AngularEmissionProfile, AzimuthalAngularEmissionProfile)
        ) or not isinstance(self.amplitude, EmissionAmplitude):
            raise ValueError("Contracte físic de font incomplet")
        if self.source_mode == "CONDITIONAL_L3" and self.amplitude.unit != "relative":
            raise ValueError("L3 condicionat no acredita watts hemisfèrics absoluts")

    def spectral_flux(self, wavelength_nm: float) -> SpectralEmissionValue:
        return SpectralEmissionValue(
            self.amplitude.value * self.spectrum.density_per_nm(wavelength_nm),
            f"{self.amplitude.unit} nm^-1",
        )

    def spectral_radiant_intensity(
        self, wavelength_nm: float, zenith_deg: float, azimuth_deg: float = 0.0,
    ) -> SpectralEmissionValue:
        density = self.angular.density_per_sr(zenith_deg, azimuth_deg)
        return SpectralEmissionValue(
            self.spectral_flux(wavelength_nm).value * density,
            f"{self.amplitude.unit} sr^-1 nm^-1",
        )

    def surface_spectral_exitance(self, wavelength_nm: float) -> SpectralEmissionValue:
        if not isinstance(self.geometry, RectangularAreaGeometry):
            raise ValueError("Una font puntual no té exitància superficial")
        return SpectralEmissionValue(
            self.spectral_flux(wavelength_nm).value / self.geometry.area_m2,
            f"{self.amplitude.unit} m^-2 nm^-1",
        )

    def area_spectral_radiant_intensity_density(
        self, wavelength_nm: float, zenith_deg: float, azimuth_deg: float = 0.0,
    ) -> SpectralEmissionValue:
        """dIλ/dA sobre el rectangle; difereix de Lλ pel factor cosθ."""
        exitance = self.surface_spectral_exitance(wavelength_nm)
        return SpectralEmissionValue(
            exitance.value * self.angular.density_per_sr(zenith_deg, azimuth_deg),
            f"{self.amplitude.unit} m^-2 sr^-1 nm^-1",
        )

    def surface_spectral_radiance(
        self, wavelength_nm: float, zenith_deg: float, azimuth_deg: float = 0.0,
    ) -> SpectralEmissionValue:
        if not isinstance(self.geometry, RectangularAreaGeometry):
            raise ValueError("Una font puntual no té radiància superficial")
        if not math.isfinite(zenith_deg) or not 0 <= zenith_deg < 90:
            raise ValueError("La radiància superficial requereix cosθ positiu")
        return SpectralEmissionValue(
            self.area_spectral_radiant_intensity_density(wavelength_nm, zenith_deg, azimuth_deg).value
            / math.cos(math.radians(zenith_deg)),
            f"{self.amplitude.unit} m^-2 sr^-1 nm^-1",
        )

    def to_dict(self) -> dict[str, object]:
        """DTO de diagnòstic S amb unitats i cadena de procedència explícites."""
        position = self.geometry.position if isinstance(self.geometry, PointSourceGeometry) else self.geometry.center
        position_dto = {
            "latitudeDeg": position.latitude_deg,
            "longitudeDeg": position.longitude_deg,
            "altitudeM": position.altitude_m,
        }
        geometry_dto: dict[str, object] = (
            {"kind": "point", "position": position_dto}
            if isinstance(self.geometry, PointSourceGeometry) else {
                "kind": "rectangular_area", "center": position_dto,
                "eastWidthM": self.geometry.east_width_m,
                "northHeightM": self.geometry.north_height_m,
                "orientationDeg": self.geometry.orientation_deg,
                "areaM2": self.geometry.area_m2,
            }
        )
        axial = self.angular.axial if isinstance(self.angular, AzimuthalAngularEmissionProfile) else self.angular
        axial_dto = {
            "profileId": axial.profile_id,
            "evidenceReference": axial.evidence_reference,
            "zenithDeg": axial.zenith_deg,
            "relativeIntensity": axial.relative_intensity,
        }
        angular_dto: dict[str, object] = (
            {"kind": "axial", **axial_dto}
            if isinstance(self.angular, AngularEmissionProfile) else {
                "kind": "separable_azimuthal",
                "profileId": self.angular.profile_id,
                "evidenceReference": self.angular.evidence_reference,
                "axial": axial_dto,
                "azimuthDeg": self.angular.azimuth_deg,
                "relativeAzimuth": self.angular.relative_azimuth,
            }
        )
        angular_dto["normalization"] = "hemisphere_integral_one"
        angular_dto["densityUnit"] = "sr^-1"
        return {
            "schemaVersion": self.schema_version,
            "sourceMode": self.source_mode,
            "sourceModelId": self.source_model_id,
            "revision": self.revision,
            "definitionReference": self.definition_reference,
            "uncertaintyStatus": self.uncertainty_status,
            "geometry": geometry_dto,
            "spectrum": {
                "spectrumId": self.spectrum.spectrum_id,
                "evidenceReference": self.spectrum.evidence_reference,
                "license": self.spectrum.license,
                "wavelengthsNm": self.spectrum.wavelengths_nm,
                "relativePower": self.spectrum.relative_power,
                "relativePowerUnit": "relative",
                "normalizedDensityUnit": "nm^-1",
                "assetSha256": self.spectrum.asset_sha256,
                "originKind": self.spectrum.origin_kind,
                "components": tuple({"spectrumId": source_id, "assetSha256": sha, "weight": weight}
                                    for source_id, sha, weight in self.spectrum.components),
                "normalization": "integral_per_nm_one",
            },
            "angular": angular_dto,
            "amplitude": {
                "value": self.amplitude.value,
                "unit": self.amplitude.unit,
                "absoluteCalibrationStatus": self.amplitude.absolute_calibration_status,
                "evidenceReference": self.amplitude.evidence_reference,
                "parameterName": self.amplitude.parameter_name,
            },
        }


@dataclass(frozen=True, slots=True)
class SourceModelEnsemble:
    """Alternatives físiques sense pesos probabilístics inferits."""

    ensemble_id: str
    alternatives: tuple[SourceModel, ...]

    def __post_init__(self) -> None:
        if not self.ensemble_id or len(self.alternatives) < 2:
            raise ValueError("L'ensemble requereix identificador i almenys dues alternatives")
        if len({model.source_model_id for model in self.alternatives}) != len(self.alternatives):
            raise ValueError("Els identificadors de les alternatives han de ser únics")


@dataclass(frozen=True, slots=True)
class SourceMeasurementAssessment:
    """Gate de base observacional H; no prohibeix escenaris condicionats C."""

    status: Literal["measurement_basis_admissible", "unavailable_for_validated_l3_inference"]
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

    Un resultat admissible només satisfà la base de mesura H: calen priors
    SPD, model angular, operador L3→font i incertesa estructural abans de
    formular cap predicció observacional.
    """
    from .dnb_measurement import RADIANCE_UNIT, MeasurementTarget

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
        if not response.validated_l3_basis_candidate:
            reasons.append("rsr_l3_gain_chain_not_accredited")
    return SourceMeasurementAssessment(
        status="unavailable_for_validated_l3_inference" if reasons else "measurement_basis_admissible",
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
