# Validació B0 — Pas 7.7

Campanya final iniciada el `2026-10-18T21:54:55.090940+00:00`; finalitzada el `2026-10-18T21:55:25.046018+00:00`. [Pas completat](../../tasques/completat/pas7.7-kernel-geometry-b0.md), [protocol congelat](protocol-b0-v1.json), [JSON complet](resultats-b0-v1.json) i [CSV de passades](passades-b0-v1.csv). Codi base `1ef37d8` que ja inclou el commit de 7.6; 7.7 al working tree. L’agent no ha fet cap commit ni modificació de l’índex.

## Resultat funcional

`PropagationKernel` és executable per API i pel CLI B0. Consumeix SourceModel S/C, observador, DirectionSet, opcions i revisió; calcula geometria ECEF/ENU sobre una esfera de radi 6371008,8 m, LOS fins al sostre definit i segments geomètrics. Integra amb GK7/15 propi, independent de SciPy/SG-REF. Cada resultat conserva revisió, signatura de les entrades, identificador/unitat de l’integrand i comptadors.

**B0 integra 1 i retorna metres, no radiància.** El rectangle emissor només aporta un ancoratge per orientar els LOS. No s’integra l’emissió de la seva àrea ni se n’aproxima la radiància al centre. Els 100 rectangles S sintètics de la sèrie principal són fixtures geomètriques equivalents a regions de benchmark; no s’ha implementat EmissionRegion de producte ni watershed.

`DirectionSet` admet azimut absolut o offset respecte del rumb de cada font. La mostra 90° usa el mateix bucle, segmentador, integrand i quadratura; no existeix un solver zenital separat. Les proves comparen el resultat de 90° dins del conjunt complet amb la petició que conté només aquella mateixa direcció, inclosos els comptadors de nodes.

## Domini, independència i error numèric

La latitud del model esfèric és radial i l’altura està referida a aquesta esfera. ECEF/ENU són coordenades en metres amb azimut nord→est. Això no és una conversió WGS84 el·lipsoïdal, un geoid ni una homologació geodèsica de producte. Esfera i LOS donen geometria de referència B0; el cribratge físic de curvatura, terreny i oclusions continua a 7.11.

La LOS resol la intersecció amb una esfera de radi `R+H` mitjançant l’arrel positiva racionalitzada de la quadràtica. El sostre és 10 km, l’observador a 100 m. La partició talla en plans de cel·les ENU de 20 km i altures 1/5 km. Les cel·les són locals a l’observador i no tenen dades ni versions d’OpticalField; no es presenten com a tiles atmosfèrics.

La parella GK7/15 usa coeficients matemàtics contrastats amb Netlib; la implementació és pròpia. Estimador `|Q15−Q7|` i sòl `50·ε·∫|f|`, refinament del pitjor interval fins al pressupost global. Toleràncies de control: relativa 10⁻⁹ i absoluta 10⁻⁶ en la unitat de la integral; màxim 4.096 intervals per LOS. L’error és estimat, **no un interval garantit**: una discontinuïtat desconeguda o un integrand advers pot enganyar una parella de quadratura. Les discontinuïtats conegudes s’han de segmentar explícitament. Falta de convergència, integrand no finit o límit de treball provoquen excepció.

SG-REF conserva la seva GK21/GL i el seu domini pla homogeni. B0 no reutilitza aquest integrador ni el compara com si ∫1 ds fos radiància atmosfèrica. El contrast amb SG-REF i el gate radiomètric continuen als passos físics i 7.12; cap tolerància de producte es deriva dels residuals d’aquest benchmark.

## Protocol executat

Protocol guardat abans de la primera prova/avaluació, SHA-256 `c12361c2a64a393ed3b9fcf70dc164fba3f7f583edb020897fbecfaba71afb79`. Seed `0x544C3344534B5947`, PCG64; 200 fonts definides amb distàncies superficials 5–80 km i rumbs uniformes. Les sèries són prefixos de la mateixa fixture de 200, amb N=1/10/25/50/100/200. Observador 41,3875° N, 2,1666667° E, altura definida 100 m. Nou elevacions: 0,5/2/5/10/20/30/45/60/90°, azimut cap a la font.

