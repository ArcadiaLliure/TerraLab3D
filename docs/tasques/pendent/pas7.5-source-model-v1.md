# Pas 7.5 — Skyglow físic — SourceModel v1: SPD, emissió angular i incertesa

> Estat: **bloquejat** per manca d'una font Black Marble de 2026 espectralment admissible i d'un operador L3→font justificat. **Estat funcional:** gate de mesura i perfil angular genèric verificats offline; cap `SourceModel` físic de producte. **Execució:** seqüencial. **Pla canònic:** [19-pla-executable-codex.md](../../skyglow/19-pla-executable-codex.md).

## Descripció funcional

El `SourceModel` ha de transformar observacions Black Marble L3 qualificades en un ensemble SPD i d'emissió angular ascendent amb normalització, procedència, domini i incertesa estructural. L'observació, la resposta instrumental, el prior espectral, la correcció L3 i la radiació emesa són magnituds diferents. El [contracte de 7.3](../../evidencies/pas7.3/contrast-granuls-black-marble-c2.md) no acredita encara aquesta inferència.

## Fonts a consultar

- [ATBD VIIRS SDR](https://ncc.nesdis.noaa.gov/documents/documentation/ATBD-VIIRS-RadiometricCal_20131212.pdf), [User Guide Black Marble C2 §2.2 Eq. (1)](https://viirsland.gsfc.nasa.gov/PDF/BlackMarbleUserGuide_Collection2.0.pdf) i [validació NASA](https://viirsland.gsfc.nasa.gov/Val/BM_Val.html), revisats el 2026-10-18 segons les [matrius de 7.3](../../evidencies/pas7.3/revisio-multisatel-lit.md).
- [NASA Black Marble Q&A, pregunta 19](https://appliedsciences.nasa.gov/sites/default/files/Black%20Marble%20Q%26A%20Doc.pdf), consultada el 2026-10-18: la banda DNB sola no identifica canvis espectrals de fonts LED.
- [Cinzano i Falchi 2012](https://academic.oup.com/mnras/article/427/4/3337/973668) i [World Atlas 2016](https://pmc.ncbi.nlm.nih.gov/articles/PMC4928945/), consultats el 2026-10-18: funcions angulars ascendents normalitzades i múltiples patrons, sense una forma universal inferida de L3.
- [Especificació](../../skyglow/01-especificacio-algorismes.md), [justificació científica](../../skyglow/04-justificacio-cientifica.md), [validació](../../skyglow/08-validacio-cientifica.md), [incertesa](../../skyglow/09-incertesa-proveniencia.md) i [evidència de 7.5](../../evidencies/pas7.5/estat-inferencia-font-2026.md), contrastades el 2026-10-18.

## Objectiu

Tancar `F1` i generar un `SourceModel` falsable d'almenys una font Black Marble amb RSR/guany/producte/període acreditats. Fins aleshores, impedir que QA 0, una corba diagnòstica o el valor L3 sol esdevinguin emissió física.

## Dependències

**Depèn de:** [Pas 7.3 — contracte de mesura](../completat/pas7.3-dnb-rsr-measurement.md) i [Pas 7.4 — oracle espectral i SpectralBandSet](../completat/pas7.4-spectral-bandset-validation.md). La homologació numèrica acotada de 7.4 no homologa automàticament cap sensor nocturn de 2026.

**En depenen:** [Pas 7.6 — SG-REF](pas7.6-sg-ref-reference-solver.md), [Pas 7.16 — incertesa quantitativa](pas7.16-uncertainty-provenance.md) i [Pas 7.17 — validació empírica](pas7.17-clear-sky-ground-truth.md).

## Codi existent a reutilitzar

- **Repositori actual — REUSE:** [observació VNP46 tipada](../../../backend/src/terralab3d/domain/light_pollution/vnp46.py), [adaptador HDF5](../../../backend/src/terralab3d/infrastructure/adapters/light_pollution/vnp46.py), [operador DNB i identitat RSR](../../../backend/src/terralab3d/domain/light_pollution/dnb_measurement.py), [lector de manifests RSR](../../../backend/src/terralab3d/infrastructure/adapters/light_pollution/viirs_rsr.py) i [bandset tabulat](../../../backend/src/terralab3d/domain/light_pollution/spectral_bandset.py).
- **Repositori actual — NEW parcial de 7.5:** [gate d'admissibilitat i forma angular](../../../backend/src/terralab3d/domain/light_pollution/source_model.py), [eina diagnòstica real](../../../tools/assess_vnp46_source_step7_5.py) i [auditoria de manifests](../../../tools/audit_source_inputs_step7_5.py). Encara no hi ha constructor físic `SourceModel`.
- **Projecte de referència:** TerraLab al commit fixat per les [normes](../../normes-arquitectura.md), només lectura. No s'ha identificat cap inversió Black Marble L3→SPD/angular acreditada per reutilitzar; no es copia el Bortle visual com a física.

## Flux tècnic

Grànul verificat → `Vnp46Observation` amb radiància L3 crua i QA → [gate de base de mesura](../../../backend/src/terralab3d/domain/light_pollution/source_model.py) per producte, dia, qualitat i RSR amb evidència de guany/L3 → prior SPD i patró angular amb procedència → operador calibrat L3→font i incertesa estructural → `SourceModel` versionat. La integral TOA `BAND_INTEGRATED` no s'aplica directament a `DNB_BRDF-Corrected_NTL`; cap etapa absent rep valors de conveniència.

El [registre de sis respostes instal·lades](../../evidencies/pas7.5/auditoria-rsr-2026.json) no té cap coincidència `operational_l3` per al 2026-09-13. El VNP46 h00v01 real té QA 2; el VJ146 h18v04 té QA 0 urbà real, però encara manca RSR/guany/L3 operatius. Per això el flux s'atura abans de crear la font.

## Errors, cancel·lació i recursos

RSR absent o ambigua, identitat/dia incompatible, QA insuficient, radiància L3 no positiva o unitats errònies retornen `unavailable_for_physical_inference` amb causes. No hi ha clipping, substitució intersensor, gap-fill silenciós ni SBAF. Les eines són síncrones i locals, sense descàrregues ni GPU; la interrupció del procés deixa intactes els assets. L'adquisició ordinària correspon al Pas 24.

## Tasques

- [x] Separar en codi l'admissibilitat de mesura per a `SourceModel` de l'homologació final que requereix incertesa quantitativa a 7.16.
- [x] Rebutjar al gate RSR diagnòstica, dia/producte incompatibles, QA no candidata i senyal nul, preservant l'observació.
- [x] Implementar una forma angular axial tabulada amb procedència i normalització hemisfèrica; no seleccionar cap perfil per defecte.
- [x] Auditar els manifests locals per al dia real i contrastar el gate amb un VNP46 real.
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

**Estat verificat 2026-10-18: bloquejat.** Cap font supera la condició RSR/guany/L3 ni hi ha una inversió angular/espectral justificada. El gate parcial i les seves proves no satisfan el criteri de sortida; el punter no avança a 7.6.

## Proves i evidències obligatòries

- [x] [Quatre proves](../../../backend/tests/test_source_model_gate_step7_5.py) del gate, fixture sintètica i normalització angular analítica/independent.
- [x] [Auditoria dels sis registres RSR](../../evidencies/pas7.5/auditoria-rsr-2026.json) i [contrast amb VNP46 real](../../evidencies/pas7.5/estat-inferencia-font-2026.md).
- [x] Regressions backend completes: 209 proves en verd; Ruff, Pyright i enllaços locals en verd el 2026-10-18.
- [ ] Evidència d'un `SourceModel` físic real amb RSR/guany, priors i angularitat admissibles.
- [x] README/inventari/estat actualitzats segons el comportament parcial verificat.
- [x] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

## Fora d’abast

SG-REF i transport (7.6+), quantificació completa d'incertesa (7.16), ground truth clear-sky (7.17), gestor ordinari de descàrregues (24) i representació Three.js. Una classe angular genèrica no és un model de ciutat homologat.

## Instrucció per a Codex

No permetis que un model angular provisional arribi a producció com si fos una mesura. Si no hi ha evidència suficient, atura la seqüència.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.

## Treball pendent

El [registre d'evidència](../../evidencies/pas7.5/estat-inferencia-font-2026.md) identifica RSR efectiva i mapping de guany vinculats a Black Marble C2 per almenys una font, i inferència L3→SPD/angular aplicable amb incertesa estructural. La biblioteca actual només permet un diagnòstic segur d'indisponibilitat.
