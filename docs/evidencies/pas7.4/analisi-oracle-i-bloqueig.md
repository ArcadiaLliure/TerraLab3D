# Pas 7.4 — Oracle fi, fonts tabulades i estat del gate V3

> **Històric anterior al requisit aprovat:** el bloqueig descrit a continuació va quedar superat quan TerraLab3D va aprovar i congelar el [criteri de 0,01 mag](criteri-preregistrat-v1.json). El resultat vigent i el domini homologat són a [homologacio-bandset-v1.md](homologacio-bandset-v1.md). Es conserva aquesta evidència sense reescriure la recerca prèvia.

Data: 2026-10-18. Estat: **oracular diagnòstic verificat; `SpectralBandSet` v1 bloquejat**.

## Recursos obtinguts i integritat

Les cinc taules CIE i els seus JSON de metadades són a `resolve_data_root()/data/earth/light-pollution/spectral-oracle/cie/`, fora de Git. El [manifest](cie-asset-manifest.json) registra pàgina oficial, nom, MD5 publicat, SHA-256, graella i llicència **CC BY-SA 4.0**. El [script](../../../tools/analyze_spectral_oracle_step7_4.py) comprova els dos checksums contra cada metadata oficial abans d'integrar res. Dades consultades directament: [LEDs típics, 1 nm](https://cie.co.at/datatable/relative-spectral-power-distributions-illuminants-representing-typical-led-lamps-1nm), [làmpades de descàrrega d'alta pressió, 5 nm](https://cie.co.at/datatable/relative-spectral-power-distributions-high-pressure-discharge-lamp-illuminants), [LED de referència L41](https://cie.co.at/datatable/cie-reference-spectrum-l41), [eficiència fotòpica V(λ)](https://cie.co.at/datatable/cie-spectral-luminous-efficiency-photopic-vision) i [observador XYZ 1931 de 2°](https://cie.co.at/datatable/cie-1931-colour-matching-functions-2-degree-observer). Les metadades CIE declaren interpolació lineal i extrapolació zero; els SPD són *relatius* i qualificats d'«approximated», les funcions V/XYZ són «nominal».

Les RSR provenen dels manifests externs de [7.3, SNPP](../pas7.3/recerca-rsr-2026.md) i [7.3, NOAA-20/21](../pas7.3/revisio-multisatel-lit.md). El script les llegeix amb el repositori verificat de 7.3 i conserva plataforma, guany, release, interval de validesa, URL i SHA. Són **LGS SNPP 2013** i **LGS/MGS J1/J2 de prelanzament**. L'HGS de J2 és un proxy de MGS, no una sisena RSR independent. Cap d'aquestes corbes està acreditada com a resposta efectiva Black Marble L3 del 2026.

## Càlcul reproduïble

Ordre des de l'arrel del repositori, amb la biblioteca de dades TerraLab configurada:

```powershell
python tools/analyze_spectral_oracle_step7_4.py --output docs/evidencies/pas7.4/diagnostic-oracle-cie-rsr.json
python -m pytest backend/tests/test_spectral_oracle_step7_4.py -q
```

L'[oracle independent](../../../backend/src/terralab3d/domain/light_pollution/spectral_oracle.py) integra el producte de SPD i respostes adimensionals amb Gauss–Legendre, partit a **tots** els nusos tabulats. No reutilitza l'integrador analític de 7.3, no normalitza implícitament cap RSR i rebutja domini sense suport declarat. Les proves verifiquen una integral polinòmica exacta, una línia triangular sintètica d'1 nm que una quadratura gruixuda podria perdre, les unitats, el suport i les entrades invàlides. L'ordre 4/8/16 és una comprovació de quadratura, **no un pressupost PASS/FAIL**.

El [JSON diagnòstic](diagnostic-oracle-cie-rsr.json) inclou 9 LED, 5 HP, L41 i 2 mescles sintètiques LED+HP amb meitat d'àrea visible normalitzada cadascuna. Per a la projecció V(λ) entre 380 i 780 nm, la diferència absoluta màxima entre ordres 8 i 16 és `9.095e-13` en unitats relatives·nm. La columna Y de l'XYZ oficial coincideix punt per punt amb V(λ), i la diferència integrada és zero als 17 casos. Aquesta coincidència comprova lectura i etiquetatge de les taules; **no** és una validació metrològica independent ni una cota d'error del model físic. La quadratura és exacta fins a arrodoniment per als productes de dues corbes lineals a trossos d'aquests casos.

Per comparar RSR històriques sense confondre cobertura, el diagnòstic restringeix **totes** al suport visible comú `417.012–780 nm` i calcula `∫SPD·RSR / ∫RSR` en aquest mateix interval. Per LED-B1, el canvi J1 MGS/LGS és `+1.088 %` i el J2 MGS/LGS `+3.185 %`; per HP1, `−0.280 %` i `+3.957 %`, respectivament. Són sensibilitats de les **taules històriques i SPD relatius**, no incerteses del producte, no una comparació entre satèl·lits operatius i no un percentatge admissible d'error de bandes. El DNB complet s'estén fora d'aquest interval.

## Evidència, inferència i dada absent

**Evidència directa:** integració independent i tests; checksums oficials CIE i SHA locals; etiquetes/condicions de les taules; RSR històriques amb procedència; domini de comparació explícit. La [CIE 214:2014](https://cie.co.at/publications/effect-instrumental-bandpass-function-and-measurement-interval-spectral-quantities) confirma que interval de mesura i amplada de banda poden afectar quantitats espectrals, però la fitxa pública no estableix un llindar de TerraLab3D per al skyglow.

**Inferència limitada:** una graella HP de 5 nm no reconstrueix estructura subgraella; els SPD CIE relatius i aproximats no representen per si sols les fonts urbanes inferides de Black Marble. L'acord de quadratura sobre taules lineals no posa cota a aquest error d'entrada, a la resposta 2026, ni al transport atmosfèric. La diferència LGS/MGS visible reforça que la tria de RSR és material, sense demostrar cap tolerància acceptable.

**Bloqueig exacte:** abans de provar o seleccionar un `SpectralBandSet` candidat manca un **pressupost numèric d'error de discretització espectral justificat i preregistrat**, amb mètrica, unitat, domini, observables que cobreix, origen i evidència, segons la política V1. Tampoc hi ha una família RSR operativa 2026 acreditada ni un domini espectral complet de fonts/respostes atmosfèriques i instrumentals que permeti afirmar homologació de producte. La convergència de quadratura de les taules CIE no autoritza a escollir retrospectivament un percentatge PASS/FAIL. Per tant **no s'ha avaluat cap candidat**, no hi ha `bandSetId` v1 i V3 roman obert. El pas 7.5 no s'inicia.

La via tècnica més directa és acreditar almenys un domini operatiu complet amb SPD/RSR i funcions de resposta/transport rellevants, establir la mètrica i la cota d'error a partir d'una font metrològica, incertesa de l'oracle o requisit de producte aprovat, registrar-ne la congelació **abans** de comparar candidats i aleshores executar la selecció. Els assets diagnòstics actuals romanen reutilitzables per a aquesta feina.
