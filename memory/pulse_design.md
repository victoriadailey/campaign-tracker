# Pulse Design — Canonical Spec

The dashboard's visual identity, page structure, and component library — designed in Claude Design through six rounds of iteration on May 6, 2026.

**Files live at:** `~/Documents/fos-dashboards/campaign-tracker/viewer/`

## Brand

- **Name**: PULSE (all-caps, Newsreader serif italic)
- **Tagline metaphor**: "Can I get a quick pulse check on that campaign?"
- **Top callouts section**: "Pulse Check" (WIN / OPPORTUNITY / WATCH cards)

## Typography

- **Serif**: Newsreader (Google Fonts; light/300 and 200 weights). Stand-in for Tiempos Headline (commercial). Used for: headlines, section titles, KPI values, hero post quote, sidebar wordmark.
- **Sans**: Inter. Used for: UI density, body, labels, table cells.
- **Mono**: JetBrains Mono. Used for: tag chips on callouts, mono accents.
- **Italic**: serif italics used aggressively in headlines (e.g., `Future of Sports`, `Portfolio Players`).

## Palette (from `viewer/styles.css`)

| Token | Hex | Use |
|---|---|---|
| `--liquorice` | `#1F1A15` | dark sidebar bg, ink text, hero post bg |
| `--cream` | `#F5F1E8` | main bg |
| `--paper` | `#FAF7EF` | card surface |
| `--flame` | `#DE6B38` | **default accent** (was sunshine, demoted) |
| `--orange` | `#FF9947` | secondary accent, ft-1 cards |
| `--pear` | `#8FC766` | budget bars, ft-4 cards |
| `--sky` | `#5CB5F2` | ft-3 cards, info callouts |
| `--lilac` | `#A896F2` | ft-5 cards |
| `--blossom` | `#F2A6A8` | ft-2 cards |
| `--sunshine` | `#FFE019` | available as tweak option, no longer default |

Tweaks panel lets users swap accent (flame / sky / sunshine / pear / lilac), toggle theme (light/dark), density (compact/balanced/spacious), serif headlines on/off.

## Page structure

### Sidebar (always visible)

- PULSE wordmark in serif at top (no rounded P tile — bare wordmark)
- **CAMPAIGNS** section split into two groups:
  - **CONTENT** — ADP, E*TRADE, TastyTrade
  - **SOCIAL** — US Bank
  - Each item shows a status dot (green/amber/red)
- Foot: user avatar + email

### Overview page

1. **Header** — "Good morning" greeting + serif italic display
2. **Pulse Check** — 3 callout cards at top (WIN / OPPORTUNITY / WATCH) — first thing user sees
3. **Data sources strip** — small status indicators with last-updated dates
4. **Campaign cards** — 4 colored cards (one per campaign), pacing bars, click → detail
5. **Top performing posts** — split into two tables side-by-side: by ER and by Organic Reach. Hero post (#1 by ER) + 4 secondary by ER on left, leaderboard 5–10 on right.
6. **What we're seeing** — bottom callouts (4) + avg CPM per channel block

### Campaign Detail (CONTENT type — `campaign.jsx`)

For ADP, E*TRADE, TastyTrade:

1. **Colored pacing banner** — campaign color background, big serif headline ("Behind *pace.*", "Goal *exceeded.*", etc.)
2. **Tab nav** — Overview / By Channel / Episodes / Top Posts / Recommendations
3. **Flight Tracker** — 3-bar pacing alignment:
   - Impressions (campaign color)
   - Budget (pear/green)
   - Time elapsed (gray)
   - Time-elapsed marker line drawn across all three
4. **KPI row (4 cells)** — Total Impressions, Total Engagements, Active Episodes / Total Posts (combined), Blended ER
5. **By Channel** — 5 channel tiles with ER + CPM benchmark deltas (no trending arrows; benchmark comparison instead)
6. **Per-Episode Performance Table** — collapsible rows. Each episode opens a panel showing per-platform breakdown with **Paid Impr.**, **Organic Impr.**, **% Organic** columns (no chart)
7. **Episode Comparison Cards** — one card per episode with: full data + top post(s) per episode (linked) + WIN / WATCH callouts
8. **Top Posts** — split tables (by ER / by organic reach), all linked
9. **Recommendations** — bottom callouts

### Campaign Detail (SOCIAL — US Bank, `usbank.jsx`)

Bespoke layout because US Bank has 3 independent components (Come Up / Native Social / Red Carpet) tracked separately.

1. **Header** with overall pacing
2. **3 component hero cards** — each with own goal, spend, status pill
3. **Master pacing bar** — single stacked showing how all 3 contribute to 14M total goal
4. **Per-component sections**:
   - **Come Up** — pacing strip + 5 KPIs + platform table (10 cols) + 4 athlete story cards (Mauigoa, Tate, Downs, Mendoza) with Collab/Non-Collab badges + 3 callouts
   - **Native Social** — pacing + KPIs + platform table + organic-momentum callout (no stories)
   - **Red Carpet** — pacing (with budget reallocation note) + KPIs + 2 video cards each with own platform table + callout
5. Distribution badges throughout: `ORGANIC + PAID`, `ORGANIC`, `PAID`
6. Budget overspend cells flag red, underspend amber

## Components delivered

In `viewer/components.jsx`:
- `Sidebar` (CONTENT/SOCIAL split)
- `PageHead`
- `KpiCard` / `KpiRow`
- `PostsTable` (linked, sortable)
- `PlatformPill` / `PlatformIcon`
- `Callout` (kind: pos/warn/neg/info)
- `EpisodePerformanceTable` (collapsible per-platform breakdown)
- `FlightTracker` (3-bar pacing)
- `Channel tile` with benchmark deltas
- Tweaks panel (theme/palette/density/serif)

## Iteration history (highlights)

- **v1**: Frontline name, sunshine yellow primary, Instrument Serif
- **v2 feedback**: rename Tiempos Headline-feel → switched to Newsreader (light weights). Demoted sunshine, flame became primary. Cooler cream bg.
- **v3 feedback**: removed delivery-over-time / channel mix from overview. Top posts split into hero + 4 + leaderboard 5–10. Avg CPM per channel block added. Flight tracker color logic. Removed format mix + delivery curve from campaign page. Per-episode table redesigned (collapsible, 3-col paid/organic/% organic).
- **Renamed Frontline → PULSE** (after the "pulse check" framing clicked)
- **Added US Bank as bespoke** — first SOCIAL campaign, multi-component shape

Full chat transcript saved at `/tmp/pulse-design/social-dashboard/chats/chat1.md` (1087 lines) — likely worth archiving into the repo at `viewer/design-history.md` if we want a permanent record.
