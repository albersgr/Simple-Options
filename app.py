"""
Options Strategy Calculator — Flask + Plotly web app.
Run:  python3 app.py
Open: http://localhost:5000
"""

from flask import Flask, jsonify, request, render_template_string
import numpy as np
import json

app = Flask(__name__)

# ── Option payoff ─────────────────────────────────────────────────────────────

def payoff(opt_type: str, S: np.ndarray, strike: float, premium: float) -> np.ndarray:
    if opt_type == "Long Call":
        return np.maximum(0, S - strike) - premium
    elif opt_type == "Short Call":
        return premium - np.maximum(0, S - strike)
    elif opt_type == "Long Put":
        return np.maximum(0, strike - S) - premium
    elif opt_type == "Short Put":
        return premium - np.maximum(0, strike - S)
    return np.zeros_like(S)


PRESETS = {
    "Long Call": [
        {"type": "Long Call", "strike": 100, "premium": 5, "qty": 1}
    ],
    "Short Call": [
        {"type": "Short Call", "strike": 100, "premium": 5, "qty": 1}
    ],
    "Long Put": [
        {"type": "Long Put", "strike": 100, "premium": 5, "qty": 1}
    ],
    "Short Put": [
        {"type": "Short Put", "strike": 100, "premium": 5, "qty": 1}
    ],
    "Bull Call Spread": [
        {"type": "Long Call",  "strike": 95,  "premium": 8, "qty": 1},
        {"type": "Short Call", "strike": 105, "premium": 3, "qty": 1},
    ],
    "Bear Put Spread": [
        {"type": "Long Put",  "strike": 105, "premium": 8, "qty": 1},
        {"type": "Short Put", "strike": 95,  "premium": 3, "qty": 1},
    ],
    "Straddle": [
        {"type": "Long Call", "strike": 100, "premium": 5, "qty": 1},
        {"type": "Long Put",  "strike": 100, "premium": 5, "qty": 1},
    ],
    "Strangle": [
        {"type": "Long Call", "strike": 105, "premium": 3, "qty": 1},
        {"type": "Long Put",  "strike": 95,  "premium": 3, "qty": 1},
    ],
    "Covered Call": [
        {"type": "Short Call", "strike": 105, "premium": 5, "qty": 1},
    ],
    "Iron Condor": [
        {"type": "Long Put",   "strike": 90,  "premium": 2, "qty": 1},
        {"type": "Short Put",  "strike": 95,  "premium": 4, "qty": 1},
        {"type": "Short Call", "strike": 105, "premium": 4, "qty": 1},
        {"type": "Long Call",  "strike": 110, "premium": 2, "qty": 1},
    ],
    "Butterfly Call": [
        {"type": "Long Call",  "strike": 90,  "premium": 12, "qty": 1},
        {"type": "Short Call", "strike": 100, "premium": 5,  "qty": 2},
        {"type": "Long Call",  "strike": 110, "premium": 1,  "qty": 1},
    ],
}

TYPE_COLORS = {
    "Long Call":  "#60a5fa",
    "Short Call": "#f87171",
    "Long Put":   "#4ade80",
    "Short Put":  "#fb923c",
}

# ── API ───────────────────────────────────────────────────────────────────────

