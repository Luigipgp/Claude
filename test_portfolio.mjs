// Test runner for portfolio_v7.html
// Loads the HTML in jsdom, mocks fetch, exercises the public functions,
// and asserts the math matches the Excel.
//
// Run: node test_portfolio.mjs

import { JSDOM, VirtualConsole } from "jsdom";
import { readFileSync } from "node:fs";
import { strict as assert } from "node:assert";

const html = readFileSync(new URL("./portfolio_v7.html", import.meta.url), "utf8");

// ---- Set up jsdom with controllable fetch & timers --------------------------
const vConsole = new VirtualConsole();
const consoleErrors = [];
vConsole.on("jsdomError", (e) => consoleErrors.push(String(e)));
vConsole.on("error", (e) => consoleErrors.push(String(e)));

const fetchCalls = [];
// Build a duck-typed response so we don't hit cross-realm issues with Response
const okResp = (body) => ({
  ok: true,
  status: 200,
  text: async () => body,
  json: async () => JSON.parse(body),
});
const fetchMock = async (url, opts = {}) => {
  fetchCalls.push(String(url));
  const u = String(url);
  // Stooq direct URL (not proxied)
  if (u.includes("stooq.com")) {
    return okResp(
      "Symbol,Date,Time,Open,High,Low,Close,Volume\nVOO,2026-04-25,21:00:00,650,660,649,656.42,12345678\n"
    );
  }
  // Yahoo FX pairs (checked before the generic Yahoo mock)
  if (u.includes("query1.finance.yahoo.com") && (u.includes("AUDUSD") || u.includes("CADUSD"))) {
    const rate = u.includes("AUDUSD") ? 0.7 : 0.72;
    return okResp(JSON.stringify({ chart: { result: [{ meta: { regularMarketPrice: rate } }] } }));
  }
  // Yahoo via any proxy: encoded query1.finance.yahoo.com
  if (u.includes("query1.finance.yahoo.com")) {
    return okResp(
      JSON.stringify({
        chart: { result: [{ meta: { regularMarketPrice: 999.99 } }] },
      })
    );
  }
  // Yahoo RSS news
  if (u.includes("feeds.finance.yahoo.com")) {
    return okResp(
      "<rss><channel><item><title><![CDATA[Mock]]></title><link>http://x</link><pubDate>Fri</pubDate></item></channel></rss>"
    );
  }
  return { ok: false, status: 404, text: async () => "", json: async () => ({}) };
};

const dom = new JSDOM(html, {
  runScripts: "dangerously",
  url: "http://localhost/",
  virtualConsole: vConsole,
  beforeParse(window) {
    window.fetch = fetchMock;
    // jsdom 24 doesn't expose structuredClone on window by default
    if (typeof window.structuredClone === "undefined") {
      window.structuredClone = (o) => JSON.parse(JSON.stringify(o));
    }
    // Mute alert() popups during tests
    window.alert = () => {};
    window.confirm = () => true;
    // Stop the 1s setInterval(updateCountdown) from firing during tests
    const origSetInterval = window.setInterval;
    window.setInterval = (fn, ms) => {
      if (ms === 1000) return 0; // suppress countdown
      return origSetInterval(fn, ms);
    };
  },
});

// Wait for init() to mount and for any microtasks to settle
await new Promise((r) => setTimeout(r, 250));

const w = dom.window;
// `let` bindings at script top-level are NOT exposed on window in jsdom.
// Use window.eval() to access them from the same realm.
const ev = (expr) => w.eval(expr);
const getState = () => ev("STATE");

// ===== ASSERTIONS =============================================================

let pass = 0;
let fail = 0;
const test = (name, fn) => {
  try {
    fn();
    console.log(`  PASS  ${name}`);
    pass++;
  } catch (e) {
    console.log(`  FAIL  ${name}`);
    console.log(`        ${e.message}`);
    fail++;
  }
};
const test_async = async (name, fn) => {
  try {
    await fn();
    console.log(`  PASS  ${name}`);
    pass++;
  } catch (e) {
    console.log(`  FAIL  ${name}`);
    console.log(`        ${e.message}`);
    fail++;
  }
};

