# Pas 21 — Regla, quadrat, rectangle i cercle editables

> Estat: **completat** el 15 de setembre de 2026. Vertical funcional, persistent i verificada en navegador real.

## Estat verificat

- [x] Existeixen models immutables, document versionat, càlcul esfèric, coordinador i contractes de bridge.
- [x] Les quatre eines estan connectades a la UI i a un renderer Three.js retingut.
- [x] Creació, selecció, moviment, redimensionament, eliminació, cancel·lació i undo/redo són observables.
- [x] El document es restaura després de reiniciar sense conservar cap coordenada de pantalla.

## Resultat funcional

L'usuari pot triar `Regla`, `Quadrat`, `Rectangle` o `Cercle` a la pàgina
**Eines** i arrossegar sobre el cel. Durant el gest es reutilitza un buffer de
preview fix; en acabar, el backend valida la intenció angular, actualitza el
document immutable i publica un `measurement_snapshot` acceptat. La forma es
pot seleccionar per nansa o vora, moure rígidament, redimensionar per la nansa
final, eliminar i recuperar amb undo.

Les etiquetes mostren distància, amplada × alçada o radi · diàmetre. Es
reprojecten quan canvien càmera, FOV o viewport, però la persistència només
conté altitud, azimut, tipus i rotació.

## Dependències reutilitzades

- [x] [Pas 6 — picking](pas6.md) i [Pas 13 — selecció](pas13.md): convencions de gest i picking en píxels CSS.
- [x] [Pas 19](pas19-modes-optics.md): una sola autoritat de càmera i actualització retinguda.
- [x] `CameraRigImpl` i `PointerGestureRouter` exposen bloqueig explícit mentre una eina és propietària del punter.

## Implementació

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
- [x] La nansa inicial mou cercle/quadrat/rectangle rígidament; la final redimensiona; una vora mou la forma; la regla permet editar ambdós extrems.
- [x] El renderer conserva un batch de línia i un de nanses per entitat, comparteix materials i només substitueix l'entitat amb `entityVersion` modificada.
- [x] El preview usa un `Float32Array`/`BufferGeometry` fix de 512 vèrtexs, sense crear geometria durant `pointermove`.
- [x] Les etiquetes DOM s'invaliden per snapshot/càmera/viewport i no es recalculen incondicionalment per frame.
- [x] `restoreResources()` reactiva materials després de restaurar WebGL; `dispose()` allibera geometries, materials, grup i etiquetes.

### Persistència i contracte

- [x] `measurement-document.schema.json` defineix el snapshot v1 compartit.
- [x] El JSON persistent usa `schemaVersion: 1` i substitució atòmica amb temporals únics.
- [x] La migració v0 accepta l'antic camp `items`; un fitxer corrupte es conserva i genera un avís recuperable.
- [x] Els bloquejos transitoris de `os.replace` a Windows tenen cinc reintents acotats i prova de regressió.
- [x] `TERRALAB_STATE_ROOT` permet aïllar estat en validacions sense tocar les preferències de l'usuari.
- [x] El bundler considera `.ts`, `.tsx` i `.css` en la frescor; una modificació només CSS ja no deixa `bundle.css` obsolet.

## Treball completat

- [x] Implementar distància angular estable, arcs, rectangle/quadrat orientat i cercle esfèric.
- [x] Definir operacions immutables i historial undo/redo amb límit configurable.
- [x] Implementar creació amb preview, finalització/cancel·lació i arbitratge amb navegació de càmera.
- [x] Implementar picking de forma, vora i nansa; moure i redimensionar sense trencar geometria esfèrica.
- [x] Generar labels de distància, amplada/alçada, radi/diàmetre i unitat.
- [x] Publicar batches versionats i actualitzar només l'entitat modificada.
- [x] Persistir document amb esquema i migració; restaurar-lo en reiniciar.

## Proves

- [x] Casos `359,9° ↔ 0,1° = 0,2°`, zenit oposat `= 0,2°`, separació antipodal `= 180°` i separació microscòpica finita.
- [x] Radi nul i rectangle degenerat rebutjats; les quatre geometries tenen punts finits dins els dominis angulars.
- [x] Historial immutable/acotat, CRUD, clear, undo/redo, versions d'entitat, round-trip, migració i corrupció.
- [x] Preview sense noves geometries, reconstrucció parcial, labels projectats i alliberament complet.
- [x] TypeScript, build frontend, suite Python, validador estructural, esquemes i link-check documental.

Resultat final de regressió: **153 proves Python** i tota la suite frontend,
inclosa `measurement_step21.test.ts`, superades. La prova específica del pas té
**11 casos Python** més les comprovacions frontend de geometria, projecció i
lifecycle.

## Evidències

- [x] [Vídeo del cicle complet](../evidencies/pas21/measurement-cycle.webm): crea les quatre eines, mou el cercle, redimensiona la regla, elimina i desfà.
- [x] [Captura de les quatre eines](../evidencies/pas21/four-tools.png) amb labels científics i nanses de selecció.
- [x] [Captura després d'editar, eliminar i desfer](../evidencies/pas21/edit-delete-undo.png).
- [x] La regla passa de `9,891°` a `15,498°`; el cercle es mou `91,76 CSS px` i conserva exactament `r 5,118° · Ø 10,236°`.
- [x] El HUD confirma conservació exacta de pose/FOV durant tots els gestos; quatre botons natius conserven `title` i `aria-pressed`.
- [x] Reinici real: es restauren quatre entitats i quatre labels visibles, sense errors de consola; JSON de cuatro mesures: **1.572 bytes**.
- [x] Comptadors retinguts: dues entitats creen 4 geometries més el preview fix; editar-ne una suma exactament 2 builds i 2 disposals, amb `activeEntityCount = 2`.

## Criteri de sortida

- [x] Les quatre eines són completes, editables, persistents i numèricament estables.
- [x] El render no es reconstrueix globalment ni contamina la UI amb matemàtica esfèrica.
- [x] No queda cap criteri o evidència pendent del pas.

## Fora d'abast

Anotacions terrestres, mesures de superfície geodèsica i exportació GIS.
