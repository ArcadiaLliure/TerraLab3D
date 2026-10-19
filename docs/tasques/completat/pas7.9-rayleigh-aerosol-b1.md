# Pas 7.9 — Skyglow físic — Rayleigh, aerosol de referència i benchmark B1

> **Estat:** completat. **Estat funcional:** observable. **Origen:** planificat. **Abast vigent:** dispersió Rayleigh/aerosol de referència en una banda i B1 diagnòstic; sense compressió de fase ni gate radiomètric de 7.12.

## Descripció funcional

Introduir la primera física de scattering sobre la ruta directa i auditable.

## Objectiu

Introduir dispersió i transmissió físicament normalitzades al kernel directe existent, amb B1 reproduïble i residuals contra una referència independent revalidada per al mateix domini.

## Dependències

**Depèn de:**

- [Pas 7.8 — Camp òptic estàndard](../completat/pas7.8-optical-field-standard.md)

**En depenen:**

- [Pas següent](../completat/pas7.10-gas-spectral-kernel.md)

## Fonts a consultar

- [01-especificacio-algorismes.md](../../skyglow/01-especificacio-algorismes.md)
- [04-justificacio-cientifica.md](../../skyglow/04-justificacio-cientifica.md)
- [07-benchmark-b0-b7.md](../../skyglow/07-benchmark-b0-b7.md)

Fonts locals i [Chance–Spurr 1997 eq. 2–7](https://lweb.cfa.harvard.edu/atmosphere/publications/1997AOring.pdf), [Henyey–Greenstein 1941](https://articles.adsabs.harvard.edu/pdf/1941ApJ....93...70H) i [documentació NIST de fases](https://pages.nist.gov/SCATMECH/docs/phase.htm) consultades el 2026-10-19. S’han implementat fórmules/fixtures pròpies, sense copiar codi extern ni redistribuir PDFs. [Abast científic i procedència](../../evidencies/pas7.9/validacio-b1.md).

## Codi existent a reutilitzar

- **Repositori actual:** [PropagationKernel](../../../backend/src/terralab3d/domain/light_pollution/propagation_kernel.py), [OpticalField](../../../backend/src/terralab3d/domain/light_pollution/optical_field.py), [guard de revisions](../../../backend/src/terralab3d/application/geometric_propagation.py) i [SG-REF homogeni](../../../backend/src/terralab3d/domain/light_pollution/reference_transport.py). L’[oracle de columnes 7.8](../../../backend/src/terralab3d/domain/light_pollution/reference_optical_column.py) es conserva. La nova [referència B1](../../../backend/src/terralab3d/domain/light_pollution/reference_single_scattering.py) revalida geometria esfèrica, transmissió variable i radiància monocromàtica amb implementació independent.
- **Projectes de referència autoritzats:** cap codi extern seleccionat; consultar fonts primàries i verificar llicències abans d’incorporar recursos.

## Flux tècnic

`PropagationRequest.scattering` conté `ScatteringConfiguration` immutable, banda monocromàtica, fases i aerosol explícit per tile. P/T/n → βR=nσ; aerosol → βext/βsca i fase → intensitat direccional del SourceModel / r² × dispersió × exp(−τsource−τobserver) → GK7/15 LOS. Els dos trajectes es segmenten per cares/altures, amb dependències de totes les capes usades. Rectangles per GL directe dA/A, sense col·lapsar al centre.

Resultat esquema 3, `stage=single_scattering_monochromatic_B1`, radiància espectral a 550 nm en W m⁻² sr⁻¹ nm⁻¹ o escala relativa C. El zenit usa el mateix operador; cap segon 1/r² fins a l’observador. Error exterior, error τ intern i error d’àrea tenen significats separats. B0 i columnes de 7.8 conserven esquemes i resultats previs.

## Errors, cancel·lació i recursos

Rebutjar coeficients no finits/negatius, fase no normalitzada, cobertura absent i geometria singular sense model. Cap fallback atmosfèric implícit. Propagar cancel·lació/revisions i descartar resultats obsolets també en publicar. Perfils/fases sota propietari explícit i recursos CPU fora del frame; sense nous serveis externs ni recursos GPU. No amagar errors de quadratura com a incertesa física.

## Tasques

- [x] Implementar Rayleigh normalitzat i una `PhaseFunction` comuna.
- [x] Implementar HG només com a fallback i una fase de referència tabulada/alta resolució per tests.
- [x] Calcular extinció, scattering source→P→observer i transmissió sense dobles factors geomètrics.
- [x] Executar B1 en 1 banda amb fixtures analítiques i comparació diagnòstica reproduïble contra SG-REF, sense dictar encara PASS/FAIL numèric de transport.
- [x] Verificar linealitat, positivitat, normalització 4π i casos isòtrops.

## Criteri de sortida

B1 supera invariants analítics de normalització, linealitat, positivitat i geometria, i documenta la discrepància contra SG-REF. El primer PASS/FAIL numèric runtime↔SG-REF és 7.12.

## Proves i evidències obligatòries

- [x] Proves unitàries/golden/property rellevants en verd.
- [x] Regressions afectades en verd.
- [x] Evidència reproduïble sota `docs/evidencies/pas7.9/`.
- [x] README/inventari/estat actualitzats només segons comportament observable.
- [x] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

**Resultats verificats (2026-10-19):** 21 proves noves i 384 proves backend superades. Ruff/Pyright dels fitxers afectats passen; Pyright global conserva 67 errors/3 avisos preexistents. B1a: 60 passades mesurades, nou elevacions i 900 LOS principals, cinc escalfaments complets. Set diagnòstics, referència GK21 revalidada, fase tabulada refinada i regressió B0 exacta. [Informe](../../evidencies/pas7.9/validacio-b1.md), [protocol](../../evidencies/pas7.9/protocol-b1-v1.json), [JSON](../../evidencies/pas7.9/resultats-b1-v1.json), [CSV](../../evidencies/pas7.9/passades-b1-v1.csv) i [proves](../../evidencies/pas7.9/proves-backend.txt). Cap gate de discrepància runtime ni homologació H.

## Fora d'abast

Compressió Legendre (7.19), absorció espectral completa (7.10), terreny/visibilitat física (7.11), gate numèric de transport (7.12), ERA5/CAMS, cache, renderer i homologació H.

## Instrucció per a Codex

No comprimeixis encara la fase en Legendre. Primer demostra la física amb la representació de referència.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.

## Treball pendent

Cap dins de 7.9. [7.10](../completat/pas7.10-gas-spectral-kernel.md) ampliarà/revalidarà espectre i absorció gasosa; continua pendent i no s’ha executat aquí.
