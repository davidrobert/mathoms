#!/usr/bin/env python3
"""
E5-regen: Aplica melhorias v3 ao relatório existente.

Abordagem: pega o relatório funcional e injeta as melhorias
(dark mode, collapse, modo tático, theme toggle, labels corrigidos).
NÃO usa template — preserva todo o HTML/JS/canvas original.

Uso: python3 scripts/e5_regen.py [--source arquivo_base.html]
     Se --source não for especificado, modifica o relatório atual in-place.
"""

import re
import os
import sys
import shutil
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT = os.path.join(BASE, 'output', 'relatorio_202604.html')

# Parse optional --source argument
source = REPORT
if '--source' in sys.argv:
    idx = sys.argv.index('--source')
    if idx + 1 < len(sys.argv):
        source = sys.argv[idx + 1]
        if not os.path.isabs(source):
            source = os.path.join(BASE, source)

with open(source, 'r', encoding='utf-8') as f:
    html = f.read()

# Archive before modifying
ts = datetime.now().strftime('%Y%m%d_%H%M%S')
archive = REPORT.replace('.html', f'_pre_regen_{ts}.html')
if os.path.exists(REPORT):
    shutil.copy2(REPORT, archive)
    print(f"[OK] Archived: {os.path.basename(archive)}")

changes = 0

# ─── 1. COVER: "Titular" → "Família" ────────────────────────────────
if 'cover-meta-label">Titular' in html:
    html = html.replace('cover-meta-label">Titular', 'cover-meta-label">Família')
    changes += 1
    print("[OK] Titular → Família")

# ─── 2. COVER: "Versão do Prompt" → "Versão Manual Operações" ───────
if 'Versão do Prompt' in html:
    html = html.replace('Versão do Prompt', 'Versão Manual Operações')
    changes += 1
    print("[OK] Versão do Prompt → Versão Manual Operações")

# ─── 3. COVER: Version value → 3.0 ──────────────────────────────────
html = re.sub(
    r'(Versão Manual Operações</div>\s*<div class="cover-meta-value">)[^<]*(</div>)',
    r'\g<1>v3.0\2', html, count=1
)
changes += 1

# ─── 4. COVER: Family name ──────────────────────────────────────────
html = re.sub(
    r'(cover-meta-label">Família</div>\s*<div class="cover-meta-value">)[^<]*(</div>)',
    r'\g<1>Ferreira Campos\2', html, count=1
)
changes += 1
print("[OK] Cover family name: Ferreira Campos")

# ─── 5. COVER: Update timestamp ─────────────────────────────────────
now = datetime.now()
data_hora = now.strftime('%d/%m/%Y — %H:%M')
html = re.sub(
    r'(Data e Hora de Geração</div>\s*<div class="cover-meta-value">)[^<]*(</div>)',
    rf'\g<1>{data_hora}\2', html, count=1
)
changes += 1
print(f"[OK] Timestamp: {data_hora}")

