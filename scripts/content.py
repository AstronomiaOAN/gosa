"""Render editable JSON records and shared HTML templates (standard library only)."""
import json
import re
import unicodedata
from html import escape, unescape
from pathlib import Path
from urllib.parse import quote

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


# Optional fields filled in at build time; records without them render the plain card.
DEFAULTS = {'member': {'has_profile': '', 'profile_html': '', 'card_links_html': ''}}


def render_record(kind, record):
    record = {**DEFAULTS.get(kind, {}), **record}
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


# ---------------------------------------------------------------------------
# Member profiles: articles, schools and theses already published on the site
# ---------------------------------------------------------------------------

def plain(text):
    """Visible text of a trusted HTML fragment, with whitespace collapsed."""
    return re.sub(r'\s+', ' ', unescape(re.sub(r'<[^>]+>', ' ', text or ''))).strip()


def name_tokens(text):
    text = unicodedata.normalize('NFD', plain(text).lower().replace('-', ' '))
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
    return re.sub(r'[^a-z ]', ' ', text).split()


def is_author(member, author):
    """`author` (tokens from a publication) is the member, allowing initials such as "J. C. Buitrago-Casas"."""
    if not author or (author[0] != member[0] and not (len(author[0]) == 1 and author[0] == member[0][0])):
        return False
    surnames = member[-2:] if len(member) >= 4 else member[-1:]
    if len(author[0]) == 1 and len(member) >= 4:
        return all(token in author[1:] for token in surnames)  # initials need both surnames
    if len(member) == 3 and len(author) > 1 and author[-1] == member[1]:
        return True  # "Benjamín Calvo" for Benjamín Calvo Mozo, but not "Juan Camilo Guevara" for Juan Camilo Buitrago
    return surnames[0] in author[1:]


def same_person(member, other):
    """Partial names on the site ("Paula González") against the full member name."""
    return (len(other) >= 2 and other[0] == member[0]
            and (set(other) <= set(member) or set(member) <= set(other)))


def split_authors(authors_html):
    return [name_tokens(part) for part in re.split(r',|;|\band\b', plain(authors_html)) if name_tokens(part)]


def read_theses():
    """Completed theses listed on produccion.html (author, level, year, title, directors)."""
    source = (TEMPLATES / 'pages' / 'produccion.html').read_text(encoding='utf-8')
    theses = []
    for match in re.finditer(r'<li class="tesis-item[^"]*" data-year="(\d+)"[^>]*>(.*?)</li>', source, re.S):
        body = match.group(2)
        author = re.search(r'class="tesis-author">(.*?)</p>', body, re.S).group(1)
        level = plain(re.search(r'class="tesis-cat">(.*?)</span>', author, re.S).group(1))
        directors = re.search(r'class="tesis-directors">(.*?)</div>', body, re.S)
        theses.append({
            'year': int(match.group(1)),
            'title': plain(re.search(r'class="tesis-title">(.*?)</h4>', body, re.S).group(1)),
            'level': level,
            'author': name_tokens(author.split('•', 1)[-1]),
            'directors': [name_tokens(re.sub(r'^\s*Director:?', '', item))
                          for item in re.split(r'<br\s*/?>', directors.group(1))] if directors else [],
        })
    return theses


LEVEL_EN = {'Maestría': "Master's", 'Pregrado': 'Undergraduate', 'Doctorado': 'PhD'}
# How each kind of school participation reads in the summary sentence: (label es, label en, clause es, clause en)
SCHOOL_ROLES = {
    'coord': ('Coordinación', 'Coordination', 'coordinó la {es}', 'coordinated the {en}'),
    'invited': ('Ponencia invitada', 'Invited lecture', 'dio una ponencia invitada en la {es}', 'gave an invited lecture at the {en}'),
    'teach': ('Docencia', 'Teaching', 'dictó clases en la {es}', 'taught at the {en}'),
    'defense': ('Sustentación', 'Thesis defence', 'sustentó su tesis (video disponible)', 'defended a thesis (video available)'),
    'organize': ('Organización', 'Organization', 'participó en la organización del {es}', 'helped organize the {en}'),
    'attend': ('Participación', 'Participation', 'participó en el {es}', 'took part in the {en}'),
}


