"""Render editable JSON records and shared HTML templates (standard library only)."""
import json
import re
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / 'templates'


def read_data(name):
    return json.loads((ROOT / 'data' / f'{name}.json').read_text(encoding='utf-8'))


def substitute(template, values):
    def replace(match):
        key = match.group(1)
        if key not in values:
            raise ValueError(f'Missing template value: {key}')
        return str(values[key])
    return re.sub(r'\{\{([\w:]+)\}\}', replace, template)


def render_record(kind, record):
    # Only explicit *_html fields contain trusted, repository-authored HTML.
    values = {key: value if key.endswith('_html') else escape(str(value), quote=True)
              for key, value in record.items()}
    template = (TEMPLATES / 'partials' / f'{kind}.html').read_text(encoding='utf-8')
    return substitute(template, values)


def render_page(page):
    source = (TEMPLATES / 'pages' / page).read_text(encoding='utf-8')
    values = {
        'header': substitute((TEMPLATES / 'partials/header.html').read_text(encoding='utf-8'),
                             {'home': '' if page == 'index.html' else 'index.html'}),
        'footer': substitute((TEMPLATES / 'partials/footer.html').read_text(encoding='utf-8'),
                             {'home': '' if page == 'index.html' else 'index.html'}),
    }
    if '{{publications}}' in source:
        records = read_data('publications')
        values['publications'] = '\n'.join(render_record('publication', item) for item in records)
        # The year selector follows the data, so new years never require HTML edits.
        years = sorted({int(item['year']) for item in records}, reverse=True)
        options = '<option value="all"><span class="es">Todos los años</span><span class="en">All years</span></option>'
        options += ''.join(f'<option value="{year}">{year}</option>' for year in years)
        source = re.sub(r'(<select id="pub-year-filter">).*?(</select>)',
                        lambda m: m[1] + options + m[2], source, flags=re.S)
    if '{{members}}' in source:
        values['members'] = '\n'.join(render_record('member', item) for item in read_data('members'))
    for index, record in enumerate(read_data('news').get(page, [])):
        values[f'news:{index}'] = render_record('news', record)
    return substitute(source, values)
