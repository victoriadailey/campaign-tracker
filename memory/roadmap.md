# MVP Scope & Roadmap

## v1 — 3 weeks

Cut hard. Ship enough to replace the manual workflow for **Live tracking** of Sponsored Social and Longform-with-Cutdowns campaigns, using **Measure Studio CSV + Google Ads CSV** as the only input sources.

### Week 1 — foundations

- Cloud Run + IAP scaffold; FOS Workspace SSO working
- Firestore schema; campaign CRUD page (`3_Manage.py`)
- GCS bucket for raw uploads
- **Measure Studio CSV parser** — wide-to-long melt, Post Group filtering, normalized output
- **Google Ads parsers** — both ad-level and campaign-level
- Upload page (`2_Upload.py`) — file picker, source detection, preview, commit-to-snapshot

### Week 2 — viewing surfaces

- Portfolio page (`0_Portfolio.py`) — card grid of Live campaigns; status pill, impressions pacing, budget pacing, days left
- Campaign detail page (`1_Campaign_Detail.py`) — KPI cards, platform table, top performers (ER + reach), notes
- Pacing logic (`compute/pacing.py`) — status pill calculation: on_track / behind / goal_hit / exceeded / at_risk
- Snapshot persistence with `is_latest` semantics

### Week 3 — polish & deploy

- Lifecycle state UI (planned/live/complete/archived) with auto-transition on flight_end
- Recap mode toggle on detail view (cleaner layout for handoff to Claude Design)
- Custom CSS to match brand colors from existing HTML
- IAP enabled, custom domain (TBD)
- Cloud Build CI/CD on git push
- Internal alpha with Content Strategist + Social Analyst

## Deferred to v2

| Feature | Trigger to build |
|---|---|
| **Auto-generated optimization callouts** ("X is pacing 30% behind, consider redistribution") | After ~10 real campaigns logged so heuristics have signal |
| **Auto-generated high-performer callouts** ("Asset A is 2.3× ER benchmark") | Same — needs benchmark integration first |
| **Benchmarks integration** — load Q1 2026 xlsx, tag above/below | When Content Strategy team asks for it (user said this is nice-to-have) |
| **Cross-campaign trend analysis** | When archive grows past ~20 completed campaigns; needs BigQuery |
| **MS API swap-in** | When Comscore provisions credentials |
| **Meta / TikTok / X Ads parsers** | When MS goes down again or user prioritizes |
| **In-platform native exports** (LinkedIn, etc.) | Same — emergency only |
| **Recap export as branded PDF/HTML** | Currently handed to Claude Design; build only if that workflow breaks down |
| **Scheduled auto-refresh** for Live campaigns | After MS API lands |
| **Role-based UI** (editor vs. viewer) | If viewers complain about upload UI clutter |

## Non-goals (explicitly out of scope)

- Public-facing partner dashboards (recaps go through Claude Design)
- Content production workflow (stays in MS / Sprout / wherever)
- Campaign planning/budget allocation (stays in current planning docs)
- Replacing Sprout / Measure Studio / Google Ads as data tools — this is reporting only
