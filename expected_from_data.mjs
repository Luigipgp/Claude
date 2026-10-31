// Independent expected values computed straight from the latest tracking/data snapshots,
// so the tests check the dashboard against broker data instead of hard-coded numbers.
import { readFileSync, readdirSync } from "node:fs";

const dir = new URL("./tracking/data/", import.meta.url);
const latest = (prefix) =>
  readdirSync(dir).filter((f) => f.startsWith(prefix) && f.endsWith(".json")).sort().at(-1);
export const ibkFile = latest("ibk_");
export const tybaFile = latest("tyba_");
export const ibk = JSON.parse(readFileSync(new URL(ibkFile, dir), "utf8"));
export const tyba = JSON.parse(readFileSync(new URL(tybaFile, dir), "utf8"));

const fx = ibk.fx_to_usd;
let value = 0, cost = 0;
for (const p of ibk.positions) { value += p.value * fx[p.ccy]; cost += p.avg * p.qty * fx[p.ccy]; }
for (const p of tyba.positions) { value += p.qty * p.price; cost += p.cost; }
export const cash = { IBK: ibk.summary.total_cash_value, TYBA: tyba.cash_usd };
export const expected = {
  portfolioValue: value + cash.IBK + cash.TYBA,
  unrealizedPnL: value - cost,
  funded: tyba.external_contributions_usd,
};
expected.totalPnL = expected.portfolioValue - expected.funded;
export const shares = Object.fromEntries([...ibk.positions, ...tyba.positions].map((p) => [p.ticker, p.qty]));
