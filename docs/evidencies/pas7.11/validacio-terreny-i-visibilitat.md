# Pas 7.11 — Validació de terreny, curvatura i visibilitat

**2026-10-19. Completat offline en el domini declarat. 427 proves backend, 22 noves.** El kernel incorpora terreny opac en B0/B1/B2/B4; les comparacions de radiància amb SG-REF són diagnòstiques. **7.12 no s'ha executat.** No es declara transport urbà homologat, H ni radiància connectada al renderer.

## Implementació i procedència

REUSE: `ElevationPort`, `ElevationBatchRequest`, `RasterioElevationAdapter`, `SphericalFrame`, GK15, SourceModel, OpticalField i TransportProfiler. ADAPT: kernel, transport B1/espectral i SG-REF. NEW: `TerrainSurface`, `TerrainVisibility`, constructor d'aplicació i oracle de terreny. El perfil d'horitzó 2D no substitueix la comprovació font→P. No s'ha copiat codi ni afegit cap dependència.

La mateixa esfera de radi **6371008,8 m** i les transformacions ECEF/ENU de 7.7 posicionen els vèrtexs DEM, fonts i observador. La superfície física és la malla triangular ECEF, amb diagonal SW→NE declarada. No és el·lipsoide WGS84 ni reproducció exacta de la interpolació bilineal del raster original. La graella triada i la seva aproximació són part de l'entrada; no es fa un suavitzat del relleu per accelerar el transport.

`build_terrain_surface` consumeix el port existent en EPSG:4326, exigeix conversió vertical i interpretació explícites, conserva procedència/màscara/índexs i rebutja nodata. El CRS horitzontal no acredita el datum vertical. La comprovació amb la biblioteca configurada EPSG:25831 de **5 m**, amb **681 fonts** descobertes, utilitza només **9 nusos/8 triangles**: és una demostració d'I/O real amb assignació explícita de l'altura numèrica a l'esfera, sense certificació geoidal. [Instantània reproduïble](dem-real-snapshot.json), [resultat i altures](dem-real-resultat.json). No s'ha alterat la biblioteca externa ni se n'ha empaquetat el raster.

L'envolupant superior és un **límit prescrit obligatori del model**, no una deducció sobre muntanyes desconegudes a partir del màxim local. Per sota d'aquesta envolupant, una porció potencialment terrestre sense DEM causa error. La cobertura és la unió dels cons radials dels triangles, no un rectangle pla ni una hipòtesi de convexitat dels paral·lels. Només s'exigeix cobertura fins al primer obstacle de l'observador. Una intersecció coneguda ja prova que un trajecte de font és ocult; si es vol declarar visible, cal demostrar la cobertura de tota la part susceptible de tocar terra.

## Visibilitat, discontinuïtats i àrea

L'observador integra fins a `min(s_TOA,s_terrain)`. El contacte inicial que entra al sòl o continua sobre la superfície produeix longitud i integral nul·les. L’observador enterrat, la geometria singular i els radis incompatibles produeixen error; els modes radiatius també rebutgen fonts enterrades. B0 continua sent ∫1 ds sobre la LOS truncada: no activa emissió ni visibilitat de trajectes de font. Les tangències interiors i els segments coplanaris són opacs; el contacte inicial d'una font al sòl no elimina l'emissió ascendent.

Per a una font puntual es calculen totes les fronteres d'ombra cara/aresta amb la LOS. Cada interval obert té una màscara **booleana**; els punts exactes de frontera tenen l'estat calculat geomètricament. No s'interpola la visibilitat. La màscara i les interseccions són independents de λ i es comparteixen dins la petició. No hi ha reutilització per moviment ni entre revisions.

Una font rectangular es retalla contra els volums d'ombra dels triangles. Els polígons visibles disjunts s'integren amb GL/Duffy i pesos `dA/A`; intensitat, distància, fase i transmissions s'avaluen a cada node. La fracció visible no multiplica una radiància de centre ni és transparència assignada. S'inclouen esdeveniments cantonada/aresta de relleu i vèrtex de relleu/aresta de font. Les escletxes geomètriques a escala d'arrodoniment ECEF es descarten amb àrea quantificada: màxim observat **2.8100327e-10** de l'àrea emissora en el refinament S. No és un llindar d'acceptació radiomètrica.