def read_school_roles():
    """Who coordinated, lectured or taught in each course of material.json."""
    roles = []
    for course in read_data('material')['courses']:
        year = re.search(r'\d{4}', course['kicker_es'])
        title_es, title_en = course['title_es'], course['title_en']
        if year and year.group(0) not in title_es:
            title_es, title_en = f'{title_es} ({year.group(0)})', f'{title_en} ({year.group(0)})'
        base = {'id': course['id'], 'title_es': title_es, 'title_en': title_en, 'href': f'material.html#{course["id"]}'}
        about = course.get('about') or {}
        for group in about.get('people', []):
            kind = 'coord' if group['role_es'].lower().startswith('coord') else 'invited'
            for person in group['names']:
                name = re.sub(r'^(Prof|Dra?|Ph\.?D)\.?\s+', '', person.split('—')[0].strip())
                blocks = [(block['title_es'], block['title_en']) for block in about.get('program', [])
                          if block.get('by') and same_person(name_tokens(block['by']), name_tokens(name))]
                roles.append({**base, 'kind': kind, 'who': name_tokens(name), 'details': blocks})
        for lesson in course['lessons']:
            if course['id'] == 'tesis':
                roles.append({**base, 'kind': 'defense', 'who': name_tokens(lesson['title_es']), 'details': [],
                              'video': lesson['video']})
                continue
            for speaker in (lesson.get('speakers') or '').split('·'):
                if speaker.strip():
                    detail = (f"{lesson['title_es']}: {lesson.get('detail_es', '')}".rstrip(': '),
                              f"{lesson['title_en']}: {lesson.get('detail_en', '')}".rstrip(': '))
                    roles.append({**base, 'kind': 'teach', 'who': name_tokens(speaker), 'details': [detail]})
    # Events (data/events.json): organizers and participants; organizing takes precedence.
    for event in read_data('events')['events']:
        base = {'id': event['id'], 'title_es': event['title_es'], 'title_en': event['title_en'], 'href': event.get('href', '')}
        organizers = [name_tokens(name) for name in event.get('organizers', [])]
        roles += [{**base, 'kind': 'organize', 'who': who, 'details': []} for who in organizers]
        roles += [{**base, 'kind': 'attend', 'who': name_tokens(name), 'details': []}
                  for name in event.get('participants', []) if name_tokens(name) not in organizers]
    return roles


def join_clauses(clauses, conjunction):
    clauses = [c for c in clauses if c]
    if not clauses:
        return ''
    text = clauses[0] if len(clauses) == 1 else ', '.join(clauses[:-1]) + f' {conjunction} ' + clauses[-1]
    return text[0].upper() + text[1:] + '.'


def year_range(years):
    return str(years[0]) if years[0] == years[-1] else f'{years[0]}–{years[-1]}'


def search_query(member, matched, publications):
    """Shortest name query whose results on produccion.html cover this member's articles (and little else)."""
    texts = [' '.join(name_tokens(p['title_html'] + ' ' + p['authors_html'] + ' ' + p['extra_html'])) for p in publications]
    surnames = member[-2:] if len(member) >= 4 else member[-1:]
    for query in (surnames, member[-2:], member[1:2], member[-2:-1], [member[0]] + surnames, member):
        hits = {i for i, text in enumerate(texts) if all(term in text for term in query)}
        if hits >= matched and len(hits) <= len(matched) * 1.1 + 1:
            return ' '.join(query)
    return ''


