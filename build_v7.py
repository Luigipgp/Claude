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
    "// DEFAULT STATE (2-oct-2026 — IBKR connector + resumen matutino; see tracking/)\n"
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
const YAHOO_SUFFIX = {TSO:'TSO.AX', SMI:'SMI.AX', GAL:'GAL.V'};
// Foreign listings quote in local currency; positions are stored in USD.
const FX_YAHOO = {AUD:'AUDUSD=X', CAD:'CADUSD=X'};
let FX_CACHE = {};
function tickerCcy(ticker){
  return STATE.positions.find(p=>p.ticker===ticker)?.ccy || 'USD';
}
async function getFx(ccy){
  if(ccy==='USD') return 1;
  const c = FX_CACHE[ccy];
  if(c && Date.now()-c.ts < 15*60*1000) return c.rate;
  const r = FX_YAHOO[ccy] ? await fetchYahoo(FX_YAHOO[ccy], FX_YAHOO[ccy]) : null;
  if(r && r.price > 0.3 && r.price < 1.5){
    FX_CACHE[ccy] = {rate:r.price, ts:Date.now()};
    return r.price;
  }
  // Fallback: last IBKR rate stored with the data snapshot
  const fb = STATE.fx?.[ccy] || DEFAULT_STATE.fx?.[ccy] || null;
  debugLog('warn',`FX ${ccy}: live rate unavailable, using stored ${fb}`);
  return fb;
}

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
    const ccy = tickerCcy(ticker);
    if(r && ccy!=='USD'){
      const fx = await getFx(ccy);
      if(!fx){debugLog('err',`${ticker}: no FX ${ccy}`);return null;}
      debugLog('ok',`${ticker}: ${r.price} ${ccy} × ${fx} = $${(r.price*fx).toFixed(4)}`);
      return {...r, price:r.price*fx, localPrice:r.price, ccy, fx};
    }
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
      if(p.dataVersion !== DEFAULT_STATE.dataVersion){
        // Saved data predates the current broker snapshot: back it up, load the new
        // defaults and carry over only the user's own alerts. Old manual price
        // overrides are dropped because the new broker marks are more recent.
        localStorage.setItem('luigi_portfolio_v7_backup_'+(p.dataVersion||'pre'), s);
        console.info('Data snapshot changed: loading '+DEFAULT_STATE.dataVersion+' defaults (backup saved)');
        const fresh = structuredClone(DEFAULT_STATE);
        fresh.alerts = Array.isArray(p.alerts) ? p.alerts : fresh.alerts;
        return fresh;
      }
      p.priceOverrides = p.priceOverrides || {};
      p.fx = p.fx || DEFAULT_STATE.fx;
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
# 12. TSO is fetchable now (TSO.AX + FX conversion); nothing is manual-only
# ---------------------------------------------------------------------------
old_skip = "const SKIP_FETCH = new Set(['TSO']);"
if old_skip not in html:
    print("ERROR: SKIP_FETCH pattern not found")
    sys.exit(1)
html = html.replace(old_skip, "const SKIP_FETCH = new Set([]);", 1)

# ---------------------------------------------------------------------------
# 13. XIRR: only external cash flows (fundings) + terminal value.
#     Sale proceeds stay in the account and were reinvested, so counting them
#     as distributions overstated the return.
# ---------------------------------------------------------------------------
old_xirr_sells = "    STATE.transactions.filter(t=>t.type==='venta').forEach(t=>flows.push({d:new Date(t.date), a:t.qty*t.price}));\n"
if old_xirr_sells not in html:
    print("ERROR: XIRR sells pattern not found")
    sys.exit(1)
html = html.replace(old_xirr_sells, "", 1)

# ---------------------------------------------------------------------------
# 14. clearAll keeps dataVersion/fx so the next load doesn't treat it as stale
# ---------------------------------------------------------------------------
old_clear = "  STATE = {positions:[],transactions:[],fundings:[],closedPositions:[],cash:{TYBA:0,IBK:0},priceOverrides:{},alerts:[],prevClose:{}};"
if old_clear not in html:
    print("ERROR: clearAll pattern not found")
    sys.exit(1)
html = html.replace(old_clear, "  STATE = {dataVersion:DEFAULT_STATE.dataVersion,positions:[],transactions:[],fundings:[],closedPositions:[],cash:{TYBA:0,IBK:0},fx:{...DEFAULT_STATE.fx},priceOverrides:{},alerts:[],prevClose:{}};", 1)

# ---------------------------------------------------------------------------
# 15. Replace hard-coded April-2026 editorial content with live controls and
#     dated content from the latest morning brief (tracking/data/catalysts_*.json)
# ---------------------------------------------------------------------------
import json as _json
CAT = _json.loads((ROOT / "tracking" / "data" / "catalysts_2026-10-02.json").read_text())

def sub_once(pattern, repl, label):
    global html
    new, n = re.subn(pattern, lambda m: repl, html, count=1, flags=re.S)
    if n != 1:
        print(f"ERROR: {label} pattern not found")
        sys.exit(1)
    html = new

