// Strony dashboardu: WIG20 (skrypt 1) i sektory GPW a cykl (skrypt 2).
const { f, date, num, SECTORS, PHASES, label, sectorColor, phaseColor, DIVERGING, SEQUENTIAL, gate, svgIn, textW, axisY, axisX, tooltip, lineChart, barChart, heatmap, dotChart, legend, normInv, fill } = window.W;

// ---------- Obliczenia (widoczne w Źródłach) ----------
dash.calc('wig20_change', {
  inputs: ['wig20_daily'],
  title: 'Zmiana WIG20 w próbie',
  description: 'Pierwsze i ostatnie zamknięcie WIG20 w próbie oraz zmiana procentowa między nimi.',
  fn: (wig20_daily) => {
    const r = wig20_daily.filter((d) => d.close != null);
    const a = r[0], b = r[r.length - 1];
    return [{ od: a.date, do: b.date, zamkniecie_od: a.close, zamkniecie_do: b.close, zmiana: b.close / a.close - 1 }];
  },
});

dash.calc('wig20_annual', {
  inputs: ['wig20_stats'],
  title: 'WIG20 w skali roku',
  description: 'Średnia dzienna log-stopa ×252 i odchylenie standardowe ×√252.',
  fn: (wig20_stats) => {
    const g = (k) => wig20_stats.find((r) => r.statystyka === k).wartosc;
    return [{ srednia_roczna: g('Średnia') * 252, zmiennosc_roczna: g('Odchylenie standardowe') * Math.sqrt(252) }];
  },
});

dash.calc('wig20_tails', {
  inputs: ['wig20_daily'],
  title: 'Grube ogony WIG20',
  description: 'Liczba sesji, w których standaryzowana stopa przekracza 3σ, wobec liczby oczekiwanej przy rozkładzie normalnym (0,27% sesji).',
  fn: (wig20_daily) => {
    const r = wig20_daily.map((d) => d.log_return).filter((v) => v != null);
    const m = d3.mean(r), s = d3.deviation(r);
    return [{ n: r.length, obserwowane: r.filter((v) => Math.abs((v - m) / s) > 3).length, oczekiwane_normalny: r.length * 0.0026998 }];
  },
});

// ---------- Stan widoku ----------
const state = {
  page: 'przeglad',
  priceFrom: '2016-01-01',
  sectorFrom: '2017-01-01',
  sectorHidden: new Set(),
  rollingHidden: new Set(),
  bins: 80,
  normal: true,
  measure: 'średnia',
  testsSort: null,
};

const $ = (s) => document.querySelector(s);
const one = (id) => { const d = dash.data(id); return d.status === 'ok' ? d.data : null; };

// ---------- Zakładki ----------
const tabs = [...document.querySelectorAll('.w-tab')];
function showPage(page, link = true) {
  if (!document.getElementById(page) || !tabs.some((t) => t.dataset.page === page)) return;
  state.page = page;
  for (const t of tabs) {
    const on = t.dataset.page === page;
    t.setAttribute('aria-selected', String(on));
    const sec = document.getElementById(t.dataset.page);
    sec.hidden = !on;
    sec.classList.toggle('is-in', on);
  }
  if (link) dash.setLink(page);
  draw();
}
tabs.forEach((t) => t.addEventListener('click', () => showPage(t.dataset.page)));

function chips(groupSel, attr, onPick) {
  const btns = [...document.querySelectorAll(`${groupSel} .w-chip`)];
  btns.forEach((b) => b.addEventListener('click', () => {
    btns.forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
    onPick(b.dataset[attr]);
    draw();
  }));
}
chips('#price-range', 'from', (v) => { state.priceFrom = v; });
chips('#sector-range', 'from', (v) => { state.sectorFrom = v; });
chips('#cal-measure', 'm', (v) => { state.measure = v; });
$('#bins').addEventListener('input', (e) => { state.bins = +e.target.value; $('#bins-val').textContent = e.target.value; draw(); });
$('#show-normal').addEventListener('change', (e) => { state.normal = e.target.checked; draw(); });
['#reg-model', '#phase-metric', '#macro-var', '#roll-var', '#roll-win'].forEach((s) => $(s).addEventListener('change', draw));
document.querySelectorAll('#tbl-tests .w-th-btn').forEach((b) => b.addEventListener('click', () => {
  const k = b.dataset.sort;
  state.testsSort = state.testsSort && state.testsSort.k === k ? { k, dir: -state.testsSort.dir } : { k, dir: 1 };
  draw();
}));