@app.route("/api/chart", methods=["POST"])
def chart():
    data  = request.get_json()
    legs  = data.get("legs", [])
    s_min = float(data.get("s_min", 50))
    s_max = float(data.get("s_max", 150))

    S     = np.linspace(s_min, s_max, 600)
    total = np.zeros_like(S)
    traces = []

    for leg in legs:
        p = payoff(leg["type"], S, float(leg["strike"]), float(leg["premium"])) * int(leg["qty"])
        total += p
        color = TYPE_COLORS.get(leg["type"], "#e2e8f0")
        label = f"{leg['qty']}× {leg['type']}  K={leg['strike']}  Prima={leg['premium']}"
        traces.append({
            "x": S.tolist(), "y": p.tolist(),
            "type": "scatter", "mode": "lines",
            "name": label,
            "line": {"color": color, "width": 1.5, "dash": "dot"},
            "opacity": 0.65,
        })

    if legs:
        # total line
        traces.append({
            "x": S.tolist(), "y": total.tolist(),
            "type": "scatter", "mode": "lines",
            "name": "P&L Total",
            "line": {"color": "#f9a8d4", "width": 3},
        })
        # profit fill
        profit_y = np.where(total >= 0, total, 0)
        loss_y   = np.where(total <  0, total, 0)
        traces.append({
            "x": S.tolist(), "y": profit_y.tolist(),
            "type": "scatter", "fill": "tozeroy",
            "fillcolor": "rgba(74,222,128,0.15)",
            "line": {"color": "rgba(0,0,0,0)", "width": 0},
            "showlegend": False, "hoverinfo": "skip",
        })
        traces.append({
            "x": S.tolist(), "y": loss_y.tolist(),
            "type": "scatter", "fill": "tozeroy",
            "fillcolor": "rgba(248,113,113,0.15)",
            "line": {"color": "rgba(0,0,0,0)", "width": 0},
            "showlegend": False, "hoverinfo": "skip",
        })

        # breakeven
        signs    = np.sign(total)
        crossings = np.where(np.diff(signs))[0]
        annotations = []
        for i in crossings:
            be = S[i] + (S[i+1] - S[i]) * (-total[i]) / (total[i+1] - total[i])
            traces.append({
                "x": [be, be], "y": [float(total.min()) * 1.1, float(total.max()) * 1.1],
                "type": "scatter", "mode": "lines",
                "line": {"color": "#fbbf24", "width": 1.2, "dash": "dot"},
                "showlegend": False, "hoverinfo": "skip",
            })
            annotations.append({
                "x": be, "y": 0,
                "text": f"BE: {be:.2f}",
                "showarrow": True, "arrowhead": 2,
                "arrowcolor": "#fbbf24",
                "font": {"color": "#fbbf24", "size": 11},
                "bgcolor": "#1e1e2e", "bordercolor": "#fbbf24",
                "ax": 0, "ay": -36,
            })
    else:
        annotations = []

    layout = {
        "paper_bgcolor": "#0f0f1a",
        "plot_bgcolor":  "#181825",
        "font": {"color": "#cdd6f4", "family": "Inter, Segoe UI, sans-serif"},
        "title": {
            "text": "Diagrama de rentabilidad a vencimiento",
            "font": {"size": 16, "color": "#cdd6f4"},
        },
        "xaxis": {
            "title": "Precio del subyacente (S)",
            "gridcolor": "#313244", "zerolinecolor": "#585b70",
            "range": [s_min, s_max],
        },
        "yaxis": {
            "title": "Beneficio / Pérdida",
            "gridcolor": "#313244", "zerolinecolor": "#a6adc8",
            "zerolinewidth": 1.5,
        },
        "legend": {
            "bgcolor": "#1e1e2e", "bordercolor": "#45475a",
            "borderwidth": 1, "font": {"size": 11},
        },
        "hovermode": "x unified",
        "margin": {"l": 60, "r": 20, "t": 50, "b": 50},
        "annotations": annotations,
    }

    return jsonify({"traces": traces, "layout": layout})


@app.route("/api/presets")
def presets():
    return jsonify(PRESETS)


