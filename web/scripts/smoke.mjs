// Frontend smoke test (SW-27) – no extra packages: drives headless Edge/Chrome over the DevTools protocol (Node 22 WebSocket).
// Needs the running app (pnpm dev on :3000 + statagent web on :8000).
//   node scripts/smoke.mjs                 all pages: renders, no uncaught exceptions / console errors, expected text and links
//   node scripts/smoke.mjs --frage         additionally asks one question in „Fragen“ and waits for the answer card
// Env: SMOKE_BASE (default http://localhost:3000), BROWSER (path to msedge/chrome).
import { spawn } from "node:child_process";
import { existsSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const BASE = process.env.SMOKE_BASE ?? "http://localhost:3000";
const CANDIDATES = [
  process.env.BROWSER,
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "/usr/bin/google-chrome",
  "/usr/bin/chromium",
].filter(Boolean);
const browser = CANDIDATES.find((p) => existsSync(p));
if (!browser) {
  console.error("Kein Edge/Chrome gefunden – Pfad in BROWSER setzen.");
  process.exit(2);
}

// [path, text that must appear, selector that must exist (links that must work)]
const PAGES = [
  ["/", "StatAgent", 'a[href="/dashboard"]'],
  ["/dashboard", "Beschäftigungsverhältnisse am Stichtag", "svg.recharts-surface"],
  ["/lieferungen", "Problemmatrix", 'a[href^="/laeufe?lauf="]'],
  ["/lieferungen?ansicht=dateien&q=lieferung_2025-06", "Paketdateien", "table"],
  ["/laeufe", "Monatslauf starten", "table"],
  ["/laeufe?lauf=171", "Laufdetail", 'a[href^="/qualitaetsberichte?monat="]'],
  ["/qualitaetsberichte?monat=2025-06&regelwerk=basis", "Qualitätsbericht", 'a[href^="/laeufe?lauf="]'],
  ["/klassifikationen", "Klassifikationen", "input"],
  ["/pensionen", "Pensionen", "svg.recharts-surface"],
  ["/modelle", "Modell", "body"],
  ["/fragen", "Frage", "textarea"],
  ["/agent", "Agent", "textarea"],
  ["/freigaben", "Freigaben", 'a, button'],
  ["/protokoll", "Protokoll", 'a[href^="/freigaben?regel="], a[href^="/qualitaetsberichte?"]'],
  ["/exporte", "Exporte", "table"],
];

const port = 9300 + Math.floor(Math.random() * 500);
const profile = mkdtempSync(join(tmpdir(), "smoke-"));
const proc = spawn(browser, ["--headless=new", "--disable-gpu", `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "about:blank"],
  { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let targets = [];
for (let i = 0; i < 60 && !targets.some((t) => t.type === "page"); i++) {
  try { targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); } catch { /* starting */ }
  await sleep(250);
}
const ws = new WebSocket(targets.find((t) => t.type === "page").webSocketDebuggerUrl);
let id = 0;
const pending = new Map();
const problems = [];
ws.onmessage = (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m.result ?? m.error); pending.delete(m.id); }
  if (m.method === "Runtime.exceptionThrown") problems.push(`Exception: ${m.params.exceptionDetails?.exception?.description ?? m.params.exceptionDetails?.text}`);
  if (m.method === "Runtime.consoleAPICalled" && m.params.type === "error")
    problems.push(`console.error: ${m.params.args.map((a) => a.value ?? a.description ?? "").join(" ").slice(0, 200)}`);
};
await new Promise((r) => (ws.onopen = r));
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const evaluate = async (expr) => (await send("Runtime.evaluate", { expression: expr, returnByValue: true })).result?.value;
await send("Page.enable");
await send("Runtime.enable");
await send("Emulation.setDeviceMetricsOverride", { width: 1400, height: 1000, deviceScaleFactor: 1, mobile: false });

async function waitFor(expr, ms) {
  const end = Date.now() + ms;
  while (Date.now() < end) {
    if (await evaluate(expr)) return true;
    await sleep(300);
  }
  return false;
}

let failed = 0;
for (const [path, text, selector] of PAGES) {
  problems.length = 0;
  const t0 = Date.now();
  await send("Page.navigate", { url: BASE + path });
  const hasText = await waitFor(`document.body && document.body.innerText.includes(${JSON.stringify(text)})`, 15000);
  const hasSel = await waitFor(`!!document.querySelector(${JSON.stringify(selector)})`, 10000);
  await sleep(500);
  const ok = hasText && hasSel && problems.length === 0;
  if (!ok) failed++;
  console.log(`${ok ? "ok  " : "FAIL"} ${path} (${Date.now() - t0} ms)${hasText ? "" : ` – Text „${text}“ fehlt`}${hasSel ? "" : ` – ${selector} fehlt`}`);
  for (const p of problems) console.log(`       ${p}`);
}

if (process.argv.includes("--frage")) {
  problems.length = 0;
  const q = "Wie viele Männer und Frauen waren im Juli 2026 beschäftigt?";
  await send("Page.navigate", { url: `${BASE}/fragen?frage=${encodeURIComponent(q)}` });
  const card = await waitFor(`document.body.innerText.includes("Verwendete Dateien") && document.body.innerText.includes("Zahlen geprüft")`, 45000);
  if (!card || problems.length) failed++;
  console.log(`${card && !problems.length ? "ok  " : "FAIL"} Fragen: „${q}“ → Karte mit Claim-Check und verwendeten Dateien`);
  for (const p of problems) console.log(`       ${p}`);
}

ws.close();
proc.kill();
try { rmSync(profile, { recursive: true, force: true }); } catch { /* browser may still hold files */ }
console.log(failed ? `${failed} Prüfung(en) fehlgeschlagen` : "Alle Seiten in Ordnung");
process.exit(failed ? 1 : 0);
