document.addEventListener('DOMContentLoaded', () => {
    const buildAvatarFallback = (name) => {
        const initials = (name || 'GoSA')
            .split(/\s+/)
            .filter(Boolean)
            .slice(0, 2)
            .map(part => part[0].toUpperCase())
            .join('');
        const svg = `
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" role="img" aria-label="${name || 'Avatar'}">
                <defs>
                    <linearGradient id="avatar-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stop-color="#ff7900" />
                        <stop offset="100%" stop-color="#9d4edd" />
                    </linearGradient>
                </defs>
                <rect width="120" height="120" rx="60" fill="url(#avatar-gradient)" />
                <text x="50%" y="53%" dominant-baseline="middle" text-anchor="middle"
                    font-family="Outfit, Arial, sans-serif" font-size="38" font-weight="700" fill="#ffffff">${initials}</text>
            </svg>`;

        return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
    };

    const initTeamAvatars = () => {
        document.querySelectorAll('.team-avatar-img').forEach(img => {
            const fallbackSrc = buildAvatarFallback(img.alt);
            const applyFallback = () => {
                if (img.dataset.fallbackApplied === 'true') return;
                img.dataset.fallbackApplied = 'true';
                img.src = fallbackSrc;
            };

            // Avoid relying on third-party avatar services on mobile networks/browsers.
            if (img.src.includes('ui-avatars.com')) {
                applyFallback();
                return;
            }

            img.addEventListener('error', applyFallback);

            if (img.complete && img.naturalWidth === 0) {
                applyFallback();
            }
        });
    };

    // Generate Stars
    const generateStars = (id, count) => {
        const container = document.getElementById(id);
        if (!container) return;

        let shadows = '';
        for (let i = 0; i < count; i++) {
            const x = Math.floor(Math.random() * window.innerWidth);
            const y = Math.floor(Math.random() * window.innerHeight);
            const c = Math.random() > 0.8 ? '#9d4edd' : '#ffffff';
            shadows += `${x}px ${y}px ${c}`;
            if (i < count - 1) shadows += ', ';
        }

        container.style.width = '2px';
        container.style.height = '2px';
        container.style.background = 'transparent';
        container.style.boxShadow = shadows;
    };

    generateStars('stars', 150);
    generateStars('stars2', 100);
    generateStars('stars3', 50);

    // Scroll Effects
    const header = document.getElementById('header');
    // Intersection Observer for Scroll Animations
    const observerOptions = {
        // 0 so that sections taller than the viewport (e.g. the team) still appear
        threshold: 0,
        rootMargin: '0px 0px -50px 0px'
    };

    const scrollAppearElements = document.querySelectorAll('.scroll-appear');
    const shouldBypassScrollAnimations = window.innerWidth <= 768 || !('IntersectionObserver' in window);

    if (shouldBypassScrollAnimations) {
        scrollAppearElements.forEach(el => el.classList.add('visible'));
    } else {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);

        scrollAppearElements.forEach(el => {
            observer.observe(el);
        });
    }

    document.documentElement.classList.add('js-started');

    const handleScroll = () => {
        if (window.scrollY > 50) {
            header.classList.add('scrolled');
        } else {
            header.classList.remove('scrolled');
        }

        // Active Nav Link Update
        let current = '';
        const sections = document.querySelectorAll('section');
        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            if (window.scrollY >= sectionTop - 200) {
                current = section.getAttribute('id');
            }
        });

        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === `#${current}`) {
                link.classList.add('active');
            }
        });
    };

    window.addEventListener('scroll', handleScroll);
    handleScroll(); // Trigger on load

    // Mobile Menu Toggle
    const menuBtn = document.getElementById('menu-btn');
    const nav = document.getElementById('navbar');

    const mobileQuery = window.matchMedia('(max-width: 768px)');
    const setMenu = (open, returnFocus = false) => {
        nav.classList.toggle('open', open);
        menuBtn.setAttribute('aria-expanded', String(open));
        nav.inert = mobileQuery.matches && !open;
        if (returnFocus) menuBtn.focus();
    };
    menuBtn.addEventListener('click', () => setMenu(!nav.classList.contains('open')));
    nav.addEventListener('click', e => {
        if (e.target.closest('.nav-link')) setMenu(false);
    });
    document.addEventListener('keydown', e => {
        if (e.key === 'Escape' && nav.classList.contains('open')) setMenu(false, true);
    });
    nav.addEventListener('focusout', e => {
        if (mobileQuery.matches && !nav.contains(e.relatedTarget)) setMenu(false);
    });
    mobileQuery.addEventListener('change', () => setMenu(false));
    setMenu(false);

    // Accessible tabs: arrows, Home and End move focus and activate the panel.
    document.querySelectorAll('.tabs-container').forEach(container => {
        const buttons = [...container.querySelectorAll('.tab-btn')];
        container.querySelector('.tabs-header').setAttribute('role', 'tablist');
        const activate = selected => buttons.forEach(btn => {
            const active = btn === selected;
            btn.classList.toggle('active', active);
            btn.setAttribute('aria-selected', String(active));
            btn.tabIndex = active ? 0 : -1;
            const panel = document.getElementById(btn.dataset.tab);
            panel.classList.toggle('active', active);
            panel.hidden = !active;
        });
        buttons.forEach((btn, index) => {
            const panel = document.getElementById(btn.dataset.tab);
            btn.id = 'tab-' + btn.dataset.tab;
            btn.setAttribute('role', 'tab');
            btn.setAttribute('aria-controls', panel.id);
            panel.setAttribute('role', 'tabpanel');
            panel.setAttribute('aria-labelledby', btn.id);
            btn.addEventListener('click', () => activate(btn));
            btn.addEventListener('keydown', e => {
                let next;
                if (e.key === 'ArrowRight') next = (index + 1) % buttons.length;
                if (e.key === 'ArrowLeft') next = (index + buttons.length - 1) % buttons.length;
                if (e.key === 'Home') next = 0;
                if (e.key === 'End') next = buttons.length - 1;
                if (next === undefined) return;
                e.preventDefault();
                activate(buttons[next]);
                buttons[next].focus();
            });
        });
        activate(buttons.find(btn => btn.classList.contains('active')) || buttons[0]);
    });

    // Team filtering
    const filterBtns = document.querySelectorAll('.filter-btn');
    const teamMembers = document.querySelectorAll('.team-member-card');

    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const filter = btn.getAttribute('data-filter');

            filterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            teamMembers.forEach(member => {
                if (filter === 'all') {
                    member.classList.remove('hidden');
                } else {
                    if (member.classList.contains(filter)) {
                        member.classList.remove('hidden');
                    } else {
                        member.classList.add('hidden');
                    }
                }
            });
        });
    });

    // Search and year are combined, including DOI URLs and accent-insensitive names.
    const pubYearFilter = document.getElementById('pub-year-filter');
    const pubSearch = document.getElementById('pub-search');
    const normalize = text => text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
    if (pubYearFilter && pubSearch) {
        const publications = [...document.querySelectorAll('#pub-list .pub-item')].map(item => ({
            item,
            text: normalize(item.textContent + ' ' + [...item.querySelectorAll('a[href]')].map(a => a.href).join(' '))
        }));
        const applyPublicationFilters = () => {
            const terms = normalize(pubSearch.value).trim().split(/\s+/).filter(Boolean);
            let count = 0;
            publications.forEach(({ item, text }) => {
                const matches = (pubYearFilter.value === 'all' || item.dataset.year === pubYearFilter.value)
                    && terms.every(term => text.includes(term));
                item.classList.toggle('hidden', !matches);
                item.hidden = !matches;
                if (matches) count++;
            });
            const isEn = document.body.classList.contains('lang-en');
            document.getElementById('pub-results').textContent = isEn
                ? `${count} of ${publications.length} publications`
                : `${count} de ${publications.length} publicaciones`;
            document.getElementById('pub-empty').hidden = count !== 0;
        };
        pubYearFilter.addEventListener('change', applyPublicationFilters);
        pubSearch.addEventListener('input', applyPublicationFilters);
        document.addEventListener('languagechange', applyPublicationFilters);
        applyPublicationFilters();
    }

    // Tesis Year and Dir Filters
    const tesisYearFilter = document.getElementById('tesis-year-filter');
    const tesisDirFilter = document.getElementById('tesis-dir-filter');
    const applyTesisFilters = () => {
        const y = tesisYearFilter ? tesisYearFilter.value : 'all';
        const d = tesisDirFilter ? tesisDirFilter.value : 'all';
        document.querySelectorAll('#tesis-list .tesis-item').forEach(item => {
            const matchesYear = (y === 'all' || item.getAttribute('data-year') === y);
            const dirEl = item.querySelector('.tesis-directors');
            const matchesDir = (d === 'all' || (dirEl && dirEl.textContent.replace(/\s+/g, ' ').includes(d)));
            item.classList.toggle('hidden', !(matchesYear && matchesDir));
        });
    };

    if (tesisYearFilter) tesisYearFilter.addEventListener('change', applyTesisFilters);
    if (tesisDirFilter) tesisDirFilter.addEventListener('change', applyTesisFilters);

    // Native buttons keep links in expanded cards independent and keyboard accessible.
    document.querySelectorAll('.research-card, .news-card.expandable').forEach((card, index) => {
        const panel = card.querySelector('.research-details, .expand-content');
        if (!panel) return;
        panel.id ||= 'card-details-' + index;
        const oldOpen = card.querySelector('.expand-btn-open');
        const oldClose = card.querySelector('.expand-btn-close');
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'card-toggle';
        button.setAttribute('aria-controls', panel.id);
        const setExpanded = expanded => {
            card.classList.toggle('expanded', expanded);
            button.setAttribute('aria-expanded', String(expanded));
            button.innerHTML = expanded
                ? '<span class="es">Mostrar menos ↑</span><span class="en">Show less ↑</span>'
                : '<span class="es">Ver más ↓</span><span class="en">Read more ↓</span>';
            panel.hidden = !expanded;
        };
        if (oldOpen) oldOpen.replaceWith(button);
        else panel.before(button);
        if (oldClose) oldClose.remove();
        button.addEventListener('click', () => setExpanded(!card.classList.contains('expanded')));
        setExpanded(false);
    });

    initTeamAvatars();

    // Play looping videos (former GIFs) only while visible, so they load on demand.
    // Includes the hero video in case the browser ignores its autoplay attribute.
    const lazyVideos = document.querySelectorAll('video[loop]');
    if ('IntersectionObserver' in window) {
        const videoObserver = new IntersectionObserver(entries => {
            entries.forEach(entry => {
                if (entry.isIntersecting) entry.target.play().catch(() => {});
                else entry.target.pause();
            });
        });
        lazyVideos.forEach(video => videoObserver.observe(video));
    } else {
        lazyVideos.forEach(video => video.play().catch(() => {}));
    }

    // Keep footer copyright year current without manual edits
    document.querySelectorAll('.footer-year').forEach(el => {
        el.textContent = new Date().getFullYear();
    });

    // Language Initialization. In the published site (scripts/build_site.py) each
    // language is its own page, so the page language wins over the saved one.
    const savedLang = isBuiltSite() ? document.documentElement.lang : readSavedLanguage();
    setLang(savedLang);
});

