# Pla de validació científica

## 1. Validació numèrica

Objectiu: demostrar que discretització i integració convergeixen abans de comparar amb el món real. Casos: atmosfera homogènia amb solució/alta precisió de referència, integrands suaus, discontinuïtats a límits de tile, oclusió, trajectes rasants i fonts puntuals/extenses.

Proves: convergència GK; comparació amb quadratura d'ordre alt; invariància sota partició equivalent de tiles; linealitat en intensitat; suma de patches igual a font no agregada dins tolerància; positivitat de radiància; absència de NaN/Inf a 0,5°.

## 1.1. Gate zenital absolut

Abans de validar cúpules, la direcció 90° ha de superar un gate amb la mateixa implementació del kernel: unitats, convergència, extinció/oclusió i comparació amb un oracle independent.

El gate valida **propagació donat un model de font**. Runtime i oracle consumeixen la mateixa hipòtesi de `SourceModel`; un PASS no valida la inferència VNP46→SPD ni VNP46→emissió angular. Aquesta validació necessita dades externes separades.

L'oracle concret és la decisió S1. La quantificació del biaix single-scattering exigeix un oracle amb multiple scattering segons F5.

## 2. Validació espectral

Cada `SpectralBandSet` actiu es compara contra un espectre de referència prou fi per demostrar convergència de radiància propagada i de les projeccions actives (fotòpica, SQM, TESS-W, XYZ quan apliqui).

No es fan sweeps de rendiment per escollir N. V3 continua obert perquè falta decidir el pressupost d'error espectral que converteix aquesta comparació en PASS/FAIL.

La normalització DNB usa `BAND_INTEGRATED`; la unitat exacta queda pendent de verificació contra l'ATBD.

## 3. Validació atmosfèrica

Separar components. Rayleigh: contrast contra formulació Bodhaine/King. Gasos: LUT contra càlcul espectral fi HITRAN/LOWTRAN-like. Aerosols: HG/Legendre contra taules Mie/mesurades. Humitat: casos secs/humits si la biblioteca aerosol la modela. Núvols: només single-scattering v1 contra casos òpticament prims/moderats.

## 4. Validació all-sky

Construir `B_full(az,el)` amb solver de referència i `B_compressed` amb mostres de cúpula. Comparar abans de tone mapping.

`Δm=|-2.5 log10(B_compressed/B_full)|`.

Mètriques mínimes: MAE hemisferi ponderat per angle sòlid, MAE 0–20°, P95 `|Δm|`, relació d'energia `∫B_compressed dΩ/∫B_full dΩ`, `Δaz_peak`, `ΔB_peak`, `ΔW`. Escombrar si cal la mostra a 1° i el percentatge de `W_effective`.

## 5. Ground truth

La comparació amb el reference solver valida implementació i aproximacions numèriques; no substitueix la validació física externa.

Fonts prioritàries: TESS-W i SQM amb resposta espectral coneguda i all-sky fotomètric calibrat quan estigui disponible. La simulació del sensor usa resposta espectral, FOV i calibratge i propaga la incertesa del prior espectral.

La validació del `SourceModel` és separada: calen dades independents capaces de restringir l'emissió angular/espectral. Una observació VNP46 quasi-nadir no valida per si sola la distribució hemisfèrica.

Si no hi ha dataset extern suficient, l'estat màxim és numèricament validat però no empíricament homologat; la manca de dades no es converteix en PASS.

### Baixa radiància

Les fixtures inclouen valors febles, prop de zero i negatius quan el producte ho permeti, sense clipping silenciós. També cobreixen sèries que travessen 2017. LOW-RAD determina si aquestes mostres s'exclouen o es propaguen amb incertesa.

## 6. Disseny estadístic

Separar calibratge i validació. Si s'ajusten priors o paràmetres d'emissió amb llocs mesurats, fer leave-one-site-out i una validació geogràfica externa. No utilitzar el mateix conjunt per ajustar emissió i reportar precisió final. El nombre de bandes no es selecciona amb una campanya comparativa.

Reportar errors amb intervals/quantils i estratificar per distància a fonts, brillantor, aerosol, relleu, elevació i tipus d'il·luminació.

## 7. Bortle

Bortle és una escala observacional qualitativa. Només es pot mostrar com `BortleEquivalent` orientatiu derivat de condicions de referència, mai com ground truth físic primari. La política té `bortlePolicyId` i està separada de SQM. El `BortleEquivalent` intrínsec del lloc s'avalua sense Lluna ni crepuscle; aquests components només alteren el diagnòstic instantani. Les conversions actuals del Pas 7 es mantenen com a legacy fins que una política nova sigui validada.

## 8. Criteris d'acceptació

Cada gate de producció necessita un perfil d'acceptació congelat **abans** de la comparació que decidirà PASS/FAIL. Cada llindar indica origen: referència publicada, requisit de producte o error/convergència numèrica.

Un llindar modificat després de veure els resultats només pot crear una nova versió prospectiva i no reescriu l'avaluació anterior ni revalida el mateix candidat/conjunt observat. El [perfil v1](skyglow-v1-profile.json) registra les decisions de dades i la política `V1` preregistrada al Pas 7.1, completat documentalment. Els valors numèrics no estan fixats: 7.4 preregistra l'error espectral abans de seleccionar bandes; 7.12 preregistra runtime↔SG-REF abans del PASS/FAIL, amb l'evidència de convergència/incertesa de 7.6; 7.17 preregistra criteris empírics amb incerteses instrumental, de dades i del model abans d'avaluar el conjunt `held-out`; 7.22 preregistra SLO de producte aprovats abans de decidir acceleracions. La manca d'un valor bloqueja aquell primer gate, no 7.2 ni 7.3. 7.28 només consumeix els criteris ja congelats.

L'error estructural single-scattering es registra separat de l'error numèric. F5 no es pot tancar amb un oracle exclusivament single-scattering.

## 9. Evidència

Cada campanya genera manifest de datasets/checksums, configuració, commit, hardware, resultats raw CSV/JSON, plots i informe. Els resultats històrics no s'esborren; es marquen vigents/obsolets amb causa.