# ── HTML ──────────────────────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Options Strategy Calculator</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg0: #0f0f1a; --bg1: #1e1e2e; --bg2: #313244; --bg3: #45475a;
    --txt: #cdd6f4; --txt2: #a6adc8; --accent: #cba6f7; --blue: #89b4fa;
    --green: #a6e3a1; --red: #f38ba8; --yellow: #f9e2af; --orange: #fab387;
    --lc: #60a5fa; --sc: #f87171; --lp: #4ade80; --sp: #fb923c;
  }
  body { background: var(--bg0); color: var(--txt); font-family: 'Inter', 'Segoe UI', sans-serif;
         font-size: 14px; min-height: 100vh; }
  h1 { color: var(--accent); font-size: 1.4rem; font-weight: 700; padding: 18px 24px 0;
       letter-spacing: .5px; }
  h1 span { color: var(--txt2); font-size: .9rem; font-weight: 400; margin-left: 10px; }

  .layout { display: flex; gap: 16px; padding: 16px 24px; height: calc(100vh - 62px); }

  /* ── Panel ── */
  .panel { width: 320px; min-width: 280px; display: flex; flex-direction: column; gap: 14px;
           overflow-y: auto; padding-right: 4px; }
  section { background: var(--bg1); border: 1px solid var(--bg3); border-radius: 10px; padding: 14px; }
  section h2 { font-size: .8rem; font-weight: 600; color: var(--accent); text-transform: uppercase;
               letter-spacing: 1px; margin-bottom: 10px; }

  /* presets */
  .presets { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 5px; }
  .preset-btn { background: var(--bg2); border: 1px solid var(--bg3); color: var(--txt);
                border-radius: 6px; padding: 5px 4px; font-size: 11px; cursor: pointer;
                transition: background .15s; text-align: center; }
  .preset-btn:hover { background: var(--bg3); }

  /* form */
  .form-grid { display: grid; grid-template-columns: 90px 1fr; gap: 7px 8px; align-items: center; }
  label { color: var(--txt2); font-size: 13px; }
  select, input[type=number], input[type=text] {
    background: var(--bg2); border: 1px solid var(--bg3); color: var(--txt);
    border-radius: 6px; padding: 6px 9px; width: 100%; font-size: 13px; outline: none;
    transition: border-color .15s;
  }
  select:focus, input:focus { border-color: var(--accent); }
  select option { background: var(--bg2); }

  .type-indicator { display: flex; gap: 6px; margin-bottom: 10px; flex-wrap: wrap; }
  .type-badge { font-size: 11px; padding: 2px 8px; border-radius: 99px; font-weight: 600; }
  .badge-lc { background: rgba(96,165,250,.18); color: var(--lc); }
  .badge-sc { background: rgba(248,113,113,.18); color: var(--sc); }
  .badge-lp { background: rgba(74,222,128,.18); color: var(--lp); }
  .badge-sp { background: rgba(251,146,60,.18); color: var(--sp); }

  .btn { width: 100%; padding: 8px; border: none; border-radius: 7px; font-size: 13px;
         font-weight: 600; cursor: pointer; transition: opacity .15s; margin-top: 2px; }
  .btn:hover { opacity: .85; }
  .btn-add  { background: var(--accent); color: var(--bg0); }
  .btn-plot { background: var(--blue);   color: var(--bg0); margin-top: 6px; }
  .btn-clear { background: var(--bg3); color: var(--txt); }
  .btn-danger { background: var(--red); color: var(--bg0); font-size: 12px; }

  /* range */
  .range-row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .range-row div { display: flex; flex-direction: column; gap: 4px; }
  .range-row label { font-size: 12px; color: var(--txt2); }

  /* legs table */
  table { width: 100%; border-collapse: collapse; font-size: 12px; }
  th { color: var(--txt2); font-weight: 600; text-align: left; padding: 4px 6px;
       border-bottom: 1px solid var(--bg3); }
  td { padding: 5px 6px; border-bottom: 1px solid var(--bg2); }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: var(--bg2); }
  .del-btn { background: none; border: none; color: var(--red); cursor: pointer;
             font-size: 15px; padding: 0 4px; line-height: 1; }
  .del-btn:hover { opacity: .7; }
  .empty-msg { color: var(--txt2); font-size: 12px; text-align: center; padding: 10px 0; }

  /* stats */
  .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .stat { background: var(--bg2); border-radius: 7px; padding: 8px 10px; }
  .stat-label { font-size: 11px; color: var(--txt2); margin-bottom: 3px; }
  .stat-value { font-size: 15px; font-weight: 700; }
  .profit { color: var(--green); }
  .loss   { color: var(--red); }
  .neutral { color: var(--txt); }

  /* chart */
  .chart-wrap { flex: 1; background: var(--bg1); border: 1px solid var(--bg3);
                border-radius: 10px; overflow: hidden; min-width: 0; }
  #chart { width: 100%; height: 100%; }