// ---------- Nagłówek ----------
function drawHeader() {
  const tests = one('wig20_tests');
  const byTest = (t) => tests && tests.find((r) => r.test === t);
  const verb = (row, yes, no) => (row ? (row.p_value < 0.05 ? yes : no) : '—');
  fill('.t-ks', verb(byTest('Kolmogorov-Smirnov'), 'nie mają', 'mają'));
  fill('.t-lb', verb(byTest('Ljung-Box lag 20'), 'wykazują', 'nie wykazują'));
  fill('.t-wd', verb(byTest('Kruskal-Wallis – dzień tygodnia'), 'jest istotny', 'nie jest istotny'));
  fill('.t-mo', verb(byTest('Kruskal-Wallis – miesiąc'), 'jest istotny', 'nie jest istotny'));
  document.querySelectorAll('[data-source="wig20_tests"][data-field="p_value"]').forEach((el) => {
    const t = new URLSearchParams(el.dataset.where).get('test');
    const r = byTest(t);
    el.textContent = r ? f.p(r.p_value) : '—';
  });
  const wd = one('wig20_weekday');
  document.querySelectorAll('[data-source="wig20_weekday"][data-field="średnia"]').forEach((el) => {
    const d = new URLSearchParams(el.dataset.where).get('dzien');
    const r = wd && wd.find((x) => x.dzien === d);
    el.textContent = r ? f.spct3(r['średnia']) : '—';
  });
  const pt = one('sector_phase_tests');
  if (pt) {
    const sig = pt.filter((r) => r.kw_p < 0.05).map((r) => `${label(r.sektor)} (p = ${f.p(r.kw_p)})`);
    $('#t-sectors').textContent = sig.length ? sig.join(', ') : 'żaden sektor';
  } else $('#t-sectors').textContent = '—';
}

// ---------- Przegląd ----------
function drawKpis() {
  const st = one('wig20_stats');
  const g = (k) => st && st.find((r) => r.statystyka === k)?.wartosc;
  const set = (where, txt) => { const el = document.querySelector(`.w-kpi [data-source="wig20_stats"][data-where="statystyka=${where}"]`); if (el) el.textContent = txt; };
  set('Liczba obserwacji', st ? f.int(g('Liczba obserwacji')) : '—');
  set('Średnia', st ? f.pct3(g('Średnia')) : '—');
  set('Odchylenie standardowe', st ? f.pct2(g('Odchylenie standardowe')) : '—');
  set('Skośność', st ? f.num2(g('Skośność')) : '—');
  set('Kurtoza nadwyżkowa', st ? f.num2(g('Kurtoza nadwyżkowa')) : '—');
  const ch = dash.data('wig20_change').data?.[0];
  fill('[data-source="wig20_change"][data-field="zmiana"]', ch ? f.spct1(ch.zmiana) : '—');
  fill('[data-source="wig20_change"][data-field="zamkniecie_od"]', ch ? f.num2(ch.zamkniecie_od) : '—');
  fill('[data-source="wig20_change"][data-field="zamkniecie_do"]', ch ? f.num2(ch.zamkniecie_do) : '—');
  const an = dash.data('wig20_annual').data?.[0];
  fill('[data-source="wig20_annual"][data-field="srednia_roczna"]', an ? f.pct1(an.srednia_roczna) : '—');
  fill('[data-source="wig20_annual"][data-field="zmiennosc_roczna"]', an ? f.pct1(an.zmiennosc_roczna) : '—');
}

function drawPrice() {
  const box = $('#chart-price');
  const res = gate(box, ['wig20_daily']);
  if (!res) return;
  const all = res[0].map((d) => ({ x: date(d.date), y: num(d.close), r: num(d.log_return) }));
  let from = state.priceFrom === 'last12' ? d3.utcMonth.offset(all[all.length - 1].x, -12) : date(state.priceFrom);
  const values = all.filter((d) => d.x >= from);
  lineChart(box, {
    series: [{ key: 'WIG20', name: 'WIG20', color: dash.colors[0], values }],
    height: 300, area: true, yFmt: f.int, tipFmt: f.num2,
    yDomain: d3.extent(values, (d) => d.y),
    extraTip: (pts) => (pts[0].d.r == null ? [] : [{ label: 'Stopa dzienna', value: f.spct2(pts[0].d.r) }]),
  });
}

function drawTests() {
  const tb = $('#tbl-tests tbody');
  const rows = one('wig20_tests');
  if (!rows) { tb.replaceChildren(); return; }
  let list = rows.map((r, i) => ({ ...r, i }));
  const s = state.testsSort;
  if (s) list.sort((a, b) => (typeof a[s.k] === 'number' ? a[s.k] - b[s.k] : String(a[s.k]).localeCompare(String(b[s.k]), 'pl')) * s.dir || a.i - b.i);
  document.querySelectorAll('#tbl-tests th').forEach((th) => {
    const k = th.querySelector('button').dataset.sort;
    th.setAttribute('aria-sort', s && s.k === k ? (s.dir > 0 ? 'ascending' : 'descending') : 'none');
  });
  tb.replaceChildren(...list.map((r) => {
    const tr = document.createElement('tr');
    const td = (txt, cls) => { const c = document.createElement('td'); c.textContent = txt; if (cls) c.className = cls; tr.appendChild(c); return c; };
    td(r.grupa);
    td(r.test);
    td(f.num3(r.statystyka), 'num');
    td(f.p(r.p_value), 'num');
    const c = td('');
    const pill = document.createElement('span');
    pill.className = 'w-pill ' + (r.p_value < 0.05 ? 'is-rej' : 'is-keep');
    pill.textContent = r.wniosek;
    c.appendChild(pill);
    return tr;
  }));
}

