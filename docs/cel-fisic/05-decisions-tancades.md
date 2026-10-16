# Decisions tancades 2–8 — cel físic

> **Estat:** decisions arquitectòniques aprovades per planificació. No equivalen a implementació ni homologació.

| # | Decisió | Elecció tancada | Condició de revisió |
|---:|---|---|---|
| 2 | Model lunar | ROLO/USGS per irradiància integrada en disc dins del domini suportat; Hapke/LS per reflectància espacial i extrapolació marcada | evidència que un altre model permissiu ofereix millor traçabilitat/precisió sense empitjorar llicència o cost |
| 3 | Fons nocturn natural | `NaturalNightSkyModel`: airglow paramètric + zodiacal eclíptic + integrated starlight no resolt; Pas 10 manté Via Làctia difusa | dataset/model comercialment compatible i validat que substitueixi una component |
| 4 | Umbrals | pressupost radiomètric amb 0,1 % individual / 0,5 % acumulat com defaults configurables + floor absolut; no tall d'altura solar | els gates científics demostren que cal estrènyer; relaxar requereix ADR + evidència |
| 5 | Garantia del scheduler/pruning | només cota superior conservadora `U`; si no hi ha bound segur, no prune; latest-wins monotònic | prova formal/numerical més forta pot substituir el bound, mai un heuristic visual |
| 6 | Nubes + horitzó + altura/limbe | `CloudOpticalState τ/ω0/g`, delta-Eddington astral, integradors separats; geometria real Terra/DEM/tangència/terminador | model 3D cloud més ric només si conserva unitats, llicència i SLO |
| 7 | Solver/validació | Bruneton espectral/CPU + Hillaire path tracer + ROLO + oracles externs específics; mètriques radiomètriques i instrumentals separades | oracle independent millor i legalment usable |
| 8 | Rendiment | perfil `desktop-60`, latest-wins, LUT/caches; SLO mesurats independentment de `spectralBandCount` | nou perfil hardware explícit o evidència de no complir el producte |

## Principis que no es reobren aquí

- `SkyView LUT` és RGB lineal de visualització.
- La ciència conserva espectre/bandes i respostes instrumentals.
- `spectralBandCount` és configurable; no hi ha competició de N per escollir-lo.
- `PropagationKernel` és artificial; Hillaire/astral és un altre integrador.
- `simulated` i `physical` són modes permanents.
- Cap fallback silenciós ni dades de llicència incerta.
- El halo del limbe surt del transport físic i de la geometria, no d'un efecte gràfic afegit.

## Fonts de decisió

- Hillaire 2020 i repositori MIT: https://github.com/sebh/UnrealEngineSkyAtmosphere
- Bruneton 2017 BSD-3: https://github.com/ebruneton/precomputed_atmospheric_scattering
- ROLO/USGS: https://www.usgs.gov/media/files/rolo-lunar-model-and-database
- Hapke/NASA NTRS: https://ntrs.nasa.gov/citations/19630006060
- ESO Sky Model/SkyCalc: https://www.eso.org/observing/etc/skycalc/
- GAMBONS: https://academic.oup.com/mnras/article/501/4/5443/6056493
- Delta-Eddington/NASA NTRS: https://ntrs.nasa.gov/search.jsp?R=19770033965
- ecRad: https://confluence.ecmwf.int/spaces/ECRAD/overview
- Copernicus licence: https://cds.climate.copernicus.eu/licences/licence-to-use-copernicus-products
- CIEDE2000 (només regressió visual): https://www.cie.co.at/publications/colorimetry-part-6-ciede2000-colour-difference-formula-1

## Regla de governança

Els percentatges i SLO anteriors són **defaults inicials de software**, no constants de la natura ni afirmacions d'exactitud total. Es poden estrènyer amb evidència. Qualsevol relaxació que augmenti error o degradi garanties requereix una decisió documental explícita, fixtures reproduïbles i impacte sobre sensors/visualització.
