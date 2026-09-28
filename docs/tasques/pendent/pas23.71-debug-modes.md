# Pas 23.71 — Skyglow físic — modes diagnòstics i observabilitat

> **Estat:** Pendent
> **Dependències:** Pas 23.70

## Fonts a consultar

- `docs/skyglow/README.md` i documents especialitzats del dossier.
- `docs/normes-arquitectura.md`, `docs/inventari-funcional.md` i `AGENTS.md`.
- Fonts científiques exactes citades a `docs/skyglow/04-justificacio-cientifica.md`.

## Objectiu

Connectar els modes de depuració definits al dossier.

## Descripció funcional

Fa inspeccionables fonts, LOS, tiles, fase, cache i incertesa.

## Abast

UI/dev toggles, fals color i telemetria.

## Fora d'abast

Cap canvi de física.

## Fitxers previsibles

frontend debug UI + backend debug payloads.

## Contractes

Debug DTOs versionats.

## Implementació

No enviar dades massives si no s'activa el mode.

## Proves i comprovacions

Toggle cleanup, no leak, revisions obsoletes.

## Benchmark / rendiment

Overhead debug OFF pràcticament nul; debug ON mesurat.

## Criteris d'acceptació

- [ ] Cada component físic té una vista diagnòstica útil.
- [ ] No marcar cap capacitat com a implementada només perquè existeixi el contracte o el document.
- [ ] Errors, cancel·lació, revisions obsoletes i recursos queden tractats segons `docs/normes-arquitectura.md`.

## Evidències

captures i perf logs. Les evidències noves s'han de desar sota `docs/evidencies/pas23.71/` o la convenció equivalent validada pel repositori, sense esborrar evidència històrica.

## Riscos

Debug altera timing.

## Rollback

Toggles desactivats.

## Impacte en inventari funcional

Mentre el pas sigui pendent, l'inventari només pot descriure'l com a planificat. En tancar-lo, classificar el resultat com `esquelet`, `parcial` o `observable` segons proves i ruta executable.

## Impacte en MANUAL / README / punt de represa

No actualitzar `docs/MANUAL.md` com si el comportament fos d'usuari fins que existeixi. En completar el pas: actualitzar `docs/README.md`, evidències i inventari; avançar el punt de represa al següent pas executable.

## Punt de represa

Si el pas queda incomplet, documentar l'última prova verda, fitxers tocats, evidència generada, bloqueig concret i primera acció següent.