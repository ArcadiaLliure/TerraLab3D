# Pas 7.12 — Gate zenital de transport radiomètric

> **Estat:** completat. **Estat funcional:** observable offline, gate numèric verificat en domini condicionat. **Origen:** planificat. **Abast vigent:** gate numèric del mateix transport directe, amb SourceModel i camp/DEM explícits; sense 7.13.

## Descripció funcional

Validar el transport complet abans de cúpules, compressions o caches. El mateix kernel calcula 90° i les altres elevacions; el PASS no acredita inferència urbana C/H ni observacions.

## Fonts a consultar

- [Pla canònic](../../skyglow/19-pla-executable-codex.md), [benchmarks](../../skyglow/07-benchmark-b0-b7.md) i [validació científica](../../skyglow/08-validacio-cientifica.md), consultats.
- [Convergència i incertesa SG-REF de 7.6](../../evidencies/pas7.6/validacio-sg-ref.md) i [criteri espectral 0,01 mag](../../evidencies/pas7.4/criteri-preregistrat-v1.json), consultats com origen de la jerarquia de precisió.
- [NASA TR R-459](https://ntrs.nasa.gov/api/citations/19760017709/downloads/19760017709.pdf), taula 3 i equilibri hidrostàtic, consultats; PDF SHA-256 `b8d324cb4a22b4fe8bf73c00e230eed51cc89f6e8c2bdf7b8c9c5f2a905e712c`.

## Objectiu

Acreditar resolució numèrica dins del domini de fixtures registrades, amb radiància positiva, unitats, zero geomètric i errors separats. Resoldre o delimitar la contribució superior sense assumir-la nul·la a 50 km.

## Dependències

**Depèn de:**
- [7.11 — Terreny i visibilitat](../completat/pas7.11-terrain-curvature.md).

**En depenen:**
- [7.13 — DomeProfile directe](../pendent/pas7.13-dome-profile-direct.md), pendent i no executat.

## Codi existent a reutilitzar

- **Repositori actual:** REUSE SourceModel S/C, kernel B0/B1/B2/B4, OpticalField, geometria/DEM, fases i espectre. ADAPT provider COESA mitjançant ampliació optativa fins a 75 km, sense canviar 0–50 km. NEW SG-REF espectral variable independent, gate i cota exterior condicionada.
- **Projectes de referència autoritzats:** cap codi extern copiat; dades i formulació NASA amb atribució. La biblioteca DEM existent només es llegeix o es reprodueix des de la instantània arxivada.

## Flux tècnic

Preregistre immutable → fixtures i codi congelats → mateix kernel → SG-REF amb tres refinaments → llibre d’errors → PASS/FAIL per cas. El [criteri v1](../../evidencies/pas7.12/criteri-transport-preregistrat-v1.json), SHA-256 `6cfa6601f02dabeb1a3462638e980959c11a12164433738689efb31e92cdb442`, fixa 10⁻⁴ relatiu amb incertesa de referència ≤10⁻⁶; la cota exterior té pressupost independent de 0,001 mag. Cap llindar deriva del residual del candidat 7.12.

## Errors, cancel·lació i recursos

Referència no convergida, entrada fora del domini, cua no acotada o errors superiors al pressupost impedeixen PASS. Es conserven resultats fallits; no es relaxen llindars retrospectivament. Cancel·lació/revisió obsoleta del kernel conservades. El cost de fonts extenses es mesura sense acceleracions.

## Tasques

- [x] Preregistrar tolerància, mètrica, unitat i domini runtime↔SG-REF abans de veure el resultat PASS/FAIL del runtime candidat; justificar-los amb font admissible, incloses convergència i incertesa numèrica de SG-REF demostrades a 7.6.
- [x] Executar fixtures zenitals sintètiques amb SourceModel conegut contra SG-REF.
- [x] Executar fonts S definides puntuals i extenses del [Pas 7.5](../completat/pas7.5-source-model-v1.md), amb atmosfera estàndard i DEM reproduïble. Una fixture Black Marble C/H s'afegeix només si el seu domini observacional ja està acreditat; no és prerequisit del gate S.
- [x] Auditar cadena d’unitats, convergència, error numèric, memòria, nodes i dependències.
- [x] Separar explícitament l’error de transport de la incertesa del SourceModel.
- [x] Bloquejar qualsevol pas posterior si necessita un factor de calibratge opac o una ruta especial a 90°.

## Criteri de sortida

La tolerància runtime↔SG-REF està justificada i congelada abans de la comparació decisòria. El mateix PropagationKernel supera el domini declarat al zenit amb fonts S, atmosfera i DEM explícits, sense calibratge arbitrari. El PASS valida transport donat el SourceModel, no la inferència C/H. La cota exterior és condicionada a les hipòtesis físiques registrades; no és una garantia per a qualsevol exosfera real.

## Proves i evidències obligatòries

- [x] Preregistre i vinculació de candidat anteriors a la primera decisió.
- [x] Gate S puntual/extens, estàndard, curvatura, terreny i horitzó; compatibilitat C realista/K separada.
- [x] Convergència vertical i cota positiva de cua, amb hipòtesis explícites.
- [x] Errors de quadratura, espectre, interpolació P/T, DEM, sostre i física separats.
- [x] Proves, regressions B0–B4 i evidències històriques preservades.
- [x] Planning, inventari, manual, normes i enllaços coherents.

**Resultats verificats:** [informe final](../../evidencies/pas7.12/validacio-gate-transport.md), nou fixtures S PASS,42 sostres, cota exterior màxima 0,000472296 mag,444 proves (17 noves). Error màxim protegit 6,895·10⁻⁷ davant 10⁻⁴; pressupost espectral 0,01 mag mantingut, errors físics separats. B0/quatre columnes exactes i 163 evidències anteriors intactes. Cap calibratge, acceleració ni 7.13 iniciat.

## Fora d'abast

- 7.13, acceleracions, factors de calibratge, H i renderer de producte.
- Homologació observacional urbana o de tota l’atmosfera superior.

## Instrucció per a Codex

Aquest és el primer gate dur de física runtime. No triïs la tolerància a partir dels residuals del candidat. Si falla, corregeix 7.7–7.11, sense compensar en 7.13 ni en el renderer. No comencis 7.13. Si el criteri no es pot demostrar, mantén aquest pas pendent amb causa i evidència.

## Treball pendent

- Cap treball pendent del gate registrat. Les incerteses físiques/exosfèriques fora de les hipòtesis continuen explícites; no s'han declarat resoltes observacionalment.
- [7.13](../pendent/pas7.13-dome-profile-direct.md) queda pendent i no iniciat. El sostre històric 10 km no hereta el PASS.