# Research topics recognised in titles (accent-free, lower case) -> research line page.
LINE_PAGES = {
    'optica': ('optica-alta-resolucion.html', 'Óptica en alta resolución', 'High-resolution optics'),
    'radio': ('radio-rayos-x.html', 'Radio y rayos X', 'Radio and X-rays'),
    'clima': ('clima-espacial.html', 'Clima espacial', 'Space weather'),
    'ml': ('simulaciones-machine-learning.html', 'Simulaciones y machine learning', 'Simulations and machine learning'),
}
TOPICS = [
    (None, r'instrument', 'instrumentación', 'instrumentation'),
    ('optica', r'photosph|fotosf', 'fotosfera solar', 'solar photosphere'),
    ('optica', r'sunspot|manchas? solar', 'manchas solares', 'sunspots'),
    ('optica', r'granul', 'granulación', 'granulation'),
    ('optica', r'bright points?|puntos brillantes', 'puntos brillantes magnéticos', 'magnetic bright points'),
    ('optica', r'spectropolar|espectropolar', 'espectropolarimetría', 'spectropolarimetry'),
    ('optica', r'(?<!spectro)polarimetr', 'polarimetría', 'polarimetry'),
    ('optica', r'stokes', 'parámetros de Stokes', 'Stokes parameters'),
    ('optica', r'penumbr', 'penumbra de manchas', 'sunspot penumbrae'),
    ('optica', r'high.resolution|alta resolucion', 'observación de alta resolución', 'high-resolution observation'),
    ('optica', r'magnetogram|magnetic field|campos? magnetic', 'campos magnéticos', 'magnetic fields'),
    ('optica', r'correlation tracking|proper motion|movimientos propios|horizontal flow|flujos horizontales', 'flujos fotosféricos', 'photospheric flows'),
    ('optica', r'vortex|vortic', 'vórtices', 'vortices'),
    ('radio', r'\bradio', 'radioastronomía', 'radio astronomy'),
    ('radio', r'x.ray|rayos x|foxsi|rhessi', 'rayos X', 'X-rays'),
    ('radio', r'flare|fulguraci', 'fulguraciones', 'solar flares'),
    ('radio', r'chromosph|cromosf|\balma\b', 'cromosfera', 'chromosphere'),
    ('radio', r'sunquake|acoustic|acustic', 'sismos solares', 'sunquakes'),
    ('radio', r'interferomet', 'interferometría', 'interferometry'),
    ('radio', r'white.light|luz blanca', 'emisión en luz blanca', 'white-light emission'),
    ('clima', r'space weather|clima espacial', 'clima espacial', 'space weather'),
    ('clima', r'coronal mass|\bcmes?\b|eyeccion', 'eyecciones de masa coronal', 'coronal mass ejections'),
    ('clima', r'geomagnet|ionosph|ionosf|storm|tormenta', 'efectos geomagnéticos', 'geomagnetic effects'),
    ('clima', r'solar wind|viento solar', 'viento solar', 'solar wind'),
    ('clima', r'active regions?|regiones? activas?', 'regiones activas', 'active regions'),
    ('clima', r'predic|forecast|pronost', 'predicción', 'prediction'),
    ('clima', r'helioseism|heliosism', 'heliosismología', 'helioseismology'),
    ('clima', r'solar cycle|ciclo solar|solar activity|actividad solar', 'actividad y ciclo solar', 'solar activity and cycle'),
    ('clima', r'cosmic|cosmico', 'rayos cósmicos', 'cosmic rays'),
    ('ml', r'machine learning|deep learning|neural|neuronal|aprendizaje|convolution|artificial intelligence|inteligencia artificial', 'machine learning', 'machine learning'),
    ('ml', r'\bpic\b|particle.in.cell|codigos de particulas', 'simulaciones de partículas (PIC)', 'particle-in-cell (PIC) simulations'),
    ('ml', r'ondas? mhd|mhd waves?|alfven|magnetoacust|oscilaciones transversales|transverse oscillation', 'ondas MHD', 'MHD waves'),
    ('ml', r'\bmhd\b|magnetohydro|magnetohidro', 'magnetohidrodinámica (MHD)', 'magnetohydrodynamics (MHD)'),
    ('ml', r'simulat|simulaci|numeric', 'simulaciones numéricas', 'numerical simulations'),
    ('ml', r'data analysis|analisis de datos|python|database|base de datos|pipeline|algorithm|algoritmo', 'análisis de datos', 'data analysis'),
]


