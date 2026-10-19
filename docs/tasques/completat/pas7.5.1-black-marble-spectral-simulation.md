# Pas 7.5.1 — Black Marble NOAA-20 i simulació espectral realista/per kelvins

> **Estat:** completat. **Estat funcional:** observable. **Origen:** planificat. **Abast vigent:** biblioteca CIE, fonts C relatives i controls científics; transport atmosfèric i radiància/render físics pendents.

## Descripció funcional

«Simulació realista» i «Simulació per kelvins» dins de Contaminació lumínica. Configuració autoritativa Python amb SPD efectiva, normalització i revisió; grànul real NOAA-20 amb QA 0 alimenta ambdues modalitats en escala condicionada relativa.

## Fonts a consultar

- [Política científica i fonts NOAA/NASA/CIE consultades el 2026-10-18](../../skyglow/20-politica-rsr-i-validacio-per-dominis.md).
- [Manifest CIE empaquetat](../../../backend/src/terralab3d/infrastructure/catalogs/spectra/manifest.json), CSV i metadades verificats contra MD5 publicat/SHA-256; CC BY-SA 4.0.
- [Grànul NOAA-20 real i evidències de 7.3](../../evidencies/pas7.3/contrast-granuls-black-marble-c2.md), preservades; nova connexió verificada en aquest pas.

## Objectiu

Fer executable Black Marble → SourceModel C abans de SG-REF i conservar l’estat científic dels controls sense representar un transport encara absent.

## Dependències

**Depèn de:**
- [Pas 7.5 — SourceModel S](pas7.5-source-model-v1.md), que reutilitza els contractes i l’oracle 7.2–7.4.

**En depenen:**
- [Pas 7.6](../completat/pas7.6-sg-ref-reference-solver.md)
- [Pas 7.10](../completat/pas7.10-gas-spectral-kernel.md)
- [Pas 7.14](../pendent/pas7.14-photometric-projections.md)
- [Pas 7.16](../pendent/pas7.16-uncertainty-provenance.md)
- [Pas 7.17](../pendent/pas7.17-clear-sky-ground-truth.md)
- [Pas 7.24](../pendent/pas7.24-full-ground-truth.md)
- [Pas 7.25](../pendent/pas7.25-bridge-runtime.md)
- [Pas 7.26](../pendent/pas7.26-three-renderer-debug.md)
- [Pas 7.27](../pendent/pas7.27-sky-composition.md)
- [Pas 7.28](../pendent/pas7.28-b7-homologacio-skyglow.md)
- [Pas 24](../pendent/pas24-cataleg-recursos-descarregues.md)

## Codi existent a reutilitzar

- **Repositori actual:** [SourceModel](../../../backend/src/terralab3d/domain/light_pollution/source_model.py), [lector A2](../../../backend/src/terralab3d/infrastructure/adapters/light_pollution/vnp46.py), [RSR](../../../backend/src/terralab3d/infrastructure/adapters/light_pollution/viirs_rsr.py), [oracle](../../../backend/src/terralab3d/domain/light_pollution/spectral_oracle.py), [bandset](../../../backend/src/terralab3d/domain/light_pollution/spectral_bandset.py) i [SkyPage](../../../frontend/src/view/ui/drawer_pages/SkyPage.ts).
- **Projectes de referència autoritzats:** cap runtime extern; taules CIE i documentació oficial NOAA/NASA amb procedència identificada.

## Flux tècnic

Grànul local verificat → lector compartit amb política NOAA-20 explícita → L3 corregit QA 0 i procedència → RSR MGS de referència amb LGS de contrast → biblioteca CIE / mescla realista o intervenció Kelvin → normalització condicionada → sis SourceModel C relatius per píxel. No es converteix L3 a watts.

La font base estimada és una de tres mescles hipotètiques de flux radiant, cadascuna amb dos patrons angulars alternatius. La intervenció conserva flux fotòpic, potència radiant, resposta DNB de referència o escala relativa. La ràtio DNB predita queda separada de l’observació original. Configuració, espectres/checksums, geometria, QA/procedència i RSR/guany/release participen en el hash d’invalidació.

El control té etiqueta superior «Temperatura de color», lliscant horitzontal, mínim **2.800 K a l’esquerra**, màxim **6.500 K a la dreta**, valor actual en K i etiqueta inferior **«Exemple: ...»**. Família LED de fòsfor CIE B1–B5 i font visibles; l’exemple no canvia la tecnologia. La CCT efectiva es resol amb CIE 1931 2° i locus CIE 1960 uv; no es fabrica una SPD amb Planck.

