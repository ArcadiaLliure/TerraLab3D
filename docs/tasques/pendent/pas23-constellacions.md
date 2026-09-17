# Pas 23 — Constel·lacions IAU, traçat de referència i documents d'usuari

> **Estat:** en curs. **Estat funcional:** vertical implementada i automatitzada; homologació visual pendent. **Origen:** planificat. **Abast vigent:** catàleg immutable de 88 identitats IAU amb un traçat visual adoptat, observació mitjançant el Pas 22 i edició persistent de constel·lacions d'usuari.

## Descripció funcional

L'usuari pot cercar una de les 88 constel·lacions IAU, centrar-la, seguir-ne el centre i veure'n la trajectòria i visibilitat sobre l'horitzó. Pot mostrar o ocultar el traçat visual de referència i crear grups propis connectant estrelles visibles, amb traços continus o discontinus, selecció, reanomenament, eliminació i undo/redo durant la sessió. El document propi es recupera després de reiniciar; l'historial d'edició no.

El domini, els esquemes i el renderer mantindran separades tres capes: identitat de constel·lació IAU, traçat visual adoptat i document editable de l'usuari. Les línies adoptades no es descriuran com a «línies oficials IAU».

## Fonts a consultar

- [IAU — Constellations](https://www.iau.org/public/themes/constellations/): identitats, noms i abreviatures de les 88 constel·lacions; localitzada i contrastada el 2026-09-17. La IAU defineix constel·lacions per regions, no per un únic dibuix de línies.

- [d3-celestial `constellations.lines.json`, commit `7e720a3`](https://github.com/ofrohn/d3-celestial/blob/7e720a3de062059d4c5400a379146a601d9010e0/data/constellations.lines.json): GeoJSON J2000 del traçat visual i `rank`; consultat el 2026-09-17.

- [d3-celestial `constellations.json`, commit `7e720a3`](https://github.com/ofrohn/d3-celestial/blob/7e720a3de062059d4c5400a379146a601d9010e0/data/constellations.json): noms i identificadors de suport; consultat el 2026-09-17.

- [Llicència BSD-3-Clause de d3-celestial](https://github.com/ofrohn/d3-celestial/blob/7e720a3de062059d4c5400a379146a601d9010e0/LICENSE): obligacions de redistribució; consultada el 2026-09-17.

- [TerraLab `constellation_drawing.py`, commit auditat](https://github.com/ArcadiaLliure/TerraLab/blob/1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d/TerraLab/widgets/constellation_drawing.py): oracle autoritzat del flux d'edició, no arquitectura ni dependència de runtime; consultat el 2026-09-17.

- [Pas 22 — Trajectòries i visibilitat](../completat/pas22-trajectories-visibilitat.md): contracte observable que s'ha d'ampliar; consultat el 2026-09-17.

## Objectiu

Lliurar una vertical completa backend → bridge → Three.js que publiqui una vegada per connexió un catàleg empaquetat i immutable, renderitzi el traçat de referència sota l'arrel celeste, integri el centre de cada constel·lació amb el Pas 22 i permeti editar i persistir un document d'usuari amb snapping autoritatiu i reconstrucció incremental.

El resultat tindrà exactament 88 entitats. `Serpens Caput` i `Serpens Cauda` formaran una única entitat `Ser`, però conservaran components geomètrics discontinus sense cap segment artificial entre ells.

A més, el Pas 23 incorporarà l'homologació visual dels traçats i la base comuna per als overlays lineals de TerraLab3D. La referència visual és un **traç lluminós amb nucli definit i halo difús**, amb més contrast i presència que les línies actuals però sense convertir-se en un neó agressiu ni perjudicar la lectura del cel. Aquesta base serà reutilitzable per les constel·lacions, les eines de mesura angular i els contorns angulars d'objectes NGC, mantenint separats l'estil compartit i els comportaments específics de cada funcionalitat.

## Dependències

**Depèn de:**
- [Pas 6 — Picking estel·lar precís](../completat/pas6.md)
- [Pas 13 — Picking real, hover, selecció i inspecció](../completat/pas13.md)
- [Pas 22 — Trajectòries i visibilitat sobre l'horitzó real](../completat/pas22-trajectories-visibilitat.md)
- [Pas 22.5 — Normalització de la documentació viva](../completat/pas22.5-normalitzacio-documental.md)

**En depenen:**
- [Pas 31 — “El millor d'aquesta nit” i planificador](pas31-millor-nit-planificador.md)
- [Pas 38 — Homologació final, recuperació i rendiment](pas38-homologacio-final.md)


## Codi existent a reutilitzar

- **Repositori actual:** `backend/src/terralab3d/domain/constellations/`, `ObservablePositionService`, ports de persistència, resolució autoritativa de `StarPickRef`, `ConstellationBatchComponent`, `ConstellationLayerRenderer.ts`, `StarPickProvider`, `PointerGestureRouter`, `CelestialSelectionController`, `TrackingTargetResolver`, el bridge versionat i el patró complet del Pas 21.

- **Projectes de referència autoritzats:** d3-celestial al commit i sota la llicència indicats a «Fonts a consultar» per a les dades; TerraLab al commit auditat només com a oracle de comportament. No copiar arquitectura Qt ni introduir dependències de runtime sobre aquests projectes.

## Flux tècnic

### Catàleg immutable i procedència

Un regenerador explícit llegeix les fonts fixades, verifica hashes, interpreta l'origen com a `FK5/J2000`, el transforma amb Astropy a la representació canònica `ICRS` de TerraLab3D i genera un recurs empaquetat determinista. Els contractes conservaran `sourceFrame: "FK5_J2000"` i `frame: "ICRS"`; no s'emprarà l'etiqueta ambigua `ICRS/J2000`.

Cada `ConstellationCatalogEntry` tindrà abreviatura IAU, nom llatí canònic, centre, `angularRadiusDeg` i `visualComponents`. Cada component conservarà el `rank` original i una llista de traços. En `Ser`, els components `caput` i `cauda` romandran separats. El `rank` queda disponible per a un futur LOD, però el Pas 23 no l'aplicarà.

Els arcs es mostrejaran sobre esfera amb un pas màxim d'1°. El centre serà la mitjana vectorial normalitzada de les mostres del traçat i el radi, la màxima separació angular respecte del centre. Ambdues magnituds descriuen la figura visual adoptada, no la regió oficial IAU.

El catàleg s'enviarà una vegada per connexió o resincronització completa. Geometria, labels i picking romandran retinguts sota l'arrel celeste. Els ticks temporals transformaran aquesta arrel; només el centre ICRS entrarà al Pas 22 per calcular trajectòria, azimut, elevació, visibilitat i oclusió.

### Document editable i comandes

`ConstellationDocumentSnapshot` tindrà `documentType: "terralab3d.constellations"`, `schemaVersion: 1`, `revision`, grups, nodes, traços i `entityVersion`. `ConstellationEditorSnapshot` contindrà selecció, mode d'edició, advertiments i `canUndo/canRedo`; serà transitori i no formarà part del JSON persistent.

Les comandes versionades seran `create_group`, `append_node`, `finish_group`, `resume_from_node`, `select`, `rename_group`, `delete_selection`, `undo`, `redo` i `clear`, amb `requestId` i `expectedRevision`. `append_node` només transportarà `StarPickRef { resourceId, resourceVersion, catalogIndex }`; mai RA/Dec del frontend.

El frontend cercarà la candidata més propera dins de 16 píxels CSS entre estrelles que compleixin els mateixos predicats del renderer/picking en aquell moment: capa visible, recurs resident i vigent, magnitud dins del límit actiu, `StarVisibilityEvaluator.visible`, no oclosa per l'horitzó i projectada davant la càmera dins del viewport. La mida gràfica o el hit radius ordinari no ampliaran aquests 16 píxels.

El backend resoldrà la referència contra el recurs autoritatiu, comprovarà versió, índex, identitat i valors finits, i fixarà RA/Dec i `sourceId`. Una referència obsoleta, inexistent o no finita produirà `ConstellationErrorMessage` amb la revisió autoritativa i no canviarà document, revisió, historial ni fitxer.

L'historial tindrà un màxim de 256 mutacions per document actiu i per sessió. Canviar de document no barrejarà piles; reobrir o reiniciar un document crearà una pila buida. Selecció i canvis purament visuals no hi entraran.

El document es desarà atòmicament a `resolve_data_root()/constellations.v1.json`. La migració de `resolve_data_root()/terralab_constellations.json` serà idempotent i no modificarà l'original. Un document invàlid es copiarà amb nom datat abans d'inicialitzar un document buit vàlid.

### Presentació i integració

El renderer mantindrà separats catàleg, document i estat visual. El catàleg es construirà una vegada; cada grup d'usuari es reconciliarà per `entityVersion`, de manera que una mutació només disposi i reconstrueixi aquell grup. Labels, geometries, índexs i listeners tindran propietari i `dispose` verificable.

«Mostrar totes» modificarà exclusivament `.visible`. Entrar o sortir del mode d'edició no amagarà, recrearà ni retransmetrà constel·lacions. Les interaccions de punter seran consumibles i prioritzades; l'edició exclourà eines de mesura i preservarà la navegació i òrbita de càmera en tot moment, resolent l'afegit de nodes mitjançant tap sense bloquejar la càmera.

La cerca actual acceptarà `kind: "constellation"` per nom llatí i abreviatura. `ConstellationTargetRef` exposarà `constellationId`, `displayName`, `raDeg`, `decDeg`, `angularRadiusDeg` i `frame: "ICRS"`. El Pas 22 tractarà el centre com un objectiu equatorial fix; el radi servirà per a l'enquadrament, no com a frontera oficial.

La distribució incorporarà a `THIRD-PARTY.md` el copyright, el text BSD-3-Clause, el projecte, el commit i els fitxers de d3-celestial reutilitzats. L'empaquetat inclourà aquest fitxer als artefactes finals. La secció de constel·lacions de `docs/MANUAL.md` identificarà el traçat com a referència visual adoptada i enllaçarà `THIRD-PARTY.md`.

### Estil visual compartit dels overlays lineals

Abans de modificar materials o shaders, cal inventariar tots els punts del frontend que dibuixen línies, polilínies, contorns o formes equivalents a l'escena. Com a mínim s'han de revisar el traçat adoptat de constel·lacions IAU, els grups de constel·lacions d'usuari, les formes de mesura angular i els contorns o formes angulars dels objectes NGC. La cerca no es limitarà a aquesta llista: qualsevol altre renderer lineal existent s'haurà de classificar i documentar breument amb el component propietari, la tecnologia/material emprat i el lloc on es defineixen color, opacitat, gruix i efectes.

Es crearà o extraurà una abstracció visual comuna coherent amb l'arquitectura existent —per exemple un estil, perfil o fàbrica d'overlays lineals— que concentri el llenguatge gràfic compartit sense convertir-se en propietària de la semàntica funcional. Conceptualment haurà de poder expressar color base, opacitat, gruix del nucli, intensitat, halo/resplendor, amplada i opacitat del halo i variants d'intensitat. Els noms i l'API concrets s'adaptaran al codi existent; no s'imposarà una interfície artificial si el renderer actual ofereix una abstracció millor.

La identitat visual comuna serà **nucli definit + lluminositat + halo subtil + contrast sobre el cel**. L'objectiu no és simplement augmentar l'opacitat ni difuminar una línia gruixuda. El nucli ha de continuar sent llegible i el halo ha de reforçar-lo sense tapar estrelles, nebuloses, galàxies, etiquetes ni altres elements astronòmics.

La implementació haurà d'avaluar la tècnica més adequada segons el renderer real: doble traç o traç multicapa, materials compartits, blending, shader específic, bloom selectiu o una altra solució equivalent. No s'aplicarà bloom global si altera el cel, crema estrelles o afecta elements aliens als overlays. Si cal postprocessament, serà selectiu o quedarà encapsulat de manera que només afecti els elements previstos.

L'estil es centralitzarà; **els efectes i els estats continuaran pertanyent a cada funcionalitat**. La capa comuna podrà saber com representar una línia lluminosa, però no decidirà quan una mesura està seleccionada, quan ha de pulsar, quin tipus NGC determina un color o quin document de constel·lació és editable. No es crearà un gestor monolític de selecció, animació i semàntica.

El sistema compartit permetrà intensitats o variants reutilitzables —conceptualment equivalents a `subtle`, `normal`, `highlight` i `selected`, sense imposar aquests noms— per evitar que cada consumidor torni a definir manualment tot l'estil.

El comportament visual requerit serà:

- **Mesura angular, estat normal:** blanca, clarament visible i amb l'estil lluminós comú, sense dominar l'escena.

- **Mesura angular, estat seleccionat:** groga, més prominent i amb pulsació suau i contínua. La pulsació modificarà preferentment intensitat o resplendor i no farà desaparèixer gairebé completament el traç. La lògica temporal continuarà dins de l'eina de mesura.

- **Objectes NGC:** conservaran la diferenciació cromàtica actual segons el tipus d'objecte. Aplicaran el mateix llenguatge visual amb una intensitat més moderada, colors identificables i un halo perceptible però no dominant. No se substituirà la paleta actual sense una justificació funcional.

- **Traçat adoptat de constel·lacions IAU:** blanc, sensiblement més viu que l'actual i amb halo subtil. S'ha de preservar la lectura de les estrelles que connecta i continuar descrivint-se com a traçat visual adoptat, no com a «línies oficials IAU».

- **Constel·lacions creades per l'usuari:** verdes, amb el mateix llenguatge visual base que el traçat adoptat i diferenciació immediata respecte de les constel·lacions IAU. Els efectes d'edició o selecció existents no es canviaran llevat que sigui necessari per integrar l'estil compartit.

La jerarquia visual continuarà sent **cel i objectes astronòmics → informació seleccionada o interactiva → overlays permanents**. Una mesura seleccionada podrà destacar clarament més que una constel·lació persistent, i els contorns NGC tindran una intensitat més continguda.

La solució evitarà una degradació perceptible del rendiment. S'haurà de vigilar especialment el cost de shaders addicionals, dobles geometries, materials duplicats, postprocessament i animacions per element. Es compartiran materials, configuracions o recursos quan sigui possible sense impedir els estats dinàmics necessaris.

## Errors, cancel·lació i recursos

- Un catàleg absent, incompatible o amb hash incorrecte és un error d'instal·lació visible; no activa descàrregues implícites ni dades inventades.

- Una ordre amb revisió conflictiva es rebutja sencera i força resincronització; no hi ha mutacions parcials.

- Sortir de l'edició cancel·la el gest obert sense esborrar geometria ni alterar visibilitat.

- Una desconnexió conserva recursos residents vàlids; la reconnexió publica un snapshot complet una vegada i reprèn deltes.

- La migració i el desament usen fitxer temporal, sincronització i reemplaçament atòmic. L'original i les còpies de recuperació no s'esborren.

- En esborrar o substituir grups, el renderer allibera geometries, materials, labels, índexs i listeners exactament una vegada.

- No iniciar operacions llargues quan ja calgui reservar marge per validar, persistir i tancar la sessió.

## Tasques

- [ ] Caracteritzar models, coordinadors, bridge, picking, persistència i renderers existents, i publicar el mapa `REUSE/EXTRACT/ADAPT/REWRITE/DISCARD/NEW`.

- [x] Implementar el regenerador, el manifest de procedència i el recurs empaquetat amb 88 entitats, frames separats, `rank`, centre, radi, components i traços.

- [x] Afegir `THIRD-PARTY.md` amb l'avís BSD-3-Clause complet i assegurar que l'empaquetat final el distribueix.

- [x] Implementar models i càlculs purs mantenint separades les tres capes semàntiques.

- [ ] Unificar els ports de persistència duplicats i implementar càrrega, desament atòmic, recuperació i migració idempotent.

- [x] Implementar el servei de comandes amb revisió optimista, errors transaccionals i historial de 256 mutacions per document i sessió.

- [x] Ampliar el resolver autoritatiu perquè `append_node` només accepti una `StarPickRef` vàlida i fixi coordenades i `sourceId` al backend.

- [x] Afegir snapshots i missatges tipats de catàleg, document, editor, comandes, errors i objectiu observable al bridge Python/TypeScript.

- [x] Implementar el renderer retingut del catàleg, labels, picking i grups d'usuari per `entityVersion`, amb mètriques de builds i `dispose`.

- [x] Integrar edició, snapping, discontinuïtats, selecció, reanomenament, eliminació, undo/redo i feedback d'error a la UI.

- [x] Separar visibilitat i edició, incloent «Mostrar totes» sense reconstruccions ni mutacions de domini.

- [x] Integrar cerca, selecció, centrat, seguiment i trajectòria del centre amb el Pas 22 sense geometria als ticks.

- [ ] Inventariar tots els renderers lineals o de contorn de l'escena —constel·lacions IAU i d'usuari, mesura angular, NGC i qualsevol altre cas existent— i documentar tecnologia/material, propietari i paràmetres visuals actuals.

- [ ] Dissenyar i implementar l'abstracció compartida d'estil per a overlays lineals, separada de la lògica de selecció, animació i semàntica de cada funcionalitat.

- [ ] Aplicar el llenguatge visual de nucli definit i halo subtil: constel·lacions adoptades blanques, constel·lacions d'usuari verdes, mesura angular normal blanca, mesura seleccionada groga i pulsant, i NGC amb els colors actuals per tipus però intensitat moderada.

- [ ] Verificar que l'efecte no depèn d'un bloom global que alteri el cel i que la implementació comparteix recursos sempre que sigui possible sense trencar els estats dinàmics.

- [ ] Afegir la secció verificada al manual i actualitzar inventari, README, caselles i evidències.

- [ ] Executar totes les proves, mètriques i escenaris manuals; corregir regressions abans de completar el pas.

- [x] Aplicar el protocol final de persistència, comprovació de processos i tancament de l'equip indicat a «Instrucció per a Codex».

## Criteri de sortida

L'usuari pot cercar i observar qualsevol de les 88 constel·lacions, mostrar el traçat adoptat, seguir-ne el centre amb el Pas 22 i crear, editar, desfer, persistir i restaurar un document propi. Serpens apareix una sola vegada amb Caput i Cauda desconnectades. Els ticks no transporten geometria, els canvis visuals no reconstrueixen recursos i modificar un grup només reconstrueix aquell grup. La procedència BSD-3-Clause es distribueix i és consultable des del manual.

Visualment, els overlays lineals comparteixen una identitat coherent de nucli definit i halo subtil sense compartir necessàriament els seus efectes funcionals: el traçat adoptat de constel·lacions IAU és blanc, els grups d'usuari són verds, les mesures angulars normals són blanques i les seleccionades són grogues i pulsen, i els contorns NGC conserven la codificació cromàtica per tipus amb una intensitat més moderada. La nova capa comuna és extensible i no degrada perceptiblement ni la lectura del cel ni el rendiment.

## Proves i evidències obligatòries

- [x] Executar dues regeneracions; resultat esperat: bytes i hashes idèntics, 88 entitats, valors finits, arcs de màxim 1° i `rank` preservat.

- [x] Verificar `Ser`: una entitat, almenys dos components i cap aresta sintètica. Desar el resum a `../../evidencies/pas23/validacio-cataleg.txt`.

- [ ] Verificar amb fixtures `FK5/J2000 → ICRS`, centre i radi prop de RA 0/360°, sempre sobre el traçat i no sobre fronteres IAU.

- [ ] Provar totes les comandes, conflictes i referències inexistents, obsoletes, fora de rang o no finites; resultat esperat: cap mutació parcial.

- [ ] Provar límit de 256 per document, invalidació de redo, aïllament entre documents i pila buida després de reiniciar.

- [ ] Provar round-trip, reemplaçament atòmic, migració repetida, original intacte i còpia datada d'un document invàlid.

- [ ] Provar snapping a DPR i FOV diferents; només són candidates les estrelles renderitzables i dins de 16 píxels CSS.

- [ ] Instrumentar bridge i escena: una publicació de catàleg per connexió, zero geometria als ticks i resincronització completa única.

- [x] Provar el renderer: visibilitat o edició fan zero builds/dispose; modificar un grup fa un dispose i un build només d'aquell grup.

- [x] Executar `python -m pytest backend/tests -q`, `npm --prefix frontend test`, `npm run typecheck` i validadors documentals; resultat esperat: tot correcte.

- [ ] Capturar comparatives visuals del nou estil: traçat adoptat IAU blanc, constel·lació d'usuari verda, mesura angular normal blanca, mesura seleccionada groga durant la pulsació i una mostra representativa de contorns NGC amb colors per tipus.

- [ ] Verificar visualment sobre camps estel·lars densos i objectes de cel profund que el halo no tapa estrelles ni degrada la lectura del cel, i registrar la configuració final d'intensitat.

- [ ] Mesurar l'impacte de l'estil compartit sobre FPS, nombre de materials, geometries i passes de render/postprocessament en un escenari representatiu; resultat esperat: cap degradació perceptible i cap creixement innecessari de recursos per element.

- [ ] Capturar una constel·lació seleccionada amb trajectòria a `../../evidencies/pas23/constellacio-amb-trajectoria.png`.

- [ ] Enregistrar creació, discontinuïtat, undo/redo i «Mostrar totes» a `../../evidencies/pas23/edicio-i-visibilitat.webm`.

- [x] Desar mètriques de bridge, builds, dispose, reinici i migració a `../../evidencies/pas23/runtime-i-persistencia.txt`.

- [x] Verificar que `THIRD-PARTY.md` conté l'avís complet, apareix a l'artefacte distribuït i és enllaçat pel manual.

**\*\*Resultats verificats:\*\*** dues regeneracions deterministes amb SHA-256 `BDEBC06F58F1ADBDC23960D533AA9F6367E82BDDFBB3BE31ABCC1A78E5B967A1`; 177 proves backend correctes; suite frontend completa, prova específica del Pas 23, typecheck i validador documental correctes; wheel verificat amb catàleg i avís BSD-3-Clause. Resten les evidències manuals i els casos avançats no marcats.

## Fora d'abast

- Fronteres o regions oficials IAU i centres o radis calculats a partir d'aquestes fronteres.

- Traduccions dels noms i variants culturals del traçat.

- Aplicar LOD segons `rank`; el Pas 23 només en conserva la dada.

- Cercador multipestanya, recomanacions i planificació temporal dels passos 31 i 33.

- Descàrrega o actualització del catàleg en runtime.

- Persistència de selecció, mode d'edició o historial undo/redo.

- Figures visuals diferents de la font adoptada i asterismes.

## Instrucció per a Codex

No comencis fins que el Pas 22.5 estigui complet. Implementa les tasques en ordre vertical, mantén separades identitat IAU, figura visual i document d'usuari, i actualitza caselles només amb proves o evidències reals. No facis canvis editorials aliens ni anticipis els passos 31 o 33.

Abans que s'esgoti el marge operatiu, deixa d'iniciar treball llarg, espera o cancel·la ordenadament només els processos iniciats per aquesta tasca, completa escriptures, persisteix codi i documentació, registra el punt de represa i executa comprovacions ràpides. Verifica `git status --short`, `git diff --check` i que no quedi cap servidor, prova, navegador automatitzat o escriptura propis pendents; no tanquis processos de l'usuari ni facis commit o push sense ordre. Prepara el traspàs abans del tancament i executa `shutdown.exe /s /t 0` com a darrera operació sobre l'ordinador, sense cap altra crida d'eina posterior.

## Treball pendent

- [ ] Capturar les evidències visuals manuals i completar els casos avançats encara no marcats abans de moure el pas a `completat/`.