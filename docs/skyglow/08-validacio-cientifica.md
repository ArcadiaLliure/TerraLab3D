# Pla de validació científica

## 1. Validació numèrica

Objectiu: demostrar que discretització i integració convergeixen abans de comparar amb el món real. Casos: atmosfera homogènia amb solució/alta precisió de referència, integrands suaus, discontinuïtats a límits de tile, oclusió, trajectes rasants i fonts puntuals/extenses.

Proves: convergència GK; comparació amb quadratura d'ordre alt; invariància sota partició equivalent de tiles; linealitat en intensitat; suma de patches igual a font no agregada dins tolerància; positivitat de radiància; absència de NaN/Inf a 0,5°.

## 2. Validació espectral

Reference spectrum de pas fi (≤1 nm o prou fi per convergir les mètriques) sobre 400–900 nm i RSR DNB real. Comparar `PropagationBandSet` candidats 4/6/8/10/12 bandes. Mètriques: error en luminància fotòpica, resposta SQM, resposta TESS-W, XYZ, radiància de banda i resultat després de Rayleigh/aerosol/gas.

Un band set només es congela si la mateixa configuració és acceptable per una biblioteca diversa d'SPD i atmosferes; no s'ajusta només a LED blanc.

## 3. Validació atmosfèrica

Separar components. Rayleigh: contrast contra formulació Bodhaine/King. Gasos: LUT contra càlcul espectral fi HITRAN/LOWTRAN-like. Aerosols: HG/Legendre contra taules Mie/mesurades. Humitat: casos secs/humits si la biblioteca aerosol la modela. Núvols: només single-scattering v1 contra casos òpticament prims/moderats.

## 4. Validació all-sky

Construir `B_full(az,el)` amb solver de referència i `B_compressed` amb mostres de cúpula. Comparar abans de tone mapping.

`Δm=|-2.5 log10(B_compressed/B_full)|`.

Mètriques mínimes: MAE hemisferi ponderat per angle sòlid, MAE 0–20°, P95 `|Δm|`, relació d'energia `∫B_compressed dΩ/∫B_full dΩ`, `Δaz_peak`, `ΔB_peak`, `ΔW`. Escombrar si cal la mostra a 1° i el percentatge de `W_effective`.

## 5. Ground truth

Fonts prioritàries: TESS-W i SQM amb resposta espectral coneguda; all-sky fotomètric calibrat quan estigui disponible. La comparació amb un sensor simula la seva banda i FOV; no es converteix una radiància espectral a «SQM» amb una constant universal.

Per cada observació registrar: posició, elevació, hora UTC, lluna, núvols, transparència/AOD si disponible, instrument/serial, calibratge, FOV, temperatura, dades VIIRS corresponents i versió atmosfèrica.

## 6. Disseny estadístic

Separar calibratge i validació. Si s'ajusten priors o paràmetres d'emissió amb llocs mesurats, fer leave-one-site-out i una validació geogràfica externa. No utilitzar el mateix conjunt per triar bandes, ajustar emissió i reportar precisió final.

Reportar errors amb intervals/quantils i estratificar per distància a fonts, brillantor, aerosol, relleu, elevació i tipus d'il·luminació.

## 7. Bortle

Bortle és una escala observacional qualitativa. Només es pot mostrar com equivalència orientativa derivada de radiància/condicions, mai com ground truth físic primari. Les conversions actuals del Pas 7 es mantenen com a legacy fins que una política nova sigui validada.

## 8. Criteris d'acceptació

No s'inventen llindars ara. Cada pas fixa una tolerància provisional només si deriva d'una referència numèrica o d'un requisit de producte. La congelació de producció es fa amb SLO multidimensional: `E_physical≤E_max`, `L_p95≤L_max`, `F_recompute≤F_max`, `renderThreadStutter=0`.

## 9. Evidència

Cada campanya genera manifest de datasets/checksums, configuració, commit, hardware, resultats raw CSV/JSON, plots i informe. Els resultats històrics no s'esborren; es marquen vigents/obsolets amb causa.