# Glossari i unitats

| Terme | Definició / unitat |
|---|---|
| radiància espectral | potència per àrea projectada, angle sòlid i longitud d'ona; `W m⁻² sr⁻¹ nm⁻¹` |
| radiància de banda | integral espectral; `W m⁻² sr⁻¹` o unitat declarada |
| irradiància | flux incident per àrea; `W m⁻²` |
| intensitat radiant | flux per angle sòlid d'una font; `W sr⁻¹` |
| luminància | radiància ponderada fotòpicament; `cd m⁻²` |
| profunditat òptica `τ` | integral de `β_ext ds`; adimensional |
| transmitància `T` | `exp(-τ)`; adimensional |
| `β_ext` | coeficient d'extinció; `m⁻¹` |
| `β_sca` | coeficient de dispersió; `m⁻¹` |
| `β_abs` | coeficient d'absorció; `m⁻¹` |
| `ω0` | single-scattering albedo `β_sca/β_ext`; adimensional |
| funció de fase | densitat angular de dispersió; normalitzada a 1 sobre 4π, `sr⁻¹` |
| estereoradià | unitat SI d'angle sòlid, `sr` |
| AOD | aerosol optical depth; adimensional, especificar longitud d'ona |
| SPD | spectral power distribution; en aquest dossier, forma espectral normalitzada o radiància espectral segons context |
| RSR | relative spectral response; funció adimensional relativa del sensor |
| VNP46 | família NASA Black Marble escollida com a font operativa; producte/release concret versionat |
| DNB | canal VIIRS que defineix el model de mesura espectral de l'observació VNP46 |
| `BAND_INTEGRATED` | operador de mesura adoptat per normalitzar la resposta DNB; unitat exacta del contracte pendent de verificació ATBD |
| radiància observada | valor del producte VNP46 abans de la inferència de font |
| radiància artificial estimada | resultat de `SourceModel`; no és sinònim de radiància observada |
| mag/arcsec² | magnitud logarítmica per angle sòlid aparent; depèn de banda/zero point |
| SQM | instrument/banda pròpia, no sinònim exacte de Johnson V |
| TESS-W | fotòmetre amb resposta espectral pròpia i FOV propi |
| Bortle | escala qualitativa observacional 1–9; no unitat física |
| BortleEquivalent | diagnòstic/política versionada de TerraLab3D; no és la classificació observacional completa |
| reference sky | estat nocturn de referència sense Lluna ni crepuscle per caracteritzar el lloc |
| instantaneous sky | estat físic a data/hora, pot incloure Lluna, crepuscle i atmosfera real |
| photometric projection | transformació post-kernel de radiància espectral a luminància o resposta instrumental |

## Regles

1. No usar «brillantor» sense indicar si és radiància, luminància o magnitud.
2. No convertir VNP46/DNB directament a `cd/m²` sense SPD/resposta; la unitat concreta es llegeix del producte i la de l'ATBD continua pendent de verificació.
3. No sumar magnituds; convertir a radiància, sumar i tornar a projectar.
4. No confondre intensitat radiant de font amb radiància del cel.
5. `P(θ)` sempre documenta la normalització.
6. Angles wire en graus només si el camp ho diu; càlcul intern pot usar radians.
7. Distàncies del kernel en metres; km només presentació/configuració.
8. Qualsevol LUT indica les unitats dels eixos.
9. No hi ha conversió directa VNP46/DNB→SQM ni `relativeRadiance×calibrationFactor→cd/m²` sense model físic/calibratge explicitat.
10. No aplicar `max(0, radiancia_observada)` silenciosament; baixa radiància conserva qualitat/incertesa.
11. LUT/FFT són acceleracions del mateix operador físic i han de declarar domini/error.
12. Cel artificial, natural, lunar i crepuscular se sumen en radiància lineal compatible, mai en magnituds.
13. Les projeccions SQM/TESS declaren resposta espectral, FOV i zero point/calibratge.
14. El `BortleEquivalent` de lloc usa condicions de referència; la Lluna només modifica el cel instantani.