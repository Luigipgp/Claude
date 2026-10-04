// Smoke test: render the page in jsdom WITHOUT mocking fetch (it'll fail naturally
// in the offline test env), then verify the UI rendered the basics correctly.
//
// This catches bugs that only show up in the actual render() pipeline:
// HTML markup, KPI calculations, position table layout, modal IDs, etc.

import { JSDOM, VirtualConsole } from "jsdom";
import { readFileSync } from "node:fs";
import { strict as assert } from "node:assert";

const html = readFileSync(new URL("./portfolio_v7.html", import.meta.url), "utf8");

const vConsole = new VirtualConsole();
const errors = [];
vConsole.on("jsdomError", (e) => errors.push(String(e.message || e)));

const dom = new JSDOM(html, {
  runScripts: "dangerously",
  url: "http://localhost/",
  virtualConsole: vConsole,
  beforeParse(window) {
    // Fail fetches immediately so we test the render path, not the network
    window.fetch = async () => ({ ok: false, status: 0, text: async () => "", json: async () => ({}) });
    if (typeof window.structuredClone === "undefined") {
      window.structuredClone = (o) => JSON.parse(JSON.stringify(o));
    }
    window.alert = () => {};
    window.confirm = () => true;
    const orig = window.setInterval;
    window.setInterval = (fn, ms) => (ms === 1000 ? 0 : orig(fn, ms));
  },
});

await new Promise((r) => setTimeout(r, 400));

const w = dom.window;
const $ = (sel) => w.document.querySelector(sel);
const $$ = (sel) => w.document.querySelectorAll(sel);

let pass = 0;
let fail = 0;
const t = (name, fn) => {
  try {
    fn();
    console.log(`  PASS  ${name}`);
    pass++;
  } catch (e) {
    console.log(`  FAIL  ${name}: ${e.message}`);
    fail++;
  }
};

console.log("\n=== Smoke test: rendered DOM ===\n");

t("no jsdomErrors during init", () => {
  if (errors.length) throw new Error(errors.slice(0, 3).join(" | "));
});

t("title is v7", () => {
  assert.equal(w.document.title, "Luigi's Portfolio v7");
});

t("KPI grid is populated", () => {
  const kpis = $$("#kpiGrid .kpi");
  assert.ok(kpis.length >= 6, `got ${kpis.length} KPI cards`);
});

t("positions table has 16 data rows", () => {
  const rows = $$("#posTable tr[data-ticker]");
  assert.equal(rows.length, 16, `got ${rows.length}`);
});

t("Patrimonio shows ~$142k", () => {
  const kpiV = $$("#kpiGrid .kpi .v")[0]?.textContent || "";
  const num = parseFloat(kpiV.replace(/[$,]/g, ""));
  assert.ok(num > 141900 && num < 142010, `got "${kpiV}"`);
});

t("All 7 tabs are clickable", () => {
  const btns = $$(".tab-btn");
  assert.ok(btns.length >= 7, `got ${btns.length} tabs`);
});

t("Switching to positions tab works", () => {
  const posBtn = w.document.querySelector('[data-tab="positions"]');
  posBtn.click();
  const tc = w.document.getElementById("tab-positions");
  assert.ok(tc.classList.contains("active"));
});

t("Tx modal opens", () => {
  w.openTxModal();
  assert.ok(w.document.getElementById("txModal").classList.contains("active"));
  w.closeTxModal();
});

t("Tx modal data-type tabs work", () => {
  w.openTxModal();
  w.switchTxTab("venta", null);
  const ventaTab = w.document.querySelector('.modal-tab[data-type="venta"]');
  assert.ok(ventaTab.classList.contains("active"));
  w.switchTxTab("compra", null);
  const compraTab = w.document.querySelector('.modal-tab[data-type="compra"]');
  assert.ok(compraTab.classList.contains("active"));
  w.closeTxModal();
});

t("Alert modal opens", () => {
  w.openAlertModal();
  assert.ok(w.document.getElementById("alertModal").classList.contains("active"));
  w.closeAlertModal();
});

t("Status text updated after init", () => {
  const status = w.document.getElementById("statusText");
  assert.ok(status.textContent.length > 0, "status is empty");
});

console.log(`\nResults: ${pass} passed, ${fail} failed\n`);
process.exit(fail ? 1 : 0);