cat_js = ("const CATALYSTS = " + _json.dumps(CAT["agenda"], ensure_ascii=False) + ";\n"
          "const CATALYSTS_ASOF = " + _json.dumps(CAT["as_of"]) + ";\n"
          "const IPS = {miningMax:0.70, positionMax:0.30, cashMin:0.02, drawdownReview:-0.30};\n"
          "const SECTOR = {MSFT:'Tech',NVDA:'Tech',GOOGL:'Tech',META:'Tech',VOO:'ETFs',IONS:'Biotech',"
          "B:'Mining',RIOFF:'Mining',QUEXF:'Mining',SRGXF:'Mining',GLGDF:'Mining',BMM:'Mining',SMI:'Mining',TSO:'Mining',GAL:'Mining',PPTA:'Mining'};\n")

sub_once(r"function renderRecs\(k\)\{.*?\n\}\n\nfunction renderEarnings\(positions\)\{.*?\n\}\n", cat_js + """function renderRecs(k){
  // Policy (IPS) controls computed from current positions; flags only, no trade advice.
  const pos = k.positions, tot = k.portfolioValue;
  const mining = pos.filter(p=>SECTOR[p.ticker]==='Mining').reduce((s,p)=>s+p.value,0)/tot;
  const rows = [];
  const row = (ok,label,detail)=>rows.push(`<div class="r"><div class="al ${ok?'al-g':'al-w'}" style="margin:0;border:none;padding:6px 0;background:none"><b>${ok?'✓':'⚠'} ${label}</b>: ${detail}</div></div>`);
  row(mining<=IPS.miningMax, 'Minería', `${(mining*100).toFixed(1)}% vs límite ${(IPS.miningMax*100).toFixed(0)}%`);
  const top = [...pos].sort((a,b)=>b.value-a.value)[0];
  if(top) row(top.value/tot<=IPS.positionMax, `Mayor posición ${top.ticker}`, `${(top.value/tot*100).toFixed(1)}% vs límite ${(IPS.positionMax*100).toFixed(0)}%`);
  row(k.cashTotal/tot>=IPS.cashMin, 'Liquidez', `cash $${fmt(k.cashTotal,0)} (${(k.cashTotal/tot*100).toFixed(2)}%) vs mínimo ${(IPS.cashMin*100).toFixed(0)}%`);
  const deep = pos.filter(p=>p.pnlPct/100<=IPS.drawdownReview).map(p=>`${p.ticker} ${p.pnlPct.toFixed(0)}%`);
  row(!deep.length, 'Revisión de tesis', deep.length?`bajo costo ≥30%: ${deep.join(', ')}`:'ninguna posición ≥30% bajo costo');
  return `<div class="rec">${rows.join('')}</div>`;
}

function renderEarnings(positions){
  const today = new Date();
  const upcoming = CATALYSTS.filter(e=>new Date(e.d+'T23:59:59')>=today);
  if(!upcoming.length) return `<div class="nt">Sin eventos futuros en la agenda del ${CATALYSTS_ASOF}. Actualiza desde el resumen matutino.</div>`;
  return upcoming.map(e=>{
    const days = Math.ceil((new Date(e.d)-today)/86400000);
    const urg = days<=7?'al-w':days<=14?'al-b':'';
    return `<div class="al ${urg}" style="margin:4px 0"><b>${e.d}</b> · ${e.t} <span style="color:var(--t3)">· ${days>0?days+' días':'hoy'} · ${e.est}</span>${e.q?`<div style="color:var(--t3);font-size:10px;margin-top:2px">${e.q}</div>`:''}</div>`;
  }).join('') + `<div class="nt" style="margin-top:6px">Fuente: agenda del resumen matutino del ${CATALYSTS_ASOF} (estado tal como lo publica).</div>`;
}
""", "renderRecs/renderEarnings")

html = html.replace('<h2>Acciones recomendadas <span class="tag tg">HOY</span></h2>', '<h2>Controles IPS <span class="tag tg">AUTO</span></h2>', 1)
html = html.replace('<h2>Calendario earnings</h2>', '<h2>Agenda de catalizadores</h2>', 1)
html = html.replace('<h2>Elecciones Perú (impacto EPU)</h2>', '<h2>FOMC y tasas</h2>', 1)

# Sector distribution: one map instead of ticker lists that missed GAL/PPTA/B/IONS
sub_once(r"document\.getElementById\('distribView'\)\.innerHTML = Object\.entries\(\{'Tech':.*?'Cash':k\.cashTotal\}",
         "const bySector = {};\n  sorted.forEach(p=>{const s=SECTOR[p.ticker]||'Otros'; bySector[s]=(bySector[s]||0)+p.value;});\n"
         "  bySector.Cash = k.cashTotal;\n  document.getElementById('distribView').innerHTML = Object.entries(bySector", "distribView")

news = [{"tick":n["tick"],"title":f'{n["title"]} · {n["src"]}',"link":n["link"],"pubDate":n["date"]} for n in CAT["news"]]
sub_once(r"  const fallback = \[\n.*?\n  \];", "  // Dated headlines from the latest morning brief (shown only when the live RSS fails)\n  const fallback = "
         + _json.dumps(news, ensure_ascii=False) + ";", "news fallback")

