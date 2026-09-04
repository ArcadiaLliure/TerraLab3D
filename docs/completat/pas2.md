# Pas 2 — Ubicació geogràfica de l’observador i orientació local

> Estat: **completat**
> Classificat mitjançant implementació, proves i validacions del repositori.

La UI permet introduir latitud, longitud i alçada addicional; l’escena mostra la ubicació activa, orienta correctament els punts cardinals i manté l’estat en canviar la càmera.

## Fonts TerraLab a consultar

- `TerraLab/ui/widget_controls_builder.py` — latitud, longitud, reubicació i alçada addicional
- `TerraLab/terrain/terrain_coordinator.py` — consulta d’elevació
- `TerraLab/application/commands.py` i `controller.py`
- `TerraLab/scene/contracts.py` — `Observer`

## Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

## Tasques

- [x] Implementar el model immutable d’ubicació geodèsica amb unitats i rangs explícits.
- [x] Implementar la comanda `SetObserverLocation` i el cas d’ús de reubicació.
- [x] Crear un panell funcional amb latitud, longitud, alçada addicional i acció de reubicar.
- [x] Validar latitud [-90, 90], longitud normalitzada i valors finits.
- [x] Mostrar l’altitud del terreny com a pendent fins que existeixi el port DEM, sense inventar-la.
- [x] Calcular l’alçada efectiva com elevació coneguda més offset de l’observador.
- [x] Orientar el marc local Three.js perquè nord, est, sud i oest coincideixin amb la convenció astronòmica.
- [x] Mostrar un HUD discret amb coordenades, alçada efectiva i font de l’elevació.
- [x] Persistir temporalment l’estat de sessió dins del backend, sense afegir encara persistència en disc.
- [x] Fer que canviar ubicació publiqui un delta petit, no una reconstrucció del host.
- [x] Definir un error visible per coordenades invàlides o elevació no disponible.
- [x] Caracteritzar els valors per defecte i el comportament de reubicació de TerraLab.

## Criteri de sortida

L’usuari pot canviar d’ubicació, veure les coordenades i l’alçada efectiva, i comprovar visualment que el sistema local i els punts cardinals s’actualitzen sense reiniciar l’escena.

## Evidència obligatòria

- [x] Proves de validació i normalització geogràfica.
- [x] Prova d’integració UI → Python → delta → escena.
- [x] Comprovació manual amb almenys tres ubicacions i hemisferis diferents.
- [x] Registre del nombre de bytes enviats en una reubicació.

## Fora d’abast del pas

No calcula encara un perfil d’horitzó ni carrega DEM.
