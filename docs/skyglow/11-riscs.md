# Registre de riscos

| Risc | Prob. | Impacte | Detecció | Mitigació | Fallback |
|---|---|---|---|---|---|
| DNB no reconstrueix SPD | alta | alt | dispersió ensemble | priors versionats + validació espectral | interval ampli / prior global |
| prior erroni dins 500–900 nm biaixa escala | mitjana-alta | alt | contrast multi-SPD | ensemble i calibratge extern | confiança baixa |
| aerosol insuficient | alta | alt | error vs ground truth/AOD | biblioteca pròpia + CAMS + RH | HG documentat |
| núvols/multiple scattering | alta | alt en cobert | residus sistemàtics | B6 limitat + solver offline | cel clar o single-scattering etiquetat |
| cost LOS excessiu | mitjana | alt | B0–B7 | vectorització, cache, quadtree, LUT | menys recompute, no menys física silenciosa |
| inestabilitat prop horitzó | mitjana | alt | casos 0,5–2° | segmentació, precisió, referència | limitar qualitat/advertir |
| oclusió DEM incorrecta | mitjana | alt local | fixtures muntanya | mateixa geodèsia + refinament patch | marcar DEM absent |
| llicència RSR/HITRAN/SPD | mitjana | alt | auditoria legal | descàrrega a origen, derivats permesos | no empaquetar |
| drift de productes meteorològics | mitjana | mitjà | versions/provenance | adapters versionats | atmosfera estàndard |
| overfitting de calibratge | mitjana | alt | leave-one-site-out | separació train/validation | paràmetres globals conservadors |
| band set massa pobre | mitjana | mitjà-alt | solver espectral fi | augmentar bandes sense canviar API | band set més ric |
| ordre Legendre insuficient | mitjana | mitjà | B3 | triar per error↔cost | HG/ordre alt |
| cache reutilitza resultat després d'oclusió | baixa si guardes | crític | test flip visible/occluded | topologia primer | invalidació total |
| AD travessa discontinuïtat | mitjana | alt | property tests | AD només branca diferenciable | recompute |
| variabilitat GPU | mitjana | mitjà | benchmark dispositius | buffers simples, zero ciència shader | CPU-side LUT |
| stutter per uploads | mitjana | alt UX | telemetry render | doble buffer/coalescing | conservar resultat anterior |
| APIs externes no disponibles | mitjana | mitjà | health/status | cache persistent + jerarquia provider | reanàlisi/climatologia/standard |

## Riscos bloquejants actuals

Per començar B0/B1 no n'hi ha cap de científic: es poden usar fixtures sintètiques. Per congelar producció sí són bloquejants la biblioteca aerosol, la política SPD, els drets dels recursos i els resultats B0–B7.