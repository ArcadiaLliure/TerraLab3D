# Justificació científica i estat de l'evidència

## Convenció d'etiquetes

- **FET PUBLICAT**: suport directe localitzat.
- **DECISIÓ NOSTRA**: arquitectura TerraLab3D.
- **HIPÒTESI**: model que cal contrastar.
- **CANDIDAT PENDENT DE BENCHMARK**: valor no congelat.
- **PENDENT DE VERIFICACIÓ**: no s'ha localitzat suport primari suficient.

## Transferència de contaminació lumínica

**FET PUBLICAT.** Cinzano & Falchi, *The propagation of light pollution in the atmosphere*, MNRAS 427 (2012) 3337–3357, DOI 10.1111/j.1365-2966.2012.21884.x, presenta EGM/LPTRAN com una solució més general que els Garstang clàssics, amb dispersió múltiple, curvatura terrestre, elevació, aerosols, absorció gasosa, núvols, BRDF i funcions d'emissió variables. Font primària: https://academic.oup.com/mnras/article/427/4/3337/973668.

**FET PUBLICAT, verificat directament.** A la descripció del model, la funció de fase total per capa s'introdueix amb els primers 20 coeficients de l'expansió de Legendre segons convencions DISORT. Això resol l'anterior dubte documental. **DECISIÓ NOSTRA:** TerraLab3D no fixa L=20; benchmarka HG, L=4,8,12,20.

**FET PUBLICAT, verificat directament.** La Taula 1 del mateix article usa 32 volums verticals, amb les darreres capes 50–80 i 80–100 km. **DECISIÓ NOSTRA:** `H_TOA` no es copia; 80/100/120 km es comparen contra solver de referència.

**FET PUBLICAT, verificat directament.** L'article limita a 120 km la computació mostrada per reduir temps i indica 250–300 km per aplicacions precises. Això és un límit horitzontal de font, no l'altura TOA.

**FET PUBLICAT.** Garstang 1986, PASP 98, 364–375, DOI 10.1086/131768, modela brillantor artificial amb dispersió molecular i aerosol i paràmetres de ciutat/atmosfera. És precedent, no especificació de runtime.

## VNP46 i VIIRS DNB

**DECISIÓ NOSTRA, revisada:** el [perfil v1](skyglow-v1-profile.json) va fixar `VNP46A2.002` com a primera font i 7.1/7.2 en van verificar contracte i lector. El [perfil v2](skyglow-v2-profile.json) amplia el disseny a `VJ146A2.002` i `VJ246A2.002` sense reescriure aquella evidència. La [matriu multisatèl·lit](../evidencies/pas7.3/revisio-multisatel-lit.md) mostra per què les tres fonts són candidates, no encara intercanviables ni homologades. La política `V1` continua preregistrada; els valors numèrics es justificaran als gates que els apliquin.

**DECISIÓ NOSTRA:** VIIRS DNB no desapareix de l'arquitectura. Es conserva com a model de mesura espectral: RSR oficial, procedència temporal i `measurementOperatorId=BAND_INTEGRATED`.

**FET PUBLICAT, verificat directament:** l'[ATBD VIIRS SDR](https://ncc.nesdis.noaa.gov/documents/documentation/ATBD-VIIRS-RadiometricCal_20131212.pdf) defineix radiància DNB integrada `W·cm⁻²·sr⁻¹` i RSR energètica amb `λ` incorporat; la [User Guide Black Marble C2 §2.2 Eq. (1)](https://viirsland.gsfc.nasa.gov/PDF/BlackMarbleUserGuide_Collection2.0.pdf) explicita la transformació a radiància nocturna ascendent de superfície L3 corregida, comprovada amb [grànuls VJ146 reals](../evidencies/pas7.3/contrast-granuls-black-marble-c2.md). [NASA](https://viirsland.gsfc.nasa.gov/Val/BM_Val.html) documenta RSR anual SNPP, estabilitat relativa J1/J2 i cap ajust RSR intersensor C2. [NOAA J2](https://ncc.nesdis.noaa.gov/NOAA-21/J2VIIRS_SpectralResponseFunctions.php) publica LGS/MGS de prelanzament; el README recomana MGS com a proxy HGS sense cota. **PENDENT PER A C/H OBSERVACIONAL:** acreditar RSR/guany de 2026 o alternativa justificable, inferència L3→SPD/angular i incertesa a 7.16–7.24. El [SourceModel S](../evidencies/pas7.5/validacio-source-model-s-v1.md) ja es verifica sense VIIRS.

