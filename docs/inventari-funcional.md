# Inventari funcional cobert per l’esquelet

Aquest document certifica que l’estructura disposa d’un lloc explícit per a totes les funcionalitats visibles de TerraLab i per als fonaments científics compartits.

| # | Capacitat | Paquet principal | Separació interna |
|---:|---|---|---|
| 1 | Fonaments científics compartits | `domain/science` | Models + càlculs + serveis |
| 2 | Ubicació de l’observador | `domain/observer` | Models + càlculs + serveis |
| 3 | Temps astronòmic i simulació temporal | `domain/time` | Models + càlculs + serveis |
| 4 | Coordenades i transformacions astronòmiques | `domain/coordinates` | Models + càlculs + serveis |
| 5 | Càmera i navegació 360° | `domain/navigation` | Models + càlculs + serveis |
| 6 | Fons celeste, dia, nit i crepuscle | `domain/sky_background` | Models + càlculs + serveis |
| 7 | Atmosfera i extinció | `domain/atmosphere` | Models + càlculs + serveis |
| 8 | Meteorologia | `domain/climate` | Models + càlculs + serveis |
| 9 | Contaminació lumínica | `domain/light_pollution` | Models + càlculs + serveis |
| 10 | Fotometria astronòmica compartida | `domain/photometry` | Models + càlculs + serveis |
| 11 | Estrelles i catàleg gaia | `domain/stars` | Models + càlculs + serveis |
| 12 | Traces circumpolars | `domain/star_trails` | Models + càlculs + serveis |
| 13 | Sol, lluna i planetes | `domain/solar_system` | Models + càlculs + serveis |
| 14 | Eclipsis i ocultacions | `domain/eclipses` | Models + càlculs + serveis |
| 15 | Via làctia i pols planck | `domain/galactic` | Models + càlculs + serveis |
| 16 | Objectes de cel profund | `domain/deep_sky` | Models + càlculs + serveis |
| 17 | Cerca astronòmica | `domain/search` | Models + càlculs + serveis |
| 18 | Elevacions i dem | `domain/elevation` | Models + càlculs + serveis |
| 19 | Horitzó topogràfic | `domain/horizon` | Models + càlculs + serveis |
| 20 | Geometria de terreny 3d | `domain/terrain` | Models + càlculs + serveis |
| 21 | Superfícies, ortofoto i cobertura categòrica | `domain/surface` | Models + càlculs + serveis |
| 22 | Telescopi, ocular i geometria òptica | `domain/optics` | Models + càlculs + serveis |
| 23 | Simulació fotogràfica | `domain/imaging` | Models + càlculs + serveis |
| 24 | Selecció i inspecció | `domain/selection` | Models + càlculs + serveis |
| 25 | Mesures angulars i formes | `domain/measurements` | Models + càlculs + serveis |
| 26 | Constel·lacions editables | `domain/constellations` | Models + càlculs + serveis |
| 27 | Capes i visibilitat | `domain/layers` | Models + càlculs + serveis |
| 28 | Datasets, descàrregues i validació | `domain/datasets` | Models + càlculs + serveis |
| 29 | Recursos binaris i cicle de vida | `domain/resources` | Models + càlculs + serveis |
| 30 | Progrés, errors, mode de reserva i estat visible | `domain/feedback` | Models + càlculs + serveis |

## Funcionalitats de producte incloses

- Ubicació, elevació i alçada addicional de l’observador.
- Data, timeline, temps real i acceleració temporal.
- Càmera 360°, FOV, zoom, seguiment i navegació RA/Dec.
- Cel diürn, nocturn i crepuscular; atmosfera, clima i contaminació lumínica.
- Gaia, mode de reserva estel·lar, fotometria, puntes, escala i traces circumpolars.
- Sol, Lluna, planetes, fases, trajectòries i eclipsis.
- Via Làctia, pols Planck i catàleg NGC/IC.
- Cerca, selecció, picking i inspecció.
- DEM, horitzó, topografia, relleu 3D, ortofoto i superfície categòrica.
- Telescopi, ocular, sensors, relacions d’aspecte, focal, obertura, ISO i exposició.
- Regla, quadrat, rectangle, cercle i constel·lacions editables.
- Capes, datasets, descàrregues, preferències, progrés, errors i mode de reserva.
