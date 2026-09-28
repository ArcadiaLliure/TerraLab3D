# Pas 23.50 — Skyglow físic — benchmark B0 i infraestructura de mesura

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Crear el harness determinista B0 sense física, amb 900 LOS, segmentació per tiles i Gauss–Kronrod 7/15.

## Descripció funcional

Mesura l'overhead estructural abans d'introduir física.

## Fonts a consultar

- [`docs/skyglow/README.md`](../../skyglow/README.md) i documents especialitzats del dossier.
- [`docs/normes-arquitectura.md`](../../normes-arquitectura.md) i [`docs/inventari-funcional.md`](../../inventari-funcional.md).
- Fonts primàries de [`04-justificacio-cientifica.md`](../../skyglow/04-justificacio-cientifica.md) quan el pas toca física o dades.

## Objectiu

Crear el harness determinista B0 sense física, amb 900 LOS, segmentació per tiles i Gauss–Kronrod 7/15.

## Dependències

**Depèn de:**
- Cap pas skyglow anterior. Prerequisits històrics: Pas 7, Pas 22.5 i Pas 23.

**En depenen:**
- [Pas 23.51](pas23.51-kernel-geometric.md)

## Codi existent a reutilitzar

- `backend/src/terralab3d/domain/light_pollution/` com a namespace de domini existent, sense donar-ne per implementada la nova física.
- `backend/src/terralab3d/domain/atmosphere/`, `domain/horizon/`, `domain/terrain/` i adaptador DEM quan pertoqui.
- `frontend/src/bridge/`, `frontend/src/contracts/`, `AtmosphereRenderer.ts` i `skyShader.ts` només quan el pas arriba al frontend.

## Flux tècnic

fixtures sintètiques → 900 LOS → segmentació de tiles → GK 7/15 amb integrand trivial → mètriques JSON/CSV.

## Errors, cancel·lació i recursos

- Resultats obsolets es descarten per revisió; cap càlcul llarg bloqueja el render thread.
- Fallbacks i dades absents es declaren amb procedència; no s'inventen valors.
- Risc principal: Mesurar el harness en lloc del camí futur.
- Rollback: Retirar només el paquet de benchmark nou.

## Tasques

- [ ] Implementar només l'abast d'aquest pas amb contractes i unitats explícites.
- [ ] Afegir instrumentació i procedència necessàries.
- [ ] Integrar cancel·lació/revisions obsoletes quan hi hagi treball asíncron.
- [ ] Executar proves i benchmark indicats.
- [ ] Actualitzar inventari, README i evidències només segons estat real.

## Criteri de sortida

B0: 5 warm-up + 30 repeticions; p50/p95/p99, nodes, segments i subdivisions. determinisme de seed, recompte de LOS, schema de resultats i absència de NaN. El resultat queda reproduïble i no anticipa capacitats posteriors.

## Proves i evidències obligatòries

- [ ] determinisme de seed, recompte de LOS, schema de resultats i absència de NaN.
- [ ] B0: 5 warm-up + 30 repeticions; p50/p95/p99, nodes, segments i subdivisions.
- [ ] Guardar JSON/CSV/plots o golden data sota `docs/evidencies/pas23.50/` quan s'executi.
- [ ] Executar `tools/validate_docs.py` i regressions afectades abans de completar.

## Fora d'abast

Cap canvi visual, VIIRS real, aerosol o renderer.

## Instrucció per a Codex

fixtures sintètiques → 900 LOS → segmentació de tiles → GK 7/15 amb integrand trivial → mètriques JSON/CSV. No redissenyar decisions congelades del dossier; si una hipòtesi de benchmark falla, registrar l'evidència i proposar un ADR de substitució.

## Treball pendent

- [ ] Completar totes les tasques, proves i evidències abans de moure aquest document a `completat/`.