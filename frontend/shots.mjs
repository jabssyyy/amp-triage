/** Screenshot every screen so the UI is actually inspected, not just compiled.
 *  Run: node shots.mjs   (needs vite on 5173 and the API on 8000)
 */
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

const OUT = "../reports/ui";
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 950 } });

const problems = [];
page.on("console", (m) => {
  if (m.type() === "error") problems.push(`console: ${m.text().slice(0, 200)}`);
});
page.on("pageerror", (e) => problems.push(`pageerror: ${String(e).slice(0, 200)}`));
page.on("requestfailed", (r) => problems.push(`requestfailed: ${r.url().slice(0, 120)}`));

const base = "http://localhost:5173";

async function shot(name, path, prep) {
  await page.goto(base + path, { waitUntil: "networkidle" });
  if (prep) await prep();
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: true });

  // Horizontal overflow is the classic silent layout bug.
  const overflow = await page.evaluate(() =>
    document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  const empty = await page.evaluate(() => document.body.innerText.trim().length < 80);
  console.log(
    `${name.padEnd(14)} overflow=${overflow}px ${overflow > 2 ? "  <-- HORIZONTAL OVERFLOW" : ""}${empty ? "  <-- PAGE LOOKS EMPTY" : ""}`,
  );
  return { name, overflow, empty };
}

const results = [];
results.push(await shot("1-overview", "/"));

// Shortlist needs time: it scores 300 peptides then runs greedy selection.
results.push(await shot("2-shortlist", "/shortlist", async () => {
  await page.waitForSelector("tbody tr", { timeout: 120000 }).catch(() => {});
  await page.waitForTimeout(1500);
}));

// Stage two candidates for the compare screen.
await page.goto(base + "/shortlist", { waitUntil: "networkidle" });
await page.waitForSelector("tbody tr", { timeout: 120000 }).catch(() => {});
const compareBtns = page.locator('tbody tr button[title*="compare" i]');
if (await compareBtns.count() >= 2) {
  await compareBtns.nth(0).click();
  await compareBtns.nth(1).click();
}
const openBtns = page.locator('tbody tr button[title="Open candidate"]');
if (await openBtns.count()) await openBtns.nth(0).click();
await page.waitForTimeout(6000);
await page.screenshot({ path: `${OUT}/3-candidate.png`, fullPage: true });
console.log("3-candidate    captured");

results.push(await shot("4-compare", "/compare", async () => page.waitForTimeout(8000)));
results.push(await shot("5-whatif", "/whatif", async () => page.waitForTimeout(4000)));
results.push(await shot("6-evidence", "/evidence", async () => page.waitForTimeout(6000)));
results.push(await shot("7-graph", "/graph", async () => page.waitForTimeout(6000)));
results.push(await shot("8-validation", "/validation", async () => page.waitForTimeout(8000)));

// Narrow viewport: does anything break on a laptop screen?
await page.setViewportSize({ width: 1024, height: 800 });
results.push(await shot("9-narrow-shortlist", "/shortlist", async () => {
  await page.waitForSelector("tbody tr", { timeout: 120000 }).catch(() => {});
  await page.waitForTimeout(1500);
}));

await browser.close();

console.log("\n=== issues ===");
const bad = results.filter((r) => r.overflow > 2 || r.empty);
if (!bad.length) console.log("no overflow or empty pages");
else bad.forEach((b) => console.log(` ${b.name}: overflow=${b.overflow} empty=${b.empty}`));

console.log("\n=== runtime errors ===");
const uniq = [...new Set(problems)];
if (!uniq.length) console.log("none");
else uniq.slice(0, 15).forEach((p) => console.log(" " + p));
