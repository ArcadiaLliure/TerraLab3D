# Pas 4 — Grid celeste, brúixola, etiquetes i HUD

> **Estat:** completat. **Estat funcional:** observable. **Origen:** planificat. **Abast vigent:** grid celeste, brúixola, etiquetes i hud implementat, verificat i observable en el repositori.

## Descripció funcional

L’entorn 3D mostra una quadrícula azimut-altura útil, brúixola, zenit, horitzó, etiquetes legibles i HUD configurable mentre la càmera i el temps es mouen.

## Fonts a consultar

- `TerraLab/render/grid_renderer.py`
- `TerraLab/render/overlays_renderer.py`
- `TerraLab/ui/astro_canvas.py`
- `TerraLab/scene/projection.py`

## Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

## Dependències

**Depèn de:**
- [Pas 1 — Entorn 3D executable, càmera 360° i bridge Python ↔ Three.js](pas1.md)
- [Pas 2 — Ubicació geogràfica de l'observador i orientació local](pas2.md)
- [Pas 3 — Rellotge de simulació, temps sideral i moviment visible](pas3.md)

**En depenen:**
- [Pas 38 — Homologació final, recuperació i rendiment](../pendent/pas38-homologacio-final.md)

## Codi existent a reutilitzar

- **Repositori actual:** Models, coordinadors i renderers Three.js del repositori.
- **Projectes de referència autoritzats:** TerraLab (commit `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`).

## Flux tècnic

Integració domini Python → bridge de missatges/binari → escena Three.js persistent.

## Errors, cancel·lació i recursos

Gestió de recursos amb `dispose()`, cancel·lació cooperativa i degradació controlada en cas d'absència de dades.

## Tasques

- [x] Definir geometria renderer-neutral per a grid horitzontal i referències principals.
- [x] Implementar línies d’azimut, cercles d’altitud, horitzó i marca de zenit.
- [x] Implementar etiquetes N/E/S/O i valors angulars amb orientació llegible.
- [x] Aplicar densitat adaptativa segons FOV per evitar soroll visual.
- [x] Evitar regenerar tota la geometria quan només canvia la càmera.
- [x] Implementar culling d’etiquetes i prevenció de solapaments bàsica.
- [x] Afegir toggles per grid, brúixola, labels i HUD.
- [x] Mostrar azimut, altitud i FOV actuals al HUD.
- [x] Fer que les etiquetes mantinguin una mida coherent amb DPR i resize.
- [x] Definir una capa overlay separada dels objectes celestes.
- [x] Afegir mode de colors purs/diagnòstic per verificar geometria i contrast.
- [x] Comparar orientació, densitat i convencions amb TerraLab.

## Criteri de sortida

La navegació ja és espacialment comprensible: l’usuari pot orientar-se, llegir azimut/altitud i activar o desactivar overlays sense canviar l’estat científic.

## Proves i evidències obligatòries

- [x] Captures amb diferents FOV, DPR i orientacions.
- [x] Prova que moure càmera no reconstrueix buffers estàtics del grid.
- [x] Proves de convencions angulars i punts cardinals.

## Fora d'abast

No inclou catàlegs astronòmics.

## Instrucció per a Codex

Pas 4 completat amb èxit. Consultar el següent pas assenyalat a `docs/README.md`.

## Treball pendent

Cap després del criteri de sortida.
