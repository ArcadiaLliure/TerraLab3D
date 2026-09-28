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
| `nW/cm²/sr` | unitat habitual VNL; `1 nW/cm² = 1e-5 W/m²` |
| mag/arcsec² | magnitud logarítmica per angle sòlid aparent; depèn de banda/zero point |
| SQM | instrument/banda pròpia, no sinònim exacte de Johnson V |
| TESS-W | fotòmetre amb resposta espectral pròpia i FOV propi |
| Bortle | escala qualitativa observacional 1–9; no unitat física |

## Regles

1. No usar «brillantor» sense indicar si és radiància, luminància o magnitud.
2. No convertir `nW/cm²/sr` VIIRS directament a `cd/m²` sense SPD/resposta.
3. No sumar magnituds; convertir a radiància, sumar i tornar a projectar.
4. No confondre intensitat radiant de font amb radiància del cel.
5. `P(θ)` sempre documenta la normalització.
6. Angles wire en graus només si el camp ho diu; càlcul intern pot usar radians.
7. Distàncies del kernel en metres; km només presentació/configuració.
8. Qualsevol LUT indica les unitats dels eixos.