# What someone working on each topic knows how to do (shown as skills in the profile window).
SKILLS = {
    'fotosfera solar': ('Observación de la fotosfera', 'Photospheric observation'),
    'manchas solares': ('Análisis de manchas solares', 'Sunspot analysis'),
    'penumbra de manchas': ('Análisis de manchas solares', 'Sunspot analysis'),
    'granulación': ('Análisis de granulación', 'Granulation analysis'),
    'puntos brillantes magnéticos': ('Seguimiento de puntos brillantes', 'Bright point tracking'),
    'espectropolarimetría': ('Espectropolarimetría', 'Spectropolarimetry'),
    'polarimetría': ('Polarimetría', 'Polarimetry'),
    'parámetros de Stokes': ('Inversión de perfiles de Stokes', 'Stokes profile inversion'),
    'observación de alta resolución': ('Reducción de datos de alta resolución', 'High-resolution data reduction'),
    'campos magnéticos': ('Análisis de magnetogramas', 'Magnetogram analysis'),
    'flujos fotosféricos': ('Local Correlation Tracking (LCT)', 'Local Correlation Tracking (LCT)'),
    'vórtices': ('Detección de vórtices', 'Vortex detection'),
    'radioastronomía': ('Instrumentación en radio', 'Radio instrumentation'),
    'rayos X': ('Análisis de datos de rayos X', 'X-ray data analysis'),
    'fulguraciones': ('Análisis de fulguraciones', 'Flare analysis'),
    'cromosfera': ('Observación de la cromosfera', 'Chromospheric observation'),
    'sismos solares': ('Sismología de fulguraciones', 'Flare seismology'),
    'interferometría': ('Interferometría', 'Interferometry'),
    'emisión en luz blanca': ('Fotometría en luz blanca', 'White-light photometry'),
    'clima espacial': ('Pronóstico de clima espacial', 'Space weather forecasting'),
    'eyecciones de masa coronal': ('Análisis de eyecciones de masa coronal', 'CME analysis'),
    'efectos geomagnéticos': ('Análisis de índices geomagnéticos', 'Geomagnetic index analysis'),
    'viento solar': ('Análisis de viento solar', 'Solar wind analysis'),
    'regiones activas': ('Seguimiento de regiones activas', 'Active region tracking'),
    'heliosismología': ('Holografía heliosísmica', 'Helioseismic holography'),
    'predicción': ('Modelos de predicción', 'Predictive modelling'),
    'actividad y ciclo solar': ('Series de tiempo de actividad solar', 'Solar activity time series'),
    'rayos cósmicos': ('Análisis de rayos cósmicos', 'Cosmic ray analysis'),
    'machine learning': ('Machine learning y deep learning', 'Machine learning and deep learning'),
    'simulaciones de partículas (PIC)': ('Simulaciones PIC', 'PIC simulations'),
    'magnetohidrodinámica (MHD)': ('Modelado MHD', 'MHD modelling'),
    'ondas MHD': ('Análisis de ondas MHD', 'MHD wave analysis'),
    'instrumentación': ('Desarrollo de instrumentación', 'Instrument development'),
    'simulaciones numéricas': ('Cómputo científico', 'Scientific computing'),
    'análisis de datos': ('Análisis de datos solares', 'Solar data analysis'),
}


def member_topics(texts, lead=''):
    """Most frequent topics in a member's work titles and the research lines they belong to.
    Topics in `lead` (a hand-written bio) go first, in the order the bio mentions them."""
    lead = ' '.join(name_tokens(lead))
    def position(es):
        pattern = next(p for _, p, label, _ in TOPICS if label == es)
        found = re.search(pattern, lead)
        return found.start() if found else len(lead) + 1
    counts, line_counts = {}, {}
    for text in texts:
        text = ' '.join(name_tokens(text)) + ' ' + plain(text).lower()
        for line, pattern, es, en in TOPICS:
            if re.search(pattern, text):
                counts[(es, en)] = counts.get((es, en), 0) + 1
                if line:  # cross-cutting topics such as instrumentation belong to no single line
                    line_counts[line] = line_counts.get(line, 0) + 1
    topics = sorted(counts, key=lambda key: (position(key[0]), -counts[key]))
    lines = [LINE_PAGES[line] for line in sorted(line_counts, key=lambda line: -line_counts[line])]
    return topics, lines


# Fallback when a member has no bio, publications or theses on the site yet.
CATEGORY_TEXT = {
    'pregrado': ('{} es estudiante de pregrado y se está formando en física solar con el GoSA.',
                 '{} is an undergraduate student training in solar physics with GoSA.'),
    'maestria': ('{} es estudiante de posgrado en el GoSA.', '{} is a graduate student at GoSA.'),
    'egresado': ('{} se formó en el GoSA.', '{} trained at GoSA.'),
    'anteriores': ('{} fue integrante del GoSA.', '{} was a member of GoSA.'),
    'otras': ('{} colabora con el GoSA desde otra institución.', '{} collaborates with GoSA from another institution.'),
    'investigador': ('{} es investigador/a del GoSA.', '{} is a GoSA researcher.'),
    '': ('{} forma parte del Grupo de Astrofísica Solar (GoSA).', '{} is part of the Solar Astrophysics Group (GoSA).'),
}


