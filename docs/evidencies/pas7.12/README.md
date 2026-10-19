# Evidències del Pas 7.12

**Completat en domini numèric condicionat.** [Informe final](validacio-gate-transport.md) i [veredicte agregat](resultat-gate-transport.json). No s'ha iniciat 7.13.

- [Preregistre immutable](criteri-transport-preregistrat-v1.json) i [SHA-256](criteri-transport-preregistrat-v1.sha256), congelats abans de calcular el candidat.
- [Vinculació del candidat](campanya-v1/vinculacio-candidat-v1.json): codi, nou fixtures primàries, SPD, camp, composició i malla complets.
- [Mesures crues](campanya-v1/): dues passades per fixture primària, tres refinaments independents, etapes i memòria de procés; 42 casos de convergència vertical completats.
- [Domini i prova de cua exterior](domini-i-cota-exterior.md), amb límit a l'infinit i sense exigir pressió exterior nul·la.
- [Llibre d'errors numèrics](llibre-errors-numerics.json), [cota inicial per perfils](cota-lut-per-perfil.json) i [cota analítica refinada](cota-lut-refinada-i-pressupost.json). La cota inicial ampla no és una observació d'error de radiància.
- [Diagnòstics complets de quadratura i dependències](diagnostics-complets-quadratura.json): sostre 10 km només per auditar estimadors, no per acreditar el domini atmosfèric.
- [Compatibilitat C realista/K](compatibilitat-c-realista-k.json), amb geometria sintètica i escala relativa conservada; cap homologació observacional.
- [Regressions i preservació](regressions-i-preservacio.json), [proves backend](proves-backend.txt), [anàlisi estàtica](analisi-estatica.txt) i [Pyright global](pyright-global.json).

La sortida crua del kernel conserva esquemes i marcadors històrics; el veredicte d'aquest gate és un artefacte separat i limitat a les entrades registrades. Les evidències 7.1–7.11 es conserven byte a byte. Cap resultat nou valida H, calibratge urbà, dispersió múltiple o aire terrestre complet.

[Cost actual B0/B1/B2/B4](rendiment-b0-b4-actual.json), [controls de quadratura separats](controls-independents-quadratura.json), [figura de gate/sostre](gate-i-convergencia-vertical.png) i [figura de cost](cost-transport-i-oclusio.png).

[Manifest final de codi, assets i evidències](codi-i-assets-finals.json).
