# Represa7.14: qualificació nominal i diagnòstic del cost

Execució del **2026-10-21**. El [gate v3](gate-represa-v3.json) conserva **PASS numèric** i **`BLOCKED_NOMINAL_RESPONSE_OR_COVERAGE`** científic. No s’ha iniciat7.15. Els llindars, el kernel, la retenció, les conversions i els projectors de v1/v2 no han canviat.

## Resultat científic

La [recerca específica](fonts-mancances-i-vies-v3.md) identifica configuracions SQM-L/SQM...2 i TESS-W separades, les dades que falten i vies concretes per obtenir-les. No s’ha recuperat una resposta conjunta nominal completa amb convenció de λ, suport/cues i cobertura suficients. No s’afirma la inexistència universal de dades públiques; es delimiten les fonts recuperades, els errors d’accés i els annexos comprovats. El [registre de candidats](perfils-candidats-i-mancances-v3.json) no adopta cap perfil nou.

El model nominal AB continua sense exigir calibratge individual. Les lectures natives i observades tenen requisits addicionals. Un producte ideal de components no substitueix camins òptics desconeguts; una gaussiana de control no acota per si sola el FOV real. El camp CIE escalar i les13 LOS retingudes no cobreixen la integral angular espectral SQM/TESS. No es declaren zeros a les zones desconegudes ni es renormalitzen retalls.

Es mantenen S en SI i C relatiu, realista/kelvins, zeros/visibilitat i límits DEM/àrea. COESA conserva75km i la cota exterior positiva condicionada de7.12/v2; la contribució superior no es fa nul·la. La dada històrica B4 del22,45% omès a10km continua vigent en el seu context. Cap nova homologació angular general o observacional, magnitud nativa o Bortle.

## Preregistre i cost mesurat

El [preregistre diagnòstic v3](criteri-diagnostic-preregistrat-v3.json), SHA-256 `09a7333914203de2a4ffb810215f89f6879cedcaf65c324f2226a1f466acb2e6`, conserva0,01mag espectral i total,10⁻¹⁰ relatiu de projecció,0,001mag assignat a cobertura i0,0001mag de quadratura FOV. No es crea un pressupost0,011mag. Preveia40s de càlcul, màxim180s,13 casos retinguts, tres repeticions i un perfilatge, en sèrie amb un fil BLAS/OMP i zero LOS noves.

El [diagnòstic cru](cost-projeccio-v3.json) mesura **14,625s** de càlcul intern total; les13 projeccions costen **0,810–0,907s**. Tres repeticions sense profiler del cas S_B4_chamber_point_5km-0 donen0,818/0,817/0,805s. Descodificar els13 espectres costa0,000928s i preparar la resposta0,03737s, per separat. No s’atribueix a aquest projector el cost3–5ms del projector lineal anterior.

| Funció / una projecció de968 panells | Crides | Temps inclusiu amb cProfile |
|---|---:|---:|
| `leggauss`, reconstrucció de regles GL | 2.904 | 0,7790s |
| `at_vacuum`, resposta en coordenada explícita | 54.720 | 0,1645s |
| Densitat quadràtica retinguda | 32.832 | 0,06646s |
| Preparació de nusos transformats | 1 | 0,003433s |

El [perfil complet](cprofile-cumulative-v3.txt) i el [fitxer pstats](projeccio-cie-v3.prof) corresponen a1,150s **instrumentats**, diferents dels temps de paret sense profiler. Les2.904 crides a `leggauss` són tres passades sobre968 panells: ordre8, ordre16 i estimació LOS ponderada d’ordre16. Acumulen aproximadament67,7% del temps instrumentat; no se sumen amb el temps inclusiu del seu integrador pare. Aquesta repetició és independent del valor de radiància i explica la major part del cost observat. No s’ha modificat el runtime, introduït cache, vectorització, multicore o acceleració espacial. Es registra la causa per a una decisió posterior amb el planning intacte; no es promet cap factor de millora o SLO.

![Cost de projecció i funcions perfilades](cost-projeccio-v3.png)

## Proves i regressions realment executades