def member_work_html(member, topics, lines):
    """A few words on what the member works on: hand-written bio if present, otherwise derived from their work."""
    bio = (f'<p class="pop-text">{bilingual(member["bio_es"], member.get("bio_en", member["bio_es"]))}</p>'
           if member.get('bio_es') else '')
    if bio:
        return bio  # the hand-written bio already says what they work on
    first = member['name'].split()[0]
    if not topics:
        es, en = CATEGORY_TEXT.get(member.get('category'), CATEGORY_TEXT[''])
        return f'<p class="pop-text">{bilingual(es.format(first), en.format(first))}</p>'
    def listing(items, conjunction):
        return items[0] if len(items) == 1 else ', '.join(items[:-1]) + f' {conjunction} ' + items[-1]
    line_es = listing([f'«{es}»' for _, es, _ in lines[:2]], 'y')
    line_en = listing([f'“{en}”' for _, _, en in lines[:2]], 'and')
    word_es, word_en = ('las líneas', 'the research lines') if len(lines) > 1 else ('la línea', 'the research line')
    top_es = listing([es for es, _ in topics[:3]], 'y')
    top_en = listing([en for _, en in topics[:3]], 'and')
    return (f'<p class="pop-text">{bilingual(f"Su trabajo en el grupo se relaciona con {word_es} {line_es}, en especial con temas de {top_es}.", f"Their work in the group relates to {word_en} {line_en}, especially {top_en}.")}</p>')