Cinc passades de warm-up completes per configuració, descartades. Trenta passades mesurades per configuració, ordre aleatoritzat per iteració amb seed fix: **180 files CSV**. Durada de la campanya `30.018 s`; desviació del protocol: `None`. No s’ha activat la regla de mínim deu passades si se superen deu minuts.

La finestra mesurada inclou la crida completa al kernel: preparació geomètrica, segments, nodes, construcció del resultat, checkpoints i signatura d’entrada. Serialització d’evidències i consulta RSS es fan fora d’aquesta finestra. B0 mesura evaluate directe: el guard de publicació de la sessió es verifica a les proves, però els seus locks/callbacks externs no formen part d’aquesta campanya. El kernel no té cache de resultats ni LUT. No s’han escombrat bandes espectrals ni escollit cap configuració per aquests temps.

## Maquinari i mètriques

- CPU: **AMD Ryzen 5 5600X 6-Core Processor**, 12 processadors lògics exposats per `os.cpu_count()`.
- RAM física: 34279714816 bytes; sistema `Windows-11-10.0.26200-SP0`.
- Python 3.13.7, NumPy 2.3.3; compilador `MSC v.1944 64 bit (AMD64)`. Flags CFLAGS: `None` perquè aquesta compilació no els exposa.
- GPU no utilitzada. Temperatura/throttling no exposats pel runner: null, sense afirmar absència de throttling.
- Peak RSS de vida del procés: 49754112 bytes (47.45 MiB). A Windows es mesuren WorkingSetSize/PeakWorkingSetSize via GetProcessMemoryInfo i RAM via GlobalMemoryStatusEx. No són assignacions aïllades per iteració ni memòria exclusiva del kernel.

Escriptori sense aïllament de càrrega/temperatura. Els percentils descriuen aquesta campanya; no són SLO, garantia de latència interactiva ni mesura de scattering.

| Fonts | LOS | Segments | Nodes GK | P50 ms | P95 ms | P99 ms |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 9 | 67 | 1005 | 2.637 | 3.564 | 3.689 |
| 10 | 90 | 651 | 9765 | 19.940 | 24.615 | 30.682 |
| 25 | 225 | 1655 | 24825 | 51.219 | 60.383 | 66.821 |
| 50 | 450 | 3305 | 49575 | 100.329 | 114.710 | 121.215 |
| 100 | 900 | 6638 | 99570 | 204.072 | 238.280 | 244.207 |
| 200 | 1800 | 13280 | 199200 | 408.386 | 461.153 | 476.371 |

Sèrie principal: 900 LOS, 6638 segments i 99570 nodes. Totes les sèries tenen zero subdivisions per a l’integrand constant, com correspon a una regla que integra constants. Les proves no trivials exerciten adaptativitat i esgotament del pressupost; aquest zero no implica absència d’adaptativitat implementada.

Identitats verificades a cada passada: `nodes=15·segments+30·subdivisions`, `intervals_finals=segments+subdivisions`, `LOS=9·N`. Diferència màxima entre ∫1 ds i longitud analítica en la sèrie principal: `0 m` a la precisió mostrada de float64; no significa error físic zero. Pressupost prospectiu d’arrodoniment: `64·ε·max(1,L)`; coordenades ECEF contrastades amb PROJ dins `64·ε·R`.

![Escalat de mides i histograma de temps B0](escalat-i-latencia-b0.png)

Cada passada d’una mateixa configuració té exactament la mateixa signatura de resultat i comptadors. Una segona campanya conserva les mateixes signatures geomètriques per a totes sis mides: [comparació](reproducibilitat-b0.json). Els temps poden variar. JSON i CSV comparteixen `runId`/`run_id`; el JSON inclou SHA-256 del codi mesurat del working tree, opcions, totes les fonts i nou exemples de LOS.

## Cancel·lació, revisions i recursos

