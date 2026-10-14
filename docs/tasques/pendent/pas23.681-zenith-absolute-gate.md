# Pas 23.681 — Skyglow físic — gate zenital radiomètric absolut

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Validar la cadena física absoluta a 90° amb el mateix PropagationKernel abans de promoure cúpules.

## Descripció funcional

Converteix el zenit en un gate científic reproduïble: mateixa font, atmosfera, terreny i kernel que la resta de direccions, però una sola LOS a 90° per auditar unitats, convergència i cost.

## Fonts a consultar

- [`docs/skyglow/README.md`](../../skyglow/README.md).
- [`01-especificacio-algorismes.md`](../../skyglow/01-especificacio-algorismes.md), [`06-contractes-dades.md`](../../skyglow/06-contractes-dades.md), [`07-benchmark-b0-b7.md`](../../skyglow/07-benchmark-b0-b7.md) i [`08-validacio-cientifica.md`](../../skyglow/08-validacio-cientifica.md).
- [ADR-017](../../skyglow/adrs/ADR-017-zenith-photometric-projections.md).

## Objectiu

Obtenir `PropagationResult` zenital en unitats radiomètriques físiques, sense factor de calibratge opac, i demostrar convergència contra el reference solver.

## Dependències

**Depèn de:**
- [Pas 23.57](pas23.57-viirs-adapter.md)
- [Pas 23.66](pas23.66-terrain-curvature.md)
- [Pas 23.68](pas23.68-uncertainty-registry.md)

**En depenen:**
- [Pas 23.69](pas23.69-dome-profile-pchip.md)
- [Pas 23.691](pas23.691-photometric-projections.md)

## Codi existent a reutilitzar

- `PropagationKernel`, `SourceModel`, `OpticalField`, terreny/geodèsia i contractes dels passos previs.
- Reference solver offline; no crear un `ZenithSolver` paral·lel.
- Infraestructura de benchmark/cancel·lació/cache, sense obligar encara el renderer.

## Flux tècnic

fixture/VIIRS → model de font → OpticalField + DEM → `DirectionSet={90°}` → PropagationKernel → radiància per banda → reference solver → informe error/cost.

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

90° usa la mateixa ruta que qualsevol direcció, convergeix, conserva unitats físiques, no usa calibratge arbitrari i compleix el pressupost provisional d'error contra la referència. El cost zenital queda caracteritzat abans de construir la compressió angular.

## Proves i evidències obligatòries

- [ ] golden runtime vs reference a 90°.
- [ ] unitats, positivitat, linealitat, extinció i oclusió.
- [ ] estrènyer tolerància redueix/estabilitza l'error.
- [ ] cold/warm benchmark amb p50/p95 i peak RSS.
- [ ] Evidència sota `docs/evidencies/pas23.681/`.

## Fora d'abast

SQM/TESS/Bortle, composició amb cel natural/Lluna i renderer.

## Instrucció per a Codex

Implementa el gate com una configuració del mateix `PropagationKernel`; no creïs un solver zenital separat ni introdueixis factors d'escala per forçar coincidència amb una magnitud observacional.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure aquest document a `completat/`.
