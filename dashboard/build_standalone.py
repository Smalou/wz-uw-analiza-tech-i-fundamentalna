# ============================================================
# SAMODZIELNY DASHBOARD HTML
#
# Składa jeden plik WIG20_dashboard.html z:
#   - kodu strony (dashboard/page/),
#   - danych JSON (dashboard/data/, z export_dashboard_data.py),
#   - biblioteki d3 (dashboard/vendor/).
#
# Plik działa offline, bez logowania: wystarczy otworzyć go
# w przeglądarce albo opublikować np. na GitHub Pages.
#
#   python dashboard/export_dashboard_data.py
#   python dashboard/build_standalone.py
# ============================================================

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAGE = HERE / "page"
DATA = HERE / "data"
OUTPUT = HERE / "WIG20_dashboard.html"
D3 = HERE / "vendor" / "d3-7.9.0.min.js"


def safe_script(text):
    # Tekst wstawiany do <script> nie może zamknąć znacznika.
    return text.replace("</", "<\\/")


data = {
    path.stem: json.loads(path.read_text(encoding="utf-8"))
    for path in sorted(DATA.glob("*.json"))
}

page = (PAGE / "index.html").read_text(encoding="utf-8")
page = page.replace(
    '<script src="core.js"></script>',
    "<script>\n" + safe_script((PAGE / "core.js").read_text(encoding="utf-8")) + "\n</script>",
)
page = page.replace(
    '<script src="app.js"></script>',
    "<script>\n" + safe_script((PAGE / "app.js").read_text(encoding="utf-8")) + "\n</script>",
)

