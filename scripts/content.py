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


def bilingual(es, en):
    es, en = escape(es), escape(en)
    return es if es == en else f'<span class="es">{es}</span><span class="en">{en}</span>'


def duration(seconds):
    hours, minutes = divmod(round(seconds / 60), 60)
    return f'{hours} h {minutes:02d} min' if hours else f'{minutes} min'


def youtube(video):
    return f'https://www.youtube.com/watch?v={escape(video)}'


def thumbnail(video):
    return f'https://i.ytimg.com/vi/{escape(video)}/hqdefault.jpg'


def render_about(about):
    """Collapsible block with a course's dates, people and programme."""
    if not about:
        return ''
    facts = ''.join(f'''
                            <div class="school-fact"><i class="{escape(fact['icon'])}" aria-hidden="true"></i>
                                <span><strong>{bilingual(fact['label_es'], fact['label_en'])}</strong>{bilingual(fact['value_es'], fact['value_en'])}</span></div>'''
                    for fact in about.get('facts', []))
    people = ''.join(f'''
                            <div class="school-people"><h4>{bilingual(group['role_es'], group['role_en'])}</h4>
                                <ul>{''.join(f'<li>{escape(name)}</li>' for name in group['names'])}</ul></div>'''
                     for group in about.get('people', []))
    program = ''.join(f'''
                            <div class="school-block"><h4>{bilingual(block['title_es'], block['title_en'])}</h4>'''
                      + (f'<p class="school-by">{escape(block["by"])}</p>' if block.get('by') else '')
                      + f'''
                                <ul class="es">{''.join(f'<li>{escape(item)}</li>' for item in block['items_es'])}</ul>
                                <ul class="en">{''.join(f'<li>{escape(item)}</li>' for item in block['items_en'])}</ul></div>'''
                      for block in about.get('program', []))
    return f'''
                    <details class="course-about">
                        <summary><i class="fa-solid fa-circle-info" aria-hidden="true"></i> {bilingual('Sobre la escuela y programa', 'About the school and programme')}</summary>
                        <div class="school-facts">{facts}
                        </div>
                        <div class="school-grid">{people}
                        </div>
                        <h4 class="school-heading">{bilingual('Programa', 'Programme')}</h4>
                        <div class="school-grid">{program}
                        </div>
                    </details>'''