Hi ha checkpoints durant interseccions, plans i retalls, i descart de revisió obsoleta abans de publicar. Els pressupostos de segments/polígons i el límit del constructor de 65.536 vèrtexs fallen explícitament; no coarsenen silenciosament el DEM. El domini conserva altures no negatives i elevacions 0,5–90° de 7.7, i una regió menor que un hemisferi. No inclou refracció, edificis no representats ni relleu absent de la graella.

## Fixtures i SG-REF independent

[Protocol geomètric i de rendiment](protocol-visibilitat-v1.json), [protocol de contrast d'àrea](protocol-contrast-area-v1.json), [malla sintètica](fixture-muntanya.json), [topologia i flips](topologia-i-flips.json), [radiàncies](diagnostic-transport.json) i [refinament d'àrea](diagnostic-area.json).

Els **200 trajectes** aleatoris reproduïbles concorden en runtime, pla d'intervals i SG-REF. El salt puntual és a **s=2291.426185228 m**; els mostreigs a ±0,1 mm i ±1 cm conserven el salt binari. Amb muntanya i elevació 5°, la LOS es trunca a **2127,273726 m**, abans dels 103948,419315 m del sostre de 10 km. La font extensa passa per estats parcialment visibles sense fer transparent el relleu. En els 41 punts del perfil d’àrea, la diferència màxima de fracció visible respecte a l’oracle independent és 2,54·10⁻¹⁰; a la frontera puntual exacta tots dos motors retornen ocult.

La corda entre punts a 100 m d'altura i separació de 200 km queda oculta; elevar l'extrem a 10 km la fa visible en la mateixa malla. El primer tall de la malla convergeix cap a la solució esfèrica analítica: error de **118,32 / 29,28 / 4,46 m** amb espaiats **10 / 5 / 2 km**. Runtime i SG-REF coincideixen en el tall de cada malla. Aquest resultat distingeix l'error de discretització DEM de l'acord entre dos motors sobre les mateixes dades.

SG-REF comparteix **dades immutables**, no helpers de visibilitat: resol els triangles amb sistemes lineals NumPy, calcula les particions pròpies i integra l'àrea per un arranjament de rectes/franges, independent del retall de polígons runtime. Manté GK21/GL i geometria/mostreig/transmissió independents. Proves amb helpers runtime prohibits comproven aquesta separació. Els medis espectrals complets contrastats aquí són homogenis prescrits; no s'amplia la referència espectral a tot l'aire terrestre variable.

| Cas | Residual relatiu runtime/referència−1 | Últim refinament relatiu SG-REF |
|---|---:|---:|
| B1_point_zenith | -2.1094237e-15 | 0 |
| B1_point_low | no definit (tots dos zero) | no definit |
| B2_point_zenith | 1.6007196e-11 | 0 |
| B4_point_zenith | 9.9853459e-13 | 0 |
| B4_C_realistic_relocated_synthetic | -2.4114764e-07 | 1.5115413e-07 |
| B4_C_kelvin_relocated_synthetic | -2.423021e-07 | 1.5193619e-07 |
| B1_area | -1.3961532e-10 | -4.5519144e-15 |

Les fonts **C** conserven SPD, amplitud relativa i `sourceMode` dels JSON realista i kelvins de 7.5.1; **només es trasllada la geometria** al rectangle sintètic 400×400 m. No són observacions noves de Barcelona. Les transformacions i hashes originals consten a [realista](input-c-realistic.json) i [kelvins](input-c-kelvin.json).

En S extensa, l'ordre per defecte 2 difereix de la referència fina en **-2.4444177e-07**; runtime 4 i 8 pràcticament coincideixen. SG-REF 4→8 varia **-4.5519144e-15**. La referència C 2→4 encara varia ~1,5·10⁻⁷: es conserva aquesta incertesa, sense seleccionar tolerància a partir del residual. **No hi ha PASS/FAIL numèric de transport de 7.12.**

