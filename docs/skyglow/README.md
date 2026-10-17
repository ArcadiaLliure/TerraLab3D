# Nou sistema físic de contaminació lumínica — índex mestre

> Estat documental: especificació aprovada per implementar; cap element nou d'aquest dossier s'ha de considerar implementat fins que el pas corresponent aporti proves i evidències. Base de repositori inspeccionada: `main@e432454273befdcc7f33cb552d2b58cb0719298f`.

## Autoritat documental

`AGENTS.md` exigeix la skill `plan`. Aquesta skill local no és accessible des de l'entorn actual; per tant s'aplica el protocol de contingència que el mateix `AGENTS.md` prescriu: `docs/README.md`, `docs/normes-arquitectura.md`, passos afectats, inventari funcional i validador documental del repositori. No s'ha inferit cap estat funcional a partir d'esquelets.

## Estat real del repositori

TerraLab3D és actualment Python 3.12+ al backend (`aiohttp`, `astropy`, `numpy`, `rasterio`, `pyproj`, `skyfield`, `spiceypy`) i TypeScript/Three.js al frontend (`three 0.179`, `typescript 5.8`, `esbuild`). El Pas 7 ja ofereix un cel observable amb atmosfera visual, Bortle i magnitud límit, però la contaminació lumínica física nova NO existeix: `domain/light_pollution` conté conversions empíriques Bortle/SQM i un port geogràfic placeholder; `infrastructure/adapters/light_pollution/adapter.py` és abstracte; el shader actual afegeix un glow visual a partir de `u_artificialBrightness`. Això és el sistema a migrar, no una base física que es pugui donar per homologada.

## Decisió central congelada

La font operativa de la primera vertical és la **família NASA Black Marble VNP46**. VIIRS DNB continua essent el **model de mesura**: RSR real, operador `BAND_INTEGRATED`, procedència temporal i semàntica radiomètrica. VNP46 no es tracta com a flux hemisfèric ni com a skyglow.

El pipeline canònic és `VNP46 → observació → model de mesura DNB → SourceModel (SPD + emissió angular + incertesa) → PropagationKernel espectral → cúpules/projeccions`.

Hi haurà un únic `PropagationKernel`. Zenit, direccions arbitràries i cúpules són avaluacions del mateix operador físic. Precomputació, LUT i FFT només poden ser **backends d'acceleració** del mateix operador i han de demostrar el seu domini de validesa i error; no substitueixen la física ni autoritzen a col·lapsar l'espectre.

Abans de promoure cúpules, la mateixa ruta del kernel a 90° ha de superar el gate zenital. Aquest gate valida la propagació numèrica donat un model de font; la validació empírica de la inferència VNP46→emissió és separada.

## Ordre de lectura

1. `00-inventari-repositori.md`: estat real del codi i punts d'integració.
2. `01-especificacio-algorismes.md`: física, matemàtiques i pipeline complet.
3. `02-arquitectura-integracio.md`: encaix amb el codi real de TerraLab3D.
4. `03-pipeline-python-typescript-threejs.md`: recorregut executable backend → bridge → frontend → GPU.
5. `04-justificacio-cientifica.md`: bibliografia, fets publicats i separació respecte de decisions pròpies.
6. `05-disseny-tecnic.md`: TDD, responsabilitats, fallades, observabilitat i alternatives.
7. `06-contractes-dades.md`: contractes canònics Python/TypeScript i unitats.
8. `07-benchmark-b0-b7.md`: protocol de benchmark obligatori.
9. `08-validacio-cientifica.md`: validació numèrica, espectral, atmosfèrica, all-sky i contra mesures.
10. `09-incertesa-proveniencia.md`: pressupostos d'error, correlació i cache validity.
11. `10-datasets-llicencies.md`: dades, drets, checksums i actualització.
12. `11-riscs.md`, `12-glossari-unitats.md`, `13-debug.md`, `14-migracio.md`, `15-tracabilitat.md`, `16-auditoria.md` i `17-bibliografia.md`.
13. `18-decisions-obertes.md`: decisions científiques i de producte que cap pas pot tancar implícitament.
14. `adrs/`: decisions arquitectòniques.

## Decisions congelades

