"""Sincroniza default_state.js (dashboard v7) con los snapshots validados de tracking/data.

Uso: python3 tracking/sync_default_state.py tracking/data/ibk_2026-10-04.json tracking/data/tyba_2026-10-02.json
- Reescribe positions, cash, prevClose y fx; agrega dataVersion.
- Agrega el aporte de mayo-2026 y los cierres realizados posteriores a abril-2026.
- Las transacciones históricas (hasta 22-abr-2026) no se tocan.
Las posiciones en AUD/CAD se guardan en USD (costo y mark × FX de IBKR del pull).
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DS = ROOT / "default_state.js"
ibk, tyba = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
fx = ibk["fx_to_usd"]
DATA_VERSION = "2026-10-02"

NOTES = {"RIOFF": "Junior - oro/cobre (Rio2)", "TSO": "Junior - oro (ASX, AUD)", "SRGXF": "Junior - cobre (Surge)",
         "GLGDF": "Junior - oro/plata (GoGold)", "QUEXF": "Junior - litio (Q2 Metals)", "GAL": "Junior - oro (TSXV, CAD)",
         "SMI": "Junior - oro (ASX, AUD)", "VOO": "Core S&P 500", "NVDA": "AI semis", "MSFT": "Tech mega-cap",
         "META": "Tech mega-cap", "B": "Oro large-cap (Barrick)", "GOOGL": "Tech mega-cap",
         "BMM": "Junior - metales (Blue Moon)", "PPTA": "Junior - oro/antimonio (Perpetua)", "IONS": "Biotecnología"}
r6 = lambda x: float(f"{x:.6f}")

pos, prev = [], {}
for p in tyba["positions"]:
    pos.append(dict(ticker=p["ticker"], broker="TYBA", shares=p["qty"], costAvg=r6(p["cost"]/p["qty"]), note=NOTES[p["ticker"]]))
    prev[p["ticker"]] = r6(p["price"])
for p in ibk["positions"]:
    f = fx[p["ccy"]]
    d = dict(ticker=p["ticker"], broker="IBK", shares=p["qty"], costAvg=r6(p["avg"]*f), note=NOTES[p["ticker"]])
    if p["ccy"] != "USD": d["ccy"] = p["ccy"]
    pos.append(d)
    prev[p["ticker"]] = r6(p["price"]*f)

def js_obj(d):
    return "{" + ", ".join(f"{k}:{json.dumps(v, ensure_ascii=False).replace(chr(34), chr(39))}" for k, v in d.items()) + "}"

src = DS.read_text()
pos_js = "  positions: [\n" + "".join(f"    {js_obj(d)},\n" for d in pos) + "  ],"
src = re.sub(r"  positions: \[\n.*?\n  \],", lambda m: pos_js, src, count=1, flags=re.S)

# Aporte externo neto de may-2026 (+$11,000): serie mensual 'cap' del brief; el 27-may el NAV de IBK
# salta ~$15k con TWR plano (Portfolio Analyst), así que se fecha ese día.
if "id:'f21'" not in src:
    src = src.replace("    {id:'f20', date:'2026-04-20', broker:'IBK', amount:3500, note:''},\n",
        "    {id:'f20', date:'2026-04-20', broker:'IBK', amount:3500, note:''},\n"
        "    {id:'f21', date:'2026-05-27', broker:'IBK', amount:11000, note:'Aporte neto may-2026 (serie de capital del resumen matutino; fecha = salto de NAV en IBKR PA)'},\n", 1)

# Resultado realizado IBK posterior al 22-abr-2026 (brief: ops.cierres, IBKR)
closed_new = [("RIOFF", 1519.75, "2026-09-22"), ("TSO", -5.55, "2026-09-03"), ("RIOFF", 1407.39, "2026-08-17"),
              ("RIOFF", 64.03, "2026-08-13"), ("MSFT", -86.85, "2026-06-25")]
if "date:'2026-09-22'" not in src:
    block = "".join(f"    {{ticker:'{t}', pnl:{p}, date:'{d}'}},\n" for t, p, d in closed_new)
    src = src.replace("  closedPositions: [\n", "  closedPositions: [\n" + block, 1)

cash = {"TYBA": tyba["cash_usd"], "IBK": ibk["summary"]["total_cash_value"]}
src = re.sub(r"  cash: \{[^}]*\},", f"  cash: {{TYBA:{cash['TYBA']}, IBK:{cash['IBK']}}},", src, count=1)
prev_js = "  prevClose: {\n" + "".join(f"    {t}: {v},\n" for t, v in prev.items()) + "  },"
src = re.sub(r"  prevClose: \{\n.*?\n  \},", lambda m: prev_js, src, count=1, flags=re.S)
fx_js = f"  fx: {{AUD:{fx['AUD']}, CAD:{fx['CAD']}}},"
if "  fx: {" in src:
    src = re.sub(r"  fx: \{[^}]*\},", fx_js, src, count=1)
else:
    src = src.replace("  priceOverrides: {},", fx_js + "\n  priceOverrides: {},", 1)
if "dataVersion" not in src:
    src = src.replace("const DEFAULT_STATE = {\n", f"const DEFAULT_STATE = {{\n  dataVersion: '{DATA_VERSION}',\n", 1)
else:
    src = re.sub(r"dataVersion: '[^']*'", f"dataVersion: '{DATA_VERSION}'", src, count=1)
DS.write_text(src)
print(f"default_state.js: {len(pos)} posiciones, cash {cash}, fx {fx_js.strip()}")
