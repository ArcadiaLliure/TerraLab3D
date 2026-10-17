# Pas 7.19 — Skyglow físic — UncertaintyModelRegistry i propagació

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
- [Pas 7.7](pas7.7-spectral-source-b2b.md)
- [Pas 7.16](pas7.16-atmos-provider-era5-cams.md)
- [Pas 7.18](pas7.18-cache-error-based.md)

**En depenen:**
- [Pas 7.20](pas7.20-zenith-absolute-gate.md)
- [Pas 7.26](pas7.26-ground-truth-validation.md)

## Codi existent a reutilitzar

- DEM/horitzó/geodèsia existents per visibilitat i coordenades.
- `domain/atmosphere`, `domain/light_pollution` i bridge actuals.
- Caches existents només com a infraestructura; no confondre-les amb `PropagationCacheEntry`.

## Flux tècnic

VNP46 product/release/low-radiance + prior SPD/model angular + provider atmosfèric → components/covariàncies/ensembles → propagació → `PredictionUncertainty` separada de `CacheValidityUncertainty`.

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

El contracte pot representar components desconeguts com a `unavailable` sense inventar sigmes. El gate 7.20 pot quantificar error numèric encara que alguns models quantitatius de producte restin pendents; la validació empírica 7.26/7.28 no els pot ometre. Biaix sistemàtic constant no força cache miss; correlació ρ=1 vs 0 queda provada.

## Proves i evidències obligatòries

- [ ] biaix sistemàtic constant no força miss; correlació ρ=1 vs 0.
- [ ] Mesurar overhead d'incertesa per preparar B7.
- [ ] Evidència sota `docs/evidencies/pas7.19/`.
- [ ] `tools/validate_docs.py` i regressions afectades en verd.

## Fora d'abast

Matriu densa enorme al runtime.

## Instrucció per a Codex

No inventis incerteses de VNP46 ni del punt zero. Separa components coneguts, desconeguts i estructurals; 7.20 necessita la infraestructura, 7.26/7.28 els models quantitatius que siguin necessaris per declarar precisió. No converteixis aproximacions de cache o renderer en física del kernel.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure el pas a `completat/`.