// ---------- Rozkład ----------
function returnsOf(rows) {
  return rows.filter((d) => d.log_return != null).map((d) => ({ x: date(d.date), y: num(d.log_return) }));
}

function drawReturns() {
  const box = $('#chart-returns');
  const res = gate(box, ['wig20_daily']);
  if (!res) return;
  const v = returnsOf(res[0]);
  const m = d3.mean(v, (d) => d.y), s = d3.deviation(v, (d) => d.y);
  lineChart(box, {
    series: [{ key: 'r', name: 'Log-stopa', color: dash.colors[0], values: v }],
    height: 240, strokeWidth: 1, endLabels: false, yFmt: f.pct0, tipFmt: f.spct2,
    refs: [{ y: 0, zero: true }, { y: m + 3 * s, label: '+3σ' }, { y: m - 3 * s, label: '−3σ' }],
    extraTip: (pts) => [{ label: 'Odchylenie', value: `${f.num1((pts[0].d.y - m) / s)} σ` }],
  });
}

function drawHist() {
  const box = $('#chart-hist');
  const res = gate(box, ['wig20_daily']);
  if (!res) return;
  const r = returnsOf(res[0]).map((d) => d.y);
  const n = r.length, m = d3.mean(r), s = d3.deviation(r);
  const { svg, w, h } = svgIn(box, 280);
  const x0 = d3.scaleLinear(d3.extent(r), [0, 1]).nice();
  const bins = d3.bin().domain(x0.domain()).thresholds(x0.ticks(state.bins))(r).filter((b) => b.x1 > b.x0);
  const dens = (b) => b.length / (n * (b.x1 - b.x0));
  const pdf = (v) => Math.exp(-0.5 * ((v - m) / s) ** 2) / (s * Math.sqrt(2 * Math.PI));
  const y = d3.scaleLinear([0, Math.max(d3.max(bins, dens), pdf(m))], [h - 26, 10]).nice();
  const ml = textW(svg, y.ticks(5).map(f.int)) + 10;
  const x = x0.copy().range([ml, w - 8]);
  axisY(svg.append('g').attr('transform', `translate(${ml},0)`), y, f.int, w - ml - 8);
  axisX(svg.append('g').attr('transform', `translate(0,${h - 26})`), x, f.pct0, Math.max(3, Math.floor((w - ml) / 70)));
  const tip = tooltip(box);
  const g = svg.append('g');
  bins.forEach((b) => {
    const bx = x(b.x0) + 0.5, bw = Math.max(0.5, x(b.x1) - x(b.x0) - 1);
    g.append('rect').attr('x', bx).attr('width', bw).attr('y', y(dens(b))).attr('height', y(0) - y(dens(b)))
      .attr('fill', dash.colors[0]).attr('rx', Math.min(2, bw / 2));
    const expected = n * (normCdf((b.x1 - m) / s) - normCdf((b.x0 - m) / s));
    g.append('rect').attr('x', x(b.x0)).attr('width', x(b.x1) - x(b.x0)).attr('y', 0).attr('height', h - 26).attr('fill', 'transparent')
      .on('pointermove', (ev) => {
        const [px, py] = d3.pointer(ev, box);
        tip.show([
          { head: true, label: `${f.pct2(b.x0)} do ${f.pct2(b.x1)}` },
          { label: 'Sesje', value: f.int(b.length) },
          { label: 'Udział', value: f.pct2(b.length / n) },
          { label: 'Oczekiwane (normalny)', value: f.num1(expected) },
        ], px, py);
      })
      .on('pointerleave', () => tip.hide());
  });
  if (state.normal) {
    const xs = d3.range(x0.domain()[0], x0.domain()[1], (x0.domain()[1] - x0.domain()[0]) / 300);
    svg.append('path').attr('fill', 'none').attr('stroke', 'var(--color-fg)').attr('stroke-width', 2).attr('stroke-linejoin', 'round')
      .attr('d', d3.line().x((v) => x(v)).y((v) => y(pdf(v)))(xs)).style('pointer-events', 'none');
    svg.append('text').attr('class', 'w-lbl').attr('x', x(m + 1.2 * s) + 6).attr('y', y(pdf(m + 1.2 * s))).text('N(μ, σ)');
  }
  const t = dash.data('wig20_tails').data?.[0];
  fill('[data-source="wig20_tails"][data-field="obserwowane"]', t ? f.int(t.obserwowane) : '—');
  fill('[data-source="wig20_tails"][data-field="oczekiwane_normalny"]', t ? f.num1(t.oczekiwane_normalny) : '—');
}

