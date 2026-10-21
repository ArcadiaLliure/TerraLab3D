# Pas 7.14 — Skyglow físic — Projeccions fotomètriques i sensors SQM/TESS

> **Estat:** pendent, bloquejat científicament (`BLOCKED_NOMINAL_RESPONSE_OR_COVERAGE`). **Estat funcional:** parcial, observable offline. **Origen:** planificat. **Abast vigent:** retenció espectral al mateix kernel, CIE, bandes de referència i integració de FOV nominal verificats numèricament. Coordenades CIE aire/buit resoltes explícitament; perfils nominals SQM/TESS i cobertura suficient encara sense acreditar. Calibratge individual només per a prediccions natives, no com a prerequisit general nominal. **Punt de represa: aquest pas; no executar 7.15.**

## Descripció funcional

Projectar les dades espectrals retingudes sense repetir el transport ni alterar la normalització de les fonts. CIE produeix luminància del component artificial modelat en cd/m² per a S i senyal fotòpic relatiu per a C. Les bandes condicionades SQM/TESS són diagnòstics; les lectures natives retornen `unavailable` amb motiu. El [gate vigent](../../evidencies/pas7.14/represa-v3/gate-represa-v3.json) distingeix PASS numèric de sortida científica bloquejada.

## Fonts a consultar

- [06-contractes-dades.md](../../skyglow/06-contractes-dades.md)
- [08-validacio-cientifica.md](../../skyglow/08-validacio-cientifica.md)
- [Pla canònic, apartat 7.14](../../skyglow/19-pla-executable-codex.md)
- [Fonts científiques, llicències i límits instrumentals](../../evidencies/pas7.14/fonts-i-models-instrumentals.md): CIE, BIPM, Bará/Tapia/Zamorano2019, SVO/Cinzano2005 i mesures TESS-W LICA2024 amb commits fixats.

Fonts locals i primàries consultades el2026-10-19 i ampliades a la [represa2026-10-20](../../evidencies/pas7.14/represa-v2/fonts-i-qualificacio-v2.md); dades i llicències arxivades amb SHA-256. Cap referència bibliogràfica acredita per si sola un perfil instrumental complet.

## Objectiu

Projectar radiància de SPD, interpolacions Kelvin i mescles sense perdre la normalització de comparació ni el suport; revalidar 0,01 mag contra l’oracle fi per resposta CIE/SQM/TESS.

## Dependències

**Depèn de:**

- [Pas 7.13](../completat/pas7.13-dome-profile-direct.md)
- [Pas 7.4](../completat/pas7.4-spectral-bandset-validation.md)
- [Pas 7.5.1](../completat/pas7.5.1-black-marble-spectral-simulation.md)

**En depenen:**

- [Pas 7.15](pas7.15-atmos-era5-cams.md)

## Codi existent a reutilitzar

- **Repositori actual:** [kernel](../../../backend/src/terralab3d/domain/light_pollution/propagation_kernel.py), [transport espectral](../../../backend/src/terralab3d/domain/light_pollution/spectral_transport.py), [DomeProfile adaptatiu](../../../backend/src/terralab3d/domain/light_pollution/adaptive_dome.py), SourceModel S/C, catàleg CIE i SG-REF existents. La retenció optativa conserva geometria, DEM/ECEF/ENU, òptica, quadratures i límits. La ruta antiga sense retenció conserva els resultats i esquemes.
- **Implementació del pas:** [projeccions](../../../backend/src/terralab3d/domain/photometric_projection.py), [aplicació](../../../backend/src/terralab3d/application/photometric_projections.py) i [CLI de postprocessament](../../../tools/project_skyglow_photometry.py). Cap canvi al bridge de producte.
- **Projectes de referència autoritzats:** cap runtime extern; els oracles científics independents han de tenir fonts i llicències verificades abans d’incorporar-los.

## Flux tècnic

Respostes explícites → unió de nusos abans d’una sola avaluació del kernel → densitats per nm i estimacions LOS retingudes per panell → integració de les bandes → suma lineal de fonts compatibles → CIE o diagnòstic AB de referència. `project_retained` executa zero transports. S conserva W; C conserva la seva escala i només permet contrast entre escales compatibles. No es divideix un escalar CIE per reconstruir un espectre.

