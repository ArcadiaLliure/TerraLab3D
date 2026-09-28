# Pas 23.62 — Skyglow físic — benchmark B3 de complexitat de fase

> **Estat:** Pendent
> **Dependències:** Pas 23.61

## Fonts a consultar

- `docs/skyglow/README.md` i documents especialitzats del dossier.
- `docs/normes-arquitectura.md`, `docs/inventari-funcional.md` i `AGENTS.md`.
- Fonts científiques exactes citades a `docs/skyglow/04-justificacio-cientifica.md`.

## Objectiu

Mesurar HG i Legendre 4/8/12/20 contra referència.

## Descripció funcional

Converteix L en decisió basada en error↔cost.

## Abast

Escenaris forward scattering i atmosferes diverses.

## Fora d'abast

No fixa aerosol provider final.

## Fitxers previsibles

benchmark configs/results.

## Contractes

Sense nous contractes.

## Implementació

Mateixa geometria i nodes per totes variants.

## Proves i comprovacions

Reference phase independent.

## Benchmark / rendiment

B3 complet.

## Criteris d'acceptació

- [ ] Informe cost/error; cap ordre declarat guanyador sense SLO.
- [ ] No marcar cap capacitat com a implementada només perquè existeixi el contracte o el document.
- [ ] Errors, cancel·lació, revisions obsoletes i recursos queden tractats segons `docs/normes-arquitectura.md`.

## Evidències

CSV/plots i decisió candidata. Les evidències noves s'han de desar sota `docs/evidencies/pas23.62/` o la convenció equivalent validada pel repositori, sense esborrar evidència històrica.

## Riscos

Referència inadequada.

## Rollback

Mantenir L configurable.

## Impacte en inventari funcional

Mentre el pas sigui pendent, l'inventari només pot descriure'l com a planificat. En tancar-lo, classificar el resultat com `esquelet`, `parcial` o `observable` segons proves i ruta executable.

## Impacte en MANUAL / README / punt de represa

No actualitzar `docs/MANUAL.md` com si el comportament fos d'usuari fins que existeixi. En completar el pas: actualitzar `docs/README.md`, evidències i inventari; avançar el punt de represa al següent pas executable de la seqüència skyglow o al pas global que correspongui.

## Punt de represa

Si el pas queda incomplet, documentar l'última prova verda, fitxers tocats, evidència generada, bloqueig concret i primera acció següent.