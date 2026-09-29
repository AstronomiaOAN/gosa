#!/usr/bin/env python3
"""Descarga desde OpenAlex las publicaciones de los investigadores principales
del GoSA (Santiago Vargas Domínguez y Benjamín Calvo Mozo) y de los estudiantes
de posgrado con perfil identificado, marca qué miembros
del grupo aparecen como coautores y señala cuáles aún no están en
produccion.html.

Uso:
    python3 scripts/scrape_publicaciones.py

Salida:
    data/publicaciones_openalex.csv
"""

import csv
import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "publicaciones_openalex.csv"

# Perfiles de OpenAlex de cada investigador principal (OpenAlex a veces parte
# un mismo autor en varios perfiles; se incluyen todos los identificados).
PIS = {
    "Santiago Vargas Domínguez": ["A5067032230", "A5123796859", "A5127492052", "A5103860334"],
    "Benjamín Calvo Mozo": ["A5071278092", "A5082411304"],
}

# Perfiles de OpenAlex de estudiantes de posgrado, para incluir trabajos en los
# que no participa ninguno de los investigadores principales.
STUDENTS = {
    "Daniel Alberto Rodríguez Torres": ["A5138226627", "A5151405479"],
    "Oscar Andres Calvo Rebellon": ["A5151352197"],
    "Juan Esteban Agudelo Ortiz": ["A5012202768"],
    "Andrés Felipe Guerrero Guio": ["A5093788776"],
    "Claudia Alejandra Cuellar Nieto": ["A5139952000"],
    "Paula Jessica González Prieto": ["A5078023816", "A5126508288"],
}

# Categorías de la sección de integrantes de index.html que corresponden a
# estudiantes activos.
STUDENT_CLASSES = {"maestria", "pregrado", "otras"}


def norm(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z ]", " ", text.lower()).split()


def load_members():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    pattern = (r'<div class="team-member-card glassmorphism ([^"]*)">.*?<h4>(.*?)</h4>\s*'
               r'<p class="role"><span class="es">(.*?)</span>')
    return [{"name": n, "class": c, "role": r} for c, n, r in re.findall(pattern, html, re.S)]


def score(member_name, author_name):
    """Puntaje de coincidencia entre un miembro y un autor de OpenAlex.

    Exige un apellido y el primer nombre (completo o inicial) y suma un punto
    por cada palabra que coincida.
    """
    m, a = norm(member_name), norm(author_name)
    if len(m) < 2 or not a:
        return 0
    surnames = m[-2:] if len(m) >= 3 else m[1:]
    given = [w for w in m if w not in surnames]
    if not any(s in a for s in surnames):
        return 0
    if not any(w == given[0] or (len(w) == 1 and w == given[0][0]) for w in a):
        return 0
    unknown = [i for i, w in enumerate(a) if len(w) > 1 and w not in m]
    # Una palabra que el miembro no tiene indica otra persona (p. ej. "Martínez
    # Oliveros" frente a "Martínez Sibaja"), salvo un segundo apellido final
    # cuando el miembro figura en el sitio con un solo apellido.
    if unknown and not (len(m) <= 3 and unknown == [len(a) - 1]):
        return 0
    return sum(1 for w in a if w in m or (len(w) == 1 and any(g[0] == w for g in given)))


def group_members(authors, members):
    """Asigna cada autor al miembro con mejor puntaje (si lo hay)."""
    found = []
    for author in authors:
        best = max(members, key=lambda mem: score(mem["name"], author))
        if score(best["name"], author) and best not in found:
            found.append(best)
    return found


def get(url):
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.load(r)
        except Exception:
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(url)


def works_for(author_ids):
    works, cursor = {}, "*"
    flt = "author.id:" + "|".join(author_ids)
    while cursor:
        url = ("https://api.openalex.org/works?" + urllib.parse.urlencode(
            {"filter": flt, "per-page": 200, "cursor": cursor}))
        data = get(url)
        for w in data["results"]:
            works[w["id"]] = w
        cursor = data["meta"].get("next_cursor")
        if not data["results"]:
            break
    return works


def existing_dois():
    html = (ROOT / "produccion.html").read_text(encoding="utf-8")
    return {d.lower().rstrip(".") for d in re.findall(r'doi\.org/([^"\s<]+)', html)}


def existing_titles():
    html = (ROOT / "produccion.html").read_text(encoding="utf-8")
    titles = re.findall(r'<h4 class="pub-title">(.*?)</h4>', html, re.S)
    return {" ".join(norm(t))[:60] for t in titles}


def main():
    members = load_members()
    known_dois, known_titles = existing_dois(), existing_titles()

    all_works = {}
    for ids in [*PIS.values(), *STUDENTS.values()]:
        for wid, w in works_for(ids).items():
            all_works.setdefault(wid, w)

    rows = []
    for w in all_works.values():
        authors = [a["author"]["display_name"] for a in w.get("authorships", [])]
        in_group = group_members(authors, members)
        doi = (w.get("doi") or "").replace("https://doi.org/", "")
        title = (w.get("title") or "").strip()
        tkey = " ".join(norm(title))[:60]
        on_site = (doi and doi.lower() in known_dois) or tkey in known_titles
        venue = ((w.get("primary_location") or {}).get("source") or {}).get("display_name") or ""
        rows.append({
            "Año": w.get("publication_year"),
            "Título": title,
            "Revista/Fuente": venue,
            "Tipo": w.get("type"),
            "Autores": ", ".join(authors),
            "Miembros GoSA": "; ".join(m["name"] for m in in_group),
            "Estudiantes activos": "; ".join(m["name"] for m in in_group
                                              if m["class"] in STUDENT_CLASSES),
            "DOI": doi,
            "Enlace": f"https://doi.org/{doi}" if doi else (w.get("id") or ""),
            "Ya en produccion.html": "sí" if on_site else "no",
        })

    rows.sort(key=lambda r: (-(r["Año"] or 0), r["Título"]))
    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    new = [r for r in rows if r["Ya en produccion.html"] == "no"]
    with_students = [r for r in rows if r["Estudiantes activos"]]
    print(f"{len(rows)} obras en total, {len(new)} no están en produccion.html, "
          f"{len(with_students)} con estudiantes activos → {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
