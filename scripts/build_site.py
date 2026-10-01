#!/usr/bin/env python3
"""Genera el sitio publicado en _site/ a partir de los HTML bilingües.

Los fuentes (index.html, escuela.html, ...) llevan los dos idiomas marcados con
las clases `es` y `en`. Para que los buscadores indexen cada idioma por
separado, este script produce:

    _site/<pagina>.html      solo español
    _site/en/<pagina>.html   solo inglés

con `lang`, canonical, hreflang y sitemap.xml coherentes. El título y la
descripción en inglés se toman de `data-en` (en <title>) y `data-en-content`
(en <meta name="description">).

Uso:
    python3 scripts/build_site.py
    python3 -m http.server 8123 -d _site     # vista previa local
"""

import re
import shutil
import subprocess
import sys
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

try:
    from .content import render_page
    from .site_assets import collect_assets
except ImportError:
    from content import render_page
    from site_assets import collect_assets

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "_site"
BASE_URL = "https://astronomiaoan.co/gosa/"

RESEARCH_PAGES = ["optica-alta-resolucion.html", "radio-rayos-x.html", "clima-espacial.html",
                  "simulaciones-machine-learning.html"]
PAGES = ["index.html", "escuela.html", "produccion.html", "dynasun.html"] + RESEARCH_PAGES
PRIORITY = {"index.html": "1.0", "escuela.html": "0.8", "produccion.html": "0.8", "dynasun.html": "0.7",
            **{page: "0.8" for page in RESEARCH_PAGES}}
# Archivos y carpetas que se publican tal cual (el resto del repo no se sube).
ASSET_GLOBS = ["google*.html"]

