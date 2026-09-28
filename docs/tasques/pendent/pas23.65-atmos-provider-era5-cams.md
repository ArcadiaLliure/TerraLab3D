# Pas 23.65 — Skyglow físic — providers ERA5/CAMS i composició de camps

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Afegir reanàlisi/forecast real sense acoblar el kernel a Copernicus.

## Descripció funcional

Compon P/T/RH, aerosols i gasos amb procedència individual.

## Fonts a consultar

- [`docs/skyglow/README.md`](../../skyglow/README.md).
- [`02-arquitectura-integracio.md`](../../skyglow/02-arquitectura-integracio.md), [`08-validacio-cientifica.md`](../../skyglow/08-validacio-cientifica.md) i [`09-incertesa-proveniencia.md`](../../skyglow/09-incertesa-proveniencia.md).
- [`docs/normes-arquitectura.md`](../../normes-arquitectura.md).

## Objectiu

Afegir reanàlisi/forecast real sense acoblar el kernel a Copernicus.

## Dependències

**Depèn de:**
- [Pas 23.64](pas23.64-atmos-provider-standard.md)

**En depenen:**
- [Pas 23.68](pas23.68-uncertainty-registry.md)
- [Pas 23.72](pas23.72-ground-truth-validation.md)
- [Pas 23.73](pas23.73-clouds-b6.md)

## Codi existent a reutilitzar

- DEM/horitzó/geodèsia existents per visibilitat i coordenades.
- `domain/atmosphere`, `domain/light_pollution` i bridge actuals.
- Caches existents només com a infraestructura; no confondre-les amb `PropagationCacheEntry`.

## Flux tècnic

ERA5/CAMS adapters → camps validats → composició per variable → OpticalState → OpticalField.

## Errors, cancel·lació i recursos

- Discontinuïtats invaliden abans de qualsevol linealització.
- Resultats obsolets es descarten i l'últim resultat vàlid es conserva segons política.
- Risc: API drift, quota o producte canviant.
- Rollback: Desactivar provider i usar atmosfera estàndard.

## Tasques

- [ ] Implementar només l'abast d'aquest pas.
- [ ] Afegir unitats, versions i procedència.
- [ ] Afegir proves de discontinuïtats i casos límit.
- [ ] Executar benchmark/validació indicats.
- [ ] Actualitzar documentació viva segons evidència.

## Criteri de sortida

fixtures de resposta, camps parcials, fallback per camp i validTime/leadTime. Latència de provider i cache fora del render thread. La decisió queda traçable i reproduïble.

## Proves i evidències obligatòries

- [ ] fixtures de resposta, camps parcials, fallback per camp i validTime/leadTime.
- [ ] Latència de provider i cache fora del render thread.
- [ ] Evidència sota `docs/evidencies/pas23.65/`.
- [ ] `tools/validate_docs.py` i regressions afectades en verd.

## Fora d'abast

Observacions locals específiques.

## Instrucció per a Codex

ERA5/CAMS adapters → camps validats → composició per variable → OpticalState → OpticalField. No converteixis aproximacions de cache o renderer en física del kernel.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure el pas a `completat/`.