function normCdf(z) {
  // Abramowitz-Stegun 7.1.26
  const t = 1 / (1 + 0.3275911 * Math.abs(z) / Math.SQRT2);
  const e = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-z * z / 2);
  return z >= 0 ? (1 + e) / 2 : (1 - e) / 2;
}

function drawQQ() {
  const box = $('#chart-qq');
  const res = gate(box, ['wig20_daily']);
  if (!res) return;
  const v = returnsOf(res[0]);
  const n = v.length, m = d3.mean(v, (d) => d.y), s = d3.deviation(v, (d) => d.y);
  const pts = v.map((d) => ({ ...d, z: (d.y - m) / s })).sort((a, b) => a.z - b.z).map((d, i) => ({ ...d, q: normInv((i + 0.5) / n) }));
  const { svg, w, h } = svgIn(box, 280);
  const lim = Math.ceil(Math.max(d3.max(pts, (d) => Math.abs(d.z)), 4));
  const y = d3.scaleLinear([-lim, lim], [h - 26, 10]);
  const ml = textW(svg, y.ticks(6).map(f.int)) + 10;
  const x = d3.scaleLinear([-4, 4], [ml, w - 8]);
  axisY(svg.append('g').attr('transform', `translate(${ml},0)`), y, f.int, w - ml - 8, 6);
  axisX(svg.append('g').attr('transform', `translate(0,${h - 26})`), x, f.int, 8);
  svg.append('line').attr('class', 'w-ref').attr('x1', x(-4)).attr('x2', x(4)).attr('y1', y(-4)).attr('y2', y(4));
  svg.append('text').attr('class', 'w-lbl-muted').attr('x', x(1.6)).attr('y', y(1.6) + 16).text('rozkład normalny');
  svg.append('text').attr('class', 'w-lbl-muted').attr('x', ml + 4).attr('y', 22).text('kwantyle empiryczne (z)');
  svg.append('text').attr('class', 'w-lbl-muted').attr('x', w - 8).attr('y', h - 32).attr('text-anchor', 'end').text('kwantyle N(0,1)');
  svg.append('g').selectAll('circle').data(pts).join('circle')
    .attr('cx', (d) => x(d.q)).attr('cy', (d) => y(d.z)).attr('r', 2.2)
    .attr('fill', (d) => (Math.abs(d.z) > 3 ? dash.colors[1] : dash.colors[0])).attr('fill-opacity', 0.75);
  const del = d3.Delaunay.from(pts, (d) => x(d.q), (d) => y(d.z));
  const hl = svg.append('circle').attr('r', 5).attr('fill', 'none').attr('stroke', 'var(--color-fg)').attr('stroke-width', 2).style('display', 'none');
  const tip = tooltip(box);
  svg.append('rect').attr('x', ml).attr('width', w - ml - 8).attr('y', 0).attr('height', h - 26).attr('fill', 'transparent')
    .on('pointermove', (ev) => {
      const [mx, my] = d3.pointer(ev);
      const d = pts[del.find(mx, my)];
      hl.attr('cx', x(d.q)).attr('cy', y(d.z)).style('display', null);
      const [px, py] = d3.pointer(ev, box);
      tip.show([{ head: true, label: f.day(d.x) }, { label: 'Log-stopa', value: f.spct2(d.y) }, { label: 'z', value: f.num2(d.z) }, { label: 'Kwantyl N(0,1)', value: f.num2(d.q) }], px, py);
    })
    .on('pointerleave', () => { hl.style('display', 'none'); tip.hide(); });
}

