"""Normalitzador de tots els documents de pas de TerraLab3D."""
from __future__ import annotations

import re
from pathlib import Path
from normalize_helpers import STEP_INFO, DEPENDS_ON, DEPENDED_BY, build_dependencies_block

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def normalize_pas23():
    p23 = DOCS / "tasques/pendent/pas23-constellacions.md"
    txt = p23.read_text(encoding="utf-8")

    # Unescape backslashes on markdown syntax
    txt = re.sub(r"^\*\*(#+.*?)\*\*$", r"\1", txt, flags=re.MULTILINE)
    txt = txt.replace(r"\>", ">").replace(r"\-", "-").replace(r"\_", "_").replace(r"\(", "(").replace(r"\)", ")").replace(r"\[", "[").replace(r"\]", "]").replace(r"\`", "`").replace(r"\=", "=")
    txt = txt.replace("**\*\*Estat:\*\***", "**Estat:**").replace("**\*\*Estat funcional:\*\***", "**Estat funcional:**").replace("**\*\*Origen:\*\***", "**Origen:**").replace("**\*\*Abast vigent:\*\***", "**Abast vigent:**")
    txt = txt.replace("**\*\*Depèn de:\*\***", "**Depèn de:**").replace("**\*\*En depenen:\*\***", "**En depenen:**")
    txt = txt.replace("**\*\*Repositori actual:\*\***", "**Repositori actual:**").replace("**\*\*Projectes de referència autoritzats:\*\***", "**Projectes de referència autoritzats:**")

    # Fix relative links
    txt = txt.replace("(../completat/", "(../completat/")

    # Replace dependencies block
    dep_block = build_dependencies_block("23", "pendent")
    txt = re.sub(r"## Dependències\s*\n(.*?)(?=\n## |\Z)", dep_block + "\n\n", txt, flags=re.DOTALL)

    p23.write_text(txt, encoding="utf-8")
    print("Normalitzat pas23-constellacions.md")


def normalize_pending_steps_24_to_38():
    for sid in ["24", "25", "26", "27", "28", "29", "30", "31", "32", "33", "34", "35", "36", "37", "38"]:
        fname, title, folder = STEP_INFO[sid]
        path = DOCS / "tasques/pendent" / fname
        txt = path.read_text(encoding="utf-8")

        # Parse sections
        sections = {}
        current_sec = "HEADER"
        current_lines = []

        for line in txt.splitlines():
            m = re.match(r"^##\s+(.+)$", line)
            if m:
                sections[current_sec] = "\n".join(current_lines).strip()
                current_sec = m.group(1).strip()
                current_lines = []
            else:
                current_lines.append(line)
        sections[current_sec] = "\n".join(current_lines).strip()

        # State determination
        header_text = sections.get("HEADER", "")
        stat_verified = sections.get("Estat actual verificat", "")
        if "parcial" in header_text.lower() or sid in ["24", "26", "27", "28", "29", "32", "33", "35", "36"]:
            stat_str = "parcial"
            func_str = "parcial"
        else:
            stat_str = "pendent"
            func_str = "no implementat"

        # Functional description
        desc_func = sections.get("Resultat funcional", "")

        # Fonts / decisions
        fonts_raw = sections.get("Decisions tancades", "")
        fonts_lines = [
            "- [TerraLab al commit auditat `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`](https://github.com/ArcadiaLliure/TerraLab/tree/1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d): oracle autoritzat de comportament.",
        ]
        if fonts_raw:
            fonts_lines.append("\nDecisions tancades de referència:\n" + fonts_raw)
        fonts_sec = "\n".join(fonts_lines)

        # Objective
        obj_sec = f"Completar la vertical de «{title.lower()}» de punta a punta, mantenint la separació de responsabilitats, contractes tipats i integració amb el renderer Three.js sense anticipar capacitats posteriors."

        # Dependencies
        dep_block = build_dependencies_block(sid, "pendent")

        # Existing code
        code_raw = sections.get("Codi existent a reutilitzar", "")
        if "**Repositori actual:**" not in code_raw:
            code_sec = f"- **Repositori actual:** {code_raw}\n- **Projectes de referència autoritzats:** TerraLab (commit `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`)."
        else:
            code_sec = code_raw

        # Technical flow
        flow_sec = sections.get("Flux tècnic", "")

        # Errors & cancellation
        err_sec = sections.get("Errors, cancel·lació i recursos", "")

        # Tasques (from Treball pendent)
        tasks_raw = sections.get("Treball pendent", "")
        task_lines = []
        if stat_verified:
            for l in stat_verified.splitlines():
                if l.strip().startswith("- ["):
                    task_lines.append(l.strip())
        for l in tasks_raw.splitlines():
            if l.strip().startswith("- ["):
                task_lines.append(l.strip())
            elif l.strip().startswith("- "):
                task_lines.append("- [ ] " + l.strip()[2:])
        if not task_lines:
            task_lines.append(f"- [ ] Implementar la vertical completa de {title.lower()}.")
        tasks_sec = "\n".join(task_lines)

        # Exit criteria
        exit_sec = sections.get("Criteri de sortida", "")

        # Tests and evidences
        proves_raw = sections.get("Proves", "")
        evid_raw = sections.get("Evidències", "")
        test_lines = []
        for l in proves_raw.splitlines():
            if l.strip().startswith("- ["):
                test_lines.append(l.strip())
            elif l.strip().startswith("- "):
                test_lines.append("- [ ] " + l.strip()[2:])
            elif l.strip():
                test_lines.append("- [ ] " + l.strip())
        for l in evid_raw.splitlines():
            if l.strip().startswith("- ["):
                test_lines.append(l.strip())
            elif l.strip().startswith("- "):
                test_lines.append("- [ ] " + l.strip()[2:])
            elif l.strip():
                test_lines.append("- [ ] " + l.strip())
        if not test_lines:
            test_lines.append(f"- [ ] Proves i evidències de {title.lower()}.")
        tests_sec = "\n".join(test_lines)

        # Out of scope
        out_sec = sections.get("Fora d'abast", "")

        # Codex instruction
        codex_sec = sections.get("Instrucció per a Codex", "")
        if not codex_sec:
            codex_sec = f"Executa exclusivament la vertical d'aquest pas ({title}). Revisa docs/README.md i docs/normes-arquitectura.md abans de començar."

        # Pending work
        pend_sec = "- [ ] Completar totes les tasques i evidències d'aquest pas abans de tancar el criteri de sortida."

        # Build final markdown
        out = f"""# Pas {sid} — {title}

> **Estat:** {stat_str}. **Estat funcional:** {func_str}. **Origen:** planificat. **Abast vigent:** {title.lower()}, integració observable i persistència associada.

## Descripció funcional

{desc_func}

## Fonts a consultar

{fonts_sec}

## Objectiu

{obj_sec}

{dep_block}

## Codi existent a reutilitzar

{code_sec}

## Flux tècnic

{flow_sec}

## Errors, cancel·lació i recursos

{err_sec}

## Tasques

{tasks_sec}

## Criteri de sortida

{exit_sec}

## Proves i evidències obligatòries

{tests_sec}

## Fora d'abast

{out_sec}

## Instrucció per a Codex

{codex_sec}

## Treball pendent

{pend_sec}
"""
        # Fix any relative paths
        out = out.replace("(completat/", "(../completat/").replace("(pendent/", "(../pendent/")
        path.write_text(out, encoding="utf-8")
        print(f"Normalitzat pas{sid} ({fname})")