**DECISIÓ NOSTRA:** la RSR es resol de manera compatible amb release/procedència i data d'adquisició; no es tria automàticament l'última.

**FET PUBLICAT, referència concreta:** Coesfeld et al. (2020), §2.3.1, tracten un canvi del valor zero el 2017 en la seva sèrie VIIRS DNB. **DECISIÓ NOSTRA:** les comparacions de baixa radiància pre/post-2017 no es consideren directament homogènies sense política explícita de producte; la correcció numèrica del treball no és una constant universal.

**DECISIÓ NOSTRA:** `radiancia_observada` i `radiancia_artificial_estimada` es mantenen separades. Valors negatius o propers a zero no es clippen silenciosament. Stray light i altres correccions es confirmen per producte/release per evitar doble correcció.

**DECISIÓ NOSTRA:** VNP46 no determina l'SPD ni la distribució angular hemisfèrica. La inferència observacional pertany a C/H i ha de conservar incertesa; el model S només defineix hipòtesis físiques explícites, sense reconstruir VNP46.

## Espectre

**FET FÍSIC.** Una única mesura pancromàtica no determina un SPD únic. **DECISIÓ NOSTRA:** S pot utilitzar formes SPD definides i ensembles sense RSR; C declara RSR de referència, hipòtesis i sensibilitat a 7.5.1. La biblioteca implementada conté LED CIE, HPS, halurs metàl·lics i fluorescents tabulats; LPS i mercuri pur continuen pendents de dades verificades. H exigeix validació addicional.

**DECISIÓ ACTUAL:** nombre de bandes de propagació configurable per `spectralBandCount` i `bandSetId`, sense valor fix ni benchmark per determinar N. La configuració activa es verifica en unitats, integració espectral, luminància fotòpica, SQM/TESS, XYZ i radiància propagada; això no és una campanya de selecció del nombre de bandes.

## Atmosfera i gasos

**FET PUBLICAT.** Cinzano–Falchi 2012 obté perfils atmosfèrics a partir de subrutines SBDART i descriu el model LOWTRAN-7 de gasos degradat a 20 cm⁻¹, aproximadament 5 nm al visible. SBDART: Ricchiazzi et al., BAMS 79 (1998) 2101–2114, DOI 10.1175/1520-0477(1998)079<2101:SARATS>2.0.CO;2.

**FET PUBLICAT.** HITRAN2024 és la versió actual de la base espectroscòpica HITRAN i el paper de referència és Gordon et al. 2026, JQSRT 353, 109807, DOI 10.1016/j.jqsrt.2026.109807: https://www.hitran.org/docs/hitran-papers/.

**DECISIÓ NOSTRA.** HITRAN no s'avalua línia per línia en runtime. S'utilitza offline per construir LUT o per validar una LUT LOWTRAN/SBDART-like. La transmitància de banda es conserva integrant `exp(-τ(λ))`; no s'exponencia una τ mitjana.

## Rayleigh i aerosols

**FET PUBLICAT.** Bodhaine et al. (1999) descriuen el coeficient Rayleigh, la dependència amb índex de refracció i el King factor/depolarització. Referència: J. Atmos. Oceanic Technol. 16, 1854–1861; còpia pública: https://web.gps.caltech.edu/~vijay/Papers/Rayleigh_Scattering/Bodhaine-etal-99.pdf.

**FET PUBLICAT.** Henyey & Greenstein 1941 introdueixen la funció de fase asimètrica clàssica, DOI 10.1086/144246. Mie 1908 és la base electromagnètica per dispersió per esferes, DOI 10.1002/andp.19083300302.

