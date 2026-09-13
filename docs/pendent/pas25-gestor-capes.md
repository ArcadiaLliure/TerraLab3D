# Pas 25 — Gestor de capes Cel/Terra

> Estat: **pendent**. Hi ha models i casos d'ús de capes, files vinculades a recursos i pantalles Cel/Terra, però no una experiència unificada ni preferències restaurables.

## Estat actual verificat

- [x] Existeixen el paquet `domain/layers`, casos d'ús inicials i entrades separades a les pàgines Cel i Terra.
- [x] La UI ja pot distingir part de l'estat d'un recurs mitjançant el gestor central.
- [ ] Disponibilitat, visibilitat, refinament, AOI i preferències encara no formen un contracte complet.

## Resultat funcional

L'usuari administra des d'un mateix patró les capes de Cel i Terra: veu què està instal·lat, què és visible, quina àrea cobreix, descarrega recursos relacionats i restaura les seves preferències sense iniciar transferències inesperades.

## Dependències

- [Pas 24 — catàleg i descàrregues](pas24-cataleg-recursos-descarregues.md).

## Decisions tancades

- Cel i Terra comparteixen model i components, amb descriptors específics; Terra afegeix selector de cos actiu.
- `available`, `visible`, `enabled`, `refinementStatus` i `coverage` són dimensions separades.
- Un interruptor global només governa visibilitat; no instal·la ni elimina recursos.
- L'àrea d'interès (AOI) és un valor reutilitzable i versionat, no estat privat de cada modal.
- Les cards poden oferir “descarregar-ho tot”, variants o un assistent, però totes les accions deleguen al pas 24.
- En restaurar sessió s'apliquen preferències compatibles amb els recursos disponibles i mai s'inicia una descàrrega sense una acció actual de l'usuari.

## Codi existent a reutilitzar

- Domini i aplicació: [`layers/models.py`](../../backend/src/terralab3d/domain/layers/models.py), [`layers/services.py`](../../backend/src/terralab3d/domain/layers/services.py) i [`use_cases/layers.py`](../../backend/src/terralab3d/application/use_cases/layers.py).
- UI: [`SkyPage.ts`](../../frontend/src/view/ui/drawer_pages/SkyPage.ts), [`EarthPage.ts`](../../frontend/src/view/ui/drawer_pages/EarthPage.ts), [`ResourceManagerModal.ts`](../../frontend/src/view/ui/modals/ResourceManagerModal.ts) i [`ResourceBackedLayerRow.ts`](../../frontend/src/view/ui/components/ResourceBackedLayerRow.ts).
- Estat de recursos: [`ResourceManager.ts`](../../frontend/src/application/ResourceManager.ts) i [`layer_database.py`](../../backend/src/terralab3d/infrastructure/resources/layer_database.py).
- Persistència: [`persistence.py`](../../backend/src/terralab3d/application/ports/persistence.py).

## Treball pendent

- [ ] Definir descriptors i estat derivat de capa, amb invariants entre disponibilitat, visibilitat i refinament.
- [ ] Implementar AOI compartida i selector de cos actiu, amb serialització i validació.
- [ ] Construir components comuns de llista/card, filtres, feedback, accions massives i resum d'espai.
- [ ] Enllaçar les accions de recursos al gestor del pas 24 i propagar deltes d'instal·lació.
- [ ] Aplicar visibilitat incrementalment als renderers sense reconstruir l'escena.
- [ ] Persistir preferències amb esquema/versionat i restaurar només estats compatibles.
- [ ] Cobrir estats buit, parcial, error, recurs extern, cos sense catàleg i AOI sense cobertura.

## Flux tècnic

Descriptors + instal·lacions + preferències → selector de capa → view-model Cel/Terra → intenció d'usuari → cas d'ús de visibilitat o treball del pas 24 → delta al renderer i persistència.

## Errors, cancel·lació i recursos

- La UI conserva l'últim estat coherent durant errors de catàleg i diferencia error de capa d'error de descàrrega.
- Canviar AOI o cos cancel·la consultes obsoletes, no descàrregues ja confirmades.
- Desmuntar la vista elimina subscripcions; els renderers disposen recursos només quan una capa realment es descarrega de l'escena.

## Proves

- Matriu de `available/visible/enabled/refinementStatus/coverage` i invariants.
- Restauració amb recursos presents, absents, versions migrades i preferències desconegudes.
- Paritat funcional Cel/Terra, canvi de cos i AOI sense resultats.
- Accions massives, deltes incrementals i absència de descàrregues automàtiques.

## Criteri de sortida

Cel i Terra utilitzen el mateix contracte de gestió, l'usuari distingeix sempre disponibilitat i visibilitat, i una sessió es restaura sense efectes laterals ni reconstrucció global de l'escena.

## Evidències

- [ ] Captures equivalents de les vistes Cel i Terra.
- [ ] Vídeo de canvi de cos, AOI, instal·lació i activació posterior.
- [ ] Proves de migració/restauració i zero descàrregues no sol·licitades.
- [ ] Comptadors de deltes i renderers afectats per una sola capa.

## Fora d'abast

Les visualitzacions especialitzades dels passos 26–29 i els catàlegs de dades concrets.

## Instrucció per a Codex

Amplia els models, casos d'ús i components existents amb un contracte comú Cel/Terra. Mantén separades disponibilitat, visibilitat i refinament, i fes passar qualsevol transferència pel gestor del pas 24.
