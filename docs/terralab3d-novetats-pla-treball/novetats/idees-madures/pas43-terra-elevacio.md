# Pas 43 — Terra → Elevació (selector d'Àrea d'Interès multi-proveïdor)

> Estat: **proposta nova — idea madura**
> Origen: pluja d'idees TerraLab3D, "Tierra → Elevación".
> Depèn de: Pas 39 (esquelet), Pas 42 (sistema de descàrregues).

## Resultat funcional palpable

Dins de "Terra", la secció "Elevació" fa servir el mateix selector d'Àrea d'Interès que "Superfície", però en lloc de mostrar la jerarquia semàntica, consulta **tots** els DEM disponibles per a aquella zona (Copernicus, NASADEM i proveïdors nacionals/regionals) i els llista ordenats per resolució, cobertura, precisió, mida i tipus DTM/DSM — només fonts lliures per a ús comercial.

## Context i decisions preses

- Reutilitza el mateix component d'**Àrea d'Interès** que Superfície (Pas 44), però **sense jerarquia semàntica**: seleccionar AOI, consultar, i retorna tots els DEM que cobreixin la zona, de qualsevol proveïdor.
- Ordenació per: **resolució, cobertura efectiva, tipus DTM vs. DSM, mida estimada, data, llicència.**
- **Només fonts lliures per a ús comercial** (mateix criteri exigit a la resta del projecte).
- Cada targeta amb la mateixa mecànica de descàrrega del Pas 42 (barra de progrés, pausa, reprèn, cancel·la).
- **NASADEM** confirmat com a candidat: 30 m de resolució horitzontal (1 arcsegon), precisió vertical típica millor de 8 m en zones poc vegetades; competirà amb Copernicus i proveïdors locals dins d'aquest mateix llistat, no és una funcionalitat separada.
- Aquesta secció és **diferent** de "Picos y montañas" (Pas 48): elevació és geometria (DEM), els pics són nomenclatura/localització (GeoNames) — no s'han de confondre.

## Objectiu

Implementar la consulta multi-proveïdor de DEMs per Àrea d'Interès amb ordenació per qualitat i llicència, i integrar-la amb el sistema de descàrregues del Pas 42.

## Tasques

- [ ] Reutilitzar el component d'Àrea d'Interès (mapamundi + selecció de zona) ja existent al gestor de capes actual.
- [ ] Implementar la consulta a múltiples proveïdors de DEM (Copernicus, NASADEM, i proveïdors nacionals/regionals rellevants) per a l'AOI seleccionada.
- [ ] Filtrar únicament fonts amb llicència d'ús comercial confirmada.
- [ ] Ordenar els resultats per resolució, cobertura efectiva, tipus DTM/DSM, mida estimada, data i llicència.
- [ ] Mostrar cada DEM candidat com a targeta amb metadades i botó de descàrrega (Pas 42).
- [ ] Verificar que NASADEM apareix correctament al llistat competint amb Copernicus i fonts locals.

## Criteri de sortida

Seleccionar una AOI mostra tots els DEM disponibles i lliures per a ús comercial, ordenats de manera útil; descarregar-ne un fa servir el gestor de descàrregues del Pas 42 sense reimplementar-lo.

## Evidència obligatòria

- [ ] Captura del llistat de DEM per a una AOI de prova amb almenys tres proveïdors diferents.
- [ ] Verificació documentada que cap font sense ús comercial lliure apareix al llistat.

## Fora d'abast del pas

El nomenclàtor de pics/muntanyes (Pas 48), que és una capa de dades diferent (nom i localització, no geometria).

## Prompt per a Codex

```
Implementa el Pas 43 (Terra → Elevació) descrit a docs/novetats/idees-madures/pas43-terra-elevacio.md
sobre main, després dels Pas 39 i 42. Reutilitza el component d'Àrea d'Interès ja existent al gestor
de capes actual. Implementa la consulta multi-proveïdor de DEM (Copernicus, NASADEM, proveïdors
nacionals/regionals) per a l'AOI seleccionada, SENSE jerarquia semàntica (a diferència de Superfície,
Pas 44): només llista i ordena per resolució/cobertura/tipus DTM-DSM/mida/data/llicència, filtrant
només fonts d'ús comercial lliure. Cada targeta ha de fer servir el gestor de descàrregues del Pas 42,
no una implementació pròpia.
```
