# Adaptador d’infraestructura `light_pollution`

## Propòsit

Estimació geogràfica de contaminació lumínica.

El lector [`vnp46.py`](vnp46.py) del Pas 7.2 consumeix un grànul local
`VNP46A2.002` amb SHA-256 esperat i el [perfil v1](../../../../../../docs/skyglow/skyglow-v1-profile.json)
carregat explícitament. Retorna observacions de píxel o una finestra iterada,
amb radiància crua, QA, coordenades i procedència; no estima emissió ni skyglow.
La descàrrega i la cache queden fora del lector. El lector s'ha contrastat
amb un [grànul VNP46A2.002 real aportat localment](../../../../../../docs/evidencies/pas7.2/validacio-adaptador.md).

El lector [`viirs_rsr.py`](viirs_rsr.py) del Pas 7.3 obre taules RSR locals amb
manifest, SHA-256 i selector plataforma/producte/col·lecció/release/guany/data/aplicació.
S'ha contrastat amb una [taula SNPP LGS real](../../../../../../docs/evidencies/pas7.3/validacio-model-dnb.md)
i corbes LGS/MGS [NOAA-20/NOAA-21](../../../../../../docs/evidencies/pas7.3/revisio-multisatel-lit.md)
per diagnosticar l'operador TOA. Els manifests v2 separen classe d'evidència,
vincle L3 i incertesa; cap d'aquestes corbes acredita encara el producte L3 de 2026.
Dos [grànuls NOAA-20 reals](../../../../../../docs/evidencies/pas7.3/contrast-granuls-black-marble-c2.md)
s'han inspeccionat offline amb `h5py`, inclòs QA 0 urbà. El lector VNP46 els
rebutja per identitat; l'script d'inspecció no és un adaptador ni un downloader
del producte.

## Pertinença arquitectònica

**Infraestructura / Adaptador.** Implementa un port propietat de l’aplicació.

## Entrades i sortides

Rep DTO tipats o peticions del port i retorna DTO tipats, handles binaris o esdeveniments de progrés.

## Dependències permeses

- Ports de `terralab3d.application.ports`.
- Models purs del domini.
- Biblioteques concretes necessàries per a aquesta integració.

## Dependències prohibides

- UI i components Three.js.
- Decisions científiques que pertanyin al domini.
- Estat global mutable no encapsulat.

## PENDENTS

- [ ] Identificar el port exacte que implementa.
- [ ] Definir configuració i cicle de vida.
- [ ] Implementar cancel·lació i errors tipats.
- [ ] Caracteritzar la font equivalent de TerraLab abans de migrar-la.
- [ ] Mesurar memòria, latència i bytes transferits.
- [ ] Afegir proves amb recursos temporals o dobles del servei extern.

## Migració des de TerraLab

S’ha de traslladar només la part d’I/O, integració, caché o execució que correspongui. Qualsevol fórmula o decisió científica s’ha d’extreure al paquet de domini funcional apropiat.


## Assets científics verificats (7.5.1)

El lector A2 compartit admet VNP46/NOAA-20 amb polítiques explícites de producte, plataforma, DOI i versió. `black_marble_sources.py` connecta el grànul local verificat amb el constructor C de domini. `spectral_library.py` carrega CSV/metadades CIE empaquetats i verifica MD5/SHA-256 sense xarxa. `viirs_rsr.py` separa la selecció operativa estricta de `resolve_reference`, que conserva la validesa original i el mateix sensor/guany per a aproximacions C. Adquisició de grànuls i variants opcionals al gestor comú del Pas 24.
