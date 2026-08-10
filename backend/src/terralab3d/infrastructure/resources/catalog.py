"""Catàleg de recursos canònics."""

from typing import Dict

from terralab3d.domain.identifiers import ResourceId, VariantId
from terralab3d.domain.resources.models import (
    AcquisitionKind,
    ResourceDescriptor,
    ResourceVariant,
)


class ResourceCatalog:
    """Proporciona la llista de tots els recursos gestionats i les seves variants."""

    def __init__(self) -> None:
        self._descriptors: Dict[ResourceId, ResourceDescriptor] = {}
        self._build_static_catalog()

    def get_descriptor(self, resource_id: ResourceId) -> ResourceDescriptor | None:
        return self._descriptors.get(resource_id)

    def get_all_descriptors(self) -> list[ResourceDescriptor]:
        return list(self._descriptors.values())

    def _register(self, descriptor: ResourceDescriptor) -> None:
        self._descriptors[descriptor.id] = descriptor

    def _build_static_catalog(self) -> None:
        # 1. Via Làctia celestial ICRF/J2000 (NASA SVS 4851).
        # No s'hi admeten les variants *_gal ni els starmap amb estrelles.
        self._register(ResourceDescriptor(
            id=ResourceId("sky.milky_way"),
            title="Via Làctia",
            provider="NASA/Goddard Space Flight Center — Scientific Visualization Studio",
            acquisition_kind=AcquisitionKind.STATIC_FILE,
            source_page_url="https://svs.gsfc.nasa.gov/4851/",
            license="NASA media usage guidelines",
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
                    id=VariantId("4k"),
                    title="4K",
                    source_url="https://svs.gsfc.nasa.gov/vis/a000000/a004800/a004851/milkyway_2020_4k.exr",
                    format="exr", mime_type="image/x-exr",
                    width=4096, height=2048,
                    published_size_label="34.7 MB",
                ),
                ResourceVariant(
                    id=VariantId("8k"),
                    title="8K",
                    source_url="https://svs.gsfc.nasa.gov/vis/a000000/a004800/a004851/milkyway_2020_8k.exr",
                    format="exr", mime_type="image/x-exr",
                    width=8192, height=4096,
                    published_size_label="130.9 MB",
                ),
                ResourceVariant(
                    id=VariantId("16k"),
                    title="16K",
                    source_url="https://svs.gsfc.nasa.gov/vis/a000000/a004800/a004851/milkyway_2020_16k.exr",
                    format="exr", mime_type="image/x-exr",
                    width=16384, height=8192,
                    published_size_label="413.9 MB",
                ),
                ResourceVariant(
                    id=VariantId("32k"),
                    title="32K",
                    source_url="https://svs.gsfc.nasa.gov/vis/a000000/a004800/a004851/milkyway_2020_32k.exr",
                    format="exr", mime_type="image/x-exr",
                    width=32768, height=16384,
                    published_size_label="1.4 GB",
                ),
                ResourceVariant(
                    id=VariantId("64k"),
                    title="64K",
                    source_url="https://svs.gsfc.nasa.gov/vis/a000000/a004800/a004851/milkyway_2020_64k.exr",
                    format="exr", mime_type="image/x-exr",
                    width=65536, height=32768,
                    published_size_label="3.7 GB",
                ),
            )
        ))

        # 2. Pols Planck. El FITS oficial es conserva com a font; el renderer
        # consumeix una cache equirectangular generada localment.
        self._register(ResourceDescriptor(
            id=ResourceId("sky.planck_dust"),
            title="Pols Planck",
            provider="Planck Legacy Archive / NASA-IPAC IRSA",
            acquisition_kind=AcquisitionKind.STATIC_FILE,
            source_page_url="https://irsa.ipac.caltech.edu/data/Planck/release_2/all-sky-maps/previews/COM_CompMap_Dust-GNILC-Model-Opacity_2048_R2.01/",
            credits=("Planck Collaboration", "NASA/IPAC Infrared Science Archive"),
            metadata=(
                ("coordinateFrame", "GALACTIC"),
                ("projection", "HEALPix"),
                ("field", "TAU353"),
                ("derivedProjection", "plate-carree/equirectangular"),
                ("derivedFormat", "png"),
            ),
            variants=(
                ResourceVariant(
                    id=VariantId("r2.01"),
                    title="GNILC τ353 R2.01",
                    source_url="https://irsa.ipac.caltech.edu/data/Planck/release_2/all-sky-maps/maps/component-maps/foregrounds/COM_CompMap_Dust-GNILC-Model-Opacity_2048_R2.01.fits",
                    format="fits", mime_type="application/fits",
                    width=3600, height=1800,
                    published_size_label="~385 MB",
                ),
            )
        ))

        # 3. NGC
        self._register(ResourceDescriptor(
            id=ResourceId("sky.ngc"),
            title="Catàleg NGC",
            provider="OpenNGC",
            acquisition_kind=AcquisitionKind.STATIC_FILE,
            source_page_url="https://github.com/mattiaverga/OpenNGC",
            license="CC BY-SA 4.0",
            credits=("Mattia Verga", "OpenNGC Contributors"),
            variants=(
                ResourceVariant(
                    id=VariantId("master"),
                    title="Master (Mutable)",
                    source_url="https://raw.githubusercontent.com/mattiaverga/OpenNGC/master/database_files/NGC.csv",
                ),
            )
        ))

        # 4. Gaia DR3
        self._register(ResourceDescriptor(
            id=ResourceId("sky.stars.full"),
            title="Catàleg d'Estrelles Gaia",
            provider="ESA / Gaia",
            acquisition_kind=AcquisitionKind.TAP_QUERY,
            source_page_url="https://gea.esac.esa.int/archive/",
            credits=("ESA/Gaia/DPAC",),
            variants=(
                ResourceVariant(
                    id=VariantId("dr3"),
                    title="Gaia DR3",
                ),
            )
        ))

        # 5. Solar System Core Bundle
        self._register(ResourceDescriptor(
            id=ResourceId("solar.core"),
            title="Nucli del Sistema Solar (SPK/PCK)",
            provider="NASA / JPL NAIF",
            acquisition_kind=AcquisitionKind.HTTP_BUNDLE,
            source_page_url="https://naif.jpl.nasa.gov/pub/naif/generic_kernels/",
            variants=(
                ResourceVariant(
                    id=VariantId("de440"),
                    title="Família DE440",
                    published_size_label="~36.2 MiB",
                ),
            )
        ))
        
        # 6. Solar System Jupiter
        self._register(ResourceDescriptor(
            id=ResourceId("solar.jupiter.satellites"),
            title="Satèl·lits de Júpiter",
            provider="NASA / JPL NAIF",
            acquisition_kind=AcquisitionKind.HTTP_BUNDLE,
            dependencies=(ResourceId("solar.core"),),
            variants=(
                ResourceVariant(
                    id=VariantId("default"),
                    title="Catàleg Jup365 + 347/348/349",
                    published_size_label="~2.06 GiB",
                ),
            )
        ))

        # 7. Saturn Rings
        self._register(ResourceDescriptor(
            id=ResourceId("solar.saturn.rings"),
            title="Anells de Saturn",
            provider="Solar System Scope",
            acquisition_kind=AcquisitionKind.STATIC_FILE,
            source_page_url="https://www6.solarsystemscope.com/textures/",
            license="CC BY 4.0",
            variants=(
                ResourceVariant(
                    id=VariantId("2k"),
                    title="2K",
                    source_url="https://www6.solarsystemscope.com/textures/download/2k_saturn_ring_alpha.png",
                ),
                ResourceVariant(
                    id=VariantId("8k"),
                    title="8K",
                    source_url="https://www6.solarsystemscope.com/textures/download/8k_saturn_ring_alpha.png",
                ),
            )
        ))
