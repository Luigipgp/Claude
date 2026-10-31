# Portafolio consolidado IBK + TYBA · 21-oct-2026

**Fuentes y frescura**
- IBK: conector IBKR, pull a las 12:25 UTC.
  - OTC (RIOFF, SRGXF, GLGDF, QUEXF): cierre del 20-oct.
  - TSO y SMI: cierre ASX del 21-oct.
  - GAL: mark de la posición, porque el snapshot fue rechazado.
- TYBA: precios IBKR pre-market del 21-oct (~8:25 ET). Las **cantidades son las del 2-oct**: TYBA no está en el conector y no se han verificado desde esa fecha.
- **Controles:** consolidado 5/5 OK · IBK 16/16 OK + 1 aviso (brecha de $308, 0,38%, entre los endpoints de balances y posiciones, que usan marks distintos).

Reproducir:
`python3 tracking/consolidated.py tracking/data/ibk_2026-10-21.json tracking/data/tyba_2026-10-21.json`

## Resumen
| | 2-oct (cierre) | **21-oct** | Δ |
|---|---|---|---|
| Valor total | $141.954 | **$131.712** | −$10.242 (−7,2%) |
| IBK (con cash) | $90.130 | $80.932 | −$9.198 |
| TYBA | $51.824 | $50.780 | −$1.044 |
| PnL abierto | $26.577 | $16.068 (+13,9%) | −$10.509 |
| Ganancia sobre aportes ($99.398) | $42.556 (+42,8%) | $32.315 (+32,5%) | −$10.241 |
| Minería (junior + Barrick) | 71,8% | **70,04%** (límite 70%) | −1,8 pp |
| RIOFF | 30,4% | 29,7% (límite 30%) | −0,7 pp |
| Cash | $104 | $134 | +$30 |
| XIRR / CAGR (dashboard) | 36,5% / 26,0% | 26,8% / 19,4% | |

**TWR de IBK (Portfolio Analyst):**
| 1D | 7D | MTD | 1M | YTD | 1Y |
|---|---|---|---|---|---|
| +0,47% | +1,99% | −8,61% | −18,15% | −21,74% | +32,54% |

## Qué movió el valor (2-oct → 21-oct, efecto precio en USD)
- Restaron:
  - RIOFF −$3.990 (−9,3%)
  - QUEXF −$1.550 (−19,0%)
  - SRGXF −$1.527 (−15,2%)
  - GAL −$1.128 (−20,4% en CAD)
  - SMI −$636 (−19,4% en AUD)
  - GLGDF −$556
  - NVDA −$475
  - META −$362
- Sumaron:
  - MSFT +$201
  - TSO +$159
  - IONS +$115
  - B +$97
- No hubo compras ni ventas en IBK desde el 2-oct. Solo hubo una conversión CAD→USD de US$13,65 el 6-oct.

## Banderas para ti
1. **Minería en 70,04%:** sigue sobre el límite de la política, por muy poco. RIOFF bajó a 29,7%, dentro del límite.
2. **Posiciones ≥30% bajo costo:** SMI (−51%). IONS mejoró a −26%; QUEXF, SRGXF y GAL quedaron entre −11% y −23%.
3. **Tus alertas IBKR cambiaron.** Ahora la mayoría son de **subida** (≥):

   | Ticker | Nivel de la alerta | Precio actual |
   |---|---|---|
   | RIOFF | 2,41 / 2,70 | 2,06 |
   | SRGXF | 0,41 | 0,316 |
   | GLGDF | 2,94 | 2,69 |
   | GAL | 0,53 | 0,39 |
   | TSO | 0,94 | 0,91 |
   | SMI | 0,52 | 0,415 |

   Y dos de bajada: SMI ≤0,40 (*stop mental*; está a +3,7%) y QUEXF ≤1,17 (a +12,8%). Ninguna está cruzada.
4. **Órdenes GTC de venta:**
   - RIOFF: 1.500 @2,79 y 2.500 @2,88 (*REPLACED* el 7-oct; requieren +35–40%).
   - GLGDF: 750 @3,28 (+22%).
   - QUEXF: 1.000 @2,80 (+112%).
5. **TYBA:** si operaste en TYBA después del 2-oct, las cifras de TYBA no lo reflejan. Necesito un pantallazo o `Inversiones.xlsx`.
6. **Hoy reporta META** (after market). Además, MSFT el 28-oct (confirmado), junto con la decisión del FOMC ese mismo día.

## Agenda verificada el 21-oct
| Fecha | Evento | Estado | Fuente |
|---|---|---|---|
| 21-oct | META, resultados 3T | **Confirmado** | [comunicado de Meta, 12-oct](https://investor.atmeta.com/investor-news/press-release-details/2026/Meta-to-Announce-Third-Quarter-2026-Results/default.aspx) |
| 28-oct | MSFT, resultados 1T FY27 | **Confirmado** | [comunicado del 7-oct vía Finviz](https://finviz.com/news/400058/microsoft-announces-quarterly-earnings-release-date) |
| ~28-oct | GOOGL | Por confirmar | [days.to](https://days.to/alphabet-earnings), [AlphaQuery](https://www.alphaquery.com/stock/GOOGL/earnings-history) (4-nov) |
| ~29-oct | IONS | Por confirmar | patrón 2025, [ir.ionis.com](https://ir.ionis.com/node/34956) |
| 13–16-nov | PPTA | Por confirmar | [AJ Bell](https://www.ajbell.co.uk/market-research/sub/TSE:PPTA/company-info), [Earnings Whispers](https://beta.earningswhispers.com/go/w/PPTA) |

El resto de la agenda (B 9-nov, NVDA 17-nov, BMM, TSO/SMI ASX, GAL, FOMC) se mantiene tal como venía del brief del 2-oct.

## Lo que no se pudo actualizar
- **Macro y noticias:** siguen siendo las del brief del 2-oct, con su fecha. El servidor de FMP se desconectó y Firecrawl no tiene créditos.
- **TipRanks:** llegó a su límite mensual, que se restablece el 1-nov.

Esto no es asesoría financiera.
