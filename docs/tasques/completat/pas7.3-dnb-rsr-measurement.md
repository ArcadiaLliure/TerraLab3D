# Pas 7.3 — Model de mesura DNB multisatèl·lit

> Estat: **completat** per al contracte matemàtic i de mesura; cap font nocturna de 2026 homologada per a inferència física. **Estat funcional:** operador TOA, repositori RSR, interpretació L3 NASA i contrast VNP46/VJ146 reals verificats. **Origen:** planificat, criteri de sortida revisat el 2026-10-18. **Abast:** identitat, RSR, guany, unitats i frontera TOA/L3/SourceModel. **Pla:** [19](../../skyglow/19-pla-executable-codex.md).

## Descripció funcional

L'operador calcula radiància integrada **al sensor TOA**. `VNP46A2.002`, `VJ146A2.002` i `VJ246A2.002` són productes **L3 corregits**; la [User Guide C2, §2.2, equació (1)](https://viirsland.gsfc.nasa.gov/PDF/BlackMarbleUserGuide_Collection2.0.pdf) documenta com NASA extrau la radiància nocturna ascendent de superfície a partir de `L_DNB` TOA amb correccions atmosfèriques, lunars, d'albedo i de dosser. La radiància L3 no és la integral TOA sense correcció. Una banda pancromàtica no identifica una SPD única ni emissió angular física; aquest tercer contracte correspon a 7.5/7.16/7.17. [Evidència detallada](../../evidencies/pas7.3/contrast-granuls-black-marble-c2.md).

## Fonts a consultar

