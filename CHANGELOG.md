# Portfolio v7 — Changelog

## 2026-10-04 · Sincronización con IBKR + resumen matutino del 2-oct

**Datos (`default_state.js`, regenerado con `tracking/sync_default_state.py`)**
- 16 posiciones (7 IBK + 9 TYBA). Antes eran 14, con datos de abril.
  - IBK, del conector IBKR: RIOFF 19.000 · TSO 17.200 · SRGXF 27.000 · GLGDF 3.000 · QUEXF 5.000 · GAL 17.000 · SMI 9.500.
  - TYBA, del resumen matutino: VOO 13,9984 · NVDA 35 · MSFT 16 · META 10 · B 139 · GOOGL 12 · BMM 700 · PPTA 144 · IONS 49.
  - Sale EPU y entran GAL, PPTA e IONS.
- `B` corregido: es **Barrick Mining** (NYSE: B), no Barnes Group.
- Las posiciones en AUD y CAD (TSO, SMI, GAL) se guardan en USD con el FX de IBKR del pull y llevan el campo `ccy`.
- Cash: TYBA $18,47 · IBK $85,87. Marks (`prevClose`): cierres del 2-oct.
- Fondeos: aporte neto de $11.000 en may-2026, fechado el 27-may (salto de NAV en IBKR PA con TWR plano). Total: $99.397,75, igual al brief.
- Se registran los cierres realizados de IBK posteriores a abril (RIOFF ×3, MSFT, TSO).
- Se elimina la alerta de EPU (posición cerrada).

**Código (`build_v7.py`, patches 12–16)**
- Conversión FX en vivo para TSO.AX, SMI.AX y GAL.V. Si el tipo de cambio en vivo falta o es implausible, usa el último FX de IBKR. Antes, SMI.AX se sumaba en AUD como si fuera USD.
- TSO deja de ser solo manual.
- XIRR: solo flujos externos más el valor final. Antes sumaba el producto de las ventas como si fuera retiro, aunque se reinvirtió.
- "Profit total" = patrimonio − fondeado. El log de ventas no tiene las ventas TYBA posteriores a abril.
- Migración: si el `dataVersion` guardado difiere del actual, se respalda el estado (`luigi_portfolio_v7_backup_*`), se cargan los datos nuevos y se conservan las alertas del usuario.
- Se reemplaza el contenido fijo de abril:
  - "Acciones recomendadas" pasa a ser **Controles IPS**, calculados en vivo.
  - El calendario de earnings pasa a ser la **agenda de catalizadores** del brief.
  - Noticias, nota macro y FOMC usan datos fechados del brief.
  - La distribución por sector usa un único mapa (antes omitía GAL, PPTA, B e IONS).
  - Oro y WTI muestran "—" cuando no hay dato en vivo, en lugar de valores de abril.

**Validación**: `node test_portfolio.mjs` → 33/33 · `node smoke_test.mjs` → 11/11 · render en Chromium sin errores (escritorio y 390 px).
Patrimonio $141.954 · PnL abierto $26.577 · XIRR 36,5% (brief: 36,0%).

## Resumen ejecutivo

**Problema reportado:** "no actualiza pero me encanta la presentación".
**Diagnóstico:** dos issues independientes que se manifestaban como uno:

1. **Datos hardcoded desactualizados** — el `DEFAULT_STATE` en el HTML era del
   snapshot del 15-abr-2026 (13 posiciones); el Excel actual tiene 14 (incluye
   "B" - Barnes Group), TSO con 8,800 shares (no 4,284), MSFT con 22 shares
   (no 18), cash diferente, 138 transacciones vs 2.
2. **Capa de fetch frágil** — sin timeout, proxies poco confiables, override
   manual expiraba a 24h, OTC pinks (RIOFF/GLGDF/QUEXF/SRGXF) fallaban siempre
   en Stooq y caían a Yahoo en cada refresh.

