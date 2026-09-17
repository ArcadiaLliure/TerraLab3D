# Pas 22 — Trajectòries i visibilitat sobre l'horitzó real

> **Estat:** completat. **Estat funcional:** observable. **Origen:** planificat. **Abast vigent:** càlcul i representació de trajectòries temporals d'objectes observables (planetes, Sol, Lluna, satèl·lits, estrelles, cel profund i coordenades), classificació de visibilitat sobre el perfil d'horitzó real i astronòmic, refinament de creuaments, marcadors temporals i controls interactius.

## Descripció funcional

L'usuari selecciona qualsevol objecte observable —estrella, planeta, satèl·lit, Sol, Lluna o objecte de cel profund— i en visualitza directament la trajectòria de 24 hores cap endavant des de l'instant actiu mitjançant la casella interactiva «Trajectòria de l'objecte» (marcada per defecte) a la pestanya «Cel». El reticle de selecció acompanya l'astre amb una etiqueta d'identificació directa (ex: «Sol») a més de la informació del HUD d'observació. El sistema projecta el recorregut aparent a la volta celeste amb diferenciació clara de visibilitat:

- **Visible:** traç continu cian brillant (`━━━━`).
- **Ocult pel relleu:** traç discontinu violeta neó (`┄ ┄ ┄`) amb subdivisió geomètrica visible a través del terreny sense interrupcions.
- **Sota l'horitzó astronòmic:** traç puntejat lila clar (`┄ ┄ ┄`).
- **Dades insuficients:** traç ambre d'avís (`┈ ┈ ┈`) quan el perfil DEM presenta buits.

El mode d'horitzó utilitzat s'enllaça automàticament amb l'estat del relleu DEM: si l'*Horitzó real* està marcat a la pestanya de terreny (Topografia), s'avalua el relleu real; altrament, s'aplica l'horitzó astronòmic pla a 0°. La trajectòria es calcula per a un interval complet de 24 hores i es manté visible de manera contínua sense parpellejos ni recàlculs innecessaris mentre el temps de simulació es mou dins d'aquest rang de 24 hores (actualitzant fluidament el marcador lluminós de posició instantània al llarg del traç calculat). Només si es desplaça el temps fora de la finestra de 24 hores o es canvia d'objecte o observador, es demana una nova trajectòria. Les etiquetes d'esdeveniments d'alba i posta s'han fet més compactes (16 px en pantalla en lloc de 26 px, canvas de 310×50 px) amb la terminologia precisa `↑ Alba` i `↓ Posta`. En clicar qualsevol astre, s'activa per defecte el seguiment continu (amb indicació `SEGUINT` i botó daurat `Seguint ✓` al HUD), i la Via Làctia s'activa i renderitza per defecte des de l'arrencada.

## Fonts a consultar