- [ATBD VIIRS SDR](https://ncc.nesdis.noaa.gov/documents/documentation/ATBD-VIIRS-RadiometricCal_20131212.pdf), [validació NASA Black Marble](https://viirsland.gsfc.nasa.gov/Val/BM_Val.html), [User Guide C2](https://viirsland.gsfc.nasa.gov/PDF/BlackMarbleUserGuide_Collection2.0.pdf) i [Román et al. 2024](https://aqua.nasa.gov/sites/default/files/1-s2.0-S0034425723005151-main.pdf), consultats el 2026-10-18.
- [NOAA-20 RSR](https://ncc.nesdis.noaa.gov/NOAA-20/J1VIIRS_NOAA20_SpectralResponseFunctions.php), [NOAA-21 RSR](https://ncc.nesdis.noaa.gov/NOAA-21/J2VIIRS_SpectralResponseFunctions.php), [fitxa VJ146](https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/VJ146A2), [file spec VJ146](https://ladsweb.modaps.eosdis.nasa.gov/filespec/VIIRS/2/VJ146A2_v2.0) i [fitxa VJ246](https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/VJ246A2), consultats; ZIP inspeccionats el 2026-10-18.
- [Recerca SNPP 2026](../../evidencies/pas7.3/recerca-rsr-2026.md), [revisió multisatèl·lit](../../evidencies/pas7.3/revisio-multisatel-lit.md), [contrast de la guia i grànuls reals](../../evidencies/pas7.3/contrast-granuls-black-marble-c2.md), [perfil v1 històric](../../skyglow/skyglow-v1-profile.json) i [perfil v2](../../skyglow/skyglow-v2-profile.json).

## Objectiu

Definir i verificar **tres contractes separats**: (1) la integral SPD/radiància espectral TOA → resposta DNB, amb RSR versionada i procedència; (2) la interpretació de la radiància Black Marble L3 corregida segons NASA, amb capa, unitat, QA i llinatge reals; (3) la inferència L3 → SPD i emissió angular, assignada als passos 7.5/7.16/7.17. El pas tanca els dos primers com a **contractes de mesura** i registra per sensor/release/període les RSR encara no homologades. No afirma que una RSR diagnòstica sigui operativa ni que es pugui reconstruir per píxel la correcció de NASA només amb el L3.

## Dependències

**Depèn de:** [7.1 — política V1](pas7.1-contracte-cientific-v1.md) i [7.2 — lector VNP46](pas7.2-vnp46-observation-adapter.md), l'abast verificat del qual no s'estén retrospectivament a VJ146/VJ246.

**En depenen:** [7.4 — bandes espectrals](../pendent/pas7.4-spectral-bandset-validation.md), [7.5 — SourceModel](../pendent/pas7.5-source-model-v1.md), [7.16 — incertesa](../pendent/pas7.16-uncertainty-provenance.md), [7.17 — validació empírica](../pendent/pas7.17-clear-sky-ground-truth.md) i la integració de grànuls amb el [gestor comú del Pas 24](../pendent/pas24-cataleg-recursos-descarregues.md).

## Codi existent a reutilitzar

- **Repositori actual:** [model DNB](../../../backend/src/terralab3d/domain/light_pollution/dnb_measurement.py), [port RSR](../../../backend/src/terralab3d/application/ports/viirs_spectral_response.py), [repositori local](../../../backend/src/terralab3d/infrastructure/adapters/light_pollution/viirs_rsr.py), [observació VNP46](../../../backend/src/terralab3d/domain/light_pollution/vnp46.py), [preparació offline NOAA](../../../tools/prepare_multisat_viirs_rsr.py) i [inspecció offline de grànuls](../../../tools/inspect_black_marble_a2.py).
- **Referències:** taules i documents NOAA/NASA inspeccionats; els assets binaris externs romanen fora del repositori.

## Flux tècnic

Identitat i dia exacte → dades/QA/llinatge → RSR per plataforma/producte/release/guany/data/aplicació → verificació de checksum, unitats, categoria d'evidència i rang → `∫Lλ(TOA)R(λ)dλ` (`Lλ`: `nW cm^-2 sr^-1 nm^-1`; `R`: adimensional) → `BAND_INTEGRATED`, `nW cm^-2 sr^-1`, `at_sensor_toa`. La capa `DNB_BRDF-Corrected_NTL` s'interpreta separadament com a `black_marble_l3_corrected_surface_upward_ntl` segons la guia C2. No es divideix per l'àrea RSR ni s'afegeix de nou `λ` a una RSR energètica. No es converteix radiància L3 en SPD o flux hemisfèric en aquest pas.

El manifest v2 distingeix `official_direct`, `official_reconstructed`, `official_recommended_proxy`, `diagnostic_historical`, `experimental` i `uncertainty_family`; vincle d'una **RSR concreta** amb L3 i incertesa quantificada són estats separats de la correcció L3 **documentada com a algorisme**. El README NOAA-21 recomana MGS com a proxy HGS, però no en dona una cota numèrica: continua diagnòstic. Les corbes de prelanzament preparades es registren com `VIIRS_DNB_TOA`/`at_launch_reference`, no com a RSR L3 VJ146/VJ246 de 2026. SNPP 2013 LGS tampoc és un fallback de 2026.

## Errors, cancel·lació i recursos

RSR absent, ambigua, d'altre dia/producte o release → indisponible; bytes, unitats, forma o evidència obligatòria incompatibles → quarantena. Absència de dades, QA insuficient i model espectral no homologat són causes diferents. Cap gap-fill, substitució temporal, SBAF o clipping implícit. Un grànul J1/J2 real aportat localment o obtingut com a recurs de recerca pot servir de fixture de validació de 7.3, com va passar amb VNP46 a 7.2; no constitueix la ruta d'adquisició del producte. La preparació offline de calibratge no reemplaça el downloader/wizard del [Pas 24](../pendent/pas24-cataleg-recursos-descarregues.md). Integració local sense GPU ni cancel·lació cooperativa.

## Tasques

- [x] Preservar i provar l'operador TOA, unitats, integral, referència fina i no renormalització per àrea.
- [x] Afegir identitat de mesura, classe d'evidència, vincle L3, incertesa i mapping de guany; rebutjar plataforma/producte/data incompatibles.
- [x] Inspeccionar directament els ZIP DAWG NOAA-20/NOAA-21 i les quatre corbes LGS/MGS, preparar manifestos externs amb SHA-256 i procedència reproduïble.
- [x] Verificar noms de grànuls VJ146/VJ246 per al dia/tile del VNP46 real; documentar que HDF5 i OPeNDAP requereixen autenticació.
- [x] Classificar NOAA-21 HGS→MGS com a proxy oficial sense cota, NOAA-20 MGS com a V1 heretada i cap ajust RSR entre sensors C2.
- [x] Inspeccionar dos grànuls VJ146 reals, amb capa, QA/fill, unitats, PGE i `InputPointer`; resoldre la discrepància QA del file spec VJ146 amb la guia C2 i els atributs reals; verificar QA 0 al tile urbà h18v04.
- [x] Separar documentalment l'equació (1) de correcció Black Marble C2 de la integral instrumental TOA i de la inferència L3→font; etiquetar explícitament l'etapa del DTO VNP46.
- [x] Registrar per sensor/producte/release/data la manca d'homologació espectral del 2026, sense prioritat automàtica NOAA-20/NOAA-21 ni fallback; traslladar-ne les exigències d'admissibilitat, incertesa i validació a 7.5/7.16/7.17.

## Criteri de sortida

**Assolit:** integral TOA, unitats, identitat i selecció RSR verificades; la correcció TOA→radiància nocturna de superfície està documentada explícitament per NASA i la semàntica/capa/QA/unitats/llinatge L3 s'han contrastat amb grànuls VNP46 i VJ146 reals, inclòs QA 0. La resposta concreta per a 2026 conserva `unverified` i **no autoritza inferència automàtica**. Aquest pas no exigeix estimar SPD, emissió angular ni les seves incerteses. 7.4 pot construir l'oracle espectral, però no promou cap RSR diagnòstica a operativa.

## Proves i evidències obligatòries

- [x] Proves de la integral, unitats, identitat, incompatibilitat temporal, manifest v2, quarantena i [evidència original](../../evidencies/pas7.3/validacio-model-dnb.md) + [revisió nova](../../evidencies/pas7.3/revisio-multisatel-lit.md).
- [x] ZIP/README/hashes i integral de quatre corbes NOAA reals a la carpeta externa.
- [x] [Contrast de dos grànuls VJ146 reals](../../evidencies/pas7.3/contrast-granuls-black-marble-c2.md): QA/fill, unitats, PGE, InputPointer i QA 0 urbà; el lector VNP46 els rebutja per identitat, com cal.
- [x] [Guia C2 §2.2, equació (1)](https://viirsland.gsfc.nasa.gov/PDF/BlackMarbleUserGuide_Collection2.0.pdf) contrastada amb els atributs L3 reals; inferència espectral i incertesa transferides a 7.5/7.16/7.17.
- [x] Backend complet: 196 proves; Ruff i Pyright correctes als fitxers afectats; 0 enllaços locals trencats als 37 Markdown afectats; validador global amb 631 incidències heretades, cap de nova al document executable de 7.3.

## Fora d'abast

Selecció del `SpectralBandSet` (7.4), inferència SPD/angular (7.5), propagació, wizard/descàrrega (24), acceleracions i renderer. No fixa llindars PASS/FAIL de V1.

## Instrucció per a Codex

Conserva la separació TOA/L3/SourceModel i els estats `unverified` per a RSR concretes sense vincle 2026. El Pas 7.4 pot usar aquests estats com a frontera de l'oracle, però mai una RSR diagnòstica com a font de producció. L'ingesta ordinària dels grànuls J1/J2 correspon al Pas 24.

## Treball pendent

El Pas 7.4 és el següent punt de represa. La RSR nocturna efectiva de 2026 per SNPP/J1/J2, el mapping de guany/producte i les cotes d'incertesa continuen pendents **per homologar fonts** a 7.5/7.16/7.17 i al gate final 7.24/7.28; no són valors inventats ni condicions retroactives de 7.3.
