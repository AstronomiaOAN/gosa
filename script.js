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
        threshold: 0.1,
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

    menuBtn.addEventListener('click', () => {
        nav.classList.toggle('open');
    });

    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', () => {
            if (nav.classList.contains('open')) {
                nav.classList.remove('open');
            }
        });
    });

    // Tab Switching
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const target = btn.getAttribute('data-tab');

            // Remove active class from all
            tabBtns.forEach(b => b.classList.remove('active'));
            tabPanes.forEach(p => p.classList.remove('active'));

            // Add active class to target
            btn.classList.add('active');
            document.getElementById(target).classList.add('active');
        });
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

    // Publications Year Filter
    const pubYearFilter = document.getElementById('pub-year-filter');
    if (pubYearFilter) {
        pubYearFilter.addEventListener('change', (e) => {
            const y = e.target.value;
            document.querySelectorAll('#pub-list .pub-item').forEach(item => {
                const matchesYear = (y === 'all' || item.getAttribute('data-year') === y);
                item.classList.toggle('hidden', !matchesYear);
            });
        });
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

    // Expandable Cards Logic (Research & News)
    const initExpandableCards = () => {
        // News cards expansion
        document.querySelectorAll('.news-card.expandable').forEach(card => {
            card.addEventListener('click', (e) => {
                // Toggle expansion
                card.classList.toggle('expanded');
            });
        });
    };

    initExpandableCards();
    initTeamAvatars();

    // Keep footer copyright year current without manual edits
    document.querySelectorAll('.footer-year').forEach(el => {
        el.textContent = new Date().getFullYear();
    });

    // Language Initialization
    const savedLang = localStorage.getItem('gosa_lang') || 'es';
    setLang(savedLang);
});

// Global Language Switcher
window.setLang = function (lang) {
    document.body.classList.remove('lang-es', 'lang-en');
    document.body.classList.add('lang-' + lang);
    localStorage.setItem('gosa_lang', lang);

    document.querySelectorAll('.lang-toggle-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    const activeBtn = document.getElementById('btn-' + lang);
    if (activeBtn) activeBtn.classList.add('active');

    // Update placeholder text in form inputs/textareas
    document.querySelectorAll('[data-es-placeholder]').forEach(el => {
        el.placeholder = lang === 'es' ? el.getAttribute('data-es-placeholder') : el.getAttribute('data-en-placeholder');
    });
};