LANGS = ("es", "en")
OG_LOCALE = {"es": "es_CO", "en": "en_US"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class LangFilter(HTMLParser):
    """Reemite el HTML original omitiendo los elementos del otro idioma."""

    def __init__(self, drop):
        super().__init__(convert_charrefs=False)
        self.drop = drop
        self.out = []
        self.skip_tag = None  # etiqueta del elemento que se está omitiendo
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if self.skip_tag:
            if tag == self.skip_tag:
                self.skip_depth += 1
            return
        classes = (dict(attrs).get("class") or "").split()
        if self.drop in classes:
            if tag not in VOID:  # los elementos vacíos (img, br...) no tienen cierre
                self.skip_tag, self.skip_depth = tag, 1
            return
        self.out.append(self.get_starttag_text())

    def handle_startendtag(self, tag, attrs):
        if not self.skip_tag and self.drop not in (dict(attrs).get("class") or "").split():
            self.out.append(self.get_starttag_text())

    def handle_endtag(self, tag):
        if self.skip_tag:
            if tag == self.skip_tag:
                self.skip_depth -= 1
                if self.skip_depth == 0:
                    self.skip_tag = None
            return
        self.out.append(f"</{tag}>")

    def _emit(self, text):
        if not self.skip_tag:
            self.out.append(text)

    def handle_data(self, data):
        self._emit(data)

    def handle_entityref(self, name):
        self._emit(f"&{name};")

    def handle_charref(self, name):
        self._emit(f"&#{name};")

    def handle_comment(self, data):
        self._emit(f"<!--{data}-->")

    def handle_decl(self, decl):
        self._emit(f"<!{decl}>")


def page_url(page, lang):
    path = "" if page == "index.html" else page
    return BASE_URL + ("en/" if lang == "en" else "") + path


def is_asset_path(value):
    """Ruta relativa a un recurso (no a otra página ni a un ancla o URL externa)."""
    if not value or value.startswith(("#", "/", "data:", "mailto:", "tel:")) or re.match(r"[a-z][a-z0-9+.-]*:", value, re.I):
        return False
    return not re.search(r"\.html($|[#?])", value)


def prefix_assets(html):
    """Las páginas de en/ están un nivel más abajo: los recursos pasan a ../"""
    def attr(m):
        return f'{m.group(1)}="../{m.group(2)}"' if is_asset_path(m.group(2)) else m.group(0)

    def css_url(m):
        return f"url({m.group(1)}../{m.group(2)}{m.group(1)})" if is_asset_path(m.group(2)) else m.group(0)

    def tag(m):
        text = re.sub(r'\b(src|href|poster)="([^"]*)"', attr, m.group(0))
        return re.sub(r"url\((['\"]?)([^)'\"]+)\1\)", css_url, text)

    return re.sub(r"<[a-zA-Z][^>]*>", tag, html)


def set_meta(html, selector, value):
    pattern = rf'(<meta\s+{selector}\s+content=")[^"]*"'
    html, n = re.subn(pattern, lambda m: m.group(1) + value + '"', html, count=1)
    if n != 1:
        sys.exit(f"build_site: no se encontró <meta {selector}>")
    return html


def build_page(page, lang):
    source = render_page(page)

    parser = LangFilter(drop="en" if lang == "es" else "es")
    parser.feed(source)
    parser.close()
    if parser.skip_tag:
        sys.exit(f"build_site: {page}: elemento <{parser.skip_tag} class=\"{parser.drop}\"> sin cerrar")
    html = "".join(parser.out)

    # Título y descripción en inglés (declarados junto a los de español)
    title_en = re.search(r'<title data-en="([^"]*)">', html)
    desc_en = re.search(r'\s+data-en-content="([^"]*)"', html)
    if not title_en or not desc_en:
        sys.exit(f"build_site: {page}: falta data-en en <title> o data-en-content en la descripción")
    html = html.replace(desc_en.group(0), "", 1)
    if lang == "en":
        html = re.sub(r"<title data-en=\"[^\"]*\">.*?</title>", f"<title>{title_en.group(1)}</title>", html, count=1, flags=re.S)
        for selector in ('property="og:title"', 'name="twitter:title"'):
            html = set_meta(html, selector, title_en.group(1))
        for selector in ('name="description"', 'property="og:description"', 'name="twitter:description"'):
            html = set_meta(html, selector, desc_en.group(1))
    else:
        html = html.replace(title_en.group(0), "<title>", 1)

    html = html.replace('<html lang="es">', f'<html lang="{lang}" data-built>', 1)
    html = html.replace('<body class="lang-es">', f'<body class="lang-{lang}">', 1)
    html = set_meta(html, 'property="og:locale"', OG_LOCALE[lang])
    html = set_meta(html, 'property="og:url"', page_url(page, lang))

    links = [f'<link rel="canonical" href="{page_url(page, lang)}">']
    links += [f'<link rel="alternate" hreflang="{code}" href="{page_url(page, code)}">' for code in LANGS]
    links.append(f'<link rel="alternate" hreflang="x-default" href="{page_url(page, "es")}">')
    html, n = re.subn(r'<link rel="canonical" href="[^"]*">', "\n    ".join(links), html, count=1)
    if n != 1:
        sys.exit(f"build_site: {page}: falta <link rel=\"canonical\">")

    if lang == "en":
        html = prefix_assets(html)
    return html


def last_modified(page):
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", f"templates/pages/{page}", "templates/partials", "data"], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout.strip()
        if out:
            return out
    except (OSError, subprocess.CalledProcessError):
        pass
    return date.fromtimestamp((ROOT / "templates/pages" / page).stat().st_mtime).isoformat()


def build_sitemap():
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
             '        xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for page in PAGES:
        lastmod = last_modified(page)
        for lang in LANGS:
            lines += ["  <url>", f"    <loc>{page_url(page, lang)}</loc>", f"    <lastmod>{lastmod}</lastmod>"]
            lines += [f'    <xhtml:link rel="alternate" hreflang="{code}" href="{page_url(page, code)}"/>' for code in LANGS]
            lines += [f"    <priority>{PRIORITY[page]}</priority>", "  </url>"]
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "en").mkdir(parents=True)

    for page in PAGES:
        (OUT / page).write_text(build_page(page, "es"), encoding="utf-8")
        (OUT / "en" / page).write_text(build_page(page, "en"), encoding="utf-8")

    source_pages = {page: render_page(page) for page in PAGES}
    assets = collect_assets(ROOT, source_pages)
    for src in assets:
        destination = OUT / src.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, destination)
    print(f"Recursos publicados: {len(assets)} ({sum(p.stat().st_size for p in assets) / 1_000_000:.2f} MB)")
    for pattern in ASSET_GLOBS:
        for src in ROOT.glob(pattern):
            shutil.copy2(src, OUT / src.name)

    (OUT / "sitemap.xml").write_text(build_sitemap(), encoding="utf-8")
    try:
        from .validate_site import validate
    except ImportError:
        from validate_site import validate
    validate(OUT)
    print(f"Sitio generado en {OUT.relative_to(ROOT)}/ ({len(PAGES)} páginas × {len(LANGS)} idiomas)")


if __name__ == "__main__":
    main()
