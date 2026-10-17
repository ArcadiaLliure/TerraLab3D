# Adaptador d’infraestructura `light_pollution`

## Propòsit

Estimació geogràfica de contaminació lumínica.

El lector [`vnp46.py`](vnp46.py) del Pas 7.2 consumeix un grànul local
`VNP46A2.002` amb SHA-256 esperat i el [perfil v1](../../../../../../docs/skyglow/skyglow-v1-profile.json)
carregat explícitament. Retorna observacions de píxel o una finestra iterada,
amb radiància crua, QA, coordenades i procedència; no estima emissió ni skyglow.
La descàrrega i la cache queden fora del lector. El lector s'ha contrastat
amb un [grànul VNP46A2.002 real aportat localment](../../../../../../docs/evidencies/pas7.2/validacio-adaptador.md).

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