def member_profiles(members):
    """Extra *_html fields for the team cards: chips on the card and the emerging summary panel."""
    publications = read_data('publications')
    authors = [split_authors(p['authors_html']) for p in publications]
    theses, schools = read_theses(), read_school_roles()
    profiles = []
    for index, member in enumerate(members):
        tokens = name_tokens(member['name'])
        pubs = [i for i, people in enumerate(authors) if any(is_author(tokens, a) for a in people)]
        own = [t for t in theses if same_person(tokens, t['author'])]
        directed = [t for t in theses if any(same_person(tokens, d) for d in t['directors'])]
        roles = [r for r in schools if same_person(tokens, r['who'])]

        years = sorted({int(publications[i]['year']) for i in pubs})
        n, k = len(pubs), len(directed)
        clauses_es, clauses_en = [], []
        if pubs:
            clauses_es.append(f'ha participado en {n} artículo{"s" if n > 1 else ""} del grupo ({year_range(years)})')
            clauses_en.append(f'co-authored {n} group article{"s" if n > 1 else ""} ({year_range(years)})')
        if own:
            latest = max(own, key=lambda t: t['year'])
            clauses_es.append(f'presentó su tesis de {latest["level"].lower()} en {latest["year"]}' if len(own) == 1
                              else f'presentó {len(own)} tesis en el grupo')
            clauses_en.append(f'completed a {LEVEL_EN.get(latest["level"], latest["level"]).lower()} thesis in {latest["year"]}'
                              if len(own) == 1 else f'completed {len(own)} theses with the group')
        if directed:
            clauses_es.append(f'dirigió {k} tesis')
            clauses_en.append(f'supervised {k} thes{"es" if k > 1 else "is"}')
        seen = set()
        for role in roles:
            key = (role['kind'], role['id'])
            if key in seen or role['kind'] == 'defense' and own:
                continue
            seen.add(key)
            clauses_es.append(SCHOOL_ROLES[role['kind']][2].format(es=role['title_es']))
            clauses_en.append(SCHOOL_ROLES[role['kind']][3].format(en=role['title_en']))
        summary = bilingual(join_clauses(clauses_es, 'y'), join_clauses(clauses_en, 'and')) if clauses_es else ''

        texts = ([plain(publications[i]['title_html']) for i in pubs] + [t['title'] for t in own]
                 + [f'{es} {en}' for r in roles for es, en in r['details']])
        # A hand-written bio says best what the member works on, so its topics come first.
        bio = member.get('bio_es', '')
        topics, lines = member_topics(([bio] * 5 if bio else []) + texts, lead=bio.split('. ')[0])
        work = member_work_html(member, topics, lines)
        topic_chips = ''.join(f'<span class="member-chip">{bilingual(es, en)}</span>' for es, en in topics[:4])

        sections = []
        if pubs:
            items = ''.join(
                f'<li><span class="pop-year">{publications[i]["year"]}</span>'
                + (f'<a href="{escape(url.group(1))}" target="_blank" rel="noopener">{publications[i]["title_html"]}</a>'
                   if (url := re.search(r'href="([^"]+)"', publications[i]['action_html'])) else f'<span>{publications[i]["title_html"]}</span>')
                + '</li>' for i in pubs[:3])
            query = search_query(tokens, set(pubs), publications)
            more = (f'<a class="pop-more" href="produccion.html?q={quote(query)}">'
                    f'{bilingual("Ver todos en Producción", "See all in Research output")} <span aria-hidden="true">→</span></a>'
                    if query and n > 3 else '')
            title = bilingual('Artículos recientes', 'Recent articles') if n > 3 else bilingual('Artículos', 'Articles')
            sections.append(f'<div class="pop-section"><h5>{title}</h5><ul class="pop-list">{items}</ul>{more}</div>')
        if roles:
            grouped = {}
            for role in roles:
                grouped.setdefault(role['id'], []).append(role)
            items = []
            for cid, entries in grouped.items():
                labels = list(dict.fromkeys((SCHOOL_ROLES[e['kind']][0], SCHOOL_ROLES[e['kind']][1]) for e in entries))
                details = list(dict.fromkeys(d for e in entries for d in e['details']))
                video = next((e['video'] for e in entries if e.get('video')), '')
                detail_html = ''.join(f'<span class="pop-detail">{bilingual(es, en)}</span>' for es, en in details)
                if video:
                    detail_html += (f'<a class="pop-detail" href="https://www.youtube.com/watch?v={escape(video)}" target="_blank" '
                                    f'rel="noopener"><i class="fa-brands fa-youtube" aria-hidden="true"></i> {bilingual("Ver sustentación", "Watch the defence")}</a>')
                title = bilingual(entries[0]['title_es'], entries[0]['title_en'])
                href = entries[0].get('href')
                items.append((f'<li><a href="{escape(href)}">{title}</a>' if href else f'<li><span class="pop-event">{title}</span>')
                             + f'<span class="pop-role">{" · ".join(bilingual(es, en) for es, en in labels)}</span>{detail_html}</li>')
            sections.append(f'<div class="pop-section"><h5>{bilingual("Escuelas y eventos", "Schools and events")}</h5>'
                            f'<ul class="pop-list pop-list-plain">{"".join(items)}</ul></div>')
        if own:
            items = ''.join(f'<li><span class="pop-year">{t["year"]}</span><span>{escape(t["title"])}'
                            f'<span class="pop-role">{bilingual(t["level"], LEVEL_EN.get(t["level"], t["level"]))}</span></span></li>'
                            for t in sorted(own, key=lambda t: -t['year']))
            sections.append(f'<div class="pop-section"><h5>{bilingual("Tesis", "Thesis" if len(own) == 1 else "Theses")}</h5>'
                            f'<ul class="pop-list">{items}</ul></div>')

        institution = member.get('institution_html', '')
        emails = re.findall(r'href="mailto:([^"]+)"', member['links_html'])
        institution += ''.join(f'<a class="pop-email" href="mailto:{escape(e)}"><i class="fa-regular fa-envelope" aria-hidden="true"></i> {escape(e)}</a>'
                               for e in emails)
        head = f'''<div class="pop-head">
            <img src="{escape(member['image'])}" alt="" class="pop-avatar" loading="lazy" decoding="async" width="52" height="52">
            <div><p class="pop-name">{escape(member['name'])}</p><p class="pop-role-main">{member['role_html']}</p>{institution}</div>
        </div>'''
        lines_html = ''.join(f'<a class="member-chip member-line" href="{page}">{bilingual(es, en)} <span aria-hidden="true">→</span></a>'
                             for page, es, en in lines)
        about = (f'<div class="pop-section"><h5>{bilingual("Sobre su trabajo", "About their work")}</h5>{work}'
                 + (f'<p class="pop-summary">{summary}</p>' if summary else '')
                 + (f'<div class="member-chips pop-chips">{lines_html}</div>' if lines_html else '') + '</div>')
        skills = list(dict.fromkeys(SKILLS[es] for es, _ in topics if es in SKILLS))[:6]
        if skills:
            about += (f'<div class="pop-section"><h5>{bilingual("Habilidades", "Skills")}</h5><div class="member-chips pop-chips">'
                      + ''.join(f'<span class="member-chip member-skill">{bilingual(es, en)}</span>' for es, en in skills)
                      + '</div></div>')
        name = escape(member['name'])
        if member.get('projects'):
            items = ''.join(f'<li><a href="{escape(pr["href"])}" target="_blank" rel="noopener">{escape(pr["name"])} <span aria-hidden="true">↗</span></a></li>'
                            if pr.get('href') else f'<li>{escape(pr["name"])}</li>' for pr in member['projects'])
            about += f'<div class="pop-section"><h5>{bilingual("Proyectos", "Projects")}</h5><ul class="pop-list pop-list-plain">{items}</ul></div>'
        profiles.append({
            'has_profile': ' has-profile',
            'card_links_html': member['links_html'].replace('✉️', '<i class="fa-regular fa-envelope" aria-hidden="true"></i>'),
            # member-pop: emerging card on hover (who they are and what they work on, no counts).
            # member-details: full profile with articles, schools and theses, shown in the mini window on click.
            'profile_html': f'''
    <button type="button" class="member-open es" aria-haspopup="dialog" aria-label="Ver perfil de {name}"></button>
    <button type="button" class="member-open en" aria-haspopup="dialog" aria-label="View profile of {name}"></button>
    <div class="member-pop">
        {head}
        {f'<div class="member-chips pop-chips">{topic_chips}</div>' if topic_chips else ''}
        <p class="pop-hint"><i class="fa-solid fa-arrow-pointer" aria-hidden="true"></i> {bilingual('Haz clic para ver su perfil', 'Click to view their profile')}</p>
    </div>
    <div class="member-details" hidden>
        {head}
        {about}
        {''.join(sections)}
        <div class="member-links pop-links">{member['links_html']}</div>
    </div>''',
        })
    return profiles


