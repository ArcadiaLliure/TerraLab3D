# Pas 45 — Nou model de refinament ràster (arbre jeràrquic sota demanda)

> Estat: **proposta nova — idea madura (arquitectura acordada en detall)**
> Origen: pluja d'idees TerraLab3D, "Nuevo modelo de refinamiento raster".
> Depèn de: Pas 46 (TLST), amb el qual forma un sol nucli conceptual: *Adapter → TLST → classe canònica → arbre → intèrpret*.

## Resultat funcional palpable

Cada cel·la de terreny es classifica llegint primer el ràster base obligatori; si aquella classe té refinadors possibles i l'usuari **té** el dataset corresponent instal·lat localment, es consulta només aquella finestra concreta; si no el té, no es descarrega ni s'intenta res i es queda amb la classe base. Sense piràmides semàntiques gegants innecessàries.

## Context i decisions preses

- **Ràster base obligatori**: sempre s'ha de tenir (p. ex. Copernicus land cover amb 13 classes).
- **Els refinadors només es consulten quan la classe base els necessita.** Cada classe declara explícitament els seus possibles refinaments i els seus fallbacks.
- **Un refinador només es consulta si el dataset existeix localment.** Si l'usuari no té aquell dataset, ni s'intenta llegir: es retorna directament la classe genèrica.
- **Refinament jerarquitzat, de més específic a més genèric**: es prova el refinador més específic; si dona *NoData*, es puja un nivell; el **primer dat vàlid més específic guanya**. Regla simple sense "ifs" niats: "Prova-Refinador-Si-Tinc-Dataset-Si-NoData-Continua".
- Exemple concret de la pluja d'idees: ràster base diu "cultiu no especificat" a Catalunya (codi 17); hi ha un refinador de vinya/oliverar disponible; es consulta **només aquella cel·la/finestra** del ràster de refinament; si diu vinya i se sap que hi ha problemes de confusió amb oliverar en aquest ràster concret, es pot fer una segona comprovació específica.
- **Evitar piràmides semàntiques gegants preprocessades.** Les piràmides (overviews) es fan servir només per accelerar la **lectura espacial**, no per precalcular la decisió semàntica de cada cel·la: la decisió de què representa cada cel·la sempre es pren **en temps de consulta**, sota demanda.
- Falta per definir en detall (documentar-ho com a treball dins d'aquest mateix pas, no com a bloquejant): la forma exacta del graf de refinament per a cadascuna de les 13 classes, la prioritat quan dos refinadors competeixen pel mateix nivell, i com alinear espacialment ràsters de resolucions diferents sense degradar categories.

## Objectiu

Implementar el motor de classificació de cel·la per arbre de refinament jeràrquic, condicionat als datasets realment instal·lats i sense preprocessat semàntic global.

## Tasques

- [ ] Modelar, per a cadascuna de les 13 classes del ràster base de Copernicus, l'arbre de possibles refinadors i el seu ordre de prioritat (de més específic a més genèric).
- [ ] Implementar el bucle de consulta: "existeix el dataset de refinament localment?" → si no, classe base; si sí, consultar només la finestra rellevant → si NoData, pujar un nivell → repetir fins al primer dat vàlid.
- [ ] Definir la política de resolució de conflictes quan dos refinadors del mateix nivell competeixen per la mateixa cel·la.
- [ ] Definir el mètode d'alineació espacial entre ràsters de resolucions diferents sense degradar la categoria resultant.
- [ ] Mantenir les piràmides (overviews) exclusivament com a acceleradors de lectura espacial, sense that afectin la decisió semàntica.
- [ ] Migrar el pipeline de mosaic/refinament existent (`mosaic.py`, generació TLST) a aquest nou model sota demanda, retirant el preprocessat semàntic global on ja no calgui.
- [ ] Connectar aquest motor amb la UI de Superfície (Pas 44).

## Criteri de sortida

Per a una zona de prova amb dataset de refinament instal·lat i una altra sense, el motor retorna la classe refinada quan toca i la classe base quan el dataset no existeix, sense error ni intent de descàrrega no sol·licitada; el temps de consulta per tile és consistent amb l'ús de piràmides només per a lectura espacial.

## Evidència obligatòria

- [ ] Cas de prova amb refinador present: cel·la resolta a classe específica.
- [ ] Cas de prova amb refinador absent: cel·la resolta a classe base, sense intents d'accés al dataset absent.
- [ ] Document amb el graf de refinament final per a les 13 classes.

## Fora d'abast del pas

La traducció de codis font a classes canòniques (Pas 46, TLST) — aquest pas opera ja sobre codis canònics.

## Prompt per a Codex

```
Implementa el Pas 45 (Nou model de refinament ràster) descrit a
docs/novetats/idees-madures/pas45-model-refinament-raster.md sobre main. Construeix un motor de
classificació de cel·la per arbre jeràrquic: ràster base obligatori (13 classes de Copernicus land
cover) + refinadors opcionals que NOMÉS es consulten si el dataset corresponent existeix localment,
de més específic a més genèric, quedant-se amb el primer dat vàlid (regla "prova-si-tinc-dataset-
si-NoData-continua", sense ifs niats). Les piràmides GDAL existents (vegeu benchmark a
docs/completat/pas16.md i tools/benchmark_refinement_overviews.py) s'han d'usar NOMÉS per accelerar
la lectura espacial, mai per precalcular la decisió semàntica. Migra el pipeline actual de
mosaic.py cap a aquest model sota demanda. Documenta l'arbre de refinament resultant per a les 13
classes base.
```
