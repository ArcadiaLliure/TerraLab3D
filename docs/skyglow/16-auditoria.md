# Auditoria del disseny

## Decisions confirmades

VNP46/VJ146/VJ246 com a fonts Black Marble candidates independents segons el [perfil v2](skyglow-v2-profile.json), sense prioritat automàtica fins a acreditar domini i qualitat; VIIRS DNB com a model de mesura TOA `BAND_INTEGRATED`, amb correcció L3 separada per producte; observació separada d'emissió estimada; RSR resolta per plataforma/producte/release/guany/data; un kernel espectral únic; radiància lineal; cúpules comprimides; PCHIP log; watershed+quadtree; provider atmosfèric; OpticalField tiled; fase unificada; absorció gasosa; single-scattering v1; LUT/FFT només com a acceleracions homologades del mateix operador; cache error-based; AD només en branques diferenciables.

## Candidats pendents de benchmark

Mostra 1°, 95% `W_effective`, 8 hipòtesis SPD, H_TOA 80/100/120 km, Legendre 4/8/12/20, GK tolerances, `ε_patch`, cache envelopes, SLO. **Bandes:** `spectralBandCount` configurable; cap N fix ni benchmark de selecció.

## Dades i decisions pendents

El producte/release VNP46, la política de baixa radiància i 2017, `S1`, `F5`, `F7` i la política V1 estan documentats al [perfil](skyglow-v1-profile.json). Resten pendents el model angular d'emissió, les biblioteques SPD/aerosol/núvols, els models d'incertesa per producte i els valors numèrics dels gates 7.4, 7.12, 7.17 i 7.22. Vegeu [decisions](18-decisions-obertes.md).

## Verificacions científiques resoltes

Els 20 coeficients Legendre i la graella fins 80–100 km sí apareixen explícitament a Cinzano–Falchi 2012. El límit horitzontal 120 km i la previsió 250–300 km també estan verificats. La RSR NOAA-20/J1 pública i els paràmetres DNB 694,8/499,1/890,5/391,4 nm estan verificats.

## Verificacions pendents

Redistribució del ZIP RSR; termes de derivats HITRAN; font/llicència de cada SPD/aerosol/cloud table; incertesa quantitativa de productes VNL/Black Marble concrets.

## Riscos bloquejants

Els valors PASS/FAIL encara nuls no bloquegen l'adaptador de 7.2 ni l'operador TOA de 7.3. **El bloqueig propi de 7.3 és la manca d'una cadena nocturna L3 acreditada, amb resposta espectral, correspondència de correccions i incertesa, per almenys un producte i període explícits**, diferent dels llindars V1. La [matriu SNPP](../evidencies/pas7.3/recerca-rsr-2026.md) descarta com a substituts les LUT de guany/DN0 i les RSR de 2011/2013; la [matriu NOAA-20/NOAA-21](../evidencies/pas7.3/revisio-multisatel-lit.md) limita les RSR de prelanzament i el proxy MGS→HGS a ús diagnòstic. Cadascun dels passos posteriors es bloqueja quan necessita aplicar una decisió PASS/FAIL sense origen i valor justificats. Aerosols, SPD, llicències i ground truth s'han de resoldre al primer gate que els requereixi.

## Revisió matemàtica

Les unitats del kernel són consistents si `I↑` és intensitat radiant direccional produïda pel `SourceModel`, de manera que `I↑/r²` és irradiància incident al node. VNP46 no entra directament en aquesta fórmula. `Γ ds` aporta la dispersió direccional i no s'introdueix un segon `1/r_PO²`. La funció de fase està normalitzada a 1 sobre 4π. La suma de fonts es fa en radiància.

## Revisió d'unitats

La unitat del VNP46 es llegeix dels atributs del grànul i es conserva explícita. L'[ATBD VIIRS SDR, §2.1.2.1](https://ncc.nesdis.noaa.gov/documents/documentation/ATBD-VIIRS-RadiometricCal_20131212.pdf#page=38) verifica que DNB és radiància integrada `W cm⁻² sr⁻¹`; VNP46A2.002 usa `nW cm⁻² sr⁻¹`, però és L3 corregit. L'[especificació VJ146](https://ladsweb.modaps.eosdis.nasa.gov/filespec/VIIRS/2/VJ146A2_v2.0) declara la mateixa unitat L3; els atributs VJ146/VJ246 reals resten pendents. SPD normalitzada té `nm⁻¹`. Coeficients d'extinció/dispersió són `m⁻¹`. Angles i distàncies tenen unitat al contracte. El vincle TOA→L3 i el pressupost d'incertesa aplicable continuen pendents per cada font candidata.

## Revisió Python/TypeScript

El model conceptual és compartit però les classes internes no travessen el bridge. DTO wire versionat, camelCase, `bandSetId` i unitats obligatòries.

## Següent pas executable

El [Pas 7.1](../tasques/completat/pas7.1-contracte-cientific-v1.md) és completat documentalment i el [Pas 7.2](../tasques/completat/pas7.2-vnp46-observation-adapter.md) ha validat l'adaptador VNP46 amb fixtures i un grànul real. **Actualització 2026-10-18:** el [Pas 7.3](../tasques/completat/pas7.3-dnb-rsr-measurement.md) ha completat el contracte de mesura TOA/L3 amb la [guia C2 i dos grànuls VJ146](../evidencies/pas7.3/contrast-granuls-black-marble-c2.md); el punt de represa és [7.4](../tasques/pendent/pas7.4-spectral-bandset-validation.md). Les RSR 2026 i la inferència física continuen no homologades; cap ZIP oficial per si sol les acredita.
