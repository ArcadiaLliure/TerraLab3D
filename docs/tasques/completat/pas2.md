# Pas 2 — Ubicació geogràfica de l'observador i orientació local

> **Estat:** completat. **Estat funcional:** observable. **Origen:** planificat. **Abast vigent:** ubicació geogràfica de l'observador i orientació local implementat, verificat i observable en el repositori.

## Descripció funcional

Implementació de ubicació geogràfica de l'observador i orientació local completada i verificada en el repositori.

## Fonts a consultar

- `TerraLab/ui/widget_controls_builder.py` — latitud, longitud, reubicació i alçada addicional
- `TerraLab/terrain/terrain_coordinator.py` — consulta d’elevació
- `TerraLab/application/commands.py` i `controller.py`
- `TerraLab/scene/contracts.py` — `Observer`

## Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

## Dependències

**Depèn de:**
- [Pas 1 — Entorn 3D executable, càmera 360° i bridge Python ↔ Three.js](pas1.md)

**En depenen:**
- [Pas 3 — Rellotge de simulació, temps sideral i moviment visible](pas3.md)
- [Pas 4 — Grid celeste, brúixola, etiquetes i HUD](pas4.md)
- [Pas 15 — Elevació real, perfil d'horitzó i oclusió](pas15.md)
- [Pas 38 — Homologació final, recuperació i rendiment](../pendent/pas38-homologacio-final.md)

## Codi existent a reutilitzar

- **Repositori actual:** Models, coordinadors i renderers Three.js del repositori.
- **Projectes de referència autoritzats:** TerraLab (commit `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`).

## Flux tècnic

Integració domini Python → bridge de missatges/binari → escena Three.js persistent.

## Errors, cancel·lació i recursos

Gestió de recursos amb `dispose()`, cancel·lació cooperativa i degradació controlada en cas d'absència de dades.

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

## Proves i evidències obligatòries

- [x] Proves de validació i normalització geogràfica.
- [x] Prova d’integració UI → Python → delta → escena.
- [x] Comprovació manual amb almenys tres ubicacions i hemisferis diferents.
- [x] Registre del nombre de bytes enviats en una reubicació.

## Fora d'abast

No calcula encara un perfil d’horitzó ni carrega DEM.

## Instrucció per a Codex

Pas 2 completat amb èxit. Consultar el següent pas assenyalat a `docs/README.md`.

## Treball pendent

Cap després del criteri de sortida.
