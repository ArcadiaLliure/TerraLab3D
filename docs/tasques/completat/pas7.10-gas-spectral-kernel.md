# Pas 7.10 — Skyglow físic — Kernel espectral complet i absorció gasosa

> **Estat:** completat. **Estat funcional:** observable offline en el domini prescrit S/C, amb O3 203–293 K. **Origen:** planificat. **Abast vigent:** 42 SPD CIE, Kelvin, mescles, Rayleigh/aerosol/gas, pressupost 0,01 mag i sensibilitat 10–50 km. No homologa aire terrestre complet ni H.

## Descripció funcional

Passar del B1 monocromàtic a transport espectral v1 complet amb absorció.

## Fonts a consultar

- [01-especificacio-algorismes.md](../../skyglow/01-especificacio-algorismes.md)
- [04-justificacio-cientifica.md](../../skyglow/04-justificacio-cientifica.md)
- [07-benchmark-b0-b7.md](../../skyglow/07-benchmark-b0-b7.md)

Fonts locals del pla vigent consultades el 2026-10-18; cap asset no es declara validat només per una referència.

Consulta primària del 2026-10-19: [dataset Serdyuchenko–Gorshelev](https://zenodo.org/records/5793207), llicència CC BY 4.0 comprovada a l'API Zenodo; [metadades de Bremen](https://www.iup.uni-bremen.de/gruppen/molspec/databases/referencespectra/o3spectra2011/index.html), λ de buit, cm²/molècula i ordre tèrmic de les columnes. Originals visibles comprimides, transformació i checksums al [manifest gasós](../../../backend/src/terralab3d/infrastructure/catalogs/gases/manifest.json). La taula de 193 K conté 69 valors negatius; es rebutja aquell domini sense alterar les dades i es restringeix a 203–293 K abans d'avaluar candidats. Es conserven els protocols [v1](../../evidencies/pas7.10/protocol-espectral-v1.json), [v2](../../evidencies/pas7.10/protocol-espectral-v2.json) i [gate v3](../../evidencies/pas7.10/protocol-gate-espectral-v3.json).

## Objectiu

Revalidar el domini de les 42 SPD CIE, interpolacions Kelvin, mescles i operadors Rayleigh/aerosols/gasos contra integració fina, mantenint el llindar preregistrat de 0,01 mag. Cap PASS nou per herència de 7.4.

## Dependències

**Depèn de:**
- [Pas 7.9](../completat/pas7.9-rayleigh-aerosol-b1.md)
- [Pas 7.4](../completat/pas7.4-spectral-bandset-validation.md)
- [Pas 7.5.1](../completat/pas7.5.1-black-marble-spectral-simulation.md)

**En depenen:**
- [Pas 7.11](../completat/pas7.11-terrain-curvature.md)

## Codi existent a reutilitzar

- **Repositori actual:** [kernel B1](../../../backend/src/terralab3d/domain/light_pollution/propagation_kernel.py), [banda/fases](../../../backend/src/terralab3d/domain/light_pollution/scattering.py), [referència B1 independent](../../../backend/src/terralab3d/domain/light_pollution/reference_single_scattering.py), [SourceModel S/C](../../../backend/src/terralab3d/domain/light_pollution/source_model.py), [escenaris i configuració](../../../backend/src/terralab3d/domain/light_pollution/simulation.py), [biblioteca](../../../backend/src/terralab3d/domain/light_pollution/spectral_library.py) i [controls](../../../frontend/src/view/ui/components/SkyglowControls.ts). Reutilitzar els contractes sense duplicar el motor.
- **Projectes de referència autoritzats:** cap runtime extern; els oracles científics independents han de tenir fonts i llicències verificades abans d’incorporar-los.

## Flux tècnic

Configuració versionada + SourceModel S/C + procedència → component del pas → sortida amb unitats, revisió i qualificació pròpies. Revalidar el domini de les 42 SPD CIE, interpolacions Kelvin, mescles i operadors Rayleigh/aerosols/gasos contra integració fina, mantenint el llindar preregistrat de 0,01 mag. Cap PASS nou per herència de 7.4.

## Errors, cancel·lació i recursos

Verificat: rebuig d’entrades no finites, unitats i revisions incompatibles; cancel·lació cooperativa, latest-wins i descart de resultats antics. Recursos grans persistents fora del JSON de cada frame; alliberament explícit pel propietari. RSR de referència C no es promou a H; incertesa desconeguda no es converteix en sigma.

## Tasques

- [x] Vectoritzar el kernel amb el `SpectralBandSet` homologat a 7.4 compartint geometria.
- [x] Implementar `GasAbsorptionModel` amb LUT offline i `T_eff` per banda.
- [x] Comparar absorció i transport contra espectre fi/SG-REF, inclosa la sanity de Jensen.
- [x] Executar les proves B2/B4 de coherència i cost incremental sense reescollir N.
- [x] Verificar bandSetId, unitats i invalidació de qualsevol resultat incompatible.
- [x] Revalidar la discretització contra oracle espectral fi amb absorció gasosa i dispersió espectral, aplicant el criteri [TL3D-SKY-V3-SPECTRAL-001](../../evidencies/pas7.4/criteri-preregistrat-v1.json) abans de donar per admissible aquest nou domini. Si supera `0,01 mag`, revisar i versionar `SpectralBandSet`; no relaxar el criteri retrospectivament.
- [x] Revalidar el domini de les 42 SPD CIE, interpolacions Kelvin, mescles i operadors Rayleigh/aerosols/gasos contra integració fina, mantenint el llindar preregistrat de 0,01 mag. Cap PASS nou per herència de 7.4.

## Criteri de sortida

La ruta directa clear-sky espectral supera invariants de banda, unitats i absorció, amb comparació diagnòstica reproduïble contra SG-REF i l'oracle espectral; cap absorció es tracta com zero per conveniència. La discretització espectral compleix el pressupost congelat de 7.4 en el domini ampliat o usa un `bandSetId` nou rehomologat. El primer PASS/FAIL numèric de transport és 7.12.

## Proves i evidències obligatòries

- [x] Proves unitàries/golden/property rellevants en verd.
- [x] Regressions afectades en verd.
- [x] Evidència reproduïble sota `docs/evidencies/pas7.10/`.
- [x] README/inventari/estat actualitzats només segons comportament observable.
- [x] Cap capacitat d’un pas posterior marcada prematurament com a implementada.
- [x] Verificar el nou abast S/C i les modalitats realista/K amb casos independents; H conserva el seu contrast empíric.

**Resultats verificats, 2026-10-19:** 405 proves backend, 21 noves; Ruff/Pyright afectats passen; global 67 errors/3 avisos heretats. 111.168/111.168 casos espectrals i 326.040 T_eff il·luminats passen 0,01 mag. B0/B1/B2/B4 amb 40 mesures, 48 casos de sostre i SG-REF independent refinat. [Informe i límits](../../evidencies/pas7.10/validacio-espectral-i-gasos.md). Cap execució de 7.11.

## Fora d'abast

Homologar H sense observacions; fabricar fonts o radiància; modificar llindars després dels resultats.

## Instrucció per a Codex

El nombre de bandes ja està decidit a 7.4. No el renegociïs aquí per rendiment.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.

Aplicar la política de referència RSR i dominis vigent; no reobrir la cerca anual exacta com a prerequisit global. No declarar la propagació implementada a partir dels controls de 7.5.1.

## Treball pendent

No queda treball executable d'aquest pas en el domini prescrit verificat. Les dades H2O/O2/NO2, l'aire terrestre complet, la meteorologia real, H i la connexió gràfica de kelvins no s'acrediten amb aquesta LUT O3. 7.27 conserva la connexió gràfica obligatòria; 7.14 revalidarà les seves projeccions noves. 7.11 queda pendent sense executar.

La implementació és directa dins de cada petició. Reutilitza interseccions/columnes entre longituds d'ona i coeficients homogenis dins de la LOS; no afegeix AD, cache entre peticions, transport precomputat, FFT, GPU ni reuse de moviment. La composició gasosa de validació conté O3 prescrit; altres absorbidors no es declaren calculats ni s'assimilen a aire terrestre complet.

## Detall de verificació i cost

Columnes independents de λ amb GK vectorial i partició exacta als nusos T; cap cache entre peticions. Les medianes instrumentades per 900 LOS són B0 0,391 s, B1 21,003 s, B2 27,155 s i B4 29,493 s. S'ha repetit el cas de 900 LOS després de la partició T i s'han preservat les mesures anteriors. El sostre de 10 km perd 22,45% respecte de 50 km en el B4 estàndard zenital de la fixture; la contribució superior a 50 km continua desconeguda. Error espectral global màxim 0,000115211 mag i T_eff per banda 0,000333073 mag; són diferents de l'error de truncament i de la incertesa experimental. Vegeu [evidència completa](../../evidencies/pas7.10/validacio-espectral-i-gasos.md).
