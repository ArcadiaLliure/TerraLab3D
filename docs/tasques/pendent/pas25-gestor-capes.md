# Pas 25 — Gestor de capes Cel/Terra

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** gestor de capes cel/terra, integració observable i persistència associada.

## Descripció funcional

L'usuari administra des d'un mateix patró les capes de Cel i Terra: veu què està instal·lat, què és visible, quina àrea cobreix, descarrega recursos relacionats i restaura les seves preferències sense iniciar transferències inesperades.

## Fonts a consultar

- [TerraLab al commit auditat `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`](https://github.com/ArcadiaLliure/TerraLab/tree/1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d): oracle autoritzat de comportament.

Decisions tancades de referència:
- Cel i Terra comparteixen model i components, amb descriptors específics; Terra afegeix selector de cos actiu.
- `available`, `visible`, `enabled`, `refinementStatus` i `coverage` són dimensions separades.
- Un interruptor global només governa visibilitat; no instal·la ni elimina recursos.
- L'àrea d'interès (AOI) és un valor reutilitzable i versionat, no estat privat de cada modal.
- Les cards poden oferir “descarregar-ho tot”, variants o un assistent, però totes les accions deleguen al pas 24.
- En restaurar sessió s'apliquen preferències compatibles amb els recursos disponibles i mai s'inicia una descàrrega sense una acció actual de l'usuari.

## Objectiu

Completar la vertical de «gestor de capes cel/terra» de punta a punta, mantenint la separació de responsabilitats, contractes tipats i integració amb el renderer Three.js sense anticipar capacitats posteriors.

## Dependències

**Depèn de:**
- [Pas 24 — Catàleg de recursos i descàrregues persistents](pas24-cataleg-recursos-descarregues.md)

**En depenen:**
- [Pas 26 — Vista de recursos del Sistema Solar](pas26-recursos-sistema-solar.md)
- [Pas 27 — Carta de recursos d'espai profund](pas27-recursos-espai-profund.md)
- [Pas 28 — Descobriment de DEM multiproveïdor](pas28-dem-multiproveidor.md)
- [Pas 29 — Superfície semàntica, TLST i refinament](pas29-superficie-semantica.md)
- [Pas 38 — Homologació final, recuperació i rendiment](pas38-homologacio-final.md)

## Codi existent a reutilitzar

- **Repositori actual:** - Domini i aplicació: [`layers/models.py`](../../../backend/src/terralab3d/domain/layers/models.py), [`layers/services.py`](../../../backend/src/terralab3d/domain/layers/services.py) i [`use_cases/layers.py`](../../../backend/src/terralab3d/application/use_cases/layers.py).
- UI: [`SkyPage.ts`](../../../frontend/src/view/ui/drawer_pages/SkyPage.ts), [`EarthPage.ts`](../../../frontend/src/view/ui/drawer_pages/EarthPage.ts), [`ResourceManagerModal.ts`](../../../frontend/src/view/ui/modals/ResourceManagerModal.ts) i [`ResourceBackedLayerRow.ts`](../../../frontend/src/view/ui/components/ResourceBackedLayerRow.ts).
- Estat de recursos: [`ResourceManager.ts`](../../../frontend/src/application/ResourceManager.ts) i [`layer_database.py`](../../../backend/src/terralab3d/infrastructure/resources/layer_database.py).
- Persistència: [`persistence.py`](../../../backend/src/terralab3d/application/ports/persistence.py).
- **Projectes de referència autoritzats:** TerraLab (commit `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`).

## Flux tècnic

Descriptors + instal·lacions + preferències → selector de capa → view-model Cel/Terra → intenció d'usuari → cas d'ús de visibilitat o treball del pas 24 → delta al renderer i persistència.

## Errors, cancel·lació i recursos

- La UI conserva l'últim estat coherent durant errors de catàleg i diferencia error de capa d'error de descàrrega.
- Canviar AOI o cos cancel·la consultes obsoletes, no descàrregues ja confirmades.
- Desmuntar la vista elimina subscripcions; els renderers disposen recursos només quan una capa realment es descarrega de l'escena.

## Tasques

- [x] Existeixen el paquet `domain/layers`, casos d'ús inicials i entrades separades a les pàgines Cel i Terra.
- [x] La UI ja pot distingir part de l'estat d'un recurs mitjançant el gestor central.
- [ ] Disponibilitat, visibilitat, refinament, AOI i preferències encara no formen un contracte complet.
- [ ] Definir descriptors i estat derivat de capa, amb invariants entre disponibilitat, visibilitat i refinament.
- [ ] Implementar AOI compartida i selector de cos actiu, amb serialització i validació.
- [ ] Construir components comuns de llista/card, filtres, feedback, accions massives i resum d'espai.
- [ ] Enllaçar les accions de recursos al gestor del pas 24 i propagar deltes d'instal·lació.
- [ ] Aplicar visibilitat incrementalment als renderers sense reconstruir l'escena.
- [ ] Persistir preferències amb esquema/versionat i restaurar només estats compatibles.
- [ ] Cobrir estats buit, parcial, error, recurs extern, cos sense catàleg i AOI sense cobertura.

## Criteri de sortida

Cel i Terra utilitzen el mateix contracte de gestió, l'usuari distingeix sempre disponibilitat i visibilitat, i una sessió es restaura sense efectes laterals ni reconstrucció global de l'escena.

## Proves i evidències obligatòries

- [ ] Matriu de `available/visible/enabled/refinementStatus/coverage` i invariants.
- [ ] Restauració amb recursos presents, absents, versions migrades i preferències desconegudes.
- [ ] Paritat funcional Cel/Terra, canvi de cos i AOI sense resultats.
- [ ] Accions massives, deltes incrementals i absència de descàrregues automàtiques.
- [ ] Captures equivalents de les vistes Cel i Terra.
- [ ] Vídeo de canvi de cos, AOI, instal·lació i activació posterior.
- [ ] Proves de migració/restauració i zero descàrregues no sol·licitades.
- [ ] Comptadors de deltes i renderers afectats per una sola capa.

## Fora d'abast

Les visualitzacions especialitzades dels passos 26–29 i els catàlegs de dades concrets.

## Instrucció per a Codex

Amplia els models, casos d'ús i components existents amb un contracte comú Cel/Terra. Mantén separades disponibilitat, visibilitat i refinament, i fes passar qualsevol transferència pel gestor del pas 24.

## Treball pendent

- [ ] Completar totes les tasques i evidències d'aquest pas abans de tancar el criteri de sortida.