# ─── 6. DARK MODE CSS ───────────────────────────────────────────────
DARK_CSS = """
[data-theme="dark"] {
  --color-bg: #0F172A;
  --color-surface: #1E293B;
  --color-text: #E2E8F0;
  --color-text-muted: #94A3B8;
  --color-border: #334155;
  --color-primary: #2E86AB;
  --color-light: #1E3A5F;
}
[data-theme="dark"] .card, [data-theme="dark"] .familia-card {
  background: var(--color-surface) !important; border-color: var(--color-border) !important;
}
[data-theme="dark"] .card-feature, [data-theme="dark"] .card-success {
  background: var(--color-surface) !important;
}
[data-theme="dark"] table tr:nth-child(even) { background: #1A2332 !important; }
[data-theme="dark"] table tr:hover { background: #243447 !important; }
[data-theme="dark"] table th { background: #1E3A5F !important; color: #E2E8F0 !important; }
[data-theme="dark"] .td-total { background: #1A2332 !important; }
[data-theme="dark"] table td { border-color: #334155 !important; }
[data-theme="dark"] .alert-danger { background: #2D1B1B !important; color: #FCA5A5 !important; }
[data-theme="dark"] .alert-warning { background: #2D2410 !important; color: #FCD34D !important; }
[data-theme="dark"] .alert-success { background: #1A2D1A !important; color: #86EFAC !important; }
[data-theme="dark"] .alert-info { background: #1A2440 !important; color: #93C5FD !important; }
[data-theme="dark"] .badge-green { background: #16533480 !important; color: #86EFAC !important; }
[data-theme="dark"] .badge-red { background: #991B1B80 !important; color: #FCA5A5 !important; }
[data-theme="dark"] .badge-yellow { background: #92400E80 !important; color: #FCD34D !important; }
[data-theme="dark"] .badge-blue { background: #1E40AF80 !important; color: #93C5FD !important; }
[data-theme="dark"] .section-summary { background: #1A2440 !important; color: #CBD5E1 !important; }
[data-theme="dark"] .chart-conclusion, [data-theme="dark"] .chart-note { background: #1A2332 !important; color: #CBD5E1 !important; }
[data-theme="dark"] .card h3 { color: #E2E8F0 !important; border-bottom-color: #334155 !important; }
[data-theme="dark"] .chart-context { color: #94A3B8 !important; }
[data-theme="dark"] .chart-conclusion { background: #1A2440 !important; border-left-color: #2E86AB !important; }
[data-theme="dark"] .kpi-grid .kpi-card { background: var(--color-surface) !important; border-color: var(--color-border) !important; }
[data-theme="dark"] .kpi-value { color: var(--color-text) !important; }
[data-theme="dark"] .kpi-value.blue { color: #60A5FA !important; }
[data-theme="dark"] .kpi-value.green { color: #4ADE80 !important; }
[data-theme="dark"] .kpi-value.red { color: #F87171 !important; }
[data-theme="dark"] .kpi-sub { color: var(--color-text-muted) !important; }
[data-theme="dark"] .export-toolbar { background: linear-gradient(135deg, #0B1929, #132337) !important; }
[data-theme="dark"] strong { color: #F1F5F9; }
[data-theme="dark"] h1, [data-theme="dark"] h2, [data-theme="dark"] h3 { color: #F1F5F9 !important; }
[data-theme="dark"] .section-header h1 { color: #F1F5F9 !important; }
[data-theme="dark"] .container.section { background: var(--color-surface); border-color: var(--color-border); }
[data-theme="dark"] .dash-section { background: var(--color-surface) !important; }
[data-theme="dark"] .dash-kpi { background: var(--color-surface) !important; border-color: var(--color-border) !important; }
[data-theme="dark"] .dash-kpi-label { color: var(--color-text-muted) !important; }
[data-theme="dark"] .dash-kpi-value { color: var(--color-text) !important; }
[data-theme="dark"] .dash-kpi-value.ok { color: #4ADE80 !important; }
[data-theme="dark"] .dash-kpi-value.alert { color: #F87171 !important; }
[data-theme="dark"] .progress-bar { background: #334155 !important; }
[data-theme="dark"] [style*="background: #EFF6FF"],
[data-theme="dark"] [style*="background:#EFF6FF"],
[data-theme="dark"] [style*="background: linear-gradient(135deg, #F8FAFC"],
[data-theme="dark"] [style*="background: linear-gradient(135deg, #EFF6FF"],
[data-theme="dark"] [style*="background: linear-gradient(135deg, #F0FDF4"] {
  background: var(--color-surface) !important;
}
[data-theme="dark"] table.table-compare td:nth-child(2) { background: #2D1B1B !important; }
[data-theme="dark"] table.table-compare td:nth-child(3) { background: #1A2D1A !important; }
"""

# Remove existing dark mode CSS block if present, then always inject fresh
if '[data-theme="dark"]' in html:
    # Remove old dark mode block (everything from first [data-theme="dark"] to the line before next non-dark rule)
    html = re.sub(r'\[data-theme="dark"\][^\n]*\n', '', html)
    print("[OK] Removed old dark mode CSS")

