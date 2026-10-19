# Pas 7.12 — Gate zenital de transport radiomètric

Tancament del 2026-10-19: **PASS numèric dins del domini condicionat declarat**. Nou fixtures S i sis contrasts addicionals del domini vertical superen el mateix criteri; 42 passades de sostre completades. 444 proves backend, 17 noves, sense avisos. La concordança amb SG-REF valida l'avaluació del model prescrit: **no és exactitud observacional ni homologació urbana C/H**. 7.13 no s'ha començat.

## Criteri prospectiu i traçabilitat

El [preregistre v1](criteri-transport-preregistrat-v1.json) es va congelar a 2026-10-19T14:18:47.645731+00:00; la [vinculació del candidat](campanya-v1/vinculacio-candidat-v1.json), a 2026-10-19T14:28:19.164334+00:00, abans de la primera avaluació. SHA-256 del criteri: **6cfa6601f02dabeb1a3462638e980959c11a12164433738689efb31e92cdb442**. No s'ha modificat després dels residuals; el veredicte viu al [resultat separat](resultat-gate-transport.json).

Mètrica per cas: (abs(I−R_fi)+u_ref)/R_fi ≤10⁻⁴. Resolució exigida a SG-REF: u_ref/R_fi ≤10⁻⁶. u_ref suma dos canvis consecutius de refinament, els tres estimadors GK de LOS i 64 ulp del màxim de les referències. És una estimació de convergència, no aritmètica d'intervals. Cas fosc: zero exacte, sense terra arbitrari de radiància. La jerarquia de dos ordres prové de la resolució d'oracle de 7.6 i d'una assignació numèrica prospectiva molt inferior a 0,01 mag; no dels residuals del candidat.

Refinaments SG-REF: GL espectral 2/4/8, trajecte 4/8/16, àrea 2/4/8 i GK21 relatiu 10⁻⁹/10⁻¹⁰/10⁻¹¹. Runtime: GK7/15 exterior relatiu 10⁻⁷, absolut 10⁻³⁰; trajectes 10⁻⁸/10⁻¹²; àrea 2. Cap factor de calibratge i cap branca especial a 90°. La mateixa classe PropagationKernel conserva geometria, operadors B0/B1/B2/B4 i esquemes històrics.

## Domini i independència

Fixtures deterministes esfèriques ECEF/ENU amb R=6371008,8 m, fonts S d'1 W puntuals o rectangles uniformes 400 × 400 m, muntanya triangular opaca, terreny pla i instantània DEM de 7.11. B1 conserva l'espectre pla històric i calcula 550 nm; B4 usa LED-B3, resposta CIE V i O3 prescrit entre 380–780 nm. Les unitats són respectivament W·m⁻²·sr⁻¹·nm⁻¹ i W·m⁻²·sr⁻¹. No es comparen com la mateixa quantitat.

Els camps estàndard tenen un tile, COESA sec discret fins a 75 km, interpolació lineal de logP i de T i aerosols HG 0,65 amb H 1200 m. La fixture extensa declara pas vertical 5 km; les puntuals, 1 km. Les cambres homogènies sintètiques acaben a 10 km per definició del problema finit, sense declarar aquest sostre suficient per a l'atmosfera terrestre. Observadors 100 m, excepte el cas DEM explícitament vinculat a 148,7701416015625 m (màxim dels nou nusos +100 m); font DEM 58,7701416015625 m. Les trajectòries són rectes sobre una esfera: no inclouen refracció atmosfèrica, el·lipsoide ni conversió geoidal.

El nou SG-REF espectral variable reutilitza la geometria/partició independents de SG-REF, amb mostreig NumPy propi, columnes GL i bases tèrmiques de gas independents. No crida OpticalField.sample/traverse, GK15, SpectralOperator, fases o visibilitat runtime. Les proves substitueixen aquests helpers per errors, contrasten el límit homogeni amb l'oracle anterior i columnes gasoses amb una integral escalar independent. La visibilitat SG-REF usa sistemes lineals/franges, davant interseccions/retalls del runtime. Es comparteixen dades científiques, no aproximacions de transport.

