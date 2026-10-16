# Pas 7.18 — Skyglow físic — cache error-based i invalidació topològica

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Implementar cache amb guardes topològiques i estimació contínua de `ΔB`.

## Descripció funcional

Moviments petits reutilitzen resultats només si l'error és acotat.

## Fonts a consultar

- [`docs/skyglow/README.md`](../../skyglow/README.md).
- [`02-arquitectura-integracio.md`](../../skyglow/02-arquitectura-integracio.md), [`08-validacio-cientifica.md`](../../skyglow/08-validacio-cientifica.md) i [`09-incertesa-proveniencia.md`](../../skyglow/09-incertesa-proveniencia.md).
- [`docs/normes-arquitectura.md`](../../normes-arquitectura.md).

## Objectiu

Implementar cache amb guardes topològiques i estimació contínua de `ΔB`.

## Dependències

**Depèn de:**
- [Pas 7.4](pas7.4-forward-ad-b1b.md)
- [Pas 7.11](pas7.11-optical-field.md)
- [Pas 7.17](pas7.17-terrain-curvature.md)

**En depenen:**
- [Pas 7.19](pas7.19-uncertainty-registry.md)
- [Pas 7.21](pas7.21-dome-profile-pchip.md)

## Codi existent a reutilitzar

- DEM/horitzó/geodèsia existents per visibilitat i coordenades.
- `domain/atmosphere`, `domain/light_pollution` i bridge actuals.
- Caches existents només com a infraestructura; no confondre-les amb `PropagationCacheEntry`.

## Flux tècnic

request/revision → coalescing → occlusion/topology guards → envelope → ΔB geometry+atmosphere → hit/miss → recompute o reutilització. El scheduler pot generar prefetch segons moviment, però el resultat prefetched passa les mateixes guardes abans de publicar-se. Cap frame de render crea per si sol una integral LOS.

## Errors, cancel·lació i recursos

- Discontinuïtats invaliden abans de qualsevol linealització.
- Resultats obsolets es descarten i l'últim resultat vàlid es conserva segons política; un resultat tardà no es publica. Pot entrar al cache només si clau, versions i dependències continuen essent vàlides.
- Risc: False hit amb error no detectat.
- Rollback: Invalidació més conservadora o total.

## Tasques

- [ ] Implementar només l'abast d'aquest pas.
- [ ] Afegir unitats, versions i procedència.
- [ ] Afegir proves de discontinuïtats i casos límit.
- [ ] Executar benchmark/validació indicats.
- [ ] Mesurar cold/warm, small-motion, moviment continu 3D, teleport, prefetch ON/OFF, coalescing, cancel·lació i time-to-first-valid.
- [ ] Actualitzar documentació viva segons evidència.

## Criteri de sortida

occlusion flip sempre miss, tile no relacionat no invalida i small move pot hit. cold/warm/small-motion/tile-change. Cap integral per frame; moviment ràpid es coalesça; teleport no reutilitza fora d'envelope; prefetch no pot produir false hit. La decisió queda traçable i reproduïble.

## Proves i evidències obligatòries

- [ ] occlusion flip sempre miss, tile no relacionat no invalida i small move pot hit.
- [ ] cold/warm/small-motion/tile-change.
- [ ] continuous-motion/teleport/prefetch/coalescing amb `recomputeHz`, `timeToFirstValidMs`, queue depth, cancelled jobs i stale discarded.
- [ ] Evidència sota `docs/evidencies/pas7.18/`.
- [ ] `tools/validate_docs.py` i regressions afectades en verd.

## Fora d'abast

SLO final de producció.

## Instrucció per a Codex

request → occlusion/topology guards → envelope → ΔB geometry+atmosphere → hit/miss. No converteixis aproximacions de cache o renderer en física del kernel.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure el pas a `completat/`.