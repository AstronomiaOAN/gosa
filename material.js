// Aula virtual (material.html): un curso visible a la vez, reproductor con
// anterior/siguiente y clases vistas guardadas en el navegador.
// Sin JavaScript la página sigue funcionando: todos los cursos se ven y cada
// clase enlaza a YouTube.
(() => {
    const courses = [...document.querySelectorAll('[data-course]')];
    if (!courses.length) return;

    const STORAGE_KEY = 'gosa_material_vistos';
    const seen = new Set();
    try { JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]').forEach(id => seen.add(id)); }
    catch { /* Storage may be disabled. */ }
    const saveSeen = () => {
        try { localStorage.setItem(STORAGE_KEY, JSON.stringify([...seen])); }
        catch { /* Storage may be disabled. */ }
    };

    const embedUrl = id => `https://www.youtube-nocookie.com/embed/${encodeURIComponent(id)}?autoplay=1&rel=0`;
    const thumbUrl = id => `https://i.ytimg.com/vi/${encodeURIComponent(id)}/hqdefault.jpg`;
    const tabs = [...document.querySelectorAll('[data-course-tab]')];
    const players = new Map();

    function setupCourse(course) {
        const lessons = [...course.querySelectorAll('.lesson')];
        const frame = course.querySelector('[data-player]');
        const poster = frame.querySelector('[data-play]');
        const posterImg = poster.querySelector('img');
        const q = sel => course.querySelector(sel);
        const state = { index: 0, playing: false };

        const lessonText = (lesson, sel) => lesson.querySelector(sel)?.innerHTML.trim() || '';

        function updateProgress() {
            let count = 0;
            lessons.forEach(lesson => {
                const isSeen = seen.has(lesson.dataset.video);
                lesson.classList.toggle('seen', isSeen);
                if (isSeen) count++;
            });
            q('[data-seen]').textContent = count;
            q('[data-bar]').style.width = `${(count / lessons.length) * 100}%`;
        }

        function stop() {
            frame.querySelector('iframe')?.remove();
            poster.hidden = false;
            state.playing = false;
        }

        function play() {
            const lesson = lessons[state.index];
            const id = lesson.dataset.video;
            if (location.protocol === 'file:') {
                // Opened from disk there is no origin to send, and YouTube refuses
                // the embed (error 153): open the class on YouTube instead.
                window.open(`https://www.youtube.com/watch?v=${encodeURIComponent(id)}`, '_blank', 'noopener');
                seen.add(id);
                saveSeen();
                updateProgress();
                return;
            }
            let iframe = frame.querySelector('iframe');
            if (!iframe) {
                iframe = document.createElement('iframe');
                iframe.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture';
                iframe.allowFullscreen = true;
                iframe.referrerPolicy = 'strict-origin-when-cross-origin';
                frame.appendChild(iframe);
            }
            iframe.title = lesson.querySelector('.lesson-title').textContent.trim();
            iframe.src = embedUrl(id);
            poster.hidden = true;
            state.playing = true;
            seen.add(id);
            saveSeen();
            updateProgress();
        }

        function select(index, { autoplay = state.playing, scroll = false, updateHash = true } = {}) {
            state.index = Math.max(0, Math.min(index, lessons.length - 1));
            const lesson = lessons[state.index];
            const id = lesson.dataset.video;
            const youtube = `https://www.youtube.com/watch?v=${encodeURIComponent(id)}`;

            lessons.forEach((item, i) => {
                item.classList.toggle('active', i === state.index);
                if (i === state.index) item.setAttribute('aria-current', 'true');
                else item.removeAttribute('aria-current');
            });
            q('[data-step]').textContent = state.index + 1;
            q('[data-title]').innerHTML = lessonText(lesson, '.lesson-title');
            q('[data-detail]').innerHTML = lessonText(lesson, '.lesson-detail');
            q('[data-speakers]').innerHTML = lessonText(lesson, '.lesson-speakers');
            q('[data-youtube]').href = youtube;
            poster.href = youtube;
            posterImg.src = thumbUrl(id);
            q('[data-prev]').disabled = state.index === 0;
            q('[data-next]').disabled = state.index === lessons.length - 1;

            if (autoplay) play();
            else stop();
            if (updateHash) {
                const hash = state.index ? `#${course.id}/${state.index + 1}` : `#${course.id}`;
                history.replaceState(null, '', hash);
            }
            if (scroll) {
                const top = frame.getBoundingClientRect().top;
                if (top < 80 || top > window.innerHeight * 0.5) {
                    frame.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
            // Keep the active lesson visible inside the scrollable list.
            const list = lesson.closest('.lesson-list');
            if (list && list.scrollHeight > list.clientHeight) {
                const item = lesson.parentElement;
                if (item.offsetTop < list.scrollTop || item.offsetTop + item.offsetHeight > list.scrollTop + list.clientHeight) {
                    list.scrollTo({ top: item.offsetTop - 8, behavior: 'smooth' });
                }
            }
        }

        lessons.forEach((lesson, i) => lesson.addEventListener('click', e => {
            if (e.metaKey || e.ctrlKey || e.shiftKey || e.button === 1) return; // let users open YouTube in a new tab
            e.preventDefault();
            select(i, { autoplay: true, scroll: true });
        }));
        poster.addEventListener('click', e => { e.preventDefault(); play(); });
        q('[data-prev]').addEventListener('click', () => select(state.index - 1, { scroll: true }));
        q('[data-next]').addEventListener('click', () => select(state.index + 1, { scroll: true }));

        updateProgress();
        return { select, stop, state };
    }

    courses.forEach(course => players.set(course.id, setupCourse(course)));
    document.documentElement.classList.add('js-courses');

    function activate(courseId, lessonNumber = 1, { updateHash = true } = {}) {
        if (!players.has(courseId)) courseId = courses[0].id;
        courses.forEach(course => {
            const active = course.id === courseId;
            course.classList.toggle('active', active);
            if (!active) players.get(course.id).stop();
        });
        tabs.forEach(tab => {
            const active = tab.dataset.courseTab === courseId;
            tab.classList.toggle('active', active);
            if (active) tab.setAttribute('aria-current', 'true');
            else tab.removeAttribute('aria-current');
        });
        players.get(courseId).select(lessonNumber - 1, { autoplay: false, updateHash });
    }

    function fromHash({ updateHash = false } = {}) {
        const [courseId, lesson] = decodeURIComponent(location.hash.slice(1)).split('/');
        activate(courseId, parseInt(lesson, 10) || 1, { updateHash });
    }

    tabs.forEach(tab => tab.addEventListener('click', e => {
        e.preventDefault();
        activate(tab.dataset.courseTab);
        const course = document.getElementById(tab.dataset.courseTab);
        if (course.getBoundingClientRect().top > window.innerHeight * 0.6) {
            course.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }));
    window.addEventListener('hashchange', () => fromHash());
    fromHash();
})();
