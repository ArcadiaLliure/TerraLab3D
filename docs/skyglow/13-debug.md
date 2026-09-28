# Manual de depuració i modes diagnòstics

## Modes

- `source-only`: geometria/radiometria de fonts sense atmosfera.
- `natural-only`: cel natural existent, artificial zero.
- `artificial-only`: skyglow físic sense natural.
- `rayleigh-only`: `Γ` només molecular.
- `aerosol-only`: `Γ` només aerosol.
- `cloud-only`: només núvol single-scattering.
- `terrain-occlusion`: colors per visible/occluded i patch refinement.
- `spectral-band`: visualitza una banda/base.
- `optical-tiles`: límits, versions i dependències.
- `cache-dependencies`: quins tiles/terrain/source revisions retenen cada entrada.
- `dome-source`: una sola `EmissionRegion`.
- `los-samples`: segmentació LOS.
- `quadrature-nodes`: nodes GK i subdivisions.
- `phase-function`: `P(θ)` i ordre/coefficients.
- `uncertainty-heatmap`: component d'incertesa dominant.

## Regla de render diagnòstic

Els modes de debug poden usar fals color, però han de mostrar clarament que no són radiometria final. El mode físic no canvia la ciència per fer visible un efecte; el debug aplica una transformació de visualització separada.

## Telemetria per cúpula

`sourceRegionId`, distància, azimut, `W_physical`, `W_effective`, patches visibles/totals, radiància per elevació, dominant scattering component, optical tiles, cache decision, numeric error, prediction interval.

## Incidències típiques

Glow massa ample: revisar geometria de regió i projecció, no shader primer. Pic desplaçat: revisar azimut topocèntric/escorç. Zenit no coincideix amb profile 90°: bug d'arquitectura. Bandes negatives/NaN: revisar LUT/transmissió/normalització. Salt en moure observador: revisar oclusió/topologia/cache. Cúpula canvia amb tone mapping però no radiància: problema de presentació, no kernel.

## Evidència

Cada pas que toqui física afegeix almenys una captura/plot diagnòstic i un JSON de mètriques reproduïble. Els modes de debug no compten com funcionalitat d'usuari fins que estiguin connectats a una UI de desenvolupador.