# Zmienne kolorów i odstępów, które w Claude dostarcza typ Dashboard.
TOKENS = """
/* Motyw wg Brandbooka WZ UW: granat #142A5B, niebieski #284BA9, ciemny granat #081732,
   grafit #3E4551, złoto #D8BC44, szary #979CA4; krój DM Sans. Kolory serii przyciemnione
   / rozjaśnione z palety uzupełniającej, by spełnić kontrast i rozróżnialność (CVD). */
:root {
  color-scheme: light;
  --font-anthropic-sans: "DM Sans", system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
  --font-anthropic-serif: "DM Sans", system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
  --cds-font-size-caption: .75rem; --cds-font-size-body: .875rem; --cds-font-size-heading: .9375rem; --cds-font-size-title: 1.5rem;
  --cds-font-weight-medium: 600;
  --cds-gap-xs: .375rem; --cds-gap-sm: .5rem; --cds-gap-md: .75rem; --cds-gap-lg: 1.25rem; --cds-gap-xl: 2rem;
  --cds-pad-xs: .375rem; --cds-pad-sm: .5rem; --cds-pad-md: .625rem; --cds-pad-lg: 1rem;
  --cds-radius: 6px; --cds-dur-slow: 300ms; --cds-ease-out: cubic-bezier(.16, 1, .3, 1);

  --uw-navy: #142A5B; --uw-navy-deep: #081732; --uw-blue: #284BA9; --uw-gold: #D8BC44; --uw-grey: #979CA4;
  --uw-title: #142A5B; --uw-band-bg: #142A5B; --uw-band-fg: #ffffff; --uw-band-muted: #c9d1e3;

  --color-bg: #f4f6fa; --color-panel: #ffffff; --color-fg: #081732; --color-fg-muted: #555d6b;
  --color-border-line: #dde2ea; --color-ok: #2f7d32; --color-warn: #8a6d00; --color-bad: #c0392b;
  --cds-surface-popover: #ffffff; --cds-border: #dde2ea; --cds-text-secondary: #3E4551;
  --cds-shadow-popover: 0 8px 24px rgba(8,23,50,.14), 0 2px 6px rgba(8,23,50,.08);

  --cds-chart-categorical-1: #284BA9; --cds-chart-categorical-2: #D86F00; --cds-chart-categorical-3: #C33693; --cds-chart-categorical-4: #A88A14;
  --cds-chart-categorical-5: #308ED9; --cds-chart-categorical-6: #6F8C0A; --cds-chart-categorical-7: #7B4FB8; --cds-chart-categorical-8: #979CA4;
  --cds-chart-diverging-1: #142A5B; --cds-chart-diverging-2: #308ED9; --cds-chart-diverging-3: #A9CBEA; --cds-chart-diverging-4: #eef0f4;
  --cds-chart-diverging-5: #F6C48C; --cds-chart-diverging-6: #EB7B00; --cds-chart-diverging-7: #A85300;
  --cds-chart-sequential-1: #E3EEF9; --cds-chart-sequential-2: #C3DBF1; --cds-chart-sequential-3: #96C4E6; --cds-chart-sequential-4: #5FA6DE;
  --cds-chart-sequential-5: #308ED9; --cds-chart-sequential-6: #284BA9; --cds-chart-sequential-7: #142A5B;
  --cds-chart-grid: rgba(20,42,91,.08); --cds-chart-axis: #c4cad4; --cds-chart-baseline: #979CA4; --cds-chart-reference: #7d838e;
  --cds-chart-reference-tint: rgba(151,156,164,.16); --cds-chart-muted: #c4cad4; --cds-chart-status-critical: #c0392b;
}
@media (prefers-color-scheme: dark) {
  :root {
    color-scheme: dark;
    --uw-title: #eef1f7; --uw-band-bg: #081732; --uw-band-muted: #97a3bf;
    --color-bg: #081732; --color-panel: #0F1F42; --color-fg: #eef1f7; --color-fg-muted: #a3aab8;
    --color-border-line: #22355f; --color-ok: #7cc47f; --color-warn: #e0c25a; --color-bad: #ef7d6d;
    --cds-surface-popover: #142A5B; --cds-border: #2b4275; --cds-text-secondary: #c9cfdb;
    --cds-shadow-popover: 0 8px 24px rgba(0,0,0,.4), 0 2px 6px rgba(0,0,0,.25);
    --cds-chart-categorical-1: #5A7FDB; --cds-chart-categorical-2: #CF6A00; --cds-chart-categorical-3: #C94B9E; --cds-chart-categorical-4: #A8891A;
    --cds-chart-categorical-5: #3A8DD3; --cds-chart-categorical-6: #7C9812; --cds-chart-categorical-7: #9070D4; --cds-chart-categorical-8: #979CA4;
    --cds-chart-diverging-1: #96C4E6; --cds-chart-diverging-2: #308ED9; --cds-chart-diverging-3: #1f427f; --cds-chart-diverging-4: #1a2a4f;
    --cds-chart-diverging-5: #6b3a08; --cds-chart-diverging-6: #D86F00; --cds-chart-diverging-7: #F6C48C;
    --cds-chart-sequential-1: #142A5B; --cds-chart-sequential-2: #1f427f; --cds-chart-sequential-3: #284BA9; --cds-chart-sequential-4: #308ED9;
    --cds-chart-sequential-5: #5FA6DE; --cds-chart-sequential-6: #96C4E6; --cds-chart-sequential-7: #d6e7f6;
    --cds-chart-grid: rgba(238,241,247,.08); --cds-chart-axis: #2b4275; --cds-chart-baseline: #4a5c86; --cds-chart-reference: #97a3bf;
    --cds-chart-reference-tint: rgba(151,163,191,.14); --cds-chart-muted: #3d4f78; --cds-chart-status-critical: #ef7d6d;
  }
}
html, body { margin: 0; background: var(--color-bg); color: var(--color-fg); }
body { font-family: var(--font-anthropic-sans); font-size: var(--cds-font-size-body); line-height: 1.45; }
#dash-root { max-width: 1280px; margin-inline: auto; padding-inline: clamp(16px, 3vw, 40px); padding-block: 28px 48px; box-sizing: border-box; }
#dash-root *, #dash-root *::before, #dash-root *::after { box-sizing: border-box; }
.dash-skeleton { background: var(--cds-chart-reference-tint); border-radius: var(--cds-radius); }

/* Pasek wydziału */
.uw-band { background: var(--uw-band-bg); color: var(--uw-band-fg); border-bottom: 3px solid var(--uw-gold); }
.uw-band-inner { max-width: 1280px; margin-inline: auto; padding: 14px clamp(16px, 3vw, 40px); display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px 14px; }
.uw-faculty { font-weight: 700; font-size: 1rem; letter-spacing: .01em; }
.uw-uni { font-size: .875rem; color: var(--uw-band-muted); }
.uw-course { margin-left: auto; font-size: .75rem; letter-spacing: .06em; text-transform: uppercase; color: var(--uw-gold); }
#dash-root .w-title { color: var(--uw-title); font-weight: 700; letter-spacing: -.01em; }
#dash-root .w-kpi-value { color: var(--uw-title); font-weight: 600; }
#dash-root .w-tab[aria-selected="true"] { border-bottom-color: var(--uw-gold); }
#dash-root .w-chip[aria-pressed="true"] { background: var(--uw-blue); border-color: var(--uw-blue); color: #fff; }
#dash-root .w-card h3 { color: var(--uw-title); }
.uw-foot { max-width: 1280px; margin-inline: auto; padding: 0 clamp(16px, 3vw, 40px) 32px; color: var(--color-fg-muted); font-size: .75rem; }
"""

