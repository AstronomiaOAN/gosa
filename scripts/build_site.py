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

import hashlib
import json
import re
import shutil
from email.utils import format_datetime
from datetime import datetime, timezone
from html import escape as html_escape
import subprocess
import sys
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

try:
    from .content import name_tokens, plain, read_data, render_page
    from .site_assets import collect_assets
except ImportError:
    from content import name_tokens, plain, read_data, render_page
    from site_assets import collect_assets

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "_site"
BASE_URL = "https://astronomiaoan.co/gosa/"

RESEARCH_PAGES = ["optica-alta-resolucion.html", "radio-rayos-x.html", "clima-espacial.html",
                  "simulaciones-machine-learning.html"]
PAGES = ["index.html", "escuela.html", "material.html", "produccion.html", "dynasun.html"] + RESEARCH_PAGES
PRIORITY = {"index.html": "1.0", "escuela.html": "0.8", "material.html": "0.7", "produccion.html": "0.8", "dynasun.html": "0.7",
            **{page: "0.8" for page in RESEARCH_PAGES}}
# Archivos y carpetas que se publican tal cual (el resto del repo no se sube).
ASSET_GLOBS = ["google*.html"]
# Página de error: una sola, bilingüe, en la raíz (GitHub Pages la sirve en cualquier ruta inexistente).
NOT_FOUND = "404.html"

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

    links = [f'<link rel="canonical" href="{page_url(page, lang)}">',
             f'<link rel="alternate" type="application/rss+xml" title="{FEED_TITLE[lang]}" href="{feed_url(lang)}">']
    links += [f'<link rel="alternate" hreflang="{code}" href="{page_url(page, code)}">' for code in LANGS]
    links.append(f'<link rel="alternate" hreflang="x-default" href="{page_url(page, "es")}">')
    html, n = re.subn(r'<link rel="canonical" href="[^"]*">', "\n    ".join(links), html, count=1)
    if n != 1:
        sys.exit(f"build_site: {page}: falta <link rel=\"canonical\">")

    html = add_analytics(version_assets(html))
    if lang == "en":
        html = prefix_assets(html)
    return html


def site_config():
    try:
        return json.loads((ROOT / "data" / "site.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def add_analytics(html):
    """GoatCounter (sin cookies) si data/site.json define su código; si está vacío no se añade nada."""
    code = site_config().get("goatcounter", "").strip()
    if not code:
        return html
    if not re.fullmatch(r"[a-z0-9-]+", code):
        sys.exit(f"build_site: código de GoatCounter no válido en data/site.json: {code!r}")
    tag = (f'    <script data-goatcounter="https://{code}.goatcounter.com/count" async '
           f'src="https://gc.zgo.at/count.js"></script>\n')
    return html.replace("</body>", tag + "</body>", 1)


def build_not_found():
    base = urlsplit(BASE_URL).path or "/"
    html = render_page(NOT_FOUND, {"base": f'<base href="{base}">'})
    return add_analytics(version_assets(html))


def version_assets(html):
    """styles.css -> styles.css?v=<hash>: browsers fetch the new file on every change instead of a cached copy."""
    def stamp(m):
        path = ROOT / m.group(2)
        if not path.is_file():
            return m.group(0)
        digest = hashlib.sha1(path.read_bytes()).hexdigest()[:10]
        return f'{m.group(1)}="{m.group(2)}?v={digest}"'
    return re.sub(r'\b(href|src)="([\w./-]+\.(?:css|js))"', stamp, html)


def last_modified(page):
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", f"templates/pages/{page}", "templates/partials", "data"], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout.strip()
        if out:
            return out
    except (OSError, subprocess.CalledProcessError):
        pass
    return date.fromtimestamp((ROOT / "templates/pages" / page).stat().st_mtime).isoformat()


FEED_TITLE = {"es": "GoSA · Novedades", "en": "GoSA · News"}
FEED_DESC = {"es": "Novedades del Grupo de Astrofísica Solar (GoSA), Observatorio Astronómico Nacional, UNAL.",
             "en": "News from the Solar Astrophysics Group (GoSA), National Astronomical Observatory, UNAL."}


def feed_url(lang):
    return BASE_URL + ("en/" if lang == "en" else "") + "feed.xml"


def in_language(fragment, lang):
    parser = LangFilter(drop="en" if lang == "es" else "es")
    parser.feed(fragment)
    parser.close()
    return plain("".join(parser.out))


def build_feed(lang):
    """RSS 2.0 con las novedades de la portada (data/news.json -> index.html).
    Un campo opcional "date" (AAAA-MM-DD) en cada novedad se publica como pubDate."""
    link = page_url("index.html", lang) + "#novedades"
    items = []
    for record in read_data("news").get("index.html", []):
        title = in_language(record["title_html"], lang)
        body = in_language(record["body_html"], lang)
        if len(body) > 600:
            body = body[:600].rsplit(" ", 1)[0] + "…"
        slug = "-".join(name_tokens(in_language(record["title_html"], "es")))[:80]
        item = [f"      <title>{html_escape(title)}</title>", f"      <link>{link}</link>",
                f'      <guid isPermaLink="false">gosa-news-{slug}</guid>',
                f"      <description>{html_escape(body)}</description>"]
        if record.get("date"):
            when = datetime.fromisoformat(record["date"]).replace(tzinfo=timezone.utc)
            item.append(f"      <pubDate>{format_datetime(when)}</pubDate>")
        items.append("    <item>\n" + "\n".join(item) + "\n    </item>")
    return "\n".join([
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
        "  <channel>",
        f"    <title>{FEED_TITLE[lang]}</title>",
        f"    <link>{page_url('index.html', lang)}</link>",
        f"    <description>{FEED_DESC[lang]}</description>",
        f"    <language>{'es-co' if lang == 'es' else 'en'}</language>",
        f'    <atom:link href="{feed_url(lang)}" rel="self" type="application/rss+xml"/>',
        *items,
        "  </channel>",
        "</rss>",
        "",
    ])


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

    (OUT / NOT_FOUND).write_text(build_not_found(), encoding="utf-8")

    source_pages = {page: render_page(page) for page in PAGES}
    source_pages[NOT_FOUND] = render_page(NOT_FOUND, {"base": ""})
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
    for lang in LANGS:
        (OUT / ("en" if lang == "en" else "") / "feed.xml").write_text(build_feed(lang), encoding="utf-8")
    try:
        from .validate_site import validate
    except ImportError:
        from validate_site import validate
    validate(OUT)
    print(f"Sitio generado en {OUT.relative_to(ROOT)}/ ({len(PAGES)} páginas × {len(LANGS)} idiomas)")


if __name__ == "__main__":
    main()
