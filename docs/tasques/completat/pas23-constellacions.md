# Pas 23 — Constel·lacions IAU, traçat de referència i documents d'usuari

> **Estat:** completat. **Estat funcional:** observable. **Origen:** planificat. **Abast vigent:** catàleg immutable de 88 identitats IAU amb un traçat visual adoptat, observació mitjançant el Pas 22, edició persistent de constel·lacions d'usuari i estil compartit d'overlays lineals amb nucli definit i halo subtil.

## Descripció funcional

L'usuari pot cercar una de les 88 constel·lacions IAU per nom llatí o abreviatura, centrar-la, seguir-ne el centre geomètric i visualitzar-ne la trajectòria de 24 hores i la visibilitat sobre l'horitzó real DEM (mitjançant la integració directa amb el Pas 22). Pot commutar la visibilitat del traçat adoptat («Mostrar totes» o selecció individual) i crear grups propis connectant estrelles visibles mitjançant un snapping autoritatiu de 16 px CSS al backend, amb traços continus o discontinus, selecció, reanomenament, eliminació i historial undo/redo (256 mutacions) durant la sessió. El document d'usuari es desa atòmicament a `constellations.v1.json` i es restaura automàticament en reiniciar la sessió.

El domini, els esquemes i el renderer mantenen estrictament separades tres capes: identitat de constel·lació IAU, traçat visual adoptat i document editable de l'usuari. Les línies adoptades es descriuen com a «traçat visual de referència adoptat» i no com a «línies oficials IAU».

## Fonts a consultar

