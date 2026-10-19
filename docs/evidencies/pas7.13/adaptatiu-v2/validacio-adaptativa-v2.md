# Reconstrucció angular adaptativa — candidat v2

Tancament del 2026-10-19. **[PASS científic en el domini preregistrat](gate-adaptatiu-v2.json)**: 900 holdouts de reconstrucció en tres fixtures S/C i tres holdouts addicionals de perfil COESA, tots dins de 0,01 mag. Els 921 contrasts de transport passen. Proves, regressions i sis figures verificades; 7.13 completat exclusivament en aquest domini. 7.14 no s’ha iniciat.

## Procedència i preservació

[Instrucció de rendiment GitHub83272b8](https://github.com/ArcadiaLliure/TerraLab3D/blob/83272b83686d26baa7540fec128165cc9775158e/docs/skyglow/21-estrategia-rendiment-interactiu.md), contrastada amb HEAD de la branca remota. Les acceleracions de fonts, vectorització addicional i multicore romanen a7.18–7.22. El [candidat v1 fallit](../validacio-camp-angular.md), els seus preregistres, tests i247evidències anteriors es preserven; el seu commit immutable és11ce68b2eb8f9a51d4701143a2ad68c095eacb10.

## Preregistre i independència

[Criteri v2](criteri-adaptatiu-preregistrat-v2.json), SHA256 `1b75bda8a311b65eecaecfb3f47ebdef51406f690935e2c12f836040b8f42b3f`, congelat abans d'avaluar. Acceptació0,01mag heretada sense relaxació; marges interns de refinament0,002mag. Els [300punts independents](punts-independents-preregistrats.json) de cada escenari inclouen160distribuïts per la semiesfera,60prop de l’horitzó,60prop de la font,16punts de gradient pronunciat i4de wrap. No s’envien al refinador. El camp complet es congela abans de consultar el holdout i se’n verifica el hash durant l’acceptació.

El pressupost espectral0,01mag i el transport10⁻⁴/SG-REF10⁻⁶ continuen separats de la reconstrucció. Tres refinaments GL2/4/8, trajectes4/8/16, àrea2/4/8 i GK21 amb les precisions de7.12. Cap ajust d’amplitud o calibratge.

## Operador i mostreig

Mateix PropagationKernel, mateixes precisions, suma lineal abans del logaritme. PCHIP vertical sobre log(B+ε) amb nusos irregulars diferents per azimut; PCHIP log periòdic en azimut amb quatre perfils veïns. Probes interiors1/4,1/2,3/4: quan fallen, es promou el punt o perfil mitjà. Les pendents veïnes es tornen a comprovar després de refinar. El registre de nodes exactes és local a una construcció/revisió: no és cache entre peticions ni acceleració espacial de fonts.

Zeros coneguts, barreres i DEM sense continuïtat acreditada exigeixen directe; cap alfa o suavitzat. El refinador rebutja geometries DEM/àrea fins a acreditar-ne la interpolació. Aquestes fonts continuen executables per la ruta directa existent; els controls nous les contrasten amb SG-REF. La sortida raw v2 i la convergència dels probes no concedeixen PASS a peticions arbitràries: el gate independent està separat i vinculat al hash del camp.

## Domini prospectiu

Tres fixtures puntuals S/C a5km a l’est, observador100m i cambra homogènia prescrita finita75km, elevació0,5–90°. S:1W LED-B3; C: models realista i kelvins3000K de7.5.1, amb SPD, amplitud, normalització i escala relatives conservades, geometria traslladada explícitament. No és una reconstrucció urbana observada.

COESA1km0–75km, O3 i aerosols prescrits: tres controls nous representatius (horitzó, gradient proper a font i direcció lateral alta), amb cota positiva de contribució>75km segons les hipòtesis seques hidrostàtiques de7.12. Aquests controls no homologuen una reconstrucció angular COESA general. No es torna silenciosament a10km. Es conserven22,45% omesos de10km vs50km a la fixture històrica B4 i el caràcter condicionat de la cua75km.

Àrea400×400m i terreny: controls directes finits, sense compressió angular acreditada. La cobertura DEM absent és error, no radiància nul·la. El domini d’ús de qualsevol resultat aprovat ha d’incloure aquests límits i exigir ruta directa fora del camp acreditat.

## Cost prospectiu

Màxim8000nodes i1800s per fixture; màxim7200s de campanya científica. Pilot històric0,195s/LOS de cambra i0,0803s/SG-REF fi: projecció4680s de construcció màxima,392s de holdout i630s de controls COESA, amb marge per als controls directes DEM/àrea. Abans de cada fase es registra una estimació amb el cost ja consumit. Les execucions científiques són seqüencials. El constructor comprova temps abans de cada nova LOS; no és un timeout preemptiu d’una integral en curs. El gate comprova els temps reals finals. No es generen malles COESA/extenses denses ni s’alteren quadratures. Cap SLO de producte o afirmació de speedup.

## Reconstrucció independent: resultats mesurats

Els tres camps es van congelar abans dels holdouts. Cadascun conté 54 perfils azimutals i 717 nusos verticals finals, construïts amb 7.736 LOS exactes, inclosos els probes descartats. Cap dels 300 punts independents de cada escenari coincideix amb cap node del registre de construcció, tampoc amb els probes que no han quedat al DTO.

| Escenari | Error màxim protegit vs SG-REF (mag) | Punts independents | Construcció (s de paret) | CPU (s) | DTO JSON (bytes) |
|---|---:|---:|---:|---:|---:|
| S LED-B3, 1 W definit | 0,001894297 | 300 PASS | 872,724 | 856,891 | 28.747 |
| C realista | 0,001882484 | 300 PASS | 828,375 | 815,469 | 27.513 |
| C kelvins, 3.000 K | 0,001886757 | 300 PASS | 832,065 | 820,156 | 27.506 |

El límit d’acceptació continua sent **0,01 mag**. L’error protegit compara la reconstrucció amb els dos extrems `R ± u_REF`; també s’exigeix el límit davant el mateix kernel directe. Els màxims dels probes d’ajust són inferiors a 0,002 mag, però no són l’evidència d’acceptació. Les 900 comparacions de transport dels holdouts passen el gate relatiu `10⁻⁴`; el màxim protegit és `1,238·10⁻¹⁰`. No hi ha factors d’ajust.

La construcció ha consumit 2.533,163 s en total; la fase de holdout, 200,184 s, davant els 392,31 s estimats. S’hi mesuren separadament 99,913 s de kernel i 69,334 s de SG-REF; els 30,936 s restants inclouen reconstrucció, serialització i arrencada. Els controls complementaris només mesuren el kernel i la fase sencera, sense atribuir tot el residual a SG-REF.

## Controls de domini i discontinuïtats

Els 18 controls complementaris passen el gate de transport:

- **COESA:** tres direccions S/C a 0,83°, 1,37° i 47,3°, amb azimuts preregistrats. Kernel: 174,061 / 173,352 / 173,108 s respectivament. Les cotes de cua >75 km són positives: `8,825·10⁻¹¹`, `1,429·10⁻¹⁰` i `2,789·10⁻⁷` mag, sota les hipòtesis de 7.12. No són una cota universal de tota l’atmosfera.
- **Terreny:** 12 direccions al voltant de la carena prescrita, sis zeros exactes i sis resultats positius. SG-REF confirma els zeros i el transport; no s’interpolen les transicions ni es dedueix la posició exacta del salt a partir d’aquest mostreig finit. La cobertura absent continua sent error, mai zero.
- **Font extensa:** tres direccions de la font uniforme de 400 × 400 m, amb integració directa. Error relatiu protegit màxim `9,470·10⁻⁷`, sense aprovar compressió angular d’àrea. Aquesta cambra no es fa servir per revisar a la baixa el cost històric d’uns 609 s/LOS extensa COESA de 7.12.

La fase ha costat **574,281 s**, davant els 820 s estimats abans d’executar-la. Les geometries DEM i d’àrea es rebutgen al constructor adaptatiu; el consumidor ha d’emprar el transport directe existent. En camps amb barreres o topologia de visibilitat desconeguda, l’ús acreditat és `directOnly=true`: la v2 no acredita interpolació azimutal segmentada ni pendents a través de barreres. `None/null` significa que cal una LOS directa, no transparència.

## Control addicional de reconstrucció COESA

El [preregistre específic](criteri-perfil-coesa-preregistrat-v2.json), congelat abans de les mesures, fixa azimut 270,7°, nusos de suport a 30/45/60/90° i tres holdouts independents a 48,73/52,19/57,41°. Només es contrasta l’interval 45–60°; no s’aprova una semiesfera COESA. Es conserva el perfil atmosfèric d’1 km, el sostre de 75 km i totes les quadratures. El perfil s’ha de congelar abans de calcular els holdouts.

El [perfil congelat](perfil-coesa-congelat.json) es contrasta amb els [holdouts](perfil-coesa-holdout.json):

| Elevació independent | Error protegit de reconstrucció (mag) | Error relatiu protegit de transport | Cota positiva >75 km (mag) |
|---:|---:|---:|---:|
| 48,73° | 0,001205805 | 2,933·10⁻¹² | 2,893·10⁻⁷ |
| 52,19° | 0,004435952 | 1,382·10⁻¹² | 3,087·10⁻⁷ |
| 57,41° | 0,004964471 | 3,528·10⁻¹² | 3,360·10⁻⁷ |

Els tres passen sense canviar els quatre nusos ni el llindar. El cost real addicional és **1.273,611 s**, davant els 1.406 s estimats. La cua superior es manté positiva; la cota històrica més exigent de 7.12, 0,000472296 mag en la fixture llunyana, també es preserva. La nova cota petita de la font propera no la substitueix ni és una cota universal.

## Cost total i domini d’acceptació

La suma de construcció i fases científiques mesurades és **4.581,239 s (76,35 min)**, inferior als 7.200 s preregistrats. Exclou els pilots històrics, l’espera entre fases, la documentació, les regressions i la generació dels gràfics; no és el temps total de la sessió ni un SLO de producte. Hi ha 23.208 LOS de construcció, 900 de holdout, 18 controls i set LOS del perfil COESA: **24.133 avaluacions runtime**, més les referències independents. Els 717 nusos per camp són els que es conserven al DTO; les 7.736 mostres inclouen probes i perfils auxiliars.

L’acceptació aprova les tres fixtures puntuals homogènies registrades i els seus 300 punts independents per escenari, més el perfil COESA fix a 270,7°/45–60° amb tres holdouts. Una validació finita no és una demostració uniforme sobre totes les direccions o totes les atmosferes. No s’aproven compressió azimutal COESA general, interpolació DEM ni compressió de fonts extenses; el transport directe continua disponible per a aquests casos. Els camps amb barreres de visibilitat requereixen `directOnly=true`. No s’ha modificat el planning d’acceleracions 7.18–7.22.

## Pressupostos d’error separats

La reconstrucció angular de 0,01 mag no absorbeix altres errors. El transport directe i la incertesa SG-REF tenen gates propis; la discretització espectral conserva el pressupost preregistrat de 0,01 mag i les evidències de 7.4/7.10; la cua atmosfèrica conserva 0,001 mag condicionat. El DEM és una superfície triangular prescrita amb datum explícit, no una garantia universal del relleu real. La composició atmosfèrica real, la dispersió múltiple i la inferència d’emissió C són incerteses físiques separades. La concordança numèrica no és exactitud observacional.

## Proves, figures i tancament

Les [495 proves backend](pytest-backend.txt) passen amb avisos com a errors, incloses les 21 noves. La [suite frontend](tests-frontend.txt) conserva les 621 comprovacions PCHIP històriques i afegeix 768 de la v2; [typecheck](typecheck-frontend.txt) i [build](build-frontend.txt) passen. Ruff/format i Pyright afectats nets. Pyright global conserva exactament el mateix multiconjunt de 67 errors/3 avisos, amb 320 fitxers analitzats davant els 318 anteriors. [Regressions exactes](regressions-i-preservacio-v2.json): B0/900 LOS, quatre columnes, 36 fitxers científics de 7.12 i 247 evidències anteriors sense canvis.

Les regressions i els gràfics s’han executat després del control COESA, sense interferir en el seu cronometratge. Els mapes es generen a partir dels camps congelats: la graella de presentació de 759 azimuts ×110 elevacions no afegeix LOS ni evidència independent. Escala, unitats, procedència i límit d’error són explícits. Les modalitats C comparteixen escala relativa i normalització original: en aquesta graella, 3.000 K dona entre **1,4409% i 2,0034%** més radiància ponderada que realista, sense calibratge absolut ni equivalència amb mesura urbana. [Valors de la graella](diagnostics-grafics-v2.json).

Les sis figures s’han inspeccionat visualment:

- [Mapa de calor S/C](mapa-calor-adaptatiu-v2.png), amb color logarítmic i escala C compartida.
- [Nusos adaptatius i holdouts](mostres-adaptatives-i-holdout.png), amb elevació logarítmica per veure el refinament prop de l’horitzó.
- [Errors independents](errors-independents-v2.png), amb el llindar original de 0,01 mag.
- [Diferència realista/kelvins](diferencia-realista-kelvins.png), a escala relativa conservada.
- [Perfil COESA i error](perfil-coesa-i-error.png), només en l’interval preregistrat.
- [Oclusió directa](oclusio-directa-v2.png), amb els sis zeros exactes sense unir els punts a través del salt.

La [preservació inicial](preservacio-inicial.json) registra 247 fitxers històrics; el gate i les regressions n’han comprovat els hashes, juntament amb el candidat i els preregistres. La [reproducció](README.md) descriu els CLI i les dades. La skill `plan` s’ha aplicat; `terralab-manel-style` continua absent i s’utilitzen les normes locals. Cap commit automàtic ni treball de 7.14. El punt de represa és 7.14 pendent; el domini no s’amplia sense una nova validació prospectiva.

[Auditoria documental](auditoria-documental-resum.json): 355 incidències heretades tant a l’inici com al final, cap de nova, cap del pas executable i zero enllaços locals trencats. El [manifest final](manifest-codi-evidencies-v2.json) vincula codi, documents i dades d’aquesta versió; el [registre de tancament](tancament-pas7.13-v2.json) conserva el domini, els controls i el punt de represa.
