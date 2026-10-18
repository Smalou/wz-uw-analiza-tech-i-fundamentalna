// Wspólne narzędzia: formaty, osie, tooltip, stany ładowania.
window.W = (() => {
  const L = d3.formatLocale({ decimal: ',', thousands: ' ', grouping: [3], currency: ['', ''] });
  const TL = d3.timeFormatLocale({
    dateTime: '%A, %e %B %Y, %X', date: '%d.%m.%Y', time: '%H:%M:%S', periods: ['', ''],
    days: ['niedziela', 'poniedziałek', 'wtorek', 'środa', 'czwartek', 'piątek', 'sobota'],
    shortDays: ['nd', 'pn', 'wt', 'śr', 'cz', 'pt', 'so'],
    months: ['styczeń', 'luty', 'marzec', 'kwiecień', 'maj', 'czerwiec', 'lipiec', 'sierpień', 'wrzesień', 'październik', 'listopad', 'grudzień'],
    shortMonths: ['sty', 'lut', 'mar', 'kwi', 'maj', 'cze', 'lip', 'sie', 'wrz', 'paź', 'lis', 'gru'],
  });
  const minus = (s) => s.replace(/^-/, '−');
  const f = {
    pct3: (v) => minus(L.format('.3%')(v)),
    pct2: (v) => minus(L.format('.2%')(v)),
    pct1: (v) => minus(L.format('.1%')(v)),
    pct0: (v) => minus(L.format('.0%')(v)),
    spct3: (v) => minus(L.format('+.3%')(v)),
    spct2: (v) => minus(L.format('+.2%')(v)),
    spct1: (v) => minus(L.format('+.1%')(v)),
    num1: (v) => minus(L.format(',.1f')(v)),
    num2: (v) => minus(L.format(',.2f')(v)),
    num3: (v) => minus(L.format(',.3f')(v)),
    num4: (v) => minus(L.format(',.4f')(v)),
    snum2: (v) => minus(L.format('+.2f')(v)),
    int: (v) => L.format(',d')(Math.round(v)),
    p: (v) => (v == null || Number.isNaN(v) ? '—' : v < 0.0001 ? '<0,0001' : L.format('.4f')(v)),
    day: TL.utcFormat('%-d %b %Y'),
    dayLong: TL.utcFormat('%A, %-d %B %Y'),
    month: TL.utcFormat('%b %Y'),
    tick: (d) => (d.getUTCMonth() === 0 && d.getUTCDate() === 1 ? TL.utcFormat('%Y')(d) : d.getUTCDate() === 1 ? TL.utcFormat('%b')(d) : TL.utcFormat('%-d %b')(d)),
    year: TL.utcFormat('%Y'),
    quarter: (d) => `${d.getUTCFullYear()} Q${Math.floor(d.getUTCMonth() / 3) + 1}`,
  };
  const date = (s) => new Date(String(s).slice(0, 10) + 'T00:00:00Z');
  const num = (v) => (v == null || v === '' ? null : Number(v));

  const SECTORS = ['BANKI', 'BUDOWNICTWO', 'SPOZYWCZY', 'ENERGIA', 'LEKI'];
  const SECTOR_NAME = { BANKI: 'Banki', BUDOWNICTWO: 'Budownictwo', SPOZYWCZY: 'Spożywczy', ENERGIA: 'Energia', LEKI: 'Leki' };
  const MACRO_NAME = { GDP_growth: 'PKB kw/kw', Inflation_YoY: 'Inflacja r/r', Unemployment: 'Bezrobocie' };
  const PHASES = ['Spadek', 'Ożywienie', 'Ekspansja', 'Spowolnienie'];
  const label = (k) => SECTOR_NAME[k] || MACRO_NAME[k] || k;
  const sectorColor = (k) => dash.colors[SECTORS.indexOf(k)];
  const phaseColor = (p) => ({
    Spadek: 'var(--cds-chart-status-critical)',
    'Ożywienie': dash.colors[5],
    Ekspansja: dash.colors[6],
    Spowolnienie: 'var(--cds-chart-muted)',
  })[p] || 'var(--cds-chart-muted)';
  const DIVERGING = [1, 2, 3, 4, 5, 6, 7].map((i) => `var(--cds-chart-diverging-${i})`);
  const SEQUENTIAL = [1, 2, 3, 4, 5, 6, 7].map((i) => `var(--cds-chart-sequential-${i})`);

  // Stan źródeł: zwraca dane albo rysuje szkielet / błąd.
  function gate(box, ids) {
    const sel = d3.select(box);
    sel.selectAll('svg, .w-fail').remove();
    const st = ids.map((id) => dash.data(id));
    if (st.every((d) => d.status === 'ok')) {
      box.classList.remove('dash-skeleton');
      return st.map((d) => d.data);
    }
    if (st.some((d) => d.status !== 'loading')) {
      box.classList.remove('dash-skeleton');
      const fail = document.createElement('div');
      fail.className = 'w-fail';
      fail.append(document.createElement('i'), 'Nie udało się wczytać');
      box.prepend(fail);
      return null;
    }
    box.classList.add('dash-skeleton');
    return null;
  }

  function svgIn(box, h) {
    const w = Math.max(box.clientWidth, 260);
    const svg = d3.select(box).insert('svg', ':first-child')
      .attr('class', 'w-svg').attr('width', '100%').attr('height', h).attr('viewBox', `0 0 ${w} ${h}`);
    return { svg, w, h };
  }

  function textW(svg, strings, cls = 'w-tick') {
    const t = svg.append('text').attr('class', cls);
    let m = 0;
    for (const s of strings) { t.text(s); m = Math.max(m, t.node().getComputedTextLength()); }
    t.remove();
    return m;
  }

  function axisY(g, y, fmt, width, ticks = 5) {
    g.call(d3.axisLeft(y).ticks(ticks).tickFormat(fmt).tickSize(-width).tickPadding(8))
      .attr('font-size', null).attr('font-family', null);
    g.select('.domain').remove();
    g.selectAll('.tick line').attr('class', 'w-grid');
    g.selectAll('.tick text').attr('class', 'w-tick');
  }

  function axisX(g, x, fmt, ticks) {
    const a = d3.axisBottom(x).tickSizeOuter(0).tickSize(4).tickPadding(6);
    if (fmt) a.tickFormat(fmt);
    if (ticks != null && x.ticks) a.ticks(ticks);
    g.call(a).attr('font-size', null).attr('font-family', null);
    g.select('.domain').attr('class', 'w-axis');
    g.selectAll('.tick line').attr('class', 'w-axis');
    g.selectAll('.tick text').attr('class', 'w-tick');
  }

  function tooltip(box) {
    let t = box.querySelector(':scope > .w-tip');
    if (!t) {
      t = document.createElement('div');
      t.className = 'w-tip';
      t.hidden = true;
      box.appendChild(t);
    }
    return {
      show(lines, x, y) {
        t.replaceChildren(...lines.map((l) => {
          const row = document.createElement('div');
          row.className = l.head ? 'w-tip-head' : 'w-tip-row';
          if (l.color) {
            const s = document.createElement('span');
            s.className = 'w-sw' + (l.ring ? ' w-ring' : '');
            s.style.background = l.color;
            row.appendChild(s);
          }
          const a = document.createElement('span');
          a.textContent = l.label ?? '';
          row.appendChild(a);
          if (l.value != null) {
            const b = document.createElement('b');
            b.textContent = l.value;
            row.appendChild(b);
          }
          return row;
        }));
        t.hidden = false;
        const bw = box.clientWidth, tw = t.offsetWidth, th = t.offsetHeight;
        let left = x + 14;
        if (left + tw > bw) left = x - 14 - tw;
        if (left < 0) left = Math.max(0, Math.min(bw - tw, x - tw / 2));
        let top = y - th - 12;
        if (top < 0) top = y + 16;
        t.style.left = left + 'px';
        t.style.top = top + 'px';
      },
      hide() { t.hidden = true; },
    };
  }

  // Rozsuwa etykiety końcowe, by się nie nakładały.
  function dodge(items, gap, lo, hi) {
    items.sort((a, b) => a.y - b.y);
    for (let i = 1; i < items.length; i++) items[i].y = Math.max(items[i].y, items[i - 1].y + gap);
    const over = items.length ? items[items.length - 1].y - hi : 0;
    if (over > 0) for (const it of items) it.y -= over;
    for (let i = items.length - 2; i >= 0; i--) items[i].y = Math.min(items[i].y, items[i + 1].y - gap);
    for (const it of items) it.y = Math.max(it.y, lo);
    return items;
  }

  // Wykres liniowy z linią pionową i tooltipem; series: [{key, name, color, values: [{x: Date, y, ...}]}]
  function lineChart(box, o) {
    const { series, height = 300, yFmt, tipFmt = yFmt, xTipFmt = f.day, refs = [], area = false, strokeWidth = 2, endLabels = true, extraTip, yDomain } = o;
    const { svg, w, h } = svgIn(box, height);
    const all = series.flatMap((s) => s.values);
    if (!all.length) return;
    let yd = yDomain || d3.extent([...all.map((d) => d.y), ...refs.map((r) => r.y)]);
    const y = d3.scaleLinear(yd, [h - 26, 10]).nice();
    const ml = textW(svg, y.ticks(5).map(yFmt)) + 10;
    const endText = (s) => `${s.name} ${yFmt(s.values[s.values.length - 1].y)}`;
    const mr = endLabels ? textW(svg, series.map(endText), 'w-lbl') + 16 : 10;
    const x = d3.scaleUtc(d3.extent(all, (d) => d.x), [ml, w - mr]);
    axisY(svg.append('g').attr('transform', `translate(${ml},0)`), y, yFmt, w - ml - mr);
    const xTicks = Math.max(2, Math.floor((w - ml - mr) / 90));
    axisX(svg.append('g').attr('transform', `translate(0,${h - 26})`), x, f.tick, xTicks);
    for (const r of refs) {
      svg.append('line').attr('class', r.zero ? 'w-zero' : 'w-ref').attr('x1', ml).attr('x2', w - mr).attr('y1', y(r.y)).attr('y2', y(r.y));
      if (r.label) svg.append('text').attr('class', 'w-lbl-muted').attr('x', ml + 4).attr('y', y(r.y) - 4).text(r.label);
    }
    const line = d3.line().defined((d) => d.y != null).x((d) => x(d.x)).y((d) => y(d.y));
    if (area && series.length === 1) {
      const id = 'g' + Math.random().toString(36).slice(2);
      const grad = svg.append('defs').append('linearGradient').attr('id', id).attr('x1', 0).attr('x2', 0).attr('y1', 0).attr('y2', 1);
      [[0, .26], [.25, .16], [.5, .08], [.75, .03], [1, 0]].forEach(([o2, a]) => grad.append('stop').attr('offset', o2).attr('style', `stop-color:${series[0].color};stop-opacity:${a}`));
      svg.append('path').attr('fill', `url(#${id})`)
        .attr('d', d3.area().defined((d) => d.y != null).x((d) => x(d.x)).y0(h - 26).y1((d) => y(d.y))(series[0].values));
    }
    for (const s of series) {
      svg.append('path').attr('fill', 'none').attr('stroke', s.color).attr('stroke-width', strokeWidth)
        .attr('stroke-linejoin', 'round').attr('stroke-linecap', 'round').attr('d', line(s.values));
    }
    if (endLabels) {
      const items = dodge(series.map((s) => ({ s, y: y(s.values[s.values.length - 1].y) })), 15, 10, h - 30);
      for (const it of items) {
        const last = it.s.values[it.s.values.length - 1];
        svg.append('circle').attr('cx', x(last.x)).attr('cy', y(last.y)).attr('r', 3.5).attr('fill', it.s.color).attr('stroke', 'var(--color-panel)').attr('stroke-width', 2);
        svg.append('text').attr('class', 'w-lbl').attr('x', x(last.x) + 8).attr('y', it.y).attr('dy', '0.32em').text(endText(it.s));
      }
    }
    // Hover
    const tip = tooltip(box);
    const rule = svg.append('line').attr('class', 'w-rule').attr('y1', 10).attr('y2', h - 26).style('display', 'none');
    const dots = svg.append('g').style('display', 'none');
    const bis = d3.bisector((d) => d.x).center;
    svg.append('rect').attr('x', ml).attr('y', 0).attr('width', Math.max(0, w - ml - mr)).attr('height', h).attr('fill', 'transparent')
      .on('pointermove', (ev) => {
        const [mx] = d3.pointer(ev);
        const t0 = x.invert(mx);
        const pts = series.map((s) => ({ s, d: s.values[bis(s.values, t0)] })).filter((p) => p.d && p.d.y != null);
        if (!pts.length) return;
        const xd = pts[0].d.x;
        rule.attr('x1', x(xd)).attr('x2', x(xd)).style('display', null);
        dots.style('display', null).selectAll('circle').data(pts).join('circle')
          .attr('cx', (p) => x(p.d.x)).attr('cy', (p) => y(p.d.y)).attr('r', 4).attr('fill', (p) => p.s.color)
          .attr('stroke', 'var(--color-panel)').attr('stroke-width', 2);
        const lines = [{ head: true, label: xTipFmt(xd) }];
        [...pts].sort((a, b) => b.d.y - a.d.y).forEach((p) => lines.push({ color: series.length > 1 ? p.s.color : null, label: p.s.name, value: tipFmt(p.d.y) }));
        if (extraTip) lines.push(...extraTip(pts));
        const [px, py] = d3.pointer(ev, box);
        tip.show(lines, px, py);
      })
      .on('pointerleave', () => { rule.style('display', 'none'); dots.style('display', 'none'); tip.hide(); });
  }

  // Wykres słupkowy pionowy z wąsami; items: [{key, label, value, lo?, hi?, color, tip: [...]}]
  function barChart(box, o) {
    const { items, height = 280, yFmt, labelFmt = yFmt } = o;
    const { svg, w, h } = svgIn(box, height);
    const vals = items.flatMap((d) => [d.value, d.lo ?? d.value, d.hi ?? d.value, 0]);
    const y = d3.scaleLinear(d3.extent(vals), [h - 28, 18]).nice();
    const ml = textW(svg, y.ticks(5).map(yFmt)) + 10;
    const x = d3.scaleBand(items.map((d) => d.key), [ml, w - 6]).padding(0.3);
    axisY(svg.append('g').attr('transform', `translate(${ml},0)`), y, yFmt, w - ml - 6);
    const xa = svg.append('g').attr('transform', `translate(0,${h - 28})`);
    axisX(xa, x, (k) => items.find((d) => d.key === k).label);
    xa.selectAll('.tick line').remove();
    if (x.bandwidth() < 40) xa.selectAll('.tick text').text((k) => items.find((d) => d.key === k).short || items.find((d) => d.key === k).label);
    svg.append('line').attr('class', 'w-zero').attr('x1', ml).attr('x2', w - 6).attr('y1', y(0)).attr('y2', y(0));
    const bw = Math.min(x.bandwidth(), 40);
    const g = svg.append('g');
    const tip = tooltip(box);
    items.forEach((d) => {
      const cx = x(d.key) + x.bandwidth() / 2;
      const y0 = y(0), y1 = y(d.value);
      g.append('rect').attr('x', cx - bw / 2).attr('width', bw).attr('y', Math.min(y0, y1)).attr('height', Math.max(1, Math.abs(y1 - y0)))
        .attr('rx', 4).attr('fill', d.color);
      if (d.lo != null) {
        g.append('line').attr('class', 'w-rule').attr('x1', cx).attr('x2', cx).attr('y1', y(d.lo)).attr('y2', y(d.hi)).attr('stroke', 'var(--color-fg)');
        [d.lo, d.hi].forEach((v) => g.append('line').attr('class', 'w-rule').attr('x1', cx - 5).attr('x2', cx + 5).attr('y1', y(v)).attr('y2', y(v)).attr('stroke', 'var(--color-fg)'));
      }
      if (x.bandwidth() >= 34) {
        const top = d.value >= 0 ? y(Math.max(d.value, d.hi ?? d.value)) - 5 : y(Math.min(d.value, d.lo ?? d.value)) + 13;
        g.append('text').attr('class', 'w-lbl-muted').attr('text-anchor', 'middle').attr('x', cx).attr('y', top).text(labelFmt(d.value));
      }
      g.append('rect').attr('x', x(d.key)).attr('width', x.bandwidth()).attr('y', 0).attr('height', h - 28).attr('fill', 'transparent')
        .on('pointermove', (ev) => { const [px, py] = d3.pointer(ev, box); tip.show(d.tip, px, py); })
        .on('pointerleave', () => tip.hide());
    });
  }

  // Mapa ciepła; cells: [{r, c, v, text, tip}]
  function heatmap(box, o) {
    const { rows, cols, cells, color, rowLabel = (d) => d, colLabel = (d) => d, cellH = 40 } = o;
    const { svg, w } = svgIn(box, 100);
    const mlNeed = textW(svg, rows.map(rowLabel)) + 12;
    const cw = (w - mlNeed) / cols.length;
    const rotate = cw < textW(svg, cols.map(colLabel)) + 8;
    const top = rotate ? 70 : 24;
    const H = top + rows.length * cellH + 4;
    svg.attr('height', H).attr('viewBox', `0 0 ${w} ${H}`);
    const x = d3.scaleBand(cols, [mlNeed, w]).padding(0.04);
    const y = d3.scaleBand(rows, [top, top + rows.length * cellH]).padding(0.06);
    rows.forEach((r) => svg.append('text').attr('class', 'w-tick').attr('x', mlNeed - 8).attr('y', y(r) + y.bandwidth() / 2).attr('dy', '0.32em').attr('text-anchor', 'end').text(rowLabel(r)));
    cols.forEach((c) => {
      const t = svg.append('text').attr('class', 'w-tick');
      if (rotate) t.attr('transform', `translate(${x(c) + x.bandwidth() / 2},${top - 6}) rotate(-40)`).text(colLabel(c));
      else t.attr('x', x(c) + x.bandwidth() / 2).attr('y', top - 8).attr('text-anchor', 'middle').text(colLabel(c));
    });
    const tip = tooltip(box);
    for (const d of cells) {
      const g = svg.append('g');
      g.append('rect').attr('x', x(d.c)).attr('y', y(d.r)).attr('width', x.bandwidth()).attr('height', y.bandwidth())
        .attr('rx', 4).attr('fill', d.v == null ? 'var(--cds-chart-reference-tint)' : color(d.v));
      if (x.bandwidth() > 34) g.append('text').attr('class', 'w-cell-lbl').attr('text-anchor', 'middle')
        .attr('x', x(d.c) + x.bandwidth() / 2).attr('y', y(d.r) + y.bandwidth() / 2).attr('dy', '0.32em').text(d.text);
      g.on('pointermove', (ev) => { const [px, py] = d3.pointer(ev, box); tip.show(d.tip, px, py); })
        .on('pointerleave', () => tip.hide());
    }
  }

  // Wykres kropkowy poziomy z przedziałami; rows: [{key, label, marks: [{v, lo?, hi?, color, hollow?, strong?}], tip}]
  function dotChart(box, o) {
    const { rows, xFmt, domain, rowH = 30, valueLabel, markGap = 9 } = o;
    const { svg, w } = svgIn(box, 100);
    const ml = textW(svg, rows.map((r) => r.label)) + 14;
    const h = rows.length * rowH + 36;
    svg.attr('height', h).attr('viewBox', `0 0 ${w} ${h}`);
    const all = rows.flatMap((r) => r.marks.flatMap((m) => [m.v, m.lo ?? m.v, m.hi ?? m.v]));
    const x = d3.scaleLinear(domain || d3.extent([...all, 0]), [ml, w - 40]).nice();
    const y = d3.scaleBand(rows.map((r) => r.key), [6, h - 30]).padding(0.2);
    const xa = svg.append('g').attr('transform', `translate(0,${h - 30})`);
    xa.call(d3.axisBottom(x).ticks(Math.max(2, Math.floor((w - ml) / 80))).tickFormat(xFmt).tickSize(-(h - 36)).tickPadding(6))
      .attr('font-size', null).attr('font-family', null);
    xa.select('.domain').remove();
    xa.selectAll('.tick line').attr('class', 'w-grid');
    xa.selectAll('.tick text').attr('class', 'w-tick');
    svg.append('line').attr('class', 'w-zero').attr('x1', x(0)).attr('x2', x(0)).attr('y1', 6).attr('y2', h - 30);
    const tip = tooltip(box);
    rows.forEach((r) => {
      const cy = y(r.key) + y.bandwidth() / 2;
      svg.append('text').attr('class', r.strong ? 'w-lbl' : 'w-tick').attr('x', ml - 10).attr('y', cy).attr('dy', '0.32em').attr('text-anchor', 'end').text(r.label);
      const n = r.marks.length;
      r.marks.forEach((m, i) => {
        const yy = cy + (n > 1 ? (i - (n - 1) / 2) * markGap : 0);
        if (m.lo != null) svg.append('line').attr('x1', x(m.lo)).attr('x2', x(m.hi)).attr('y1', yy).attr('y2', yy).attr('stroke', m.color).attr('stroke-width', 2).attr('stroke-linecap', 'round');
        svg.append('circle').attr('cx', x(m.v)).attr('cy', yy).attr('r', m.strong ? 6 : 4.5)
          .attr('fill', m.hollow ? 'var(--color-panel)' : m.color).attr('stroke', m.hollow ? m.color : 'var(--color-panel)').attr('stroke-width', 2);
        if (valueLabel && m.strong) svg.append('text').attr('class', 'w-lbl').attr('x', x(d3.max(r.marks, (k) => Math.max(k.v, k.hi ?? k.v))) + 10).attr('y', yy).attr('dy', '0.32em').text(valueLabel(m));
      });
      svg.append('rect').attr('x', 0).attr('width', w).attr('y', y(r.key)).attr('height', y.bandwidth()).attr('fill', 'transparent')
        .on('pointermove', (ev) => { const [px, py] = d3.pointer(ev, box); tip.show(r.tip, px, py); })
        .on('pointerleave', () => tip.hide());
    });
  }

  // Legenda z przełącznikami serii.
  function legend(el, keys, { name, color, hidden, onToggle }) {
    el.replaceChildren(...keys.map((k) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.setAttribute('aria-pressed', hidden && hidden.has(k) ? 'false' : 'true');
      const s = document.createElement('span');
      s.className = 'w-sw';
      s.style.background = color(k);
      b.append(s, name(k));
      if (onToggle) b.addEventListener('click', () => onToggle(k));
      else b.disabled = true;
      return b;
    }));
  }

  // Kwantyl rozkładu normalnego (Acklam).
  function normInv(p) {
    const a = [-3.969683028665376e1, 2.209460984245205e2, -2.759285104469687e2, 1.38357751867269e2, -3.066479806614716e1, 2.506628277459239];
    const b = [-5.447609879822406e1, 1.615858368580409e2, -1.556989798598866e2, 6.680131188771972e1, -1.328068155288572e1];
    const c = [-7.784894002430293e-3, -3.223964580411365e-1, -2.400758277161838, -2.549732539343734, 4.374664141464968, 2.938163982698783];
    const d = [7.784695709041462e-3, 3.224671290700398e-1, 2.445134137142996, 3.754408661907416];
    const pl = 0.02425;
    if (p < pl) { const q = Math.sqrt(-2 * Math.log(p)); return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1); }
    if (p > 1 - pl) { const q = Math.sqrt(-2 * Math.log(1 - p)); return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1); }
    const q = p - 0.5, r = q * q;
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1);
  }

  function fill(sel, text) {
    document.querySelectorAll(sel).forEach((el) => { el.textContent = text; });
  }

  return { f, date, num, SECTORS, PHASES, label, sectorColor, phaseColor, DIVERGING, SEQUENTIAL, gate, svgIn, textW, axisY, axisX, tooltip, lineChart, barChart, heatmap, dotChart, legend, normInv, fill };
})();
