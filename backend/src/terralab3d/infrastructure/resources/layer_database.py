import json
import os
from pathlib import Path
from typing import Dict, List

from terralab3d.domain.identifiers import ResourceId, VariantId
from terralab3d.domain.resources.models import (
    AcquisitionKind,
    ResourceDescriptor,
    ResourceVariant,
    ResourceDomain,
    ResourceCategory,
)

CATALOG_SCHEMA_VERSION = 2

def _get_app_data_dir() -> Path:
    # Use standard APPDATA on Windows if available, otherwise fallback to ~/.terralab3d
    appdata = os.environ.get("APPDATA")
    if appdata:
        p = Path(appdata) / "TerraLab3D"
    else:
        p = Path.home() / ".terralab3d"
    p.mkdir(parents=True, exist_ok=True)
    return p

class LayerDatabase:
    """Proporciona accés al catàleg JSON de capes de TerraLab3D."""

    def __init__(self) -> None:
        self.db_path = _get_app_data_dir() / "layers.json"
        self._descriptors: Dict[ResourceId, ResourceDescriptor] = {}
        self.load()

    def load(self) -> None:
        if not self.db_path.exists():
            self._seed_database()
            self.save()
        else:
            with open(self.db_path, "r", encoding="utf-8") as f:
                catalog = json.load(f)

            descriptors: Dict[ResourceId, ResourceDescriptor] = {}
            for item in self._descriptor_items(catalog):
                desc = self._parse_descriptor(item)
                descriptors[desc.id] = desc
            self._descriptors = descriptors

    def save(self) -> None:
        catalog = {
            "schemaVersion": CATALOG_SCHEMA_VERSION,
            "layers": [d.to_dict() for d in self._descriptors.values()],
        }
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(catalog, f, indent=2, ensure_ascii=False)

    def get_descriptor(self, resource_id: ResourceId) -> ResourceDescriptor | None:
        return self._descriptors.get(resource_id)

    def get_all_descriptors(self) -> List[ResourceDescriptor]:
        return list(self._descriptors.values())

    def public_snapshot(self) -> list[dict]:
        """Return catalog descriptors without backend-only acquisition plans."""
        snapshot: list[dict] = []
        for descriptor in self._descriptors.values():
            public_descriptor = descriptor.to_dict()
            for variant in public_descriptor.get("variants", []):
                metadata = variant.get("metadata")
                if isinstance(metadata, dict):
                    metadata.pop("parametricPlan", None)
                if public_descriptor.get("acquisitionKind") == "PARAMETRIC_DOWNLOAD":
                    variant["sourceUrl"] = None
                    variant["sourceUrls"] = []
            snapshot.append(public_descriptor)
        return snapshot

    @staticmethod
    def _descriptor_items(catalog: object) -> list[dict]:
        if isinstance(catalog, list):
            items = catalog
        elif isinstance(catalog, dict):
            items = catalog.get("layers")
            if not isinstance(items, list):
                raise ValueError("El catàleg de capes no conté una llista 'layers' vàlida")
        else:
            raise ValueError("El catàleg de capes ha de ser una llista o un objecte JSON")

        if not all(isinstance(item, dict) for item in items):
            raise ValueError("Tots els elements del catàleg de capes han de ser objectes JSON")
        return items

    def _parse_descriptor(self, data: dict) -> ResourceDescriptor:
        variants = []
        for v in data.get("variants", []):
            variants.append(ResourceVariant(
                id=VariantId(v["id"]),
                title=v["title"],
                source_url=v.get("sourceUrl"),
                source_urls=tuple(v.get("sourceUrls", [])),
                format=v.get("format"),
                mime_type=v.get("mimeType"),
                width=v.get("width"),
                height=v.get("height"),
                published_size_label=v.get("publishedSizeLabel"),
                expected_bytes=v.get("expectedBytes"),
                metadata=tuple(v.get("metadata", {}).items())
            ))
        
        return ResourceDescriptor(
            id=ResourceId(data["id"]),
            name=data["name"],
            description=data.get("description", ""),
            domain=ResourceDomain(data["domain"]),
            category=ResourceCategory(data["category"]),
            provider=data["provider"],
            acquisition_kind=AcquisitionKind(data["acquisitionKind"]),
            citation=data.get("citation", ""),
            license=data.get("license", ""),
            original_source_url=data.get("originalSourceUrl"),
            direct_url=data.get("directUrl"),
            variants=tuple(variants),
            credits=tuple(data.get("credits", [])),
            dependencies=tuple(ResourceId(d) for d in data.get("dependencies", [])),
            metadata=tuple(data.get("metadata", {}).items())
        )

    def _seed_database(self) -> None:
        def register(desc: ResourceDescriptor):
            self._descriptors[desc.id] = desc

        # 1. Via Làctia
        register(ResourceDescriptor(
            id=ResourceId("sky.milky_way"),
            name="Via Làctia",
            description="Mapa profund estel·lar complet elaborat per la NASA SVS (2020).",
            domain=ResourceDomain.SKY,
            category=ResourceCategory.DEEP_SKY,
            provider="NASA/Goddard Space Flight Center — Scientific Visualization Studio",
            acquisition_kind=AcquisitionKind.STATIC_FILE,
            citation="Goddard Space Flight Center Scientific Visualization Studio. (2020). Deep Star Maps 2020.",
            license="NASA media usage guidelines",
            original_source_url="https://svs.gsfc.nasa.gov/4851/",
            direct_url=None,
            credits=(
                "NASA/Goddard Space Flight Center",
                "Scientific Visualization Studio",
                "Deep Star Maps 2020 — SVS ID 4851",
            ),
            metadata=(
                ("coordinateFrame", "ICRF/J2000"),
                ("projection", "plate-carree/equirectangular"),
                ("raAtHorizontalCenterHours", 0.0),
                ("raIncreases", "left"),
                ("declinationIncreases", "up"),
                ("containsBrightHipparcosTychoStars", False),
            ),
            variants=(
                ResourceVariant(
                    id=VariantId("4k"), title="4K",
                    source_url="https://svs.gsfc.nasa.gov/vis/a000000/a004800/a004851/milkyway_2020_4k.exr",
                    format="exr", mime_type="image/x-exr", width=4096, height=2048, published_size_label="34.7 MB",
                ),
                ResourceVariant(
                    id=VariantId("8k"), title="8K",
                    source_url="https://svs.gsfc.nasa.gov/vis/a000000/a004800/a004851/milkyway_2020_8k.exr",
                    format="exr", mime_type="image/x-exr", width=8192, height=4096, published_size_label="130.9 MB",
                ),
                ResourceVariant(
                    id=VariantId("16k"), title="16K",
                    source_url="https://svs.gsfc.nasa.gov/vis/a000000/a004800/a004851/milkyway_2020_16k.exr",
                    format="exr", mime_type="image/x-exr", width=16384, height=8192, published_size_label="413.9 MB",
                ),
                ResourceVariant(
                    id=VariantId("32k"), title="32K",
                    source_url="https://svs.gsfc.nasa.gov/vis/a000000/a004800/a004851/milkyway_2020_32k.exr",
                    format="exr", mime_type="image/x-exr", width=32768, height=16384, published_size_label="1.4 GB",
                ),
                ResourceVariant(
                    id=VariantId("64k"), title="64K",
                    source_url="https://svs.gsfc.nasa.gov/vis/a000000/a004800/a004851/milkyway_2020_64k.exr",
                    format="exr", mime_type="image/x-exr", width=65536, height=32768, published_size_label="3.7 GB",
                ),
            )
        ))

        # 2. Pols Planck
        register(ResourceDescriptor(
            id=ResourceId("sky.planck_dust"),
            name="Pols Planck",
            description="Model d'opacitat de pols GNILC de Planck (2015).",
            domain=ResourceDomain.SKY,
            category=ResourceCategory.DEEP_SKY,
            provider="Planck Legacy Archive / NASA-IPAC IRSA",
            acquisition_kind=AcquisitionKind.STATIC_FILE,
            citation="Planck Collaboration (2016). Planck 2015 results. X. Dust GNILC model opacity.",
            license="ESA/Planck",
            original_source_url="https://irsa.ipac.caltech.edu/data/Planck/release_2/all-sky-maps/previews/COM_CompMap_Dust-GNILC-Model-Opacity_2048_R2.01/",
            credits=("Planck Collaboration", "NASA/IPAC Infrared Science Archive"),
            metadata=(
                ("coordinateFrame", "GALACTIC"),
                ("projection", "HEALPix"),
                ("field", "TAU353"),
            ),
            variants=(
                ResourceVariant(
                    id=VariantId("r2.01"), title="GNILC τ353 R2.01",
                    source_url="https://irsa.ipac.caltech.edu/data/Planck/release_2/all-sky-maps/maps/component-maps/foregrounds/COM_CompMap_Dust-GNILC-Model-Opacity_2048_R2.01.fits",
                    format="fits", mime_type="application/fits", width=3600, height=1800, published_size_label="~385 MB",
                ),
            )
        ))

        # 3. NGC
        register(ResourceDescriptor(
            id=ResourceId("sky.ngc"),
            name="Catàleg NGC",
            description="OpenNGC: Base de dades d'objectes NGC i IC.",
            domain=ResourceDomain.SKY,
            category=ResourceCategory.DEEP_SKY,
            provider="OpenNGC",
            acquisition_kind=AcquisitionKind.STATIC_FILE,
            citation="Verga, M. (2023). OpenNGC: A database of NGC and IC objects.",
            license="CC BY-SA 4.0",
            original_source_url="https://github.com/mattiaverga/OpenNGC",
            credits=("Mattia Verga", "OpenNGC Contributors"),
            variants=(
                ResourceVariant(
                    id=VariantId("pinned"), title="OpenNGC (da90466)",
                    source_url="https://raw.githubusercontent.com/mattiaverga/OpenNGC/da90466031b0372c896588b85be6016c617e205b/database_files/NGC.csv",
                ),
            )
        ))

        # 4. Gaia DR3
        register(ResourceDescriptor(
            id=ResourceId("sky.stars.full"),
            name="Catàleg d'Estrelles Gaia",
            description="Gaia Data Release 3. Conté milions de posicions estel·lars.",
            domain=ResourceDomain.SKY,
            category=ResourceCategory.DEEP_SKY,
            provider="ESA / Gaia",
            acquisition_kind=AcquisitionKind.TAP_QUERY,
            citation="Gaia Collaboration et al. (2023). Gaia Data Release 3. Summary of the content and survey properties.",
            license="ESA/Gaia",
            original_source_url="https://gea.esac.esa.int/archive/",
            credits=("ESA/Gaia/DPAC",),
            variants=(
                ResourceVariant(id=VariantId("dr3"), title="Gaia DR3"),
            )
        ))

        # 5. Copernicus DEM (Terra)
        register(ResourceDescriptor(
            id=ResourceId("earth.elevation.copernicus"),
            name="Copernicus DEM GLO-30",
            description="Model d'elevació digital global a 30m de resolució.",
            domain=ResourceDomain.EARTH,
            category=ResourceCategory.ELEVATION,
            provider="Copernicus Data Space Ecosystem",
            acquisition_kind=AcquisitionKind.PARAMETRIC_DOWNLOAD,
            citation="Copernicus DEM GLO-30. (2020). European Space Agency. DOI: 10.5270/ESA-c5d3d65",
            license="Free and Open",
            original_source_url="https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-dem",
            credits=("© European Union", "Copernicus Space Component"),
            variants=(
                ResourceVariant(id=VariantId("glo-30"), title="GLO-30 (30m)"),
            )
        ))

        # 6. Copernicus Land Cover (Terra)
        register(ResourceDescriptor(
            id=ResourceId("earth.land_cover.copernicus"),
            name="Global Dynamic Land Cover",
            description="Cobertura del sòl dinàmica a nivell global amb resolució de 100m.",
            domain=ResourceDomain.EARTH,
            category=ResourceCategory.LAND_COVER,
            provider="Copernicus Global Land Service",
            acquisition_kind=AcquisitionKind.PARAMETRIC_DOWNLOAD,
            citation="Buchhorn, M. et al. (2020). Copernicus Global Land Cover Layers—Collection 2.",
            license="Free and open access",
            original_source_url="https://land.copernicus.eu/global/products/lc",
            credits=("© European Union", "Copernicus Land Monitoring Service"),
            variants=(
                ResourceVariant(id=VariantId("100m-2019"), title="100m - 2019"),
            )
        ))

        # 7. Efemèrides Planetàries (SPK)
        register(ResourceDescriptor(
            id=ResourceId("solar.core.ephemeris"),
            name="Efemèrides Planetàries (SPK)",
            description="Famílies de kernels (DE440s, DE421) per al càlcul de la posició dels planetes i la Lluna.",
            domain=ResourceDomain.SKY,
            category=ResourceCategory.SOLAR_SYSTEM,
            provider="NASA / JPL NAIF",
            acquisition_kind=AcquisitionKind.HTTP_BUNDLE,
            citation="Acton, C. H. (1996). Ancillary data services of NASA's Navigation and Ancillary Information Facility.",
            license="NASA Public Domain",
            original_source_url="https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/",
            variants=(
                ResourceVariant(
                    id=VariantId("de440s"), title="Família DE440s", published_size_label="~31.2 MiB",
                    source_urls=(
                        "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de440s.bsp",
                    )
                ),
                ResourceVariant(
                    id=VariantId("de421"), title="Família DE421", published_size_label="~17 MiB",
                    source_urls=(
                        "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/a_old_versions/de421.bsp",
                    )
                ),
            )
        ))

        # 8. Constants del Sistema Solar (PCK/LSK)
        register(ResourceDescriptor(
            id=ResourceId("solar.core.constants"),
            name="Constants i Temps (PCK/LSK)",
            description="Lleis d'orientació, radis planetaris (PCK) i segons intercalars (LSK).",
            domain=ResourceDomain.SKY,
            category=ResourceCategory.SOLAR_SYSTEM,
            provider="NASA / JPL NAIF",
            acquisition_kind=AcquisitionKind.HTTP_BUNDLE,
            citation="NASA / JPL NAIF.",
            license="NASA Public Domain",
            original_source_url="https://naif.jpl.nasa.gov/pub/naif/generic_kernels/",
            variants=(
                ResourceVariant(
                    id=VariantId("constants_default"), title="PCK i LSK per defecte", published_size_label="Mida desconeguda",
                    source_urls=(
                        "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/pck00011.tpc",
                        "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/earth_latest_high_prec.bpc",
                        "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/lsk/naif0012.tls",
                        "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/moon_pa_de421_1900-2050.bpc",
                    )
                ),
            )
        ))

        # 9. Satèl·lits de Mart
        register(ResourceDescriptor(
            id=ResourceId("solar.satellites.mars"),
            name="Satèl·lits de Mart",
            description="Efemèrides dels satèl·lits marcians (mar099s).",
            domain=ResourceDomain.SKY,
            category=ResourceCategory.SOLAR_SYSTEM,
            provider="NASA / JPL NAIF",
            acquisition_kind=AcquisitionKind.HTTP_BUNDLE,
            citation="NASA / JPL NAIF. Mars Satellite Ephemerides.",
            license="NASA Public Domain",
            original_source_url="https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/",
            dependencies=(ResourceId("solar.core.ephemeris"),),
            variants=(
                ResourceVariant(
                    id=VariantId("mar099s"), title="mar099s", published_size_label="~64 MiB", expected_bytes=67594240,
                    source_urls=(
                        "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/mar099s.bsp",
                    )
                ),
            )
        ))

        # 10. Satèl·lits de Júpiter
        register(ResourceDescriptor(
            id=ResourceId("solar.satellites.jupiter"),
            name="Satèl·lits de Júpiter",
            description="Efemèrides dels satèl·lits jovians (jup365, jup347-349).",
            domain=ResourceDomain.SKY,
            category=ResourceCategory.SOLAR_SYSTEM,
            provider="NASA / JPL NAIF",
            acquisition_kind=AcquisitionKind.HTTP_BUNDLE,
            citation="NASA / JPL NAIF. Jupiter Jovian Satellite Ephemerides.",
            license="NASA Public Domain",
            original_source_url="https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/",
            dependencies=(ResourceId("solar.core.ephemeris"),),
            variants=(
                ResourceVariant(
                    id=VariantId("default"), title="Catàleg Jup365 + 347/348/349", published_size_label="~2.06 GiB", expected_bytes=2215238656,
                    source_urls=(
                        "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/jup365.bsp",
                        "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/jup347.bsp",
                        "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/jup348.bsp",
                        "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/jup349.bsp",
                    )
                ),
            )
        ))

        # 11. Satèl·lits de Saturn
        register(ResourceDescriptor(
            id=ResourceId("solar.satellites.saturn"),
            name="Satèl·lits de Saturn",
            description="Efemèrides dels satèl·lits saturnians (sat441, sat415, etc.).",
            domain=ResourceDomain.SKY,
            category=ResourceCategory.SOLAR_SYSTEM,
            provider="NASA / JPL NAIF",
            acquisition_kind=AcquisitionKind.HTTP_BUNDLE,
            citation="NASA / JPL NAIF. Saturn Satellite Ephemerides.",
            license="NASA Public Domain",
            original_source_url="https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/",
            dependencies=(ResourceId("solar.core.ephemeris"),),
            variants=(
                ResourceVariant(
                    id=VariantId("default"), title="Kernels SAT (Múltiples)", published_size_label="~1.8 GiB", expected_bytes=1994689536,
                    source_urls=(
                        "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/sat393_daphnis.bsp",
                        "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/sat415.bsp",
                        "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/sat441.bsp",
                        "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/sat455.bsp",
                        "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/sat456.bsp",
                        "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/sat457.bsp",
                        "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/sat459.bsp",
                        "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/sat480.bsp",
                    )
                ),
            )
        ))

        # 12. Satèl·lits d'Urà
        register(ResourceDescriptor(
            id=ResourceId("solar.satellites.uranus"),
            name="Satèl·lits d'Urà",
            description="Efemèrides dels satèl·lits uranians (ura184).",
            domain=ResourceDomain.SKY,
            category=ResourceCategory.SOLAR_SYSTEM,
            provider="NASA / JPL NAIF",
            acquisition_kind=AcquisitionKind.HTTP_BUNDLE,
            citation="NASA / JPL NAIF. Uranus Satellite Ephemerides.",
            license="NASA Public Domain",
            original_source_url="https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/",
            dependencies=(ResourceId("solar.core.ephemeris"),),
            variants=(
                ResourceVariant(
                    id=VariantId("ura184"), title="ura184 (1, 2, 3)", published_size_label="~4.3 GiB", expected_bytes=4511944704,
                    source_urls=(
                        "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/ura184_part-1.bsp",
                        "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/ura184_part-2.bsp",
                        "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/ura184_part-3.bsp",
                    )
                ),
            )
        ))

        # 13. Satèl·lits de Neptú
        register(ResourceDescriptor(
            id=ResourceId("solar.satellites.neptune"),
            name="Satèl·lits de Neptú",
            description="Efemèrides dels satèl·lits neptunians (nep098, nep104, nep105).",
            domain=ResourceDomain.SKY,
            category=ResourceCategory.SOLAR_SYSTEM,
            provider="NASA / JPL NAIF",
            acquisition_kind=AcquisitionKind.HTTP_BUNDLE,
            citation="NASA / JPL NAIF. Neptune Satellite Ephemerides.",
            license="NASA Public Domain",
            original_source_url="https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/",
            dependencies=(ResourceId("solar.core.ephemeris"),),
            variants=(
                ResourceVariant(
                    id=VariantId("default"), title="Kernels NEP (Múltiples)", published_size_label="~4.6 GiB", expected_bytes=4949300224,
                    source_urls=(
                        "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/nep098_part-1.bsp",
                        "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/nep098_part-2.bsp",
                        "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/nep098_part-3.bsp",
                        "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/nep104.bsp",
                        "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/nep105.bsp",
                    )
                ),
            )
        ))

        # 14. Satèl·lits de Plutó
        register(ResourceDescriptor(
            id=ResourceId("solar.satellites.pluto"),
            name="Satèl·lits de Plutó",
            description="Efemèrides dels satèl·lits plutonians (plu060).",
            domain=ResourceDomain.SKY,
            category=ResourceCategory.SOLAR_SYSTEM,
            provider="NASA / JPL NAIF",
            acquisition_kind=AcquisitionKind.HTTP_BUNDLE,
            citation="NASA / JPL NAIF. Pluto Satellite Ephemerides.",
            license="NASA Public Domain",
            original_source_url="https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/",
            dependencies=(ResourceId("solar.core.ephemeris"),),
            variants=(
                ResourceVariant(
                    id=VariantId("plu060"), title="plu060", published_size_label="~129 MiB", expected_bytes=135207936,
                    source_urls=(
                        "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/plu060.bsp",
                    )
                ),
            )
        ))

        # 15. Anells de Saturn
        register(ResourceDescriptor(
            id=ResourceId("solar.saturn.rings"),
            name="Anells de Saturn",
            description="Textura d'alta resolució dels anells de Saturn.",
            domain=ResourceDomain.SKY,
            category=ResourceCategory.SOLAR_SYSTEM,
            provider="Solar System Scope",
            acquisition_kind=AcquisitionKind.STATIC_FILE,
            citation="Solar System Scope. High Resolution Planet Textures.",
            license="CC BY 4.0",
            original_source_url="https://www.solarsystemscope.com/textures/",
            variants=(
                ResourceVariant(id=VariantId("2k"), title="2K", source_url="https://www.solarsystemscope.com/textures/download/2k_saturn_ring_alpha.png"),
                ResourceVariant(id=VariantId("8k"), title="8K", source_url="https://www.solarsystemscope.com/textures/download/8k_saturn_ring_alpha.png"),
            )
        ))

        # 16. Superfície de la Lluna
        register(ResourceDescriptor(
            id=ResourceId("solar.moon.surface"),
            name="Superfície de la Lluna",
            description="Textura d'alta resolució de la Lluna.",
            domain=ResourceDomain.SKY,
            category=ResourceCategory.SOLAR_SYSTEM,
            provider="Solar System Scope",
            acquisition_kind=AcquisitionKind.STATIC_FILE,
            citation="Solar System Scope. High Resolution Planet Textures.",
            license="CC BY 4.0",
            original_source_url="https://www.solarsystemscope.com/textures/",
            variants=(
                ResourceVariant(id=VariantId("2k"), title="2K", source_url="https://www.solarsystemscope.com/textures/download/2k_moon.jpg"),
                ResourceVariant(id=VariantId("8k"), title="8K", source_url="https://www.solarsystemscope.com/textures/download/8k_moon.jpg"),
            )
        ))

        # 17. Contaminació Lumínica DVNL (Terra)
        register(ResourceDescriptor(
            id=ResourceId("earth.light_pollution.dvnl"),
            name="Earth Observation Group DVNL",
            description="Mapa global VIIRS de llum nocturna (2020).",
            domain=ResourceDomain.EARTH,
            category=ResourceCategory.LIGHT_POLLUTION,
            provider="Earth Observation Group (EOG)",
            acquisition_kind=AcquisitionKind.STATIC_FILE,
            citation="Elvidge, C. D. et al. (2021). A global VIIRS nighttime light map.",
            license="Open Data",
            original_source_url="https://eogdata.mines.edu/products/vnl/",
            variants=(
                ResourceVariant(
                    id=VariantId("2020"), title="VNL V2 2020",
                    source_url="https://eogdata.mines.edu/nighttime_light/annual/v21/2020/VNL_v21_npp_2020_global_vcmslcfg_c202102150000.average_masked.tif.gz",
                ),
            )
        ))
