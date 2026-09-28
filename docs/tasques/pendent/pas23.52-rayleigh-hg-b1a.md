# Pas 23.52 — Skyglow físic — Rayleigh, aerosol HG fallback i benchmark B1a

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Afegir single-scattering mínim monocromàtic amb Rayleigh i HG fallback.

## Descripció funcional

Primera física source→P→observer.

## Fonts a consultar

- [`docs/skyglow/README.md`](../../skyglow/README.md) i documents especialitzats del dossier.
- [`docs/normes-arquitectura.md`](../../normes-arquitectura.md) i [`docs/inventari-funcional.md`](../../inventari-funcional.md).
- Fonts primàries de [`04-justificacio-cientifica.md`](../../skyglow/04-justificacio-cientifica.md) quan el pas toca física o dades.

## Objectiu

Afegir single-scattering mínim monocromàtic amb Rayleigh i HG fallback.

## Dependències

**Depèn de:**
- [Pas 23.51](pas23.51-kernel-geometric.md)

**En depenen:**
- [Pas 23.53](pas23.53-forward-ad-b1b.md)
- [Pas 23.54](pas23.54-spectral-bandset-b2a.md)
- [Pas 23.61](pas23.61-phase-aerosol-library.md)

## Codi existent a reutilitzar

- `backend/src/terralab3d/domain/light_pollution/` com a namespace de domini existent, sense donar-ne per implementada la nova física.
- `backend/src/terralab3d/domain/atmosphere/`, `domain/horizon/`, `domain/terrain/` i adaptador DEM quan pertoqui.
- `frontend/src/bridge/`, `frontend/src/contracts/`, `AtmosphereRenderer.ts` i `skyShader.ts` només quan el pas arriba al frontend.

## Flux tècnic

calcular `E`, `Γ`, `dB` i integral LOS amb `T=exp(-τ)` i sense segon `1/r_PO²`.

## Errors, cancel·lació i recursos

- Resultats obsolets es descarten per revisió; cap càlcul llarg bloqueja el render thread.
- Fallbacks i dades absents es declaren amb procedència; no s'inventen valors.
- Risc principal: Confondre intensitat, irradiància i radiància.
- Rollback: Feature flag del kernel físic.

## Tasques

- [ ] Implementar només l'abast d'aquest pas amb contractes i unitats explícites.
- [ ] Afegir instrumentació i procedència necessàries.
- [ ] Integrar cancel·lació/revisions obsoletes quan hi hagi treball asíncron.
- [ ] Executar proves i benchmark indicats.
- [ ] Actualitzar inventari, README i evidències només segons estat real.

## Criteri de sortida

B1a: 1 banda, 1 base, AD OFF. normalització 4π, positivitat, linealitat i transmissió. El resultat queda reproduïble i no anticipa capacitats posteriors.

## Proves i evidències obligatòries

- [ ] normalització 4π, positivitat, linealitat i transmissió.
- [ ] B1a: 1 banda, 1 base, AD OFF.
- [ ] Guardar JSON/CSV/plots o golden data sota `docs/evidencies/pas23.52/` quan s'executi.
- [ ] Executar `tools/validate_docs.py` i regressions afectades abans de completar.

## Fora d'abast

Legendre, gasos, núvols i espectre real.

## Instrucció per a Codex

calcular `E`, `Γ`, `dB` i integral LOS amb `T=exp(-τ)` i sense segon `1/r_PO²`. No redissenyar decisions congelades del dossier; si una hipòtesi de benchmark falla, registrar l'evidència i proposar un ADR de substitució.

## Treball pendent

- [ ] Completar totes les tasques, proves i evidències abans de moure aquest document a `completat/`.