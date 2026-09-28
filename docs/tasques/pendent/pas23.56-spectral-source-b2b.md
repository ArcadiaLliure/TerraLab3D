# Pas 23.56 — Skyglow físic — SpectralSourceModel, bases SPD i benchmark B2b

> **Estat:** Pendent
> **Dependències:** Pas 23.55

## Fonts a consultar

- `docs/skyglow/README.md` i documents especialitzats del dossier.
- `docs/normes-arquitectura.md`, `docs/inventari-funcional.md` i `AGENTS.md`.
- Fonts científiques exactes citades a `docs/skyglow/04-justificacio-cientifica.md`.

## Objectiu

Implementar base espectral normalitzada, priors i ensemble sense inferir SPD únic.

## Descripció funcional

Separa escala DNB de composició espectral.

## Abast

Bases candidates LED/HPS/LPS/halogenur, `A_j`, `c_jf`, B2b.

## Fora d'abast

Biblioteca definitiva i calibratge regional.

## Fitxers previsibles

SpectralBasisLibrary, source model, tests.

## Contractes

`SpectralBasis`, `SpectrumHint`, `SpectralSourceEstimate`.

## Implementació

Normalitzar `Φ`, pesos sumen 1, calcular `A_j` i `L_j,k,f` una sola vegada.

## Proves i comprovacions

Conservació d'energia, prior erroni dins DNB canvia escala, ensemble lineal.

## Benchmark / rendiment

B2b bases 1/2/3/5.

## Criteris d'acceptació

- [ ] No hi ha doble comptatge d'`A` o `c`.
- [ ] No marcar cap capacitat com a implementada només perquè existeixi el contracte o el document.
- [ ] Errors, cancel·lació, revisions obsoletes i recursos queden tractats segons `docs/normes-arquitectura.md`.

## Evidències

golden spectra i plot cost. Les evidències noves s'han de desar sota `docs/evidencies/pas23.56/` o la convenció equivalent validada pel repositori, sense esborrar evidència històrica.

## Riscos

SPD sense llicència.

## Rollback

Base sintètica mínima documentada.

## Impacte en inventari funcional

Mentre el pas sigui pendent, l'inventari només pot descriure'l com a planificat. En tancar-lo, classificar el resultat com `esquelet`, `parcial` o `observable` segons proves i ruta executable.

## Impacte en MANUAL / README / punt de represa

No actualitzar `docs/MANUAL.md` com si el comportament fos d'usuari fins que existeixi. En completar el pas: actualitzar `docs/README.md`, evidències i inventari; avançar el punt de represa al següent pas executable de la seqüència skyglow o al pas global que correspongui.

## Punt de represa

Si el pas queda incomplet, documentar l'última prova verda, fitxers tocats, evidència generada, bloqueig concret i primera acció següent.