# Zamiennik API `dash` z Claude: dane są wbudowane w plik.
SHIM = """
window.dash = (() => {
  const DATA = JSON.parse(document.getElementById('dash-data').textContent);
  const calcs = {};
  const subs = [];
  const data = (id) => {
    if (id in DATA) return { status: 'ok', data: DATA[id], columns: Object.keys(DATA[id][0] || {}), refreshing: false, meta: [] };
    if (id in calcs) return { status: 'ok', data: calcs[id], columns: Object.keys(calcs[id][0] || {}), refreshing: false, meta: [] };
    return { status: 'missing', data: [], refreshing: false, meta: [] };
  };
  const run = () => subs.forEach((fn) => { try { fn(); } catch (e) { console.error(e); } });
  let lastW = 0, raf = 0;
  window.addEventListener('resize', () => {
    cancelAnimationFrame(raf);
    raf = requestAnimationFrame(() => { const w = document.getElementById('dash-root').clientWidth; if (w !== lastW) { lastW = w; run(); } });
  });
  return {
    data,
    calc(id, { inputs, fn }) { calcs[id] = fn(...inputs.map((i) => data(i).data)); },
    loader() {},
    onData(fn) { subs.push(fn); lastW = document.getElementById('dash-root').clientWidth; fn(); },
    colors: [1, 2, 3, 4, 5, 6, 7, 8].map((i) => `var(--cds-chart-categorical-${i})`),
    refresh() {}, params: () => ({}), setParams() {}, resetParams() {},
    setLink(name) { try { history.replaceState(null, '', '#' + name); } catch (e) {} },
  };
})();
"""

html = f"""<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>WIG20 i sektory GPW 2016–2026</title>
<meta name="description" content="Interaktywne wyniki analizy losowości i sezonowości WIG20 oraz sektorów GPW w cyklu koniunkturalnym.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700&display=swap">
<style>{TOKENS}</style>
<script>{D3.read_text(encoding="utf-8")}</script>
</head>
<body>
<header class="uw-band"><div class="uw-band-inner"><span class="uw-faculty">Wydział Zarządzania</span><span class="uw-uni">Uniwersytet Warszawski</span><span class="uw-course">Analiza techniczna i fundamentalna · projekt zaliczeniowy</span></div></header>
<script type="application/json" id="dash-data">{safe_script(json.dumps(data, ensure_ascii=False, separators=(",", ":")))}</script>
<div id="dash-root">
<script>{SHIM}</script>
{page}
</div>
<footer class="uw-foot">Projekt studencki przygotowany w ramach zajęć na Wydziale Zarządzania UW. Kolorystyka i krój pisma wg Brandbooka WZ UW.</footer>
</body>
</html>
"""

OUTPUT.write_text(html, encoding="utf-8")
print(f"Zapisano {OUTPUT} ({OUTPUT.stat().st_size / 1024:.0f} KB)")