`cie_dome_luminance` reutilitza el camp validat de 7.13 multiplicant per 683 dins el seu domini. SQM/TESS no es dedueixen d’aquell escalar. La gaussiana nominal es normalitza en angle sòlid sobre l’hemisferi frontal complet; cobertura absent amb pes positiu implica indisponibilitat si no hi ha una cota de contribució suficient, sense retall ni renormalització arbitrària. COESA conserva 75 km i cota exterior positiva condicionada; DEM/àrea i zones sense garanties segueixen per transport directe.

## Errors, cancel·lació i recursos

Entrades no finites, unitats/escales incompatibles i nusos de resposta absents es rebutgen. Es comproven revisió, cancel·lació cooperativa i vigència abans de publicar; cap resultat parcial. Zero físic es conserva i una magnitud no finita retorna indisponibilitat, sense sòl artificial. Espectres retinguts només sota petició, sense dades per frame ni cache entre peticions. La incertesa LOS estimada es projecta linealment; espectre, cua atmosfèrica, resposta/FOV/calibratge i física es documenten per separat, sense sigma fictícia.

## Tasques

- [x] Implementar luminància CIE i motor de bandes/FOV amb identitat, unitats i disponibilitat explícites.
- [x] Implementar referència AB documentada (3631 Jy/arcsec²), contrastada amb Decimal50; rebutjar zero points natius desconeguts.
- [x] Comparar projeccions tabulades amb GL independent, transport amb SG-REF i FOV nominal amb integrals analítiques independents.
- [x] Retenir/projectar l’estimació LOS i separar el pressupost espectral preregistrat de les incerteses físiques i instrumentals.
- [x] Revalidar `0,01 mag` per a les finestres conegudes de les tres respostes: 10.624/10.624 PASS, màxim 0,000115197 mag. No homologa cues instrumentals desconegudes.
- [x] Separar projecció AB nominal, predicció nativa i observació: no exigir calibratge individual per defecte al model nominal.
- [x] Resoldre la coordenada CIE2019 amb aire estàndard450ppm, transformació de resposta/densitat diferenciada i jacobià verificat; preservar evidències heretades.
- [ ] Acreditar un perfil nominal SQM/TESS amb convenció de λ, resposta/cues i model òptic suficients. Les lectures natives afegeixen fosc/guany/zero point i domini tèrmic coherents.
- [ ] Revalidar el pressupost de discretització `0,01 mag` de [7.4](../../evidencies/pas7.4/criteri-preregistrat-v1.json) sobre les respostes SQM/TESS/CIE realment implementades. Si falla, versionar i rehomologar el `SpectralBandSet`, sense relaxació retroactiva.
- [x] Justificar i preregistrar toleràncies abans de comparar; els dos preregistres conserven el seu hash. Incertesa instrumental desconeguda explícita, fora del PASS numèric.
- [x] Mantenir `BortleEquivalent` separat: cap política nova acreditada, valor `None`; no convertir luminància o AB en Bortle.
- [x] Conservar SPD/K/mescles i escales S/C en les proves i campanyes; cap calibratge absolut C ni homologació H.
- [ ] Demostrar una projecció nominal SQM/TESS integrada sobre camp angular espectral amb cobertura suficient o cotes justificades; el CIE escalar i el domini 7.13 actuals no ho acrediten.

## Criteri de sortida

SQM/TESS/CIE coincideixen amb oracles de projecció dins toleràncies justificades i preregistrades a 7.14 abans de la comparació decisòria; sense aquestes toleràncies, 7.14 es bloqueja. La discretització també compleix el criteri heretat de 7.4 en aquest domini nou o el bandset es versiona i rehomologa. Cap projecció modifica la radiància física.

## Proves i evidències obligatòries

- [x] Candidat inicial:19 proves noves/514 backend. Represa:26 proves noves/540 backend, frontend/typecheck/build superats; pressupost0,01mag preservat.
- [x] B0 i quatre columnes exactes; Pyright global conserva el mateix multiconjunt de 67 errors/3 avisos heretats. Abast afectat amb configuració relativa: zero errors/avisos.
- [x] Evidència reproduïble, dades crues, costos i tres figures sota `docs/evidencies/pas7.14/`.
- [x] README/inventari/manual/normes/planning coherents amb l’estat parcial bloquejat.
- [x] Cap capacitat posterior anticipada; 7.15 i acceleracions 7.18–7.22 sense executar.
- [x] Abast S/C realista/K verificat en fixtures independents; no requalificar H.