// True for pages generated by scripts/build_site.py (one URL per language)
function isBuiltSite() {
    return document.documentElement.hasAttribute('data-built');
}

// URL of the current page in the other language: /gosa/x.html <-> /gosa/en/x.html
function langUrl(lang) {
    const path = window.location.pathname;
    const inEn = /\/en\/[^/]*$/.test(path);
    let target = path;
    if (lang === 'en' && !inEn) target = path.replace(/([^/]*)$/, 'en/$1');
    if (lang === 'es' && inEn) target = path.replace(/\/en\/([^/]*)$/, '/$1');
    return target + window.location.hash;
}

function readSavedLanguage() {
    try { return localStorage.getItem('gosa_lang') === 'en' ? 'en' : 'es'; }
    catch { return 'es'; }
}

// Global Language Switcher
window.setLang = function (lang) {
    document.body.classList.remove('lang-es', 'lang-en');
    document.body.classList.add('lang-' + lang);
    document.documentElement.lang = lang;
    try { localStorage.setItem('gosa_lang', lang); } catch { /* Storage may be disabled. */ }

    document.querySelectorAll('.lang-toggle-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    const activeBtn = document.getElementById('btn-' + lang);
    if (activeBtn) activeBtn.classList.add('active');

    // Update placeholder text in form inputs/textareas
    document.querySelectorAll('[data-es-placeholder]').forEach(el => {
        el.placeholder = lang === 'es' ? el.getAttribute('data-es-placeholder') : el.getAttribute('data-en-placeholder');
    });
    document.dispatchEvent(new Event('languagechange'));
};

// Delegated handlers (replace inline onclick so the CSP can forbid inline scripts)
document.addEventListener('click', (e) => {
    const langBtn = e.target.closest('[data-lang]');
    if (langBtn) {
        const lang = langBtn.dataset.lang;
        if (!isBuiltSite()) window.setLang(lang);
        else if (lang !== document.documentElement.lang) window.location.href = langUrl(lang);
        return;
    }
});