![Topologia i visibilitat binària de la fixture](topologia-i-visibilitat.png)

## Cost computacional mesurat

Campanya final aïllada d'altres feines numèriques Codex: **90 LOS**, 10 identificadors de font puntual a la mateixa posició de 5 km, 9 elevacions; 1 warm-up i **5 passades mesurades per configuració**, ordre barrejat amb llavor 711. 12 configuracions, 60 mesures i 12 warm-ups. És una fixture de control diferent dels 100 emplaçaments/900 LOS històrics; **no s'extrapola a 900 LOS** ni es declara SLO.

| Mode | Terreny | P50 s/90 LOS | P95 s/90 LOS | Mitjana exclusiva oclusió s |
|---|---|---:|---:|---:|
| B0 | sense DEM | 0.0418 | 0.0431 | 0.0000 |
| B0 | DEM pla | 0.0670 | 0.0901 | 0.0264 |
| B0 | muntanya | 0.0528 | 0.0612 | 0.0343 |
| B1 | sense DEM | 3.6362 | 3.7093 | 0.0000 |
| B1 | DEM pla | 4.0992 | 4.2227 | 0.2090 |
| B1 | muntanya | 1.3732 | 1.3780 | 0.2988 |
| B2 | sense DEM | 4.6894 | 4.8036 | 0.0000 |
| B2 | DEM pla | 5.3927 | 5.5565 | 0.2115 |
| B2 | muntanya | 1.6567 | 1.7740 | 0.3028 |
| B4 | sense DEM | 5.0984 | 5.1764 | 0.0000 |
| B4 | DEM pla | 5.7407 | 5.9111 | 0.2123 |
| B4 | muntanya | 1.7777 | 1.8041 | 0.3003 |

El DEM pla preserva la visibilitat i mostra el cost afegit de comprovacions/particions. La muntanya canvia la física i elimina treball radiatiu: la reducció del temps total no és una acceleració a igual treball. Les dades conserven geometria, mostreig atmosfèric, transmissions, quadratura, integració espectral i **oclusió** com etapes exclusives; aquesta última inclou preparació dels polígons/nodes d'àrea visibles. Tots els comptadors i signatures són a [la campanya final](rendiment-b0-b1-b2-b4.json). El [preassaig](rendiment-preliminar-sense-estats-frontera.json), anterior al tractament exacte dels punts de frontera, es conserva sense emprar-lo per a aquestes conclusions.

| Etapa exclusiva B4 | DEM pla (s/90 LOS) | Muntanya (s/90 LOS) |
|---|---:|---:|
| Geometria | 2.4233 | 0.6013 |
| Mostreig atmosfèric | 1.0130 | 0.3195 |
| Transmissions | 0.8775 | 0.1834 |
| Quadratura i dispatch | 1.0940 | 0.2850 |
| Integració espectral | 0.1403 | 0.0551 |
| Oclusió | 0.2123 | 0.3003 |

Fonts extenses: 1 LOS zenital, ordre d'àrea 2, 1 warm-up i **3 mesures aïllades** per configuració:

| Mode/terreny | P50 s/LOS | Mitjana exclusiva oclusió s |
|---|---:|---:|
| B1/none | 0.0114 | 0.0000 |
| B1/mountain | 11.2799 | 9.3296 |
| B4/none | 0.0700 | 0.0000 |
| B4/mountain | 12.5276 | 9.2549 |

El refinament S d'ordre 8 va costar **137.97 s/LOS** en la passada diagnòstica, coexecutada parcialment amb comprovacions; no és un percentil aïllat. El cost de l'àrea directa continua sent alt i queda visible, sense introduir índexs espacials, quadtree, FFT, AD, cache de moviment o aproximacions dels passos següents.