## Decisions per fixture

| Fixture | Decisió | Error relatiu protegit | u_ref/R |
|---|---|---:|---:|
| S_B1_std_point_zenith_5km | PASS | 2.60764077e-12 | 2.60641477e-12 |
| S_B4_std_point_zenith_5km | PASS | 2.75723779e-12 | 9.20129539e-14 |
| S_B4_std_area_zenith_5km | PASS | 6.89496756e-07 | 6.38755414e-07 |
| S_B1_std_point_far_zenith_200km | PASS | 3.21210505e-09 | 3.21210228e-09 |
| S_B1_homog_area_mountain_zenith | PASS | 3.97814644e-07 | 1.53372873e-07 |
| S_B4_homog_area_mountain_zenith | PASS | 3.97668545e-07 | 1.53322256e-07 |
| S_B4_homog_point_mountain_dark_5deg | PASS | zero exacte | zero exacte |
| S_B1_std_far_horizon_200km | PASS | 3.4180709e-09 | 3.41803549e-09 |
| S_B4_homog_realDEM_snapshot | PASS | 6.832459e-12 | 4.19811784e-12 |

Totes les repeticions són exactes en radiància. Màxim protegit: **6,8949675598·10⁻⁷**, davant 10⁻⁴; màxim u_ref/R 6,3875541409·10⁻⁷, davant 10⁻⁶. Els [JSON per cas](campanya-v1/) conserven entrades vinculades, unitats, signatures, comptadors, costos i refinaments. Els casos d'horitzó i DEM es van executar concurrentment en un procés independent amb el mateix codi/inputs: [dispatch anterior](dispatch-fixtures-independents.json) i [transferències sense sobreescriptura](tramesa-fixtures-independents.json).

## Convergència vertical i cua superior

