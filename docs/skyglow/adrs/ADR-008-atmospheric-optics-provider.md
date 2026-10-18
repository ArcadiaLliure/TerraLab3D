# ADR-008 — AtmosphericOpticsProvider

- **Estat:** Acceptada — camp estàndard implementat; composició/transport futurs pendents
- **Data:** 2026-09-28
- **Àmbit:** skyglow físic

## Context

El kernel no ha de dependre de ERA5/CAMS/API concreta.

## Decisió

Un provider materialitza un `OpticalField` immutable a partir d’origen, temps, tiles i resolució vertical; el camp resol `OpticalState` per posició i conserva procedència per magnitud. A 7.8 només es materialitza l’atmosfera estàndard seca; la composició amb dades reals correspon a 7.15.

## Conseqüències

Permet jerarquia observació→forecast→reanàlisi→climatologia→standard.

## Alternatives

Es mantenen documentades al TDD i a l'especificació d'algorismes; qualsevol alternativa futura que canviï aquesta decisió requereix un ADR que la substitueixi.

## Validació

Contract tests del port, determinisme, P/T analítics, idealitat, cobertura i procedència. Fallbacks per camp amb dades reals pendents de 7.15.

## Estat d'implementació

[7.8](../../tasques/completat/pas7.8-optical-field-standard.md) implementa el camp estàndard sec P/T/n, port/provider, interpolació i dependències per capes. [Fixtures 1/2/8 tiles, regressió B0 i oracle de columnes](../../evidencies/pas7.8/validacio-optical-field.md). Encara no hi ha composició ERA5/CAMS, β espectrals, transport radiomètric ni cache.