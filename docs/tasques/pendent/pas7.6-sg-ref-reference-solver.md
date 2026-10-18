# Pas 7.6 — Skyglow físic — SG-REF: oracle independent de transport i integració d’àrea

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Propagar fonts S i C de 7.5.1 amb el mateix oracle; conservar unitats relatives C, hipòtesis i etiqueta de domini, sense exigir H ni equivalència RSR anual exacta.

## Descripció funcional

Crear una veritat numèrica offline més estricta que el runtime i independent de les seves aproximacions.

## Fonts a consultar

- [01-especificacio-algorismes.md](../../skyglow/01-especificacio-algorismes.md)
- [04-justificacio-cientifica.md](../../skyglow/04-justificacio-cientifica.md)
- [08-validacio-cientifica.md](../../skyglow/08-validacio-cientifica.md)

Fonts locals del pla vigent consultades el 2026-10-18; cap asset no es declara validat només per una referència.

## Objectiu

Propagar fonts S i C de 7.5.1 amb el mateix oracle; conservar unitats relatives C, hipòtesis i etiqueta de domini, sense exigir H ni equivalència RSR anual exacta.

## Dependències

**Depèn de:**
- [Pas 7.5](../completat/pas7.5-source-model-v1.md)
- [Pas 7.5.1](../completat/pas7.5.1-black-marble-spectral-simulation.md)

**En depenen:**
- [Pas 7.7](pas7.7-kernel-geometry-b0.md)

## Codi existent a reutilitzar

- **Repositori actual:** [SourceModel S/C](../../../backend/src/terralab3d/domain/light_pollution/source_model.py), [escenaris i configuració](../../../backend/src/terralab3d/domain/light_pollution/simulation.py), [biblioteca](../../../backend/src/terralab3d/domain/light_pollution/spectral_library.py) i [controls](../../../frontend/src/view/ui/components/SkyglowControls.ts). Reutilitzar els contractes sense duplicar el motor.
- **Projectes de referència autoritzats:** cap runtime extern; els oracles científics independents han de tenir fonts i llicències verificades abans d’incorporar-los.

## Flux tècnic

Configuració versionada + SourceModel S/C + procedència → component del pas → sortida amb unitats, revisió i qualificació pròpies. Propagar fonts S i C de 7.5.1 amb el mateix oracle; conservar unitats relatives C, hipòtesis i etiqueta de domini, sense exigir H ni equivalència RSR anual exacta.

## Errors, cancel·lació i recursos

Previst: rebutjar entrades no finites, unitats i revisions incompatibles; cancel·lació cooperativa, latest-wins i descart de resultats antics. Recursos grans persistents fora del JSON de cada frame; alliberament explícit pel propietari. RSR de referència C no es promou a H; incertesa desconeguda no es converteix en sigma.

## Tasques

- [ ] Implementar `SG-REF` amb toleràncies estrictes, convergència demostrada i integració directa d’àrea/raster de fonts.
- [ ] Evitar compartir amb el runtime codi d’aproximació que pugui produir errors correlacionats; compartir només contractes/constants autoritatives quan sigui segur.
- [ ] Afegir fases de referència d’alta resolució i ruta espectral fina per fixtures.
- [ ] Quantificar offline el biaix single-scattering (`F5`) en el domini v1 amb una referència més rica o oracle extern quan sigui necessari.
- [ ] Crear fixtures sintètiques analítiques i escenaris reproduïbles que seran consumits pels gates posteriors.
- [ ] Registrar convergència, incertesa numèrica i domini de SG-REF perquè 7.12 pugui justificar una tolerància sense usar resultats del runtime candidat.
- [ ] Propagar fonts S i C de 7.5.1 amb el mateix oracle; conservar unitats relatives C, hipòtesis i etiqueta de domini, sense exigir H ni equivalència RSR anual exacta.

## Criteri de sortida

`S1` és executable: SG-REF demostra convergència i incertesa numèrica i pot comparar radiància espectral per direcció i fonts extenses sense quadtree, cache ni LUT de runtime. El PASS/FAIL del runtime queda per a 7.12.

## Proves i evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.6/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.
- [ ] Verificar el nou abast S/C i les modalitats realista/K amb casos independents; H conserva el seu contrast empíric.

**Resultats verificats:** aquest pas encara no s’ha executat; les proves de configuració/font corresponen a 7.5.1.
- [ ] Verificar el nou abast S/C i les modalitats realista/K amb casos independents; H conserva el seu contrast empíric.

**Resultats verificats:** aquest pas encara no s’ha executat; les proves de configuració/font corresponen a 7.5.1.

## Fora d'abast

Homologar H sense observacions; fabricar fonts o radiància; modificar llindars després dels resultats.

## Instrucció per a Codex

L’oracle no és una versió “més lenta” del mateix codi aproximat. Si comparteixes una aproximació crítica, documenta per què no invalida la independència.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.

Aplicar la política de referència RSR i dominis vigent; no reobrir la cerca anual exacta com a prerequisit global. No declarar la propagació implementada a partir dels controls de 7.5.1.

Aplicar la política de referència RSR i dominis vigent; no reobrir la cerca anual exacta com a prerequisit global. No declarar la propagació implementada a partir dels controls de 7.5.1.

## Treball pendent

- [ ] Executar les tasques i demostrar el criteri de sortida d’aquest pas. La connexió gràfica final de kelvins continua obligatòria fins a 7.27.
