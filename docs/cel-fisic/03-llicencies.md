# Auditoria de llicències — cel físic comercial

## Política vinculant

**No incorporar codi, textures, dades espectrals ni LUT de tercers amb restriccions d'ús comercial.** La disponibilitat pública, la publicació científica i l'ús en un motor comercial no concedeixen per si mateixos permís de còpia o redistribució. Registrar origen, URL, commit/versió, titular, text de llicència, atribució, dret de modificació, distribució de binaris, datasets derivats i dependències transitives abans de fer vendoring.

## Implementacions verificades (consulta de repositoris originals, 2026-10-16)

| Recurs | Llicència del repositori consultat | Ús comercial | Obligacions / límit |
|---|---|---|---|
| [Hillaire — UnrealEngineSkyAtmosphere](https://github.com/sebh/UnrealEngineSkyAtmosphere) | [MIT](https://github.com/sebh/UnrealEngineSkyAtmosphere/blob/master/LICENSE), copyright 2020 Epic Games, Inc. | **Permès** per al codi cobert per aquesta llicència | Conservar copyright i avís MIT en còpies o porcions substancials. Portar shaders/algoritme necessaris, no assumir llicència de tots els submòduls |
| [Bruneton — precomputed_atmospheric_scattering](https://github.com/ebruneton/precomputed_atmospheric_scattering) | [BSD-3-Clause](https://github.com/ebruneton/precomputed_atmospheric_scattering/blob/master/LICENSE), copyright 2017 Eric Bruneton | **Permès** | Retenir avisos i disclaimer; no usar noms per promocionar sense permís |
| [Three.js](https://github.com/mrdoob/three.js) | [MIT](https://github.com/mrdoob/three.js/blob/master/LICENSE) | **Permès** | Conservar avís i copyright en distribució |
| Unreal Engine i altres fitxers no coberts pel repositori MIT de Hillaire | **No verificat com a MIT** | **No autoritzat per inferència** | No copiar codi del motor ni assets propietaris; cal llicència independent |

L'exemple Hillaire conté submòduls com imgui i tinyexr i indica codi Bruneton copiat amb autorització. **No importar la demo sencera**: cada fitxer de tercers o dependència que es vulgui incorporar requereix auditoria individual. La llicència MIT del repositori no substitueix la dels submòduls.

## Models i dades encara no autoritzats per incorporar

- Espectre solar tabulat, reflectància/espectre lunar, paràmetres de models tipus ROLO, ozó/gasos, taules Mie i altres LUT: **pendent de verificar la llicència del producte/versió exactes**. Preferir models propis basats en equacions publicades i dades de domini públic o llicència permissiva verificable; les equacions publicades no impliquen que les taules o el codi de l'article siguin lliures.
- Productes meteorològics i òptics ERA5/CAMS: registrar producte concret, termes Copernicus i atribució. Les dades VIIRS, HITRAN i DEM tenen auditories específiques a [datasets skyglow](../skyglow/10-datasets-llicencies.md).
- Referències visuals, imatges terrestres o de núvols, fotografies i calibratges d'instruments: no empaquetar sense drets comercials i de redistribució verificats.

## Gate d'implementació

1. Fixar commit exacte de la font MIT/BSD i fitxers realment reutilitzats.
2. Inventariar dependències, fragments de codi, datasets i possibles restriccions.
3. Copiar els avisos necessaris a **THIRD-PARTY.md** només quan s'incorpori efectivament codi/recurs; aquest dossier és **planificació**, no declaració d'inclusió.
4. Bloquejar qualsevol asset o LUT amb drets no verificats; no substituir-lo per un resultat opac sense procedència.
5. Mantenir test de distribució que comprovi avisos i manifests.

Aquesta auditoria tècnica no substitueix una revisió jurídica de la distribució comercial final.