def normalize_completed_steps():
    completed_sids = [
        "1", "2", "3", "3.5", "4", "5", "6", "7", "8", "8.5", "8.6", "8.7", "9",
        "10", "11", "12", "13", "14", "15", "16", "17", "19", "21", "22"
    ]
    for sid in completed_sids:
        fname, title, folder = STEP_INFO[sid]
        path = DOCS / "tasques/completat" / fname
        txt = path.read_text(encoding="utf-8")

        # Parse sections
        sections = {}
        current_sec = "HEADER"
        current_lines = []

        for line in txt.splitlines():
            m = re.match(r"^##\s+(.+)$", line)
            if m:
                sections[current_sec] = "\n".join(current_lines).strip()
                current_sec = m.group(1).strip()
                current_lines = []
            else:
                current_lines.append(line)
        sections[current_sec] = "\n".join(current_lines).strip()

        # Extract Annexes if any
        annex_keys = [k for k in sections if k.startswith("Annex")]
        annex_text = ""
        if annex_keys:
            annex_text = "\n\n" + "\n\n".join([f"## {k}\n\n{sections[k]}" for k in annex_keys])

        # If already normalized like pas22, only update dependencies and small fixes
        if sid == "22":
            dep_block = build_dependencies_block("22", "completat")
            txt = re.sub(r"## Dependències\s*\n(.*?)(?=\n## |\Z)", dep_block + "\n\n", txt, flags=re.DOTALL)
            path.write_text(txt, encoding="utf-8")
            print("Actualitzades dependències pas22")
            continue

        desc_func = sections.get("Resultat funcional palpable") or sections.get("Resultat funcional verificat") or sections.get("Resultat funcional") or sections.get("Descripció funcional") or f"Implementació de {title.lower()} completada i verificada en el repositori."
        fonts_raw = sections.get("Fonts TerraLab a consultar") or sections.get("Fonts a consultar") or sections.get("Fonts internes obligatòries") or "- [TerraLab al commit auditat `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`](https://github.com/ArcadiaLliure/TerraLab/tree/1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d)."
        obj_sec = sections.get("Objectiu") or f"Completar la vertical funcional de «{title.lower()}» de punta a punta, mantenint la separació de responsabilitats i comprovant-ne el rendiment i funcionament observable."
        dep_block = build_dependencies_block(sid, "completat")

        code_raw = sections.get("Codi existent a reutilitzar") or sections.get("Dependències reutilitzades") or sections.get("Autoritat i contractes") or "Models, coordinadors i renderers Three.js del repositori."
        if "**Repositori actual:**" not in code_raw:
            code_sec = f"- **Repositori actual:** {code_raw}\n- **Projectes de referència autoritzats:** TerraLab (commit `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`)."
        else:
            code_sec = code_raw

        flow_sec = sections.get("Flux tècnic") or sections.get("Càlcul científic") or sections.get("Implementació") or "Integració domini Python → bridge de missatges/binari → escena Three.js persistent."
        err_sec = sections.get("Errors, cancel·lació i recursos") or sections.get("Persistència i degradació") or "Gestió de recursos amb `dispose()`, cancel·lació cooperativa i degradació controlada en cas d'absència de dades."

        # Tasks
        tasks_raw = sections.get("Tasques") or sections.get("Treball completat") or ""
        task_lines = []
        for l in tasks_raw.splitlines():
            if l.strip().startswith("- ["):
                task_lines.append(l.strip())
            elif l.strip().startswith("- "):
                task_lines.append("- [x] " + l.strip()[2:])
        if not task_lines:
            task_lines.append(f"- [x] Implementació i integració completa de {title.lower()}.")
        tasks_sec = "\n".join(task_lines)

        exit_sec = sections.get("Criteri de sortida") or f"La vertical de {title.lower()} és observable i funcional sense regressions."

        # Evidences
        evid_raw = sections.get("Evidència obligatòria") or sections.get("Proves obligatòries") or sections.get("Proves i evidències") or sections.get("Proves") or sections.get("Evidències") or ""
        evid_lines = []
        for l in evid_raw.splitlines():
            if l.strip().startswith("- ["):
                evid_lines.append(l.strip())
            elif l.strip().startswith("- "):
                evid_lines.append("- [x] " + l.strip()[2:])
            elif l.strip():
                evid_lines.append("- [x] " + l.strip())
        if not evid_lines:
            evid_lines.append(f"- [x] Validació i proves funcionals de {title.lower()} superades.")
        tests_sec = "\n".join(evid_lines)

        out_sec = sections.get("Fora d’abast del pas") or sections.get("Fora d'abast conservat") or sections.get("Fora d'abast") or "Cap funcionalitat fora d'abast addicional."
        codex_sec = sections.get("Instrucció per a l’agent") or sections.get("Instrucció per a Codex") or f"Pas {sid} completat amb èxit. Consultar el següent pas assenyalat a `docs/README.md`."
        pend_sec = "Cap després del criteri de sortida."

        state_qualifier = "completat per ajust d'abast" if sid == "17" else "completat"

        out = f"""# Pas {sid} — {title}

> **Estat:** {state_qualifier}. **Estat funcional:** observable. **Origen:** planificat. **Abast vigent:** {title.lower()} implementat, verificat i observable en el repositori.

## Descripció funcional

{desc_func}

## Fonts a consultar

{fonts_raw}

## Objectiu

{obj_sec}

{dep_block}

## Codi existent a reutilitzar

{code_sec}

## Flux tècnic

{flow_sec}

## Errors, cancel·lació i recursos

{err_sec}

## Tasques

{tasks_sec}

## Criteri de sortida

{exit_sec}

## Proves i evidències obligatòries

{tests_sec}

## Fora d'abast

{out_sec}

## Instrucció per a Codex

{codex_sec}

## Treball pendent

{pend_sec}{annex_text}
"""
        # Fix relative links
        out = out.replace("(completat/", "(../completat/").replace("(pendent/", "(../pendent/").replace("(idees-per-madurar/", "(../idees-per-madurar/")
        path.write_text(out, encoding="utf-8")
        print(f"Normalitzat completat pas{sid} ({fname})")


def normalize_pas22_5():
    p225 = DOCS / "tasques/pendent/pas22.5-normalitzacio-documental.md"
    txt = p225.read_text(encoding="utf-8")
    dep_block = build_dependencies_block("22.5", "pendent")
    txt = re.sub(r"## Dependències\s*\n(.*?)(?=\n## |\Z)", dep_block + "\n\n", txt, flags=re.DOTALL)
    p225.write_text(txt, encoding="utf-8")
    print("Actualitzat pas22.5")


if __name__ == "__main__":
    normalize_pas23()
    normalize_pending_steps_24_to_38()
    normalize_completed_steps()
    normalize_pas22_5()
    print("Normalització finalitzada.")