- un únic `PropagationKernel`;
- mostres de cúpula inicials a 0,5°, 2°, 5°, 10°, 20°, 30°, 45°, 60° i 90°; 1° queda candidat;
- reconstrucció PCHIP sobre `log(B + ε)` i suma de fonts en radiància lineal;
- watershed radiomètric per `EmissionRegion` i quadtree intern que no travessa regions;
- separació `NormalizationSpectrum` / `PropagationBandSet`;
- VNP46 com a família de dades operativa, sense confondre observació amb emissió;
- RSR real de VIIRS DNB, resolta amb release/procedència i data d'adquisició, amb `measurementOperatorId=BAND_INTEGRATED`;
- `AtmosphericOpticsProvider` separat del kernel i `OpticalField` en tiles/capes;
- `PhaseFunction` unificada; HG és fallback;
- absorció gasosa no nul·la i LUT offline;
- v1 de producció candidata single-scattering, explicitada com a simplificació pròpia;
- Gauss–Kronrod 7/15 adaptatiu com a candidat congelat per benchmark;
- cache invalidada per error de canvi, amb discontinuïtats geomètriques comprovades abans de la linealització;
- benchmark B0–B7 per rendiment, ordre de Legendre, H_TOA i SLO; **el nombre de bandes no es tria amb benchmarks** i és configurable;
- gate zenital absolut abans de donar per vàlida la compressió direccional;
- projeccions fotomètriques i de sensor sempre posteriors al kernel: cap conversió directa VNP46/DNB→SQM ni `calibrationFactor` opac;
- `radiancia_observada` i `radiancia_artificial_estimada` separades, sense `max(0,·)` silenciós;
- precomputació/LUT/FFT només com a acceleració homologada contra el mateix operador físic;
- `BortleEquivalent` és una projecció orientativa versionada, no una magnitud física ni ground truth;
- composició del cel en radiància lineal separant com a mínim artificial, natural sense Lluna, Lluna dispersada i crepuscle;
- cap integral LOS al render loop ni una integral nova per frame: cache, coalescing, cancel·lació i precàrrega només si preserven una cota d'error mesurable.

## Configuració espectral i candidats de rendiment

El nombre de bandes de propagació és **parametritzable** (`spectralBandCount`, `bandSetId`, límits i pesos espectrals). No es fixa a vuit ni es fa cap benchmark comparatiu per seleccionar N. Es mantenen proves d'unitats, coherència espectral de la configuració activa i validació científica. Els candidats pendents de benchmark són la mostra a 1°, 95% per `W_effective`, màxim 8 hipòtesis SPD, `H_TOA` 80/100/120 km, ordre de Legendre 4/8/12/20, toleràncies GK, `ε_patch`, límits de cache i SLO.

## Verificacions científiques resoltes en aquesta recerca

Cinzano & Falchi (2012) sí descriuen, per a la funció de fase atmosfèrica usada per LPTRAN, els primers 20 coeficients de l'expansió de Legendre (secció 3, entorn de l'eq. 27). El mateix article publica una graella vertical de 32 volums que arriba a 80–100 km a la capa superior tabulada i afirma que, per reduir cost, el càlcul mostrat es limita als primers 120 km horitzontals, amb previsió de 250–300 km per aplicacions precises. Això valida l'atribució històrica, però NO converteix 20 coeficients ni 100 km en paràmetres obligatoris de TerraLab3D.

## Qüestions encara obertes

El registre autoritatiu és [18-decisions-obertes.md](18-decisions-obertes.md). Hi consten el producte VNP46 concret, emissió angular, oracle de multiple scattering/reference solver, percepció nocturna, radi de fonts, llindars d'acceptació, convergència espectral, punt zero 2017 i política de baixa radiància. Biblioteca d'aerosols/núvols, models d'incertesa per proveïdor i SLO continuen requerint evidència pròpia.

## Relació amb el pla

**Numeració canònica:** els passos abans anomenats 23.50–23.74 són ara **7.1–7.28** en el mateix ordre, sense perdre'n dependències ni abast; **7.29–7.50** reservats per skyglow artificial. El cel físic solar/lunar ocupa **7.51+** i té [dossier propi](../cel-fisic/README.md). El mode simulat actual es manté permanentment i no és una autoritat científica.

El dossier introdueix una seqüència de passos de retrofit del Pas 7. El primer pas és infraestructura/benchmark, no el renderer. El punt de represa només s'ha de moure quan els documents de passos, dependències i README del pla quedin actualitzats en el mateix lot documental.


## Equivalència de numeració anterior

Els identificadors 23.* eren **pendents** i es traslladen sense canviar-ne l'ordre ni donar-los per implementats:

| Identificador anterior | Subpas canònic actual |
|---|---|
| 23.50 | 7.1 |
| 23.51 | 7.2 |
| 23.52 | 7.3 |
| 23.53 | 7.4 |
| 23.54 | 7.5 |
| 23.55 | 7.6 |
| 23.56 | 7.7 |
| 23.57 | 7.8 |
| 23.58 | 7.9 |
| 23.59 | 7.10 |
| 23.60 | 7.11 |
| 23.61 | 7.12 |
| 23.62 | 7.13 |
| 23.63 | 7.14 |
| 23.64 | 7.15 |
| 23.65 | 7.16 |
| 23.66 | 7.17 |
| 23.67 | 7.18 |
| 23.68 | 7.19 |
| 23.681 | 7.20 |
| 23.69 | 7.21 |
| 23.691 | 7.22 |
| 23.692 | 7.23 |
| 23.70 | 7.24 |
| 23.71 | 7.25 |
| 23.72 | 7.26 |
| 23.73 | 7.27 |
| 23.74 | 7.28 |

## Actualitzacions documentals del projecte

`docs/README.md`, l'inventari funcional i el Pas 38 s'han actualitzat en aquest lot. `docs/MANUAL.md` i el `README.md` d'arrel es mantenen deliberadament sense canvis perquè no hi ha cap comportament d'usuari nou implementat; el protocol del projecte prohibeix documentar com a observable una capacitat només especificada.
