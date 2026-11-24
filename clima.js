// Monitor de clima espacial en tiempo real (clima-espacial.html#tiempo-real).
// Adaptado, con permiso, del monitor de Santiago Vargas Domínguez
// (https://astronomiaoan.co/santiagovargas/climaespacial · github.com/AstronomiaOAN/santiagovargas).
// Datos abiertos: NOAA SWPC (JSON con CORS) e imágenes NASA SDO y ESA/NASA SOHO.
(() => {
    'use strict';
    const root = document.getElementById('tiempo-real');
    if (!root) return;

    const BASE = 'https://services.swpc.noaa.gov/';
    const REFRESH_MS = 5 * 60 * 1000;
    const $ = (id) => document.getElementById(id);
    const both = (es, en) => `<span class="es">${es}</span><span class="en">${en}</span>`;
    const SVG_NS = 'http://www.w3.org/2000/svg';

    async function get(path) {
        const response = await fetch(BASE + path, { cache: 'no-store' });
        if (!response.ok) throw new Error(path + ' ' + response.status);
        return response.json();
    }

    // [{t: ms, v: number}] ordenado por tiempo, a partir de filas NOAA.
    function series(rows, key, keep = () => true) {
        return rows
            .filter((r) => keep(r) && r[key] !== null && r[key] !== '' && Number.isFinite(Number(r[key])))
            .map((r) => ({ t: Date.parse(r.time_tag.endsWith('Z') ? r.time_tag : r.time_tag + 'Z'), v: Number(r[key]) }))
            .filter((p) => Number.isFinite(p.t))
            .sort((a, b) => a.t - b.t);
    }

    function utcLabel(ms) {
        const d = new Date(ms);
        const pad = (n) => String(n).padStart(2, '0');
        return `${pad(d.getUTCDate())}/${pad(d.getUTCMonth() + 1)} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())} UTC`;
    }

    // Mini gráfica SVG (línea o barras), escala log opcional.
    function sparkline(id, points, { log = false, bars = false, range = null, zero = false } = {}) {
        const box = $(id);
        if (!box) return;
        box.textContent = '';
        if (points.length < 2) return;
        const W = 300, H = 70, P = 4;
        const val = (v) => (log ? Math.log10(Math.max(v, 1e-9)) : v);
        const vs = points.map((p) => val(p.v));
        let lo = range ? range[0] : Math.min(...vs);
        let hi = range ? range[1] : Math.max(...vs);
        if (zero) { lo = Math.min(lo, 0); hi = Math.max(hi, 0); }
        if (hi === lo) { hi += 1; lo -= 1; }
        const t0 = points[0].t, t1 = points[points.length - 1].t || t0 + 1;
        const x = (t) => P + ((t - t0) / (t1 - t0 || 1)) * (W - 2 * P);
        const y = (v) => H - P - ((v - lo) / (hi - lo)) * (H - 2 * P);
        const svg = document.createElementNS(SVG_NS, 'svg');
        svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
        svg.setAttribute('preserveAspectRatio', 'none');
        svg.setAttribute('aria-hidden', 'true');
        if (zero) {
            const axis = document.createElementNS(SVG_NS, 'line');
            axis.setAttribute('x1', P); axis.setAttribute('x2', W - P);
            axis.setAttribute('y1', y(0)); axis.setAttribute('y2', y(0));
            axis.setAttribute('class', 'sw-axis');
            svg.appendChild(axis);
        }
        if (bars) {
            const w = Math.max(2, (W - 2 * P) / points.length - 1);
            points.forEach((p, i) => {
                const r = document.createElementNS(SVG_NS, 'rect');
                const top = y(val(p.v));
                r.setAttribute('x', P + i * ((W - 2 * P) / points.length));
                r.setAttribute('y', top);
                r.setAttribute('width', w);
                r.setAttribute('height', Math.max(1, H - P - top));
                r.setAttribute('class', p.v >= 5 ? 'sw-bar sw-bar-storm' : p.v >= 4 ? 'sw-bar sw-bar-active' : 'sw-bar');
                svg.appendChild(r);
            });
        } else {
            // Reducir a ~300 puntos para que el trazo sea liviano.
            const step = Math.max(1, Math.floor(points.length / 300));
            const d = points
                .filter((_, i) => i % step === 0 || i === points.length - 1)
                .map((p, i) => `${i ? 'L' : 'M'}${x(p.t).toFixed(1)},${y(val(p.v)).toFixed(1)}`)
                .join('');
            const path = document.createElementNS(SVG_NS, 'path');
            path.setAttribute('d', d);
            path.setAttribute('class', 'sw-line');
            path.setAttribute('vector-effect', 'non-scaling-stroke');
            svg.appendChild(path);
        }
        box.appendChild(svg);
    }

    function setLevel(id, level) {
        const el = $(id);
        if (!el) return;
        el.classList.remove('sw-level-0', 'sw-level-1', 'sw-level-2', 'sw-level-3');
        el.classList.add('sw-level-' + level);
    }

    const SCALE_TEXT = [
        ['Sin evento', 'None'], ['Menor', 'Minor'], ['Moderada', 'Moderate'],
        ['Fuerte', 'Strong'], ['Severa', 'Severe'], ['Extrema', 'Extreme'],
    ];

    const jobs = [
        async () => {
            const now = (await get('products/noaa-scales.json'))['0'];
            for (const k of ['R', 'S', 'G']) {
                const v = Number(now[k].Scale);
                if (!Number.isFinite(v)) throw new Error('scale ' + k);
                $('sw-' + k).textContent = k + v;
                $('sw-' + k + '-text').innerHTML = both(...SCALE_TEXT[v]);
                setLevel('sw-' + k + '-card', v === 0 ? 0 : v <= 2 ? 1 : v <= 3 ? 2 : 3);
            }
        },
        async () => {
            const d = series(await get('json/goes/primary/xrays-1-day.json'), 'flux', (r) => r.energy === '0.1-0.8nm' && Number(r.flux) > 0);
            const last = d.at(-1);
            if (!last) throw new Error('xrays');
            const classes = [['X', 1e-4], ['M', 1e-5], ['C', 1e-6], ['B', 1e-7], ['A', 1e-8]];
            const [letter, base] = classes.find(([, b]) => last.v >= b) || ['A', 1e-8];
            $('sw-xray').textContent = letter + (last.v / base).toFixed(1);
            $('sw-xray-time').textContent = utcLabel(last.t);
            setLevel('sw-xray-card', letter === 'X' ? 3 : letter === 'M' ? 2 : letter === 'C' ? 1 : 0);
            sparkline('sw-xray-chart', d, { log: true, range: [-8.5, -3.5] });
        },
        async () => {
            const rows = (await get('json/rtsw/rtsw_wind_1m.json')).filter((r) => r.active === true);
            const d = series(rows, 'proton_speed', (r) => Number(r.proton_speed) > 0);
            const last = d.at(-1);
            if (!last) throw new Error('wind');
            const dens = series(rows, 'proton_density', (r) => Number(r.proton_density) > 0).at(-1);
            $('sw-wind').textContent = last.v.toFixed(0);
            $('sw-dens').textContent = dens ? dens.v.toFixed(1) : '—';
            $('sw-wind-time').textContent = utcLabel(last.t);
            setLevel('sw-wind-card', last.v >= 700 ? 3 : last.v >= 600 ? 2 : last.v >= 500 ? 1 : 0);
            sparkline('sw-wind-chart', d);
        },
        async () => {
            const d = series(await get('json/rtsw/rtsw_mag_1m.json'), 'bz_gsm', (r) => r.active === true && Math.abs(Number(r.bz_gsm)) < 1000);
            const last = d.at(-1);
            if (!last) throw new Error('bz');
            $('sw-bz').textContent = (last.v > 0 ? '+' : '') + last.v.toFixed(1);
            $('sw-bz-time').textContent = utcLabel(last.t);
            setLevel('sw-bz-card', last.v <= -20 ? 3 : last.v <= -10 ? 2 : last.v <= -5 ? 1 : 0);
            sparkline('sw-bz-chart', d, { zero: true });
        },
        async () => {
            const d = series(await get('products/noaa-planetary-k-index.json'), 'Kp');
            const last = d.at(-1);
            if (!last) throw new Error('kp');
            $('sw-kp').textContent = last.v.toFixed(1);
            $('sw-kp-text').innerHTML = last.v >= 5
                ? both('Tormenta geomagnética', 'Geomagnetic storm')
                : last.v >= 4 ? both('Campo activo', 'Active field') : both('Campo tranquilo', 'Quiet field');
            $('sw-kp-time').textContent = utcLabel(last.t);
            setLevel('sw-kp-card', last.v >= 7 ? 3 : last.v >= 5 ? 2 : last.v >= 4 ? 1 : 0);
            sparkline('sw-kp-chart', d.slice(-24), { bars: true, range: [0, 9] });
        },
    ];

    let busy = false;
    async function update() {
        if (busy) return;
        busy = true;
        const button = $('sw-refresh');
        const status = $('sw-status');
        button.disabled = true;
        status.innerHTML = both('Consultando NOAA…', 'Querying NOAA…');
        const results = await Promise.allSettled(jobs.map((job) => job()));
        const failed = results.filter((r) => r.status === 'rejected').length;
        const stamp = utcLabel(Date.now());
        status.innerHTML = failed
            ? both(`Actualizado ${stamp} · ${failed} fuente(s) sin respuesta`, `Updated ${stamp} · ${failed} source(s) not responding`)
            : both(`Actualizado ${stamp}`, `Updated ${stamp}`);
        // Refrescar imágenes (las URLs "latest" cambian de contenido, no de nombre).
        const bust = '?t=' + Math.floor(Date.now() / REFRESH_MS);
        const sun = $('sw-sun');
        sun.src = sun.dataset.base + bust;
        const c2 = $('sw-c2');
        c2.src = c2.dataset.base + bust;
        button.disabled = false;
        busy = false;
    }

    // Selector de canal SDO.
    root.querySelectorAll('[data-channel]').forEach((btn) => {
        btn.addEventListener('click', () => {
            root.querySelectorAll('[data-channel]').forEach((b) => b.setAttribute('aria-pressed', String(b === btn)));
            const sun = $('sw-sun');
            sun.dataset.base = `https://sdo.gsfc.nasa.gov/assets/img/latest/latest_1024_${btn.dataset.channel}.jpg`;
            sun.src = sun.dataset.base + '?t=' + Math.floor(Date.now() / REFRESH_MS);
            root.querySelectorAll('[data-channel-note]').forEach((n) => { n.hidden = n.dataset.channelNote !== btn.dataset.channel; });
        });
    });

    $('sw-refresh').addEventListener('click', update);

    // Cargar sólo cuando la sección se acerca a la vista; refrescar cada 5 min mientras la pestaña esté visible.
    let started = false;
    const start = () => {
        if (started) return;
        started = true;
        update();
        setInterval(() => { if (!document.hidden) update(); }, REFRESH_MS);
    };
    if ('IntersectionObserver' in window) {
        const io = new IntersectionObserver((entries) => {
            if (entries.some((e) => e.isIntersecting)) { io.disconnect(); start(); }
        }, { rootMargin: '400px' });
        io.observe(root);
    } else {
        start();
    }
})();
