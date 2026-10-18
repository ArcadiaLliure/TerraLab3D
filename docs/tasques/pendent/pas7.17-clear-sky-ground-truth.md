# Pas 7.17 — Skyglow físic — Validació empírica clear-sky de SourceModel i transport

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Separar gate físic S/C del transport i contrast empíric H. Els C relatius poden validar invariants i sensibilitat amb SG-REF; una predicció absoluta urbana continua exigint observacions independents i criteris preregistrats.

## Descripció funcional

Contrastar el sistema físic directe amb observacions externes abans de qualsevol acceleració espacial o cache.

## Fonts a consultar

- [08-validacio-cientifica.md](../../skyglow/08-validacio-cientifica.md)
- [09-incertesa-proveniencia.md](../../skyglow/09-incertesa-proveniencia.md)

**Separació obligatòria:** (1) gate numèric/físic preacceleracions S amb fonts definides i oracle independent, criteris justificats/preregistrats, permet 7.18 en els dominis de transport S/C verificats; (2) gate empíric observacional C/H amb ground truth extern i `held-out`, criteris i incerteses preregistrats. Si (2) no és avaluable, registrar `not_evaluated`, no PASS; no impedir la continuació de S/C condicionat. Un oracle numèric no és una observació empírica. [Política](../../skyglow/20-politica-rsr-i-validacio-per-dominis.md).

Fonts locals del pla vigent consultades el 2026-10-18; cap asset no es declara validat només per una referència.

## Objectiu

Separar gate físic S/C del transport i contrast empíric H. Els C relatius poden validar invariants i sensibilitat amb SG-REF; una predicció absoluta urbana continua exigint observacions independents i criteris preregistrats.

## Dependències

**Depèn de:**
- [Pas 7.16](pas7.16-uncertainty-provenance.md)
- [Pas 7.5](../completat/pas7.5-source-model-v1.md)
- [Pas 7.3](../completat/pas7.3-dnb-rsr-measurement.md)
- [Pas 7.5.1](../completat/pas7.5.1-black-marble-spectral-simulation.md)

**En depenen:**
- [Pas 7.18](pas7.18-source-spatial-acceleration.md)

## Codi existent a reutilitzar

- **Repositori actual:** [SourceModel S/C](../../../backend/src/terralab3d/domain/light_pollution/source_model.py), [escenaris i configuració](../../../backend/src/terralab3d/domain/light_pollution/simulation.py), [biblioteca](../../../backend/src/terralab3d/domain/light_pollution/spectral_library.py) i [controls](../../../frontend/src/view/ui/components/SkyglowControls.ts). Reutilitzar els contractes sense duplicar el motor.
- **Projectes de referència autoritzats:** cap runtime extern; els oracles científics independents han de tenir fonts i llicències verificades abans d’incorporar-los.

## Flux tècnic

Configuració versionada + SourceModel S/C + procedència → component del pas → sortida amb unitats, revisió i qualificació pròpies. Separar gate físic S/C del transport i contrast empíric H. Els C relatius poden validar invariants i sensibilitat amb SG-REF; una predicció absoluta urbana continua exigint observacions independents i criteris preregistrats.

## Errors, cancel·lació i recursos

Previst: rebutjar entrades no finites, unitats i revisions incompatibles; cancel·lació cooperativa, latest-wins i descart de resultats antics. Recursos grans persistents fora del JSON de cada frame; alliberament explícit pel propietari. RSR de referència C no es promou a H; incertesa desconeguda no es converteix en sigma.

## Tasques

**Gate S obligatori per autoritzar acceleracions:**

- [ ] Registrar abans de la comparació un pressupost d'error físic/numèric, mètriques, domini de fonts S, referència independent i criteris amb procedència.
- [ ] Comparar SG-REF/ruta directa contra casos analítics o altres oracles independents, sense reutilitzar la mateixa aproximació crítica.
- [ ] Verificar transport zenital/all-sky, projeccions i invariants per fonts S del domini aprovat, incloent casos adversos.
- [ ] Documentar PASS/FAIL S amb evidència reproduïble; una fallada obliga a reparar el model físic, mai a relaxar retrospectivament el pressupost.
- [ ] Permetre 7.18 dins els dominis de transport S/C realment validats, amb homologació empírica H separada.

**Gate empíric C/H separat, no bloquejant si encara no és avaluable:**

- [ ] Preparar, si hi ha dades adequades, observacions externes TESS/SQM/all-sky i estratificació per plataforma/lloc/data; mantenir metadata i prevenir filtració de dades.
- [ ] Preregistrar criteris empírics, incertesa i partició `held-out` abans d'avaluar, amb leave-one-site-out o equivalent, sense reajustar al conjunt reservat.
- [ ] Contrastar explícitament la inferència L3→font/transport quan C sigui avaluable; si no, deixar `not_evaluated` documentat, **no** un PASS ni un obstacle al gate S.
- [ ] Separar gate físic S/C del transport i contrast empíric H. Els C relatius poden validar invariants i sensibilitat amb SG-REF; una predicció absoluta urbana continua exigint observacions independents i criteris preregistrats.

## Criteri de sortida

El gate S contra oracle físic independent supera els criteris preregistrats i només habilita acceleracions S. Els criteris empírics C/H precedeixen l'avaluació `held-out` i no s'ajusten als residuals; absència de dades C/H implica `not_evaluated`, sense frenar acceleracions S ni declarar skyglow Black Marble homologat.

## Proves i evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.17/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.
- [ ] Verificar el nou abast S/C i les modalitats realista/K amb casos independents; H conserva el seu contrast empíric.

**Resultats verificats:** aquest pas encara no s’ha executat; les proves de configuració/font corresponen a 7.5.1.

## Fora d'abast

Homologar H sense observacions; fabricar fonts o radiància; modificar llindars després dels resultats.

## Instrucció per a Codex

Aquest pas valida el model contra el món real. Mantén separats error de font, atmosfera, transport i sensor.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.

Aplicar la política de referència RSR i dominis vigent; no reobrir la cerca anual exacta com a prerequisit global. No declarar la propagació implementada a partir dels controls de 7.5.1.

## Treball pendent

- [ ] Executar les tasques i demostrar el criteri de sortida d’aquest pas. La connexió gràfica final de kelvins continua obligatòria fins a 7.27.