La revisió i la cancel·lació es comproven a cada node GK, entre fonts i abans de retornar. `GeometricPropagationSession` comprova novament revisió/cancel·lació sota lock abans de publicar. Una prova amb ThreadPoolExecutor bloqueja l’integrand real al primer node, obre una revisió nova i allibera el fil: l’antic càlcul es descarta, no es publica cap parcial, i la revisió vigent es calcula i publica després. No s’usa una cursa basada en sleeps per fer passar el test.

`cancel()` invalida el resultat retingut i causa PropagationCancelledError; una revisió antiga causa StalePropagationError i comptador de descart. `close()` invalida treballs, esborra el resultat de la sessió i rebutja noves peticions. El guard no crea fils ni una cua: no anticipa el scheduler/cache/prefetch de 7.21. Arrays i intervals són locals; cap recurs GPU ni trànsit de bridge.

## Proves, reproducció i documentació

**48 proves noves i 330 proves backend superades.** [Sortida pytest](proves-backend.txt). Inclouen PROJ esfèric independent (pols/antimeridià), ortonormalitat, interseccions, partició contínua, polinomis 0–23 i antiderivada exponencial, discontinuïtat segmentada, adaptativitat/fallada, finitud, S/C, zenit, revisions, cancel·lació i lifecycle.

Ruff i Pyright dels set fitxers nous passen: [comprovacions](comprovacions-codi.txt). `pyright backend/src` conserva els mateixos 67 errors i 3 avisos preexistents, sense diagnòstics nous: [comparació](pyright-backend-comparacio.json). No s’ha modificat el frontend ni s’ha repetit la seva verificació visual de 7.5.1; la UI continua sense radiància d’aquest kernel.

```powershell
python -X utf8 tools/benchmark_skyglow_b0.py --output-dir .runtime-b0-resultats
python -X utf8 tools/plot_skyglow_b0.py --input .runtime-b0-resultats/resultats-b0-v1.json --output .runtime-b0-resultats/escalat-i-latencia-b0.png
python -m pytest backend/tests -q -p no:cacheprovider --basetemp=.runtime-b0-regressio --tb=short
python -X utf8 tools/validate_docs.py
python -X utf8 tools/check_doc_links.py
```

La figura es regenera amb el CLI de plot indicat, amb matplotlib opcional instal·lat (no és una dependència del kernel). El CLI B0 no requereix xarxa ni assets Black Marble; usa fixtures S definides. Ctrl+C interromp la campanya i no declara resultats parcials com a vàlids. Les dades finals s’escriuen després del càlcul mitjançant fitxers temporals i replace; cada fitxer és substituït individualment, i el runId permet detectar una parella JSON/CSV d’execucions diferents si s’interromp durant la publicació.

README, inventari, manual, contractes, perfil v2, traçabilitat i ADR de quadratura actualitzats. 7.7 traslladat a completat; dependència entrant 7.8 normalitzada sense implementar-la. [Auditoria documental](auditoria-documental.txt) i [resum diferencial](auditoria-documental-resum.json): 546 incidències heretades inicials i 534 finals; zero incidències noves i zero enllaços trencats. Tancament documental el 2026-10-19; les marques UTC anteriors corresponen a la campanya mesurada. Es preserven els recursos històrics de 7.1–7.6, el perfil v1 i els criteris radiomètrics anteriors. La skill `plan` s’ha aplicat; `terralab-manel-style` continua absent dels roots de skills accessibles.

**Punt de represa 7.8.** B0 no implementa OpticalField, scattering, absorció física, integració d’emissió d’àrea, DEM/visibilitat, curvatura radiativa, H, AD/cache/LUT, bridge ni renderer. Els gràfics i escenaris B1–B7 es faran quan existeixin aquests components, sense generar placeholders ni llindars retrospectius.

## Fonts consultades el 2026-10-18

- [ESA Navipedia, ECEF/ENU](https://gssc.esa.int/navipedia/index.php/Transformations_between_ECEF_and_ENU_coordinates): convenció i rotacions; B0 n’utilitza explícitament la interpretació esfèrica.
- [Netlib DQK15](https://www.netlib.org/quadpack/dqk15.f): contrast de nodes/pesos matemàtics de la parella 7/15. Implementació pròpia, sense copiar la rutina Fortran ni importar SciPy al kernel.
