# Architecture (v3 — post-Pulse design)

## What changed from v2

The original "Streamlit-only on Cloud Run" plan was right for the admin surface, but wrong for the viewer. After Claude Design produced **PULSE** — a sophisticated React-based dashboard with bespoke per-campaign layouts (US Bank's 3-component shape, episode-level breakdowns, custom typography game) — translating it to Streamlit would lose ~30% visual fidelity and take 2–3 weeks. The design quality is too high to throw away.

**Hybrid architecture instead.** Two surfaces, different audiences, different tools.

## Architecture

```
┌──── Editors (Content Strategist, Social Analyst) ────┐
│                                                       │
│   Streamlit on Cloud Run  (admin)                    │
│     - upload CSVs                                     │
│     - manage campaigns                                │
│     - "Refresh Dashboard" button                      │
│                                                       │
└─────────────┬─────────────────────────────────────────┘
              │
              │ writes parsed + computed data
              ▼
        ┌─────────────────┐
        │  GCS bucket     │
        │   data.js       │  (overwritten on each refresh)
        │   raw uploads/  │
        └────────┬────────┘
                 │
                 │ fetched on load
                 ▼
┌──── Viewers (AM, Sales, Partnership Marketing) ────┐
│                                                     │
│   Pulse static React app on Cloud Run  (viewer)    │
│     - viewer/index.html                             │
│     - read-only                                     │
│     - matches the design 1:1                        │
│                                                     │
└─────────────────────────────────────────────────────┘

Both Cloud Run services gated by IAP, frontofficesports.com only.
Firestore stores campaign config + snapshot history (operational layer).
BigQuery (later) stores normalized post-level metrics for trends.
```

## Why this is right

- **Editors get a forms-friendly tool.** Streamlit is ideal for upload + CRUD.
- **Viewers get a beautiful dashboard.** The Pulse design ships pixel-perfect.
- **The "two surfaces" split actually solves a real audience split** — editors and viewers want different things. We're not duplicating UI; we're matching tool to job.
- **Streamlit's scope shrinks**, which makes the build smaller and faster.
- **The Pulse design files become the source of truth for the viewer.** No translation loss.

## Repo structure (updated)

```
fos-campaign-tracker/
├── app/                          # Streamlit admin
│   ├── main.py                   # Streamlit entry — landing + parser demo
│   ├── pages/                    # multi-page Streamlit routes (TBD)
│   ├── parsers/                  # CSV → NormalizedPost (DONE for MS + GAds)
│   ├── viewer/
│   │   ├── data_contract.py      # JSON shape spec the Pulse viewer expects
│   │   └── render.py             # (TBD) PulsePayload → data.js string
│   ├── models/                   # (TBD) Pydantic Campaign, Snapshot
│   ├── storage/                  # (TBD) Firestore + GCS clients
│   ├── compute/                  # (TBD) pacing, callouts, hero post selection
│   └── components/styles.py      # Pulse-aligned Streamlit CSS
├── viewer/                       # Pulse React static app
│   ├── index.html                # entry; loads external scripts
│   ├── standalone.html           # single-file inlined version
│   ├── styles.css                # design system
│   ├── data.sample.js            # sample data showing target shape
│   ├── components.jsx            # shared React components
│   ├── overview.jsx              # overview page
│   ├── campaign.jsx              # CONTENT campaign detail
│   ├── usbank.jsx                # SOCIAL bespoke (US Bank x NFL Draft)
│   ├── tweaks-panel.jsx          # theme/palette/density tweaks
│   └── README.md                 # explains regen pipeline
├── tests/                        # parser tests against real fixtures (18 passing)
├── Dockerfile, pyproject.toml    # ...
└── README.md
```

## Data flow on a refresh

1. Content Strategist uploads MS CSV in Streamlit
2. `app/parsers/measure_studio.py` parses → `list[NormalizedPost]`
3. Streamlit shows preview, user clicks "Commit snapshot"
4. Snapshot written to Firestore (config) + GCS (raw CSV) + BigQuery (post-level rows)
5. User clicks "Refresh Dashboard"
6. `app/compute/...` rolls up posts → campaign-level metrics, picks hero post, generates pacing/status, produces a `PulsePayload`
7. `app/viewer/render.py` serializes `PulsePayload` → `data.js` string
8. Written to `gs://pulse-data/data.js`
9. Pulse viewer (next page load) fetches new `data.js` → renders updated dashboard

Key property: **the viewer's React code never changes**; only the data file is regenerated. New campaigns appear automatically.

## What needs to happen to wire the viewer to live data

The viewer currently uses `data.sample.js` (hardcoded sample). To make it dynamic:

1. ✅ **Document the data shape** → `app/viewer/data_contract.py` (DONE)
2. ⬜ **Refactor `usbank.jsx`** to read US Bank components from `window.UB_COMPONENTS` (currently hardcoded inline). Single ~40-line change.
3. ⬜ **Implement `render.py`** to serialize `PulsePayload` → JS file.
4. ⬜ **Wire the viewer's `index.html`** to load `data.js` (live) with fallback to `data.sample.js` (dev).

## Two Cloud Run services or one?

**Two**, simpler IAM:
- `pulse-admin` — Python/Streamlit container, the admin app
- `pulse-viewer` — nginx or simple Python static server, just serves `viewer/` directory + fetches `data.js` from GCS

Both behind the same IAP allowlist (frontofficesports.com). Shared GCP project. Editors hit `admin.campaigns.frontofficesports.com`, viewers hit `campaigns.frontofficesports.com` (or just one URL with role-based redirect).

Single service with both is also viable — Streamlit + custom Tornado route to serve viewer. More complex but one deploy. **Two services is cleaner.**

## Stack (unchanged from v2 except viewer additions)

| Layer | Choice |
|---|---|
| Admin runtime | Python 3.12 + Streamlit on Cloud Run |
| Viewer runtime | Static HTML + React 18 + Babel-in-browser; served by nginx on Cloud Run |
| Templating | None on viewer (data.js is JS, not template) |
| Storage | Firestore (operational) + GCS (raw + data.js) + BigQuery (analytical, later) |
| Auth | IAP, frontofficesports.com only |
| Charts | Plotly (admin) + native HTML/SVG (viewer, already built) |
| CI/CD | Cloud Build → both Cloud Run services on git push |

## Deferred to v2

Same as before. Plus:
- **Two-deployment story** — figure out custom domain + how editors navigate to admin app from viewer (probably a "manage" link in viewer header that bounces to admin URL)
- **Refactor of US Bank-specific bespoke** — the design hardcodes Mauigoa/Tate/Downs/Mendoza. For the next NFL Draft campaign or any new social-only multi-component campaign, we'll either generalize the layout or accept that bespoke campaigns ship as one-off views.