- Les13 projeccions repetides coincideixen **exactament** amb els senyals congelats de v2 i passen contra els seus oracles independents QUADPACK, amb màxim relatiu2,2205·10⁻¹⁶ davant10⁻¹⁰. S’han repetit les projeccions del candidat, sense tornar a calcular l’oracle ni el transport.
- Els [auditors numèrics v1](gate-numeric-v1-repetit-v3.json) i [v2](gate-numeric-v2-repetit-v3.json) es tornen a executar amb les mateixes entrades, hashes i comprovacions. Només se’n redirigeixen les sortides a v3, sense sobreescriure evidències. Es revaliden els resultats arxivats de10.624 i21.184 contrasts espectrals; **no** s’ha repetit la campanya d’integració espectral ni s’ha homologat una banda instrumental nova.
- [540 proves backend](pytest-backend-v3.txt) PASS en51,74s de pytest,53,498s de procés. No hi ha canvi de codi científic ni necessitat de proves unitàries noves per a una física no implementada. [Frontend](frontend-tests-v3.txt), [typecheck](frontend-typecheck-v3.txt) i [build](frontend-build-v3.txt) PASS. [Ordres, sortides i costos](regressions-v3.json).
- [B0 i quatre columnes](columnes-b0-v3.json) repetits i exactes. Signatura B0 `21d3453df822b95d56aa508fee6bd9c76e712b27c63f3f03a3222e86e075b53e`. Els benchmarks B0–B4 i costos de transport previs no s’han sobreescrit ni repetit.
- Els nous auditor, perfilador i figura passen Ruff i Pyright de l’abast. El backend científic conserva els99 hashes de fonts v2; la comprovació global Pyright es documenta separadament de l’abast nou, sense atribuir-li zero errors globals.
- [Preservació inicial](preservacio-inicial-v3.json): **576 fitxers d’evidència anteriors** intactes,99 fonts intactes i25 documents/atributs anteriors conservats byte per byte en [ZIP](instantanies-documents-v2.zip). Els preregistres v1/v2 i el candidat fallit7.13 continuen íntegres. El manifest final distingeix documents vius actualitzats i evidències congelades.
- L’auditoria documental compara amb l’estat trobat a l’inici d’aquesta execució: **280 incidències mecàniques heretades**. El recompte històric v2 de355 es preserva. A l’inici ja hi havia cinc tasques històriques marcades com a suprimides a Git; s’han registrat, no modificat ni restaurat. No s’atribueix aquella reducció a aquesta execució.

Un primer intent de l’embolcall d’auditoria es va aturar perquè v1 escriu també un delta de tipatge: ara es comprova que aquell delta coincideix amb l’original i es redirigeix igualment. Cap evidència anterior es va arribar a modificar. Ruff inicial va detectar imports després de preparar `sys.path`; s’ha eliminat aquella preparació innecessària. No són canvis del candidat numèric ni d’un llindar.

Les [primeres comprovacions finals](comprovacions-finals-primer-intent-v3.zip) també es conserven: Pyright desconeixia l’atribut dinàmic `pstats.Stats.stats`, ara llegit amb un tipus explícit, i el guard de preservació va impedir sobreescriure el primer gate en afegir la comprovació del ZIP de metadades. Aquell [primer gate](gate-represa-v3-abans-check-metadades.json) continua arxivat; el [vigent](gate-represa-v3.json) afegeix integritat, amb els mateixos criteris i PASS numèric. Les comprovacions finals passen: Pyright nou0/0, global amb els mateixos67 errors/3avisos,280 incidències documentals heretades i cap enllaç viu trencat. No s’ha tornat a executar física per aquestes correccions d’eines.

Descàrregues, lectura de fonts, proves, gràfic i auditories queden fora dels14,625s de càlcul diagnòstic. Les ordres finals i el control d’enllaços consten a [comprovacions finals](comprovacions-finals-v3.json). El gate complet retorna1 pel bloqueig científic explícit; el numèric retorna0.

## Reproducció i represa

Des de l’arrel, sense repetir transport:

```powershell
python -X utf8 tools/audit_photometry_nominal_step7_14_v3.py --numeric-only
python -X utf8 tools/audit_photometry_nominal_step7_14_v3.py
python -X utf8 tools/audit_photometry_nominal_step7_14_v3.py --verify-manifest
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
python -X utf8 tools/profile_photometry_step7_14_v3.py --output .runtime-photometry-v3/nova-mesura
python -X utf8 tools/plot_photometry_nominal_v3.py --output .runtime-photometry-v3/nou-grafic.png
```

Les sortides de perfilatge/gràfic han de ser noves. L’auditor conserva les sortides anteriors i en comprova la identitat. El gràfic es reconstrueix de la mesura arxivada, no d’una mesura física nova. El manifest de v2 inclou documents vius que ara han canviat; per comprovar el candidat vigent s’utilitza el manifest v3 i el seu ZIP de preservació.

El [Pas7.14](../../../tasques/pendent/pas7.14-photometric-projections.md) segueix pendent i parcial. La represa requereix les dades concretades al [registre](perfils-candidats-i-mancances-v3.json) i una nova campanya prospectiva sobre el perfil seleccionat. No repetir investigacions tancades sense novetat. **No iniciar7.15;7.18–7.22 sense alterar ni anticipar.**