Provider 0–50 km preservat exactament; ampliació optativa COESA 0–75 km versionada. La taula 3 de [NASA TR R-459](https://ntrs.nasa.gov/api/citations/19760017709/downloads/19760017709.pdf) i una integral hidrostàtica independent validen l'extensió. El perfil O3 superior és prescrit, no observat. Vegeu la [derivació i hipòtesis](domini-i-cota-exterior.md).

| Fixture zenital | Mode | Omès a10km respecte50km (%) | Omès a50km respecte75km (%) | Cota superior >75km (mag) |
|---|---|---:|---:|---:|
| pas7.10_original_B4_standard | B1 | 22.794126 | 0.0169496393 | 4.51017475e-06 |
| pas7.10_original_B4_standard | B4 | 22.4487507 | 0.0156126955 | 4.57952031e-06 |
| S_near5km | B1 | 7.4151397 | 0.00165764453 | 3.96916721e-07 |
| S_near5km | B4 | 7.31727897 | 0.00151855827 | 3.99795762e-07 |
| S_far200km | B1 | 62.5853179 | 0.454287024 | 0.000449762194 |
| S_far200km | B4 | 58.5964654 | 0.38402924 | 0.000472296123 |

Es reprodueix **exactament 22,448750675641016%** de 7.10 a B4 original. 50 km tampoc no és un final nul: a 200 km, B1 omet 0,454287% i B4 0,384029% respecte 75 km. El càlcul a 75 km **no posa a zero la resta**: la cota integra fins a l'infinit amb pressió no negativa/no creixent, massa d'aire sec limitada inferiorment, gravetat exterior prescrita i aerosol exponencial. No exigeix P(infinit)=0. Transmissió i visibilitat≤1, intensitat de font/fase/secció eficaç limitades superiorment.

La cota màxima protegida amb R_fi−u_ref és **0,000472296122708 mag**, davant el pressupost independent 0,001 mag. També passen les cinc fixtures primàries estàndard, inclosos horitzó i àrea; resultats a [l'auditoria](resultat-gate-transport.json). Aquesta és una justificació condicionada del domini de fixtures, **no una cota per a qualsevol termosfera real**, H/He, composició arbitrària o atmosfera no hidrostàtica.

![Gate i convergència vertical](gate-i-convergencia-vertical.png)

## Llibre d'errors separat

| Component | Evidència i límit |
|---|---|
| Quadratura LOS/trajectes | [Diagnòstics complets](diagnostics-complets-quadratura.json): a10km estàndard, GK exterior relatiu1,11·10⁻¹⁴ B1 i2,22·10⁻¹¹ B4; màxim error estimat τ8,04·10⁻¹⁵ /2,56·10⁻¹³. Aquests quatre diagnòstics no certifiquen el sostre10km. El gate75km usa els refinaments independents complets. Estimadors, no cotes rigoroses. |
| Àrea / espectre / trajecte de SG-REF | [Controls d'un ordre cada vegada](controls-independents-quadratura.json), mateixa fixture extensa estàndard: canvi àrea2→8 −6,387864645·10⁻⁷; trajecte4→16 3,203148857·10⁻¹¹; espectre2→8 −8,949507802·10⁻¹³. La incertesa decisòria manté la suma conjunta preregistrada, sense descartar el refinament gruixut. |
| Simpson / LUT espectral | Mateixa estratègia Simpson/unió de nusos. A75km, GL amb dades O3 originals0,01nm dona diferència LUT1,31758715·10⁻⁸mag en el punt proper. Cota uniforme de LUT sobre pesos positius i T203–293K; sumada a l'assignació completa de transport, màxim **0,007009282781mag <0,01** en les fixtures B4. |
| Interpolació P/T | Comparació independent de perfils5000/2500/1000/500m: respecte500m,5km canvia −0,5228199% (0,00569134mag),1km −0,0160202% (0,000173951mag). No és error del kernel contra el mateix camp ni prova que500m sigui la solució contínua exacta. |
| DEM / datum | Mateixa malla immutable als dos solucionadors. Es preserva7.11: error de primer impacte de118,32/29,28/4,46m amb graelles10/5/2km, mentre que concordança sobre la mateixa malla és molt més fina. El detall5m del raster no equival a la instantània de nou nusos. No hi ha cota universal de radiància per DEM/datum. |
| Truncament atmosfèric | 42 passades i cota exterior positiva condicionada. Pressupost0,001mag separat de0,01mag; cap contribució superior nul·la assumida. |
| Incertesa física / fonts | No quantificada observacionalment: aerosol/HG real, meteorologia, altres absorbidors, dades experimentals, dispersió múltiple, refracció, geoid, inferència urbana C/H. No s'absorbeix dins la tolerància numèrica ni es calibra amb el residual. |

La [primera cota analítica per perfils](cota-lut-per-perfil.json) de pas 5 km era 0,0131900 mag i no podia certificar 0,01 mag; no era un error observat de radiància. Es conserva. La [cota refinada](cota-lut-refinada-i-pressupost.json) subdivideix analíticament en closques 50 m el **mateix camp interpolat**, sense remostrejar COESA ni canviar inputs/llindars: màxim LUT 0,00690070 mag. El [llibre d'errors](llibre-errors-numerics.json) conserva els contrasts crus. No es declara que la suma de tots els errors físics sigui 0,01 mag.

## Rendiment sense acceleracions

Les passades decisòries i verticals tenen concurrència de fixtures; els seus temps descriuen la campanya, amb CPU/etapes separats, sense inferir acceleració. La comparativa següent es va executar després d'acabar les altres campanyes científiques. Dues passades per configuració: primera avaluació i repetició en procés, excloent construcció d'inputs/arrencada Python. **No són percentils ni cold d'instal·lació.**

900 LOS homogènies històriques,100 fonts,9 elevacions:

| Mode | Primera (s) | Repetició (s) |
|---|---:|---:|
| B0 | 0.467541 | 0.395741 |
| B1 | 20.845979 | 20.867567 |
| B2 | 26.350629 | 26.622899 |
| B4 | 28.769318 | 31.376128 |

Una LOS, rectangle 400 × 400 m i muntanya, medi homogeni 10 km:

| Mode | Primera (s) | Repetició (s) | Oclusió exclusiva a la repetició (s) |
|---|---:|---:|---:|
| B1 | 11.549188 | 11.229721 | 9.380043 |
| B4 | 12.698197 | 12.345203 | 9.179604 |

La fixture estàndard extensa 75 km va costar **594,578/609,084 s per 1 LOS**, amb 450 nodes LOS i 5.886.271 mostres atmosfèriques a la primera passada: geometria 27,773 s; oclusió directa 6,059 s; mostreig 411,495 s; transmissions 26,698 s; quadratura 122,260 s; espectre 0,270 s. El retall genera 25.200 contribucions de font, de mitjana 56 per node LOS, davant 4 nodes inicials: la despesa indirecta de nous trajectes no és només el temps exclusiu d'oclusió. No es repeteixen geometria ni columnes per λ.

Es preserven íntegres 7.9 (20,1933169 s/900 LOS B1),7.10 (p 50 B0/B1/B2/B4:0,3910/21,0034/27,1553/29,4929 s) i 7.11 (cost elevat d'oclusió d'àrees). El nou mostreig no és aparellat amb aquests percentils ni prova cap speedup/SLO. [Mesures actuals, RSS/peak de procés i comptadors](rendiment-b0-b4-actual.json), [memòria del procés principal de gate](campanya-v1/memoria-proces.jsonl). Peak és acumulat de procés; no assignació per petició. Cap cache entre peticions, índex espacial, quadtree, FFT, GPU, compressió o acceleració posterior implementada.

![Cost mesurat de transport i oclusió](cost-transport-i-oclusio.png)

## Compatibilitat, regressions i represa

[C realista/K arxivat](compatibilitat-c-realista-k.json): residuals−2,4114764·10⁻⁷ i−2,4230210·10⁻⁷ contra SG-REF, geometria traslladada explícitament a la muntanya sintètica, escala relativa preservada. Sense PASS observacional ni promoció H.

[444 proves backend](proves-backend.txt),17 noves; cap avís amb avisos convertits a errors. [Ruff/format/Pyright afectats](analisi-estatica.txt) passen. [Pyright global](pyright-global.json):67 errors/3 avisos heretats, mateix multiconjunt normalitzat de diagnòstics, no només recompte. [Regressions](regressions-i-preservacio.json): B0/900 LOS serialitzat SHA21d3453df822b95d56aa508fee6bd9c76e712b27c63f3f03a3222e86e075b53e exacte; quatre resultats de columnes 7.8 exactes;163 evidències anteriors intactes per hash.

Les regles Git protegeixen els bytes del preregistre/mesures i LF dels fitxers nous vinculats davant core.autocrlf de Windows. La reproducció usa una carpeta nova i els CLI del [manual](../../MANUAL.md); l'auditoria final retorna error si manca evidència o falla una condició. El veredicte no s'aplica automàticament a peticions arbitràries del kernel: els marcadors crus històrics es conserven per compatibilitat.

La skill plan s'ha aplicat. La skill addicional terralab-manel-style continua absent de les dues ubicacions locals verificades; s'han seguit les normes accessibles. Cap commit automàtic. **7.13 queda pendent i no iniciat**; haurà de consumir un domini/camp explícits i no donar per vàlid el sostre històric 10 km.

[Auditoria documental](auditoria-documental-resum.json): 375→365 incidències heretades, cap de nova i zero enllaços locals trencats. La reducció prové de normalitzar el pas 7.12; la resta del deute documental es conserva identificat.

[Hashes finals de codi, assets i evidències](codi-i-assets-finals.json). Les quatre signatures d’entrada de la comparativa de 900 LOS coincideixen exactament amb les de 7.10; la variabilitat temporal no es presenta com a canvi del model.