function drawAcf() {
  const box = $('#chart-acf');
  const res = gate(box, ['wig20_acf']);
  if (!res) return;
  const rows = res[0].map((d) => ({ lag: +d.lag, acf: +d.acf, band: +d.przedzial }));
  const { svg, w, h } = svgIn(box, 260);
  const lim = Math.max(d3.max(rows, (d) => Math.max(Math.abs(d.acf), d.band)) * 1.15, 0.06);
  const y = d3.scaleLinear([-lim, lim], [h - 26, 10]).nice();
  const ml = textW(svg, y.ticks(5).map(f.num2)) + 10;
  const x = d3.scaleBand(rows.map((d) => d.lag), [ml, w - 8]).padding(0.25);
  axisY(svg.append('g').attr('transform', `translate(${ml},0)`), y, f.num2, w - ml - 8);
  const xa = svg.append('g').attr('transform', `translate(0,${h - 26})`);
  axisX(xa, x, (d) => d);
  xa.selectAll('.tick').style('display', (d) => (d % 5 === 0 || d === 1 ? null : 'none'));
  const cx = (d) => x(d.lag) + x.bandwidth() / 2;
  svg.append('path').attr('fill', 'var(--cds-chart-reference-tint)')
    .attr('d', d3.area().x(cx).y0((d) => y(-d.band)).y1((d) => y(d.band)).curve(d3.curveStepAfter)(rows));
  svg.append('line').attr('class', 'w-zero').attr('x1', ml).attr('x2', w - 8).attr('y1', y(0)).attr('y2', y(0));
  const tip = tooltip(box);
  rows.forEach((d) => {
    const out = Math.abs(d.acf) > d.band;
    svg.append('rect').attr('x', cx(d) - Math.min(x.bandwidth(), 10) / 2).attr('width', Math.min(x.bandwidth(), 10))
      .attr('y', Math.min(y(0), y(d.acf))).attr('height', Math.max(1, Math.abs(y(d.acf) - y(0)))).attr('rx', 2)
      .attr('fill', out ? dash.colors[1] : 'var(--cds-chart-muted)');
    svg.append('rect').attr('x', x(d.lag)).attr('width', x.bandwidth()).attr('y', 0).attr('height', h - 26).attr('fill', 'transparent')
      .on('pointermove', (ev) => {
        const [px, py] = d3.pointer(ev, box);
        tip.show([{ head: true, label: `Opóźnienie ${d.lag}` }, { label: 'ACF', value: f.num3(d.acf) }, { label: 'Granica 95%', value: `±${f.num3(d.band)}` }, { label: out ? 'Poza przedziałem' : 'W przedziale' }], px, py);
      })
      .on('pointerleave', () => tip.hide());
  });
}

function drawLB() {
  const box = $('#chart-lb');
  const leg = $('#leg-lb');
  const res = gate(box, ['wig20_ljungbox']);
  const ser = [{ k: 'lb_pvalue', name: 'Ljung-Box', color: dash.colors[0] }, { k: 'bp_pvalue', name: 'Box-Pierce', color: dash.colors[1] }];
  legend(leg, ser.map((s) => s.k), { name: (k) => ser.find((s) => s.k === k).name, color: (k) => ser.find((s) => s.k === k).color });
  if (!res) return;
  const rows = res[0];
  const { svg, w, h } = svgIn(box, 240);
  const y = d3.scaleLinear([0, Math.max(0.45, d3.max(rows, (d) => Math.max(d.lb_pvalue, d.bp_pvalue)))], [h - 26, 10]).nice();
  const ml = textW(svg, y.ticks(5).map(f.num2)) + 10;
  const x = d3.scaleBand(rows.map((d) => d.lag), [ml, w - 8]).padding(0.3);
  axisY(svg.append('g').attr('transform', `translate(${ml},0)`), y, f.num2, w - ml - 8);
  axisX(svg.append('g').attr('transform', `translate(0,${h - 26})`), x, (d) => `lag ${d}`);
  svg.append('line').attr('class', 'w-ref').attr('x1', ml).attr('x2', w - 8).attr('y1', y(0.05)).attr('y2', y(0.05));
  svg.append('text').attr('class', 'w-lbl-muted').attr('x', w - 8).attr('y', y(0.05) - 5).attr('text-anchor', 'end').text('α = 0,05');
  const tip = tooltip(box);
  rows.forEach((d) => {
    const c = x(d.lag) + x.bandwidth() / 2;
    ser.forEach((s, i) => {
      svg.append('circle').attr('cx', c + (i ? 7 : -7)).attr('cy', y(d[s.k])).attr('r', 5.5).attr('fill', s.color).attr('stroke', 'var(--color-panel)').attr('stroke-width', 2);
    });
    svg.append('rect').attr('x', x(d.lag)).attr('width', x.bandwidth()).attr('y', 0).attr('height', h - 26).attr('fill', 'transparent')
      .on('pointermove', (ev) => {
        const [px, py] = d3.pointer(ev, box);
        tip.show([{ head: true, label: `Opóźnienie ${d.lag}` },
          { color: ser[0].color, label: `Q = ${f.num2(d.lb_stat)}`, value: `p ${f.p(d.lb_pvalue)}` },
          { color: ser[1].color, label: `Q = ${f.num2(d.bp_stat)}`, value: `p ${f.p(d.bp_pvalue)}` }], px, py);
      })
      .on('pointerleave', () => tip.hide());
  });
}

