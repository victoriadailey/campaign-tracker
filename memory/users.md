# Users & Viewers

## Active editors (write access)

- **Content Strategist** — primary daily user; uploads exports, reviews pacing, makes optimization calls
- **Social Analyst** — co-primary; works alongside Content Strategist
- **Victoria** — oversight; uses for high-level review and recaps

These three run all FOS sponsored campaigns from a paid media perspective.

## Viewers (read access)

Cross-functional team:
- **Account Management (AM)** — partner-facing; needs to see campaign health to brief partners
- **Sales** — uses pacing/performance data for renewal conversations and case studies
- **Partnership Marketing** — uses for portfolio storytelling

Viewers should see clean dashboards without upload UI clutter. Could be same app with role-based UI hiding, or a separate read-only deployment.

## Auth implications

- IAP gated to `frontofficesports.com` Workspace covers all internal users
- No external/agency access mentioned — confirm before building
- Role split (editor vs. viewer) can be enforced via Firestore rules + UI toggles, not separate apps
