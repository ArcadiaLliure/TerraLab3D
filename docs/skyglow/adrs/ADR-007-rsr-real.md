# ADR-007 — Utilitzar la RSR real del DNB

- **Estat:** Acceptada amb revisió multisatèl·lit 2026-10-18 — operador TOA implementat; aplicació L3 nocturna encara bloquejada
- **Data:** 2026-09-28
- **Àmbit:** skyglow físic

## Context

VNP46 era l'única font inicial del [perfil v1](../skyglow-v1-profile.json). El [perfil v2](../skyglow-v2-profile.json) incorpora VJ146/VJ246 com a candidates. Tots deriven d'una mesura DNB de banda ampla, però les seves radiàncies L3 corregides no són la integral TOA crua. Aproximar la resposta per centre/FWHM/rectangle o ignorar plataforma/release/data pot introduir errors espectrals.

## Decisió

Integrar contra una RSR versionada amb checksum/procedència i evidència de categoria explícita, compatible amb plataforma, producte, release, data, guany i domini. Separar operador **TOA** i transformacions **L3**. Una resposta efectiva o proxy oficial pot satisfer el contracte sense RSR MGS/HGS independents només si la seva incertesa i aplicabilitat nocturna al producte C2 es demostren. Una LUT NASA exacta és una possible prova, no un requisit universal.

La vertical usa `measurementOperatorId=BAND_INTEGRATED`. La normalització `A = L / ∫S·R dλ` només és aplicable quan `L` està identificada com a mesura de banda compatible amb aquella RSR i el mateix estat de correcció. No s'aplica directament a cap valor cru L3 de VNP46/VJ146/VJ246. No es normalitza `R` per la seva integral per defecte.

La unitat de `L` està verificada a l'[ATBD VIIRS SDR, §2.1.2.1](https://ncc.nesdis.noaa.gov/documents/documentation/ATBD-VIIRS-RadiometricCal_20131212.pdf#page=38): radiància integrada `W cm⁻² sr⁻¹`; Black Marble L3 l'expressa en `nW cm⁻² sr⁻¹`. La RSR energètica de l'ATBD ja incorpora `λ` i es normalitza al pic. Igualtat d'unitat no prova igualtat física TOA/L3; la [User Guide C2 §2.2 Eq. (1)](https://viirsland.gsfc.nasa.gov/PDF/BlackMarbleUserGuide_Collection2.0.pdf) documenta la transformació. El [Pas 7.3](../../tasques/completat/pas7.3-dnb-rsr-measurement.md) ha tancat el contracte de mesura; l'homologació d'una RSR i un SourceModel nocturns per domini correspon a 7.5/7.16/7.17.

## Conseqüències

Més fidelitat; introdueix gestió de recurs/llicència.

## Alternatives

Es mantenen documentades al TDD i a l'especificació d'algorismes; qualsevol alternativa futura que canviï aquesta decisió requereix un ADR que la substitueixi.

## Validació

Test integral amb fixtures, SNPP LGS diagnòstica i quatre corbes DAWG NOAA-20/NOAA-21; resolució d'identitat, release/data/guany, unitats i procedència. La [matriu SNPP](../../evidencies/pas7.3/recerca-rsr-2026.md) i la [revisió multisatèl·lit](../../evidencies/pas7.3/revisio-multisatel-lit.md) documenten l'homologació RSR pendent per a fonts de 2026. La [guia C2 i grànuls reals](../../evidencies/pas7.3/contrast-granuls-black-marble-c2.md) documenten el contracte de mesura completat a 7.3.

## Estat d'implementació

Implementació parcial documentada a l'[evidència de 7.3](../../evidencies/pas7.3/validacio-model-dnb.md). El tancament exigeix correspondència i incertesa L3 nocturna per una font i període explícits.
