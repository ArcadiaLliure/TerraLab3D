# Domini vertical i cota exterior del gate 7.12

## Abast físic

El [preregistre v1](criteri-transport-preregistrat-v1.json) es va congelar abans de calcular el candidat. La validació és de dispersió simple escalar donats SourceModel, P/T, composició, fases i superfície triangular prescrits. No és una validació observacional de la Terra ni de fonts urbanes Black Marble. Cap factor de calibratge s'ajusta als residuals.

L'ampliació COESA és **optativa**, amb revisió `coesa1975-nasa-tr459-dry-0-75km-v1`. El provider històric 0–50 km conserva revisió, nusos i valors. La taula 3 de [NASA TR R-459](https://ntrs.nasa.gov/api/citations/19760017709/downloads/19760017709.pdf), pàgina impresa 9, afegeix les bases geopotencials 71 i 84,852 km i gradients −2,8 i −2 K/km. S'empra la mateixa conversió d'altura geomètrica a geopotencial i la mateixa hidrostàtica publicada. Per sota de 50 km es delega exactament a la funció antiga.

75 km geomètrics queden sota el límit de massa molar constant de 80 km documentat per COESA i dins 203–293 K de la LUT O3. No es congela, retalla ni extrapola T per encaixar-la en la LUT. NASA distingeix explícitament el règim superior a 86 km, amb composicions d'espècies i formulació diferents: aquest treball no l'implementa. El model exterior següent és una **hipòtesi condicionada d'aire sec**, no una afirmació sobre qualsevol termosfera real.

El perfil O3 0–50 km conserva la prescripció de 7.10. A 60/70/75 km s'afegeix `q=5e-7 exp(-(h-50000)/8000)`, interpolada linealment entre nusos: prescripció reproduïble, sense atribució de climatologia. L'aerosol exterior queda limitat pel mateix exponencial H=1200 m. Les transmissions i la visibilitat es limiten superiorment per 1 per acotar radiància positiva, sense canviar-les al kernel.

## Derivació de la cua

Siguin `P=O+s d`, altura radial `h=|P|−R`, sostre `H`, font central `X` i `sH` el creuament de H per la LOS esfèrica existent. Per a elevacions positives,

```
ds/dh <= JH = (R+H)/sqrt((R+H)^2−b_observador^2).
a = (X−O)·d; b^2 = |X−O|^2−a^2; q=s−a; A=R+hO+a.
(R+h)^2/|P−X|^2 <= (q+A)^2/(q^2+b^2).
```

Amb `q>=qH>0` i `A>0`, el màxim de la darrera expressió es troba entre el cap qH, el punt estacionari `b²/A` si pertany al domini i el límit a l'infinit **1**. Aquest límit es conserva encara que no es calculi cap capa per damunt de 75 km. Per a una font d'àrea continguda dins de radi `rA` respecte del centre, s'infla el màxim per `(1−rA/rH)^−2`, amb `rH=|O+sH d−X|` i `rA<rH`. Això cobreix cada punt de l'àrea; no substitueix l'àrea per una font puntual al transport.

La hipòtesi exterior és

```
dP/dh = −m n g0 (R/(R+h))²,
m >= 0,0289644/N_A kg, P>=0 i no creixent.
```

Per tant,

```
∫[H,∞] n(h)/r_font(h)^2 ds
 <= JH Fmax/(m_min g0 R²) ∫[H,∞] (−dP)
 <= JH Fmax P(H)/(m_min g0 R²).
```

**No es pressuposa P(infinit)=0**: la caiguda total de pressió és com a màxim P(H). La massa efectiva del COESA inferior amb la constant R històrica i kB actual és lleugerament superior a m_min; la desigualtat de massa és una hipòtesi exterior expressa, inadequada per a una exosfera arbitrària dominada per H/He.

Per a l'aerosol prescrit, la columna ponderada queda limitada per

```
JH Ha exp(−H/Ha)/(rH−rA)².
```

La cota multiplica aquestes columnes per l'envolupant d'intensitat angular normalitzada, la potència/SPD definida i les envolupants de secció eficaç/fase. Rayleigh usa fase màxima ≤3/(8π) i màxim de sigma al cap esquerre de cada interval visible. HG usa `(1+|g|)/(4π(1−|g|)²)`; fases tabulades usen el màxim de la taula normalitzada. S'integra exactament amb GL2 el producte de fins a tres corbes lineals positives SPD/respostes a la unió de nusos; sigma i Ångström es limiten pels màxims d'interval. Absorció i ombres només poden reduir aquesta contribució exterior de dispersió simple.

El pressupost prospectiu de cua és **0,001 mag**, separat del pressupost espectral de 0,01 mag. La magnitud de la cota és `2,5 log10(1+I_cua_superior/I_finit)`. Els errors numèrics de I_finit es documenten separadament. La implementació incorpora marge d'arrodoniment, però no és aritmètica d'intervals certificada.

## Errors que aquesta cota no resol

No quantifica dispersió múltiple, meteorologia, aerosol real desconegut, altres absorbidors, incertesa experimental de seccions eficaces, inferència d'emissió C/H, detall DEM no mostrejat o datum vertical. La contribució de qualsevol atmosfera real que incompleixi les hipòtesis continua sense acotar. La concordança amb SG-REF valida l'avaluació numèrica del model declarat, no aquestes hipòtesis.
