# Pas 23.63 — Skyglow físic — GasAbsorptionModel i benchmark B4

> **Estat:** Pendent
> **Dependències:** Pas 23.54 i Pas 23.60

## Fonts a consultar

- `docs/skyglow/README.md` i documents especialitzats del dossier.
- `docs/normes-arquitectura.md`, `docs/inventari-funcional.md` i `AGENTS.md`.
- Fonts científiques exactes citades a `docs/skyglow/04-justificacio-cientifica.md`.

## Objectiu

Afegir absorció O3/H2O/O2 via LUT efectiva preservant transmitància.

## Descripció funcional

Evita `β_abs=0` i `exp(-mean τ)`.

## Abast

Generador offline/referència, LUT runtime per banda/base.

## Fora d'abast

Line-by-line runtime.

## Fitxers previsibles

gas model, LUT metadata, tests.

## Contractes

`GasState`, `GasAbsorptionModelRef`.

## Implementació

`T_eff` ponderat per base espectral; eixos T/p/columnes documentats.

## Proves i comprovacions

Jensen sanity, comparació espectral fina, interpolació LUT.

## Benchmark / rendiment

B4 cost incremental.

## Criteris d'acceptació

- [ ] Error LUT i cost reportats.
- [ ] No marcar cap capacitat com a implementada només perquè existeixi el contracte o el document.
- [ ] Errors, cancel·lació, revisions obsoletes i recursos queden tractats segons `docs/normes-arquitectura.md`.

## Evidències

manifest HITRAN/LOWTRAN source + checksum derivat. Les evidències noves s'han de desar sota `docs/evidencies/pas23.63/` o la convenció equivalent validada pel repositori, sense esborrar evidència històrica.

## Riscos

Llicència derivats.

## Rollback

LUT pròpia mínima basada en font permesa.

## Impacte en inventari funcional

Mentre el pas sigui pendent, l'inventari només pot descriure'l com a planificat. En tancar-lo, classificar el resultat com `esquelet`, `parcial` o `observable` segons proves i ruta executable.

## Impacte en MANUAL / README / punt de represa

No actualitzar `docs/MANUAL.md` com si el comportament fos d'usuari fins que existeixi. En completar el pas: actualitzar `docs/README.md`, evidències i inventari; avançar el punt de represa al següent pas executable de la seqüència skyglow o al pas global que correspongui.

## Punt de represa

Si el pas queda incomplet, documentar l'última prova verda, fitxers tocats, evidència generada, bloqueig concret i primera acció següent.