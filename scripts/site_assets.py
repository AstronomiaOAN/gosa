"""Discover local assets transitively from HTML/CSS, including social metadata."""
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

SITE_HOST = 'astronomiaoan.co'
SITE_PREFIX = '/gosa/'


def css_urls(text):
    pattern = r"url\(\s*(?:'([^']*)'|\"([^\"]*)\"|([^)]*?))\s*\)"
    return [next(value for value in match if value).strip() for match in re.findall(pattern, text)]


class References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.references = []
        self.ids = []
        self.jsonld = False
        self.json_text = ''

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        for key in ('href', 'src', 'poster'):
            if attrs.get(key):
                self.references.append(attrs[key])
        for entry in attrs.get('srcset', '').split(','):
            if entry.strip():
                self.references.append(entry.strip().split()[0])
        self.references.extend(css_urls(attrs.get('style', '')))
        if tag == 'meta' and attrs.get('property', attrs.get('name')) in ('og:image', 'twitter:image'):
            self.references.append(attrs.get('content', ''))
        if tag == 'script' and attrs.get('type') == 'application/ld+json':
            self.jsonld = True
            self.json_text = ''

    def handle_data(self, data):
        if self.jsonld:
            self.json_text += data

    def handle_endtag(self, tag):
        if tag == 'script' and self.jsonld:
            def visit(value):
                if isinstance(value, dict):
                    for key, child in value.items():
                        if key in ('logo', 'image') and isinstance(child, str):
                            self.references.append(child)
                        else:
                            visit(child)
                elif isinstance(value, list):
                    for child in value:
                        visit(child)
            visit(json.loads(self.json_text))
            self.jsonld = False


def local_target(root, source, url):
    parsed = urlsplit(url)
    if parsed.netloc and parsed.netloc != SITE_HOST:
        return None
    if parsed.scheme and parsed.scheme not in ('http', 'https'):
        return None
    path = unquote(parsed.path)
    if path.startswith(SITE_PREFIX):
        target = root / path[len(SITE_PREFIX):]
    elif path.startswith('/'):
        return None  # Outside this site's deployment prefix.
    elif parsed.netloc:
        return None
    else:
        target = source.parent / path if path else source
    target = target.resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError(f'Local reference escapes site: {source}: {url}')
    if path.endswith('/') or target == root.resolve():
        target /= 'index.html'
    return target, unquote(parsed.fragment)


def references(text):
    parser = References()
    parser.feed(text)
    # Includes CSS in <style> blocks as well as style attributes.
    parser.references.extend(css_urls(text))
    return parser


def collect_assets(root, pages):
    """pages maps output paths (relative to root) to rendered HTML."""
    pending = []
    for name, html in pages.items():
        pending.extend((root / name, url) for url in references(html).references)
    assets = set()
    while pending:
        source, url = pending.pop()
        resolved = local_target(root, source, url)
        if not resolved:
            continue
        target, _ = resolved
        if target.suffix == '.html' or target.name == 'sitemap.xml':
            continue
        if target in assets:
            continue
        if not target.is_file():
            raise ValueError(f'Missing asset: {source.relative_to(root)} → {url}')
        assets.add(target)
        if target.suffix == '.css':
            pending.extend((target, item) for item in css_urls(target.read_text(encoding='utf-8')))
    return sorted(assets)
