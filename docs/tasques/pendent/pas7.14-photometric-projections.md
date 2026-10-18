# Pas 7.14 — Skyglow físic — Projeccions fotomètriques i sensors SQM/TESS

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Projectar radiància de SPD, interpolacions Kelvin i mescles sense perdre la normalització de comparació ni el suport; revalidar 0,01 mag contra l’oracle fi per resposta CIE/SQM/TESS.

## Descripció funcional

Projectar radiància espectral física a magnituds/instruments sense retroalimentar el kernel.

## Fonts a consultar

- [06-contractes-dades.md](../../skyglow/06-contractes-dades.md)
- [08-validacio-cientifica.md](../../skyglow/08-validacio-cientifica.md)

Fonts locals del pla vigent consultades el 2026-10-18; cap asset no es declara validat només per una referència.

## Objectiu

Projectar radiància de SPD, interpolacions Kelvin i mescles sense perdre la normalització de comparació ni el suport; revalidar 0,01 mag contra l’oracle fi per resposta CIE/SQM/TESS.

## Dependències

**Depèn de:**
- [Pas 7.13](pas7.13-dome-profile-direct.md)
- [Pas 7.4](../completat/pas7.4-spectral-bandset-validation.md)
- [Pas 7.5.1](../completat/pas7.5.1-black-marble-spectral-simulation.md)

**En depenen:**
- [Pas 7.15](pas7.15-atmos-era5-cams.md)

## Codi existent a reutilitzar

- **Repositori actual:** [SourceModel S/C](../../../backend/src/terralab3d/domain/light_pollution/source_model.py), [escenaris i configuració](../../../backend/src/terralab3d/domain/light_pollution/simulation.py), [biblioteca](../../../backend/src/terralab3d/domain/light_pollution/spectral_library.py) i [controls](../../../frontend/src/view/ui/components/SkyglowControls.ts). Reutilitzar els contractes sense duplicar el motor.
- **Projectes de referència autoritzats:** cap runtime extern; els oracles científics independents han de tenir fonts i llicències verificades abans d’incorporar-los.

## Flux tècnic

Configuració versionada + SourceModel S/C + procedència → component del pas → sortida amb unitats, revisió i qualificació pròpies. Projectar radiància de SPD, interpolacions Kelvin i mescles sense perdre la normalització de comparació ni el suport; revalidar 0,01 mag contra l’oracle fi per resposta CIE/SQM/TESS.

## Errors, cancel·lació i recursos

Previst: rebutjar entrades no finites, unitats i revisions incompatibles; cancel·lació cooperativa, latest-wins i descart de resultats antics. Recursos grans persistents fora del JSON de cada frame; alliberament explícit pel propietari. RSR de referència C no es promou a H; incertesa desconeguda no es converteix en sigma.

## Tasques

- [ ] Implementar luminància CIE i respostes espectrals/FOV versionades de SQM/TESS.
- [ ] Implementar zero points/calibratge només des de fonts documentades.
- [ ] Comparar cada projecció contra integració espectral/focal fina.
- [ ] Propagar l’error espectral a la projecció.
- [ ] Revalidar el pressupost de discretització `0,01 mag` de [7.4](../../evidencies/pas7.4/criteri-preregistrat-v1.json) sobre les respostes SQM/TESS/CIE realment implementades. Si falla, versionar i rehomologar el `SpectralBandSet`, sense relaxació retroactiva.
- [ ] Justificar i preregistrar qualsevol tolerància de projecció pròpia abans de comparar el candidat amb l'oracle, amb incertesa de resposta/FOV i error espectral pertinents.
- [ ] Mantenir `BortleEquivalent` com a diagnòstic versionat i mai com a ground truth.
- [ ] Projectar radiància de SPD, interpolacions Kelvin i mescles sense perdre la normalització de comparació ni el suport; revalidar 0,01 mag contra l’oracle fi per resposta CIE/SQM/TESS.

## Criteri de sortida

SQM/TESS/CIE coincideixen amb oracles de projecció dins toleràncies justificades i preregistrades a 7.14 abans de la comparació decisòria; sense aquestes toleràncies, 7.14 es bloqueja. La discretització també compleix el criteri heretat de 7.4 en aquest domini nou o el bandset es versiona i rehomologa. Cap projecció modifica la radiància física.

## Proves i evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.14/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.
- [ ] Verificar el nou abast S/C i les modalitats realista/K amb casos independents; H conserva el seu contrast empíric.

**Resultats verificats:** aquest pas encara no s’ha executat; les proves de configuració/font corresponen a 7.5.1.

## Fora d'abast

Homologar H sense observacions; fabricar fonts o radiància; modificar llindars després dels resultats.

## Instrucció per a Codex

No ajustis el SourceModel ni el kernel perquè una lectura SQM concreta coincideixi.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.

Aplicar la política de referència RSR i dominis vigent; no reobrir la cerca anual exacta com a prerequisit global. No declarar la propagació implementada a partir dels controls de 7.5.1.

## Treball pendent

- [ ] Executar les tasques i demostrar el criteri de sortida d’aquest pas. La connexió gràfica final de kelvins continua obligatòria fins a 7.27.
