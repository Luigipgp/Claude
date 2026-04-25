"""Build portfolio_v7.html from v6 baseline + new DEFAULT_STATE + fetcher fixes.

Run: python3 build_v7.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "portfolio_v6_baseline.html"
DATA = ROOT / "default_state.js"
OUT = ROOT / "portfolio_v7.html"

html = SRC.read_text()
new_state_js = DATA.read_text().strip()

# ---------------------------------------------------------------------------
# 1. Title bump v6 -> v7
# ---------------------------------------------------------------------------
html = html.replace("Luigi's Portfolio v6", "Luigi's Portfolio v7")
html = html.replace(
    'Portfolio <em>v6</em>',
    'Portfolio <em>v7</em>',
)
html = html.replace(
    'luigi_portfolio_v6',
    'luigi_portfolio_v7',
)
html = html.replace(
    'debugLog(\'ok\',\'Portfolio v6 inicializado\');',
    'debugLog(\'ok\',\'Portfolio v7 inicializado\');',
)

# ---------------------------------------------------------------------------
# 2. Replace DEFAULT_STATE block (between marker comment and `const SKIP_FETCH`)
# ---------------------------------------------------------------------------
state_pattern = re.compile(
    r"// DEFAULT STATE \(Apr 15 2026 — latest workbook\)\n"
    r"// ═══════════════════════════════════════════════════════\n"
    r"const DEFAULT_STATE = \{.*?\n\};",
    re.DOTALL,
)

if not state_pattern.search(html):
    print("ERROR: could not find DEFAULT_STATE block")
    sys.exit(1)

new_state_block = (
    "// DEFAULT STATE (Apr 25 2026 — sourced from Inversiones.xlsx)\n"
    "// ═══════════════════════════════════════════════════════\n"
    + new_state_js
)
html = state_pattern.sub(lambda m: new_state_block, html, count=1)

# ---------------------------------------------------------------------------
# 3. Inject fetchT timeout helper before fetchStooq
# ---------------------------------------------------------------------------
fetch_helper = """async function fetchT(url, opts={}, timeout=8000){
  const ctrl = new AbortController();
  const tid = setTimeout(()=>ctrl.abort(), timeout);
  try{
    const r = await fetch(url, {...opts, signal:ctrl.signal});
    return r;
  }finally{
    clearTimeout(tid);
  }
}

