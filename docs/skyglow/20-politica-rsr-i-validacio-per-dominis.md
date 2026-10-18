# Política científica de skyglow — RSR opcional i tres dominis de validació

> **Revisió prospectiva, 2026-10-18.** Aquesta decisió corregeix dependències del pla, no modifica l'evidència històrica ni els gates preregistrats de 7.1–7.4.

## Decisió

**Es retira l'exigència de trobar la RSR operativa exacta de 2026 per poder desenvolupar el transport físic.** VIIRS DNB és una observació pancromàtica: fins i tot coneixent la RSR exacta, Black Marble L3 no determina de forma única l'SPD, la potència hemisfèrica i l'emissió angular d'una ciutat.

S'han de separar tres dominis, amb estat propi per resultat:

- **S — DEFINED_SOURCE (font física definida):** SPD, geometria, radiància/intensitat o potència física coneguda o escala paramètrica explícita, emissió angular definida. SG-REF i el kernel poden propagar S **sense VIIRS ni RSR**; cap font sintètica no es presenta com una ciutat mesurada.
- **C — CONDITIONAL_L3 (escenari condicionat Black Marble):** L3 amb QA, sensor/producte/data, hipòtesis SPD/angular, RSR pública de referència *identificada com a aproximació*, normalització condicionada i anàlisi de sensibilitat. Pot expressar intervals o famílies d'escenaris; si l'escala absoluta no és defensable, només resultat relatiu o `unavailable`, mai watts inventats.
- **H — OBSERVATION_VALIDATED:** cal cadena sensor/RSR/calibratge/guany/TOA–L3 documentada o model empíric validat dins del seu domini; incertesa justificada, dades observacionals independents, preregistre dels criteris i resultats reproduïbles. Ni QA 0, ni estabilitat del sensor, ni una RSR històrica, ni l'èxit numèric de S fan H automàticament.

**Regla de bloqueig:** mancar una RSR exacta 2026 bloqueja, si escau, només l'afirmació observacional H per aquell producte/període. No bloqueja el SourceModel físic S, SG-REF ni l'optimització validada per S. Les evidències anteriors d'indisponibilitat observacional no es reinterpreten com a èxit.

## Selecció de parella Black Marble–RSR per a recerca

**Primera candidata:** NOAA-20 VIIRS DNB / `VJ146A2.002` + RSR oficial de NOAA-20 de prelanzament, mantenint-ne el mode LGS/MGS/detector i la identitat real. És preferible per **començar a investigar**, perquè hi ha grànuls C2 reals ja contrastats a TerraLab3D, inclòs `h18v04` del 2026-09-13 amb QA 0, i NASA descriu estabilitat espectral del DNB NOAA-20/21 respecte a Suomi-NPP. **Això no verifica una RSR efectiva nocturna de 2026 ni autoritza l'extrapolació automàtica de validesa.** No alterar `l3LinkStatus`, `spectralUncertaintyStatus`, mapping de guany ni `validThrough` sense proves.

**NOAA-21 / `VJ246A2.002`:** alternativa comparable quan s'hagin verificat grànuls reals i modes; el proxy MGS→HGS no és homologat sense cota. **Suomi-NPP / `VNP46A2.002`:** conservar sèries històriques; no perseguir una LUT SNPP anual 2026 com a prerequisit global. Si una altra combinació temporal *més antiga* té millor correspondència documentada de resposta nocturna, processament Black Marble i incertesa, comparar-la i prioritzar-la per qualitat d'evidència, no per recència.

Fonts per a l'auditoria:
- [NASA Black Marble VJ146](https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/VJ146A2) i [validació](https://viirsland.gsfc.nasa.gov/Val/BM_Val.html).
- [NOAA RSR NOAA-20](https://ncc.nesdis.noaa.gov/NOAA-20/J1VIIRS_NOAA20_SpectralResponseFunctions.php) i [NOAA-21](https://ncc.nesdis.noaa.gov/NOAA-21/J2VIIRS_SpectralResponseFunctions.php).
- [Black Marble Collection 2 User Guide](https://landweb.modaps.eosdis.nasa.gov/data/userguide/BlackMarbleUserGuide_Collection2.0_20241203.pdf).
- [Auditoria real de 7.5](../evidencies/pas7.5/estat-inferencia-font-2026.md).

## Seqüència executable

1. **7.5:** construir un `SourceModel` S físic (SPD/angles/geometria/normalització/amplitud/units), reusar el gate observacional ja implementat però sense imposar-lo a S. No començar 7.6 durant la mateixa execució.
2. **7.6–7.15:** SG-REF, transport directe, atmosfera, absorció i projeccions sobre S. Revalidar el `SpectralBandSet` a 7.10 i 7.14.
3. **7.16:** ledger d'incerteses S + estudi implementable de C, incloses respostes de referència i priors, sense inventar interval d'error.
4. **7.17:** gate preacceleracions físic/numèric de S amb oracle independent, amb pressupost preregistrat; **separar** l'eventual validació empírica C/H sobre dades reservades i criteris preregistrats. Si C/H no és avaluable, registrar `not_evaluated` i permetre acceleracions **només de S**. Un oracle numèric no prova el cel real.
5. **7.18–7.23:** accelerar i ampliar el motor en el domini científic verificat.
6. **7.24–7.28:** gates i homologació per domini. Integració de S com a simulació física etiquetada és possible sense H; no activar cap skyglow urbà absolut «real» sense validació observacional.

Preservar tots els resultats passats i la política V1 de llindars (incloent 0,01 mag i 238/238 de 7.4). La revisió de criteri fou documental; posteriorment el [Pas 7.5 ha implementat i verificat `SourceModel` S](../evidencies/pas7.5/validacio-source-model-s-v1.md). El transport S comença a 7.6; cap predicció C/H no es declara implementada.
