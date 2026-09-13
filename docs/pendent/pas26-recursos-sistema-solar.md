# Pas 26 — Vista de recursos del Sistema Solar

> Estat: **parcial**. El catàleg i el renderer del Sistema Solar existeixen; falta la navegació jeràrquica visual dins del gestor de recursos.

## Estat actual verificat

- [x] El pas 8.6 incorpora actius versionats del Sistema Solar, manifest i càrrega incremental.
- [x] El gestor central ja pot representar recursos genèrics.
- [ ] No hi ha una vista jeràrquica Sol → planetes → satèl·lits amb navegació animada i accions contextuals.

## Resultat funcional

L'usuari entra a “Sistema Solar”, navega visualment per la jerarquia de cossos, consulta i instal·la els recursos de cada node i torna enrere sense perdre el context ni interrompre treballs en curs.

## Dependències

- [Pas 24 — catàleg i descàrregues](pas24-cataleg-recursos-descarregues.md).
- [Pas 25 — gestor de capes](pas25-gestor-capes.md).

## Decisions tancades

- La jerarquia és declarativa i prové del catàleg: arrel Sol, planetes i satèl·lits disponibles.
- La representació animada és una vista del gestor; no és una segona escena astronòmica ni navegació física lliure.
- Seleccionar un cos fa una transició espacial interactiva i obre les seves cards; “enrere” restaura el nivell i focus previs.
- SPICE i altres dependències compartides apareixen a l'arrel; els recursos específics pertanyen al cos corresponent.
- “Descarregar-ho tot” crea un bundle explícit al pas 24, amb resum de mida i llicències abans de confirmar.

## Codi existent a reutilitzar

- Recursos solars: [`solar_system.py`](../../backend/src/terralab3d/domain/resources/solar_system.py), [`solar_system_assets.py`](../../backend/src/terralab3d/application/ports/solar_system_assets.py) i [`layer_database.py`](../../backend/src/terralab3d/infrastructure/resources/layer_database.py).
- Model astronòmic: [`solar_system/catalog.py`](../../backend/src/terralab3d/domain/solar_system/catalog.py) i [`solar_system/models.py`](../../backend/src/terralab3d/domain/solar_system/models.py).
- Render existent: [`SolarSystemLayerRenderer.ts`](../../frontend/src/view/three/layers/SolarSystemLayerRenderer.ts) i [`solar_system_contracts.ts`](../../frontend/src/contracts/solar_system_contracts.ts).
- UI del gestor: [`ResourceManagerModal.ts`](../../frontend/src/view/ui/modals/ResourceManagerModal.ts) i [`ResourceManager.ts`](../../frontend/src/application/ResourceManager.ts).

## Treball pendent

- [ ] Estendre descriptors amb relació pare/fill, cos, dependències compartides i ordre de presentació.
- [ ] Crear el navegador jeràrquic amb breadcrumb/enrere, focus, teclat i reducció de moviment.
- [ ] Renderitzar nodes i transicions amb una escena lleugera, reutilitzant textures/previews sense acoblar-la a l'escena principal.
- [ ] Integrar cards, variants, estats i bundles del pas 24 a cada nivell.
- [ ] Preservar focus i scroll quan canvia l'estat d'una descàrrega.
- [ ] Afegir estats per cos sense recursos, recurs compartit i dependència ja instal·lada.

## Flux tècnic

Catàleg jeràrquic → view-model del node actual → escena de previsualització + llista de recursos → intenció de navegació o descàrrega → gestor del pas 24 → delta d'estat sense reiniciar la navegació.

## Errors, cancel·lació i recursos

- Una preview absent utilitza una representació determinista, sense impedir accedir a les cards.
- Navegar cancel·la només la càrrega visual obsoleta; les descàrregues confirmades continuen al gestor central.
- Geometries, textures temporals i listeners de la vista es disposen en tancar el modal.

## Proves

- Jerarquia, breadcrumb, enrere, focus i navegació per teclat.
- Dependències compartides, bundles, cos buit i preview absent.
- Actualització d'estat durant una transició i tancament/reobertura del gestor.
- Pressupost de GPU i absència de recursos vius després de desmuntar.

## Criteri de sortida

La jerarquia completa es pot recórrer de forma accessible i estable, i totes les instal·lacions es deleguen al catàleg i gestor centrals sense duplicar recursos ni escena científica.

## Evidències

- [ ] Vídeo Sol → planeta → satèl·lit → enrere amb focus preservat.
- [ ] Captura d'un bundle amb mida, llicències i dependències.
- [ ] Proves de navegació accessible i actualitzacions asíncrones.
- [ ] Mètriques de geometries, textures i memòria GPU abans/després.

## Fora d'abast

Vol lliure entre planetes, pilotatge d'una nau i representació científica nova dels cossos.

## Instrucció per a Codex

Construeix aquesta vista sobre el catàleg dels passos 24–25 i els actius del pas 8.6. La jerarquia i les transicions són UI del gestor; no introdueixis una segona font de veritat ni navegació espacial física.
