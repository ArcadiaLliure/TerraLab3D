# Pas 7.6 — SG-REF: oracle independent de transport i integració d’àrea

> **Estat:** completat. **Estat funcional:** observable offline. **Origen:** planificat. **Abast vigent:** transport S/C en slab espectral homogeni pla, integració directa d’àrea/raster, fases fines i contrast F5 independent; sense homologació urbana H ni runtime.

## Descripció funcional

SG-REF calcula radiància espectral per direcció donat el mateix `SourceModel` S/C de 7.5–7.5.1. És executable per API Python i pel CLI de validació. Les fonts condicionades continuen en unitats relatives i les alternatives d’un ensemble es calculen separadament. El contrast Monte Carlo d’ordre superior quantifica el biaix single-scattering dels benchmarks, amb error mostral i cota del truncament.

## Fonts a consultar

- [Especificació](../../skyglow/01-especificacio-algorismes.md), [justificació](../../skyglow/04-justificacio-cientifica.md) i [validació](../../skyglow/08-validacio-cientifica.md), consultades el 2026-10-18.
- [SciPy `quad_vec`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.quad_vec.html), consultada el 2026-10-18: quadratura vectorial adaptativa GK21, norma màxima i diagnòstics de convergència. Dependència BSD-3-Clause; cap codi de LPTRAN incorporat.
- [Cinzano–Falchi, 2012](https://arxiv.org/abs/1209.2031), consultat el 2026-10-18: distingeix un model de transport més ric amb dispersions múltiples, curvatura i atmosfera variable. SG-REF no es presenta com a implementació d’aquest model complet.
- [Whitney, Monte Carlo Radiative Transfer](https://arxiv.org/abs/1104.4990) i [NASA, Modeling Atmosphere-Ocean Radiative Transfer](https://ntrs.nasa.gov/api/citations/20190026727/downloads/20190026727.pdf), consultats el 2026-10-18 com a referències de transport estocàstic i traçat invers. Algorisme escalar propi; sense importar implementacions externes.

## Objectiu

Disposar d’una referència numèrica independent abans de construir el runtime. Quantificar precisió/convergència dins el domini verificat, sense confondre error numèric, simplificació single-scattering i incertesa de les hipòtesis urbanes.

## Dependències

**Depèn de:**

- [Pas 7.5 — SourceModel S](pas7.5-source-model-v1.md)
- [Pas 7.5.1 — Fonts C i configuració](pas7.5.1-black-marble-spectral-simulation.md)

**En depenen:**

- [Pas 7.7 — Kernel geomètric B0](../completat/pas7.7-kernel-geometry-b0.md)

## Codi existent a reutilitzar

- **REUSE:** [SourceModel](../../../backend/src/terralab3d/domain/light_pollution/source_model.py), [escenaris](../../../backend/src/terralab3d/domain/light_pollution/simulation.py), biblioteca CIE i adaptadors Black Marble/RSR de 7.5.1. Es comparteixen definicions d’entrada i la normalització angular autoritativa; cap integrador de transport.
- **NEW:** [transport determinista](../../../backend/src/terralab3d/domain/light_pollution/reference_transport.py), [transport Monte Carlo independent](../../../backend/src/terralab3d/domain/light_pollution/reference_multiple_scattering.py), [CLI](../../../tools/run_sg_ref_step7_6.py) i [proves](../../../backend/tests/test_reference_transport_step7_6.py).
- **Projectes de referència autoritzats:** cap runtime extern incorporat ni dependència del checkout TerraLab. La visualització històrica no és oracle radiomètric; aquest pas crea una capacitat científica nova.

## Flux tècnic

Font i observador geodèsics → coordenades locals explícites del pla de referència → integral LOS GK21 de SciPy, amb canvi de variable exacte `s=scale*sinh(t)` i segmentació als límits del suport emissor → integral directa Gauss–Legendre del rectangle `dA/A` → refinaments espacials consecutius → radiància espectral, error estimat, comptadors i signatura SHA-256 de totes les entrades/revisions.

El medi és un slab homogeni espectral `0≤z≤H`, terra negre i cel clar escalar. Admet fases isòtropa, Rayleigh escalar, HG analítica i taula normalitzada sobre cosinus. La ruta fina conserva els 401 nusos CIE; no usa el bandset ni LUT de runtime. Geometria amb font/LOS singular es rebutja. Les altures són coordenades del slab definit; no són un model DEM/geoidal.

El transport F5 traça trajectòries iid des del detector fins a terra/cel, amb longituds exponencials i mostreig propi de les tres fases analítiques. La contribució de frontera té pes `ωⁿ`. No reutilitza nodes, LOS, canvi de variable ni integrador determinista. La cota de la cua és `Lmax·ω^(N+1)` per a rectangles amb radiància superficial limitada i `0<ω<1`.

Les toleràncies i la regla diagnòstica de 6 errors estàndard es van [congelar abans de la primera avaluació](../../evidencies/pas7.6/criteri-oracle-v1.json). No són toleràncies de producte ni intervals rigorosos. El gate 7.12 segueix pendent i haurà de preregistrar el seu propi llindar sense mirar els residuals del runtime candidat.

## Errors, cancel·lació i recursos

Es rebutgen entrades no finites, unitats/escales relatives incompatibles, duplicats, geometria singular, òptica amb dispersió superior a extinció i convergència insuficient. La suma és de fonts físiques additives, mai d’alternatives del mateix píxel. Cancel·lació cooperativa per callback; el CLI també admet Ctrl+C. No es retorna una estimació parcial com a resultat convergit.

El CLI és síncron i offline: no hi ha scheduler latest-wins, bridge per frame ni recursos GPU. Cada resultat porta signatura immutable; cap cache de propagació. Arrays de quadratura i trajectòries són locals al càlcul. HDF5 es tanca amb context manager. El JSON final es reemplaça només després de completar tots els contrasts; un error conserva l’anterior fitxer i retorna un codi de sortida no nul.

## Tasques

- [x] Implementar SG-REF amb toleràncies estrictes, diagnòstics i dues refinacions espacials consecutives convergents.
- [x] Integrar directament àrees i rasters de rectangles uniformes; provar subdivisió, rotació i conservació de potència.
- [x] Mantenir independència respecte del futur ECEF/ENU i GK7/15 del runtime; compartir només el contracte de font.
- [x] Incorporar fases d’alta resolució i transport als 401 nusos espectrals CIE.
- [x] Quantificar F5 amb transport Monte Carlo d’ordre superior en nou benchmarks plans homogenis, amb error mostral i cota de cua explícits.
- [x] Crear fixtures analítiques E1, contrast GL compost independent, invariants i escenaris reproduïbles.
- [x] Registrar convergència, error estimat i límits de domini per al futur gate 7.12.
- [x] Propagar S i 18 alternatives C reals de 7.5.1 en modalitats realista/3.000 K/6.500 K, conservant escala, hipòtesis i procedència.

## Criteri de sortida

`S1` és executable i verificat en el domini declarat: radiància espectral per direcció, fonts puntuals no singulars i rectangles/raster, sense quadtree, cache ni LUT de runtime. Convergència i errors estan registrats; F5 té una referència independent d’ordre superior. El PASS/FAIL del runtime i la validació empírica H no s’han executat.

## Proves i evidències obligatòries

- [x] 35 proves noves: solució E1, normalització de fase, linealitat, S/C, unitats, àrea/raster rotat, fase fina, determinisme, errors, cancel·lació, azimut periòdic i suport emissor prim prop del sostre.
- [x] 282 proves backend superades; Ruff i Pyright dels mòduls nous i CLI sense errors.
- [x] [Resultats reproduïbles](../../evidencies/pas7.6/resultats-sg-ref-v1.json), [criteri congelat](../../evidencies/pas7.6/criteri-oracle-v1.json) i [informe científic](../../evidencies/pas7.6/validacio-sg-ref.md).
- [x] README, inventari, manual, perfils, decisions, dependències i punt de represa actualitzats; auditoria proporcional registrada.
- [x] Cap capacitat dels passos 7.7–7.28 marcada com a implementada.
- [x] Modalitats realista/K verificades amb el grànul NOAA-20 real; C continua relatiu i H sense homologar.

**Resultats verificats:** 2026-10-18, Python 3.13.7, NumPy 2.3.3, SciPy 1.16.2. Contrast analític i GL compost coincidents a la precisió mostrada; diferència raster/rectangle `9,95·10⁻¹³` relativa. Refinament de fase 4.097→16.385 mostres redueix el desajust de radiància d’`1,04·10⁻⁶` a `6,61·10⁻⁸`. Els nou contrasts de primer ordre Monte Carlo queden entre 0,04 i 1,84 errors estàndard del determinista. Detall, incerteses i límits a l’informe.

## Fora d'abast

ECEF/ENU del runtime, atmosfera vertical/tiled real, Mie/polarització, DEM, curvatura, reflexió del terra, núvols, projeccions SQM/TESS, homologació H i render físic. F5 no és una cota universal urbana ni una correcció multiplicativa per a Barcelona. Els escenaris amb nous medis/geometries requereixen ampliar i revalidar l’oracle en el pas que els introdueixi, abans de qualsevol gate que els consumeixi.

## Instrucció per a Codex

Pas tancat en el domini verificat. Reprendre exclusivament 7.7. No reutilitzar la quadratura de SG-REF com a kernel runtime; no convertir la seva estimació d’error en un interval garantit. A 7.8–7.11 conservar aquests benchmarks i ampliar la referència quan s’introdueixin atmosfera variable, terreny o curvatura; 7.12 no pot validar aquests dominis amb el slab pla ni homologar H amb els contrasts numèrics.

## Treball pendent

Cap tasca oberta dins l’abast verificat de 7.6. Runtime geomètric a 7.7; els dominis atmosfèrics/geogràfics posteriors i la connexió gràfica dels controls continuen pendents als seus passos.