console.log("\n=== Portfolio v7 test suite ===\n");

console.log("[1] Page basics");
test("title is v7", () => {
  assert.equal(w.document.title, "Luigi's Portfolio v7");
});
test("no jsdom errors during load", () => {
  if (consoleErrors.length) {
    throw new Error("Console errors:\n" + consoleErrors.join("\n"));
  }
});
test("STATE loaded from DEFAULT_STATE", () => {
  const STATE = getState();
  assert.equal(typeof STATE, "object");
  assert.ok(Array.isArray(STATE.positions));
});

console.log("\n[2] DEFAULT_STATE matches broker snapshot (IBKR 4-oct + TYBA 2-oct)");
const shares = (t) => getState().positions.find((p) => p.ticker === t)?.shares;
test("16 active positions (7 IBK + 9 TYBA)", () => {
  const S = getState();
  assert.equal(S.positions.length, 16, `got ${S.positions.length}`);
  assert.equal(S.positions.filter((p) => p.broker === "IBK").length, 7);
  assert.equal(S.positions.filter((p) => p.broker === "TYBA").length, 9);
});
test("B is Barrick Mining (139 sh, TYBA), not Barnes", () => {
  const b = getState().positions.find((p) => p.ticker === "B");
  assert.ok(b, "missing 'B' position");
  assert.equal(b.shares, 139);
  assert.equal(b.broker, "TYBA");
  assert.match(b.note, /Barrick/);
});
test("IBK quantities match IBKR positions", () => {
  assert.equal(shares("RIOFF"), 19000);
  assert.equal(shares("TSO"), 17200);
  assert.equal(shares("SRGXF"), 27000);
  assert.equal(shares("SMI"), 9500);
  assert.equal(shares("GAL"), 17000);
});
test("TYBA quantities match broker (MSFT 16, NVDA 35, PPTA 144, IONS 49)", () => {
  assert.equal(shares("MSFT"), 16);
  assert.equal(shares("NVDA"), 35);
  assert.equal(shares("PPTA"), 144);
  assert.equal(shares("IONS"), 49);
  assert.equal(shares("EPU"), undefined);
});
test("foreign listings flagged with currency", () => {
  const ccy = (t) => getState().positions.find((p) => p.ticker === t)?.ccy;
  assert.equal(ccy("TSO"), "AUD");
  assert.equal(ccy("SMI"), "AUD");
  assert.equal(ccy("GAL"), "CAD");
  assert.equal(ccy("RIOFF"), undefined);
});
test("transactions count matches Excel (~137)", () => {
  const n = getState().transactions.length;
  assert.ok(n >= 130 && n <= 140, `got ${n}`);
});
test("fundings include May-2026 $11,000", () => {
  const f = getState().fundings.find((x) => x.date === "2026-05-27" && x.amount === 11000);
  assert.ok(f, "missing May-2026 funding");
});
test("fundings sum to $99,397.75 (external capital in morning brief)", () => {
  const total = getState().fundings.reduce((s, f) => s + f.amount, 0);
  assert.ok(Math.abs(total - 99397.75) < 0.01, `got ${total}`);
});
test("cash balances match brokers", () => {
  const S = getState();
  assert.equal(S.cash.TYBA, 18.47);
  assert.equal(S.cash.IBK, 85.87);
});