# Insert after :root { ... } block
html = re.sub(
    r'(--font-body:[^}]+\})',
    r'\1\n' + DARK_CSS,
    html, count=1
)
changes += 1
print("[OK] Dark mode CSS injected (fresh)")

# ─── 7. COLLAPSE CSS ────────────────────────────────────────────────
COLLAPSE_CSS = """
.section-header { cursor: pointer; user-select: none; display: flex; align-items: center; justify-content: space-between; }
.section-header .collapse-icon { transition: transform 0.3s; font-size: 14px; color: var(--color-text-muted); margin-left: 8px; }
.section-header.collapsed .collapse-icon { transform: rotate(-90deg); }
.section-content { max-height: 50000px; overflow: hidden; transition: max-height 0.4s ease; }
.section-content.collapsed { max-height: 0; overflow: hidden; padding: 0; }
"""

if 'collapse-icon' not in html:
    html = html.replace('</style>', COLLAPSE_CSS + '\n</style>', 1)
    changes += 1
    print("[OK] Collapse CSS injected")

# ─── 8. THEME TOGGLE CSS ────────────────────────────────────────────
THEME_CSS = """
.theme-toggle { display: flex; gap: 2px; margin-left: 12px; padding: 6px 0; flex-shrink: 0; }
.theme-btn { background: transparent; border: 1px solid rgba(255,255,255,0.15); color: rgba(255,255,255,0.6); padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 12px; transition: all 0.2s; }
.theme-btn:hover { background: rgba(255,255,255,0.1); color: #fff; }
.theme-btn.active { background: rgba(255,255,255,0.15); color: #fff; border-color: rgba(255,255,255,0.3); }
"""

if 'theme-toggle' not in html:
    html = html.replace('</style>', THEME_CSS + '\n</style>', 1)
    changes += 1
    print("[OK] Theme toggle CSS injected")

# ─── 9. CHART CONTAINER CARD STYLING ────────────────────────────────
CHART_CONTAINER_CSS = """
.chart-container {
  position:relative; margin:20px 0; max-width:100%;
  background: var(--color-surface); border-radius:12px; padding:24px;
  box-shadow:0 1px 3px rgba(0,0,0,0.06); border:1px solid var(--color-border);
}
.chart-container canvas { max-height:550px; min-height:350px; }
.chart-row { display:grid; grid-template-columns: 1fr 1fr; gap:20px; margin:20px 0; }
.chart-row .chart-container { margin:0; }
"""

# Check if chart-container already has card styling (box-shadow)
existing_cc = re.findall(r'\.chart-container\s*\{[^}]+\}', html)
needs_fix = True
if existing_cc:
    if 'box-shadow' in existing_cc[0]:
        needs_fix = False
        print("[SKIP] Chart container card styling already present")

if needs_fix:
    # Remove existing minimal .chart-container rule if present
    if existing_cc:
        html = html.replace(existing_cc[0], '')
    html = html.replace('</style>', CHART_CONTAINER_CSS + '\n</style>', 1)
    changes += 1
    print("[OK] Chart container card styling injected")

# ─── 10. CARD TITLE STYLING (.card h3, .chart-context, .chart-conclusion) ──
CARD_TITLE_CSS = """
.card h3 { font-family: var(--font-display); font-size:15px; font-weight:700;
  color: var(--color-primary); margin:0 0 14px 0; padding-bottom:10px;
  border-bottom:1px solid var(--color-border); line-height:1.4; }
.card h3 .icon-badge { margin-right:6px; }
.chart-context { font-size:13px; color: var(--color-text-muted); margin:0 0 12px 0;
  line-height:1.5; font-style:italic; }
.chart-conclusion { font-size:13px; color: var(--color-text); margin:12px 0 0 0;
  padding:10px 14px; background:#F0F9FF; border-radius:8px; border-left:3px solid var(--color-secondary);
  line-height:1.5; }
.chart-note { font-size:12px; color: var(--color-text-muted); margin:8px 0 0 0; font-style:italic; }
"""

