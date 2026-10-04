"""Seguimiento de la cuenta IBK a partir de un snapshot JSON del conector IBKR.

Uso: python3 tracking/ibk_tracker.py tracking/data/ibk_YYYY-MM-DD.json
Los precios son los marks del broker (fuente de verdad); no se reemplazan con web.
"""
import json, sys
from datetime import datetime, timezone

snap = json.load(open(sys.argv[1]))
fx = snap["fx_to_usd"]; S = snap["summary"]
rows, fails = [], []

warns = []
def check(name, ok, detail="", warn_only=False):
    tag = 'OK' if ok else ('AVISO' if warn_only else 'FALLA')
    print(f"  [{tag}] {name} {detail}")
    if not ok: (warns if warn_only else fails).append(name)

print("== CONTROLES ==")
for p in snap["positions"]:
    recon = abs(p["qty"] * p["price"] - p["value"]) / p["value"]
    check(f"recon {p['ticker']} qty*precio=valor", recon < 0.001, f"(desv {recon:.4%})")
    upnl = (p["price"] - p["avg"]) * p["qty"]
    check(f"PnL {p['ticker']}", abs(upnl - p["upnl"]) < max(1, 0.002 * abs(p["upnl"])), f"(calc {upnl:,.2f} vs broker {p['upnl']:,.2f})")
    usd = p["value"] * fx[p["ccy"]]
    rows.append({**p, "usd": usd, "cost_usd": p["avg"] * p["qty"] * fx[p["ccy"]], "upnl_usd": p["upnl"] * fx[p["ccy"]], "dpnl_usd": p["dpnl"] * fx[p["ccy"]]})

tot = sum(r["usd"] for r in rows)
check("suma posiciones ≈ gross_position_value", abs(tot - S["gross_position_value"]) / S["gross_position_value"] < 0.005, f"({tot:,.2f} vs {S['gross_position_value']:,.2f})")
check("posiciones + cash ≈ net_liq", abs(tot + S["total_cash_value"] - S["net_liquidation"]) / S["net_liquidation"] < 0.005)
upnl_tot = sum(r["upnl_usd"] for r in rows)
# get_account_balances y get_account_positions usan marks tomados en momentos distintos:
# una brecha < 0.5% del valor bruto es desfase entre endpoints, no un error de datos.
gap = upnl_tot - S["unrealized_pnl_base"]
check("PnL no realizado total ≈ broker (balances)", abs(gap) < 0.001 * tot, f"({upnl_tot:,.2f} vs {S['unrealized_pnl_base']:,.2f}, brecha {gap:,.2f} = {gap/tot:.2%} del bruto)", warn_only=abs(gap) < 0.005 * tot)

print("\n== POSICIONES (USD, marks IBK) ==")
print(f"{'Ticker':7}{'Px':>9}{'Costo':>9}{'Valor USD':>12}{'Peso':>7}{'PnL USD':>11}{'PnL%':>8}{'Día USD':>9}{'vs52H':>8}{'Últ. trade (UTC)':>18}")
for r in sorted(rows, key=lambda r: -r["usd"]):
    ts = datetime.fromtimestamp(r["last_ts"], timezone.utc).strftime("%m-%d %H:%M") if r["last_ts"] else "n/d"
    print(f"{r['ticker']:7}{r['price']:>9.4f}{r['avg']:>9.4f}{r['usd']:>12,.0f}{r['usd']/tot:>7.1%}{r['upnl_usd']:>11,.0f}{r['price']/r['avg']-1:>8.1%}{r['dpnl_usd']:>9,.0f}{r['price']/r['hi52']-1:>8.1%}{ts:>18}")
print(f"{'TOTAL':7}{'':>18}{tot:>12,.0f}{1:>7.0%}{upnl_tot:>11,.0f}{upnl_tot/sum(r['cost_usd'] for r in rows):>8.1%}{sum(r['dpnl_usd'] for r in rows):>9,.0f}")

print("\n== ALERTAS DE PRECIO (last ≤ umbral) ==")
px = {r["ticker"]: r["price"] for r in rows}
for t, th in snap["price_alerts_lte"].items():
    st = "CRUZADA" if px[t] <= th else "activa"
    print(f"  {t:6} umbral {th:<6} precio {px[t]:<8.4f} dist {px[t]/th-1:+7.1%}  -> {st}")

print("\n== ÓRDENES VIVAS ==")
for o in snap["orders"]:
    print(f"  {o['side']} {o['qty']} {o['ticker']} @ {o['limit']} ({o['status']}, {o['tif']}) -> requiere {o['limit']/px[o['ticker']]-1:+.1%} desde {px[o['ticker']]}")

print("\n== RIESGO ==")
top = max(rows, key=lambda r: r["usd"])
print(f"  Mayor posición: {top['ticker']} {top['usd']/tot:.1%} de la cuenta IBK")
print(f"  Cash: {S['total_cash_value']:,.2f} USD ({S['total_cash_value']/S['net_liquidation']:.2%}) · buying power {S['buying_power']:,.2f} · leverage {S['leverage']}")
pk = snap["nav_peak"]; print(f"  Drawdown NAV desde pico {pk['date']} ({pk['nav']:,.0f}): {S['net_liquidation']/pk['nav']-1:.1%} (incluye flujos; ver TWR)")
for k, v in snap["performance_twr"].items(): print(f"  TWR {k:4}: {v:+.2%}")
print("\nResultado de controles:", "TODOS OK" if not fails else f"{len(fails)} FALLAS: {fails}", f"| avisos: {warns}" if warns else "")
