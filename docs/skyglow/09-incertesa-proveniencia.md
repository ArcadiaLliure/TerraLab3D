# Incertesa i procedència

## Separació principal

`PredictionUncertainty` descriu incertesa absoluta de la predicció. `CacheValidityUncertainty` descriu incertesa en el canvi respecte del resultat cachejat. Barrejar-les provocaria invalidacions innecessàries per errors sistemàtics que no han canviat.

## Fonts de PredictionUncertainty

Radiometria per plataforma/producte Black Marble; calibratge/processament/release; RSR, proxy de guany i transformació TOA→L3 com a components diferenciats; règim de baixa radiància/punt zero; prior espectral; model angular d'emissió; atmosfera; aerosol/núvol; gas; DEM/oclusió; error numèric; error estructural single-scattering; compressió de cúpula.

No es combina tot en quadratura. Un ensemble SPD és epistèmic; un biaix de calibratge és sistemàtic; errors locals atmosfèrics poden estar correlacionats.

## Black Marble multisatèl·lit / VIIRS DNB

La incertesa conserva per separat radiometria de VNP46/VJ146/VJ246, processament/release, model DNB/RSR, mapping MGS/HGS, correcció L3, prior espectral, inferència angular i règim de baixa radiància. Cada terme té font, domini, estat quantitatiu i correlacions; l'etiqueta «RSR oficial» no dona per si sola una cota.

No es transfereixen automàticament percentatges del DNB SDR a VNP46. Un composite pot tenir altres fonts d'error i correlació.

La comparabilitat de baixa radiància pre/post-2017 és una restricció de producte fins que es tanqui la política de punt zero. Valors negatius o febles no es transformen en zero abans de representar-ne la incertesa.

Stray light i altres correccions només entren com a transformació/incertesa pròpia si el producte/release no les ha resolt ja.

## Ensemble espectral

Per hipòtesi `m`, calcular la predicció amb el mateix operador vectoritzat. Reportar distribució/interval entre hipòtesis i pesos només si hi ha base per als pesos. Amb `priorConfidence=LOW`, el cache pot usar el màxim entre hipòtesis en lloc d'un quantil ponderat.

## Atmosfera

`OpticalParameter<T>` pot tenir `sigma` només si el proveïdor/model ho justifica. `REANALYSIS` no implica un sigma universal. `UncertaintyModelRegistry` indexa per provider/product/variable/lead/resolució/règim.

Per paràmetres correlacionats: `σ_B²=J Σ Jᵀ`, amb `Σ_ij=σ_i σ_j ρ(d_ij)`. Candidat inicial `ρ(d)=exp(-d/Lc)`. Runtime usa dominis/grups de correlació; la simplificació es valida offline.

## Cache

Per hipòtesi m: `ΔB_hat^m = ΔB_geometry^m + Σ_p J_p^m Δp`. Inflació conservadora opcional: `|Δp|_safe=|Δp_measured|+kσ_p` quan el model d'incertesa ho permet.

El cache metric pot ser `Q95(|ΔB_hat|/B_total)` o màxim sobre hipòtesis de baixa confiança. Abans, sempre s'executen guardes de discontinuïtat.

## No-linealitat

La linealització només és vàlida dins una envolupant. Si una cota de segon ordre/remainder pot consumir una fracció excessiva del pressupost, invalidar. No usar llindars màgics de `Δg`, `ΔAOD` o metres sense relació amb error radiomètric.

## Què veu l'usuari

UI: font de dades, data/temps de validesa, mode `observed/forecast/reanalysis/climatology/standard`, indicador de confiança qualitatiu derivat i, si és útil, interval de brillantor. Intern: matrius/correlacions, Jacobians, components detallats i bounds numèrics.

## Procedència mínima

Qualsevol resultat físic ha de poder respondre: quina versió VIIRS, quina RSR, quin prior SPD, quin model d'emissió, quina atmosfera, quins tiles, quin DEM, quin band set, quina fase, quina LUT gas, quin modelVersion i quin commit.
