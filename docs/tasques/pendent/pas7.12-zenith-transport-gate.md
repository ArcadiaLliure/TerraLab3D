# Pas 7.12 — Skyglow físic — Gate zenital de transport radiomètric

> **Estat:** pendent. **Execució:** seqüencial. **Pla canònic:** [19-pla-executable-codex.md](../../skyglow/19-pla-executable-codex.md).

## Finalitat

Validar el transport complet abans de cúpules, compressions o caches.

## Dependències

7.11

## Referències obligatòries

- [07-benchmark-b0-b7.md](../../skyglow/07-benchmark-b0-b7.md)
- [08-validacio-cientifica.md](../../skyglow/08-validacio-cientifica.md)

## Tasques

- [ ] Preregistrar tolerància, mètrica, unitat i domini runtime↔SG-REF abans de veure el resultat PASS/FAIL del runtime candidat; justificar-los amb font admissible, incloses convergència i incertesa numèrica de SG-REF demostrades a 7.6.
- [ ] Executar fixtures zenitals sintètiques amb SourceModel conegut contra SG-REF.
- [ ] Executar fonts S definides puntuals i extenses del [Pas 7.5](../completat/pas7.5-source-model-v1.md), amb atmosfera estàndard i DEM reproduïble. Una fixture Black Marble C/H s'afegeix només si el seu domini observacional ja està acreditat; no és prerequisit del gate S.
- [ ] Auditar cadena d’unitats, convergència, error numèric, memòria, nodes i dependències.
- [ ] Separar explícitament l’error de transport de la incertesa del SourceModel.
- [ ] Bloquejar qualsevol pas posterior si necessita un factor de calibratge opac o una ruta especial a 90°.

## Criteri de sortida

La tolerància runtime↔SG-REF està justificada i congelada abans de la comparació decisòria; si manca, 7.12 queda bloquejat. El mateix `PropagationKernel` supera el perfil V1 al zenit amb fonts S, sense calibratge arbitrari. El PASS valida transport donat un SourceModel S, no la inferència d'emissió C/H.

## Evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.12/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

## Instrucció per a Codex

Aquest és el primer gate dur de física runtime. No triïs la tolerància a partir dels residuals del candidat. Si falla, corregeix 7.7–7.11; no compensis el resultat en 7.13 o en el renderer.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.
