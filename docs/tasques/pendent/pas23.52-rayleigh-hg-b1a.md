# Pas 23.52 — Skyglow físic — Rayleigh, aerosol HG fallback i benchmark B1a

> **Estat:** Pendent
> **Dependències:** Pas 23.51

## Fonts a consultar

- `docs/skyglow/README.md` i documents especialitzats del dossier.
- `docs/normes-arquitectura.md`, `docs/inventari-funcional.md` i `AGENTS.md`.
- Fonts científiques exactes citades a `docs/skyglow/04-justificacio-cientifica.md`.

## Objectiu

Afegir single-scattering mínim monocromàtic amb Rayleigh normalitzat i HG fallback.

## Descripció funcional

Primera física completa source→P→observer amb extinció i scattering.

## Abast

1 banda, 1 base, AD OFF, atmosfera sintètica.

## Fora d'abast

Legendre, gasos, clouds, espectre real.

## Fitxers previsibles

càlculs òptics, fase Rayleigh/HG, tests i benchmark.

## Contractes

`PhaseFunction`, `OpticalTileBand` mínim.

## Implementació

Implementar `E`, `Γ`, `dB` i integral LOS sense segon `1/r_PO²`.

## Proves i comprovacions

Normalització 4π, positivitat, linealitat, transmissió `exp(-τ)`.

## Benchmark / rendiment

B1a exactament segons dossier.

## Criteris d'acceptació

- [ ] Resultat físic estable i error contra reference fixture dins tolerància documentada.
- [ ] No marcar cap capacitat com a implementada només perquè existeixi el contracte o el document.
- [ ] Errors, cancel·lació, revisions obsoletes i recursos queden tractats segons `docs/normes-arquitectura.md`.

## Evidències

B1a raw + tests de fórmula. Les evidències noves s'han de desar sota `docs/evidencies/pas23.52/` o la convenció equivalent validada pel repositori, sense esborrar evidència històrica.

## Riscos

Confondre intensitat/irradiància/radiància.

## Rollback

Feature flag del kernel físic.

## Impacte en inventari funcional

Mentre el pas sigui pendent, l'inventari només pot descriure'l com a planificat. En tancar-lo, classificar el resultat com `esquelet`, `parcial` o `observable` segons proves i ruta executable.

## Impacte en MANUAL / README / punt de represa

No actualitzar `docs/MANUAL.md` com si el comportament fos d'usuari fins que existeixi. En completar el pas: actualitzar `docs/README.md`, evidències i inventari; avançar el punt de represa al següent pas executable de la seqüència skyglow o al pas global que correspongui.

## Punt de represa

Si el pas queda incomplet, documentar l'última prova verda, fitxers tocats, evidència generada, bloqueig concret i primera acció següent.