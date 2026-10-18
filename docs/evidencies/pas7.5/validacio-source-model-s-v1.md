# Pas 7.5 — Validació de la font física definida S v1

Data: 2026-10-18. [Política S/C/H](../../skyglow/20-politica-rsr-i-validacio-per-dominis.md). **Domini verificat:** fonts definides amb SPD tabulada, amplitud explícita, posició puntual o rectangle uniforme al pla tangent i distribució angular axial o separable en azimut. Cap resultat d'aquí no és una mesura urbana ni una homologació Black Marble C/H.

## Contracte físic i unitats

El [model immutable](../../../backend/src/terralab3d/domain/light_pollution/source_model.py) normalitza la SPD energètica `s(λ)` a `∫s(λ)dλ=1` (`nm⁻¹`) i el patró ascendent `a(θ,φ)` a `∫hemisferi a dΩ=1` (`sr⁻¹`). Amb potència hemisfèrica **definida** `P` (`W`), el flux espectral és `Pλ=P·s(λ)` (`W nm⁻¹`) i la intensitat radiant espectral de la font sencera és `Iλ=P·s(λ)·a(θ,φ)` (`W sr⁻¹ nm⁻¹`). Per a un rectangle uniforme d'àrea `A`, l'exitància espectral és `Mλ=P·s(λ)/A` (`W m⁻² nm⁻¹`); la intensitat espectral per unitat d'àrea és `Mλ·a`, i la radiància superficial local, quan `cosθ>0`, és `Lλ=Mλ·a/cosθ` (`W m⁻² sr⁻¹ nm⁻¹`). La radiància superficial no es defineix per a fonts puntuals ni a l'horitzó geomètric.

L'escala `parametric` conserva unitats `relative` en tots els resultats: no s'hi assignen watts. `defined_absolute` vol dir que l'usuari o una fixture **ha definit** `P` en watts; no vol dir que s'hagi mesurat una ciutat. `measured_absolute` exigeix declarar una referència de calibratge, però aquest pas no en presenta cap cas real. `uncertaintyStatus=not_quantified` evita atribuir precisió instrumental a S. Les alternatives d'`SourceModelEnsemble` no porten pesos probabilístics inventats. La forma angular axial existent i la modulació azimutal nova tenen procedència pròpia; no s'imposa Lambert ni un perfil urbà per defecte.

## Assets i contrast independent

La [validació JSON](validacio-source-model-s-v1.json) es regenera amb l'[eina offline](../../../tools/validate_defined_source_step7_5.py). Llegeix els fitxers CIE LED B1 i HP1 de la biblioteca de dades configurada, comprova MD5 publicat i SHA-256 local contra el [manifest verificat de 7.4](../pas7.4/cie-asset-manifest.json), i no incorpora els CSV al repositori. Són **SPD relatives aproximades de llums representatives**, no SPD d'un lloc. [CIE LED 1 nm](https://cie.co.at/datatable/relative-spectral-power-distributions-illuminants-representing-typical-led-lamps-1nm) identifica la taula, la procedència CIE 015:2018 i el checksum extern. La llicència de l'asset figura al manifest (`CC BY-SA 4.0`).

La fixture puntual associa LED B1 a **1 W ascendent definit com a entrada analítica**. La fixture extensa associa una mescla LED B1 + HP1 a una amplitud relativa `P_area`; cap de les dues usa VIIRS. El JSON registra 401 nusos LED, 81 HP i 401 de la mescla, amb integral espectral independent `1,0` per a cada forma; les quadratures independents de les formes angulars axial i anisòtropa donen `1,0`. Les proves comparen també una línia triangular estreta amb els seus nusos explícits, una geometria de `200 m²`, la identitat `Iλ=A·(dIλ/dA)` i `dIλ/dA=Lλ cosθ`.

Les [set proves noves](../../../backend/tests/test_defined_source_model_step7_5.py) contrasten integral espectral per trapezis i integral angular Gauss–Legendre en coordenades de cosinus/azimut, separades de les primitives de normalització del model. També rebutgen espectres negatius/nuls/no finits, una taula publicada sense SHA-256, àrea degenerada, perfil azimutal no periòdic, amplitud negativa i watts paramètrics. La serialització conserva identitat, classe d'origen (`defined_input`, `published_table` o `derived_mixture`), unitats, checksum, llicència i components de mescla; no conté cap identificador de grànul. Les quatre proves anteriors del [gate C/H](../../../backend/tests/test_source_model_gate_step7_5.py) continuen vigents.

## Reproducció i límit de la conclusió

```powershell
python -X utf8 tools/validate_defined_source_step7_5.py --output docs/evidencies/pas7.5/validacio-source-model-s-v1.json
python -m pytest backend/tests -q
python -m ruff check backend/src/terralab3d/domain/light_pollution/source_model.py backend/tests/test_defined_source_model_step7_5.py tools/validate_defined_source_step7_5.py
python -m pyright backend/src/terralab3d/domain/light_pollution/source_model.py tools/validate_defined_source_step7_5.py
```

Resultat del 2026-10-18: **216 proves backend superades**, Ruff i Pyright sense errors. L'oracle del Pas 7.4 i el seu criteri de `0,01 mag` no canvien; el Pas 7.6 encara ha de verificar el transport i la convergència. Aquest gate acredita conservació i coherència dimensional **de S en el domini declarat**. No estableix una RSR efectiva nocturna de 2026, la inferència de radiància Black Marble L3 a emissió, una incertesa instrumental ni la precisió del cel real; aquests continuen als dominis C/H i als passos 7.16–7.24.
