# Pas 12 — Cerca astronòmica, focus i seguiment

> Estat: **completat**  
> Classificat mitjançant implementació, proves i validacions del repositori.

## Resultat funcional palpable

L’usuari pot cercar estrelles, planetes, Sol, Lluna, NGC o coordenades i orientar-hi la càmera o el scope.

## Fonts TerraLab a consultar

- `TerraLab/astro/search_engine.py`
- `TerraLab/ui/widget_controls_builder.py` — `txt_search`
- `TerraLab/ui/astro_canvas.py`
- `TerraLab/widgets/telescope_scope_mode.py` — RA/Dec

## Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

## Tasques

- [ ] Construir un índex unificat de noms, àlies i identificadors.
- [ ] Definir una sintaxi explícita per a coordenades RA/Dec.
- [ ] Implementar normalització, ranking i límit de resultats.
- [ ] Retornar resultats tipats amb ID, tipus, nom i coordenada.
- [ ] Crear una UI de resultats navegable amb estat buit i errors.
- [ ] Separar completament `search` de `focus`.
- [ ] Implementar focus suau de càmera a una direcció o coordenada.
- [ ] Implementar seguiment d’un objecte mentre avança el temps.
- [ ] Permetre alliberar el seguiment amb una acció explícita.
- [ ] Fer que la cerca continuï disponible si una capa visual està oculta.
- [ ] Gestionar resultats de datasets no instal·lats amb explicació accionable.
- [ ] Comparar àlies, prioritats i casos de cerca de TerraLab.

## Criteri de sortida

La cerca retorna resultats reals i la càmera pot enfocar o seguir qualsevol objecte suportat sense alterar catàlegs o reconstruir l’escena.

## Evidència obligatòria

- [ ] Proves de noms, àlies, coordenades i consultes ambigües.
- [ ] Vídeo de cerca → focus → seguiment → alliberament.
- [ ] Prova de dataset absent.

## Fora d’abast del pas

El click directe, hover i inspecció es completen al pas següent.
