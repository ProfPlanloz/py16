#!/usr/bin/env python3
"""Buendelt das modulare Paket src/appstore/ zu EINER Datei: dist/appstore.py.

Warum: py16os laedt genau eine flache .py-Datei pro Plugin (der Installer
flacht apps/<id>/<id>.py zu apps/<id>.py ab). Ein echtes Paket mit
Untermodulen wuerde der Host nicht aufloesen. Dieser Bundler fuegt die
Module in Abhaengigkeitsreihenfolge zusammen und entfernt die
paket-internen Importe - heraus kommt ein einziger Namensraum, in dem alle
Funktionen und das State-Objekt S weiter zusammenarbeiten.

Aufruf:  python3 build.py
Ausgabe: dist/appstore.py
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, "appstore")
OUT_DIR = os.path.join(HERE, "dist")
OUT = os.path.join(OUT_DIR, "appstore.py")

# Reihenfolge = Abhaengigkeitsreihenfolge (config zuerst, controller zuletzt).
MODULES = ["config", "state", "helpers", "tasks", "views", "controller"]



def _read(mod):
    with open(os.path.join(PKG, mod + ".py"), "r", encoding="utf-8") as f:
        return f.read()


def _classify_imports(src):
    """Quelltext in (externe_top_level_imports, rest_zeilen) zerlegen.

    Erkennt auch mehrzeilige Importe mit Klammern. Relative Importe
    (from .x import ...) fallen komplett weg; eingerueckte (lazy) Importe
    bleiben im Rest erhalten; externe Top-Level-Importe werden gesammelt.
    """
    lines = src.split("\n")
    ext = []
    rest = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.lstrip()
        indented = (line[:1] == " " or line[:1] == "\t")
        is_import = stripped.startswith("import ") or stripped.startswith("from ")
        if is_import:
            # vollstaendiges Statement einsammeln (ueber Klammern / Backslash)
            stmt_lines = [line]
            depth = line.count("(") - line.count(")")
            cont = line.rstrip().endswith("\\")
            while (depth > 0 or cont) and i + 1 < n:
                i += 1
                stmt_lines.append(lines[i])
                depth += lines[i].count("(") - lines[i].count(")")
                cont = lines[i].rstrip().endswith("\\")
            joined = "\n".join(stmt_lines)
            is_relative = stripped.startswith("from .")
            if is_relative:
                pass  # komplett verwerfen
            elif indented:
                rest.extend(stmt_lines)  # lazy import: an Ort belassen
            else:
                ext.append(" ".join(s.strip() for s in stmt_lines))
            i += 1
            continue
        rest.append(line)
        i += 1
    return ext, rest


def build():
    ext_imports = []
    bodies = []

    for mod in MODULES:
        src = _read(mod)
        ext, rest = _classify_imports(src)
        ext_imports.extend(ext)
        body = "\n".join(rest).strip("\n")
        bodies.append("# ===== " + mod + ".py " + "=" * (54 - len(mod)) + "\n" + body)

    # Externe Importe deduplizieren, Reihenfolge stabil halten.
    seen = set()
    uniq = []
    for imp in ext_imports:
        if imp not in seen:
            seen.add(imp)
            uniq.append(imp)

    header = (
        "# AUTO-GENERATED von build.py - NICHT direkt editieren.\n"
        "# Quelle: src/appstore/*.py  |  Neu erzeugen: python3 build.py\n"
        "#\n"
        "# py16os App-Store (gebuendelte Einzeldatei).\n"
    )
    parts = [header, "\n".join(uniq), ""]
    parts.extend(bodies)
    # Plugin-Interface explizit am Ende verfuegbar machen (init/update/draw/APP
    # stehen bereits als Top-Level-Namen im zusammengefuehrten Modul).
    text = "\n\n".join(parts).rstrip() + "\n"

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text)
    return OUT


if __name__ == "__main__":
    path = build()
    print("wrote", path)
