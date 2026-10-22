# Pas 7.14A — Projeccions CIE i AB de referència en domini acreditat

> **Estat:** completat per partició documental prospectiva (2026-10-22), limitada a funcionalitat **ja contrastada** en els resultats 7.14 v1/v2/v3. No és un PASS del gate original de 7.14, que continua bloquejat, ni una homologació SQM/TESS o observacional H.

## Objectiu

Permetre que 7.15 i els passos posteriors consumeixin radiància espectral i projeccions fotomètriques **CIE i AB de referència** dins del domini que ja s'ha validat, sense convertir un model instrumental incomplet en una dependència de tota la física.

## Dependències

- [Pas 7.13 — camp angular verificat per dominis](pas7.13-dome-profile-direct.md).
- [Pas 7.4 — discretització espectral](pas7.4-spectral-bandset-validation.md).
- [Pas 7.5.1 — escenaris S/C i SPD](pas7.5.1-black-marble-spectral-simulation.md).
- [Pas 7.14 original — candidat parcial i gate bloquejat](../pendent/pas7.14-photometric-projections.md).

## Abast implementat i acreditat

- La retenció `retain_spectrum` i `project_retained` integren respostes documentades sense executar un segon transport. Es preserven suport espectral, unitats, revisions, cancel·lació, zeros i escala compatible.
- En fonts S amb radiància espectral SI, `683∫LλV(λ)dλ` dona luminància artificial fotòpica cd/m²; les fonts C continuen en **escala relativa condicionada**, sense luminància/magnitud absoluta inventada.
- La corba CIE 018:2019 declara longituds d'ona en aire estàndard; la conversió versionada a `vacuum_nm` i el jacobià estan contrastats independentment. No reetiquetar espectres de catàleg que no tenen convenció.
- La magnitud **AB de referència** només és matemàticament vàlida per a la banda/resposta **tabulada i identificada**, el suport spectral i la normalització declarats; no és el zero point natiu SQM/TESS ni una lectura instrumental.
- DomeProfile CIE és un camp escalar, vàlid només en els dominis de [7.13 adaptatiu](../../evidencies/pas7.13/adaptatiu-v2/validacio-adaptativa-v2.md). No permet obtenir espectres ni SQM/TESS per inversió. Oclusions DEM, fonts extenses, COESA all-sky i àrees no homologades continuen amb ruta directa o `unavailable`.

## Evidències existents i criteri de sortida de 7.14A

La [v1](../../evidencies/pas7.14/validacio-projeccions.md) registra 10.624 casos espectrals, 39 contrasts de transport i projecció CIE/AB numèrica. La [v2](../../evidencies/pas7.14/represa-v2/validacio-represa-v2.md) documenta conversió aire/buit, 21.184 casos espectrals, 55 controls de flux, 13 projeccions independents i 540 proves backend, tots PASS dins dels seus **suports tabulats**. La [v3](../../evidencies/pas7.14/represa-v3/validacio-represa-v3.md) preserva exactament aquells senyals i el bloqueig instrumental.

**Sortida de 7.14A:** aquestes projeccions matemàtiques CIE/AB es poden consumir quan banda, suport, unitats, coordenades i geometria estiguin acreditats; qualsevol altra entrada queda `unavailable` o ha de passar nous gates prospectius. Es manté el pressupost espectral preregistrat de **0,01 mag** al domini efectivament avaluat. **No s'ha executat cap gate nou ni s'ha transformat el veredicte de 7.14 original**.

## Represa

- [7.15 ERA5/CAMS](../pendent/pas7.15-atmos-era5-cams.md) pot continuar amb aquesta capacitat, sense exigir SQM/TESS.
- [7.14B SQM/TESS](../pendent/pas7.14b-perfils-instrumentals-sqm-tess.md) queda pendent. El [gate v3 original](../../evidencies/pas7.14/represa-v3/gate-represa-v3.json) continua amb `numericStatus=PASS` però `scientificExitPassed=false`.
- [Revisió prospectiva i limitacions](../../skyglow/22-revisio-dependencies-7.14-7.15.md). Cap canvi de codi o evidència històrica.
