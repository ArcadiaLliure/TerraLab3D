# Pas 44 — Terra → Superfície (jerarquia de refinament conservada)

> Estat: **proposta nova — idea madura**
> Origen: pluja d'idees TerraLab3D, "Tierra → Superficie".
> Depèn de: Pas 39 (esquelet), Pas 42 (descàrregues), Pas 45 (model de refinament), Pas 46 (TLST).

## Resultat funcional palpable

Dins de "Terra", la secció "Superfície" conserva la vista jeràrquica actual (per classe de cobertura del sòl): l'usuari selecciona una jerarquia, prem "consultar" i el sistema li diu quins productes la resolen per a l'Àrea d'Interès triada, permetent descarregar el que vulgui.

## Context i decisions preses

- **Es conserva** l'enfocament actual de vista de jerarquies per obtenir productes ("no ho toquem, ho reaprofitem"): AOI → jerarquia → consultar → productes candidats.
- El que **canvia** és la **forma d'interpretar-los** un cop descarregats: passa del model antic (refinament com a família de capes separada) al nou model de refinament jeràrquic sota demanda (Pas 45) i a la traducció via TLST (Pas 46).
- Mateix component d'Àrea d'Interès que Elevació (Pas 43), però aquí **sí** apareix la jerarquia semàntica (13 classes del ràster base de Copernicus, cadascuna amb el seu arbre de refinadors possibles).
- Mateixa mecànica de descàrrega que la resta (Pas 42).

## Objectiu

Adaptar la UI actual de "Superfície" (àrea d'interès + jerarquia + consulta) al nou model conceptual del gestor de capes (Pas 39), connectant-la amb el motor de refinament sota demanda (Pas 45) i la traducció TLST (Pas 46).

## Tasques

- [ ] Migrar el component actual d'AOI + vista de jerarquies a l'esquelet del nou gestor de capes (Pas 39), sense reimplementar la lògica de consulta que ja funciona.
- [ ] Connectar el resultat de la consulta amb el nou motor de refinament jeràrquic (Pas 45) en lloc del pipeline antic de capes de refinament separades.
- [ ] Assegurar que cada producte descarregat passi pel traductor TLST (Pas 46) abans d'entrar a l'arbre de refinament.
- [ ] Reutilitzar el gestor de descàrregues (Pas 42) per a cada producte.
- [ ] Provar que seleccionar "superfície" mostra la jerarquia i seleccionar "elevació" (Pas 43) no la mostra, confirmant que els dos fluxos són coherents però diferenciats.

## Criteri de sortida

El flux AOI → jerarquia → consultar → descarregar funciona igual que abans des del punt de vista de l'usuari, però per sota utilitza el nou model de refinament (Pas 45) i la traducció TLST (Pas 46) en lloc del pipeline antic desconnectat.

## Evidència obligatòria

- [ ] Captura del flux complet de consulta per jerarquia per a una AOI de prova.
- [ ] Verificació que un dataset descarregat es tradueix correctament via TLST abans d'utilitzar-se en el refinament.

## Fora d'abast del pas

El disseny intern del motor de refinament (Pas 45) i de TLST (Pas 46), que es documenten a part.

## Prompt per a Codex

```
Implementa el Pas 44 (Terra → Superfície) descrit a docs/novetats/idees-madures/pas44-terra-superficie.md
sobre main, després dels Pas 39, 42, 45 i 46. Migra el flux actual d'Àrea d'Interès + vista de
jerarquies + consulta de productes (ja funcional al projecte) a l'esquelet del nou gestor de capes,
SENSE reimplementar la lògica de consulta existent. Substitueix el pipeline antic de "refinament com
a família de capes separada" per la connexió amb el nou motor de refinament jeràrquic sota demanda
(Pas 45) i el traductor TLST (Pas 46). Usa el gestor de descàrregues del Pas 42 per a cada producte.
```
