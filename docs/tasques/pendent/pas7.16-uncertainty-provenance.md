# Pas 7.16 — Skyglow físic — Incertesa quantitativa i provenance completa

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Consumir els escenaris C ja executables de 7.5.1; propagar sensibilitat RSR LGS/MGS, SPD, mescles, normalització, angles i escala fins a les projeccions. Una dispersió d’alternatives no és sigma; registrar les incerteses no quantificades.

## Descripció funcional

Construir intervals i components d’error després que font, atmosfera i transport ja tinguin models concrets.

## Fonts a consultar

- [09-incertesa-proveniencia.md](../../skyglow/09-incertesa-proveniencia.md)
- [08-validacio-cientifica.md](../../skyglow/08-validacio-cientifica.md)

**Ampliació executiva del domini C:** estudiar VJ146A2.002/NOAA-20 amb RSR de prelanzament com a referència **condicionada**, priors SPD/angular, mapping de guany i relació TOA/L3 identificats com a verificats o desconeguts. Quantificar sensibilitat o retornar `absoluteCalibrationStatus=unavailable`, mai inferir flux hemisfèric únic. Construir el ledger d’incertesa de S/C perquè l'absència d'H no freni el transport. [Política](../../skyglow/20-politica-rsr-i-validacio-per-dominis.md).

Fonts locals del pla vigent consultades el 2026-10-18; cap asset no es declara validat només per una referència.

## Objectiu

Consumir els escenaris C ja executables de 7.5.1; propagar sensibilitat RSR LGS/MGS, SPD, mescles, normalització, angles i escala fins a les projeccions. Una dispersió d’alternatives no és sigma; registrar les incerteses no quantificades.

## Dependències

**Depèn de:**
- [Pas 7.15](pas7.15-atmos-era5-cams.md)
- [Pas 7.5](../completat/pas7.5-source-model-v1.md)
- [Pas 7.3](../completat/pas7.3-dnb-rsr-measurement.md)
- [Pas 7.5.1](../completat/pas7.5.1-black-marble-spectral-simulation.md)

**En depenen:**
- [Pas 7.17](pas7.17-clear-sky-ground-truth.md)

## Codi existent a reutilitzar

- **Repositori actual:** [SourceModel S/C](../../../backend/src/terralab3d/domain/light_pollution/source_model.py), [escenaris i configuració](../../../backend/src/terralab3d/domain/light_pollution/simulation.py), [biblioteca](../../../backend/src/terralab3d/domain/light_pollution/spectral_library.py) i [controls](../../../frontend/src/view/ui/components/SkyglowControls.ts). Reutilitzar els contractes sense duplicar el motor.
- **Projectes de referència autoritzats:** cap runtime extern; els oracles científics independents han de tenir fonts i llicències verificades abans d’incorporar-los.

## Flux tècnic

Configuració versionada + SourceModel S/C + procedència → component del pas → sortida amb unitats, revisió i qualificació pròpies. Consumir els escenaris C ja executables de 7.5.1; propagar sensibilitat RSR LGS/MGS, SPD, mescles, normalització, angles i escala fins a les projeccions. Una dispersió d’alternatives no és sigma; registrar les incerteses no quantificades.

## Errors, cancel·lació i recursos

Previst: rebutjar entrades no finites, unitats i revisions incompatibles; cancel·lació cooperativa, latest-wins i descart de resultats antics. Recursos grans persistents fora del JSON de cada frame; alliberament explícit pel propietari. RSR de referència C no es promou a H; incertesa desconeguda no es converteix en sigma.

## Abast fotomètric vigent

Les projeccions CIE/AB de referència del [7.14A](../completat/pas7.14a-projeccions-cie-ab.md) només poden propagar incertesa als dominis acreditats. Sense [7.14B](pas7.14b-perfils-instrumentals-sqm-tess.md), SQM/TESS continua `unavailable`; cap sigma inventada ni bloqueig del ledger S/C.

## Tasques

**Obligatòries per al criteri de sortida S/C:**

- [ ] Implementar `UncertaintyModelRegistry` i `Provenance` dels resultats físics S/C, separant error numèric, atmosfera, font i model estructural.
- [ ] Representar absència de sigma amb `unavailable`; mai derivar-lo d'una etiqueta de confiança ni usar un valor inventat.
- [ ] Propagar incerteses conegudes fins a radiància i projeccions de S/C; documentar correlacions quan siguin materials, biaixos i domini.
- [ ] Generar un ledger per resultat S/C, amb identitat d'inputs, revisions de model i hipòtesis.
- [ ] Demostrar amb tests que la branca S no exigeix RSR, ni producte Black Marble, ni una inversió L3→emissió.

**Homologació H addicional, separada de la simulació S/C:**

- [ ] Investigar la parella NOAA-20 VJ146A2.002 + RSR pública de referència, el mode nocturn, el mapping de guany i la semàntica TOA→L3; registrar precisament què no és verificable.
- [ ] Ampliar els escenaris C de 7.5.1 amb dades auxiliars verificades quan existeixin; mantenir ensembles deterministes sense probabilitats ni precisió absoluta fictícies.
- [ ] Si no hi ha evidència per H, publicar H `not_evaluated` amb causes; mantenir C relatiu executable sense falsificar PASS ni retocar la font per obtenir una escala absoluta.
- [ ] Consumir els escenaris C ja executables de 7.5.1; propagar sensibilitat RSR LGS/MGS, SPD, mescles, normalització, angles i escala fins a les projeccions. Una dispersió d’alternatives no és sigma; registrar les incerteses no quantificades.

## Criteri de sortida

Cada resultat S/C identifica incertesa numèrica/física i les absències de dades; C preserva els escenaris condicionats executables de 7.5.1 amb incertesa no quantificada quan correspongui sense sigmes ni amplituds fictícies; H exigeix evidència externa. La manca de RSR 2026 no impedeix acabar el ledger físic S.

## Proves i evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.16/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.
- [ ] Verificar el nou abast S/C i les modalitats realista/K amb casos independents; H conserva el seu contrast empíric.

**Resultats verificats:** aquest pas encara no s’ha executat; les proves de configuració/font corresponen a 7.5.1.

## Fora d'abast

Homologar H sense observacions; fabricar fonts o radiància; modificar llindars després dels resultats.

## Instrucció per a Codex

No amaguis una incertesa estructural dins el residual de validació.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.

Aplicar la política de referència RSR i dominis vigent; no reobrir la cerca anual exacta com a prerequisit global. No declarar la propagació implementada a partir dels controls de 7.5.1.

## Treball pendent

- [ ] Executar les tasques i demostrar el criteri de sortida d’aquest pas. La connexió gràfica final de kelvins continua obligatòria fins a 7.27.