## Errors, cancel·lació i recursos

SHA-256/identitat/plataforma/DOI/versió/unitats/QA invalidats provoquen rebuig, sense gap-fill ni substitució temporal/sensor. HDF5 amb context manager i cancel·lació existent. Recursos CIE petits empaquetats, sense xarxa implícita. Configuració versionada, generació monotònica i descart de càlculs de configuració obsolets; resolució SPD fora del loop asíncron. Transport absent declarat, cap recurs GPU nou.

## Tasques

- [x] Inspeccionar commits, arquitectura, perfils, models i adaptadors existents.
- [x] Documentar la millor referència oficial NOAA-20, contrast J2/SNPP i limitacions de guany, detectors, calibratge i L3.
- [x] Reutilitzar el lector amb política NOAA-20 explícita; conservar VNP46 i QA/procedència.
- [x] Empaquetar 42 SPD CIE i colorimetria amb atribució, llicència, suport, unitats i checksums; no fabricar tecnologies absents.
- [x] Implementar família K estable amb CCT efectiva comprovada, i tractament explícit del sodi LPS sense CCT significativa.
- [x] Implementar ensembles deterministes, quatre normalitzacions i fonts C amb el contracte de transport S.
- [x] Integrar controls accessibles i estat científic via bridge; cap resultat atmosfèric fictici.
- [x] Refactoritzar noms obsolets del gate estricte: `validated_l3_basis_candidate` i `unavailable_for_validated_l3_inference` limiten afirmacions acreditades, no les fonts C condicionades. Preservar evidències anteriors.
- [x] Actualitzar planning, perfils, dependències, inventari, manual, evidències i punt de represa.

## Criteri de sortida

El grànul `VJ146A2.A2026256.h18v04.002.2026264085938.h5` amb SHA-256 conegut i píxel urbà QA 0 genera fonts realistes i per K diferenciades, relatives i consumibles pel futur SG-REF compartit. UI verificable amb teclat, ratolí i tacte i configuració confirmada per Python. Cap skyglow calculat ni H declarats.

## Proves i evidències obligatòries

- [x] Proves científiques independents: CCT per graella de Planck, integració analítica/trapezoïdal, normalització fotòpica/radiant/DNB i conservació de pics/nusos.
- [x] Integració real NOAA-20, dates/QA/unitats/RSR/procedència, determinisme, serialització, invalidació i rebuig de conversions injustificades.
- [x] Regressions backend i frontend, Ruff i Pyright dels mòduls afectats; baseline global documentat.
- [x] UI i bridge real amb teclat/ratolí/tacte, captures inspeccionades i absència de radiància fictícia.
- [x] [Validació i reproducció](../../evidencies/pas7.5.1/validacio-simulacio-condicionada.md), [UI](../../evidencies/pas7.5.1/verificacio-ui.json), [captura Kelvin](../../evidencies/pas7.5.1/control-kelvins.png) i [captura realista](../../evidencies/pas7.5.1/simulacio-realista.png).

**Resultats verificats:** 2026-10-18, Python 3.13 / Windows; 247 proves backend i suite frontend en verd. CCT objectiu amb error numèric inferior a 0,1 K en els valors verificats; no tolerància de fabricació. Detall i limitacions a l’informe d’evidència.

La comprovació TypeScript ha requerit resoldre `dashed = base.dashed ?? false` a `OverlayLineStyle`: el camp opcional passa a tenir el mateix valor efectiu booleà que ja emprava el material, sense alterar el model de línies. Regressions frontend superades.

## Fora d'abast

SG-REF, transport atmosfèric complet, radiància del cel, homologació H, dades locals de parc d’enllumenat, extrapolació CIE a 1.800 K i gestor ordinari de descàrregues (24).

## Instrucció per a Codex

Pas completat en aquest domini. Reprendre 7.6 amb els SourceModel S i C; reutilitzar biblioteca, configuració i normalitzacions. No repetir una cerca indefinida de RSR anual ni convertir escala relativa en watts. A 7.10/7.14 revalidar SPD/mescles/operadors nous sense relaxar 0,01 mag; a 7.25–7.27 connectar els controls existents a resultats físics reals.

## Treball pendent

Cap tasca oberta dins l’abast d’aquest pas. La connexió gràfica física dels controls és obligatòria i resta assignada a 7.25–7.27, sense marcar-la completada. SG-REF és el següent pas realment pendent.