- [IAU — Constellations](https://www.iau.org/public/themes/constellations/): identitats, noms i abreviatures de les 88 constel·lacions. La IAU defineix constel·lacions per regions/fronteres, no per un únic dibuix de línies.
- [d3-celestial `constellations.lines.json`, commit `7e720a3`](https://github.com/ofrohn/d3-celestial/blob/7e720a3de062059d4c5400a379146a601d9010e0/data/constellations.lines.json): GeoJSON J2000 del traçat visual i `rank`.
- [d3-celestial `constellations.json`, commit `7e720a3`](https://github.com/ofrohn/d3-celestial/blob/7e720a3de062059d4c5400a379146a601d9010e0/data/constellations.json): noms i identificadors de suport.
- [Llicència BSD-3-Clause de d3-celestial](https://github.com/ofrohn/d3-celestial/blob/7e720a3de062059d4c5400a379146a601d9010e0/LICENSE): obligacions de redistribució recollides a [THIRD-PARTY.md](../../../THIRD-PARTY.md).
- [TerraLab `constellation_drawing.py`, commit auditat](https://github.com/ArcadiaLliure/TerraLab/blob/1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d/TerraLab/widgets/constellation_drawing.py): oracle autoritzat del flux d'edició (no arquitectura ni dependència de runtime).
- [Pas 22 — Trajectòries i visibilitat](pas22-trajectories-visibilitat.md): contracte d'objectes observables i trajectòria 24h.

## Objectiu

Lliurar una vertical completa backend → bridge → Three.js que publiqui una vegada per connexió un catàleg empaquetat i immutable, renderitzi el traçat de referència sota l'arrel celeste, integri el centre de cada constel·lació amb el Pas 22 i permeti editar i persistir un document d'usuari amb snapping autoritatiu i reconstrucció incremental.

El resultat té exactament 88 entitats. `Serpens Caput` i `Serpens Cauda` formen una única entitat `Ser`, conservant components geomètrics discontinus sense cap segment artificial entre ells.

A més, el Pas 23 incorpora l'homologació visual dels traçats i la base comuna per als overlays lineals de TerraLab3D (`OverlayLineStyle`). La referència visual és un **traç lluminós amb nucli definit i halo difús**, amb més contrast i presència sobre el cel nocturn sense convertir-se en un neó agressiu ni alterar el fons celeste. Aquesta base és compartida per les constel·lacions, les eines de mesura angular, els contorns angulars d'objectes NGC i les trajectòries aparents dels objectes.

## Dependències

**Depèn de:**
- [Pas 6 — Picking estel·lar precís](pas6.md)
- [Pas 13 — Picking real, hover, selecció i inspecció](pas13.md)
- [Pas 22 — Trajectòries i visibilitat sobre l'horitzó real](pas22-trajectories-visibilitat.md)
- [Pas 22.5 — Normalització de la documentació viva](pas22.5-normalitzacio-documental.md)

**En depenen:**
- [Pas 31 — “El millor d'aquesta nit” i planificador](../pendent/pas31-millor-nit-planificador.md)
- [Pas 38 — Homologació final, recuperació i rendiment](../pendent/pas38-homologacio-final.md)

## Codi existent a reutilitzar

| Element | Classificació | Destinació / Rol a TerraLab3D |
|---|---|---|
| Catàleg de línies d3-celestial (7e720a3) | `ADAPT` | [`generate_constellation_catalog.py`](../../../tools/generate_constellation_catalog.py) converteix FK5/J2000 a ICRS canònic i genera recurs empaquetat determinista. |
| Avís de copyright i llicència BSD-3 | `REUSE` | [`THIRD-PARTY.md`](../../../THIRD-PARTY.md) distribuït amb el paquet Python i enllaçat des del manual. |
| `ObservablePositionService` | `REUSE` | Resolució de posició azimutal/elevació instantània del centre de la constel·lació com a objecte equatorial fix. |
| `ApparentTrajectoryCoordinator` (Pas 22) | `REUSE` | Trajectòria 24h del centre de la constel·lació amb avaluació d'horitzó real DEM. |
| `StarPickResolver` / `gaia_stars` | `ADAPT` | Resolució autoritativa al backend de `StarPickRef` per assignar coordenades ICRS exactes i `sourceId`. |
| `PointerGestureRouter` | `REUSE` | Encaminament de clics i gestos amb prioritat d'edició i alliberament de càmera. |
| `AtomicTextPreferencesAdapter` | `REUSE` | Persistència atòmica de `constellations.v1.json` i backup de fitxers invàlids. |
| `ConstellationLayerRendererImpl` | `NEW` | Renderer retingut sota l'arrel celeste amb batches per `entityVersion` i suport d'OverlayLineStyle. |
| `OverlayLineStyle` | `NEW` | Fàbrica compartida de materials lineals de doble capa (nucli definit + halo lluminós). |

## Flux tècnic

### Catàleg immutable i procedència

Un regenerador determinista ([`generate_constellation_catalog.py`](../../../tools/generate_constellation_catalog.py)) llegeix les fonts fixades de d3-celestial, verifica hashes SHA-256, transforma les coordenades FK5/J2000 a ICRS canònic mitjançant Astropy i produeix [`constellations.v1.json`](../../../backend/src/terralab3d/infrastructure/catalogs/constellations.v1.json).

Cada entrada conté identificador IAU de 3 lletres, nom llatí, centre ICRS (mitjana vectorial normalitzada de les mostres del traçat), radi angular (màxima separació al centre) i components visuals amb `rank` (1, 2 o 3) i llista de traços mostrejats sobre l'esfera amb pas $\le 1.0^\circ$. En `Ser`, `caput` i `cauda` es mantenen com a components desconnectats.

### Document editable i comandes

`ConstellationCoordinator` gestiona el document persistent (`ConstellationDocument`) amb historial en memòria de fins a 256 mutacions. Les accions admeses (`create_group`, `append_node`, `finish_group`, `resume_from_node`, `select`, `rename_group`, `delete_selection`, `undo`, `redo`, `clear`) requereixen revisió optimista (`documentRevision`). L'acció `append_node` rep una `StarPickRef` que el backend valida contra el catàleg estel·lar autoritatiu abans de mutar el document.

El desament és atòmic a `constellations.v1.json`. Si existeix un document antic (`terralab_constellations`), es migra de forma idempotent conservant l'original; si el fitxer és corrupte, es preserva en una còpia datada (`constellations.v1.invalid-*.json`) abans d'iniciar un document buit vàlid.

### Estil visual compartit dels overlays lineals (`OverlayLineStyle`)

S'ha creat l'abstracció [`OverlayLineStyle.ts`](../../../frontend/src/view/three/materials/OverlayLineStyle.ts) que implementa una tècnica multicapa (nucli d'alta opacitat + halo difús amb blending additiu) compartida per tots els renderers lineals:
- **Constel·lacions IAU adoptades:** Traç blanc (`#ffffff`) amb halo subtil translúcid, mantenint la llegibilitat de les estrelles connectades.
- **Constel·lacions d'usuari:** Traç verd maragda (`#6ee7a8`) amb halo verd lluminós, clarament distingible de les oficials.
- **Mesura angular:** Traç blanc pur en estat normal; groc daurat (`#fbbf24`) amb pulsació suau d'intensitat en estat seleccionat.
- **Objectes NGC:** Contorns amb codificació cromàtica per tipus d'objecte i intensitat continguda.
- **Trajectòries aparents:** Traç cian brillant (`#38bdf8`) per a `visible`, discontinu violeta (`#c084fc`) per a `terrain_occluded` i sota l'horitzó, i ambre per a `insufficient_data`.

## Errors, cancel·lació i recursos

- Un catàleg absent o corrupte és un error visible a l'arrencada; no activa dades inventades.
- Les ordres de constel·lació amb revisió obsoleta o conflictes de referència es rebutgen íntegrament sense mutacions parcials.
- Sortir del mode d'edició cancel·la el gest obert sense esborrar geometria ni alterar la visibilitat.
- Els canvis de grup alliberen geometries, materials i recursos Three.js associats (`dispose()`).
- Totes les operacions asíncrones tenen descart de revisions obsoletes.

## Tasques

- [x] Caracteritzar models, coordinadors, bridge, picking, persistència i renderers existents, i publicar el mapa `REUSE/EXTRACT/ADAPT/REWRITE/DISCARD/NEW`.
- [x] Implementar el regenerador, el manifest de procedència i el recurs empaquetat amb 88 entitats, frames separats, `rank`, centre, radi, components i traços.
- [x] Afegir `THIRD-PARTY.md` amb l'avís BSD-3-Clause complet i assegurar que l'empaquetat final el distribueix.
- [x] Implementar models i càlculs purs mantenint separades les tres capes semàntiques.
- [x] Unificar els ports de persistència duplicats i implementar càrrega, desament atòmic, recuperació i migració idempotent.
- [x] Implementar el servei de comandes amb revisió optimista, errors transaccionals i historial de 256 mutacions per document i sessió.
- [x] Ampliar el resolver autoritatiu perquè `append_node` només accepti una `StarPickRef` vàlida i fixi coordenades i `sourceId` al backend.
- [x] Afegir snapshots i missatges tipats de catàleg, document, editor, comandes, errors i objectiu observable al bridge Python/TypeScript.
- [x] Implementar el renderer retingut del catàleg, labels, picking i grups d'usuari per `entityVersion`, amb mètriques de builds i `dispose`.
- [x] Integrar edició, snapping, discontinuïtats, selecció, reanomenament, eliminació, undo/redo i feedback d'error a la UI.
- [x] Separar visibilitat i edició, incloent «Mostrar totes» sense reconstruccions ni mutacions de domini.
- [x] Integrar cerca, selecció, centrat, seguiment i trajectòria del centre amb el Pas 22 sense geometria als ticks.
- [x] Inventariar tots els renderers lineals o de contorn de l'escena i documentar tecnologia, propietari i paràmetres visuals.
- [x] Dissenyar i implementar l'abstracció compartida `OverlayLineStyle` per a overlays lineals amb nucli definit i halo subtil.
- [x] Integrar `ApparentTrajectoryRenderer` amb l'estil compartit preservant la semàntica per segments (`visible`, `terrain_occluded`, `below_astronomical_horizon`, `insufficient_data`).
- [x] Aplicar el llenguatge visual a constel·lacions adoptades (blanques), d'usuari (verdes), mesura normal (blanca), seleccionada (groga pulsant) i NGC (per tipus).
- [x] Aplicar el llenguatge visual a les trajectòries aparents amb nucli definit i glow respectant la codificació existent.
- [x] Verificar l'absència de bloom global destructiu i la reutilització eficient de materials i geometries.
- [x] Afegir la secció verificada al manual ([Secció 13](../../MANUAL.md#13--constellacions-de-referència-i-figures-pròpies)) i actualitzar inventari, README, caselles i evidències.
- [x] Executar totes les proves, mètriques i escenaris manuals; corregir regressions abans de completar el pas.
- [x] Aplicar el protocol final de persistència, comprovació de processos i tancament de l'equip.

## Criteri de sortida

- [x] L'usuari pot cercar i observar qualsevol de les 88 constel·lacions, mostrar el traçat adoptat, seguir-ne el centre amb el Pas 22 i crear, editar, desfer, persistir i restaurar un document propi.
- [x] Serpens apareix una sola vegada amb Caput i Cauda desconnectades.
- [x] Els ticks no transporten geometria, els canvis visuals no reconstrueixen recursos i modificar un grup només reconstrueix aquell grup.
- [x] La procedència BSD-3-Clause es distribueix a `THIRD-PARTY.md` i és consultable des del manual.
- [x] Els overlays lineals comparteixen la identitat visual de nucli definit i halo subtil sense barrejar semàntiques pròpies ni degradar el rendiment.

## Proves i evidències obligatòries

- [x] Dues regeneracions consecutives amb bytes i SHA-256 idèntics (`BDEBC06F58F1ADBDC23960D533AA9F6367E82BDDFBB3BE31ABCC1A78E5B967A1`), 88 entitats, valors finits i arcs $\le 1.0^\circ$.
- [x] Verificació de Serpens: 1 entitat, 2 components (`caput`, `cauda`) i cap aresta sintètica ([`validacio-cataleg.txt`](../../evidencies/pas23/validacio-cataleg.txt)).
- [x] Verificació de transformació FK5/J2000 → ICRS, centre i radi angular sobre el traçat ([`test_constellations_step23.py`](../../../backend/tests/test_constellations_step23.py)).
- [x] Proves de comandes transaccionals, rebuig de revisions obsoletes i snapping amb comprovació al backend.
- [x] Prova de límit d'historial a 256 mutacions, invalidació de redo i aïllament de sessions.
- [x] Prova de persistència atòmica, còpia de seguretat datada de fitxer invàlid i migració idempotent legacy.
- [x] Prova de snapping a 16 px CSS en DPR i FOV variables.
- [x] Prova de bridge i escena: catàleg publicat una vegada per connexió, zero geometria als ticks.
- [x] Prova del renderer: `setShowAll` fa 0 builds/dispose; canviar un grup fa 1 build/dispose d'aquell grup ([`constellation_step23.test.ts`](../../../frontend/src/tests/constellation_step23.test.ts)).
- [x] Captura del catàleg complet de constel·lacions oficials en zoom-out màxim sense constel·lacions d'usuari ([`constellacio-amb-trajectoria.png`](../../evidencies/pas23/constellacio-amb-trajectoria.png)).
- [x] Captura de constel·lació personalitzada sencera («Triangle d'Estiu propi») aïllada sobre la Via Làctia sense la resta de constel·lacions ([`edicio-i-visibilitat.png`](../../evidencies/pas23/edicio-i-visibilitat.png)).
- [x] Resum de mètriques de runtime i persistència ([`runtime-i-persistencia.txt`](../../evidencies/pas23/runtime-i-persistencia.txt)).
- [x] `THIRD-PARTY.md` inclòs a l'arrel, al paquet Python i referenciat al manual.

## Fora d'abast

- Fronteres o regions oficials IAU i càlculs basats en aquestes fronteres.
- Traduccions dels noms i variants culturals del traçat.
- Aplicar LOD segons `rank` en runtime (es conserva l'atribut per a futures millores).
- Cercador multipestanya i planificador dels passos 31 i 33.
- Descàrrega dinàmica del catàleg en runtime.
- Persistència d'historial undo/redo o selecció transitòria.
- Asterismes o figures alternatives fora de la font d3-celestial adoptada.

## Instrucció per a Codex

No comencis fins que el Pas 22.5 estigui complet. Implementa les tasques en ordre vertical, mantén separades identitat IAU, figura visual i document d'usuari, i actualitza caselles només amb proves o evidències reals. No facis canvis editorials aliens ni anticipis els passos 31 o 33.

## Treball pendent

Cap. Totes les tasques, criteris de sortida, proves i evidències estan verificades.
