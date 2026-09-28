# Pas 23.61 — Skyglow físic — PhaseFunction unificada i AerosolOpticsLibrary mínima

> **Estat:** Pendent
> **Dependències:** Pas 23.52 i Pas 23.60

## Fonts a consultar

- `docs/skyglow/README.md` i documents especialitzats del dossier.
- `docs/normes-arquitectura.md`, `docs/inventari-funcional.md` i `AGENTS.md`.
- Fonts científiques exactes citades a `docs/skyglow/04-justificacio-cientifica.md`.

## Objectiu

Substituir branques de fase per una representació comuna i preparar aerosol data project.

## Descripció funcional

HG continua com fallback però entra al kernel a través del mateix contracte.

## Abast

Legendre representation, provenance, HG→Legendre, fixtures Mie/tabulades si legals.

## Fora d'abast

Selecció definitiva d'aerosols.

## Fitxers previsibles

phase functions, aerosol library metadata.

## Contractes

`PhaseFunction`.

## Implementació

Normalització 4π, `a0=1`, `a1=g`; recurrència estable.

## Proves i comprovacions

HG directe vs expansió alta, isotropic case, positivity diagnostics.

## Benchmark / rendiment

Microbenchmark fase.

## Criteris d'acceptació

- [ ] Kernel no té switch Mie/HG per font.
- [ ] No marcar cap capacitat com a implementada només perquè existeixi el contracte o el document.
- [ ] Errors, cancel·lació, revisions obsoletes i recursos queden tractats segons `docs/normes-arquitectura.md`.

## Evidències

coefficients/plots. Les evidències noves s'han de desar sota `docs/evidencies/pas23.61/` o la convenció equivalent validada pel repositori, sense esborrar evidència històrica.

## Riscos

Truncació pot crear lobes negatius.

## Rollback

HG directe només com implementació del contracte.

## Impacte en inventari funcional

Mentre el pas sigui pendent, l'inventari només pot descriure'l com a planificat. En tancar-lo, classificar el resultat com `esquelet`, `parcial` o `observable` segons proves i ruta executable.

## Impacte en MANUAL / README / punt de represa

No actualitzar `docs/MANUAL.md` com si el comportament fos d'usuari fins que existeixi. En completar el pas: actualitzar `docs/README.md`, evidències i inventari; avançar el punt de represa al següent pas executable de la seqüència skyglow o al pas global que correspongui.

## Punt de represa

Si el pas queda incomplet, documentar l'última prova verda, fitxers tocats, evidència generada, bloqueig concret i primera acció següent.