</style>
</head>
<body>

<h1>Options Strategy Calculator <span>— P&L a vencimiento</span></h1>

<div class="layout">
  <div class="panel">

    <!-- Presets -->
    <section>
      <h2>Estrategias</h2>
      <div class="presets" id="preset-grid"></div>
    </section>

    <!-- Add leg form -->
    <section>
      <h2>Añadir posición</h2>
      <div class="type-indicator">
        <span class="type-badge badge-lc">Long Call</span>
        <span class="type-badge badge-sc">Short Call</span>
        <span class="type-badge badge-lp">Long Put</span>
        <span class="type-badge badge-sp">Short Put</span>
      </div>
      <div class="form-grid">
        <label for="sel-type">Tipo</label>
        <select id="sel-type">
          <option>Long Call</option>
          <option>Short Call</option>
          <option>Long Put</option>
          <option>Short Put</option>
        </select>

        <label for="inp-strike">Strike (K)</label>
        <input id="inp-strike" type="number" value="100" min="0" step="1">

        <label for="inp-premium">Prima</label>
        <input id="inp-premium" type="number" value="5" min="0" step="0.5">

        <label for="inp-qty">Cantidad</label>
        <input id="inp-qty" type="number" value="1" min="1" step="1">
      </div>
      <button class="btn btn-add" onclick="addLeg()">+ Añadir posición</button>
    </section>

    <!-- Active legs -->
    <section>
      <h2>Posiciones activas</h2>
      <div id="legs-container">
        <p class="empty-msg">Sin posiciones. Añade una o carga una estrategia.</p>
      </div>
      <button class="btn btn-clear" onclick="clearLegs()" style="margin-top:8px">Limpiar todo</button>
    </section>

    <!-- Price range + plot -->
    <section>
      <h2>Rango del subyacente</h2>
      <div class="range-row">
        <div><label for="inp-smin">Mínimo</label>
             <input id="inp-smin" type="number" value="50" step="5"></div>
        <div><label for="inp-smax">Máximo</label>
             <input id="inp-smax" type="number" value="150" step="5"></div>
      </div>
      <button class="btn btn-plot" onclick="updateChart()">Actualizar gráfico</button>
    </section>

    <!-- Stats -->
    <section>
      <h2>Estadísticas</h2>
      <div class="stats-grid" id="stats-grid">
        <div class="stat"><div class="stat-label">Máx. beneficio</div>
          <div class="stat-value neutral" id="stat-max">—</div></div>
        <div class="stat"><div class="stat-label">Máx. pérdida</div>
          <div class="stat-value neutral" id="stat-min">—</div></div>
        <div class="stat"><div class="stat-label">Breakeven(s)</div>
          <div class="stat-value neutral" id="stat-be">—</div></div>
        <div class="stat"><div class="stat-label">Prima neta</div>
          <div class="stat-value neutral" id="stat-cost">—</div></div>
      </div>
    </section>

  </div><!-- /panel -->

  <div class="chart-wrap">
    <div id="chart"></div>
  </div>
</div>

<script>
let legs = [];

// ── Presets ──────────────────────────────────────────────────────────────────
fetch('/api/presets').then(r => r.json()).then(presets => {
  const grid = document.getElementById('preset-grid');
  Object.keys(presets).forEach(name => {
    const btn = document.createElement('button');
    btn.className = 'preset-btn';
    btn.textContent = name;
    btn.onclick = () => { legs = presets[name].map(l => ({...l})); renderLegs(); updateChart(); };
    grid.appendChild(btn);
  });
});

// ── Legs ─────────────────────────────────────────────────────────────────────
function addLeg() {
  const type    = document.getElementById('sel-type').value;
  const strike  = parseFloat(document.getElementById('inp-strike').value);
  const premium = parseFloat(document.getElementById('inp-premium').value);
  const qty     = parseInt(document.getElementById('inp-qty').value);
  if (isNaN(strike) || isNaN(premium) || isNaN(qty) || qty < 1 || premium < 0 || strike < 0) {
    alert('Valores inválidos. Strike y prima deben ser ≥ 0 y cantidad ≥ 1.'); return;
  }
  legs.push({ type, strike, premium, qty });
  renderLegs();
  updateChart();
}

