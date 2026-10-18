# Pas 7.9 — Skyglow físic — Rayleigh, aerosol de referència i benchmark B1

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** dispersió Rayleigh/aerosol de referència en una banda i B1 diagnòstic; sense compressió de fase ni gate radiomètric de 7.12.

## Descripció funcional

Introduir la primera física de scattering sobre la ruta directa i auditable.

## Objectiu

Introduir dispersió i transmissió físicament normalitzades al kernel directe existent, amb B1 reproduïble i residuals contra una referència independent revalidada per al mateix domini.

## Dependències

**Depèn de:**

- [Pas 7.8 — Camp òptic estàndard](../completat/pas7.8-optical-field-standard.md)

**En depenen:**

- [Pas següent](pas7.10-gas-spectral-kernel.md)

## Fonts a consultar

- [01-especificacio-algorismes.md](../../skyglow/01-especificacio-algorismes.md)
- [04-justificacio-cientifica.md](../../skyglow/04-justificacio-cientifica.md)
- [07-benchmark-b0-b7.md](../../skyglow/07-benchmark-b0-b7.md)

Fonts locals revisades en normalitzar aquesta dependència el 2026-10-19. La selecció de fonts primàries per coeficients/fases i les llicències s’han de verificar en executar 7.9; cap física B1 no es declara implementada aquí.

## Codi existent a reutilitzar

- **Repositori actual:** [PropagationKernel](../../../backend/src/terralab3d/domain/light_pollution/propagation_kernel.py), [OpticalField](../../../backend/src/terralab3d/domain/light_pollution/optical_field.py), [guard de revisions](../../../backend/src/terralab3d/application/geometric_propagation.py) i [SG-REF homogeni](../../../backend/src/terralab3d/domain/light_pollution/reference_transport.py). L’[oracle de columnes 7.8](../../../backend/src/terralab3d/domain/light_pollution/reference_optical_column.py) no valida radiància: ampliar i revalidar la referència radiomètrica abans de comparar el domini nou.
- **Projectes de referència autoritzats:** cap codi extern seleccionat; consultar fonts primàries i verificar llicències abans d’incorporar recursos.

## Flux tècnic

SourceModel S/C i camp estàndard versionat → coeficients moleculars/aerosol i fase de referència per una banda → transmissió source→P i P→observer → integrand de dispersió simple del kernel → radiància amb unitats, error numèric, dependències i comptadors → B1/invariants i discrepàncies SG-REF. El zenit usa el mateix operador. Conservar amplituds relatives C, sense convertir-les en watts.

## Errors, cancel·lació i recursos

Rebutjar coeficients no finits/negatius, fase no normalitzada, cobertura absent i geometria singular sense model. Cap fallback atmosfèric implícit. Propagar cancel·lació/revisions i descartar resultats obsolets també en publicar. Perfils/fases sota propietari explícit i recursos CPU fora del frame; sense nous serveis externs ni recursos GPU. No amagar errors de quadratura com a incertesa física.

## Tasques

- [ ] Implementar Rayleigh normalitzat i una `PhaseFunction` comuna.
- [ ] Implementar HG només com a fallback i una fase de referència tabulada/alta resolució per tests.
- [ ] Calcular extinció, scattering source→P→observer i transmissió sense dobles factors geomètrics.
- [ ] Executar B1 en 1 banda amb fixtures analítiques i comparació diagnòstica reproduïble contra SG-REF, sense dictar encara PASS/FAIL numèric de transport.
- [ ] Verificar linealitat, positivitat, normalització 4π i casos isòtrops.

## Criteri de sortida

B1 supera invariants analítics de normalització, linealitat, positivitat i geometria, i documenta la discrepància contra SG-REF. El primer PASS/FAIL numèric runtime↔SG-REF és 7.12.

## Proves i evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.9/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

**Resultats verificats:** B1 encara no executat. La dependència 7.8 verifica P/T/n, travesses i columnes, sense coeficients de dispersió. El domini homogeni de 7.6 conserva les seves proves històriques.

## Fora d'abast

Compressió Legendre (7.19), absorció espectral completa (7.10), terreny/visibilitat física (7.11), gate numèric de transport (7.12), ERA5/CAMS, cache, renderer i homologació H.

## Instrucció per a Codex

No comprimeixis encara la fase en Legendre. Primer demostra la física amb la representació de referència.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.

## Treball pendent

- [ ] Executar les tasques B1 i revalidar SG-REF per al domini introduït; conservar el pas pendent fins a demostrar-ne el criteri de sortida.
