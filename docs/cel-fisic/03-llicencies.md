# Auditoria de llicències — cel físic comercial

## Política vinculant

Només es poden incorporar codi i dades amb **llicència permissiva compatible amb distribució comercial** o amb termes de dades que autoritzin explícitament l'ús requerit. La política no es limita literalment a MIT/BSD: pot admetre MIT, BSD, Apache-2.0, domini públic i llicències de dades comercials compatibles, sempre amb manifest i obligacions verificades.

La disponibilitat pública d'un article o repositori **no** autoritza automàticament codi, assets, LUT, taules o datasets. Registrar URL, versió/commit, titular, llicència, atribució, modificació, redistribució, derivats, checksum i dependències transitives.

## Recursos verificats o elegibles

| Recurs | Situació | Política TerraLab3D |
|---|---|---|
| Hillaire — `sebh/UnrealEngineSkyAtmosphere` | MIT per al codi del repositori cobert pel LICENSE | **Permès** amb avís; no inferir drets sobre Unreal Engine ni submòduls |
| Bruneton — `precomputed_atmospheric_scattering` | BSD-3-Clause | **Permès** amb avisos BSD |
| Three.js | MIT | **Permès** |
| ROLO/USGS lunar model/database | recursos USGS produïts pel govern federal, generalment domini públic; verificar cada fitxer i qualsevol contingut de tercers | **Preferit** per al model lunar, amb provenance per fitxer |
| ecRad / implementacions de referència modernes auditades | Apache-2.0 quan la versió exacta ho declari | **Permès** com a referència o dependència si es fixa versió i avisos |
| ERA5/CAMS/Copernicus | llicència de productes Copernicus compatible amb ús/redistribució comercial amb atribució, segons producte | **Permès** només amb manifest del producte exacte i text d'atribució |

## Recursos de referència que no es vendoritzen amb la política actual

| Recurs | Motiu | Ús permès al pla |
|---|---|---|
| ESO Advanced Sky Model / SkyCalc software | GPL en el software distribuït | articles, metodologia i comparacions externes; no incorporar el codi runtime |
| LIME Toolbox | LGPL-3 segons el repositori auditat | oracle extern/validació; no vendoritzar mentre la política exclogui copyleft |
| Hipparcos/Tycho com a nova dependència distribuïda | pàgines oficials poden imposar termes no comercials al producte concret | no introduir com a nova font comercial sense revisió específica |
| Gaia i derivats | els crèdits/open access no substitueixen els termes del release/producte exacte | reutilitzar només el recurs ja autoritzat pel projecte o auditar el producte concret abans de crear nous derivats |

GPL/LGPL **no significa “no comercial”**; s'exclouen del producte distribuït per la política de copyleft/compatibilitat del projecte, no perquè prohibeixin vendre.

## Fonts i URLs a registrar

- Hillaire: https://github.com/sebh/UnrealEngineSkyAtmosphere
- Bruneton: https://github.com/ebruneton/precomputed_atmospheric_scattering
- ROLO/USGS: https://www.usgs.gov/media/files/rolo-lunar-model-and-database
- Copernicus licence: https://cds.climate.copernicus.eu/licences/licence-to-use-copernicus-products
- ecRad: https://confluence.ecmwf.int/spaces/ECRAD/overview
- LIME: https://github.com/LIME-ESA/lime_tbx
- ESO Sky Model: https://www.hq.eso.org/sci/software/pipelines/skytools/skycalc

## Gate d'implementació

1. Fixar versió/commit i fitxers realment reutilitzats.
2. Resoldre llicència **per fitxer/dataset**, inclosos submòduls i dades.
3. Bloquejar `unavailable` qualsevol recurs de drets incerts; no substituir-lo per dades opaques.
4. Actualitzar `THIRD-PARTY.md` només quan el recurs s'incorpori realment.
5. Mantenir manifests d'atribució i proves de distribució.
6. No copiar codi propietari d'Unreal Engine ni assets propietaris perquè l'exemple Hillaire sigui MIT.

Aquesta auditoria tècnica no substitueix la revisió jurídica de la distribució comercial final.
