# Pas 23.55 — Skyglow físic — RSR real NOAA-20/J1

> **Estat:** Pendent
> **Dependències:** Pas 23.54

## Fonts a consultar

- `docs/skyglow/README.md` i documents especialitzats del dossier.
- `docs/normes-arquitectura.md`, `docs/inventari-funcional.md` i `AGENTS.md`.
- Fonts científiques exactes citades a `docs/skyglow/04-justificacio-cientifica.md`.

## Objectiu

Incorporar repositori/loader de RSR amb provenance i checksum sense empaquetar el ZIP si la redistribució no és verificada.

## Descripció funcional

Elimina aproximacions centre/FWHM/rectangle.

## Abast

NOAA-20/J1 DNB band-averaged; fixture mínima legal.

## Fora d'abast

Detector-specific raw SDR si no cal.

## Fitxers previsibles

recurs metadata, loader, tests, docs llicència.

## Contractes

`ViirsSpectralResponse`.

## Implementació

Validar λ ordenada, RSR no negativa i integració normalitzada segons convenció documentada.

## Proves i comprovacions

Paràmetres de control 694,8/499,1/890,5/391,4 nm com sanity checks, no com substitut de corba.

## Benchmark / rendiment

Cost de normalització offline, no runtime LOS.

## Criteris d'acceptació

- [ ] Cap normalització DNB usa rectangle.
- [ ] No marcar cap capacitat com a implementada només perquè existeixi el contracte o el document.
- [ ] Errors, cancel·lació, revisions obsoletes i recursos queden tractats segons `docs/normes-arquitectura.md`.

## Evidències

source URL, release, sha256, test integral. Les evidències noves s'han de desar sota `docs/evidencies/pas23.55/` o la convenció equivalent validada pel repositori, sense esborrar evidència històrica.

## Riscos

Drets de redistribució.

## Rollback

Descàrrega externa obligatòria.

## Impacte en inventari funcional

Mentre el pas sigui pendent, l'inventari només pot descriure'l com a planificat. En tancar-lo, classificar el resultat com `esquelet`, `parcial` o `observable` segons proves i ruta executable.

## Impacte en MANUAL / README / punt de represa

No actualitzar `docs/MANUAL.md` com si el comportament fos d'usuari fins que existeixi. En completar el pas: actualitzar `docs/README.md`, evidències i inventari; avançar el punt de represa al següent pas executable de la seqüència skyglow o al pas global que correspongui.

## Punt de represa

Si el pas queda incomplet, documentar l'última prova verda, fitxers tocats, evidència generada, bloqueig concret i primera acció següent.