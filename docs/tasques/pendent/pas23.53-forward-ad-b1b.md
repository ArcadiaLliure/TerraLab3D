# Pas 23.53 — Skyglow físic — forward AD geomètric i benchmark B1b

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Propagar `(B,dBx,dBy,dBz)` en la mateixa quadratura dins branques diferenciables.

## Descripció funcional

Mesura sensibilitats geomètriques per al cache.

## Fonts a consultar

- [`docs/skyglow/README.md`](../../skyglow/README.md) i documents especialitzats del dossier.
- [`docs/normes-arquitectura.md`](../../normes-arquitectura.md) i [`docs/inventari-funcional.md`](../../inventari-funcional.md).
- Fonts primàries de [`04-justificacio-cientifica.md`](../../skyglow/04-justificacio-cientifica.md) quan el pas toca física o dades.

## Objectiu

Propagar `(B,dBx,dBy,dBz)` en la mateixa quadratura dins branques diferenciables.

## Dependències

**Depèn de:**
- [Pas 23.52](pas23.52-rayleigh-hg-b1a.md)

**En depenen:**
- [Pas 23.67](pas23.67-cache-error-based.md)

## Codi existent a reutilitzar

- `backend/src/terralab3d/domain/light_pollution/` com a namespace de domini existent, sense donar-ne per implementada la nova física.
- `backend/src/terralab3d/domain/atmosphere/`, `domain/horizon/`, `domain/terrain/` i adaptador DEM quan pertoqui.
- `frontend/src/bridge/`, `frontend/src/contracts/`, `AtmosphereRenderer.ts` i `skyShader.ts` només quan el pas arriba al frontend.

## Flux tècnic

forward-mode AD + terme de Leibniz; discontinuïtats invaliden i no es diferencien.

## Errors, cancel·lació i recursos

- Resultats obsolets es descarten per revisió; cap càlcul llarg bloqueja el render thread.
- Fallbacks i dades absents es declaren amb procedència; no s'inventen valors.
- Risc principal: Derivades incorrectes a `s_max`.
- Rollback: AD OFF sense canviar el kernel base.

## Tasques

- [ ] Implementar només l'abast d'aquest pas amb contractes i unitats explícites.
- [ ] Afegir instrumentació i procedència necessàries.
- [ ] Integrar cancel·lació/revisions obsoletes quan hi hagi treball asíncron.
- [ ] Executar proves i benchmark indicats.
- [ ] Actualitzar inventari, README i evidències només segons estat real.

## Criteri de sortida

B1b vs B1a i `AD_overhead`. comparació amb diferències finites offline en casos suaus. El resultat queda reproduïble i no anticipa capacitats posteriors.

## Proves i evidències obligatòries

- [ ] comparació amb diferències finites offline en casos suaus.
- [ ] B1b vs B1a i `AD_overhead`.
- [ ] Guardar JSON/CSV/plots o golden data sota `docs/evidencies/pas23.53/` quan s'executi.
- [ ] Executar `tools/validate_docs.py` i regressions afectades abans de completar.

## Fora d'abast

Diferenciar oclusió, quadtree o canvis topològics.

## Instrucció per a Codex

forward-mode AD + terme de Leibniz; discontinuïtats invaliden i no es diferencien. No redissenyar decisions congelades del dossier; si una hipòtesi de benchmark falla, registrar l'evidència i proposar un ADR de substitució.

## Treball pendent

- [ ] Completar totes les tasques, proves i evidències abans de moure aquest document a `completat/`.