// ---------- Kalendarz ----------
function calItems(rows, nameKey, short) {
  const m = state.measure;
  return rows.slice().sort((a, b) => a.nr - b.nr).map((r) => {
    const se = r.odchylenie_std / Math.sqrt(r.liczba);
    const ci = m === 'średnia' ? { lo: r['średnia'] - 1.96 * se, hi: r['średnia'] + 1.96 * se } : {};
    return {
      key: r[nameKey], label: r[nameKey], short: short ? r[nameKey].slice(0, 3) : null, value: r[m], ...ci, color: dash.colors[0],
      tip: [
        { head: true, label: r[nameKey] },
        { label: 'Sesje', value: f.int(r.liczba) },
        { label: 'Średnia', value: f.spct3(r['średnia']) },
        { label: '95% CI', value: `${f.pct2(r['średnia'] - 1.96 * se)} do ${f.pct2(r['średnia'] + 1.96 * se)}` },
        { label: 'Mediana', value: f.spct3(r.mediana) },
        { label: 'Odchylenie std.', value: f.pct2(r.odchylenie_std) },
        { label: 'Min / max', value: `${f.pct1(r.minimum)} / ${f.pct1(r.maksimum)}` },
      ],
    };
  });
}

function drawCalendar() {
  const tests = one('wig20_tests');
  document.querySelectorAll('#kalendarz [data-source="wig20_tests"]').forEach((el) => {
    const t = new URLSearchParams(el.dataset.where).get('test');
    const r = tests && tests.find((x) => x.test === t);
    el.textContent = r ? f.p(r.p_value) : '—';
  });
  const b1 = $('#chart-weekday'), r1 = gate(b1, ['wig20_weekday']);
  if (r1) barChart(b1, { items: calItems(r1[0], 'dzien', true), yFmt: f.pct2, labelFmt: f.spct3 });
  const b2 = $('#chart-month'), r2 = gate(b2, ['wig20_month']);
  if (r2) barChart(b2, { items: calItems(r2[0], 'miesiac', true), yFmt: f.pct2, labelFmt: f.spct2 });

  const box = $('#chart-reg');
  const res = gate(box, ['wig20_regression']);
  const model = $('#reg-model').value;
  const base = { 'Dzień tygodnia': 'poniedziałek', 'Miesiąc': 'styczeń', 'Łączna': 'poniedziałek w styczniu' }[model];
  $('#reg-base').textContent = base;
  $('#reg-intercept-name').textContent = base;
  const iv = $('#reg-intercept-val');
  iv.dataset.where = `model=${model}&term=Intercept`;
  if (!res) { iv.textContent = '—'; return; }
  const rows = res[0].filter((r) => r.model === model);
  const ic = rows.find((r) => r.term === 'Intercept');
  iv.textContent = ic ? `${f.spct3(ic.coef)} (p ${f.p(ic.p_value)})` : '—';
  dotChart(box, {
    rows: rows.filter((r) => r.term !== 'Intercept').map((r) => {
      const sig = r.p_value < 0.05;
      return {
        key: r.term, label: r.zmienna, strong: sig,
        marks: [{ v: r.coef, lo: r.coef - 1.96 * r.std_err_HAC, hi: r.coef + 1.96 * r.std_err_HAC, color: sig ? dash.colors[0] : 'var(--cds-chart-muted)', strong: sig }],
        tip: [{ head: true, label: `${r.zmienna} vs ${base}` }, { label: 'Współczynnik', value: f.spct3(r.coef) }, { label: 'Błąd HAC', value: f.pct3(r.std_err_HAC) }, { label: 't', value: f.num2(r.t) }, { label: 'p-value', value: f.p(r.p_value) }],
      };
    }),
    xFmt: f.pct2, rowH: model === 'Łączna' ? 24 : 30,
    valueLabel: (m) => f.spct3(m.v),
  });
}

// ---------- Sektory ----------
function toggler(set) {
  return (k) => { if (set.has(k)) set.delete(k); else if (set.size < SECTORS.length - 1) set.add(k); draw(); };
}

function drawSectorPrices() {
  const box = $('#chart-sector-prices');
  legend($('#leg-sector-prices'), SECTORS, { name: label, color: sectorColor, hidden: state.sectorHidden, onToggle: toggler(state.sectorHidden) });
  const res = gate(box, ['sector_prices']);
  if (!res) return;
  const from = date(state.sectorFrom);
  const rows = res[0].map((d) => ({ ...d, x: date(d.date) })).filter((d) => d.x >= from);
  const series = SECTORS.filter((k) => !state.sectorHidden.has(k)).map((k) => {
    const vals = rows.filter((d) => d[k] != null);
    const base = vals.length ? vals[0][k] : 1;
    return { key: k, name: label(k), color: sectorColor(k), values: vals.map((d) => ({ x: d.x, y: (100 * d[k]) / base })) };
  }).filter((s) => s.values.length);
  lineChart(box, { series, height: 340, yFmt: f.int, tipFmt: f.num1, refs: [{ y: 100, zero: true }] });
}

