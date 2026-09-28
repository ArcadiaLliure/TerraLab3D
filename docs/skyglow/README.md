# Nou sistema físic de contaminació lumínica — índex mestre

> Estat documental: especificació aprovada per implementar; cap element nou d'aquest dossier s'ha de considerar implementat fins que el pas corresponent aporti proves i evidències. Base de repositori inspeccionada: `main@e432454273befdcc7f33cb552d2b58cb0719298f`.

## Autoritat documental

`AGENTS.md` exigeix la skill `plan`. Aquesta skill local no és accessible des de l'entorn actual; per tant s'aplica el protocol de contingència que el mateix `AGENTS.md` prescriu: `docs/README.md`, `docs/normes-arquitectura.md`, passos afectats, inventari funcional i validador documental del repositori. No s'ha inferit cap estat funcional a partir d'esquelets.

## Estat real del repositori

TerraLab3D és actualment Python 3.12+ al backend (`aiohttp`, `astropy`, `numpy`, `rasterio`, `pyproj`, `skyfield`, `spiceypy`) i TypeScript/Three.js al frontend (`three 0.179`, `typescript 5.8`, `esbuild`). El Pas 7 ja ofereix un cel observable amb atmosfera visual, Bortle i magnitud límit, però la contaminació lumínica física nova NO existeix: `domain/light_pollution` conté conversions empíriques Bortle/SQM i un port geogràfic placeholder; `infrastructure/adapters/light_pollution/adapter.py` és abstracte; el shader actual afegeix un glow visual a partir de `u_artificialBrightness`. Això és el sistema a migrar, no una base física que es pugui donar per homologada.

## Decisió central congelada

Hi haurà un únic `PropagationKernel`. Zenit, direccions arbitràries i cúpules són avaluacions del mateix operador físic. Les cúpules són una compressió angular del camp, no un segon model. La moneda interna és radiància lineal; magnituds, SQM, luminància, XYZ/RGB i Bortle són projeccions posteriors.

## Ordre de lectura

1. `01-especificacio-algorismes.md`: física, matemàtiques i pipeline complet.
2. `02-arquitectura-integracio.md`: encaix amb el codi real de TerraLab3D.
3. `03-pipeline-python-typescript-threejs.md`: recorregut executable backend → bridge → frontend → GPU.
4. `04-justificacio-cientifica.md`: bibliografia, fets publicats i separació respecte de decisions pròpies.
5. `05-disseny-tecnic.md`: TDD, responsabilitats, fallades, observabilitat i alternatives.
6. `06-contractes-dades.md`: contractes canònics Python/TypeScript i unitats.
7. `07-benchmark-b0-b7.md`: protocol de benchmark obligatori.
8. `08-validacio-cientifica.md`: validació numèrica, espectral, atmosfèrica, all-sky i contra mesures.
9. `09-incertesa-proveniencia.md`: pressupostos d'error, correlació i cache validity.
10. `10-datasets-llicencies.md`: dades, drets, checksums i actualització.
11. `11-riscs.md`, `12-glossari-unitats.md`, `13-debug.md`, `14-migracio.md`, `15-tracabilitat.md`.
12. `adrs/`: decisions arquitectòniques.

## Decisions congelades

- un únic `PropagationKernel`;
- mostres de cúpula inicials a 0,5°, 2°, 5°, 10°, 20°, 30°, 45°, 60° i 90°; 1° queda candidat;
- reconstrucció PCHIP sobre `log(B + ε)` i suma de fonts en radiància lineal;
- watershed radiomètric per `EmissionRegion` i quadtree intern que no travessa regions;
- separació `NormalizationSpectrum` / `PropagationBandSet`;
- RSR real de VIIRS DNB, amb procedència i checksum;
- `AtmosphericOpticsProvider` separat del kernel i `OpticalField` en tiles/capes;
- `PhaseFunction` unificada; HG és fallback;
- absorció gasosa no nul·la i LUT offline;
- v1 de producció candidata single-scattering, explicitada com a simplificació pròpia;
- Gauss–Kronrod 7/15 adaptatiu com a candidat congelat per benchmark;
- cache invalidada per error de canvi, amb discontinuïtats geomètriques comprovades abans de la linealització;
- benchmark B0–B7 abans de congelar bandes, ordre de Legendre, H_TOA o SLO.

## Candidats pendents de benchmark

`VISIBLE_V1_CANDIDATE` (~8 bandes), mostra a 1°, 95% per `W_effective`, màxim 8 hipòtesis SPD, `H_TOA` 80/100/120 km, ordre de Legendre 4/8/12/20, toleràncies GK, `ε_patch`, límits de cache i SLO de latència/freqüència.

## Verificacions científiques resoltes en aquesta recerca

Cinzano & Falchi (2012) sí descriuen, per a la funció de fase atmosfèrica usada per LPTRAN, els primers 20 coeficients de l'expansió de Legendre (secció 3, entorn de l'eq. 27). El mateix article publica una graella vertical de 32 volums que arriba a 80–100 km a la capa superior tabulada i afirma que, per reduir cost, el càlcul mostrat es limita als primers 120 km horitzontals, amb previsió de 250–300 km per aplicacions precises. Això valida l'atribució històrica, però NO converteix 20 coeficients ni 100 km en paràmetres obligatoris de TerraLab3D.

## Qüestions encara obertes

La biblioteca d'aerosols de producció, la parametrització de núvols, el prior espectral regional/temporal, la política exacta de producte VIIRS/VNL/Black Marble, els models d'incertesa per proveïdor i els SLO de rendiment requereixen passos i evidència propis.

## Relació amb el pla

El dossier introdueix una seqüència de passos de retrofit del Pas 7. El primer pas és infraestructura/benchmark, no el renderer. El punt de represa només s'ha de moure quan els documents de passos, dependències i README del pla quedin actualitzats en el mateix lot documental.