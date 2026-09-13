# Pas 34 — Miniatures i animacions d'efemèrides

> Estat: **pendent**. L'escena i el bucle de render existeixen, però no hi ha captures offscreen versionades per esdeveniment.

## Estat actual verificat

- [x] TerraLab3D disposa de renderer real, scene host, render loop i exportació d'imatge.
- [x] Els passos 32–33 aporten resultats d'efemèride i la seva llista.
- [ ] No existeixen framing automàtic, render offscreen, cache ni animació curta vinculada a una efemèride.

## Resultat funcional

Cada efemèride pot mostrar una miniatura generada pel mateix renderer i, en obrir el detall, una animació curta centrada i enquadrada en els actors reals de l'esdeveniment.

## Dependències

- [Pas 32 — motor d'efemèrides](pas32-motor-efemerides.md).
- [Pas 33 — cercador multipestanya](pas33-cercador-objectes-efemerides.md).

## Decisions tancades

- No s'utilitzen fotografies externes: la previsualització és una captura de l'escena científica amb un preset controlat.
- La llista mostra miniatures estàtiques; l'animació només s'activa al detall o sota acció explícita.
- La càmera offscreen calcula FOV i centre a partir de l'envolupant angular dels actors, amb marges i límits deterministes.
- La cache es clau per esdeveniment, observador, instant/interval, tema, viewport, versions de catàleg/kernel i versió del preset.
- Generar previews no muta càmera, selecció, temps ni recursos de l'escena principal.

## Codi existent a reutilitzar

- Escena: [`ThreeSceneHostImpl.ts`](../../frontend/src/view/three/ThreeSceneHostImpl.ts), [`RenderLoopImpl.ts`](../../frontend/src/view/three/RenderLoopImpl.ts) i [`CameraRigImpl.ts`](../../frontend/src/view/three/CameraRigImpl.ts).
- Exportació: [`ports/imaging.py`](../../backend/src/terralab3d/application/ports/imaging.py) i [`imaging_export/adapter.py`](../../backend/src/terralab3d/infrastructure/adapters/imaging_export/adapter.py).
- Contractes: [`astronomical_event_contracts.ts`](../../frontend/src/contracts/astronomical_event_contracts.ts).
- Models visuals: [`InspectionModelBuilder.ts`](../../frontend/src/application/InspectionModelBuilder.ts).

## Treball pendent

- [ ] Definir `PreviewRequest`, preset, clau de cache, resultat i política d'invalidació.
- [ ] Implementar framing esfèric per un o múltiples actors, incloent wrap RA/azimut i mides aparents extremes.
- [ ] Crear host offscreen aïllat que reutilitzi renderers/catàlegs sense compartir estat mutable amb l'escena principal.
- [ ] Generar thumbnail estàtic i seqüència curta al voltant de l'instant de l'esdeveniment.
- [ ] Integrar miniatures virtualitzades i animació lazy al detall del pas 33.
- [ ] Afegir cache acotada, deduplicació de treballs i prioritat per elements visibles.

## Flux tècnic

Resultat d'efemèride → sol·licitud/versionat → càlcul de framing → escena offscreen → captura o frames → cache → URL/bitmap transferible → card o detall.

## Errors, cancel·lació i recursos

- Scroll, tancament o canvi de consulta cancel·la previews fora de viewport i prioritza les visibles.
- Una preview fallida mostra placeholder tipat i no afecta el resultat d'efemèride.
- Render targets, textures, bitmaps i workers es disposen; la cache té límit de bytes i política LRU.
- Context loss invalida artefactes GPU i permet regenerar-los des del model.

## Proves

- Framing de dos actors, envolupant al wrap, objecte únic i escala extrema.
- Aïllament: temps/càmera/selecció principals invariants abans i després.
- Cache hit/miss/invalidation, deduplicació, prioritats i cancel·lació per scroll.
- Context loss, límit de memòria i desmuntatge de l'host offscreen.

## Criteri de sortida

La llista carrega miniatures sense bloquejar ni alterar l'escena principal i el detall anima l'esdeveniment real amb framing correcte, cache acotada i recursos recuperables.

## Evidències

- [ ] Golden captures de casos de framing representatius.
- [ ] Vídeo de llista virtualitzada i animació al detall.
- [ ] Prova d'invariància de l'escena principal i cancel·lació per scroll.
- [ ] Mètriques de latència, hit ratio, bytes de cache i recursos GPU.

## Fora d'abast

Exportació de vídeos llargs, assets promocionals i fotografies de tercers.

## Instrucció per a Codex

Genera previews amb un host offscreen aïllat que reutilitzi els renderers reals. Mantén la llista estàtica, anima només sota demanda i prova que càmera, temps i selecció principals no canvien.
