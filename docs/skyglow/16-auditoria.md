# Auditoria del disseny

## Decisions confirmades

VNP46/VJ146/VJ246 com a fonts Black Marble candidates independents segons el [perfil v2](skyglow-v2-profile.json), sense prioritat automàtica fins a acreditar domini i qualitat; VIIRS DNB com a model de mesura TOA `BAND_INTEGRATED`, amb correcció L3 separada per producte; observació separada d'emissió estimada; RSR resolta per plataforma/producte/release/guany/data; un kernel espectral únic; radiància lineal; cúpules comprimides; PCHIP log; watershed+quadtree; provider atmosfèric; OpticalField tiled; fase unificada; absorció gasosa; single-scattering v1; LUT/FFT només com a acceleracions homologades del mateix operador; cache error-based; AD només en branques diferenciables.

## Candidats pendents de benchmark

Mostra 1°, 95% `W_effective`, 8 hipòtesis SPD, H_TOA 80/100/120 km, Legendre 4/8/12/20, GK tolerances, `ε_patch`, cache envelopes, SLO. **Bandes:** `spectralBandCount` configurable; cap N fix ni benchmark de selecció.

## Dades i decisions pendents

El producte/release VNP46, la política de baixa radiància i 2017, `S1`, `F5`, `F7` i la política V1 estan documentats al [perfil](skyglow-v1-profile.json). El valor de 7.4 ja està congelat i verificat per al domini tabulat. Resten pendents el model angular d'emissió, les biblioteques SPD/aerosol/núvols, els models d'incertesa per producte i els valors numèrics dels gates 7.12, 7.17 i 7.22. Vegeu [decisions](18-decisions-obertes.md).

## Verificacions científiques resoltes

Els 20 coeficients Legendre i la graella fins 80–100 km sí apareixen explícitament a Cinzano–Falchi 2012. El límit horitzontal 120 km i la previsió 250–300 km també estan verificats. La RSR NOAA-20/J1 pública i els paràmetres DNB 694,8/499,1/890,5/391,4 nm estan verificats.

## Verificacions pendents

Redistribució del ZIP RSR; termes de derivats HITRAN; font/llicència de cada SPD/aerosol/cloud table; incertesa quantitativa de productes VNL/Black Marble concrets.

## Riscos bloquejants

Els valors PASS/FAIL pendents no bloquejaven l'adaptador de 7.2 ni el contracte de mesura TOA/L3 de 7.3, ja completats. **7.4 ha resolt el pressupost de discretització** amb el [requisit de producte preregistrat](../evidencies/pas7.4/criteri-preregistrat-v1.json) i l'[avaluació de 238 integrals](../evidencies/pas7.4/homologacio-bandset-v1.md). El domini és estrictament tabulat i la incertesa de la RSR instrumental continua separada i no quantificada. La [matriu SNPP](../evidencies/pas7.3/recerca-rsr-2026.md) descarta com a substituts les LUT de guany/DN0 i les RSR de 2011/2013; la [matriu NOAA-20/NOAA-21](../evidencies/pas7.3/revisio-multisatel-lit.md) limita les RSR de prelanzament i el proxy MGS→HGS a ús diagnòstic. **7.5 verifica una font S definida**, sense inferència L3; aquesta i la seva incertesa observacional corresponen a 7.16–7.24. 7.10 i 7.14 revalidaran el pressupost per als operadors nous. Aerosols, llicències i ground truth es resolen al primer gate que els requereixi.

## Revisió matemàtica

Les unitats del kernel són consistents si `I↑` és intensitat radiant direccional produïda pel `SourceModel`, de manera que `I↑/r²` és irradiància incident al node. VNP46 no entra directament en aquesta fórmula. `Γ ds` aporta la dispersió direccional i no s'introdueix un segon `1/r_PO²`. La funció de fase està normalitzada a 1 sobre 4π. La suma de fonts es fa en radiància.

## Revisió d'unitats

La unitat del VNP46 es llegeix dels atributs del grànul i es conserva explícita. L'[ATBD VIIRS SDR, §2.1.2.1](https://ncc.nesdis.noaa.gov/documents/documentation/ATBD-VIIRS-RadiometricCal_20131212.pdf#page=38) verifica que DNB és radiància integrada `W cm⁻² sr⁻¹`; VNP46A2.002 usa `nW cm⁻² sr⁻¹`, però és L3 corregit. L'[especificació VJ146](https://ladsweb.modaps.eosdis.nasa.gov/filespec/VIIRS/2/VJ146A2_v2.0) declara la mateixa unitat L3; els atributs de dos VJ146 reals estan [contrastats a 7.3](../evidencies/pas7.3/contrast-granuls-black-marble-c2.md), i VJ246 real resta pendent. SPD normalitzada té `nm⁻¹`. Coeficients d'extinció/dispersió són `m⁻¹`. Angles i distàncies tenen unitat al contracte. La transformació TOA→L3 està documentada a la guia C2; 7.5.1 executa caracterització espectral/angular C relativa NOAA-20. El pressupost d’incertesa de propagació i H continuen pendents.

## Revisió Python/TypeScript

El model conceptual és compartit però les classes internes no travessen el bridge. DTO wire versionat, amb configuració científica snake_case explícita segons el contracte 7.5.1 i escena camelCase; `bandSetId` i unitats obligatòries.

## Següent pas executable

Els [Passos 7.1](../tasques/completat/pas7.1-contracte-cientific-v1.md), [7.2](../tasques/completat/pas7.2-vnp46-observation-adapter.md), [7.3](../tasques/completat/pas7.3-dnb-rsr-measurement.md), [7.4](../tasques/completat/pas7.4-spectral-bandset-validation.md) i [7.5 S](../tasques/completat/pas7.5-source-model-v1.md) estan completats en els seus dominis declarats. **Actualització 2026-10-18:** el punt de represa és [7.6 — SG-REF](../tasques/pendent/pas7.6-sg-ref-reference-solver.md). La [validació S](../evidencies/pas7.5/validacio-source-model-s-v1.md) prova conservació i unitats de fonts definides; el [registre observacional](../evidencies/pas7.5/estat-inferencia-font-2026.md) continua sense RSR/guany/L3 acreditats per al 2026 ni inversió SPD/angular urbana. 7.5.1 completa C relatiu amb biblioteca i controls; cap prova de S/C homologa H.
