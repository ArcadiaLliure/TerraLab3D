# Política científica de skyglow — RSR de referència aplicable i dominis S/C/H

Revisió prospectiva del 2026-10-18. No hem renunciat a la RSR: retirem l’exigència d’una RSR anual exacta com a condició universal de desenvolupament. Les evidències històriques 7.1–7.5 i el pressupost preregistrat de 0,01 mag de 7.4 es conserven.

## Pipeline i modalitats

Black Marble amb QA i procedència → caracterització espectral/angular → `SourceModel` → únic SG-REF/PropagationKernel espectral → radiància del cel → visualització. Les fonts S entren directament al mateix contracte de transport. Les dues modalitats són «Simulació realista» i «Simulació per kelvins»; difereixen en les hipòtesis de font, no en el motor atmosfèric.

- **S — DEFINED_SOURCE:** font definida independent de VIIRS, absoluta definida o paramètrica; 7.5 completat en el domini original.
- **C — CONDITIONAL_L3:** observació real L3 amb QA, sensor/producte/release/data/píxel, SPD i angularitat hipotètiques, RSR pública de referència i escala condicionada. Implementat a [7.5.1](../tasques/completat/pas7.5.1-black-marble-spectral-simulation.md) com a font relativa consumible pel futur transport. Cap pes de mescla és una estadística observada; les alternatives no tenen probabilitats inventades.
- **H — OBSERVATION_VALIDATED:** exigeix cadena instrumental/guany/calibratge/TOA–L3 o model empíric acreditat, incerteses justificades, observacions independents i criteris preregistrats. Continua pendent.

Una RSR històrica no certificada per al dia exacte permet C identificat com a aproximació; només es bloquegen afirmacions H o amplituds absolutes injustificades. L’absència d’una publicació anual no demostra estabilitat ni irrellevància del calibratge.

## Conclusió executable RSR

Consulta acotada el 2026-10-18: [NOAA-20 NCC](https://ncc.nesdis.noaa.gov/NOAA-20/J1VIIRS_NOAA20_SpectralResponseFunctions.php) publica la referència final de prel llançament J1 DAWG V2.1 (novembre 2016). El seu README conserva DNB MGS V1 basada en SpMA i LGS fusionada V2 amb filtre de densitat neutra; no són equivalents. S’utilitza **MGS band-average com a hipòtesi de referència**, amb LGS com a contrast; no s’afirma que MGS sigui la resposta efectiva HGS del píxel L3. Els detectors individuals no se substitueixen ni s’agreguen implícitament.

[NOAA-21 NCC](https://ncc.nesdis.noaa.gov/NOAA-21/J2VIIRS_SpectralResponseFunctions.php) publica J2 DAWG V2 (juliol 2019): LGS/MGS mesurades amb GLAMR; el README recomana MGS com a proxy d’HGS no mesurada, sense cota numèrica. No es transfereix aquesta recomanació a NOAA-20. [SNPP NCC](https://ncc.nesdis.noaa.gov/VIIRS/VIIRSSpectralResponseFunctions.php) conserva respostes de 2011/2012 i modulated RSR Release 1.0 de 2013, no una certificació de 2026.

[NASA Black Marble](https://viirsland.gsfc.nasa.gov/Val/BM_Val.html) informa d’estabilitat de forma espectral NOAA-20/21 davant la degradació SNPP, calibratge mensual i absència d’ajust interplataforma RSR a C2. Això dona suport a una referència condicionada del mateix sensor; no equipara sensibilitat absoluta, forma normalitzada, guanys ni correccions TOA–L3. La [guia C2](https://landweb.modaps.eosdis.nasa.gov/data/userguide/BlackMarbleUserGuide_Collection2.0_20241203.pdf), §2.2 i §5.2, preserva la distinció L3/TOA.

Primera connexió executable: `VJ146A2.A2026256.h18v04.002.2026264085938.h5`, NOAA-20, 2026-09-13, capa `DNB_BRDF-Corrected_NTL`, QA 0. `resolve_reference` selecciona mateix sensor i guany entre els epochs publicats instal·lats, rebutja ambigüitat i conserva `validFrom/validThrough`. `resolve` manté la selecció estricta d’operació. No s’allarga cap interval per simular validesa instrumental. Si manca MGS es pot sol·licitar LGS explícitament; si manca una referència verificable del mateix sensor, el cas queda indisponible, sense substituir NOAA-21 ni fabricar una RSR.

No s’ha identificat una parella antiga Black Marble–RSR amb cadena nocturna L3 millor acreditada. Les referències SNPP de 2013 continuen com a contrast històric, no com a validació observacional. Incertesa de mapping HGS, estructura urbana i escala L3→flux: **no quantificada**. La sensibilitat entre MGS/LGS, SPD i angles és una dispersió d’escenaris, no sigma ni interval de confiança.

## Normalització i espectres

42 SPD CIE verificades, amb unitats relatives, suport, resolució, font, llicència i hashes. Família estable de LED de fòsfor B1–B5: rang UI 2.800–6.500 K, interpolació convexa radiant entre veïns i resolució de la CCT efectiva amb CIE 1931 2° / locus de Planck CIE 1960 uv. Planck només defineix el locus, mai fabrica l’SPD LED. La precisió numèrica de cerca és 0,1 K; no acredita exactitud de fabricació. No es fabrica mercuri, LPS ni LED ambre absent del catàleg.

Ancoratge històric L3, font base estimada i substitució hipotètica es conserven separats. Es permet conservar flux fotòpic, potència radiant, resposta DNB de referència o amplitud relativa. En C aquestes magnituds són paramètriques, no lúmens o watts mesurats. La resposta DNB relativa predita varia si es conserva una altra magnitud. Mai es converteix L3 a watts hemisfèrics amb una constant universal.

## Seqüència executable

1. 7.5 continua completat per S; 7.5.1 incorpora biblioteca, escenaris C NOAA-20 i controls amb estat científic real.
2. [7.6 completat](../tasques/completat/pas7.6-sg-ref-reference-solver.md) consumeix S i C al mateix oracle pla homogeni, amb 18 alternatives C reals verificades i contrast F5 independent. No exigeix ni acredita H. 7.7 verifica el kernel geomètric B0; 7.8 verifica el camp estàndard P/T/n i columnes multi-tile; dispersió i transport radiomètric pendents des de 7.9.
3. 7.10/7.14 revaliden SPD, mescles i operadors nous amb el pressupost de 0,01 mag sense relaxar-lo.
4. 7.16 propaga incerteses del transport i hipòtesis; 7.17 separa verificació física de contrast empíric; 7.24 congela resultats per domini.
5. 7.25–7.27 connecten els controls ja existents als resultats, invaliden revisions/caches i visualitzen radiància lineal. Mentre falta transport no hi ha filtre RGB ni radiància fictícia.
6. 7.28 homologa per domini sense convertir una simulació plausible C en H. Pas 24 manté l’adquisició ordinària Black Marble/RSR/SPD al gestor comú; les petites taules CIE verificades són dades base empaquetades.
