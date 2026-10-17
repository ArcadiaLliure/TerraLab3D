# Auditoria del disseny

## Decisions confirmades

VNP46 com a font operativa; VIIRS DNB com a model de mesura `BAND_INTEGRATED`; observació separada d'emissió estimada; RSR resolta per release/data; un kernel espectral únic; radiància lineal; cúpules comprimides; PCHIP log; watershed+quadtree; provider atmosfèric; OpticalField tiled; fase unificada; absorció gasosa; single-scattering v1; LUT/FFT només com a acceleracions homologades del mateix operador; cache error-based; AD només en branques diferenciables.

## Candidats pendents de benchmark

Mostra 1°, 95% `W_effective`, 8 hipòtesis SPD, H_TOA 80/100/120 km, Legendre 4/8/12/20, GK tolerances, `ε_patch`, cache envelopes, SLO. **Bandes:** `spectralBandCount` configurable; cap N fix ni benchmark de selecció.

## Dades i decisions pendents

Producte/release VNP46 concret, política de baixa radiància i punt zero 2017, model angular d'emissió, oracle S1/F5, biblioteca SPD, biblioteca aerosol, biblioteca núvols i models d'incertesa per producte. Vegeu `18-decisions-obertes.md`.

## Verificacions científiques resoltes

Els 20 coeficients Legendre i la graella fins 80–100 km sí apareixen explícitament a Cinzano–Falchi 2012. El límit horitzontal 120 km i la previsió 250–300 km també estan verificats. La RSR NOAA-20/J1 pública i els paràmetres DNB 694,8/499,1/890,5/391,4 nm estan verificats.

## Verificacions pendents

Redistribució del ZIP RSR; termes de derivats HITRAN; font/llicència de cada SPD/aerosol/cloud table; incertesa quantitativa de productes VNL/Black Marble concrets.

## Riscos bloquejants

No bloquegen B0/B1. Bloquegen producció: aerosols, SPD, llicències i benchmark/ground truth.

## Revisió matemàtica

Les unitats del kernel són consistents si `I↑` és intensitat radiant direccional produïda pel `SourceModel`, de manera que `I↑/r²` és irradiància incident al node. VNP46 no entra directament en aquesta fórmula. `Γ ds` aporta la dispersió direccional i no s'introdueix un segon `1/r_PO²`. La funció de fase està normalitzada a 1 sobre 4π. La suma de fonts es fa en radiància.

## Revisió d'unitats

La unitat del producte VNP46 es llegeix del producte/metadata i es conserva explícita. La unitat exacta de l'operador DNB de l'ATBD continua pendent de verificació; no es codifica a partir d'una suposició. SPD normalitzada té `nm⁻¹`. Coeficients d'extinció/dispersió són `m⁻¹`. Angles i distàncies tenen unitat al contracte.

## Revisió Python/TypeScript

El model conceptual és compartit però les classes internes no travessen el bridge. DTO wire versionat, camelCase, `bandSetId` i unitats obligatòries.

## Següent pas executable

`Pas 7.1 — Benchmark B0 i infraestructura de mesura`, un cop incorporat formalment a `docs/README.md` i les dependències. No cal esperar la biblioteca aerosol definitiva per començar-lo.