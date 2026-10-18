# Pas 7.5 — Estat verificat de la inferència Black Marble L3→font

> **Evidència històrica del gate observacional C/H.** El bloqueig de 7.5 descrit a continuació correspon al criteri anterior, que exigia una font Black Marble admissible. La [revisió prospectiva S/C/H](../../skyglow/20-politica-rsr-i-validacio-per-dominis.md) trasllada aquesta exigència a C/H; el [SourceModel S](validacio-source-model-s-v1.md) es valida independentment. Cap resultat observacional d'aquesta auditoria s'ha requalificat.

Data: 2026-10-18. **Resultat:** encara no hi ha una font Black Marble de 2026 admissible per construir un `SourceModel` físic. El Pas 7.5 resta bloquejat. Aquest estat no invalida el contracte de mesura de 7.3 ni l'homologació numèrica acotada de 7.4.

## Evidència directa

- La [User Guide Black Marble C2 §2.2, equació (1)](https://viirsland.gsfc.nasa.gov/PDF/BlackMarbleUserGuide_Collection2.0.pdf) defineix la transformació TOA→radiància nocturna ascendent de superfície corregida. El [contrast local de 7.3](../pas7.3/contrast-granuls-black-marble-c2.md) mostra que la capa L3 no inclou els termes auxiliars per invertir-la píxel a píxel. **Inferència:** aplicar `∫SPD·RSR` directament al número L3 confondria dues etapes físiques.
- [NASA, preguntes i respostes de Black Marble, Q19](https://appliedsciences.nasa.gov/sites/default/files/Black%20Marble%20Q%26A%20Doc.pdf) explica que una sola banda DNB no identifica una conversió a LED si la diferència espectral cau sobretot per sota de 450 nm. Això acredita la no identificabilitat espectral, sense proporcionar un prior SPD local.
- [Cinzano i Falchi (2012)](https://academic.oup.com/mnras/article/427/4/3337/973668) defineixen una funció d'emissió ascendent normalitzada sobre l'hemisferi i permeten variació espacial. El [World Atlas (2016)](https://pmc.ncbi.nlm.nih.gov/articles/PMC4928945/) compara tres patrons angulars i ajusta contribucions amb mesures del cel. **Inferència:** cap d'aquestes formes, sense selecció i validació per regió/temps, és una llei angular universal derivable d'un píxel DNB.
- La [validació NASA de Black Marble](https://viirsland.gsfc.nasa.gov/Val/BM_Val.html) documenta la dependència temporal de RSR SNPP i l'estabilitat relativa NOAA-20; no publica una taula numèrica operativa 2026 ni el mapping L3 específic. La [revisió 7.3](../pas7.3/revisio-multisatel-lit.md) examina les taules NOAA-20/NOAA-21 de prelanzament i el proxy HGS de NOAA-21 sense promoure'ls a 2026.

## Auditoria reproduïble de recursos instal·lats

L'[script d'auditoria](../../../tools/audit_source_inputs_step7_5.py) ha llegit tres manifests externs de la biblioteca configurada i ha registrat [sis entrades](auditoria-rsr-2026.json) amb identitat, aplicació, dates, estat L3 i SHA-256 dels manifests. **Entrades `operational_l3` que cobreixen el 2026-09-13: 0; candidates de metadades per a `SourceModel`: 0.** El segon recompte exigeix també producte C2, classe d'evidència, vincle L3 i referència de guany; tampoc no validaria per si sol els bytes de la RSR. Això és un resultat sobre els assets instal·lats, no prova que no existeixi cap taula en un altre arxiu. Les sis són SNPP LGS 2013, NOAA-20 LGS/MGS de prelanzament i NOAA-21 LGS/MGS més proxy HGS; conserven el seu estat diagnòstic.

| Font candidata | Observació real | Manca concreta per al gate de 7.5 |
|---|---|---|
| Suomi-NPP `VNP46A2.002`, 2026-09-13 | [Grànul h00v01](../pas7.2/validacio-adaptador.md) llegit amb SHA-256; mostra `(2171,2370)` de `1,6307218074798584 nW cm⁻² sr⁻¹`, QA 2 diagnòstic. | RSR numèrica efectiva anual 2026, regla de guany i vincle amb PGE/L1B→L3; també falta observació QA candidata en aquest tile. |
| NOAA-20 `VJ146A2.002`, 2026-09-13 | [Tile h18v04 i mostres urbanes QA 0](../pas7.3/contrast-granuls-black-marble-c2.md) reals; no es confon QA 0 amb homologació espectral. | RSR efectiva i mapping MGS/HGS o resposta equivalent amb vincle Black Marble C2 de 2026; inversió física L3→SPD/angular; adaptador J1 de producte encara no disponible. |
| NOAA-21 `VJ246A2.002`, 2026-09-13 | Fitxa i índex de grànuls documentats a [7.3](../pas7.3/revisio-multisatel-lit.md), sense HDF5 real verificat. | Grànul/QA real, resposta efectiva i cota del proxy MGS→HGS, mapping L3 i model de font. |

L'[eina diagnòstica de 7.5](../../../tools/assess_vnp46_source_step7_5.py) reobre el VNP46 h00v01 real, comprova identitat i hash mitjançant l'adaptador de 7.2 i retorna `unavailable_for_physical_inference` amb causes `quality_not_source_candidate` i `operational_rsr_unavailable`; `sourceModel=null`. Conserva la radiància crua i la procedència, sense clipping, gap-fill, normalització TOA ni emissió inferida. Ordre reproduïble:

```powershell
python -X utf8 tools/audit_source_inputs_step7_5.py --date 2026-09-13 --output docs/evidencies/pas7.5/auditoria-rsr-2026.json
python -X utf8 tools/assess_vnp46_source_step7_5.py 'I:\TerraLab\data\earth\light-pollution\vnp46a2\2026\256\VNP46A2.A2026256.h00v01.002.2026264113205.h5' --sha256 dd399776275745e7d04f4ac01d567de6827442ade2257c47a2c1ee536ee04878 --date 2026-09-13 --row 2171 --column 2370
```

## Implementació parcial i frontera científica

El [gate de mesura](../../../backend/src/terralab3d/domain/light_pollution/source_model.py) exigeix QA candidata, senyal L3 positiu, identitat de producte/dia i RSR operativa amb evidència de cadena L3 i guany. Un resultat `measurement_basis_admissible` **només** seria una condició necessària; encara faltarien un prior/ensemble SPD, un model angular amb domini, un operador L3→font i incertesa estructural. La prova positiva del gate usa una RSR **sintètica etiquetada com a fixture** i no afirma que existeixi aquest asset real. `product_homologation_candidate` exigeix, addicionalment, incertesa espectral quantificada a 7.16.

La classe `AngularEmissionProfile` representa una forma axial tabulada d'intensitat relativa amb font explícita i normalització `2π∫p(θ)sinθdθ=1`; no crea cap perfil físic per defecte ni iguala radiància L3 amb flux hemisfèric. Les proves contrasen la integral analítica amb quadratura independent i un perfil sintètic que concentra més intensitat cap a l'horitzó. Aquest component és reutilitzable, però **no** tanca `F1`.

La incertesa RSR instrumental, els termes de correcció L3, la variabilitat SPD i l'ambigüitat angular continuen separades i sense nombres inventats. La quantificació sistemàtica pertany a 7.16; el contrast empíric clear-sky, a 7.17. El Pas 7.5 necessita almenys una cadena RSR/guany/producte/període acreditada i un model L3→font amb priors SPD i angulars aplicables abans de poder generar un `SourceModel` d'una observació real.

## Via tècnica següent

La via més prometedora és obtenir la taula anual efectiva SNPP de Black Marble C2 o una acreditació equivalent de la resposta NOAA-20 de 2026, juntament amb el llinatge de guany/PGE; després, reunir mesures multiespectrals i multiangle o priors verificats que permetin acotar l'operador L3→font. Les figures RSR, els guanys radiomètrics i les formes angulars genèriques no substitueixen aquests assets. Fins que hi siguin, cap font no entra a la ruta física de producte.