# ---------------------------------------------------------------------------
# Production indicators (produccion.html): theses, publications by line, team
# ---------------------------------------------------------------------------

def bar_rows(rows, label_es, label_en):
    """Horizontal bars (label, value, optional link) scaled to the largest value; one hue, values labelled."""
    top = max(value for _, _, value, _ in rows) or 1
    items = []
    for es, en, value, href in rows:
        name = bilingual(es, en)
        name = f'<a href="{escape(href)}">{name}</a>' if href else name
        items.append(f'''<li class="ind-row" title="{escape(es)}: {value}">
                            <span class="ind-name">{name}</span>
                            <span class="ind-track"><span class="ind-fill" style="width:{value / top * 100:.1f}%"></span></span>
                            <span class="ind-val">{value}</span></li>''')
    return (f'<ul class="ind-bars" aria-label="{escape(label_es)} / {escape(label_en)}">' + ''.join(items) + '</ul>')


def render_indicators():
    theses = read_theses()
    levels = {}
    for t in theses:
        levels[t['level']] = levels.get(t['level'], 0) + 1
    directors = {' '.join(d) for t in theses for d in t['directors'] if d}
    first_year = min(t['year'] for t in theses)
    level_rows = [(level, LEVEL_EN.get(level, level), levels[level], '')
                  for level in ('Doctorado', 'Maestría', 'Pregrado') if levels.get(level)]

    publications = read_data('publications')
    line_counts, other = {}, 0
    for item in publications:
        text = ' '.join(name_tokens(item['title_html'])) + ' ' + plain(item['title_html']).lower()
        found = {line for line, pattern, _, _ in TOPICS if line and re.search(pattern, text)}
        for line in found:
            line_counts[line] = line_counts.get(line, 0) + 1
        other += not found
    line_rows = [(LINE_PAGES[line][1], LINE_PAGES[line][2], n, LINE_PAGES[line][0])
                 for line, n in sorted(line_counts.items(), key=lambda kv: -kv[1])]
    line_rows.append(('Ciencia y sociedad, otros temas', 'Science and society, other topics', other, ''))

    categories = {}
    for member in read_data('members'):
        categories[member['category']] = categories.get(member['category'], 0) + 1
    team_rows = [(es, en, categories.get(key, 0), '') for key, es, en in (
        ('investigador', 'Investigadores y colaboradores', 'Researchers and collaborators'),
        ('maestria', 'Posgrado', 'Graduate students'),
        ('pregrado', 'Pregrado', 'Undergraduates'),
        ('otras', 'Otras instituciones', 'Other institutions')) if categories.get(key)]
    current = sum(n for _, _, n, _ in team_rows)
    alumni = categories.get('egresado', 0) + categories.get('anteriores', 0)

    def card(title_es, title_en, number, number_es, number_en, rows, note_es, note_en):
        return f'''<div class="ind-card">
                        <h5 class="ind-title">{bilingual(title_es, title_en)}</h5>
                        <p class="ind-big"><span class="ind-num">{number}</span> {bilingual(number_es, number_en)}</p>
                        {bar_rows(rows, title_es, title_en)}
                        <p class="ind-note">{bilingual(note_es, note_en)}</p>
                    </div>'''

    return f'''<div class="info-panel ind-panel">
                        <div class="info-panel-head">
                            <div>
                                <h4 class="info-section-title">{bilingual('Formación, líneas y equipo', 'Training, research lines and team')}</h4>
                                <p class="info-section-sub">{bilingual('Indicadores calculados a partir de las tesis, publicaciones e integrantes listados en el sitio', 'Indicators computed from the theses, publications and members listed on the site')}</p>
                            </div>
                        </div>
                        <div class="ind-grid">
                    {card('Tesis completadas', 'Completed theses', len(theses), f'tesis desde {first_year}', f'theses since {first_year}',
                          level_rows, f'Dirigidas o codirigidas por {len(directors)} investigadores.',
                          f'Supervised or co-supervised by {len(directors)} researchers.')}
                    {card('Publicaciones por línea', 'Publications by research line', len(publications), 'publicaciones', 'publications',
                          line_rows, 'Clasificadas por palabras clave del título; una publicación puede tocar varias líneas.',
                          'Classified by title keywords; a publication can belong to several lines.')}
                    {card('Equipo actual', 'Current team', current, 'integrantes', 'members',
                          team_rows, f'Además, {alumni} egresados y antiguos integrantes han pasado por el grupo.',
                          f'In addition, {alumni} alumni and former members have been part of the group.')}
                        </div>
                    </div>'''


