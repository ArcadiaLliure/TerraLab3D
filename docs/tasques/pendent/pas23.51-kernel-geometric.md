# Pas 23.51 — Skyglow físic — esquelet geomètric del PropagationKernel

> **Estat:** Pendent
> **Dependències:** Pas 23.50

## Fonts a consultar

- `docs/skyglow/README.md` i documents especialitzats del dossier.
- `docs/normes-arquitectura.md`, `docs/inventari-funcional.md` i `AGENTS.md`.
- Fonts científiques exactes citades a `docs/skyglow/04-justificacio-cientifica.md`.

## Objectiu

Crear el kernel únic, geometria LOS, `s_max` i contractes de radiància sense scattering real.

## Descripció funcional

Estableix la frontera física comuna per zenit i cúpules.

## Abast

Observer, DirectionSet, source point fixture, segments, curvatura bàsica i resultat.

## Fora d'abast

Espectre, aerosols, gasos, clouds, renderer.

## Fitxers previsibles

`domain/light_pollution` i/o nou subpaquet coherent amb arquitectura; tests.

## Contractes

`PropagationRequest`, `PropagationResult`, `DirectionSample`.

## Implementació

Una sola ruta d'avaluació per qualsevol direcció; 90° no té codi especial.

## Proves i comprovacions

Zenit com direcció ordinària; unitats; geometria esfèrica; cancel·lació.

## Benchmark / rendiment

Reexecutar B0 amb kernel real i comparar overhead.

## Criteris d'acceptació

- [ ] No existeix cap solver zenital separat.
- [ ] No marcar cap capacitat com a implementada només perquè existeixi el contracte o el document.
- [ ] Errors, cancel·lació, revisions obsoletes i recursos queden tractats segons `docs/normes-arquitectura.md`.

## Evidències

Tests, perfil de cost i diagrama de crides. Les evidències noves s'han de desar sota `docs/evidencies/pas23.51/` o la convenció equivalent validada pel repositori, sense esborrar evidència històrica.

## Riscos

Abstracció massa genèrica.

## Rollback

Conservar harness B0 i retirar només l'esquelet no connectat.

## Impacte en inventari funcional

Mentre el pas sigui pendent, l'inventari només pot descriure'l com a planificat. En tancar-lo, classificar el resultat com `esquelet`, `parcial` o `observable` segons proves i ruta executable.

## Impacte en MANUAL / README / punt de represa

No actualitzar `docs/MANUAL.md` com si el comportament fos d'usuari fins que existeixi. En completar el pas: actualitzar `docs/README.md`, evidències i inventari; avançar el punt de represa al següent pas executable de la seqüència skyglow o al pas global que correspongui.

## Punt de represa

Si el pas queda incomplet, documentar l'última prova verda, fitxers tocats, evidència generada, bloqueig concret i primera acció següent.