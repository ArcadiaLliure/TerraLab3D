# Pas 23.65 — Skyglow físic — providers ERA5/CAMS i composició de camps

> **Estat:** Pendent
> **Dependències:** Pas 23.64

## Fonts a consultar

- `docs/skyglow/README.md` i documents especialitzats del dossier.
- `docs/normes-arquitectura.md`, `docs/inventari-funcional.md` i `AGENTS.md`.
- Fonts científiques exactes citades a `docs/skyglow/04-justificacio-cientifica.md`.

## Objectiu

Afegir reanàlisi/forecast real sense acoblar el kernel a Copernicus.

## Descripció funcional

Compon P/T/RH i aerosols/gasos amb procedència individual.

## Abast

ERA5 i CAMS, cache de dades, validTime/leadTime.

## Fora d'abast

Observacions locals específiques.

## Fitxers previsibles

infra adapters atmosphere/weather, cache.

## Contractes

mateix provider port.

## Implementació

Mapping explícit variable→òptica; versions i llicència.

## Proves i comprovacions

fixtures de resposta, camps parcialment absents, fallback per camp.

## Benchmark / rendiment

latència de provider fora del render thread.

## Criteris d'acceptació

- [ ] Kernel rep OpticalState idèntic independentment de font.
- [ ] No marcar cap capacitat com a implementada només perquè existeixi el contracte o el document.
- [ ] Errors, cancel·lació, revisions obsoletes i recursos queden tractats segons `docs/normes-arquitectura.md`.

## Evidències

manifests i exemples de composició. Les evidències noves s'han de desar sota `docs/evidencies/pas23.65/` o la convenció equivalent validada pel repositori, sense esborrar evidència històrica.

## Riscos

API drift/quota.

## Rollback

ERA5/CAMS desactivables; standard fallback.

## Impacte en inventari funcional

Mentre el pas sigui pendent, l'inventari només pot descriure'l com a planificat. En tancar-lo, classificar el resultat com `esquelet`, `parcial` o `observable` segons proves i ruta executable.

## Impacte en MANUAL / README / punt de represa

No actualitzar `docs/MANUAL.md` com si el comportament fos d'usuari fins que existeixi. En completar el pas: actualitzar `docs/README.md`, evidències i inventari; avançar el punt de represa al següent pas executable de la seqüència skyglow o al pas global que correspongui.

## Punt de represa

Si el pas queda incomplet, documentar l'última prova verda, fitxers tocats, evidència generada, bloqueig concret i primera acció següent.