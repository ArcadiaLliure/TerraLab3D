# Pas 23.64 — Skyglow físic — AtmosphericOpticsProvider amb atmosfera estàndard

> **Estat:** Pendent
> **Dependències:** Pas 23.60, Pas 23.61 i Pas 23.63

## Fonts a consultar

- `docs/skyglow/README.md` i documents especialitzats del dossier.
- `docs/normes-arquitectura.md`, `docs/inventari-funcional.md` i `AGENTS.md`.
- Fonts científiques exactes citades a `docs/skyglow/04-justificacio-cientifica.md`.

## Objectiu

Implementar provider fallback complet amb procedència per camp.

## Descripció funcional

Permet executar el kernel sense xarxa ni reanàlisi.

## Abast

P/T/RH/gasos/aerosol fallback i perfil vertical versionat.

## Fora d'abast

ERA5/CAMS/live.

## Fitxers previsibles

provider domain port + standard adapter.

## Contractes

`AtmosphericOpticsProvider`, `OpticalParameter`.

## Implementació

Cap confidence→sigma inventat; camps absents explícits.

## Proves i comprovacions

Offline deterministic, altitude interpolation, provenance.

## Benchmark / rendiment

Resolve throughput i build OpticalField.

## Criteris d'acceptació

- [ ] Resultat físic pot declarar `STANDARD_ATMOSPHERE` de punta a punta.
- [ ] No marcar cap capacitat com a implementada només perquè existeixi el contracte o el document.
- [ ] Errors, cancel·lació, revisions obsoletes i recursos queden tractats segons `docs/normes-arquitectura.md`.

## Evidències

snapshot perfil i tests. Les evidències noves s'han de desar sota `docs/evidencies/pas23.64/` o la convenció equivalent validada pel repositori, sense esborrar evidència històrica.

## Riscos

Fallback confós amb observació.

## Rollback

Provider unavailable en lloc de dades falses.

## Impacte en inventari funcional

Mentre el pas sigui pendent, l'inventari només pot descriure'l com a planificat. En tancar-lo, classificar el resultat com `esquelet`, `parcial` o `observable` segons proves i ruta executable.

## Impacte en MANUAL / README / punt de represa

No actualitzar `docs/MANUAL.md` com si el comportament fos d'usuari fins que existeixi. En completar el pas: actualitzar `docs/README.md`, evidències i inventari; avançar el punt de represa al següent pas executable de la seqüència skyglow o al pas global que correspongui.

## Punt de represa

Si el pas queda incomplet, documentar l'última prova verda, fitxers tocats, evidència generada, bloqueig concret i primera acció següent.