function drawCycle() {
  const box = $('#chart-cycle');
  const present = PHASES;
  legend($('#leg-cycle'), present, { name: (k) => k, color: phaseColor });
  $('#leg-cycle').querySelectorAll('button').forEach((b) => { b.disabled = true; b.style.cursor = 'default'; });
  const res = gate(box, ['business_cycle']);
  if (!res) return;
  const rows = res[0].map((d) => ({ ...d, x: date(d.date) }));
  const { svg, w, h } = svgIn(box, 260);
  const y = d3.scaleLinear(d3.extent([...rows.map((d) => d.GDP_growth), 0]), [h - 26, 12]).nice();
  const yFmt = (v) => `${f.num1(v)}%`;
  const ml = textW(svg, y.ticks(5).map(yFmt)) + 10;
  const x = d3.scaleBand(rows.map((d) => d.quarter), [ml, w - 6]).padding(0.2);
  axisY(svg.append('g').attr('transform', `translate(${ml},0)`), y, yFmt, w - ml - 6);
  const xa = svg.append('g').attr('transform', `translate(0,${h - 26})`);
  axisX(xa, x, (q) => q.slice(0, 4));
  const every = x.bandwidth() * 4 < 34 ? 8 : 4;
  xa.selectAll('.tick').style('display', (q, i) => (q.endsWith('Q1') && (Number(q.slice(0, 4)) % (every / 4) === 0) ? null : 'none'));
  svg.append('line').attr('class', 'w-zero').attr('x1', ml).attr('x2', w - 6).attr('y1', y(0)).attr('y2', y(0));
  const tip = tooltip(box);
  rows.forEach((d) => {
    const y1 = y(d.GDP_growth);
    svg.append('rect').attr('x', x(d.quarter)).attr('width', x.bandwidth()).attr('y', Math.min(y(0), y1)).attr('height', Math.max(1, Math.abs(y1 - y(0))))
      .attr('rx', Math.min(4, x.bandwidth() / 2)).attr('fill', phaseColor(d.phase));
    svg.append('rect').attr('x', x(d.quarter) - x.step() * x.paddingInner() / 2).attr('width', x.step()).attr('y', 0).attr('height', h - 26).attr('fill', 'transparent')
      .on('pointermove', (ev) => {
        const [px, py] = d3.pointer(ev, box);
        tip.show([{ head: true, label: d.quarter.replace('Q', ' Q') }, { color: phaseColor(d.phase), label: d.phase },
          { label: 'PKB kw/kw', value: yFmt(d.GDP_growth) },
          { label: 'Zmiana vs poprz. kw.', value: d.GDP_change == null ? '—' : `${f.snum2(d.GDP_change)} pp` }], px, py);
      })
      .on('pointerleave', () => tip.hide());
  });
  const low = rows.reduce((a, b) => (b.GDP_growth < a.GDP_growth ? b : a));
  svg.append('text').attr('class', 'w-lbl').attr('x', x(low.quarter) + x.bandwidth() + 6).attr('y', y(low.GDP_growth)).attr('dy', '0.32em')
    .text(`${low.quarter.replace('Q', ' Q')}: ${yFmt(low.GDP_growth)}`);
}

function drawPhaseHeat() {
  const box = $('#chart-phase-heat');
  const res = gate(box, ['phase_stats']);
  if (!res) return;
  const metric = $('#phase-metric').value;
  const rows = res[0];
  const vals = rows.map((r) => r[metric]).filter((v) => v != null);
  let color, fmt;
  if (metric === 'odchylenie') {
    color = d3.scaleQuantize(d3.extent(vals), SEQUENTIAL);
    fmt = f.pct1;
  } else {
    const m = d3.max(vals, Math.abs);
    color = d3.scaleQuantize([-m, m], [...DIVERGING].reverse());
    fmt = f.spct1;
  }
  heatmap(box, {
    rows: PHASES, cols: SECTORS, rowLabel: (p) => p, colLabel: label, cellH: 44,
    cells: rows.map((r) => ({
      r: r.phase, c: r.sektor, v: r[metric], text: r[metric] == null ? '' : fmt(r[metric]),
      tip: [{ head: true, label: `${label(r.sektor)} · ${r.phase}` },
        { label: 'Miesięcy', value: r.liczba_miesiecy == null ? '—' : f.int(r.liczba_miesiecy) },
        { label: 'Średnia', value: f.spct2(r.srednia) }, { label: 'Mediana', value: f.spct2(r.mediana) },
        { label: 'Suma log-stóp', value: f.spct1(r.skumulowana) }, { label: 'Odchylenie std.', value: f.pct2(r.odchylenie) }],
    })),
    color,
  });
}

