# Pas 21 — Eines de mesura esfèrica

> **Estat:** completat. **Estat funcional:** observable. **Origen:** planificat. **Abast vigent:** eines de mesura esfèrica implementat, verificat i observable en el repositori.

## Descripció funcional

L'usuari pot triar `Regla`, `Quadrat`, `Rectangle` o `Cercle` a la pàgina
**Eines** i arrossegar sobre el cel. Durant el gest es reutilitza un buffer de
preview fix; en acabar, el backend valida la intenció angular, actualitza el
document immutable i publica un `measurement_snapshot` acceptat. La forma es
pot seleccionar per nansa o vora, moure rígidament, redimensionar per la nansa
final, eliminar i recuperar amb undo.

Les etiquetes mostren distància, amplada × alçada o radi · diàmetre. Es
reprojecten quan canvien càmera, FOV o viewport, però la persistència només
conté coordenades angulars, tipus, rotació i el marc 3D de seguiment; mai
coordenades de pantalla.

## Fonts a consultar

- [TerraLab al commit auditat `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`](https://github.com/ArcadiaLliure/TerraLab/tree/1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d).

## Objectiu

Completar la vertical funcional de «eines de mesura esfèrica» de punta a punta, mantenint la separació de responsabilitats i comprovant-ne el rendiment i funcionament observable.

## Dependències

**Depèn de:**
- [Pas 1 — Entorn 3D executable, càmera 360° i bridge Python ↔ Three.js](pas1.md)
- [Pas 13 — Picking real, hover, selecció i inspecció](pas13.md)

**En depenen:**
- [Pas 38 — Homologació final, recuperació i rendiment](../pendent/pas38-homologacio-final.md)

## Codi existent a reutilitzar

- **Repositori actual:** - [x] [Pas 6 — picking](pas6.md) i [Pas 13 — selecció](pas13.md): convencions de gest i picking en píxels CSS.
- [x] [Pas 19](pas19-modes-optics.md): una sola autoritat de càmera i actualització retinguda.
- [x] `CameraRigImpl` i `PointerGestureRouter` exposen bloqueig explícit mentre una eina és propietària del punter.
- **Projectes de referència autoritzats:** TerraLab (commit `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`).

## Flux tècnic

### Domini i aplicació

- [x] `SphericalMeasurementCalculator` calcula distància estable amb `atan2(|a×b|, a·b)`.
- [x] Els arcs de regla són SLERP, amb branca explícita per punts antipodals.
- [x] Cercle, quadrat i rectangle es construeixen sobre l'esfera amb destins i offsets gnòmics renderer-neutral.
- [x] `MeasurementDocumentHistory` aplica operacions immutables i manté undo/redo acotat (50 per defecte).
- [x] `MeasurementCoordinator` valida, versiona cada entitat i publica snapshots complets amb revisions monotòniques.
- [x] El bridge rebutja una `measurementRevision` obsoleta i conserva l'últim document acceptat.

### Interacció i render

- [x] `MeasurementController` converteix el raig de pantalla a coordenada horitzontal i no envia píxels al backend.
- [x] Un gest actiu bloqueja càmera i picking ordinari; `Escape` i `pointercancel` cancel·len sense crear historial.
- [x] El picking prioritza nanses i calcula distància real a cada segment projectat de la vora.
- [x] El control es diu simplement **Seguiment**: activat, les formes segueixen el marc RA/Dec; desactivat, totes congelen sense salt el quaternion 3D de l'instant i queden independents del moviment posterior del cel.
- [x] El mateix marc congelat s'aplica a línies, nanses, etiquetes, picking, preview d'edició i conversió del raig de pantalla.
- [x] La nansa inicial mou cercle/quadrat/rectangle rígidament; la final redimensiona; una vora mou la forma; la regla permet editar ambdós extrems.
- [x] El renderer conserva un batch de línia i un de nanses per entitat, comparteix materials i només substitueix l'entitat amb `entityVersion` modificada.
- [x] El preview usa un `Float32Array`/`BufferGeometry` fix de 512 vèrtexs, sense crear geometria durant `pointermove`.
- [x] Les etiquetes DOM s'invaliden per snapshot/càmera/viewport i no es recalculen incondicionalment per frame.
- [x] `restoreResources()` reactiva materials després de restaurar WebGL; `dispose()` allibera geometries, materials, grup i etiquetes.

### Persistència i contracte

- [x] `measurement-document.schema.json` defineix el snapshot v1 compartit.
- [x] `trackingEnabled` i `fixedQuaternion` formen part del snapshot i del JSON persistent; el canvi és autoritatiu, versionat, atòmic i reversible amb undo/redo.
- [x] El JSON persistent usa `schemaVersion: 1` i substitució atòmica amb temporals únics.
- [x] La migració v0 accepta l'antic camp `items`; un fitxer corrupte es conserva i genera un avís recuperable.
- [x] Els bloquejos transitoris de `os.replace` a Windows tenen cinc reintents acotats i prova de regressió.
- [x] `TERRALAB_STATE_ROOT` permet aïllar estat en validacions sense tocar les preferències de l'usuari.
- [x] El bundler considera `.ts`, `.tsx` i `.css` en la frescor; una modificació només CSS ja no deixa `bundle.css` obsolet.
- [x] L'HTML, el JS i el CSS actius es serveixen amb `Cache-Control: no-store`, i cada arrencada obre una URL identificada pel build; una pestanya antiga ja no pot reconnectar-se silenciosament a un backend nou.

## Errors, cancel·lació i recursos

Gestió de recursos amb `dispose()`, cancel·lació cooperativa i degradació controlada en cas d'absència de dades.

## Tasques

- [x] Implementar distància angular estable, arcs, rectangle/quadrat orientat i cercle esfèric.
- [x] Definir operacions immutables i historial undo/redo amb límit configurable.
- [x] Implementar creació amb preview, finalització/cancel·lació i arbitratge amb navegació de càmera.
- [x] Implementar picking de forma, vora i nansa; moure i redimensionar sense trencar geometria esfèrica.
- [x] Generar labels de distància, amplada/alçada, radi/diàmetre i unitat.
- [x] Publicar batches versionats i actualitzar només l'entitat modificada.
- [x] Persistir document amb esquema i migració; restaurar-lo en reiniciar.

## Criteri de sortida

- [x] Les quatre eines són completes, editables, persistents i numèricament estables.
- [x] El render no es reconstrueix globalment ni contamina la UI amb matemàtica esfèrica.
- [x] No queda cap criteri o evidència pendent del pas.

## Proves i evidències obligatòries

- [x] Casos `359,9° ↔ 0,1° = 0,2°`, zenit oposat `= 0,2°`, separació antipodal `= 180°` i separació microscòpica finita.
- [x] Radi nul i rectangle degenerat rebutjats; les quatre geometries tenen punts finits dins els dominis angulars.
- [x] Historial immutable/acotat, CRUD, clear, undo/redo, versions d'entitat, round-trip, migració i corrupció.
- [x] El toggle de seguiment congela totes les formes en un únic marc 3D normalitzat, persisteix després de reiniciar i reprèn RA/Dec en desfer o reactivar-lo.
- [x] Preview sense noves geometries, reconstrucció parcial, labels projectats i alliberament complet.
- [x] TypeScript, build frontend, suite Python, validador estructural, esquemes i link-check documental.
- [x] Resultat final de regressió: **156 proves Python** i tota la suite frontend,
- [x] inclosa `measurement_step21.test.ts`, superades. La prova específica del pas té
- [x] **12 casos Python** més les comprovacions frontend de geometria, projecció,
- [x] seguiment/fixació 3D i
- [x] lifecycle.

## Fora d'abast

Anotacions terrestres, mesures de superfície geodèsica i exportació GIS.

## Instrucció per a Codex

Pas 21 completat amb èxit. Consultar el següent pas assenyalat a `docs/README.md`.

## Treball pendent

Cap després del criteri de sortida.
