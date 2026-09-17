# Pas 5 — Camp estel·lar Gaia real, fallback i buffers persistents

> **Estat:** completat. **Estat funcional:** observable. **Origen:** planificat. **Abast vigent:** camp estel·lar gaia real, fallback i buffers persistents implementat, verificat i observable en el repositori.

## Descripció funcional

La volta celeste mostra estrelles reals de Gaia o del catàleg fallback, amb posició, magnitud, color, mida, puntes i rotació sideral fluida.

## Fonts a consultar

- `TerraLab/data/star_data_coordinator.py`
- `TerraLab/data/star_catalog_store.py`
- `TerraLab/data/tile_manifest.py`
- `TerraLab/data/catalogs/star_catalog.py`
- `TerraLab/scene/plans/stars.py`
- `TerraLab/render/stars_renderer.py`
- `TerraLab/data/layer_manager.py` — `SKY_STARS`

## Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

## Dependències

**Depèn de:**
- [Pas 1 — Entorn 3D executable, càmera 360° i bridge Python ↔ Three.js](pas1.md)
- [Pas 3 — Rellotge de simulació, temps sideral i moviment visible](pas3.md)

**En depenen:**
- [Pas 6 — Picking estel·lar precís](pas6.md)
- [Pas 10 — Via Làctia i pols galàctica Planck](pas10.md)
- [Pas 11 — Cel profund NGC/IC](pas11.md)
- [Pas 12 — Cerca astronòmica, focus i seguiment](pas12.md)
- [Pas 14 — Traces circumpolars i exposició temporal](pas14.md)
- [Pas 19 — Modes d'observació: ull nu, càmera fotogràfica i telescopi/Scope](pas19-modes-optics.md)
- [Pas 30 — Plate solving i comparador foto/simulació](../pendent/pas30-plate-solving.md)
- [Pas 38 — Homologació final, recuperació i rendiment](../pendent/pas38-homologacio-final.md)

## Codi existent a reutilitzar

- **Repositori actual:** Models, coordinadors i renderers Three.js del repositori.
- **Projectes de referència autoritzats:** TerraLab (commit `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`).

## Flux tècnic

Integració domini Python → bridge de missatges/binari → escena Three.js persistent.

## Errors, cancel·lació i recursos

Gestió de recursos amb `dispose()`, cancel·lació cooperativa i degradació controlada en cas d'absència de dades.

## Tasques

- [x] Definir registres i columnes tipades per RA, Dec, magnitud, BP-RP/color i identificador.
- [x] Implementar `StarCatalogPort` amb catàleg general, fallback i consultes de con.
- [x] Preservar la política out-of-core, generacions, cancel·lació i last-request-wins.
- [x] Preservar pressupostos de caché per bytes i eviction de tiles no actius.
- [x] Convertir el catàleg a buffers binaris transferibles sense còpies innecessàries.
- [x] Registrar cada catàleg o tile com a recurs amb ID, versió, owner i mida.
- [x] Construir `BufferGeometry` persistent amb atributs separats de posició, magnitud, color i ID.
- [x] Implementar shader de punt circular o PSF suau; prohibir estrelles quadrades.
- [x] Implementar escala de mida, magnitud límit i llindar de puntes de difracció.
- [x] Mantenir les posicions estel·lars fixes en el marc celeste i rotar un node pare.
- [x] Mostrar estat de Gaia, fallback, extensió i errors de catàleg a la UI.
- [x] Implementar càrrega progressiva sense fer desaparèixer el catàleg general.
- [x] Evitar retransferir buffers quan canvia la càmera, el temps o un uniform visual.
- [x] Caracteritzar recompte, color, ordenació i màxim de magnitud de TerraLab.

## Criteri de sortida

Les estrelles són reals, suaus i fluides; Gaia/fallback és visible; el catàleg es transfereix una sola vegada per versió; canviar un segon o moure càmera només altera transforms o uniforms.

## Proves i evidències obligatòries

- [x] Recompte i hash dels buffers carregats.
- [x] Captures de magnituds i colors representatius.
- [x] Mesures de temps de càrrega, RSS, memòria GPU estimada i bytes del bridge.
- [x] Prova de cancel·lació d’una consulta de con obsoleta.
- [x] Vídeo de navegació i timeline amb el catàleg carregat.

## Fora d'abast

No inclou encara cel físic, contaminació lumínica ni picking final.

## Instrucció per a Codex

Pas 5 completat amb èxit. Consultar el següent pas assenyalat a `docs/README.md`.

## Treball pendent

Cap després del criteri de sortida.