**Execució 2026-10-19:** [informe](../../evidencies/pas7.14/validacio-projeccions.md), [gate](../../evidencies/pas7.14/gate-projeccions-v1.json), [preregistre principal](../../evidencies/pas7.14/criteri-projeccions-preregistrat-v1.json) i [espectral](../../evidencies/pas7.14/criteri-espectral-sensors-preregistrat-v1.json). 39 contrasts SG-REF PASS (màxim relatiu protegit 9,890·10⁻⁷ davant 10⁻⁴), sis controls FOV i 319 evidències històriques intactes. Cost científic 272,718 s, incloent un intent aturat abans de cap LOS. Control COESA: 183,393 s de kernel; projeccions: 3,06–5,11 ms/LOS, zero transport addicional. Auditories històriques 7.13 repetides en checkout aïllat amb codi/hashes originals, sense confondre-les amb regressions actuals.

**Represa2026-10-20:** [informe v2](../../evidencies/pas7.14/represa-v2/validacio-represa-v2.md), [fonts primàries](../../evidencies/pas7.14/represa-v2/fonts-i-qualificacio-v2.md) i [gate](../../evidencies/pas7.14/represa-v2/gate-represa-v2.json).21.184 contrasts espectrals,55 controls de flux i13 postprojeccions PASS.449 evidències anteriors preservades;179,850s, zero LOS noves.

**Represa 2026-10-21:** [informe v3](../../evidencies/pas7.14/represa-v3/validacio-represa-v3.md), [fonts, mancances i vies de dades](../../evidencies/pas7.14/represa-v3/fonts-mancances-i-vies-v3.md) i [gate](../../evidencies/pas7.14/represa-v3/gate-represa-v3.json). SQM-L GD/CM500, família BK7/UVIR650 i lots TESS-W diferenciats; cap perfil nou adoptat. Fuites IR i cues angulars impedeixen acreditar el producte ideal o la gaussiana com a cota instrumental. Perfilatge de 13 projeccions: 14,625 s, zero LOS noves; 2.904 reconstruccions GL en una projecció de 968 panells expliquen el cost. 540 proves backend i regressions PASS, 576 evidències anteriors i 99 fonts intactes. La represa requereix dades noves identificades, sense repetir cerques genèriques.

**Bloqueig vigent:** perfil nominal SQM/TESS encara sense convenció de λ i cues acotades, i camp/cobertura del FOV insuficients. La manca de calibratge individual no bloqueja per si sola un model nominal AB. La coordenada CIE s’ha resolt prospectivament; les convencions de laboratori desconegudes es mantenen explícites. No s’han convertit absències en zero ni s’han relaxat llindars.

## Fora d'abast

Homologar H sense observacions; fabricar fonts, calibratge, fosc o radiància; modificar llindars després dels resultats; ampliar homologació angular COESA/DEM/àrea; noves acceleracions, multicore, Three.js definitiu o qualsevol treball de 7.15.

## Instrucció per a Codex

No ajustis el SourceModel ni el kernel perquè una lectura SQM concreta coincideixi.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.

Aplicar la política de referència RSR i dominis vigent; no reobrir la cerca anual exacta com a prerequisit global. No declarar la propagació implementada a partir dels controls de 7.5.1.

## Treball pendent

- [x] Investigar les pistes primàries específiques SQM-L/TESS-W i documentar configuracions, annexos, dades mancants i vies per obtenir-les, sense empalmar lots ni exigir calibratge individual nominal.
- [x] Perfilar el cost de postprojecció sobre espectres retinguts, sense modificar el candidat ni anticipar acceleracions.
- [ ] Obtenir les dades concretades al [registre de mancances v3](../../evidencies/pas7.14/represa-v3/perfils-candidats-i-mancances-v3.json); seleccionar un nominal òptic coherent amb convenció de λ i suport/cues i FOV acotats abans d’una nova campanya. No repetir les cerques tancades sense novetat; preregistrar domini, criteris i cost. Conservar aquest candidat i els preregistres. Tancar només amb el criteri científic íntegre demostrat. La connexió gràfica final de kelvins continua a 7.27.
