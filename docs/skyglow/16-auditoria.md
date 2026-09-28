# Auditoria del disseny

## Decisions confirmades

Un kernel únic; radiància lineal; cúpules comprimides; PCHIP log; watershed+quadtree; RSR real; separació espectral; provider atmosfèric; OpticalField tiled; fase unificada; absorció gasosa; single-scattering v1 com a simplificació pròpia; cache error-based; AD només en branques diferenciables; benchmark abans d'optimitzar.

## Candidats pendents de benchmark

Mostra 1°, 95% `W_effective`, 8 bandes, 8 hipòtesis SPD, H_TOA 80/100/120 km, Legendre 4/8/12/20, GK tolerances, `ε_patch`, cache envelopes, SLO.

## Dades pendents

Biblioteca SPD, biblioteca aerosol, biblioteca núvols, models d'incertesa per producte, selecció final VIIRS/VNL/Black Marble per cas d'ús.

## Verificacions científiques resoltes

Els 20 coeficients Legendre i la graella fins 80–100 km sí apareixen explícitament a Cinzano–Falchi 2012. El límit horitzontal 120 km i la previsió 250–300 km també estan verificats. La RSR NOAA-20/J1 pública i els paràmetres DNB 694,8/499,1/890,5/391,4 nm estan verificats.

## Verificacions pendents

Redistribució del ZIP RSR; termes de derivats HITRAN; font/llicència de cada SPD/aerosol/cloud table; incertesa quantitativa de productes VNL/Black Marble concrets.

## Riscos bloquejants

No bloquegen B0/B1. Bloquegen producció: aerosols, SPD, llicències i benchmark/ground truth.

## Revisió matemàtica

Les unitats del kernel són consistents si `I↑/r²` es tracta com irradiància incident a P i `Γ ds` com probabilitat/densitat direccional de dispersió; no s'introdueix `1/r_PO²`. La funció de fase està normalitzada a 1 sobre 4π. La suma de fonts es fa en radiància.

## Revisió d'unitats

VIIRS VNL (`nW cm⁻² sr⁻¹`) no es barreja directament amb `W m⁻² sr⁻¹`; la conversió és explícita. SPD normalitzada té `nm⁻¹`. Coeficients d'extinció/dispersió són `m⁻¹`. Angles i distàncies tenen unitat al contracte.

## Revisió Python/TypeScript

El model conceptual és compartit però les classes internes no travessen el bridge. DTO wire versionat, camelCase, `bandSetId` i unitats obligatòries.

## Següent pas executable

`Pas 23.50 — Benchmark B0 i infraestructura de mesura`, un cop incorporat formalment a `docs/README.md` i les dependències. No cal esperar la biblioteca aerosol definitiva per començar-lo.