# Pas 7.4 — Skyglow físic — Oracle espectral fi i homologació del SpectralBandSet v1

> **Estat:** pendent. **Execució:** seqüencial. **Pla canònic:** [19-pla-executable-codex.md](../../skyglow/19-pla-executable-codex.md).

## Finalitat

Tancar `V3` abans que el nombre de bandes entri al kernel de producció.

## Dependències

7.3

## Referències obligatòries

- [01-especificacio-algorismes.md](../../skyglow/01-especificacio-algorismes.md)
- [07-benchmark-b0-b7.md](../../skyglow/07-benchmark-b0-b7.md)
- [12-glossari-unitats.md](../../skyglow/12-glossari-unitats.md)

## Tasques

- [ ] Construir una integració espectral fina independent per fixtures i projeccions de sensor.
- [ ] Definir SPDs adverses i representatives, incloses mescles LED i espectres amb estructura estreta.
- [ ] Avaluar candidats `SpectralBandSet` per error científic, no per temps d’execució.
- [ ] Seleccionar i versionar el `bandSetId` v1 amb pressupost d’error preregistrat i criteri de rehomologació.
- [ ] Afegir golden tests perquè qualsevol canvi de bandes invalida caches i exigeix nova homologació.

## Criteri de sortida

`V3` queda tancada: existeix un `SpectralBandSet` v1 que compleix el pressupost espectral contra l’oracle fi. Cap benchmark de rendiment ha decidit N.

## Evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.4/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

## Instrucció per a Codex

Primer precisió espectral, després rendiment. No facis sweeps de temps per escollir el nombre de bandes.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.
