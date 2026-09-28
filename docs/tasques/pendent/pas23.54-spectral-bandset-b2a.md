# Pas 23.54 — Skyglow físic — infraestructura espectral i benchmark B2a

> **Estat:** Pendent
> **Dependències:** Pas 23.52

## Fonts a consultar

- `docs/skyglow/README.md` i documents especialitzats del dossier.
- `docs/normes-arquitectura.md`, `docs/inventari-funcional.md` i `AGENTS.md`.
- Fonts científiques exactes citades a `docs/skyglow/04-justificacio-cientifica.md`.

## Objectiu

Introduir `SpectralBandSet`/`BandRadiance` sense fixar 8 bandes.

## Descripció funcional

Vectoritza la física en 1/2/4/8 bandes i mesura escalat.

## Abast

Band sets sintètics, Rayleigh espectral, B2a.

## Fora d'abast

RSR i priors SPD.

## Fitxers previsibles

models espectrals, càlculs vectoritzats, tests.

## Contractes

`SpectralBandSet`, `BandRadiance`.

## Implementació

Compartir geometria/tiles entre bandes.

## Proves i comprovacions

Mateix resultat per 1 banda equivalent; unitats i longitud de vectors.

## Benchmark / rendiment

B2a `t(Nbands)`.

## Criteris d'acceptació

- [ ] API independent del nombre de bandes i corba de cost disponible.
- [ ] No marcar cap capacitat com a implementada només perquè existeixi el contracte o el document.
- [ ] Errors, cancel·lació, revisions obsoletes i recursos queden tractats segons `docs/normes-arquitectura.md`.

## Evidències

CSV/plot B2a. Les evidències noves s'han de desar sota `docs/evidencies/pas23.54/` o la convenció equivalent validada pel repositori, sense esborrar evidència històrica.

## Riscos

Duplicar ray-march per banda.

## Rollback

Conservar 1 banda.

## Impacte en inventari funcional

Mentre el pas sigui pendent, l'inventari només pot descriure'l com a planificat. En tancar-lo, classificar el resultat com `esquelet`, `parcial` o `observable` segons proves i ruta executable.

## Impacte en MANUAL / README / punt de represa

No actualitzar `docs/MANUAL.md` com si el comportament fos d'usuari fins que existeixi. En completar el pas: actualitzar `docs/README.md`, evidències i inventari; avançar el punt de represa al següent pas executable de la seqüència skyglow o al pas global que correspongui.

## Punt de represa

Si el pas queda incomplet, documentar l'última prova verda, fitxers tocats, evidència generada, bloqueig concret i primera acció següent.