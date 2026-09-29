#!/usr/bin/env python3
"""Descarga desde OpenAlex las publicaciones de los investigadores principales
del GoSA (Santiago Vargas Domínguez y Benjamín Calvo Mozo), de los colaboradores
externos y de los estudiantes de posgrado con perfil identificado, marca qué
miembros
del grupo aparecen como coautores y señala cuáles aún no están en
produccion.html.

Uso:
    python3 scripts/scrape_publicaciones.py
    python3 scripts/scrape_publicaciones.py --reusar-csv   # no consulta OpenAlex:
        # parte del CSV existente y solo actualiza los colaboradores (útil
        # cuando se agota la cuota diaria gratuita de OpenAlex)

Salida:
    data/publicaciones_openalex.csv
"""

import csv
import sys
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

# Colaboradores externos que figuran como miembros activos en index.html. Se
# consultan por ORCID (+ Crossref para los autores) porque en OpenAlex sus
# perfiles están partidos y mezclados con homónimos.
COLLABORATORS = {
    "Juan Carlos Martínez Oliveros": "0000-0002-2587-1342",
    "Juan Camilo Buitrago": "0000-0002-8203-4794",
    "Jose Ivan Campos Rozo": "0000-0001-8883-6790",
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


def get_json(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.load(r)
        except Exception:
            time.sleep(2 * (attempt + 1))
    return None


ORCID_TYPES = {"journal-article": "article", "conference-abstract": "conference-abstract",
               "conference-paper": "conference-paper", "preprint": "preprint",
               "book": "book", "book-chapter": "book-chapter", "dissertation-thesis": "dissertation"}


CROSSREF_TYPES = {"journal-article": "article", "proceedings-article": "conference-paper",
                  "posted-content": "preprint", "book-chapter": "book-chapter", "book": "book"}


def crossref_by_title(title):
    """Busca en Crossref una obra con exactamente el mismo título."""
    query = urllib.parse.urlencode({"query.bibliographic": title, "rows": 3})
    items = ((get_json(f"https://api.crossref.org/works?{query}") or {})
             .get("message", {}).get("items", []))
    for item in items:
        if norm(" ".join(item.get("title") or [""])) == norm(title):
            return item
    return None


def orcid_records(orcid):
    """Obras de un perfil ORCID, completando los autores con Crossref."""
    data = get_json(f"https://pub.orcid.org/v3.0/{orcid}/works") or {}
    records = []
    for group in data.get("group", []):
        w = group["work-summary"][0]
        ids = (w.get("external-ids") or {}).get("external-id", [])
        ids += [e for g in group["work-summary"][1:]
                for e in (g.get("external-ids") or {}).get("external-id", [])]
        doi = next((e["external-id-value"] for e in ids if e["external-id-type"] == "doi"), "")
        doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi.strip()).lower()
        year = ((w.get("publication-date") or {}).get("year") or {}).get("value")
        rec = {
            "year": int(year) if year else None,
            "title": " ".join(w["title"]["title"]["value"].split()),
            "venue": ((w.get("journal-title") or {}).get("value") or ""),
            "type": ORCID_TYPES.get(w.get("type"), w.get("type") or ""),
            "authors": [],
            "doi": doi,
            "link": (w.get("url") or {}).get("value", "") if w.get("url") else "",
        }
        bibcode = next((e["external-id-value"] for e in ids if e["external-id-type"] == "bibcode"), "")
        if not rec["link"] and bibcode:
            rec["link"] = f"https://ui.adsabs.harvard.edu/abs/{bibcode}"
        if doi:
            msg = (get_json(f"https://api.crossref.org/works/{urllib.parse.quote(doi)}") or {}).get("message")
        else:
            msg = crossref_by_title(rec["title"])
            if msg:
                rec["doi"] = msg["DOI"].lower()
        if msg:
            rec["authors"] = [f"{a.get('given', '')} {a.get('family', '')}".strip()
                              for a in msg.get("author", [])]
            rec["venue"] = rec["venue"] or (msg.get("container-title") or [""])[0]
            rec["type"] = CROSSREF_TYPES.get(msg.get("type"), rec["type"])
        time.sleep(0.1)
        records.append(rec)
    return records


def openalex_record(w):
    return {
        "year": w.get("publication_year"),
        "title": (w.get("title") or "").strip(),
        "venue": ((w.get("primary_location") or {}).get("source") or {}).get("display_name") or "",
        "type": w.get("type"),
        "authors": [a["author"]["display_name"] for a in w.get("authorships", [])],
        "doi": (w.get("doi") or "").replace("https://doi.org/", "").lower(),
        "link": w.get("id") or "",
    }


def csv_record(r):
    return {"year": int(r["Año"]) if r["Año"] else None, "title": r["Título"],
            "venue": r["Revista/Fuente"], "type": r["Tipo"],
            "authors": [a.strip() for a in r["Autores"].split(",") if a.strip()],
            "doi": r["DOI"].lower(), "link": r["Enlace"]}


def existing_dois():
    html = (ROOT / "produccion.html").read_text(encoding="utf-8")
    # DOI en cualquier enlace (doi.org o la página de la editorial).
    hrefs = re.findall(r'href="([^"]+)"', html)
    return {m.group(1).lower().rstrip(".") for h in hrefs
            for m in [re.search(r"(10\.\d{4,9}/[^\s?#]+)", urllib.parse.unquote(h))] if m}


def existing_titles():
    html = (ROOT / "produccion.html").read_text(encoding="utf-8")
    titles = re.findall(r'<h4 class="pub-title">(.*?)</h4>', html, re.S)
    return {" ".join(norm(t))[:60] for t in titles}


def main():
    members = load_members()
    known_dois, known_titles = existing_dois(), existing_titles()

    if "--reusar-csv" in sys.argv:
        with OUT.open(encoding="utf-8") as f:
            records = [csv_record(r) for r in csv.DictReader(f)]
    else:
        works = {}
        for ids in [*PIS.values(), *STUDENTS.values()]:
            works.update(works_for(ids))
        records = [openalex_record(w) for w in works.values()]
    for orcid in COLLABORATORS.values():
        records += orcid_records(orcid)

    rows, seen = [], set()
    for rec in records:
        title = rec["title"]
        tkey = " ".join(norm(title))[:60]
        key = rec["doi"] or tkey
        if not title or key in seen:
            continue
        seen.add(key)
        doi = rec["doi"]
        in_group = group_members(rec["authors"], members)
        on_site = (doi and doi in known_dois) or tkey in known_titles
        rows.append({
            "Año": rec["year"],
            "Título": title,
            "Revista/Fuente": rec["venue"],
            "Tipo": rec["type"],
            "Autores": ", ".join(rec["authors"]),
            "Miembros GoSA": "; ".join(m["name"] for m in in_group),
            "Estudiantes activos": "; ".join(m["name"] for m in in_group
                                              if m["class"] in STUDENT_CLASSES),
            "DOI": doi,
            "Enlace": f"https://doi.org/{doi}" if doi else rec["link"],
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
