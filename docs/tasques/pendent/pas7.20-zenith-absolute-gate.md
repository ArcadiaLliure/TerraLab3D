# Pas 7.20 — Skyglow físic — gate zenital radiomètric absolut

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Validar la cadena física absoluta a 90° amb el mateix PropagationKernel abans de promoure cúpules.

## Descripció funcional

Converteix el zenit en un gate científic reproduïble: mateixa font, atmosfera, terreny i kernel que la resta de direccions, però una sola LOS a 90° per auditar unitats, convergència i cost.

## Fonts a consultar

- [`docs/skyglow/README.md`](../../skyglow/README.md).
- [`01-especificacio-algorismes.md`](../../skyglow/01-especificacio-algorismes.md), [`06-contractes-dades.md`](../../skyglow/06-contractes-dades.md), [`07-benchmark-b0-b7.md`](../../skyglow/07-benchmark-b0-b7.md) i [`08-validacio-cientifica.md`](../../skyglow/08-validacio-cientifica.md).
- [ADR-017](../../skyglow/adrs/ADR-017-zenith-photometric-projections.md).

## Objectiu

Obtenir `PropagationResult` zenital sense factor de calibratge opac i demostrar convergència del **transport donat el mateix `SourceModel`** contra un oracle independent. La validació empírica de l'emissió és separada.

## Dependències

**Depèn de:**
- [Pas 7.8](pas7.8-vnp46-adapter.md)
- [Pas 7.17](pas7.17-terrain-curvature.md)
- [Pas 7.19](pas7.19-uncertainty-registry.md)

**En depenen:**
- [Pas 7.21](pas7.21-dome-profile-pchip.md)
- [Pas 7.22](pas7.22-photometric-projections.md)

## Codi existent a reutilitzar

- `PropagationKernel`, `SourceModel`, `OpticalField`, terreny/geodèsia i contractes dels passos previs.
- Oracle offline independent; no crear un `ZenithSolver` paral·lel. **S1 continua bloquejant el tancament del pas:** opció A `SG-REF`; opció B dependència creuada amb 7.65.
- Infraestructura de benchmark/cancel·lació/cache, sense obligar encara el renderer.

## Flux tècnic

fixture/VNP46 → model de mesura DNB → mateix `SourceModel` a runtime i oracle → OpticalField + DEM → `DirectionSet={90°}` → PropagationKernel/oracle → radiància per banda → informe error/cost.

## Errors, cancel·lació i recursos

- Qualsevol ruptura d'unitats, NaN/Inf, manca de convergència o necessitat de `calibrationFactor` opac fa fallar el gate.
- Resultats obsolets no es publiquen; cold/warm es mesuren separadament.
- No es converteix encara a SQM/Bortle dins el kernel.

## Tasques

- [ ] Afegir fixture zenital sintètica i almenys una fixture real reproduïble amb provenance.
- [ ] Verificar cadena d'unitats i resultats físics per banda.
- [ ] Comparar toleràncies del runtime candidate contra reference solver.
- [ ] Mesurar cold/warm, nodes, segments, memòria i dependències tocades.
- [ ] Registrar incertesa numèrica separada de la de model/font/atmosfera.

## Criteri de sortida

90° usa la mateixa ruta que qualsevol direcció, convergeix, conserva la cadena d'unitats definida, no usa calibratge arbitrari i compleix el pressupost d'error preregistrat contra l'oracle escollit a S1. Un PASS valida transport, no `SourceModel`. El pas no es pot completar mentre S1 no estigui resolta.

## Proves i evidències obligatòries

- [ ] golden runtime vs reference a 90°.
- [ ] unitats, positivitat, linealitat, extinció i oclusió.
- [ ] estrènyer tolerància redueix/estabilitza l'error.
- [ ] cold/warm benchmark amb p50/p95 i peak RSS.
- [ ] Evidència sota `docs/evidencies/pas7.20/`.

## Fora d'abast

SQM/TESS/Bortle, composició amb cel natural/Lluna i renderer.

## Instrucció per a Codex

Implementa el gate com una configuració del mateix `PropagationKernel`; no creïs un solver zenital separat ni introdueixis factors d'escala. No presentis el PASS com a validació de l'emissió VNP46→font i no tanquis S1 implícitament.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure aquest document a `completat/`.
