# Open Decisions

## Still open (can wait until later in week 1)

### 1. Custom domain

Where does the dashboard live? Suggested:
- `campaigns.frontofficesports.com` (cleanest)
- `campaigns.fosreports.com` (matches existing reporting infra naming)
- Default Cloud Run URL is fine for v1; custom domain is a polish step

### 2. Editor vs. viewer separation

Three editors, ~10 viewers across AM/Sales/Partnership Marketing. Options:
- **Same app, role-based UI** — viewers don't see Upload/Manage pages. Roles in Firestore, enforced in app. (Recommended.)
- **Separate read-only deployment** — same data, no upload UI in the build. Simpler app code, more deploy overhead.

## Confirmed

- **Build philosophy**: from-scratch Python on Cloud Run, not Retool
- **GCP project**: **new project** (not reusing Google Reports). Cleaner separation of IAM, billing, and blast radius. Service account, IAP config, and Cloud Run service all live in this new project.
- **IAP scope**: **`frontofficesports.com` only**. No external/agency access. Editors and viewers all sign in with FOS Workspace Google accounts. IAP is a 5-minute config in the Cloud Run service settings.
- **HTML treatment**: **mine for design**. Copy CSS variables, KPI card layout, status pill colors, brand color tokens (`--scoreboard`, `--turf`, `--red-card`, etc.), freshness banner pattern into Streamlit components. The existing HTML files stay untouched as a style reference document.
- **Source priority**: MS CSV first, Google Ads second; everything else deferred
- **Refresh cadence**: user-driven uploads (twice weekly default, daily for tight flights), no scheduled automation in v1
- **Recap deliverable**: handed to Claude Design from this tool; not built into v1
- **Benchmarks**: nice-to-have, deferred
