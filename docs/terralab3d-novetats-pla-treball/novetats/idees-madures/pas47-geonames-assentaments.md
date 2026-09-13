# Pas 47 — GeoNames per a assentaments (nomenclàtor de pobles/ciutats)

> Estat: **proposta nova — idea madura**
> Origen: pluja d'idees TerraLab3D, "GeoNames para asentamientos" + tota la discussió de "pueblos".

## Resultat funcional palpable

En mirar el terreny, TerraLab3D sap dir quin poble o ciutat s'està mirant, etiquetant correctament la taca urbana detectada al ràster de superfície amb el nom real del nucli de població, fins i tot quan hi ha dos pobles molt junts.

## Context i decisions preses

- Font: **GeoNames**, classe **"P" (populated place)** — poble, ciutat, llogaret — amb coordenades. Llicència **CC BY 4.0**, permet ús comercial amb atribució. És **un punt per localitat** (latitud/longitud), no un contorn ni un polígon administratiu.
- **No confondre** amb un terme municipal/administratiu: un municipi és un polígon administratiu completament diferent (fora d'abast, capa administrativa separada si mai s'implementa).
- **La taca urbana la determina el ràster de superfície** (ja detectat com a "superfície artificial" al pipeline de refinament); **GeoNames només serveix per posar-hi el nom**.
- **Algorisme d'assignació:** un cop detectada una taca de superfície artificial, es comprova si alguna coordenada de GeoNames (punt de poble) **cau dins** de la taca → assignació directa. Si no, provar per **proximitat amb un llindar raonable**.
- **Diverses localitats a la mateixa taca** (p. ex. "El Morell" i "La Pobla de Mafumet" molt juntes, o una aglomeració): es posen **totes** les etiquetes corresponents, cadascuna al centre ja calculat pel seu propi punt GeoNames. Simple, predictible, sense necessitat de polígons administratius globals.
- La coordenada de GeoNames és només una **àncora nominal** ("aquesta taca es diu Àger"), mai defineix per si sola l'extensió del poble (que ve del ràster).
- Dataset descarregat/filtrat una sola vegada (classe P), empaquetat com a dada base (connecta amb el Pas 49).

## Objectiu

Integrar el dataset filtrat de GeoNames (classe P) i l'algorisme d'assignació de nom a taca urbana detectada.

## Tasques

- [ ] Descarregar i filtrar GeoNames per la classe "P" una sola vegada; empaquetar-lo com a asset del producte (no com a descàrrega sota demanda; connecta amb el Pas 49).
- [ ] Implementar la detecció de taques de superfície artificial ja disponible al pipeline de refinament (reaprofitar, no reimplementar).
- [ ] Implementar l'algorisme d'assignació: punt GeoNames dins la taca → assignació directa; si no, cerca per proximitat amb llindar configurable.
- [ ] Gestionar el cas de múltiples localitats sobre la mateixa taca: mostrar totes les etiquetes corresponents.
- [ ] Renderitzar l'etiqueta al centre calculat pel punt GeoNames de cada localitat assignada.
- [ ] Incloure l'atribució requerida per la llicència CC BY 4.0 al producte.

## Criteri de sortida

Per a una zona de prova amb pobles coneguts (inclosa una parella de pobles molt junts), TerraLab3D etiqueta correctament cada taca urbana amb el nom real, mostrant dues etiquetes quan calgui.

## Evidència obligatòria

- [ ] Captura d'una zona amb un sol poble ben etiquetat.
- [ ] Captura d'una zona amb dos pobles junts mostrant les dues etiquetes.
- [ ] Text d'atribució CC BY 4.0 visible a la documentació/crèdits del producte.

## Fora d'abast del pas

Límits administratius/municipals (capa diferent, no prevista). Rius (Pas fora d'aquest bloc, vegeu idea pendent "rius").

## Prompt per a Codex

```
Implementa el Pas 47 (GeoNames per a assentaments) descrit a
docs/novetats/idees-madures/pas47-geonames-assentaments.md sobre main. Descarrega i filtra GeoNames
per la classe "P" (populated place), empaqueta'l com a asset del producte (llicència CC BY 4.0, amb
atribució als crèdits). Implementa l'assignació de nom a taca urbana: reaprofita la detecció de
"superfície artificial" ja existent al pipeline de refinament de terreny, comprova si un punt
GeoNames cau dins la taca (assignació directa) o per proximitat amb llindar si no; si diverses
localitats cauen dins la mateixa taca, mostra totes les etiquetes. La coordenada GeoNames és només
una àncora nominal, mai defineix l'extensió de la taca (que ve del ràster).
```