function removeLeg(i) { legs.splice(i, 1); renderLegs(); updateChart(); }
function clearLegs()  { legs = []; renderLegs(); updateChart(); }

const TYPE_COLORS = {
  'Long Call': '#60a5fa', 'Short Call': '#f87171',
  'Long Put':  '#4ade80', 'Short Put':  '#fb923c',
};

function renderLegs() {
  const el = document.getElementById('legs-container');
  if (!legs.length) {
    el.innerHTML = '<p class="empty-msg">Sin posiciones. Añade una o carga una estrategia.</p>';
    return;
  }
  let html = '<table><thead><tr><th>Tipo</th><th>K</th><th>Prima</th><th>Qty</th><th></th></tr></thead><tbody>';
  legs.forEach((l, i) => {
    const c = TYPE_COLORS[l.type] || '#cdd6f4';
    html += `<tr>
      <td style="color:${c};font-weight:600">${l.type}</td>
      <td>${l.strike}</td><td>${l.premium}</td><td>${l.qty}</td>
      <td><button class="del-btn" onclick="removeLeg(${i})">×</button></td>
    </tr>`;
  });
  html += '</tbody></table>';
  el.innerHTML = html;
}

// ── Chart ─────────────────────────────────────────────────────────────────────
function updateChart() {
  const s_min = parseFloat(document.getElementById('inp-smin').value) || 50;
  const s_max = parseFloat(document.getElementById('inp-smax').value) || 150;

  fetch('/api/chart', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ legs, s_min, s_max }),
  })
  .then(r => r.json())
  .then(data => {
    Plotly.react('chart', data.traces, data.layout, {
      responsive: true,
      displayModeBar: true,
      modeBarButtonsToRemove: ['select2d','lasso2d','autoScale2d'],
      displaylogo: false,
    });
    updateStats(data.traces, s_min, s_max);
  });
}

function updateStats(traces, s_min, s_max) {
  const totalTrace = traces.find(t => t.name === 'P&L Total');
  if (!totalTrace) {
    ['stat-max','stat-min','stat-be','stat-cost'].forEach(id => {
      const el = document.getElementById(id);
      el.textContent = '—'; el.className = 'stat-value neutral';
    });
    return;
  }
  const y = totalTrace.y;
  const maxP = Math.max(...y);
  const minP = Math.min(...y);

  // cost
  let netPremium = 0;
  legs.forEach(l => {
    if (l.type.startsWith('Long'))  netPremium -= l.premium * l.qty;
    else                             netPremium += l.premium * l.qty;
  });

  // breakevens from annotations
  const beTraces = traces.filter(t => !t.name && t.x && t.x.length === 2 && t.x[0] === t.x[1]);
  const bes = beTraces.map(t => parseFloat(t.x[0]).toFixed(2));

  const setEl = (id, val, cls) => {
    const el = document.getElementById(id);
    el.textContent = val;
    el.className = `stat-value ${cls}`;
  };

  setEl('stat-max', maxP === Infinity ? '∞' : maxP.toFixed(2), maxP > 0 ? 'profit' : 'loss');
  setEl('stat-min', minP === -Infinity ? '-∞' : minP.toFixed(2), minP >= 0 ? 'profit' : 'loss');
  setEl('stat-be',  bes.length ? bes.join(', ') : 'Ninguno', 'neutral');
  setEl('stat-cost', netPremium.toFixed(2), netPremium >= 0 ? 'profit' : 'loss');
}

// Initial empty chart
updateChart();
</script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(HTML)


if __name__ == "__main__":
    print("\n  Options Strategy Calculator")
    print("  ─────────────────────────────")
    print("  Abre en tu navegador: http://localhost:5000\n")
    app.run(debug=False, port=5000)
