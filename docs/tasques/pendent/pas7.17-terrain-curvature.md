# Pas 7.17 — Skyglow físic — terreny, horitzó i curvatura al kernel

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Integrar DEM real i curvatura amb visibilitat binària per raig.

## Descripció funcional

Trunca observer→sky i oculta source→P sense transparència artificial.

## Fonts a consultar

- [`docs/skyglow/README.md`](../../skyglow/README.md).
- [`02-arquitectura-integracio.md`](../../skyglow/02-arquitectura-integracio.md), [`08-validacio-cientifica.md`](../../skyglow/08-validacio-cientifica.md) i [`09-incertesa-proveniencia.md`](../../skyglow/09-incertesa-proveniencia.md).
- [`docs/normes-arquitectura.md`](../../normes-arquitectura.md).

## Objectiu

Integrar DEM real i curvatura amb visibilitat binària per raig.

## Dependències

**Depèn de:**
- [Pas 7.10](pas7.10-radiance-patch-quadtree.md)
- [Pas 7.2](pas7.2-kernel-geometric.md)

**En depenen:**
- [Pas 7.18](pas7.18-cache-error-based.md)
- [Pas 7.20](pas7.20-zenith-absolute-gate.md)

## Codi existent a reutilitzar

- DEM/horitzó/geodèsia existents per visibilitat i coordenades.
- `domain/atmosphere`, `domain/light_pollution` i bridge actuals.
- Caches existents només com a infraestructura; no confondre-les amb `PropagationCacheEntry`.

## Flux tècnic

Observer/source/ECEF + DEM authority → ray visibility → `V∈{0,1}` i `s_terrain`.

## Errors, cancel·lació i recursos

- Discontinuïtats invaliden abans de qualsevol linealització.
- Resultats obsolets es descarten i l'últim resultat vàlid es conserva segons política.
- Risc: Cost DEM source→P.
- Rollback: Acceleració conservadora; mai smoothing d'oclusió.

## Tasques

- [ ] Implementar només l'abast d'aquest pas.
- [ ] Afegir unitats, versions i procedència.
- [ ] Afegir proves de discontinuïtats i casos límit.
- [ ] Executar benchmark/validació indicats.
- [ ] Actualitzar documentació viva segons evidència.

## Criteri de sortida

muntanya sintètica, font parcial i font llunyana amb curvatura. Cost de visibilitat per patch/node. La decisió queda traçable i reproduïble.

## Proves i evidències obligatòries

- [ ] muntanya sintètica, font parcial i font llunyana amb curvatura.
- [ ] Cost de visibilitat per patch/node.
- [ ] Evidència sota `docs/evidencies/pas7.17/`.
- [ ] `tools/validate_docs.py` i regressions afectades en verd.

## Fora d'abast

Refracció atmosfèrica geomètrica.

## Instrucció per a Codex

Observer/source/ECEF + DEM authority → ray visibility → `V∈{0,1}` i `s_terrain`. No converteixis aproximacions de cache o renderer en física del kernel.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure el pas a `completat/`.