**DECISIÓ NOSTRA.** La interfície de producció és una expansió de Legendre; HG és fallback. La biblioteca d'aerosols real és un projecte de dades separat i encara bloqueja la qualitat absoluta.

## Núvols

**FET PUBLICAT.** Kyba et al. 2011 van mesurar amplificació de luminància del cel sota núvols de 10,1 dins Berlín i 2,8 a 32 km, DOI 10.1371/journal.pone.0017307. Cinzano–Falchi 2012 també incorpora fins a cinc capes de núvol i cita aquest efecte.

**DECISIÓ NOSTRA.** `A_skyglow=B_artificial_cloudy/B_artificial_clear` és diagnòstic derivat. No és un multiplicador d'entrada. **LIMITACIÓ V1:** single-scattering pot infravalorar núvols òpticament gruixuts.

## Mesures de validació

**FET PUBLICAT.** Duriscoe 2016, JQSRT 181, 33–45, DOI 10.1016/j.jqsrt.2016.02.022, defensa indicadors all-sky i mostra que el zenit sol no descriu tota la severitat. **DECISIÓ NOSTRA:** validar hemisferi i banda 0–20°, no només zenit.

**FET PUBLICAT.** Bará et al. 2019 calibren radiomètricament TESS-W i SQM i mostren que cada instrument té una sensibilitat espectral pròpia; DOI 10.3390/s19061336. **DECISIÓ NOSTRA:** simular la resposta espectral real del sensor quan es compara amb ground truth.

## Interpolació i quadratura

**FET PUBLICAT.** Fritsch & Carlson 1980, DOI 10.1137/0717021, construeixen interpolació cúbica monòtona/shape-preserving. **DECISIÓ NOSTRA:** PCHIP sobre log-radiància per compressió vertical; l'adequació específica a skyglow es valida contra all-sky.

**DECISIÓ NOSTRA.** Gauss–Kronrod 7/15 adaptatiu és el candidat de benchmark. La diferència entre regles embegudes és estimador, no una garantia matemàtica universal del límit d'error; el reference solver i casos adversos han de detectar integrands difícils.

## Reanàlisi i forecast

**FET ESTÀNDARD.** CIE 018:2019 fixa el vincle SI entre radiometria i fotometria i la constant `K_cd=683 lm/W`, juntament amb les funcions d'eficiència lluminosa espectral. **DECISIÓ NOSTRA:** la luminància fotòpica és una projecció post-kernel; no s'utilitza per calibrar retrospectivament el camp radiomètric.

**FET PUBLICAT.** L'escala Bortle original (Bortle, 2001) combina criteris observacionals com magnitud límit, Via Làctia, llum zodiacal i visibilitat d'objectes; no és una funció universal d'SQM. **DECISIÓ NOSTRA:** TerraLab3D només exposa `BortleEquivalent` com a diagnòstic versionat sota condicions de referència sense Lluna/crepuscle.

**FET PUBLICAT/OFICIAL.** ERA5 dona camps horaris globals i 137 nivells de model fins aproximadament 80 km; CAMS dona anàlisi/forecast de composició amb espècies químiques i famílies d'aerosol. Fonts: https://www.ecmwf.int/en/forecasts/dataset/ecmwf-reanalysis-v5 i https://www.ecmwf.int/en/forecasts/datasets/cams-global-atmospheric-composition-forecasts.

**DECISIÓ NOSTRA.** `AtmosphericOpticsProvider` pot barrejar camps de proveïdors diferents i conserva procedència/incertesa per camp.

## Punts encara pendents

- PENDENT DE VERIFICACIÓ: llicència/redistribució específica del ZIP RSR de NOAA-20; l'accés públic no és prova suficient de redistribució.
- PENDENT DE DADES: biblioteca SPD amb llicències clares i cobertura de tecnologies modernes.
- PENDENT DE DADES: biblioteca d'aerosols que transformi AOD/RH/composició en `ω0` i coeficients de fase.
- PENDENT DE DADES: microfísica de núvols i política de multiple scattering.
