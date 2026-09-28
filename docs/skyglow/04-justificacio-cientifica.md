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

## VIIRS DNB

**FET PUBLICAT.** NOAA documenta DNB com una banda molt ampla. Per NOAA-20, el NCC publica centre LGS 694,8 nm, punts de mitja alçada 499,1 i 890,5 nm i FWHM 391,4 nm: https://ncc.nesdis.noaa.gov/NOAA-20/StandardizedCalibrationParameters.php. La RSR oficial NOAA-20/J1 és accessible a https://ncc.nesdis.noaa.gov/NOAA-20/J1VIIRS_NOAA20_SpectralResponseFunctions.php.

**FET PUBLICAT.** L'ATBD de calibratge VIIRS indica que la incertesa especificada del DNB depèn del gain state i del nivell de radiància: LGS 5–10%, MGS 10–30%, HGS 30–100% als punts de prova especificats. Font: https://ncc.nesdis.noaa.gov/documents/documentation/gsfc-474-00027-jpss-npp-viirs-radiometric-calibration-atbd--alt.-doc.-no.-d43777-.pdf. **DECISIÓ NOSTRA:** no aplicar aquests percentatges cegament a composites VNL/Black Marble.

**FET PUBLICAT.** VNL V2 de l'Earth Observation Group publica radiància en `nW/cm²/sr`, 15 arcsec, amb composites i màscares; Black Marble VNP46A1 és radiància nocturna TOA a sensor i VNP46A2 aplica correccions lunar/atmosfèrica/BRDF. Fonts: https://eogdata.mines.edu/products/vnl/ i https://viirsland.gsfc.nasa.gov/Products/NASA/BlackMarble.html.

**DECISIÓ NOSTRA.** Cap producte VIIRS es tracta com skyglow a nivell de terra. Sempre passa per un model de font amb procedència.

## Espectre

**FET FÍSIC.** Una única mesura panchromàtica no determina un SPD únic. **DECISIÓ NOSTRA:** representar la forma amb una base/ensemble i normalitzar-la contra la RSR real. Les famílies LED/HPS/LPS/halogenur són candidates de biblioteca, no una base científica definitiva.

**CANDIDAT PENDENT DE BENCHMARK.** 8 bandes de propagació. Es valida contra espectre fi en luminància fotòpica, resposta SQM/TESS, XYZ i radiància propagada.

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

**FET PUBLICAT/OFICIAL.** ERA5 dona camps horaris globals i 137 nivells de model fins aproximadament 80 km; CAMS dona anàlisi/forecast de composició amb espècies químiques i famílies d'aerosol. Fonts: https://www.ecmwf.int/en/forecasts/dataset/ecmwf-reanalysis-v5 i https://www.ecmwf.int/en/forecasts/datasets/cams-global-atmospheric-composition-forecasts.

**DECISIÓ NOSTRA.** `AtmosphericOpticsProvider` pot barrejar camps de proveïdors diferents i conserva procedència/incertesa per camp.

## Punts encara pendents

- PENDENT DE VERIFICACIÓ: llicència/redistribució específica del ZIP RSR de NOAA-20; l'accés públic no és prova suficient de redistribució.
- PENDENT DE DADES: biblioteca SPD amb llicències clares i cobertura de tecnologies modernes.
- PENDENT DE DADES: biblioteca d'aerosols que transformi AOD/RH/composició en `ω0` i coeficients de fase.
- PENDENT DE DADES: microfísica de núvols i política de multiple scattering.