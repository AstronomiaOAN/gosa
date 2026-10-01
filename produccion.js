// Infografía de producción: cifras y gráfico calculados desde #pub-list.
(function () {
    const items = [...document.querySelectorAll('#pub-list .pub-item')];
    if (!items.length) return;
    const counts = {};
    items.forEach(li => {
        const y = +li.dataset.year;
        counts[y] = (counts[y] || 0) + 1;
    });
    const years = Object.keys(counts).map(Number);
    const first = Math.min(...years), last = Math.max(...years);
    const series = [];
    for (let y = first; y <= last; y++) series.push({ year: y, n: counts[y] || 0 });
    const peak = series.reduce((a, b) => (b.n > a.n ? b : a));
    const current = new Date().getFullYear();
    const both = (es, en) => `<span class="es">${es}</span><span class="en">${en}</span>`;

    document.getElementById('info-total').textContent = items.length;
    document.getElementById('info-period').innerHTML = `${first}<span class="dash">–</span>${last}`;
    document.getElementById('info-period-sub').innerHTML =
        both(`${series.length} años calendario`, `${series.length} calendar years`);
    document.getElementById('info-last').textContent = counts[last];
    document.getElementById('info-last-lbl').innerHTML =
        both(`contribuciones en ${last}`, `contributions in ${last}`);
    document.getElementById('info-last-sub').innerHTML = last === current
        ? both('Año en curso · cifra parcial', 'Current year · partial count')
        : both('Último año del listado', 'Latest year listed');

    // Escala: múltiplo de 10 por encima del máximo.
    const max = Math.max(10, Math.ceil(peak.n / 10) * 10);
    const chart = document.getElementById('info-chart');
    for (let v = 0; v <= max; v += 10) {
        const line = document.createElement('div');
        line.className = 'info-grid-line';
        line.style.bottom = `${(v / max) * 100}%`;
        line.innerHTML = `<span>${v}</span>`;
        chart.insertBefore(line, chart.firstChild);
    }

    const bars = document.getElementById('info-bars');
    const labels = document.getElementById('info-years');
    const tip = document.getElementById('info-tooltip');
    const isEn = () => document.body.classList.contains('lang-en');
    series.forEach(({ year, n }) => {
        const b = document.createElement('button');
        b.type = 'button';
        b.className = 'info-bar' + (year === peak.year || year === last ? ' is-hl' : '');
        b.setAttribute('aria-label', `${year}: ${n}`);
        b.innerHTML = `<span class="val">${n || ''}</span>` +
            `<span class="fill" style="height:${(n / max) * 100}%"></span>`;
        const show = () => {
            tip.textContent = isEn()
                ? `${year} · ${n} ${n === 1 ? 'publication' : 'publications'} · click to filter`
                : `${year} · ${n} ${n === 1 ? 'publicación' : 'publicaciones'} · clic para filtrar`;
            const r = b.getBoundingClientRect(), c = chart.getBoundingClientRect();
            const fill = b.querySelector('.fill').getBoundingClientRect();
            const half = tip.offsetWidth / 2;
            const x = r.left - c.left + r.width / 2;
            tip.style.left = `${Math.min(Math.max(x, half - 26), c.width - half)}px`;
            tip.style.top = `${Math.min(fill.top, r.bottom - 20) - c.top - 24}px`;
            tip.classList.add('show');
        };
        const hide = () => tip.classList.remove('show');
        b.addEventListener('mouseenter', show);
        b.addEventListener('focus', show);
        b.addEventListener('mouseleave', hide);
        b.addEventListener('blur', hide);
        b.addEventListener('click', () => {
            const select = document.getElementById('pub-year-filter');
            const tab = document.querySelector('.tab-btn[data-tab="pubs"]');
            if (tab && !tab.classList.contains('active')) tab.click();
            if (select) {
                select.value = String(year);
                select.dispatchEvent(new Event('change'));
            }
            document.getElementById('pubs').scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
        bars.appendChild(b);
        labels.insertAdjacentHTML('beforeend',
            `<span><span class="full">${year}</span><span class="short">'${String(year).slice(2)}</span></span>`);
    });

    document.getElementById('info-callout').innerHTML =
        `<strong>${peak.year}</strong>` +
        both(`${peak.n} contribuciones, el mayor total anual del periodo.`,
            `${peak.n} contributions, the highest yearly total in the period.`);
})();
