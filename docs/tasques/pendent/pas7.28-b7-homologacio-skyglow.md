# Pas 7.28 — Skyglow físic — B7 FULL, SLO i homologació del skyglow artificial

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Homologar les dues modalitats i la UI per dominis S/C/H, amb criteris congelats. Una simulació realista plausible C es presenta com a condicionada; cap precisió absoluta H per herència del PASS numèric.

## Descripció funcional

Tancar la vertical només després que ciència, rendiment i integració hagin passat gates independents.

## Fonts a consultar

- [07-benchmark-b0-b7.md](../../skyglow/07-benchmark-b0-b7.md)
- [08-validacio-cientifica.md](../../skyglow/08-validacio-cientifica.md)
- [16-auditoria.md](../../skyglow/16-auditoria.md)

Fonts locals del pla vigent consultades el 2026-10-18; cap asset no es declara validat només per una referència.

## Objectiu

Homologar les dues modalitats i la UI per dominis S/C/H, amb criteris congelats. Una simulació realista plausible C es presenta com a condicionada; cap precisió absoluta H per herència del PASS numèric.

## Dependències

**Depèn de:**
- [Pas 7.27](pas7.27-sky-composition.md)
- [Pas 7.5.1](../completat/pas7.5.1-black-marble-spectral-simulation.md)

**En depenen:**
- [Pas 38](pas38-homologacio-final.md)

## Codi existent a reutilitzar

- **Repositori actual:** [SourceModel S/C](../../../backend/src/terralab3d/domain/light_pollution/source_model.py), [escenaris i configuració](../../../backend/src/terralab3d/domain/light_pollution/simulation.py), [biblioteca](../../../backend/src/terralab3d/domain/light_pollution/spectral_library.py) i [controls](../../../frontend/src/view/ui/components/SkyglowControls.ts). Reutilitzar els contractes sense duplicar el motor.
- **Projectes de referència autoritzats:** cap runtime extern; els oracles científics independents han de tenir fonts i llicències verificades abans d’incorporar-los.

## Flux tècnic

Configuració versionada + SourceModel S/C + procedència → component del pas → sortida amb unitats, revisió i qualificació pròpies. Homologar les dues modalitats i la UI per dominis S/C/H, amb criteris congelats. Una simulació realista plausible C es presenta com a condicionada; cap precisió absoluta H per herència del PASS numèric.

## Errors, cancel·lació i recursos

Previst: rebutjar entrades no finites, unitats i revisions incompatibles; cancel·lació cooperativa, latest-wins i descart de resultats antics. Recursos grans persistents fora del JSON de cada frame; alliberament explícit pel propietari. RSR de referència C no es promou a H; incertesa desconeguda no es converteix en sigma.

## Abast instrumental final

La [partició de 7.14](../../skyglow/22-revisio-dependencies-7.14-7.15.md) manté l'original bloquejat, [7.14A CIE/AB](../completat/pas7.14a-projeccions-cie-ab.md) limitada a fixtures i [7.14B SQM/TESS](pas7.14b-perfils-instrumentals-sqm-tess.md) pendent. Si 7.14B encara no ha superat un gate propi, **B7 no pot publicar lectures SQM/TESS com homologades**, i les ha d'etiquetar `unavailable/not_evaluated`. La comparació Falchi és model contra model, no H ni homologació instrumental.

## Tasques

- [ ] Executar B7 amb AD OFF/ON, uncertainty OFF/ON, cold/warm/movement/prefetch/teleport/tile-change/occlusion-flip i backend 7.22 si existeix.
- [ ] Auditar DATA-VNP46 històric i DATA-MULTISAT, DNB-TOA-L3, F1, F5, F7, V1, V3, S1, DNB-2017 i LOW-RAD **per cada plataforma/producte/release/període declarat**, sense exigir homologació de sensors fora de l'abast publicat.
- [ ] Verificar la procedència, versió i congelació prèvia de tots els criteris PASS/FAIL aplicables; consumir-los sense crear-ne ni modificar-ne cap a 7.28.
- [ ] Reexecutar gate zenital, regressions all-sky, projeccions i validació empírica congelada.
- [ ] Verificar `kernelIntegralsPerRenderFrame=0`, stutter i memòria segons els SLO de producte aprovats, i lifecycle.
- [ ] Decidir shadow/default i retirar només els fallbacks que l’evidència autoritza; actualitzar inventari, README i evidències finals.

- [ ] Auditar resultats i UI per domini S/C/H; completar S no implica validar un skyglow urbà absolut C/H.
- [ ] Homologar les dues modalitats i la UI per dominis S/C/H, amb criteris congelats. Una simulació realista plausible C es presenta com a condicionada; cap precisió absoluta H per herència del PASS numèric.

## Criteri de sortida

Els resultats es completen per domini: S pot ser simulació física verificada per B7; C es publica només com a condicionat; H exigeix incertesa/validació empírica i producte/release/període/QA comprovats. Sense H no es declara cap predicció Black Marble absoluta homologada. SQM/TESS només s'homologuen si 7.14B té evidència suficient; altrament, queden `unavailable/not_evaluated` sense impedir S/C acreditat. No crear o modificar llindars a 7.28.

## Proves i evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.28/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.
- [ ] Verificar el nou abast S/C i les modalitats realista/K amb casos independents; H conserva el seu contrast empíric.

**Resultats verificats:** aquest pas encara no s’ha executat; les proves de configuració/font corresponen a 7.5.1.

## Fora d'abast

Homologar H sense observacions; fabricar fonts o radiància; modificar llindars després dels resultats.

## Instrucció per a Codex

Consumeix només criteris ja congelats; no creïs ni modifiquis llindars a 7.28 o després de veure B7. No homologuis una acceleració perquè sigui ràpida ni una font perquè runtime i SG-REF coincideixin.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.

Aplicar la política de referència RSR i dominis vigent; no reobrir la cerca anual exacta com a prerequisit global. No declarar la propagació implementada a partir dels controls de 7.5.1.

## Treball pendent

- [ ] Executar les tasques i demostrar el criteri de sortida d’aquest pas. La connexió gràfica final de kelvins continua obligatòria fins a 7.27.
