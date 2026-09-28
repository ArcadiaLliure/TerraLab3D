# Pas 23.69 — Skyglow físic — DomeProfile, mostres angulars i PCHIP

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Comprimir el camp per font a 9 elevacions i reconstruir-lo en log-radiància.

## Descripció funcional

Produeix cúpules direccionals del mateix kernel.

## Fonts a consultar

- [`docs/skyglow/README.md`](../../skyglow/README.md).
- [`02-arquitectura-integracio.md`](../../skyglow/02-arquitectura-integracio.md), [`08-validacio-cientifica.md`](../../skyglow/08-validacio-cientifica.md) i [`09-incertesa-proveniencia.md`](../../skyglow/09-incertesa-proveniencia.md).
- [`docs/normes-arquitectura.md`](../../normes-arquitectura.md).

## Objectiu

Comprimir el camp per font a 9 elevacions i reconstruir-lo en log-radiància.

## Dependències

**Depèn de:**
- [Pas 23.51](pas23.51-kernel-geometric.md)
- [Pas 23.59](pas23.59-radiance-patch-quadtree.md)
- [Pas 23.67](pas23.67-cache-error-based.md)

**En depenen:**
- [Pas 23.70](pas23.70-three-renderer.md)
- [Pas 23.72](pas23.72-ground-truth-validation.md)

## Codi existent a reutilitzar

- DEM/horitzó/geodèsia existents per visibilitat i coordenades.
- `domain/atmosphere`, `domain/light_pollution` i bridge actuals.
- Caches existents només com a infraestructura; no confondre-les amb `PropagationCacheEntry`.

## Flux tècnic

kernel a 0.5/2/5/10/20/30/45/60/90° → `DomeProfile` → PCHIP log → radiància lineal.

## Errors, cancel·lació i recursos

- Discontinuïtats invaliden abans de qualsevol linealització.
- Resultats obsolets es descarten i l'últim resultat vàlid es conserva segons política.
- Risc: Error concentrat entre 0–2°.
- Rollback: Afegir mostres sense canviar API.

## Tasques

- [ ] Implementar només l'abast d'aquest pas.
- [ ] Afegir unitats, versions i procedència.
- [ ] Afegir proves de discontinuïtats i casos límit.
- [ ] Executar benchmark/validació indicats.
- [ ] Actualitzar documentació viva segons evidència.

## Criteri de sortida

zenit=90°, positivitat, wrap azimut i comparació all-sky. Mètriques de compressió i prova de mostra 1°. La decisió queda traçable i reproduïble.

## Proves i evidències obligatòries

- [ ] zenit=90°, positivitat, wrap azimut i comparació all-sky.
- [ ] Mètriques de compressió i prova de mostra 1°.
- [ ] Evidència sota `docs/evidencies/pas23.69/`.
- [ ] `tools/validate_docs.py` i regressions afectades en verd.

## Fora d'abast

Renderer final i tone mapping.

## Instrucció per a Codex

kernel a 0.5/2/5/10/20/30/45/60/90° → `DomeProfile` → PCHIP log → radiància lineal. No converteixis aproximacions de cache o renderer en física del kernel.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure el pas a `completat/`.