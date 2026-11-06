# StatAgent – web frontend

New session? Read `web/STATUS.md` first (handoff: pages, API contracts, conventions, progress, known problems).

German web UI for StatAgent (Next.js 16, React 19, Tailwind v4, shadcn/ui in medlyn styling – see `NOTICE.md`).
All numbers come from the backend API (FastAPI on `http://127.0.0.1:8000`); the browser talks same-origin
via the rewrite `/api/*` → backend (`next.config.ts`, override with `STATAGENT_API`). Works offline: no CDN,
fonts are self-hosted.

## Requirements

- Node 22 (portable: `C:\Users\pickm\tools\node22`; system Node 19 is too old)
- pnpm 10 via corepack (`packageManager: pnpm@10.34.8`)
- Backend running: from the repo root `.venv\Scripts\python.exe -m statagent web`

Dependency rule: only releases older than 7 days – enforced by `minimumReleaseAge: 10080` in
`pnpm-workspace.yaml` (and `.npmrc`); versions are pinned exactly in `package.json` + `pnpm-lock.yaml`.

## Start (Windows PowerShell)

```powershell
$env:Path = "C:\Users\pickm\tools\node22;" + $env:Path
corepack enable --install-directory C:\Users\pickm\tools\node22   # once
cd web
pnpm install          # once
pnpm dev              # http://localhost:3000
# production:
pnpm build; pnpm start
```

## Start (bash / Git Bash)

```bash
export PATH="/c/Users/pickm/tools/node22:$PATH"
corepack enable --install-directory /c/Users/pickm/tools/node22   # once
cd web
pnpm install          # once
pnpm dev              # http://localhost:3000
pnpm build && pnpm start
```

## Pages

Übersicht · Lieferungen (problem matrix, file registry, integrity check via SSE) · Läufe (start run, live
progress, history, run detail) · Qualitätsberichte (findings with classification, revisions, Markdown QB,
Annahmen, Rückfragen) · Klassifikationen (browser, explanation, transition graph) · Pensionen (Tabellen 12/13, carriers, merger graph, delivered cells) · Dashboard (optional model corridor) · Modelle (model card, detector heatmap, corridor per series) · Fragen
(streamed chat with StatCards, Rückfrage chips, claim check, pin to dashboard, CSV) · Exporte · Agent ·
Freigaben (approve/reject as the logged-in named person) · Protokoll. `Strg+K` opens the command palette.

Login = name of a person, stored only in this browser (localStorage); the API rejects placeholders (T7).
