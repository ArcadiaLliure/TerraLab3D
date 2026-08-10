# Integració d’infraestructura `milky_way`

La Via Làctia no reutilitza la textura galàctica de TerraLab. El catàleg
`ResourceCatalog` descriu exclusivament els EXR celestes `milkyway_2020_*` de
NASA SVS 4851. `DownloadJobManager` els descarrega per streaming i calcula el
SHA-256 local; `ManagedGalacticAssets` només exposa al frontend el fitxer
registrat com a `READY` dins de la llibreria de dades.

No hi ha conversió Galactic→ICRS per a aquest recurs. La interpretació
ICRF/J2000 i les convencions RA/Dec pertanyen al renderer persistent
`GalacticSkyRenderer`.
