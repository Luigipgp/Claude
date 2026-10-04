"""Portafolio consolidado IBK + TYBA con controles.

Uso: python3 tracking/consolidated.py tracking/data/ibk_2026-10-04.json tracking/data/tyba_2026-10-02.json
IBK: posiciones del conector (marks del broker). TYBA: tenencias del bróker + último print IBKR.
"""
import json, sys
ibk, tyba = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
IPS = {"mineria_max": 0.70, "posicion_max": 0.30}
MINING = {"Minería junior", "Oro large-cap"}
fx = ibk["fx_to_usd"]; fails = []

def check(name, ok, detail=""):
    print(f"  [{'OK' if ok else 'FALLA'}] {name} {detail}")
    if not ok: fails.append(name)

rows = []
for p in ibk["positions"]:
    f = fx[p["ccy"]]
    rows.append(dict(t=p["ticker"], cust="IBK", sec="Minería junior", val=p["value"]*f, cost=p["avg"]*p["qty"]*f, hi=p["price"]/p["hi52"]-1))
for p in tyba["positions"]:
    rows.append(dict(t=p["ticker"], cust="TYBA", sec=p["sec"], val=p["qty"]*p["price"], cost=p["cost"], hi=p["price"]/p["hi52"]-1))
cash_ibk, cash_tyba = ibk["summary"]["total_cash_value"], tyba["cash_usd"]
pos_val = sum(r["val"] for r in rows); tot = pos_val + cash_ibk + cash_tyba
for r in rows: r["w"] = r["val"]/tot; r["pnl"] = r["val"]-r["cost"]

print("== CONTROLES ==")
ibk_val = sum(r["val"] for r in rows if r["cust"] == "IBK") + cash_ibk
check("IBK consolidado ≈ net_liquidation", abs(ibk_val/ibk["summary"]["net_liquidation"]-1) < 0.005, f"({ibk_val:,.2f} vs {ibk['summary']['net_liquidation']:,.2f}, {ibk_val/ibk['summary']['net_liquidation']-1:+.2%})")
check("pesos suman 100%", abs(sum(r["w"] for r in rows) + (cash_ibk+cash_tyba)/tot - 1) < 1e-9)
check("16 posiciones (7 IBK + 9 TYBA)", len(rows) == 16, f"({len(rows)})")
check("sin precios nulos/≤0", all(r["val"] > 0 for r in rows))
b = tyba["ibk_cash_bridge"]
bridge = b["brief_cash_ibk_0852_lima"] - b["usd_sold_for_cad"] - b["fx_commission"]
pa_cash = ibk["summary"]["pa_allocation_cash"]
check("puente cash IBK (brief 08:52 → hoy) vs cash de Portfolio Analyst ±$2", abs(bridge - pa_cash) < 2, f"(629.93 − 508.57 − 2.85 = {bridge:,.2f} vs {pa_cash:,.2f})")
gap = pa_cash - cash_ibk
print(f"  [AVISO] cash PA {pa_cash:,.2f} vs total_cash_value {cash_ibk:,.2f}: brecha {gap:,.2f} sin explicar con los datos del conector" if abs(gap) > 2 else "")

print("\n== CONSOLIDADO (USD) ==")
print(f"{'Ticker':7}{'Cust':6}{'Valor':>11}{'Peso':>7}{'PnL':>10}{'PnL%':>8}{'vs52H':>8}  Sector")
for r in sorted(rows, key=lambda r: -r["val"]):
    print(f"{r['t']:7}{r['cust']:6}{r['val']:>11,.0f}{r['w']:>7.1%}{r['pnl']:>10,.0f}{r['pnl']/r['cost']:>8.1%}{r['hi']:>8.1%}  {r['sec']}")
cost = sum(r["cost"] for r in rows); pnl = pos_val - cost
print(f"{'POS.':13}{pos_val:>11,.0f}{pos_val/tot:>7.1%}{pnl:>10,.0f}{pnl/cost:>8.1%}")
print(f"{'CASH':13}{cash_ibk+cash_tyba:>11,.0f}{(cash_ibk+cash_tyba)/tot:>7.1%}")
print(f"{'TOTAL':13}{tot:>11,.0f}")
for c in ("IBK", "TYBA"):
    v = sum(r["val"] for r in rows if r["cust"] == c) + (cash_ibk if c == "IBK" else cash_tyba)
    print(f"  {c}: {v:,.0f} ({v/tot:.1%})")

ap = tyba["external_contributions_usd"]
print(f"\n== RETORNO SOBRE CAPITAL APORTADO ==\n  Aportes externos {ap:,.2f} · ganancia {tot-ap:,.0f} · retorno acumulado {tot/ap-1:.1%}")

print("\n== IPS ==")
sec = {}
for r in rows: sec[r["sec"]] = sec.get(r["sec"], 0) + r["w"]
for k, v in sorted(sec.items(), key=lambda x: -x[1]): print(f"  {k:16}{v:>7.1%}")
mining = sum(v for k, v in sec.items() if k in MINING)
print(f"  Minería total (junior + oro large-cap) {mining:.1%} vs límite {IPS['mineria_max']:.0%} -> {'EXCEDE' if mining > IPS['mineria_max'] else 'ok'}")
for r in rows:
    if r["w"] > IPS["posicion_max"]*0.9: print(f"  {r['t']} {r['w']:.1%} vs límite por posición {IPS['posicion_max']:.0%} -> {'EXCEDE' if r['w'] > IPS['posicion_max'] else 'cerca'}")
hhi = sum((r["w"]*100)**2 for r in rows); print(f"  HHI {hhi:,.0f} · N efectivo {10000/hhi:.1f}")
print("\nResultado de controles:", "TODOS OK" if not fails else f"FALLAS: {fails}")
