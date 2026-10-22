# Pas 7.24 — Skyglow físic — Validació empírica final clear/cloudy i congelació de model

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Contrastar el transport final en S i C, incloent comparacions Kelvin i ensemble realista; publicar estats per domini i incerteses. Homologació empírica H separada, sense ocultar el resultat C plausible.

## Descripció funcional

Repetir la validació del sistema ja optimitzat i amb núvols abans d’integrar-lo al renderer.

## Fonts a consultar

- [08-validacio-cientifica.md](../../skyglow/08-validacio-cientifica.md)
- [09-incertesa-proveniencia.md](../../skyglow/09-incertesa-proveniencia.md)

Fonts locals del pla vigent consultades el 2026-10-18; cap asset no es declara validat només per una referència.

## Objectiu

Contrastar el transport final en S i C, incloent comparacions Kelvin i ensemble realista; publicar estats per domini i incerteses. Homologació empírica H separada, sense ocultar el resultat C plausible.

## Dependències

**Depèn de:**
- [Pas 7.23](pas7.23-clouds-b6.md)
- [Pas 7.5.1](../completat/pas7.5.1-black-marble-spectral-simulation.md)

**En depenen:**
- [Pas 7.25](pas7.25-bridge-runtime.md)

## Codi existent a reutilitzar

- **Repositori actual:** [SourceModel S/C](../../../backend/src/terralab3d/domain/light_pollution/source_model.py), [escenaris i configuració](../../../backend/src/terralab3d/domain/light_pollution/simulation.py), [biblioteca](../../../backend/src/terralab3d/domain/light_pollution/spectral_library.py) i [controls](../../../frontend/src/view/ui/components/SkyglowControls.ts). Reutilitzar els contractes sense duplicar el motor.
- **Projectes de referència autoritzats:** cap runtime extern; els oracles científics independents han de tenir fonts i llicències verificades abans d’incorporar-los.

## Flux tècnic

Configuració versionada + SourceModel S/C + procedència → component del pas → sortida amb unitats, revisió i qualificació pròpies. Contrastar el transport final en S i C, incloent comparacions Kelvin i ensemble realista; publicar estats per domini i incerteses. Homologació empírica H separada, sense ocultar el resultat C plausible.

## Errors, cancel·lació i recursos

Previst: rebutjar entrades no finites, unitats i revisions incompatibles; cancel·lació cooperativa, latest-wins i descart de resultats antics. Recursos grans persistents fora del JSON de cada frame; alliberament explícit pel propietari. RSR de referència C no es promou a H; incertesa desconeguda no es converteix en sigma.

## Sensors després de 7.14A/7.14B

El gate original 7.14 continua `BLOCKED_NOMINAL_RESPONSE_OR_COVERAGE`. [7.14A](../completat/pas7.14a-projeccions-cie-ab.md) només és CIE/AB de referència; [7.14B](pas7.14b-perfils-instrumentals-sqm-tess.md) no homologat. Les afirmacions empíriques que necessitin SQM/TESS han de quedar `not_evaluated` si falta el seu perfil; no bloquejar el gate físic S.

## Tasques

- [ ] Reexecutar clear-sky per demostrar que acceleracions 7.18–7.22 no han degradat la validesa.
- [ ] Afegir subset cloudy només dins el domini de 7.23 amb metadata suficient, per a fonts S verificades; el fet de simular núvols no demostra calibratge observacional C/H.
- [ ] Validar intervals d’incertesa, cobertura i biaixos per sensor/lloc/condició.
- [ ] Separar els resultats per plataforma Black Marble, producte, release i període; contrastar superposicions sense sumar radiàncies ni ampliar el domini d'una font amb dades d'una altra.
- [ ] Fer data-leakage checks i mantenir particions preregistrades **quan s'avalua una afirmació C/H**; si no hi ha campanya empírica, registrar `not_evaluated` en lloc de marcar fals PASS.
- [ ] Congelar versions de producte, SourceModel, atmosfera, phase/backend i criteris que passin.

- [ ] Informar S (simulació física, gates propis), C (escenari condicionat) i H (validació empírica independent) per separat; sense H, cap «skyglow urbà absolut real» homologat.
- [ ] Si les dades C/H no permeten validació, registrar `not_evaluated`/`unavailable`; permetre la integració del motor S només amb etiqueta de simulació.
- [ ] Contrastar el transport final en S i C, incloent comparacions Kelvin i ensemble realista; publicar estats per domini i incerteses. Homologació empírica H separada, sense ocultar el resultat C plausible.

## Criteri de sortida

Existeix informe reproduïble dels gates físics S i, quan hi hagi dades, informes empírics C/H separats. Si C/H no es pot validar, roman explícitament no homologat mentre S pot continuar com a simulació. Els núvols només es qualifiquen al domini provat.

## Proves i evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.24/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.
- [ ] Verificar el nou abast S/C i les modalitats realista/K amb casos independents; H conserva el seu contrast empíric.

**Resultats verificats:** aquest pas encara no s’ha executat; les proves de configuració/font corresponen a 7.5.1.

## Fora d'abast

Homologar H sense observacions; fabricar fonts o radiància; modificar llindars després dels resultats.

## Instrucció per a Codex

No ampliïs el domini per màrqueting. Homologa només el que les dades suporten.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.

Aplicar la política de referència RSR i dominis vigent; no reobrir la cerca anual exacta com a prerequisit global. No declarar la propagació implementada a partir dels controls de 7.5.1.

## Treball pendent

- [ ] Executar les tasques i demostrar el criteri de sortida d’aquest pas. La connexió gràfica final de kelvins continua obligatòria fins a 7.27.
