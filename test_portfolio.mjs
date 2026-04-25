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

console.log("\n[2] DEFAULT_STATE content matches Excel");
test("14 active positions", () => {
  const S = getState();
  assert.equal(S.positions.length, 14, `got ${S.positions.length}`);
});
test("positions contain new ticker B (Barnes)", () => {
  const b = getState().positions.find((p) => p.ticker === "B");
  assert.ok(b, "missing 'B' position");
  assert.equal(b.shares, 100);
  assert.equal(b.broker, "TYBA");
});
test("MSFT updated to 22 shares (was 18)", () => {
  const m = getState().positions.find((p) => p.ticker === "MSFT");
  assert.equal(m.shares, 22);
});
test("TSO updated to 8800 shares (was 4284)", () => {
  const t = getState().positions.find((p) => p.ticker === "TSO");
  assert.equal(t.shares, 8800);
});
test("transactions count matches Excel (~137)", () => {
  const n = getState().transactions.length;
  assert.ok(n >= 130 && n <= 140, `got ${n}`);
});
test("fundings include latest 2026-04-20 IBK $3500", () => {
  const f = getState().fundings.find(
    (x) => x.date === "2026-04-20" && x.amount === 3500
  );
  assert.ok(f, "missing latest funding");
});
test("fundings sum to ~$88,398", () => {
  const total = getState().fundings.reduce((s, f) => s + f.amount, 0);
  assert.ok(Math.abs(total - 88397.75) < 1, `got ${total}`);
});
test("cash balances match Excel", () => {
  const S = getState();
  assert.equal(S.cash.TYBA, 3761.2);
  assert.equal(S.cash.IBK, 95.36);
});

console.log("\n[3] Calculations");
// Reset PRICES to prevClose values so calc tests are deterministic
// (init() may have populated PRICES with mock fetch values).
ev("STATE.positions.forEach(p => { PRICES[p.ticker] = STATE.prevClose?.[p.ticker] || p.costAvg; });");
test("calcKPIs returns sane patrimonio (~$128k)", () => {
  const k = ev("calcKPIs()");
  assert.ok(k.portfolioValue > 120000 && k.portfolioValue < 135000,
    `got ${k.portfolioValue}`);
});
test("calcKPIs unrealizedPnL is positive", () => {
  const k = ev("calcKPIs()");
  assert.ok(k.unrealizedPnL > 0, `got ${k.unrealizedPnL}`);
});
test("calcXIRR returns positive number", () => {
  const x = ev("calcXIRR()");
  assert.ok(x !== null && x > 0, `got ${x}`);
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
test("YAHOO_SUFFIX maps TSO and SMI to .AX", () => {
  assert.equal(ev("YAHOO_SUFFIX.TSO"), "TSO.AX");
  assert.equal(ev("YAHOO_SUFFIX.SMI"), "SMI.AX");
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
  const r = await evAsync(`
    SKIP_FETCH.delete("TSO");
    const r = await fetchTicker("TSO");
    SKIP_FETCH.add("TSO");
    return r;
  `);
  assert.ok(r);
  assert.equal(r.source, "yahoo");
  assert.ok(fetchCalls.some((u) => u.includes("TSO.AX")),
    "should have used .AX suffix");
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

console.log("\n=========================================");
console.log(`Results: ${pass} passed, ${fail} failed`);
console.log("=========================================\n");
process.exit(fail ? 1 : 0);
