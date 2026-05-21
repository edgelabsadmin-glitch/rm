# Pulse front-end (`03_build/front/`)

The EDGE Pulse web shell — **spec 034**. React 18 + Vite + TypeScript + Tailwind v3,
with Tier-0 design tokens plumbed through. This is the chrome + routing skeleton;
feature surfaces land in specs 035–045.

## Stack (per Design 11 ADR-005 + pre-034 audit dispositions)

- **Vite + React 18 + TypeScript**
- **Tailwind v3** (not v4 — ecosystem not ready), theme generated from Tier-0
  Appendix A → `tailwind.config.ts`, backed by `src/styles/tokens.css` (single
  source of truth; dynamic values like the conic ring + Pulse Bar keyframes live
  in the CSS file).
- **Inter** self-hosted via `@fontsource-variable/inter` (imported in `main.tsx`).
- **framer-motion** — per-component fade-and-lift (`<FadeLift>`); the Pulse Bar is
  CSS keyframes, not framer-motion.
- **shadcn/ui** as substrate (copy-in primitives, re-tokened) — see
  `src/components/README.md` for the substrate-vs-custom boundary.
- **React Query** (server state) · **react-router-dom v6** (routing) ·
  **react-hook-form** (forms) · `localStorage` for filter persistence.
  No Redux / Zustand / IndexedDB.

## Develop

```bash
cd 03_build/front
npm install
npm run dev        # http://localhost:5173
```

The dev server proxies `/api/*` → the local Pulse FastAPI (`VITE_API_BASE`,
default `http://localhost:8000`). Set `VITE_API_BASE` for a different back-end.

```bash
npm run build      # tsc -b && vite build → dist/
npm run typecheck
npm run preview
```

## Auth (stubbed in spec 034)

The shell runs against a **hardcoded demo session** (`src/session/useSession.ts`:
`{ id: 'rm-demo', name: 'Demo RM', email: 'demo@onedge.co', role: 'admin' }`).
Real Google Workspace OAuth is **spec 043's** Definition of Done (pre-034 audit
sequencing decision). Front-end role checks gate route *visibility* only —
server-side scope (spec 042 `derive_scope`) is the security boundary.

## Routes

`/` → `/accounts` · `/accounts` · `/accounts/:id` · `/actions` (Queue) ·
`/constellation` · `/ceo` · `/submit` · `/admin/{signals,outcomes,settings}`
(admin-gated). All are placeholders until their feature specs land. The Pulse Bar
renders on every authed route (chrome singleton); login is pre-shell.

## Deploy (Vercel — operator step)

> **Do not let CI/agents deploy.** This is a manual operator step after the spec lands.

1. **Rename the Vercel project to `pulse`** so the URL is **`pulse.vercel.app`**,
   not the repo-default `rm.vercel.app` (the product is white-labeled "Pulse"; the
   repo name `rm` is internal). Pre-034 audit disposition D8. A custom
   `*.onedge.co` domain is deferred to post-demo (needs operator DNS).
2. Project settings: framework **Vite**, build `npm run build`, output `dist`
   (already declared in `vercel.json`, incl. the SPA rewrite so deep links resolve).
3. Set env `VITE_API_BASE` to the deployed Pulse API origin (pulse-api Fly deploy
   is pending — Week 4; until then the shell renders with placeholders).
4. Deploy:
   ```bash
   cd 03_build/front
   vercel --prod        # or connect the GitHub repo with root dir 03_build/front
   ```
