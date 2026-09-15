"""Comprueba que los enlaces Markdown locales de ``docs`` resuelven.

El chequeo es deliberadamente estructural: valida el destino de archivo o
directorio y deja la semántica de los anchors al renderer Markdown.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit


LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")


def local_target(raw: str) -> str | None:
    value = raw.strip()
    if value.startswith("<") and ">" in value:
        value = value[1:value.index(">")]
    else:
        value = value.split(maxsplit=1)[0]
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None
    return unquote(parsed.path)


def broken_links(docs_root: Path) -> list[str]:
    failures: list[str] = []
    for document in sorted(docs_root.rglob("*.md")):
        text = document.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            for match in LINK.finditer(line):
                target = local_target(match.group(1))
                if target is None:
                    continue
                resolved = (document.parent / target).resolve()
                if not resolved.exists():
                    failures.append(f"{document}:{line_number}: {target}")
    return failures


def main() -> int:
    repository = Path(__file__).resolve().parents[1]
    failures = broken_links(repository / "docs")
    if failures:
        print("Enlaces documentales rotos:")
        print("\n".join(failures))
        return 1
    print("Documentación: enlaces locales válidos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