console.log("\n[3] Calculations");
// Reset PRICES to prevClose values so calc tests are deterministic
// (init() may have populated PRICES with mock fetch values).
ev("STATE.positions.forEach(p => { PRICES[p.ticker] = STATE.prevClose?.[p.ticker] || p.costAvg; });");
test("calcKPIs patrimonio = consolidated report $141,954 (±$5)", () => {
  const k = ev("calcKPIs()");
  assert.ok(Math.abs(k.portfolioValue - 141954) < 5, `got ${k.portfolioValue}`);
});
test("unrealized PnL = consolidated report $26,577 (±$5)", () => {
  const k = ev("calcKPIs()");
  assert.ok(Math.abs(k.unrealizedPnL - 26577) < 5, `got ${k.unrealizedPnL}`);
});
test("calcKPIs unrealizedPnL is positive", () => {
  const k = ev("calcKPIs()");
  assert.ok(k.unrealizedPnL > 0, `got ${k.unrealizedPnL}`);
});
test("calcXIRR uses external flows only (in line with brief's 36% XIRR)", () => {
  const x = ev("calcXIRR()");
  // Brief: 36.0% on 2-oct with 17 dated external flows. Terminal date here is "now",
  // so allow a band rather than an exact match.
  assert.ok(x !== null && x > 28 && x < 44, `got ${x}`);
});
test("profit total = patrimonio − fondeado ($42,556 ±$5)", () => {
  const k = ev("calcKPIs()");
  assert.ok(Math.abs(k.totalPnL - (k.portfolioValue - 99397.75)) < 0.01, `got ${k.totalPnL}`);
  assert.ok(Math.abs(k.totalPnL - 42556) < 5, `got ${k.totalPnL}`);
});
test("calcRealizedPnL > 0 (winners > losers historically)", () => {
  const r = ev("calcRealizedPnL()");
  assert.ok(r > 0, `got ${r}`);
});

console.log("\n[4] Fetcher routing");
await test_async("fetchT helper exists and respects timeout", async () => {
  const start = Date.now();
  let aborted = false;
  // Override fetch to hang
  const origFetch = w.fetch;
  w.fetch = (url, opts) =>
    new Promise((res, rej) => {
      if (opts && opts.signal) {
        opts.signal.addEventListener("abort", () => {
          aborted = true;
          rej(new w.DOMException("Aborted", "AbortError"));
        });
      }
      // Never resolves
    });
  await w.fetchT("https://example.com/hang", {}, 200).catch(() => {});
  w.fetch = origFetch;
  const elapsed = Date.now() - start;
  assert.ok(elapsed >= 180 && elapsed < 1500, `elapsed=${elapsed}ms`);
  assert.ok(aborted, "fetch was not aborted");
});
test("OTC_TICKERS set contains the 5 pinks", () => {
  const has = ev("(t)=>OTC_TICKERS.has(t)");
  ["RIOFF", "GLGDF", "QUEXF", "SRGXF", "BMM"].forEach((t) => {
    assert.ok(has(t), `missing ${t} from OTC set`);
  });
});
test("YAHOO_SUFFIX maps TSO/SMI to .AX and GAL to .V", () => {
  assert.equal(ev("YAHOO_SUFFIX.TSO"), "TSO.AX");
  assert.equal(ev("YAHOO_SUFFIX.SMI"), "SMI.AX");
  assert.equal(ev("YAHOO_SUFFIX.GAL"), "GAL.V");
});
test("TSO is no longer manual-only", () => {
  assert.equal(ev("SKIP_FETCH.has('TSO')"), false);
});

// Helper to run async window code that needs to wait for fetches
const evAsync = async (code) =>
  await Promise.resolve(ev(`(async () => { ${code} })()`));

await test_async("fetchTicker for VOO calls Stooq first", async () => {
  fetchCalls.length = 0;
  const r = await evAsync(`return await fetchTicker("VOO");`);
  assert.ok(r);
  assert.equal(r.source, "stooq");
  assert.ok(fetchCalls[0].includes("stooq.com"));
});

await test_async("fetchTicker for RIOFF skips Stooq, goes to Yahoo", async () => {
  fetchCalls.length = 0;
  const r = await evAsync(`return await fetchTicker("RIOFF");`);
  assert.ok(r);
  assert.equal(r.source, "yahoo");
  assert.ok(!fetchCalls.some((u) => u.includes("stooq.com")),
    "should NOT have called Stooq for RIOFF");
});

