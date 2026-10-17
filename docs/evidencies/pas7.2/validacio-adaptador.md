# Validació reproduïble de l'adaptador VNP46A2.002 — Pas 7.2

Data: 2026-10-17. Estat: implementació local verificada amb fixtures i grànul VNP46A2.002 real aportat per l'usuari.

## Fonts i correspondència

- L'[especificació oficial VNP46A2 v2.0.4](https://ladsweb.modaps.eosdis.nasa.gov/filespec/VIIRS/2/VNP46A2_v2.0.fs) documenta el grup `HDFEOS/GRIDS/VIIRS_Grid_DNB_2d/Data Fields`, la capa `DNB_BRDF-Corrected_NTL` float32, les coordenades `lat`/`lon`, `Mandatory_Quality_Flag` i els flags auxiliars.
- Les [metadades OPeNDAP d'un grànul NASA Collection 2](https://ladsweb.modaps.eosdis.nasa.gov/opendap/RemoteResources/laads/allData/5200/VNP46A2/2022/050/VNP46A2.A2022050.h26v03.002.2025116070200.h5.html) mostren aquest camí i els atributs de radiància `units=nWatts/(cm^2 sr)`, `_FillValue=-999.9`, `valid_range=>=0.0`, `scale_factor=1` i `offset=0`. El grànul binari local s'ha contrastat separadament amb el lector.
- El [perfil v1](../../skyglow/skyglow-v1-profile.json) continua sent la font de veritat per producte, col·lecció, capa principal, QA, dia exacte i política LOW-RAD. El lector rep el perfil explícitament i no conté llindars PASS/FAIL científics.
- `h5py>=3.16` s'ha afegit a `backend/pyproject.toml`; la [llicència oficial és BSD-3-Clause](https://github.com/h5py/h5py).

## Implementació i fixtures

- [Model immutable](../../../backend/src/terralab3d/domain/light_pollution/vnp46.py), [port](../../../backend/src/terralab3d/application/ports/vnp46_observations.py), [lector](../../../backend/src/terralab3d/infrastructure/adapters/light_pollution/vnp46.py) i [eina CLI](../../../tools/inspect_vnp46_granule.py).
- [Proves HDF5 reproduïbles](../../../backend/tests/test_vnp46_adapter_step7_2.py): radiància alta i baixa, negativa, fill, zero, QA 0/1/5/9/255, georeferència, serialització JSON, dia de traspàs, frontera 2016/2017, checksum incompatible, col·lecció incompatible, unitat incompatible, capa primària o de qualitat absent, dia absent i cancel·lació. La capa gap-fill de la fixture té valors deliberadament diferents per detectar-ne l'ús accidental.
- Els valors crus no es retallen ni es converteixen a emissió. El lector exigeix SHA-256 esperat, preserva l'atribut de la unitat original i tanca HDF5 amb un context. No descarrega dades.

## Ordres de comprovació

```powershell
python -X utf8 -m pytest backend/tests/test_vnp46_adapter_step7_2.py -q
python -X utf8 -m pytest backend/tests -q
python -m ruff check backend/src/terralab3d/domain/light_pollution/vnp46.py backend/src/terralab3d/application/ports/vnp46_observations.py backend/src/terralab3d/infrastructure/adapters/light_pollution/vnp46.py backend/tests/test_vnp46_adapter_step7_2.py tools/inspect_vnp46_granule.py
python -m pyright backend/src/terralab3d/domain/light_pollution/vnp46.py backend/src/terralab3d/application/ports/vnp46_observations.py backend/src/terralab3d/infrastructure/adapters/light_pollution/vnp46.py
python -X utf8 tools/check_doc_links.py
```

Resultat verificat el 2026-10-17: **9 proves específiques i 186 proves de backend en verd**; Ruff i Pyright sense errors; enllaços locals vàlids després del trasllat del document de pas. El validador documental manté les 720 incidències heretades d'altres passos i no n'atribueix cap al Pas 7.2.

## Contrast amb el grànul real

L'usuari ha facilitat el fitxer local `VNP46A2.A2026256.h00v01.002.2026264113205.h5`. S'ha traslladat de `C:\Users\Manel\Downloads` a l'arrel configurada per `resolve_data_root()` (`I:\TerraLab` en aquesta sessió), sota `data/earth/light-pollution/vnp46a2/2026/256/`. La mida és **4.289.573 bytes**; SHA-256 abans i després del trasllat: `dd399776275745e7d04f4ac01d567de6827442ade2257c47a2c1ee536ee04878`. La ruta d'origen ja no conté el fitxer. La suma identifica i comprova la integritat del trasllat, però no és un checksum extern publicat per NASA. Tampoc no s'ha verificat l'URL exacte des del qual es va descarregar; `source_url` és `null` deliberadament.

La inspecció `h5py` confirma `ShortName=VNP46A2`, `VersionID=002`, `PlatformShortName=SUOMI-NPP`, DOI `10.5067/VIIRS/VNP46A2.002`, `RangeBeginningDate=RangeEndingDate=2026-09-13`, `AlgorithmVersion=NPP_PR46A2 1.0.3`, `PGEVersion=2.0.5`, dimensió de radiància `2400×2400` float32 i QA uint8. La capa principal és `DNB_BRDF-Corrected_NTL`, diferent de la capa gap-filled. Els atributs reals contenen salts de línia finals a `units` i `valid_range`: el lector en comprova el valor semàntic amb `strip()`, però conserva el text original a la procedència. No cal cap conversió d'escala (`scale_factor=1`, `offset=0`).

Comprovació directa de les dues mostres amb [`inspect_vnp46_granule.py`](../../../tools/inspect_vnp46_granule.py) i `Vnp46GranuleAdapter`:

| Fila, columna | Radiància crua | QA | Classificació | Resultat |
|---|---:|---:|---|---|
| 2171, 2370 | `1.6307218074798584` | 2 | `diagnostic_only` | Conserva radiància i coordenades `70.9541666666749, -170.12500000000898`; exclou inferència de font. |
| 1181, 332 | `-999.9000244140625` | 255 | `no_retrieval` | Conserva el fill float32, `isFill=true`; exclou inferència. |

El recompte de `Mandatory_Quality_Flag` del tile és QA 2: 90.426, QA 5: 109 i QA 255: 5.669.465 píxels; **no hi ha QA 0**. Per això el comportament candidat de QA 0 continua cobert per les fixtures reproduïbles, no per aquest grànul. Les mostres llegides són observacions HDF-EOS5 transformades al contracte intern `Vnp46Observation`, no imatges carregades directament per TerraLab3D.

Ordre reproduïble per al píxel de diagnòstic (substituir `$granule` per la ruta dins l'arrel configurada en una altra instal·lació):

```powershell
$granule = 'I:\TerraLab\data\earth\light-pollution\vnp46a2\2026\256\VNP46A2.A2026256.h00v01.002.2026264113205.h5'
python -X utf8 tools/inspect_vnp46_granule.py $granule --sha256 dd399776275745e7d04f4ac01d567de6827442ade2257c47a2c1ee536ee04878 --date 2026-09-13 --row 2171 --column 2370
```

La CLI ha retornat JSON amb `rawRadiance=1.6307218074798584`, `qualityFlag=2`, `classification=diagnostic_only`, `sourceInferenceCandidate=false`, DOI, identificador, SHA-256, versions i atributs d'origen. El contrast real verifica la lectura binària i la semàntica de diagnòstic/fill; no prova encara un cas candidat real ni autentica independentment la descàrrega original.
