# Pas 7.10 — Skyglow físic — Kernel espectral complet i absorció gasosa

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Revalidar el domini de les 42 SPD CIE, interpolacions Kelvin, mescles i operadors Rayleigh/aerosols/gasos contra integració fina, mantenint el llindar preregistrat de 0,01 mag. Cap PASS nou per herència de 7.4.

## Descripció funcional

Passar del B1 monocromàtic a transport espectral v1 complet amb absorció.

## Fonts a consultar

- [01-especificacio-algorismes.md](../../skyglow/01-especificacio-algorismes.md)
- [04-justificacio-cientifica.md](../../skyglow/04-justificacio-cientifica.md)
- [07-benchmark-b0-b7.md](../../skyglow/07-benchmark-b0-b7.md)

Fonts locals del pla vigent consultades el 2026-10-18; cap asset no es declara validat només per una referència.

## Objectiu

Revalidar el domini de les 42 SPD CIE, interpolacions Kelvin, mescles i operadors Rayleigh/aerosols/gasos contra integració fina, mantenint el llindar preregistrat de 0,01 mag. Cap PASS nou per herència de 7.4.

## Dependències

**Depèn de:**
- [Pas 7.9](pas7.9-rayleigh-aerosol-b1.md)
- [Pas 7.4](../completat/pas7.4-spectral-bandset-validation.md)
- [Pas 7.5.1](../completat/pas7.5.1-black-marble-spectral-simulation.md)

**En depenen:**
- [Pas 7.11](pas7.11-terrain-curvature.md)

## Codi existent a reutilitzar

- **Repositori actual:** [SourceModel S/C](../../../backend/src/terralab3d/domain/light_pollution/source_model.py), [escenaris i configuració](../../../backend/src/terralab3d/domain/light_pollution/simulation.py), [biblioteca](../../../backend/src/terralab3d/domain/light_pollution/spectral_library.py) i [controls](../../../frontend/src/view/ui/components/SkyglowControls.ts). Reutilitzar els contractes sense duplicar el motor.
- **Projectes de referència autoritzats:** cap runtime extern; els oracles científics independents han de tenir fonts i llicències verificades abans d’incorporar-los.

## Flux tècnic

Configuració versionada + SourceModel S/C + procedència → component del pas → sortida amb unitats, revisió i qualificació pròpies. Revalidar el domini de les 42 SPD CIE, interpolacions Kelvin, mescles i operadors Rayleigh/aerosols/gasos contra integració fina, mantenint el llindar preregistrat de 0,01 mag. Cap PASS nou per herència de 7.4.

## Errors, cancel·lació i recursos

Previst: rebutjar entrades no finites, unitats i revisions incompatibles; cancel·lació cooperativa, latest-wins i descart de resultats antics. Recursos grans persistents fora del JSON de cada frame; alliberament explícit pel propietari. RSR de referència C no es promou a H; incertesa desconeguda no es converteix en sigma.

## Tasques

- [ ] Vectoritzar el kernel amb el `SpectralBandSet` homologat a 7.4 compartint geometria.
- [ ] Implementar `GasAbsorptionModel` amb LUT offline i `T_eff` per banda.
- [ ] Comparar absorció i transport contra espectre fi/SG-REF, inclosa la sanity de Jensen.
- [ ] Executar les proves B2/B4 de coherència i cost incremental sense reescollir N.
- [ ] Verificar bandSetId, unitats i invalidació de qualsevol resultat incompatible.
- [ ] Revalidar la discretització contra oracle espectral fi amb absorció gasosa i dispersió espectral, aplicant el criteri [TL3D-SKY-V3-SPECTRAL-001](../../evidencies/pas7.4/criteri-preregistrat-v1.json) abans de donar per admissible aquest nou domini. Si supera `0,01 mag`, revisar i versionar `SpectralBandSet`; no relaxar el criteri retrospectivament.
- [ ] Revalidar el domini de les 42 SPD CIE, interpolacions Kelvin, mescles i operadors Rayleigh/aerosols/gasos contra integració fina, mantenint el llindar preregistrat de 0,01 mag. Cap PASS nou per herència de 7.4.

## Criteri de sortida

La ruta directa clear-sky espectral supera invariants de banda, unitats i absorció, amb comparació diagnòstica reproduïble contra SG-REF i l'oracle espectral; cap absorció es tracta com zero per conveniència. La discretització espectral compleix el pressupost congelat de 7.4 en el domini ampliat o usa un `bandSetId` nou rehomologat. El primer PASS/FAIL numèric de transport és 7.12.

## Proves i evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.10/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.
- [ ] Verificar el nou abast S/C i les modalitats realista/K amb casos independents; H conserva el seu contrast empíric.

**Resultats verificats:** aquest pas encara no s’ha executat; les proves de configuració/font corresponen a 7.5.1.
- [ ] Verificar el nou abast S/C i les modalitats realista/K amb casos independents; H conserva el seu contrast empíric.

**Resultats verificats:** aquest pas encara no s’ha executat; les proves de configuració/font corresponen a 7.5.1.

## Fora d'abast

Homologar H sense observacions; fabricar fonts o radiància; modificar llindars després dels resultats.

## Instrucció per a Codex

El nombre de bandes ja està decidit a 7.4. No el renegociïs aquí per rendiment.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.

Aplicar la política de referència RSR i dominis vigent; no reobrir la cerca anual exacta com a prerequisit global. No declarar la propagació implementada a partir dels controls de 7.5.1.

Aplicar la política de referència RSR i dominis vigent; no reobrir la cerca anual exacta com a prerequisit global. No declarar la propagació implementada a partir dels controls de 7.5.1.

## Treball pendent

- [ ] Executar les tasques i demostrar el criteri de sortida d’aquest pas. La connexió gràfica final de kelvins continua obligatòria fins a 7.27.
