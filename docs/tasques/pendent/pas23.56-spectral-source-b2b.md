# Pas 23.56 — Skyglow físic — SpectralSourceModel, bases SPD i benchmark B2b

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Implementar bases normalitzades, priors i ensemble sense inferir un SPD únic.

## Descripció funcional

Separa escala DNB i composició espectral.

## Fonts a consultar

- [`docs/skyglow/README.md`](../../skyglow/README.md).
- [`docs/normes-arquitectura.md`](../../normes-arquitectura.md) i [`docs/inventari-funcional.md`](../../inventari-funcional.md).
- [`04-justificacio-cientifica.md`](../../skyglow/04-justificacio-cientifica.md) i [`10-datasets-llicencies.md`](../../skyglow/10-datasets-llicencies.md).

## Objectiu

Implementar bases normalitzades, priors i ensemble sense inferir un SPD únic.

## Dependències

**Depèn de:**
- [Pas 23.55](pas23.55-viirs-rsr.md)

**En depenen:**
- [Pas 23.68](pas23.68-uncertainty-registry.md)

## Codi existent a reutilitzar

- `backend/src/terralab3d/domain/light_pollution/` i ports/adaptadors actuals.
- `backend/src/terralab3d/infrastructure/adapters/dem/adapter.py` quan hi hagi geometria/ràster.
- Contractes/bridge existents; no crear un segon canal paral·lel.

## Flux tècnic

`Φ_f` + pesos `c_jf` + RSR → `A_j` → `L_j,k,f`; vectorització per bases.

## Errors, cancel·lació i recursos

- Dades absents/corruptes tenen estat explícit i procedència.
- Resultats tardans es descarten; recursos grans no es dupliquen pel bridge.
- Risc: SPD sense llicència o prior massa rígid.
- Rollback: Base sintètica mínima amb confiança baixa.

## Tasques

- [ ] Implementar contractes i transformacions d'aquest pas.
- [ ] Afegir unitats, versions i procedència.
- [ ] Afegir proves numèriques/fixtures.
- [ ] Executar benchmark indicat.
- [ ] Actualitzar evidències i inventari segons estat real.

## Criteri de sortida

conservació d'energia, suma de pesos i absència de doble comptatge. B2b amb 1/2/3/5 bases. Cap capacitat posterior queda marcada com a implementada.

## Proves i evidències obligatòries

- [ ] conservació d'energia, suma de pesos i absència de doble comptatge.
- [ ] B2b amb 1/2/3/5 bases.
- [ ] Evidència reproduïble sota `docs/evidencies/pas23.56/`.
- [ ] `tools/validate_docs.py` i regressions afectades en verd.

## Fora d'abast

Biblioteca SPD definitiva o calibratge regional.

## Instrucció per a Codex

`Φ_f` + pesos `c_jf` + RSR → `A_j` → `L_j,k,f`; vectorització per bases. Mantén les decisions congelades del dossier i registra qualsevol desviació amb evidència.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure el pas a `completat/`.