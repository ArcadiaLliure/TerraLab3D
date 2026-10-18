# Pas 7.5 — Skyglow físic — SourceModel v1: SPD, emissió angular i incertesa

> **Estat:** pendent. **Execució:** seqüencial. **Pla canònic:** [19-pla-executable-codex.md](../../skyglow/19-pla-executable-codex.md).

## Finalitat

Tancar `F1` i transformar observacions DNB admissibles per sensor/producte/release en una distribució de font explícita, versionada i falsable.

## Dependències

[Pas 7.4 — oracle espectral i SpectralBandSet](../completat/pas7.4-spectral-bandset-validation.md) i [Pas 7.3 — contracte de mesura](../completat/pas7.3-dnb-rsr-measurement.md). La homologació numèrica acotada de 7.4 i la conclusió matemàtica de 7.3 no homologuen automàticament cap sensor nocturn de 2026.

## Referències obligatòries

- [01-especificacio-algorismes.md](../../skyglow/01-especificacio-algorismes.md)
- [04-justificacio-cientifica.md](../../skyglow/04-justificacio-cientifica.md)
- [08-validacio-cientifica.md](../../skyglow/08-validacio-cientifica.md)
- [09-incertesa-proveniencia.md](../../skyglow/09-incertesa-proveniencia.md)

## Tasques

- [ ] Definir `SourceModel` separant normalització DNB, pesos SPD, distribució angular i components d’incertesa.
- [ ] Adoptar un model angular publicat/empíric/ensemble amb domini declarat; Lambert no és fallback implícit.
- [ ] Documentar inputs auxiliars necessaris i comportament quan falten.
- [ ] Per cada font candidata i període, acreditar la RSR efectiva o família aplicable, el mapping de guany i el vincle amb la cadena Black Marble C2; si manca, mantenir aquella font `unavailable_for_physical_inference` sense convertir una corba diagnòstica en operativa.
- [ ] Definir la inferència L3 corregit → prior/ensemble SPD i emissió angular amb la semàntica de l'equació (1) de NASA; no aplicar la integral TOA directament al valor L3 ni reconstruir correccions auxiliars absents com si fossin mesurades.
- [ ] Propagar la incertesa estructural de la inferència Black Marble L3→font, incloent RSR, correccions L3 i prior SPD per plataforma, sense confondre-la amb error numèric; una SPD única no es dedueix d'una banda pancromàtica.
- [ ] Conservar observacions superposades de plataformes diferents sense sumar-les; el fallback i la selecció manual mantenen la procedència i la causa de no admissibilitat. Cap SBAF per defecte.
- [ ] Validar fixtures sintètiques i, si existeixen, dades angulars externes independents; versionar `sourceModelId`.

## Criteri de sortida

`F1` queda resolta per al domini concret d'almenys una font **espectralment admissible** o el pas queda `bloquejat`. Una observació L3 tipada i qualificada produeix `SourceModel` amb provenance, SPD prior/ensemble, model angular i incertesa estructural justificats. La correspondència RSR/guany/producte/període ha d'estar acreditada per a la font escollida; les altres poden romandre no homologades. `Vnp46Observation` continua sent el cas implementat de lectura, sense validar automàticament VJ146/VJ246.

## Evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.5/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

## Instrucció per a Codex

No permetis que un model angular provisional arribi a producció com si fos una mesura. Si no hi ha evidència suficient, atura la seqüència.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.
