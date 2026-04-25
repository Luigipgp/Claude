# Portfolio v7 — Changelog

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
