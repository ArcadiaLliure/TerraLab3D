# Pas 12 — Cerca astronòmica, focus i seguiment

> **Estat:** completat. **Estat funcional:** observable. **Origen:** planificat. **Abast vigent:** cerca astronòmica, focus i seguiment implementat, verificat i observable en el repositori.

## Descripció funcional

L’usuari pot cercar estrelles, planetes, Sol, Lluna, NGC o coordenades i orientar-hi la càmera o el scope.

## Fonts a consultar

- `TerraLab/astro/search_engine.py`
- `TerraLab/ui/widget_controls_builder.py` — `txt_search`
- `TerraLab/ui/astro_canvas.py`
- `TerraLab/widgets/telescope_scope_mode.py` — RA/Dec

## Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

## Dependències

**Depèn de:**
- [Pas 5 — Camp estel·lar Gaia real, fallback i buffers persistents](pas5.md)
- [Pas 11 — Cel profund NGC/IC](pas11.md)

**En depenen:**
- [Pas 13 — Picking real, hover, selecció i inspecció](pas13.md)
- [Pas 24 — Catàleg de recursos i descàrregues persistents](../pendent/pas24-cataleg-recursos-descarregues.md)
- [Pas 38 — Homologació final, recuperació i rendiment](../pendent/pas38-homologacio-final.md)

## Codi existent a reutilitzar

- **Repositori actual:** Models, coordinadors i renderers Three.js del repositori.
- **Projectes de referència autoritzats:** TerraLab (commit `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`).

## Flux tècnic

Integració domini Python → bridge de missatges/binari → escena Three.js persistent.

## Errors, cancel·lació i recursos

Gestió de recursos amb `dispose()`, cancel·lació cooperativa i degradació controlada en cas d'absència de dades.

## Tasques

- [ ] Construir un índex unificat de noms, àlies i identificadors.
- [ ] Definir una sintaxi explícita per a coordenades RA/Dec.
- [ ] Implementar normalització, ranking i límit de resultats.
- [ ] Retornar resultats tipats amb ID, tipus, nom i coordenada.
- [ ] Crear una UI de resultats navegable amb estat buit i errors.
- [ ] Separar completament `search` de `focus`.
- [ ] Implementar focus suau de càmera a una direcció o coordenada.
- [ ] Implementar seguiment d’un objecte mentre avança el temps.
- [ ] Permetre alliberar el seguiment amb una acció explícita.
- [ ] Fer que la cerca continuï disponible si una capa visual està oculta.
- [ ] Gestionar resultats de datasets no instal·lats amb explicació accionable.
- [ ] Comparar àlies, prioritats i casos de cerca de TerraLab.

## Criteri de sortida

La cerca retorna resultats reals i la càmera pot enfocar o seguir qualsevol objecte suportat sense alterar catàlegs o reconstruir l’escena.

## Proves i evidències obligatòries

- [ ] Proves de noms, àlies, coordenades i consultes ambigües.
- [ ] Vídeo de cerca → focus → seguiment → alliberament.
- [ ] Prova de dataset absent.

## Fora d'abast

El click directe, hover i inspecció es completen al pas següent.

## Instrucció per a Codex

Pas 12 completat amb èxit. Consultar el següent pas assenyalat a `docs/README.md`.

## Treball pendent

Cap després del criteri de sortida.
