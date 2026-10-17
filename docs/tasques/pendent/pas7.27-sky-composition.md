# Pas 7.27 — Skyglow físic — Composició lineal del cel i estats reference/instantaneous

> **Estat:** pendent. **Execució:** seqüencial. **Pla canònic:** [19-pla-executable-codex.md](../../skyglow/19-pla-executable-codex.md).

## Finalitat

Integrar el canal artificial amb la resta del cel sense doble comptatge ni calibratge creuat.

## Dependències

7.26

## Referències obligatòries

- [01-especificacio-algorismes.md](../../skyglow/01-especificacio-algorismes.md)
- [06-contractes-dades.md](../../skyglow/06-contractes-dades.md)

## Tasques

- [ ] Definir `SkyRadianceComposer` amb canals artificial, natural sense Lluna, lunar i crepuscular.
- [ ] Mantenir `reference` i `instantaneous` amb provenance separada.
- [ ] Fer la suma en radiància lineal abans d’exposició/tone mapping.
- [ ] Permetre que canals astrals encara no físics entrin com a estratègies/versionats sense modificar el canal artificial.
- [ ] Provar linealitat, commutativitat i absència de double count amb Pas 7 històric/7.51+.

## Criteri de sortida

El skyglow artificial conserva identitat i provenance dins la composició; la Lluna/crepuscle no canvien la inferència artificial i `reference` és invariant als components instantanis.

## Evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.27/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

## Instrucció per a Codex

No facis servir una lectura SQM total per recalibrar el canal artificial.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.