Entorn: AMD Ryzen 5 5600X 6-Core Processor; Python 3.13.7, NumPy 2.3.3, Windows-11-10.0.26200-SP0. Pic RSS del procés de campanya **80.80 MiB**; RAM física **31.93 GiB**. És memòria del procés complet, no una atribució exclusiva al DEM.

![Cost mesurat per mode i terreny](cost-oclusio.png)

## Pressupostos, regressions i límits conservats

- **Sostre atmosfèric:** a la fixture B4 estàndard zenital de 7.10, 10 km omet **22,448750675641016%** respecte a 50 km. La cua per damunt de 50 km és desconeguda. Aquests diagnòstics a 10 km no acrediten que el sostre sigui suficient: **la justificació definitiva correspon al gate 7.12, no executat**.
- **Espectre:** es preserven les 111.168 integrals i 326.040 T_eff de 7.10 i el pressupost preregistrat **0,01 mag** en el seu domini. L'AST de `SpectralOperator` no ha canviat; la nova visibilitat és acromàtica i els pesos geomètrics són no negatius. [Regressió de l'operador](regressio-operador-espectral.json). No es presenta 0,01 mag com error total de DEM, àrea, transport o sostre.
- **B0 i columnes:** la serialització/comptadors de 900 LOS conserva exactament el golden `21d3453df822b95d56aa508fee6bd9c76e712b27c63f3f03a3222e86e075b53e`; quatre resultats serialitzats de columnes de 7.8 idèntics. [Prova](regressio-columnes-i-b0.json). Sense terreny es preserven esquemes 1/2/3/4; amb terreny s'utilitza schema 5 amb procedència, signatura, longituds i treball geomètric.
- **Proves:** [427 superades, 22 noves](pytest-backend-final.txt), [Ruff](ruff-final.txt) i [Pyright afectat](pyright-afectat-final.txt) sense errors. [Pyright global](pyright-comparacio.json): els mateixos **67 errors/3 avisos heretats**, amb comparació del multiconjunt de diagnòstics, no només recompte.
- **Història:** les **133 evidències preexistents de 7.1–7.10** es preserven per SHA-256. [Manifest](preservacio-historica.json). [Auditoria documental](auditoria-documental-resum.json) i enllaços locals verificats al tancament.
- **Límits de producte:** O3 prescrit i dispersió simple; no aire terrestre complet, escala urbana absoluta, inversió d'emissió, validació H ni renderer nou.

## Reproducció i fonts

Des de l'arrel del repositori, amb el backend instal·lat:

```powershell
python -X utf8 tools/validate_terrain_step7_11.py --output .runtime-terreny-local --part topology
python -X utf8 tools/validate_terrain_step7_11.py --output .runtime-terreny-local --part transport
python -X utf8 tools/validate_terrain_step7_11.py --output .runtime-terreny-local --part area
python -X utf8 tools/validate_terrain_step7_11.py --output .runtime-terreny-local --part dem
```

`dem` necessita la biblioteca DEM configurada; la instantània de nou nusos es conserva a l'evidència. La campanya de cost necessita copiar `protocol-visibilitat-v1.json` al directori de sortida abans d'executar `benchmark_terrain_step7_11.py --output <directori>`. Els casos sintètics i C arxivats no necessiten xarxa. [Hashes finals de codi i assets](codi-i-assets-finals.json).

[GDAL: geotransformació](https://gdal.org/en/stable/tutorials/geotransforms_tut.html) i [CRS vertical/reprojecció](https://gdal.org/en/stable/programs/gdal_raster_reproject.html), consultats. [Möller–Trumbore 1997](https://doi.org/10.1080/10867651.1997.10487468), referència bibliogràfica; PDF accessible amb extracció textual incompleta i captura web no disponible, sense copiar-ne codi. Les fórmules de productes vectorials/sistemes lineals s'han derivat i contrastat amb fixtures analítiques.

La skill `plan` s'ha aplicat. `terralab-manel-style`, exigida per la norma heretada, continua absent de les dues ubicacions locals comprovades; s'han aplicat les normes accessibles i no s'ha inventat cap skill. No s'ha fet commit automàtic ni s'ha començat 7.12.
