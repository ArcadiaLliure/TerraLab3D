# Nou sistema físic de contaminació lumínica — índex mestre

> **Pla executable canònic per a Codex:** [19-pla-executable-codex.md](19-pla-executable-codex.md). Des del redisseny de 2026-10-17, la numeració 7.1–7.28 es conserva només com a espai de la vertical; **l’ordre i la descomposició antics queden substituïts**. Si una referència de passos dins els documents 00–18 entra en conflicte amb el pla executable, prevalen `docs/README.md`, el document 19 i el fitxer del pas actual.

> Estat documental: especificació aprovada per implementar. El lector local de 7.2 té [proves i contrast amb un grànul VNP46 real](../evidencies/pas7.2/validacio-adaptador.md). El Pas 7.3 ha tancat el [contracte de mesura TOA i interpretació Black Marble L3](../evidencies/pas7.3/contrast-granuls-black-marble-c2.md), amb dos VJ146 reals i QA 0 urbà. La [recerca SNPP](../evidencies/pas7.3/recerca-rsr-2026.md) i la [revisió NOAA-20/NOAA-21](../evidencies/pas7.3/revisio-multisatel-lit.md) encara no acrediten cap RSR aplicable de 2026 ni la inferència física L3→font; cap skyglow físic de producte no està homologat. Base de repositori inspeccionada: `main@e432454273befdcc7f33cb552d2b58cb0719298f`.

## Autoritat documental

`AGENTS.md` exigeix la skill `plan`. S'ha carregat i aplicat el 2026-10-17 per continuar des del Pas 7.1. L'estat del codi i les evidències prevalen sobre els esquelets; no s'ha inferit cap nova capacitat funcional.

## Estat real del repositori

TerraLab3D és actualment Python 3.12+ al backend (`aiohttp`, `astropy`, `numpy`, `rasterio`, `pyproj`, `skyfield`, `spiceypy`) i TypeScript/Three.js al frontend (`three 0.179`, `typescript 5.8`, `esbuild`). El Pas 7 ja ofereix un cel observable amb atmosfera visual, Bortle i magnitud límit, però la contaminació lumínica física nova NO existeix: `domain/light_pollution` conté conversions empíriques Bortle/SQM i un port geogràfic placeholder; `infrastructure/adapters/light_pollution/adapter.py` és abstracte; el shader actual afegeix un glow visual a partir de `u_artificialBrightness`. Això és el sistema a migrar, no una base física que es pugui donar per homologada.

## Decisió central congelada

El [perfil v1](skyglow-v1-profile.json) conserva **VNP46A2 Collection 2** com a font inicial històrica. El [perfil v2](skyglow-v2-profile.json) amplia la política a tres candidats Black Marble independents: Suomi-NPP/VNP46A2, NOAA-20/VJ146A2 i NOAA-21/VJ246A2. El Pas 7.1 ha completat el contracte documental i la política PASS/FAIL `V1`; els valors es preregistren amb evidència als gates 7.4, 7.12, 7.17 i 7.22. El Pas 7.2 ha validat l'adaptador VNP46; el [Pas 7.3](../tasques/completat/pas7.3-dnb-rsr-measurement.md) ha tancat el contracte matemàtic DNB i la semàntica L3 documentada per NASA, amb dos VJ146 reals inspeccionats offline. El punt de represa és **7.4**. VIIRS DNB conserva l'operador `BAND_INTEGRATED` al sensor amb RSR versionada; la correcció L3 és separada i la inferència SPD/angular correspon a 7.5/7.16/7.17. Cap RSR no homologada s'usa com a resposta operativa.

El pipeline canònic és `font Black Marble admissible → observació L3 i QA → model de mesura DNB i correcció L3 per producte → SourceModel (SPD + emissió angular + incertesa) → PropagationKernel espectral → cúpules/projeccions`.

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
- watershed/`EmissionRegion`/quadtree només com a **acceleració posterior** a la validació de la integració directa d’àrea;
- separació `NormalizationSpectrum` / `PropagationBandSet`;
- VNP46/VJ146/VJ246 com a candidats Black Marble independents, amb domini i llinatge propis i sense confondre observació amb emissió;
- RSR real de VIIRS DNB, resolta amb release/procedència i data d'adquisició, amb `measurementOperatorId=BAND_INTEGRATED`;
- `AtmosphericOpticsProvider` separat del kernel i `OpticalField` en tiles/capes;
- `PhaseFunction` unificada; HG és fallback;
- absorció gasosa no nul·la i LUT offline;
- v1 de producció candidata single-scattering, explicitada com a simplificació pròpia;
- Gauss–Kronrod 7/15 adaptatiu com a candidat congelat per benchmark;
- cache/AD només després del gate físic directe, invalidada per cota d’error i discontinuïtats topològiques;
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

El registre autoritatiu continua sent [18-decisions-obertes.md](18-decisions-obertes.md). `DATA-VNP46`, `DNB-2017`, `LOW-RAD`, `S1`, `F5`, `F7`, l'abast de `F6` i la política `V1` estan documentats al perfil v1. Els valors numèrics `V1` resten pendents als seus gates; `V3` es resol a 7.4 i `F1` a 7.5. Una decisió sense evidència suficient bloqueja el primer pas que l'ha d'aplicar, sense retrobloquejar la infraestructura precedent.

## Relació amb el pla

La vertical continua ocupant **7.1–7.28**, però ja **no hereta l’ordre 23.50–23.74**. El nou pla s’ha linealitzat perquè Codex l’executi seqüencialment: contracte/dades → model de mesura i espectre → SourceModel → oracle independent → kernel directe → gate zenital → all-sky/projeccions → atmosfera real/validació → acceleracions → núvols → bridge/renderer/composició → B7.

La regla central és: **cap aproximació es valida contra ella mateixa**. Quadtree, Legendre, AD, cache, precomputació/LUT/FFT apareixen després d’un baseline directe i d’un oracle independent. El document canònic és [19-pla-executable-codex.md](19-pla-executable-codex.md).

## Equivalència de numeració anterior

La taula 23.50–23.74 només conserva valor **històric**. Ja no existeix equivalència semàntica 1:1 amb els nous 7.1–7.28 perquè el backlog s’ha redissenyat per dependències científiques i d’execució. Els documents antics de pas es mantenen únicament com a redireccions cap als nous fitxers executables.

## Actualitzacions documentals del projecte

`docs/README.md`, l'inventari funcional i els passos afectats registren la política multisatèl·lit. `docs/MANUAL.md` descriu només el comportament d'usuari observable; els models de 7.3 encara no estan connectats al producte.
