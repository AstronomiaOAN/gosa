#!/usr/bin/env python3
"""Fail a build on broken internal links, assets, IDs or language metadata."""
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

try:
    from .site_assets import references, local_target, css_urls
except ImportError:
    from site_assets import references, local_target, css_urls


class Metadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self.lang = None
        self.links = []
        self.navigation = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'html':
            self.lang = attrs.get('lang')
        if tag == 'link':
            self.links.append(attrs)
        if tag == 'a' and 'nav-link' in attrs.get('class', '').split():
            self.navigation.append(attrs.get('href', ''))


def validate(root):
    root = root.resolve()
    errors = []
    parsed = {}
    for page in root.rglob('*.html'):
        html = page.read_text(encoding='utf-8')
        parsed[page] = references(html)
        duplicates = [key for key, n in Counter(parsed[page].ids).items() if n > 1]
        if duplicates:
            errors.append(f'{page.relative_to(root)}: duplicate IDs {duplicates}')
        if '{{' in html:
            errors.append(f'{page.relative_to(root)}: unresolved template')
        if page.name.startswith('google'):
            continue
        meta = Metadata()
        meta.feed(html)
        expected = 'en' if page.parent == root / 'en' else 'es'
        if meta.lang != expected:
            errors.append(f'{page.relative_to(root)}: expected lang={expected}')
        canonical = [link['href'] for link in meta.links if link.get('rel') == 'canonical']
        if len(canonical) != 1 or local_target(root, page, canonical[0])[0] != page:
            errors.append(f'{page.relative_to(root)}: invalid canonical')
        alternates = {link.get('hreflang'): link.get('href', '') for link in meta.links if link.get('rel') == 'alternate'}
        for language in ('es', 'en', 'x-default'):
            target = local_target(root, page, alternates.get(language, ''))
            expected_page = root / ('en' if language == 'en' else '') / page.name
            if not alternates.get(language) or not target or target[0] != expected_page:
                errors.append(f'{page.relative_to(root)}: invalid hreflang {language}')
        for url in meta.navigation:
            target = local_target(root, page, url)
            if target and target[0].suffix == '.html' and (target[0].parent == root / 'en') != (expected == 'en'):
                errors.append(f'{page.relative_to(root)}: navigation changes language: {url}')
    for page, data in parsed.items():
        for url in data.references:
            target = local_target(root, page, url)
            if not target:
                continue
            path, fragment = target
            if not path.is_file():
                errors.append(f'{page.relative_to(root)}: missing target {url}')
            elif fragment and path.suffix == '.html' and fragment not in parsed[path].ids:
                errors.append(f'{page.relative_to(root)}: missing anchor {url}')
    for css in root.rglob('*.css'):
        for url in css_urls(css.read_text(encoding='utf-8')):
            target = local_target(root, css, url)
            if target and not target[0].is_file():
                errors.append(f'{css.relative_to(root)}: missing asset {url}')
    sitemap = ET.parse(root / 'sitemap.xml')
    urls = sitemap.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
    expected_pages = {p for p in parsed if not p.name.startswith('google')}
    actual_pages = {local_target(root, root / 'index.html', node.text)[0] for node in urls}
    if actual_pages != expected_pages or len(urls) != len(expected_pages):
        errors.append('Sitemap does not match published pages')
    if errors:
        raise ValueError('Site validation failed:\n' + '\n'.join(sorted(set(errors))))
    print(f'Validated {len(expected_pages)} pages: links, assets, IDs, languages and sitemap.')


if __name__ == '__main__':
    validate(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / '_site')