- [TerraLab al commit auditat `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`](https://github.com/ArcadiaLliure/TerraLab/tree/1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d): `widget_controls_builder.py` i regles de visibilitat i oclusió.
- Efemèrides DE440 i SPICE kernels del projecte TerraLab3D.
- Model d'elevació DEM local i coordenades topocèntriques ENU.

## Objectiu

Connectar l'objecte observable seleccionat amb el mostreig d'altura/azimut, el perfil d'horitzó real del terreny 3D, la classificació de visibilitat, el contracte de bridge binari V2 i el renderer Three.js, homologant visualment i interactivament el comportament G1–G9 sense regressions.

## Dependències

**Depèn de:**
- [Pas 9 — Eclipsis, ocultacions, separacions i trajectòries](pas9.md)
- [Pas 15 — Elevació real, perfil d'horitzó i oclusió](pas15.md)

**En depenen:**
- [Pas 23 — Constel·lacions IAU, traçat de referència i documents d'usuari](../pendent/pas23-constellacions.md)
- [Pas 31 — “El millor d'aquesta nit” i planificador](../pendent/pas31-millor-nit-planificador.md)
- [Pas 32 — Motor general d'efemèrides](../pendent/pas32-motor-efemerides.md)
- [Pas 38 — Homologació final, recuperació i rendiment](../pendent/pas38-homologacio-final.md)


## Codi existent a reutilitzar

- **Repositori actual:**
  - Coordinadors: [`apparent_trajectory.py`](../../../backend/src/terralab3d/application/apparent_trajectory.py) i [`horizon_coordinator.py`](../../../backend/src/terralab3d/application/horizon_coordinator.py).
  - Posicions observables: [`observable_positions.py`](../../../backend/src/terralab3d/application/observable_positions.py) i el seu port [`ports/observable_positions.py`](../../../backend/src/terralab3d/application/ports/observable_positions.py).
  - Domini de visibilitat: [`terralab3d/domain/visibility/`](../../../backend/src/terralab3d/domain/visibility/).
  - Contractes i bridge: [`astronomical_event_contracts.ts`](../../../frontend/src/contracts/astronomical_event_contracts.ts), [`bridge_messages.ts`](../../../frontend/src/contracts/bridge_messages.ts).
  - Renderers: [`ApparentTrajectoryRenderer.ts`](../../../frontend/src/view/three/ApparentTrajectoryRenderer.ts), [`GalacticSkyRenderer.ts`](../../../frontend/src/view/three/GalacticSkyRenderer.ts) i [`SolarSystemRenderer.ts`](../../../frontend/src/view/three/SolarSystemRenderer.ts).
  - UI: [`TrajectoryVisibilityPanel.ts`](../../../frontend/src/view/ui/components/TrajectoryVisibilityPanel.ts), [`ResourceBackedLayerRow.ts`](../../../frontend/src/view/ui/components/ResourceBackedLayerRow.ts), [`LocationHUD.ts`](../../../frontend/src/view/ui/panels/LocationHUD.ts) i [`SkyPage.ts`](../../../frontend/src/view/ui/drawer_pages/SkyPage.ts).
- **Projectes de referència autoritzats:** TerraLab (commit `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`).

## Flux tècnic

1. **Selecció i seguiment actiu:** `selectedTrajectoryTarget()` a [`main.ts`](../../../frontend/src/main.ts) resol la identitat, coordenades o identificador SPICE de l'objecte seleccionat. S'inicia automàticament el seguiment de focus (`focusTrackingController.startTracking`) reflectit al HUD amb badge actiu `SEGUINT` i botó `Seguint ✓`.
2. **Petició:** Envia missatge `request_apparent_trajectory` pel pont WebSocket amb identificador monotònic (`latest-wins`), interval fix de 24 hores (d'ara endavant respecte al temps de simulació actiu), resolució detallada fixa (128 mostres) i mode d'horitzó sincronitzat amb la visibilitat del terreny DEM.
3. **Càlcul científic (Python):** `ApparentTrajectoryCoordinator` mostreja les posicions topocèntriques ENU de l'objecte amb mostreig adaptatiu i associació de perfil DEM per proximitat de coordenades de l'observador.
4. **Comparació d'horitzó:** Avalua $f(t) = \text{alt}_{\text{astre}}(t) - \text{alt}_{\text{horitzó}}(\text{az}(t))$. Refina per bisecció els creuaments temporals exactes.
5. **Classificació:** Divideix la trajectòria en segments contigus (`visible`, `terrain_occluded`, `below_astronomical_horizon`, `insufficient_data`).
6. **Bridge binari V2:** Empaqueta vèrtexs ENU, offsets temporals, validesa i màscara de visibilitat preservant compatibilitat amb el contracte V1 del pas 9.
7. **Renderitzat (Three.js):** `ApparentTrajectoryRenderer` manté `LineSegments` retinguts amb retroil·luminació fluorescent additiva, marcadors d'esdeveniments amb escalat adaptatiu invariant al zoom (16 px de pantalla, compacte) i el marcador temporal de l'instant actiu.
8. **UI:** `TrajectoryVisibilityPanel` presenta una única casella minimalista «Trajectòria de l'objecte» (marcada per defecte) i línia d'estat amb els esdeveniments, amb actualització automàtica en desplaçar el temps o commutar l'horitzó DEM a Topografia.

## Errors, cancel·lació i recursos

- **Cancel·lació i concurrència:** Les sol·licituds ràpides apliquen la política `latest-wins`. Una resposta arribada amb una revisió anterior a l'actual es descarta sense modificar la vista.
- **Dades insuficients i buits:** Els buits del DEM es classifiquen com a `insufficient_data` amb traç groc d'avís i no generen esdeveniments ficticis. Si no hi ha cap perfil DEM, s'activa el fallback a 0° indicant-ho a la UI.
- **Cicle de vida:** En desseleccionar o desactivar la trajectòria, s'alliberen geometries i materials propis mitjançant `dispose()`, sense afectar recursos compartits de l'escena.

## Tasques

- [x] Definir DTO i port renderer-neutral d'objecte observable, amb adaptadors per a les famílies disponibles i capacitats declarades.
- [x] Generalitzar el coordinador sense regressar el format binari ni el renderer del pas 9.
- [x] Mostrejar altura/azimut amb resolució adaptativa, comparar-los amb el perfil real i refinar els creuaments temporals.
- [x] Classificar els trams i diferenciar creuaments, tangències, absència de creuaments, circumpolaritat astronòmica i buits de perfil.
- [x] Projectar els trams amb estils diferenciats, retroil·luminació emissiva, marcadors temporals i etiquetes d'esdeveniment adaptatives al zoom (16 px).
- [x] Simplificar la interfície d'usuari a una única casella interactiva «Trajectòria de l'objecte» (activada per defecte) amb càlcul automàtic permanent de 24 hores i resolució detallada.
- [x] Activar el seguiment automàtic de càmera per defecte en clicar qualsevol objecte observable, amb indicació visual daurada `Seguint ✓` al HUD i manteniment de seguiment en mode d'ull nu.
- [x] Activar la Via Làctia per defecte en iniciar l'aplicació, amb persistència d'activació durant la càrrega del catàleg.
- [x] Implementar eina de captura i validació interactiva en navegador real (`frontend/tools/capture_step22.mjs`).
- [x] Generar evidències gràfiques reproduïbles a `docs/evidencies/pas22/`.
- [x] Verificar l'alliberament de recursos i absència de fuites de memòria en cicles repetits.

## Criteri de sortida

Totes les famílies d'objectes actualment disponibles (planetes, Sol, Lluna, satèl·lits naturals, estrelles, cel profund NGC/IC i coordenades lliures) disposen d'adaptador observable i mostren una trajectòria temporal coherent amb el perfil d'horitzó real (DEM) o astronòmic (0°), sense bloquejar la interfície, duplicar lògica astronòmica ni regressar el pas 9. El contracte de constel·lacions queda preparat per al pas 23.
S'han verificat tant les proves automatitzades com l'homologació visual interactiva i el cicle de vida dels recursos.

## Proves i evidències obligatòries

- [x] **Càlcul i classificació:** sortida i posta sobre horitzó pla, creuaments múltiples sobre relleu, tangència sense canvi de signe, continuïtat azimutal $0^\circ/360^\circ$: [`test_trajectory_visibility_step22.py`](../../../backend/tests/test_trajectory_visibility_step22.py) (9 proves superades).
- [x] **Regressió backend:** 165 proves superades a la suite de tests Python (`pytest backend/tests`).
- [x] **Frontend i contractes:** [`trajectory_visibility_step22.test.ts`](../../../frontend/src/tests/trajectory_visibility_step22.test.ts) (16 proves superades).
- [x] **Compilació i tipus:** `npm run typecheck` superat sense cap incidència.
- [x] **Homologació visual en navegador real (Chromium headless a 1440×900):**
  - [x] [Alba sobre el relleu oriental](../../evidencies/pas22/alba.png): sortida centrada a les carenes amb etiqueta de sortida més compacta `↑ Alba` i traça subterrània.
  - [x] [Posta sobre les muntanyes](../../evidencies/pas22/puesta.png): posta de Sol amb línia discontínua lila travessant de forma contínua tot el cos de les muntanyes sense talls i etiqueta compacta `↓ Posta`.
  - [x] [Trajectòria completa general amb zoom-out](../../evidencies/pas22/trajectoria-completa.png): perspectiva panoràmica (FOV 95°) mostrant la identificació de l'astre ("Sol") al HUD amb estat de seguiment actiu (`Seguint ✓`), l'astre centrat a la càmera i la caiguda diagonal de la línia cap a l'horitzó.
  - [x] [Horitzó astronòmic 0°](../../evidencies/pas22/astronomical-horizon.png): posta i sortida a l'horitzó pla en desactivar el terreny a Topografia.
  - [x] [Etiquetes invariants al zoom](../../evidencies/pas22/time-marker-and-labels.png): caixes d'esdeveniments amb alçada constant i compacta de 16 px de pantalla invariant al camp de visió.
- [x] **Neteja i cicle de vida:** desactivació de la trajectòria restablint l'estat a `Inactiva` i alliberant geometries, amb `browserErrors: []`.

## Fora d'abast

Planificació de sessions, edició de constel·lacions, geometria de constel·lacions pendent del pas 23, càlcul de nous tipus d'efemèride, meteorologia, foscor del cel, il·luminació de satèl·lits i predicció de detectabilitat instrumental.

## Instrucció per a Codex

Pas 22 completat amb èxit. El següent pas executable és el **Pas 23 — Constel·lacions oficials i d'usuari**. Revisa `docs/README.md` i `docs/normes-arquitectura.md` abans de començar.

## Treball pendent

Cap després del criteri de sortida.