## Cambios técnicos en `portfolio_v7.html`

### Datos sincronizados con `Inversiones.xlsx`
- 14 posiciones activas (antes 13). Incluye **B (Barnes Group, TYBA, 100 sh)**.
- TSO: 8,800 sh @ $0.7127 (antes 4,284 sh @ $0.6806).
- MSFT: 22 sh @ $446.67 (antes 18 sh @ $453.15).
- Cash TYBA: $3,761.20 · Cash IBK: $95.36 (de la hoja Portafolio).
- **138 transacciones históricas** importadas (antes 2). Esto hace que XIRR,
  CAGR y PnL realizado salgan exactos contra el Excel.
- 20 fundings (suma $88,397.75, coincide con Excel).
- `prevClose` actualizado con los precios "Precio Dia" de cada ticker.

### Fetcher de precios (sección "PRICE FETCHER")
1. **Helper `fetchT(url, opts, timeout)`** — wraps `fetch` con `AbortController`.
   Default 8s, override 6-7s para Stooq/Yahoo/Macro/News. Una request colgada
   ya no congela la app (antes Promise.all esperaba al más lento sin límite).
2. **Routing inteligente en `fetchTicker`**:
   - `OTC_TICKERS` (RIOFF, GLGDF, QUEXF, SRGXF, GOGOF, BMOOF, TLSA, BMM, VZLA)
     → saltan Stooq, van directo a Yahoo. Ahorra ~2s por ticker.
   - `YAHOO_SUFFIX` (TSO → TSO.AX, SMI → SMI.AX) → usa el símbolo del ASX en
     Yahoo. Antes TSO estaba en `SKIP_FETCH` (manual obligatorio); ahora se
     puede traer automáticamente.
3. **4 proxies CORS** (orden de confiabilidad observada en 2026):
   1. `corsproxy.io` (acepta `Origin: null` desde `file://`)
   2. `cors.lol` (nuevo fallback)
   3. `allorigins.win`
   4. `codetabs.com`
4. **Override manual permanente** — eliminada la expiración a 24h (línea 667
   v6). Si pones un precio manual, dura hasta que lo edites o limpies el cache.

### Persistencia y migración
- Clave de localStorage: `luigi_portfolio_v6` → `luigi_portfolio_v7`.
- En `loadState()`, si encuentra la clave v6, la borra y carga el nuevo
  `DEFAULT_STATE` (sincronizado con el Excel). Reset automático sin
  intervención del usuario.

### Otros fixes
- `switchTxTab` usa `data-type` attribute en vez de array hardcodeado
  `['compra','venta','fondeo'][i]` — más robusto si reordenas los tabs.
- `init()` envuelve `fetchAllPrices/refreshMacro/refreshNews` en
  `Promise.resolve().then(...).catch(...)` para que un error temprano no
  rompa la inicialización del resto de la UI.

## Validación

- `node test_portfolio.mjs` → **23/23 PASS** (cálculos, fetcher routing,
  override permanente, migración v6→v7, mocks Stooq/Yahoo).
- `node smoke_test.mjs` → **11/11 PASS** (DOM rendering, KPIs ≈ $128k,
  14 filas en Positions, modales abren/cierran, tabs funcionan).

## Cómo regenerar

```bash
python3 build_v7.py             # produce portfolio_v7.html
node test_portfolio.mjs         # 23 unit tests
node smoke_test.mjs             # 11 DOM smoke tests
```

## Archivos

- `portfolio_v7.html` — entregable final (1,692 líneas, 92 KB).
- `portfolio_v6_baseline.html` — baseline original que se le pasó al script.
- `default_state.js` — datos extraídos del Excel (auto-generado).
- `build_v7.py` — script reproducible que aplica los parches al HTML.
- `test_portfolio.mjs` — 23 tests con mocks (jsdom).
- `smoke_test.mjs` — 11 tests sobre el DOM renderizado.