# Check for light-mode .card h3 (has font-family, unlike dark mode variant)
style_block = html.split('</style>')[0]
has_card_h3_light = bool(re.search(r'\.card h3\s*\{[^}]*font-family', style_block))
if not has_card_h3_light:
    html = html.replace('</style>', CARD_TITLE_CSS + '\n</style>', 1)
    changes += 1
    print("[OK] Card title styling (.card h3, .chart-context, .chart-conclusion) injected")
else:
    print("[SKIP] Card title styling already present")

# ─── 11. MODE: Dashboard → Tático ────────────────────────────────────
if 'mode-dashboard' in html:
    html = html.replace('mode-dashboard', 'mode-tactical')
    html = html.replace("data-mode=\"dashboard\"", "data-mode=\"tactical\"")
    html = re.sub(r'Dashboard</button>', '⚡ Tático</button>', html)
    html = re.sub(r"data-target=\"dashboard\"", "data-target=\"tactical\"", html)
    html = re.sub(r"setMode\('dashboard'\)", "setMode('tactical')", html)
    changes += 1
    print("[OK] Dashboard → Tático")

# ─── 11. Family card: data-mode="both" → "strategic" ────────────────
# Fix the family section wrapper
html = re.sub(
    r'(<!-- PERFIL DA FAMÍLIA -->\s*<div )data-mode="both"',
    r'\1data-mode="strategic"',
    html, count=1
)
changes += 1

# ─── 12. Fix family card broken HTML ────────────────────────────────
# Fix: <div class="card" ...> data-mode="strategic" (text leak)
html = re.sub(
    r'(<div class="card"[^>]*>)\s*data-mode="strategic"',
    r'\1',
    html
)

# Ensure family card has title and class
if 'familia-card' not in html:
    html = re.sub(
        r'(<!-- PERFIL DA FAMÍLIA -->.*?<div class="card")([^>]*>)',
        r'\1 familia-card"\2\n  <div class="card-title" style="font-size:16px;">👨‍👩‍👦 A Família Ferreira Campos</div>',
        html, count=1, flags=re.DOTALL
    )

# ─── 13. "vs quinzena anterior" → "vs último período" ───────────────
html = html.replace('vs quinzena anterior', 'vs último período')

# ─── 14. THEME TOGGLE BUTTONS in nav ────────────────────────────────
THEME_BUTTONS = """<div class="theme-toggle" data-mode="both">
    <button class="theme-btn" data-theme="light" onclick="setTheme('light')" title="Modo Claro">☀️</button>
    <button class="theme-btn" data-theme="dark" onclick="setTheme('dark')" title="Modo Escuro">🌙</button>
    <button class="theme-btn active" data-theme="system" onclick="setTheme('system')" title="Sistema">⚙️</button>
  </div>"""

if 'theme-toggle' not in html or 'theme-btn' not in html.split('<script')[0]:
    # Find the mode-toggle div end and insert after it
    html = re.sub(
        r'(</div>\s*)(</div>\s*<!-- /nav-sticky -->)',
        r'\1' + THEME_BUTTONS + r'\n\2',
        html, count=1
    )
    if 'theme-toggle' in html.split('<script')[0]:
        changes += 1
        print("[OK] Theme toggle buttons injected in nav")

# ─── 15. Remove Export Prompt button ─────────────────────────────────
html = re.sub(r'<button[^>]*onclick="exportPrompt\(\)"[^>]*>.*?</button>', '', html)
html = re.sub(r'window\.exportPrompt\s*=\s*function\(\)\s*\{.*?\};', '', html, flags=re.DOTALL)
# Also remove base64 prompt data if present
html = re.sub(r"var\s+PROMPT_B64\s*=\s*'[^']*';", '', html)

