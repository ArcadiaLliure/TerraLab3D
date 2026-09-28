# Pas 23.68 — Skyglow físic — UncertaintyModelRegistry i propagació

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Separar PredictionUncertainty de CacheValidityUncertainty i modelar correlacions.

## Descripció funcional

Evita barrejar errors epistèmics, sistemàtics i canvis temporals.

## Fonts a consultar

- [`docs/skyglow/README.md`](../../skyglow/README.md).
- [`02-arquitectura-integracio.md`](../../skyglow/02-arquitectura-integracio.md), [`08-validacio-cientifica.md`](../../skyglow/08-validacio-cientifica.md) i [`09-incertesa-proveniencia.md`](../../skyglow/09-incertesa-proveniencia.md).
- [`docs/normes-arquitectura.md`](../../normes-arquitectura.md).

## Objectiu

Separar PredictionUncertainty de CacheValidityUncertainty i modelar correlacions.

## Dependències

**Depèn de:**
- [Pas 23.56](pas23.56-spectral-source-b2b.md)
- [Pas 23.65](pas23.65-atmos-provider-era5-cams.md)
- [Pas 23.67](pas23.67-cache-error-based.md)

**En depenen:**
- [Pas 23.72](pas23.72-ground-truth-validation.md)

## Codi existent a reutilitzar

- DEM/horitzó/geodèsia existents per visibilitat i coordenades.
- `domain/atmosphere`, `domain/light_pollution` i bridge actuals.
- Caches existents només com a infraestructura; no confondre-les amb `PropagationCacheEntry`.

## Flux tècnic

provider metadata + registry → components/covariàncies → propagació per Jacobians/ensemble → resultats separats.

## Errors, cancel·lació i recursos

- Discontinuïtats invaliden abans de qualsevol linealització.
- Resultats obsolets es descarten i l'últim resultat vàlid es conserva segons política.
- Risc: Falsa precisió estadística.
- Rollback: Intervals conservadors i components separats.

## Tasques

- [ ] Implementar només l'abast d'aquest pas.
- [ ] Afegir unitats, versions i procedència.
- [ ] Afegir proves de discontinuïtats i casos límit.
- [ ] Executar benchmark/validació indicats.
- [ ] Actualitzar documentació viva segons evidència.

## Criteri de sortida

biaix sistemàtic constant no força miss; correlació ρ=1 vs 0. Mesurar overhead d'incertesa per preparar B7. La decisió queda traçable i reproduïble.

## Proves i evidències obligatòries

- [ ] biaix sistemàtic constant no força miss; correlació ρ=1 vs 0.
- [ ] Mesurar overhead d'incertesa per preparar B7.
- [ ] Evidència sota `docs/evidencies/pas23.68/`.
- [ ] `tools/validate_docs.py` i regressions afectades en verd.

## Fora d'abast

Matriu densa enorme al runtime.

## Instrucció per a Codex

provider metadata + registry → components/covariàncies → propagació per Jacobians/ensemble → resultats separats. No converteixis aproximacions de cache o renderer en física del kernel.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure el pas a `completat/`.