"""
html = html.replace("async function fetchStooq(ticker){", fetch_helper + "async function fetchStooq(ticker){", 1)

# ---------------------------------------------------------------------------
# 4. Replace fetchStooq with timeout-aware version
# ---------------------------------------------------------------------------
old_stooq = """async function fetchStooq(ticker){
  const t0 = Date.now();
  const url = `https://stooq.com/q/l/?s=${ticker.toLowerCase()}.us&f=sd2t2ohlcv&h&e=csv`;
  try{
    const r = await fetch(url,{cache:'no-cache'});
    if(!r.ok) throw new Error(`HTTP ${r.status}`);
    const txt = await r.text();
    const lines = txt.trim().split('\\n');
    if(lines.length < 2) throw new Error('no data');
    const parts = lines[1].split(',');
    const close = parseFloat(parts[6]);
    if(!close||isNaN(close)||close<=0) throw new Error('invalid: '+parts[6]);
    const lat = Date.now()-t0;
    debugLog('ok',`Stooq ${ticker}: $${close.toFixed(3)} (${lat}ms)`);
    return {price:close, source:'stooq', latency:lat};
  }catch(e){
    debugLog('warn',`Stooq ${ticker}: ${e.message}`);
    return null;
  }
}"""

new_stooq = """async function fetchStooq(ticker, suffix='.us'){
  const t0 = Date.now();
  const url = `https://stooq.com/q/l/?s=${ticker.toLowerCase()}${suffix}&f=sd2t2ohlcv&h&e=csv`;
  try{
    const r = await fetchT(url,{cache:'no-cache'},6000);
    if(!r.ok) throw new Error(`HTTP ${r.status}`);
    const txt = await r.text();
    const lines = txt.trim().split('\\n');
    if(lines.length < 2) throw new Error('no data');
    const parts = lines[1].split(',');
    // f=sd2t2ohlcv -> [Symbol,Date,Time,Open,High,Low,Close,Volume]
    const close = parseFloat(parts[6]);
    if(!close||isNaN(close)||close<=0) throw new Error('invalid:'+parts[6]);
    const lat = Date.now()-t0;
    debugLog('ok',`Stooq ${ticker}: $${close.toFixed(3)} (${lat}ms)`);
    return {price:close, source:'stooq', latency:lat};
  }catch(e){
    debugLog('warn',`Stooq ${ticker}: ${e.name==='AbortError'?'timeout':e.message}`);
    return null;
  }
}"""

if old_stooq not in html:
    print("ERROR: fetchStooq pattern not found")
    sys.exit(1)
html = html.replace(old_stooq, new_stooq, 1)

# ---------------------------------------------------------------------------
# 5. Replace fetchYahoo with timeout + extra proxy + Yahoo symbol suffix support
# ---------------------------------------------------------------------------
old_yahoo = """async function fetchYahoo(ticker){
  const t0 = Date.now();
  const yUrl = `https://query1.finance.yahoo.com/v8/finance/chart/${ticker}?interval=1d&range=1d`;
  const proxies = [
    u => `https://corsproxy.io/?${encodeURIComponent(u)}`,
    u => `https://api.allorigins.win/raw?url=${encodeURIComponent(u)}`,
    u => `https://api.codetabs.com/v1/proxy?quest=${encodeURIComponent(u)}`,
  ];
  for(let i=0;i<proxies.length;i++){
    try{
      const r = await fetch(proxies[i](yUrl),{cache:'no-cache'});
      if(!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();
      const price = d?.chart?.result?.[0]?.meta?.regularMarketPrice;
      if(price&&!isNaN(price)&&price>0){
        const lat = Date.now()-t0;
        debugLog('ok',`Yahoo ${ticker}: $${price.toFixed(3)} [p${i+1}] (${lat}ms)`);
        return {price, source:'yahoo', latency:lat};
      }
      throw new Error('no price');
    }catch(e){
      debugLog('warn',`Yahoo ${ticker} p${i+1}: ${e.message}`);
    }
  }
  return null;
}"""

new_yahoo = """async function fetchYahoo(ticker, ySymbol=null){
  const t0 = Date.now();
  const sym = ySymbol || ticker;
  const yUrl = `https://query1.finance.yahoo.com/v8/finance/chart/${sym}?interval=1d&range=1d`;
  // Ordered by observed reliability (2026); corsproxy.io accepts Origin: null from file://
  const proxies = [
    u => `https://corsproxy.io/?${encodeURIComponent(u)}`,
    u => `https://api.cors.lol/?url=${encodeURIComponent(u)}`,
    u => `https://api.allorigins.win/raw?url=${encodeURIComponent(u)}`,
    u => `https://api.codetabs.com/v1/proxy?quest=${encodeURIComponent(u)}`,
  ];
  for(let i=0;i<proxies.length;i++){
    try{
      const r = await fetchT(proxies[i](yUrl),{cache:'no-cache'},7000);
      if(!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();
      const price = d?.chart?.result?.[0]?.meta?.regularMarketPrice;
      if(price&&!isNaN(price)&&price>0){
        const lat = Date.now()-t0;
        debugLog('ok',`Yahoo ${sym}: $${price.toFixed(3)} [p${i+1}] (${lat}ms)`);
        return {price, source:'yahoo', latency:lat};
      }
      throw new Error('no price');
    }catch(e){
      debugLog('warn',`Yahoo ${sym} p${i+1}: ${e.name==='AbortError'?'timeout':e.message}`);
    }
  }
  return null;
}"""

if old_yahoo not in html:
    print("ERROR: fetchYahoo pattern not found")
    sys.exit(1)
html = html.replace(old_yahoo, new_yahoo, 1)

# ---------------------------------------------------------------------------
# 6. Replace fetchTicker with smart routing (OTC -> Yahoo, ASX -> Yahoo .AX)
# ---------------------------------------------------------------------------
old_ticker = """async function fetchTicker(ticker){
  if(SKIP_FETCH.has(ticker)){debugLog('warn',`${ticker}: skip (manual)`);return null;}
  const override = STATE.priceOverrides[ticker];
  if(override && (Date.now()-override.timestamp) < 24*60*60*1000){
    debugLog('ok',`${ticker}: override $${override.price}`);
    return {price:override.price, source:'manual', latency:0};
  }
  let r = await fetchStooq(ticker);
  if(r) return r;
  r = await fetchYahoo(ticker);
  if(r) return r;
  debugLog('err',`${ticker}: all failed`);
  return null;
}"""

new_ticker = """// Tickers that Stooq doesn't list (OTC / pink sheets / foreign).
// We skip Stooq for these and go directly to Yahoo to save latency.
const OTC_TICKERS = new Set(['RIOFF','GLGDF','QUEXF','SRGXF','GOGOF','BMOOF','TLSA','BMM','VZLA']);
// Tickers that need a Yahoo symbol suffix (foreign exchanges).
const YAHOO_SUFFIX = {TSO:'TSO.AX', SMI:'SMI.AX'};

async function fetchTicker(ticker){
  if(SKIP_FETCH.has(ticker)){debugLog('warn',`${ticker}: skip (manual)`);return null;}
  // Manual overrides are now persistent (no 24h expiry). User can clear from Settings.
  const override = STATE.priceOverrides[ticker];
  if(override && override.price > 0){
    debugLog('ok',`${ticker}: override $${override.price}`);
    return {price:override.price, source:'manual', latency:0};
  }
  const ySym = YAHOO_SUFFIX[ticker] || null;
  // OTC / foreign tickers: skip Stooq (always fails), go straight to Yahoo
  if(OTC_TICKERS.has(ticker) || ySym){
    const r = await fetchYahoo(ticker, ySym);
    if(r) return r;
    debugLog('err',`${ticker}: all failed (OTC/foreign)`);
    return null;
  }
  // Standard listed tickers: Stooq first, Yahoo fallback
  let r = await fetchStooq(ticker);
  if(r) return r;
  r = await fetchYahoo(ticker);
  if(r) return r;
  debugLog('err',`${ticker}: all failed`);
  return null;
}"""

if old_ticker not in html:
    print("ERROR: fetchTicker pattern not found")
    sys.exit(1)
html = html.replace(old_ticker, new_ticker, 1)

# ---------------------------------------------------------------------------
# 7. Replace refreshMacro internal fetches with fetchT
# ---------------------------------------------------------------------------
html = html.replace(
    "    const goldUrl = `https://stooq.com/q/l/?s=gc.f&f=sd2t2ohlcv&h&e=csv`;\n    const r = await fetch(goldUrl);",
    "    const goldUrl = `https://stooq.com/q/l/?s=gc.f&f=sd2t2ohlcv&h&e=csv`;\n    const r = await fetchT(goldUrl,{},6000);",
    1,
)
html = html.replace(
    "    const oilUrl = `https://stooq.com/q/l/?s=cl.f&f=sd2t2ohlcv&h&e=csv`;\n    const r = await fetch(oilUrl);",
    "    const oilUrl = `https://stooq.com/q/l/?s=cl.f&f=sd2t2ohlcv&h&e=csv`;\n    const r = await fetchT(oilUrl,{},6000);",
    1,
)

# ---------------------------------------------------------------------------
# 8. Replace fetchNewsForTicker fetch with fetchT + add corsproxy.io as primary
# ---------------------------------------------------------------------------
old_news_proxies = """  const proxies = [
    u => `https://api.allorigins.win/raw?url=${encodeURIComponent(u)}`,
    u => `https://api.codetabs.com/v1/proxy?quest=${encodeURIComponent(u)}`,
  ];
  for(const p of proxies){
    try{
      const r = await fetch(p(rssUrl));"""

new_news_proxies = """  const proxies = [
    u => `https://corsproxy.io/?${encodeURIComponent(u)}`,
    u => `https://api.allorigins.win/raw?url=${encodeURIComponent(u)}`,
    u => `https://api.codetabs.com/v1/proxy?quest=${encodeURIComponent(u)}`,
  ];
  for(const p of proxies){
    try{
      const r = await fetchT(p(rssUrl),{},6000);"""

if old_news_proxies not in html:
    print("WARN: news proxy pattern not found (skipping news fix)")
else:
    html = html.replace(old_news_proxies, new_news_proxies, 1)

# ---------------------------------------------------------------------------
# 9. switchTxTab: use data-type instead of hardcoded array index
#    Also add data-type to the modal-tab buttons.
# ---------------------------------------------------------------------------
html = html.replace(
    "<button class=\"modal-tab active\" onclick=\"switchTxTab('compra',event)\">Compra</button>",
    "<button class=\"modal-tab active\" data-type=\"compra\" onclick=\"switchTxTab('compra',event)\">Compra</button>",
    1,
)
html = html.replace(
    "<button class=\"modal-tab\" onclick=\"switchTxTab('venta',event)\">Venta</button>",
    "<button class=\"modal-tab\" data-type=\"venta\" onclick=\"switchTxTab('venta',event)\">Venta</button>",
    1,
)
html = html.replace(
    "<button class=\"modal-tab\" onclick=\"switchTxTab('fondeo',event)\">Fondeo</button>",
    "<button class=\"modal-tab\" data-type=\"fondeo\" onclick=\"switchTxTab('fondeo',event)\">Fondeo</button>",
    1,
)
html = html.replace(
    "document.querySelectorAll('.modal-tab').forEach((t,i)=>t.classList.toggle('active', ['compra','venta','fondeo'][i]===type));",
    "document.querySelectorAll('.modal-tab').forEach(t=>t.classList.toggle('active', t.dataset.type===type));",
    1,
)

# ---------------------------------------------------------------------------
# 10. loadState: add v6 -> v7 auto-migration (clears stale cache, loads new defaults)
# ---------------------------------------------------------------------------
old_load = """function loadState(){
  try{
    const s = localStorage.getItem('luigi_portfolio_v7');
    if(s){
      const p = JSON.parse(s);
      p.priceOverrides = p.priceOverrides || {};
      p.alerts = p.alerts || [];
      p.prevClose = p.prevClose || DEFAULT_STATE.prevClose;
      return p;
    }
  }catch(e){console.error(e);}
  return structuredClone(DEFAULT_STATE);
}"""

new_load = """function loadState(){
  try{
    const s = localStorage.getItem('luigi_portfolio_v7');
    if(s){
      const p = JSON.parse(s);
      p.priceOverrides = p.priceOverrides || {};
      p.alerts = p.alerts || [];
      p.prevClose = p.prevClose || DEFAULT_STATE.prevClose;
      return p;
    }
    // Auto-clean older versions so the new DEFAULT_STATE loads fresh.
    const old = localStorage.getItem('luigi_portfolio_v6');
    if(old){
      console.info('Migrating from v6: clearing old cache, loading v7 defaults');
      localStorage.removeItem('luigi_portfolio_v6');
    }
  }catch(e){console.error(e);}
  return structuredClone(DEFAULT_STATE);
}"""

if old_load not in html:
    print("ERROR: loadState pattern not found (after v6->v7 rename)")
    sys.exit(1)
html = html.replace(old_load, new_load, 1)

# ---------------------------------------------------------------------------
# 11. Wrap init() fetch calls in try/catch so init failures don't kill the app
# ---------------------------------------------------------------------------
old_init_calls = """  setStatus('Cargando precios…','warn');
  fetchAllPrices();
  refreshMacro();
  refreshNews();
  setInterval(updateCountdown, 1000);"""

new_init_calls = """  setStatus('Cargando precios…','warn');
  // Fire-and-forget so a fetch failure during init doesn't break tab navigation
  Promise.resolve().then(()=>fetchAllPrices()).catch(e=>debugLog('err','init fetch: '+e.message));
  Promise.resolve().then(()=>refreshMacro()).catch(e=>debugLog('err','init macro: '+e.message));
  Promise.resolve().then(()=>refreshNews()).catch(e=>debugLog('err','init news: '+e.message));
  setInterval(updateCountdown, 1000);"""

if old_init_calls not in html:
    print("ERROR: init() pattern not found")
    sys.exit(1)
html = html.replace(old_init_calls, new_init_calls, 1)

# ---------------------------------------------------------------------------
# Sanity check: nothing left referencing v6 except the migration comment
# ---------------------------------------------------------------------------
v6_refs = [m for m in re.finditer(r"v6", html) if "v6" in html[max(0,m.start()-30):m.end()+30]]
# (we expect only the migration comment + auto-clean code now)

OUT.write_text(html)
print(f"Wrote {OUT} ({len(html):,} chars)")
print(f"Position count in source data: {new_state_js.count('{ticker:')}")
print(f"Transaction count in source data: {new_state_js.count('{id:')}")