# ---------------------------------------------------------------------------
# News: short summary and target link (RSS feed and rss.html)
# ---------------------------------------------------------------------------

def news_summary_html(body_html, limit=320):
    """Leading paragraphs of a news body (trusted HTML), without tables, expandable blocks or "Ver más →" links."""
    # "Ver más →" call-to-action links are dropped; links inside a sentence keep their text.
    body = re.sub(r'<a\b[^>]*class="news-link"[^>]*>(.*?)</a>',
                  lambda m: '' if '→' in m.group(1) else m.group(1), body_html, flags=re.S)
    body = re.sub(r'<table\b.*?</table>', '', body, flags=re.S)
    paragraphs, length = [], 0
    for paragraph in re.findall(r'<p\b[^>]*>(.*?)</p>', body, flags=re.S):
        text = plain(paragraph)
        if not text:
            continue
        paragraphs.append(paragraph.strip())
        length += len(text) / 2  # both languages are in the same fragment
        if length >= limit:
            break
    return ' '.join(paragraphs)


def news_link(record):
    """Where a news item points: its own "Ver más →" link, else the news section of the home page."""
    found = re.search(r'<a\b[^>]*href="([^"]+)"[^>]*class="news-link"|<a\b[^>]*class="news-link"[^>]*href="([^"]+)"',
                      record['body_html'], flags=re.S)
    return (found.group(1) or found.group(2)) if found else 'index.html#novedades'


def render_rss_items():
    items = []
    for record in read_data('news').get('index.html', []):
        href = news_link(record)
        external = href.startswith('http')
        items.append(f'''                        <li class="rss-item">
                            <h3><a href="{escape(href)}"{' target="_blank" rel="noopener"' if external else ''}>{record['title_html']}</a></h3>
                            <p class="rss-date">{record['date_html']}</p>
                            <p>{news_summary_html(record['body_html'])}</p>
                        </li>''')
    return '\n'.join(items)


def initials_avatar(name):
    """Inline SVG with the member's initials, instead of requesting a third-party avatar service."""
    initials = ''.join(part[0] for part in name.split()[:2]).upper()
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120">'
           '<rect width="120" height="120" fill="#133f59"/>'
           f'<text x="60" y="62" dominant-baseline="middle" text-anchor="middle" font-family="Georgia, serif" '
           f'font-size="40" fill="#e0bd86">{escape(initials)}</text></svg>')
    return 'data:image/svg+xml,' + quote(svg)


def render_page(page, extra=None):
    source = (TEMPLATES / 'pages' / page).read_text(encoding='utf-8')
    values = {
        **(extra or {}),
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
        members = [{**item, 'image': initials_avatar(item['name'])} if 'ui-avatars.com' in item['image'] else item
                   for item in read_data('members')]
        values['members'] = '\n'.join(render_record('member', {**item, **extra})
                                      for item, extra in zip(members, member_profiles(members)))
    if '{{indicators}}' in source:
        values['indicators'] = render_indicators()
    if '{{rss_items}}' in source:
        values['rss_items'] = render_rss_items()
    if '{{material}}' in source:
        values['material'] = render_material(read_data('material'))
    for index, record in enumerate(read_data('news').get(page, [])):
        values[f'news:{index}'] = render_record('news', record)
    return substitute(source, values)
