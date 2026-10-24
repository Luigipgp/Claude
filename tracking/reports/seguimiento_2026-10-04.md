# Seguimiento de portafolio · Cuenta IBK · 4-oct-2026

**Fuente:** conector IBKR (pull 2026-10-04 05:22 UTC). Marks = cierre del viernes 2-oct (mercado cerrado domingo).
**Alcance:** solo IBK. TYBA no está en el conector y `Inversiones.xlsx` no está en el repo → TYBA **no evaluado**.
**Controles:** 16/16 OK + 1 aviso (desfase de $174 / 0,19% entre los endpoints de balances y posiciones). Ver `salida_controles_2026-10-04.txt`.

## Resumen
| Métrica | Valor |
|---|---|
| NAV (net liquidation) | **$89.988** |
| PnL no realizado | +$16.923 (+23,1% sobre costo) |
| PnL del día (2-oct) | +$2.645 |
| Cash / buying power | $85,87 / $343 (0,1%) |
| TWR 1D / 7D / 1M | −0,13% / −7,72% / −13,72% |
| TWR YTD / 1Y | −13,37% / +50,94% |
| NAV vs pico 9-sep ($106.852) | −15,8% |

## Posiciones (USD, marks IBK)
| Ticker | Precio | Costo | Valor USD | Peso | PnL USD | PnL % | vs máx 52s |
|---|---|---|---|---|---|---|---|
| RIOFF | 2,27 | 1,303 | 43.130 | 47,9% | +18.376 | +74,2% | −24,8% |
| TSO (AUD) | 0,905 | 1,006 | 10.824 | 12,0% | −1.207 | −10,0% | −36,9% |
| SRGXF | 0,3728 | 0,4121 | 10.067 | 11,2% | −1.060 | −9,5% | −43,3% |
| GLGDF | 2,8755 | 2,2323 | 8.626 | 9,6% | +1.929 | +28,8% | −12,6% |
| QUEXF | 1,63 | 1,481 | 8.150 | 9,1% | +745 | +10,1% | −33,5% |
| GAL (CAD) | 0,49 | 0,4597 | 5.845 | 6,5% | +361 | +6,6% | −31,0% |
| SMI (AUD) | 0,515 | 0,8513 | 3.402 | 3,8% | −2.221 | −39,5% | −57,1% |

## Banderas (preguntas para ti, no correcciones)
1. **5 de 7 alertas de precio ya cruzadas:** RIOFF (≤2,37), SRGXF (≤0,41), GAL (≤0,52), TSO (≤0,93), SMI (≤0,52). ¿Siguen siendo tus niveles de stop/revisión o las actualizamos?
2. **Concentración:** RIOFF = 47,9% de IBK; 99,9% de la cuenta en Basic Materials (mineras junior).
3. **Liquidez:** cash 0,1% → sin capacidad de promediar sin vender.
4. **Órdenes GTC vivas:** RIOFF 1.000 @2,79 (+22,9%) y @2,89 (+27,3%, *REPLACED*); GLGDF 750 @3,28 (+14,1%, *REPLACED*); QUEXF 1.000 @2,80 (+71,8%). ¿Confirmas que las *REPLACED* siguen activas en tu pantalla?
5. **Dashboard v7 desactualizado:** `default_state.js` (abr-2026) muestra RIOFF 21.300 / SRGXF 17.000 / TSO 8.800 / SMI 8.000 sin GAL; IBK hoy tiene 19.000 / 27.000 / 17.200 / 9.500 y GAL 17.000. Requiere `Inversiones.xlsx` actualizado para resincronizar (también TYBA).
6. **GAL:** el snapshot no devolvió `last` con timestamp; el mark viene de `get_account_positions`.

## Cómo reproducir
```bash
python3 tracking/ibk_tracker.py tracking/data/ibk_2026-10-04.json
```

Esto no es asesoría financiera.