# ─── 16. THEME JS ───────────────────────────────────────────────────
THEME_JS = """
<script>
var _currentThemePref = 'system';
function setTheme(theme) {
  _currentThemePref = theme;
  var html = document.documentElement;
  var resolved = theme;
  if (theme === 'system') {
    resolved = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  html.setAttribute('data-theme', resolved);
  document.querySelectorAll('.theme-btn').forEach(function(b) {
    b.classList.toggle('active', b.dataset.theme === theme);
  });
  var isDark = resolved === 'dark';
  var textColor = isDark ? '#94A3B8' : '#64748B';
  var gridColor = isDark ? '#334155' : '#E2E8F0';
  if (typeof Chart !== 'undefined' && Chart.instances) {
    Chart.defaults.color = textColor;
    Chart.defaults.borderColor = gridColor;
    Object.values(Chart.instances).forEach(function(chart) {
      if (chart && chart.options && chart.options.scales) {
        Object.values(chart.options.scales).forEach(function(s) {
          if (s.ticks) s.ticks.color = textColor;
          if (s.grid) s.grid.color = gridColor;
        });
      }
      if (chart && chart.options && chart.options.plugins && chart.options.plugins.legend && chart.options.plugins.legend.labels) {
        chart.options.plugins.legend.labels.color = textColor;
      }
      if (chart) chart.update('none');
    });
  }
}
(function() {
  document.documentElement.setAttribute('data-theme', 'light');
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
    if (_currentThemePref === 'system') setTheme('system');
  });
})();
</script>
"""

# Remove existing setTheme if present, then inject fresh
html = re.sub(r'<script>\s*var _currentThemePref.*?</script>', '', html, flags=re.DOTALL)
html = re.sub(r'<script>\s*function setTheme.*?</script>', '', html, flags=re.DOTALL)
html = html.replace('</body>', THEME_JS + '\n</body>')
changes += 1
print("[OK] Theme JS injected")

# ─── 17. COLLAPSE JS ────────────────────────────────────────────────
COLLAPSE_JS = """
<script>
document.querySelectorAll('.section-header').forEach(function(header) {
  if (!header.querySelector('.collapse-icon')) {
    var icon = document.createElement('span');
    icon.className = 'collapse-icon';
    icon.textContent = '▼';
    header.appendChild(icon);
  }
  var content = header.nextElementSibling;
  while (content && !content.classList.contains('section-summary') && content.tagName !== 'DIV') {
    content = content.nextElementSibling;
  }
  if (!content) return;
  // Wrap remaining section content for collapse
  header.addEventListener('click', function() {
    var siblings = [];
    var el = header.nextElementSibling;
    while (el) { siblings.push(el); el = el.nextElementSibling; }
    var isCollapsed = header.classList.contains('collapsed');
    header.classList.toggle('collapsed');
    siblings.forEach(function(s) { s.style.display = isCollapsed ? '' : 'none'; });
  });
});
</script>
"""

if 'collapse-icon' not in html.split('</style>')[-1] or 'initializeCollapsibleSections' not in html:
    # Remove any existing collapse JS
    html = re.sub(r'<script>\s*document\.querySelectorAll\(\'.section-header\'\)\.forEach.*?</script>', '', html, flags=re.DOTALL)
    html = html.replace('</body>', COLLAPSE_JS + '\n</body>')
    changes += 1
    print("[OK] Collapse JS injected")

# ─── 18. Make DATA global ───────────────────────────────────────────
if 'const DATA = JSON.parse' in html:
    html = html.replace(
        'const DATA = JSON.parse',
        'var DATA = JSON.parse'
    )
    changes += 1
    print("[OK] const DATA → var DATA (global)")

# ─── WRITE OUTPUT ────────────────────────────────────────────────────
with open(REPORT, 'w', encoding='utf-8') as f:
    f.write(html)

size_kb = os.path.getsize(REPORT) / 1024
print(f"\n[OK] Report written: {size_kb:.0f} KB → {REPORT}")
print(f"[OK] {changes} modifications applied")
print("Done! ✓")
