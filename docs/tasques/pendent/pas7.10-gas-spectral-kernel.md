# Pas 7.10 — Skyglow físic — Kernel espectral complet i absorció gasosa

> **Estat:** pendent. **Execució:** seqüencial. **Pla canònic:** [19-pla-executable-codex.md](../../skyglow/19-pla-executable-codex.md).

## Finalitat

Passar del B1 monocromàtic a transport espectral v1 complet amb absorció.

## Dependències

[Pas 7.9 — Rayleigh i aerosol](pas7.9-rayleigh-aerosol-b1.md) i [Pas 7.4 — bandset tabulat v1](../completat/pas7.4-spectral-bandset-validation.md). El pressupost `0,01 mag` s'ha de revalidar en aquest nou domini de transport.

## Referències obligatòries

- [01-especificacio-algorismes.md](../../skyglow/01-especificacio-algorismes.md)
- [04-justificacio-cientifica.md](../../skyglow/04-justificacio-cientifica.md)
- [07-benchmark-b0-b7.md](../../skyglow/07-benchmark-b0-b7.md)

## Tasques

- [ ] Vectoritzar el kernel amb el `SpectralBandSet` homologat a 7.4 compartint geometria.
- [ ] Implementar `GasAbsorptionModel` amb LUT offline i `T_eff` per banda.
- [ ] Comparar absorció i transport contra espectre fi/SG-REF, inclosa la sanity de Jensen.
- [ ] Executar les proves B2/B4 de coherència i cost incremental sense reescollir N.
- [ ] Verificar bandSetId, unitats i invalidació de qualsevol resultat incompatible.
- [ ] Revalidar la discretització contra oracle espectral fi amb absorció gasosa i dispersió espectral, aplicant el criteri [TL3D-SKY-V3-SPECTRAL-001](../../evidencies/pas7.4/criteri-preregistrat-v1.json) abans de donar per admissible aquest nou domini. Si supera `0,01 mag`, revisar i versionar `SpectralBandSet`; no relaxar el criteri retrospectivament.

## Criteri de sortida

La ruta directa clear-sky espectral supera invariants de banda, unitats i absorció, amb comparació diagnòstica reproduïble contra SG-REF i l'oracle espectral; cap absorció es tracta com zero per conveniència. La discretització espectral compleix el pressupost congelat de 7.4 en el domini ampliat o usa un `bandSetId` nou rehomologat. El primer PASS/FAIL numèric de transport és 7.12.

## Evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.10/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

## Instrucció per a Codex

El nombre de bandes ja està decidit a 7.4. No el renegociïs aquí per rendiment.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.
