# Portafolio consolidado IBK + TYBA · cierre 2-oct-2026 (reporte del 4-oct)

**Fuentes:** IBK → conector IBKR (posiciones, pull 4-oct 05:22 UTC). TYBA → cantidades/costo de `Resumen_matutino_2026-10-02.html` × último print IBKR del 2-oct (US hasta 23:59 UTC; puede incluir after-hours).
**Controles:** 5/5 OK + 1 aviso. Ver `salida_consolidado_2026-10-04.txt`. Reproducir:
`python3 tracking/consolidated.py tracking/data/ibk_2026-10-04.json tracking/data/tyba_2026-10-02.json`

## Resumen
| | Brief 2-oct 08:52 Lima | Cierre 2-oct (este reporte) | Δ |
|---|---|---|---|
| Valor total | $141.207 | **$141.954** | +$747 |
| IBK (con cash) | $89.024 | $90.130 | +$1.106 |
| TYBA | $52.165 | $51.824 | −$341 |
| PnL abierto | $25.813 | $26.577 (+23,1%) | +$764 |
| Ganancia s/ aportes ($99.398) | $41.809 (+42,1%) | $42.556 (+42,8%) | +$747 |
| Minería (junior + Barrick) | 71,2% | **71,8%** (límite IPS 70%) | +0,6 pp |
| RIOFF | 30,0% | **30,4%** (límite IPS 30%) | +0,4 pp |
| Cash | $648 | $104 | −$544 |

## Conciliación brief → hoy (todo explicado)
1. **GAL 15.500 → 17.000:** compra de 1.500 @ 0,48 CAD el 2-oct 14:29 UTC (37 min después del brief), financiada vendiendo US$508,57 → CAD. Costo prom. sube a 0,4597.
2. **Cash IBK $629,93 → $117,61 (Portfolio Analyst):** 629,93 − 508,57 − 2,85 comisión FX = 118,51; diferencia $0,90.
3. **Cambio de precios:** RIOFF 2,23 → 2,27 (+$760), SRGXF 0,358 → 0,3728 (+$401), GLGDF 2,94 → 2,8755 (−$194), US tech mixto.
4. **Alertas IBKR reajustadas** después del brief: QUEXF 1,69 → 1,50; SRGXF 0,40 → 0,41; TSO 0,92 → 0,93; nuevas en RIOFF 2,37, GLGDF 2,83, GAL 0,52, SMI 0,52.

## Verificación del brief (cálculos internos)
Revisé que Σ posiciones + cash = total, que Σ PnL = PnL total, que los subtotales IBK/TYBA cuadran, que el GAAR 25,5% cuadra y que el retorno acumulado es 42,06%: **todo cuadra al centavo.**
Observaciones:
- El campo `ibk` del brief ($88.394) **excluye el cash** IBK ($630); el net liq comparable es $89.024.
- El TWR YTD del brief (−13,98%) y el drawdown (−28,2%) son estimaciones intradía de las 08:52. Al cierre del 2-oct, Portfolio Analyst marca TWR YTD −13,25%.
- El XIRR (36,0%) no se puede re-verificar sin la serie de aportes fechados.

## Banderas para ti
1. **IPS excedido en dos frentes:** minería 71,8% > 70% y RIOFF 30,4% > 30%. El exceso es pequeño y se debe a la compra de GAL y a la subida de RIOFF el viernes.
2. **Alertas cruzadas:** RIOFF, SRGXF, GAL, TSO y SMI ya están bajo su nivel. GAL cruzó su alerta (0,52) un día después de que compraste a 0,48–0,55.
3. **Liquidez:** el cash consolidado es $104 (0,07%). No hay colchón para promediar ni para cubrir comisiones.
4. **Aviso:** el conector da dos cifras de cash IBK distintas: $117,61 (Portfolio Analyst) y $85,87 (`total_cash_value`). La brecha de $31,74 no se explica con los datos del conector; confírmala en tu pantalla.
5. **Precios TYBA:** usé el último print IBKR, que puede incluir after-hours y no es el cierre oficial. El impacto esperado es de ±$50.
6. **Repo:** en `default_state.js`, `B` figura como "Barnes Group / Insurance" con 100 acciones. En realidad es **Barrick Mining** (NYSE: B), con 139 acciones. Además faltan PPTA, IONS y GAL.

Esto no es asesoría financiera.
