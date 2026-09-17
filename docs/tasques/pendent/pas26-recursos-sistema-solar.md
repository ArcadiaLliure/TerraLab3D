# Pas 26 — Vista de recursos del Sistema Solar

> **Estat:** parcial. **Estat funcional:** parcial. **Origen:** planificat. **Abast vigent:** vista de recursos del sistema solar, integració observable i persistència associada.

## Descripció funcional

L'usuari entra a “Sistema Solar”, navega visualment per la jerarquia de cossos, consulta i instal·la els recursos de cada node i torna enrere sense perdre el context ni interrompre treballs en curs.

## Fonts a consultar

- [TerraLab al commit auditat `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`](https://github.com/ArcadiaLliure/TerraLab/tree/1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d): oracle autoritzat de comportament.

Decisions tancades de referència:
- La jerarquia és declarativa i prové del catàleg: arrel Sol, planetes i satèl·lits disponibles.
- La representació animada és una vista del gestor; no és una segona escena astronòmica ni navegació física lliure.
- Seleccionar un cos fa una transició espacial interactiva i obre les seves cards; “enrere” restaura el nivell i focus previs.
- SPICE i altres dependències compartides apareixen a l'arrel; els recursos específics pertanyen al cos corresponent.
- “Descarregar-ho tot” crea un bundle explícit al pas 24, amb resum de mida i llicències abans de confirmar.

## Objectiu

Completar la vertical de «vista de recursos del sistema solar» de punta a punta, mantenint la separació de responsabilitats, contractes tipats i integració amb el renderer Three.js sense anticipar capacitats posteriors.

## Dependències

**Depèn de:**
- [Pas 24 — Catàleg de recursos i descàrregues persistents](pas24-cataleg-recursos-descarregues.md)
- [Pas 25 — Gestor de capes Cel/Terra](pas25-gestor-capes.md)

**En depenen:**
- [Pas 38 — Homologació final, recuperació i rendiment](pas38-homologacio-final.md)

## Codi existent a reutilitzar

- **Repositori actual:** - Recursos solars: [`solar_system.py`](../../../backend/src/terralab3d/domain/resources/solar_system.py), [`solar_system_assets.py`](../../../backend/src/terralab3d/application/ports/solar_system_assets.py) i [`layer_database.py`](../../../backend/src/terralab3d/infrastructure/resources/layer_database.py).
- Model astronòmic: [`solar_system/catalog.py`](../../../backend/src/terralab3d/domain/solar_system/catalog.py) i [`solar_system/models.py`](../../../backend/src/terralab3d/domain/solar_system/models.py).
- Render existent: [`SolarSystemLayerRenderer.ts`](../../../frontend/src/view/three/layers/SolarSystemLayerRenderer.ts) i [`solar_system_contracts.ts`](../../../frontend/src/contracts/solar_system_contracts.ts).
- UI del gestor: [`ResourceManagerModal.ts`](../../../frontend/src/view/ui/modals/ResourceManagerModal.ts) i [`ResourceManager.ts`](../../../frontend/src/application/ResourceManager.ts).
- **Projectes de referència autoritzats:** TerraLab (commit `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`).

## Flux tècnic

Catàleg jeràrquic → view-model del node actual → escena de previsualització + llista de recursos → intenció de navegació o descàrrega → gestor del pas 24 → delta d'estat sense reiniciar la navegació.

## Errors, cancel·lació i recursos

- Una preview absent utilitza una representació determinista, sense impedir accedir a les cards.
- Navegar cancel·la només la càrrega visual obsoleta; les descàrregues confirmades continuen al gestor central.
- Geometries, textures temporals i listeners de la vista es disposen en tancar el modal.

## Tasques

- [x] El pas 8.6 incorpora actius versionats del Sistema Solar, manifest i càrrega incremental.
- [x] El gestor central ja pot representar recursos genèrics.
- [ ] No hi ha una vista jeràrquica Sol → planetes → satèl·lits amb navegació animada i accions contextuals.
- [ ] Estendre descriptors amb relació pare/fill, cos, dependències compartides i ordre de presentació.
- [ ] Crear el navegador jeràrquic amb breadcrumb/enrere, focus, teclat i reducció de moviment.
- [ ] Renderitzar nodes i transicions amb una escena lleugera, reutilitzant textures/previews sense acoblar-la a l'escena principal.
- [ ] Integrar cards, variants, estats i bundles del pas 24 a cada nivell.
- [ ] Preservar focus i scroll quan canvia l'estat d'una descàrrega.
- [ ] Afegir estats per cos sense recursos, recurs compartit i dependència ja instal·lada.

## Criteri de sortida

La jerarquia completa es pot recórrer de forma accessible i estable, i totes les instal·lacions es deleguen al catàleg i gestor centrals sense duplicar recursos ni escena científica.

## Proves i evidències obligatòries

- [ ] Jerarquia, breadcrumb, enrere, focus i navegació per teclat.
- [ ] Dependències compartides, bundles, cos buit i preview absent.
- [ ] Actualització d'estat durant una transició i tancament/reobertura del gestor.
- [ ] Pressupost de GPU i absència de recursos vius després de desmuntar.
- [ ] Vídeo Sol → planeta → satèl·lit → enrere amb focus preservat.
- [ ] Captura d'un bundle amb mida, llicències i dependències.
- [ ] Proves de navegació accessible i actualitzacions asíncrones.
- [ ] Mètriques de geometries, textures i memòria GPU abans/després.

## Fora d'abast

Vol lliure entre planetes, pilotatge d'una nau i representació científica nova dels cossos.

## Instrucció per a Codex

Construeix aquesta vista sobre el catàleg dels passos 24–25 i els actius del pas 8.6. La jerarquia i les transicions són UI del gestor; no introdueixis una segona font de veritat ni navegació espacial física.

## Treball pendent

- [ ] Completar totes les tasques i evidències d'aquest pas abans de tancar el criteri de sortida.
