# Pas 23.51 — Skyglow físic — esquelet geomètric del PropagationKernel

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Crear el kernel únic, geometria LOS i `s_max` sense scattering real.

## Descripció funcional

Estableix la frontera comuna per zenit i cúpules.

## Fonts a consultar

- [`docs/skyglow/README.md`](../../skyglow/README.md) i documents especialitzats del dossier.
- [`docs/normes-arquitectura.md`](../../normes-arquitectura.md) i [`docs/inventari-funcional.md`](../../inventari-funcional.md).
- Fonts primàries de [`04-justificacio-cientifica.md`](../../skyglow/04-justificacio-cientifica.md) quan el pas toca física o dades.

## Objectiu

Crear el kernel únic, geometria LOS i `s_max` sense scattering real.

## Dependències

**Depèn de:**
- [Pas 23.50](pas23.50-skyglow-b0.md)

**En depenen:**
- [Pas 23.52](pas23.52-rayleigh-hg-b1a.md)
- [Pas 23.66](pas23.66-terrain-curvature.md)
- [Pas 23.69](pas23.69-dome-profile-pchip.md)

## Codi existent a reutilitzar

- `backend/src/terralab3d/domain/light_pollution/` com a namespace de domini existent, sense donar-ne per implementada la nova física.
- `backend/src/terralab3d/domain/atmosphere/`, `domain/horizon/`, `domain/terrain/` i adaptador DEM quan pertoqui.
- `frontend/src/bridge/`, `frontend/src/contracts/`, `AtmosphereRenderer.ts` i `skyShader.ts` només quan el pas arriba al frontend.

## Flux tècnic

Observer+DirectionSet+Source fixture → LOS → segments → resultat; 90° usa exactament la mateixa ruta.

## Errors, cancel·lació i recursos

- Resultats obsolets es descarten per revisió; cap càlcul llarg bloqueja el render thread.
- Fallbacks i dades absents es declaren amb procedència; no s'inventen valors.
- Risc principal: Abstracció massa genèrica.
- Rollback: Conservar B0 i retirar l'esquelet no connectat.

## Tasques

- [ ] Implementar només l'abast d'aquest pas amb contractes i unitats explícites.
- [ ] Afegir instrumentació i procedència necessàries.
- [ ] Integrar cancel·lació/revisions obsoletes quan hi hagi treball asíncron.
- [ ] Executar proves i benchmark indicats.
- [ ] Actualitzar inventari, README i evidències només segons estat real.

## Criteri de sortida

Reexecutar B0 amb l'esquelet real. zenit com direcció ordinària, geometria esfèrica, unitats i cancel·lació. El resultat queda reproduïble i no anticipa capacitats posteriors.

## Proves i evidències obligatòries

- [ ] zenit com direcció ordinària, geometria esfèrica, unitats i cancel·lació.
- [ ] Reexecutar B0 amb l'esquelet real.
- [ ] Guardar JSON/CSV/plots o golden data sota `docs/evidencies/pas23.51/` quan s'executi.
- [ ] Executar `tools/validate_docs.py` i regressions afectades abans de completar.

## Fora d'abast

Espectre, aerosols, gasos, núvols i renderer.

## Instrucció per a Codex

Observer+DirectionSet+Source fixture → LOS → segments → resultat; 90° usa exactament la mateixa ruta. No redissenyar decisions congelades del dossier; si una hipòtesi de benchmark falla, registrar l'evidència i proposar un ADR de substitució.

## Treball pendent

- [ ] Completar totes les tasques, proves i evidències abans de moure aquest document a `completat/`.