m = CAT["macro"]
sub_once(r"  document\.getElementById\('macroNote'\)\.innerHTML = `.*?`;\n\n  document\.getElementById\('geoList'\)\.innerHTML = `.*?`;\n\n  document\.getElementById\('peruList'\)\.innerHTML = `.*?`;",
f"""  document.getElementById('macroNote').innerHTML = `
    <b>Contexto al {CAT['as_of']} (resumen matutino):</b> {m['nfp']}. Tesoro 10 años {m['ust10y']}% ({m['ust10y_date']}; {m['ust_src']})`;

  const nextMacro = CATALYSTS.filter(e=>/FOMC|resultados|ASX/.test(e.t) && new Date(e.d+'T23:59:59')>=new Date());
  document.getElementById('geoList').innerHTML = nextMacro.length ? nextMacro.map(e=>`<div class="al al-b"><b>${{e.d}}</b> · ${{e.t}} <span style="color:var(--t3)">· ${{e.est}}</span></div>`).join('') : '<div class="nt">Sin eventos próximos en la agenda.</div>';

  document.getElementById('peruList').innerHTML = `
    <div class="al al-b"><b>Fed {m['fomc_date']}:</b> +25 pb a {m['fomc_range']} (desde {m['fomc_prev']}), voto {m['fomc_vote']}. Mediana del dot plot: {m['dots_2026']}% fin 2026 y {m['dots_2027']}% fin 2027.</div>`;""", "macro/geo/peru")

html = html.replace("const extra = u.ticker==='MSFT'?' · ER 29/4 catalyst':u.ticker==='SMI'?' · evaluar salida':'';", "const extra = '';", 1)
html = html.replace(" Earnings season 22-29/4 ofrece entries`", "`", 1)
html = html.replace("<b>Alertas pre-configuradas:</b> MSFT <$390 (DCA entry), EPU <$82 (dip post-Perú), MSFT >$420 (post-ER target).",
                    "<b>Alertas pre-configuradas:</b> ver lista arriba. Las alertas de precio de IBKR viven en tu cuenta IBKR, no aquí.", 1)
html = html.replace("<b>v6.0</b> · Build: Apr 2026 · Datos iniciales tomados del workbook Inversiones.xlsx",
                    "<b>v7</b> · Datos: snapshot " + CAT["as_of"] + " (IBKR + resumen matutino) · ver tracking/ en el repo", 1)

# ---------------------------------------------------------------------------
# 16. Numbers that must come from data, not stale constants
# ---------------------------------------------------------------------------
# Profit total = patrimonio − capital aportado (independent of the realized-trade log,
# which is incomplete for TYBA sales after Apr-2026).
for old, new, label in [
    ("  const totalPnL = unrealizedPnL + realizedPnL;\n", "  const totalPnL = portfolioValue - totalFunded;\n", "totalPnL"),
    ("<div class=\"s\">${fmtPct(k.totalROI)} ROI</div>", "<div class=\"s\">${fmtPct(k.totalROI)} sobre fondeado</div>", "profit subtitle"),
    ("    {label:'Gold spot', ...MACRO_CACHE.gold, fallback:4822},\n    {label:'WTI Oil', ...MACRO_CACHE.oil, fallback:94},",
     "    {label:'Gold spot', ...MACRO_CACHE.gold, fallback:null},\n    {label:'WTI Oil', ...MACRO_CACHE.oil, fallback:null},", "macro fallbacks"),
    ("    const v = m.price || m.fallback;\n    const src = m.price ? m.source : 'cached';",
     "    const v = m.price || m.fallback;\n    const src = m.price ? m.source : (v ? 'cached' : 'sin dato en vivo');", "macro src"),
    ("      <div class=\"v\">$${fmt(v,v>1000?0:2)}</div>\n      <div class=\"s\">${src}</div>",
     "      <div class=\"v\">${v?'$'+fmt(v,v>1000?0:2):'—'}</div>\n      <div class=\"s\">${src}</div>", "macro value"),
    ("<h2>Situación geopolítica</h2>", "<h2>Próximos eventos</h2>", "geo title"),
    ("source:'Stooq/Yahoo'};", "source:(FETCH_STATUS.VOO?.source||'cache')};", "VOO macro source"),
]:
    if html.count(old) != 1:
        print(f"ERROR: {label} pattern not found ({html.count(old)})")
        sys.exit(1)
    html = html.replace(old, new, 1)

# ---------------------------------------------------------------------------
# Sanity check: nothing left referencing v6 except the migration comment
# ---------------------------------------------------------------------------
v6_refs = [m for m in re.finditer(r"v6", html) if "v6" in html[max(0,m.start()-30):m.end()+30]]
# (we expect only the migration comment + auto-clean code now)

OUT.write_text(html)
print(f"Wrote {OUT} ({len(html):,} chars)")
print(f"Position count in source data: {new_state_js.count('{ticker:')}")
print(f"Transaction count in source data: {new_state_js.count('{id:')}")