function drawPhaseTests() {
  const tb = $('#tbl-phase-tests tbody');
  const rows = one('sector_phase_tests');
  if (!rows) { tb.replaceChildren(); return; }
  tb.replaceChildren(...SECTORS.map((k) => rows.find((r) => r.sektor === k)).filter(Boolean).map((r) => {
    const tr = document.createElement('tr');
    tr.dataset.key = r.sektor;
    const td = (txt, cls) => { const c = document.createElement('td'); c.textContent = txt; if (cls) c.className = cls; tr.appendChild(c); return c; };
    const c0 = td('');
    const sw = document.createElement('span');
    sw.className = 'w-sw';
    sw.style.background = sectorColor(r.sektor);
    sw.style.marginRight = '0.4rem';
    c0.append(sw, label(r.sektor));
    td(f.num2(r.H), 'num');
    td(f.p(r.kw_p), 'num');
    td(f.num2(r.F), 'num');
    td(f.p(r.anova_p), 'num');
    const c = td('');
    const pill = document.createElement('span');
    pill.className = 'w-pill ' + (r.kw_p < 0.05 ? 'is-rej' : 'is-keep');
    pill.textContent = r.wniosek_kw;
    c.appendChild(pill);
    return tr;
  }));
}

function drawCorrMatrix() {
  const box = $('#chart-corr-matrix');
  const res = gate(box, ['sector_corr_matrix']);
  if (!res) return;
  const rows = res[0];
  const keys = [...new Set(rows.map((r) => r.wiersz))];
  heatmap(box, {
    rows: keys, cols: keys, rowLabel: label, colLabel: label, cellH: 36,
    color: d3.scaleQuantize([-1, 1], [...DIVERGING].reverse()),
    cells: rows.map((r) => ({
      r: r.wiersz, c: r.kolumna, v: r.korelacja, text: f.num2(r.korelacja),
      tip: [{ head: true, label: `${label(r.wiersz)} × ${label(r.kolumna)}` }, { label: 'r Pearsona', value: f.num3(r.korelacja) }],
    })),
  });
}

function drawMacroCorr() {
  const box = $('#chart-macro-corr');
  const res = gate(box, ['sector_macro_corr']);
  if (!res) return;
  const v = $('#macro-var').value;
  const rows = SECTORS.map((k) => res[0].find((r) => r.sektor === k && r.zmienna === v)).filter(Boolean);
  dotChart(box, {
    domain: [-0.5, 0.5], xFmt: f.num1, rowH: 44, markGap: 14,
    rows: rows.map((r) => {
      const sp = r.pearson_p < 0.05, ss = r.spearman_p < 0.05;
      return {
        key: r.sektor, label: label(r.sektor), strong: sp || ss,
        marks: [
          { v: r.pearson, color: sp ? 'var(--color-fg)' : 'var(--cds-chart-muted)', strong: sp },
          { v: r.spearman, color: ss ? 'var(--color-fg)' : 'var(--cds-chart-muted)', hollow: true, strong: ss },
        ],
        tip: [{ head: true, label: `${label(r.sektor)} × ${label(r.zmienna)}` },
          { label: 'Pearson r', value: `${f.num3(r.pearson)} (p ${f.p(r.pearson_p)})` },
          { label: 'Spearman ρ', value: `${f.num3(r.spearman)} (p ${f.p(r.spearman_p)})` },
          { label: 'Miesięcy', value: f.int(r.N) }],
      };
    }),
    valueLabel: (m) => f.num2(m.v),
  });
}

function drawRolling() {
  const box = $('#chart-rolling');
  legend($('#leg-rolling'), SECTORS, { name: label, color: sectorColor, hidden: state.rollingHidden, onToggle: toggler(state.rollingHidden) });
  const res = gate(box, ['rolling_corr']);
  if (!res) return;
  const v = $('#roll-var').value, win = +$('#roll-win').value;
  const rows = res[0].filter((r) => r.zmienna === v && +r.okno === win);
  const series = SECTORS.filter((k) => !state.rollingHidden.has(k)).map((k) => ({
    key: k, name: label(k), color: sectorColor(k),
    values: rows.filter((r) => r.sektor === k).map((r) => ({ x: date(r.date), y: +r.korelacja })).sort((a, b) => a.x - b.x),
  })).filter((s) => s.values.length);
  lineChart(box, { series, height: 320, yFmt: f.num1, tipFmt: f.num2, xTipFmt: f.month, yDomain: [-1, 1], refs: [{ y: 0, zero: true }] });
}

// ---------- Rysowanie ----------
function draw() {
  drawHeader();
  drawKpis();
  drawTests();
  drawPhaseTests();
  const p = state.page;
  if (p === 'przeglad') { drawPrice(); }
  if (p === 'rozklad') { drawReturns(); drawHist(); drawQQ(); drawAcf(); drawLB(); }
  if (p === 'kalendarz') { drawCalendar(); }
  if (p === 'sektory') { drawSectorPrices(); drawCycle(); drawPhaseHeat(); drawCorrMatrix(); drawMacroCorr(); drawRolling(); }
}

dash.onData(draw);

const named = location.hash.slice(1);
if (named && tabs.some((t) => t.dataset.page === named)) showPage(named, false);