await test_async("fetchTicker for TSO uses TSO.AX symbol", async () => {
  fetchCalls.length = 0;
  const r = await evAsync(`return await fetchTicker("TSO");`);
  assert.ok(r);
  assert.equal(r.source, "yahoo");
  assert.ok(fetchCalls.some((u) => u.includes("TSO.AX")),
    "should have used .AX suffix");
});

await test_async("TSO price converted AUD->USD with live FX", async () => {
  ev("FX_CACHE = {}");
  const r = await evAsync(`return await fetchTicker("TSO");`);
  assert.equal(r.ccy, "AUD");
  assert.equal(r.localPrice, 999.99);
  assert.ok(Math.abs(r.price - 999.99 * 0.7) < 1e-6, `got ${r.price}`);
});
await test_async("GAL price converted CAD->USD via GAL.V", async () => {
  ev("FX_CACHE = {}");
  fetchCalls.length = 0;
  const r = await evAsync(`return await fetchTicker("GAL");`);
  assert.ok(fetchCalls.some((u) => u.includes("GAL.V")), "should use GAL.V");
  assert.ok(Math.abs(r.price - 999.99 * 0.72) < 1e-6, `got ${r.price}`);
});
await test_async("FX falls back to stored IBKR rate if live rate is implausible", async () => {
  const origFetch = w.fetch;
  w.fetch = async () => ({ ok: true, status: 200, text: async () => "", json: async () => ({ chart: { result: [{ meta: { regularMarketPrice: 999.99 } }] } }) });
  ev("FX_CACHE = {}");
  const r = await evAsync(`return await fetchTicker("SMI");`);
  w.fetch = origFetch;
  assert.ok(Math.abs(r.fx - 0.69535525) < 1e-9, `got fx ${r.fx}`);
});
test("USD tickers are not converted", () => {
  assert.equal(ev("tickerCcy('NVDA')"), "USD");
});

console.log("\n[5] Manual override is permanent (no 24h expiry)");
await test_async("override older than 24h still applies", async () => {
  const r = await evAsync(`
    STATE.priceOverrides["RIOFF"] = {price: 2.5, timestamp: Date.now() - 30*24*60*60*1000};
    const r = await fetchTicker("RIOFF");
    delete STATE.priceOverrides["RIOFF"];
    return r;
  `);
  assert.equal(r.source, "manual");
  assert.equal(r.price, 2.5);
});

console.log("\n[6] Persistence & migration");
test("saveState writes to luigi_portfolio_v7 key", () => {
  ev("saveState()");
  const stored = w.localStorage.getItem("luigi_portfolio_v7");
  assert.ok(stored, "no value stored");
  const parsed = JSON.parse(stored);
  assert.ok(Array.isArray(parsed.positions));
});

test("stale v7 cache is backed up and replaced, alerts kept", () => {
  const stale = { positions: [{ ticker: "EPU", broker: "TYBA", shares: 81, costAvg: 85 }], alerts: [{ id: "x", ticker: "MSFT", condition: "below", price: 1 }], cash: { TYBA: 1, IBK: 1 } };
  w.localStorage.setItem("luigi_portfolio_v7", JSON.stringify(stale));
  const S = ev("loadState()");
  assert.equal(S.dataVersion, ev("DEFAULT_STATE.dataVersion"));
  assert.equal(S.positions.length, 16);
  assert.equal(S.alerts.length, 1);
  assert.ok(w.localStorage.getItem("luigi_portfolio_v7_backup_pre"), "backup missing");
});
test("current-version cache loads as-is", () => {
  ev("saveState()");
  const S = ev("loadState()");
  assert.equal(S.positions.length, 16);
});

console.log("\n=========================================");
console.log(`Results: ${pass} passed, ${fail} failed`);
console.log("=========================================\n");
process.exit(fail ? 1 : 0);