def render_material(data):
    """Course-style video library: tabs, a player per course and its lesson list."""
    tabs, courses = [], []
    for course in data['courses']:
        cid, lessons = escape(course['id']), course['lessons']
        unit = bilingual(course['unit_es'], course['unit_en'])
        total = duration(sum(lesson['seconds'] for lesson in lessons))
        count = f'{len(lessons)} ' + bilingual('videos', 'videos')
        tabs.append(f'''
                    <a class="course-tab" href="#{cid}" data-course-tab="{cid}">
                        <span class="course-tab-cover"><img src="{thumbnail(lessons[0]['video'])}" alt="" loading="lazy" decoding="async"></span>
                        <span class="course-tab-text">
                            <span class="course-kicker">{bilingual(course['kicker_es'], course['kicker_en'])}</span>
                            <span class="course-tab-title">{bilingual(course['title_es'], course['title_en'])}</span>
                            <span class="course-tab-meta">{count} · {total}</span>
                        </span>
                    </a>''')
        links = ''.join(
            f'<a class="course-link" href="{escape(link["href"])}"'
            + ('' if '://' not in link['href'] else ' target="_blank" rel="noopener"')
            + f'><i class="{escape(link["icon"])}" aria-hidden="true"></i> {bilingual(link["label_es"], link["label_en"])}</a>'
            for link in course.get('links', []))
        items = []
        for index, lesson in enumerate(lessons):
            detail = bilingual(lesson.get('detail_es', ''), lesson.get('detail_en', ''))
            speakers = escape(lesson.get('speakers', ''))
            items.append(f'''
                            <li>
                                <a class="lesson" href="{youtube(lesson['video'])}" target="_blank" rel="noopener" data-video="{escape(lesson['video'])}" data-index="{index}">
                                    <span class="lesson-num">{index + 1}</span>
                                    <span class="lesson-body">
                                        <span class="lesson-title">{bilingual(lesson['title_es'], lesson['title_en'])}</span>
                                        <span class="lesson-detail">{detail}</span>
                                        <span class="lesson-speakers">{speakers}</span>
                                        <span class="lesson-time"><i class="fa-regular fa-clock" aria-hidden="true"></i> {duration(lesson['seconds'])}</span>
                                    </span>
                                    <i class="lesson-check fa-solid fa-circle-check" aria-hidden="true"></i>
                                </a>
                            </li>''')
        first = lessons[0]
        courses.append(f'''
            <section class="course" id="{cid}" data-course="{cid}">
                <div class="course-head">
                    <p class="course-kicker">{bilingual(course['kicker_es'], course['kicker_en'])}</p>
                    <h2 class="course-title">{bilingual(course['title_es'], course['title_en'])}</h2>
                    <p class="course-summary">{bilingual(course['summary_es'], course['summary_en'])}</p>
                    <div class="course-links">
                        <span class="course-stat"><i class="fa-solid fa-circle-play" aria-hidden="true"></i> {count}</span>
                        <span class="course-stat"><i class="fa-regular fa-clock" aria-hidden="true"></i> {total}</span>
                        {links}
                    </div>{render_about(course.get('about'))}
                </div>
                <div class="course-layout">
                    <div class="player">
                        <div class="player-frame" data-player>
                            <a class="player-poster" href="{youtube(first['video'])}" target="_blank" rel="noopener" data-play>
                                <img src="{thumbnail(first['video'])}" alt="" decoding="async">
                                <span class="player-play"><i class="fa-solid fa-play" aria-hidden="true"></i><span class="sr-only">{bilingual('Reproducir', 'Play')}</span></span>
                            </a>
                        </div>
                        <div class="player-info">
                            <p class="player-step">{unit} <span data-step>1</span> / {len(lessons)}</p>
                            <h3 class="player-title" data-title>{bilingual(first['title_es'], first['title_en'])}</h3>
                            <p class="player-detail" data-detail>{bilingual(first.get('detail_es', ''), first.get('detail_en', ''))}</p>
                            <p class="player-speakers" data-speakers>{escape(first.get('speakers', ''))}</p>
                            <div class="player-nav">
                                <button type="button" class="player-btn" data-prev disabled><i class="fa-solid fa-chevron-left" aria-hidden="true"></i> {bilingual('Anterior', 'Previous')}</button>
                                <a class="player-yt" href="{youtube(first['video'])}" target="_blank" rel="noopener" data-youtube><i class="fa-brands fa-youtube" aria-hidden="true"></i> YouTube</a>
                                <button type="button" class="player-btn player-btn-next" data-next{' disabled' if len(lessons) == 1 else ''}>{bilingual('Siguiente', 'Next')} <i class="fa-solid fa-chevron-right" aria-hidden="true"></i></button>
                            </div>
                        </div>
                    </div>
                    <aside class="lesson-panel">
                        <div class="lesson-progress">
                            <span>{bilingual('Tu progreso', 'Your progress')}</span>
                            <span><span data-seen>0</span> / {len(lessons)}</span>
                            <span class="lesson-bar"><span data-bar></span></span>
                        </div>
                        <ol class="lesson-list">{''.join(items)}
                        </ol>
                    </aside>
                </div>
            </section>''')
    return f'''<div class="course-tabs" role="navigation" aria-label="{escape('Cursos / Courses')}">{''.join(tabs)}
                </div>
{''.join(courses)}'''


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
    if '{{material}}' in source:
        values['material'] = render_material(read_data('material'))
    for index, record in enumerate(read_data('news').get(page, [])):
        values[f'news:{index}'] = render_record('news', record)
    return substitute(source, values)
