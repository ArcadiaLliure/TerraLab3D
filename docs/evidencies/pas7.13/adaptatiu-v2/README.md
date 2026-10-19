# Evidències del Pas 7.13 — reconstrucció adaptativa v2

El [report científic](validacio-adaptativa-v2.md) distingeix reconstrucció angular, transport, cua atmosfèrica i domini d’ús. El [candidat v1](../README.md) conserva el FAIL i totes les mesures originals. No s’ha executat 7.14.

## Registres prospectius

- [Criteri adaptatiu v2](criteri-adaptatiu-preregistrat-v2.json) i [SHA256](criteri-adaptatiu-preregistrat-v2.sha256): 0,01 mag d’acceptació, 0,002 mag de refinament i pressupost de cost.
- [Punts independents](punts-independents-preregistrats.json), generats abans de la construcció i absents del refinador.
- [Vinculació del candidat](vinculacio-candidat-v2.json): hashes del codi científic i entrades completes S/C.
- [Control de perfil COESA](criteri-perfil-coesa-preregistrat-v2.json) i [vinculació](vinculacio-perfil-coesa.json): quatre nodes de suport i tres holdouts, sense malla COESA densa.
- [Preservació inicial](preservacio-inicial.json): hashes dels 247 fitxers històrics protegits.

## Mesures

Els fitxers `*-camp.json` contenen cada camp congelat, tots els nodes de construcció i costos. Els `*-holdout.json` inclouen els resultats directes, els tres refinaments SG-REF, la decisió de transport i els errors de reconstrucció. Els noms distingeixen S, C realista i C kelvins 3.000 K. [Controls de domini](controls-domini.json) conserva les 18 entrades completes de COESA/DEM/àrea i els resultats, inclosos zeros físics i cotes positives de cua.

`perfil-coesa-entrenament.json`, `perfil-coesa-congelat.json` i `perfil-coesa-holdout.json` separen suport, perfil congelat i validació. Les estimacions es registren abans de cada fase; `temps-*.json` dona el cost real. `log-*.txt` conserva la sortida progressiva. El mostreig de memòria és una captura del procés durant la construcció, amb el màxim conegut fins a aquell instant; no és el pic global de tota la campanya.

## Reproducció de l’auditoria i els gràfics

Des de l’arrel, amb les dependències de desenvolupament existents:

```powershell
python -X utf8 tools/audit_adaptive_dome_step7_13_v2.py
python -X utf8 tools/audit_regressions_step7_13_v2.py
python -X utf8 tools/plot_adaptive_dome_step7_13_v2.py
```

El primer CLI retorna zero només si passen els criteris complets, la independència, els pressupostos, la cua i la preservació. El segon només reconstrueix dades congelades: no executa transport addicional ni valida els píxels com a nous holdouts. El golden compartit es genera amb `tools/golden_adaptive_dome_step7_13_v2.py`, utilitzant SciPy com a oracle independent.

Per repetir les integrals, utilitza una còpia de treball aïllada i una carpeta d’evidències nova/versionada, amb preregistre i estimació abans de començar. Els CLI de mesura són `validate_adaptive_dome_step7_13_v2.py --part build|holdout|controls` i `validate_coesa_profile_step7_13_v2.py`; reprenen les files ja guardades i no sobreescriuen camps congelats. No esborres les mesures d’aquesta carpeta per forçar un recàlcul. La construcció i les fases científiques són seqüencials; no hi ha acceleració de fonts, vectorització addicional ni multicore.

El gate és una qualificació de les fixtures i els punts registrats. No és una garantia uniforme de qualsevol atmosfera, DEM, font extensa o ciutat Black Marble. Fora del domini acreditat, cal transport directe o resultat no disponible amb motiu explícit.

[Manifest de codi, documents i evidències](manifest-codi-evidencies-v2.json) · [Tancament i punt de represa](tancament-pas7.13-v2.json) · [Auditoria documental](auditoria-documental-resum.json).
