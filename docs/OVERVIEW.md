# Pulse Campaign Tracker — Logic & Context Overview

A complete audit of every rule, formula, exclusion, and special case baked into the dashboard. Read top-to-bottom to understand the whole pipeline, or jump to a section to spot-check one piece of logic.

**Last refreshed:** May 2026 (after Meta Ads support, new thresholds, Data Archive page)

---

## Contents

1. [Architecture at a glance](#1-architecture-at-a-glance)
2. [Required export columns by source](#2-required-export-columns-by-source)
3. [Per-source parsing rules & quirks](#3-per-source-parsing-rules--quirks)
4. [Naming convention best practices (paid exports)](#4-naming-convention-best-practices-paid-exports)
5. [Campaign config (campaigns.yaml)](#5-campaign-config-campaignsyaml)
6. [Episode attribution](#6-episode-attribution)
7. [Aggregation formulas (the math)](#7-aggregation-formulas-the-math)
8. [YouTube ad subtype handling](#8-youtube-ad-subtype-handling)
9. [Pre-roll exclusion rule](#9-pre-roll-exclusion-rule)
10. [Benchmarks](#10-benchmarks)
11. [Callouts logic (WIN / OPPORTUNITY / WATCH)](#11-callouts-logic-win--opportunity--watch)
12. [Top posts ranking](#12-top-posts-ranking)
13. [UI display rules](#13-ui-display-rules)
14. [Lifecycle: active vs wrapped (and how to wrap a campaign)](#14-lifecycle-active-vs-wrapped-and-how-to-wrap-a-campaign)
15. [Inputs page (data capture)](#15-inputs-page-data-capture)
16. [Data Archive page (audit trail)](#16-data-archive-page-audit-trail)
17. [End-to-end data flow](#17-end-to-end-data-flow)
18. [Known special cases & manual overrides](#18-known-special-cases--manual-overrides)
19. [Test coverage](#19-test-coverage)
20. [Auditing checklist](#20-auditing-checklist)

---

## 1. Architecture at a glance

Two layers, one data model.

```
┌─────────────────────────────────────────────────────────────────┐
│ Inputs                                                          │
│   tests/fixtures/*.csv / *.tsv     Source exports                │
│   config/campaigns.yaml            Campaign rules                │
│   config/social_benchmarks.csv     FOS benchmarks by category    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ python -m app.viewer.refresh
┌─────────────────────────────────────────────────────────────────┐
│ Python pipeline                                                 │
│   app/parsers/   Source-specific parsers → NormalizedPost       │
│   app/compute/   Attribution, rollups, callouts, benchmarks     │
│   app/viewer/    Serializes to viewer/data.js                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Static React viewer                                             │
│   viewer/data.js          Generated payload                      │
│   viewer/*.jsx            Babel-compiled components              │
│   viewer/index.html       Entry point                            │
│   Pulse_Dashboard_Standalone.html   Single-file shareable build  │
└─────────────────────────────────────────────────────────────────┘
```

The viewer is **read-only**. It cannot write back to disk. The Inputs page captures form drafts + queued uploads to `localStorage`, generates a YAML snippet you paste into `config/campaigns.yaml`, and lists files you copy into `tests/fixtures/`. Same pattern for the "Mark as wrapped" button — it generates a two-line YAML edit for you to apply.

---

## 2. Required export columns by source

Set your exports up with these columns and the parsers will ingest them cleanly. Anything not listed is ignored.

### 2a. Measure Studio (`.csv`, UTF-8, wide format)

The full per-platform wide export. Required columns (per-platform metric column names vary by platform — these are the ones the parser reads):

**Identity (required on every row):**
- `Account Name` / `Account Handle`
- `Post ID` *— the native platform id; we use this for `manual_posts` overrides*
- `Post URL`
- `Post Title`
- `Post Description`
- `Post Platform` *— one of Instagram / Facebook / Twitter (X) / TikTok / YouTube / LinkedIn / Snapchat*
- `Post Type`
- `Date Published` / `Time Published`
- `Organic / Boosted / Dark`
- `Post Group(s)` *— used to bucket rows into the right campaign*

**Episode attribution (required for content campaigns):**
- `User Tags` ← **most reliable attribution signal.** The social team tags posts with `PP Episode N - Guest Name`. We match against this column first.
- `Post Tags`
- `AI - Categories`

**Per-platform metrics (required, one set per platform present in the export):**
- `<Platform> Impressions - Total` / `Impressions - Paid`
- `<Platform> Views - Total` / `Views - Organic` / `Views - Paid`
- `<Platform> Total Engagements - Total` / `Engagements - Organic` / `Engagements - Paid`
- `<Platform> Engagement Rate - Total` *— stored as 0.0–1.0 fraction*
- `<Platform> Ad Spend - Paid` (for paid platforms)

### 2b. Google Ads YouTube Paid (`.tsv`, UTF-16 LE w/ BOM)

This is the standard Google Ads campaign-report export. Set it up with these columns (in any order) and the parser will handle it:

**Required:**
- `Campaign` — campaign name (drives subtype detection and episode attribution via `PP Episode N -` prefix)
- `Impressions` *(or `Impr.`)* — total ad-render count. **Use the explicit Google Ads value**; only auto-derived as a fallback if this column is missing entirely.
- `TrueView views` — view count
- `Cost` — total spend, USD
- `Engagement rate` — Google Ads' official ER as a percent (e.g., `64.98%`)
- `Engagements` — Google Ads' engagement count

**Required for subtype detection (Google Ads fills these per campaign):**
- `TrueView view rate (In-stream)` — populated only if the campaign ran as Pre-roll
- `TrueView view rate (In-feed)` — populated only if In-feed
- `TrueView view rate (Shorts)` — populated only if Shorts

**Fallback behavior:** if `Impressions` (or `Impr.`) is missing from a row, we derive it as `TrueView views ÷ view rate` and surface a warning naming the file. Add the Impressions column to your Google Ads export template to keep the warning from firing — Google Ads' own number is always the authoritative one.

*Both the new UTF-16 TSV format and the legacy comma-separated CSV are supported; either column name (`Impressions` or `Impr.`) works.*

### 2c. X Ads (`.csv` from Apple Numbers `.numbers`)

Sheet columns (export both Full + Cutdown sheets into one combined CSV):
- `Tweet text` or `Ad name` *— acts as the campaign name (needs `PP Episode N -` prefix for episode attribution; see §4)*
- `Impressions`
- `Engagements`
- `Spend`
- `Engagement rate` *(optional — parser computes it if missing)*

### 2d. Meta Ads (`.csv`, UTF-8) — **NEW**

From Meta Ads Manager export. Use these columns:

- `Campaign name` *— follow naming convention (see §4)*
- `Impressions`
- `Reach`
- `Post engagements` *— Meta's total post-engagement count*
- `Amount spent (USD)`
- `Reporting starts` / `Reporting ends` *(optional, for display)*

**Platform detection** comes from the suffix on `Campaign name`:
- `... (IG)` → Instagram
- `... (FB)` → Facebook
- No suffix → defaults to Instagram

### 2e. TikTok Ads (placeholder — coming when you share an export)

Tentative required columns (will firm up once you share a sample):
- `Campaign name` or `Ad name`
- `Impressions`
- `Video views`
- `Engagements`
- `Cost (USD)`

The parser is in "flexible" mode now — it tries several known column names and surfaces a warning if it can't find what it needs.

---

## 3. Per-source parsing rules & quirks

### 3a. Measure Studio

**Curly-quote normalization (still required — don't remove).** MS exports use curly apostrophes (`Women's`). YAML configs typically use straight (`Women's`). Without normalization, substring matching silently fails. The attribution normalizer lowercases everything and replaces:

| Curly | Straight |
|---|---|
| `'` `'` | `'` |
| `"` `"` | `"` |

This still matters in practice — every MS export goes through this on the way to episode attribution. Keep it.

**YouTube negative-export bug.** YT columns sometimes export as negative numbers (`YouTube Total Engagements - Organic = -6325`). `_to_int` / `_to_float` take `abs()` to normalize. Metric values are inherently non-negative.

**MS "Engagements - Organic" for YT specifically.** MS exports YT organic engagement as `Total − Paid`, but the "Paid" column on cross-posted videos contains Google Ads' inflated interaction count (clicks + watch-progress + earned views), not just L+C+S. The subtraction yields negatives; `abs()` then flips them into bogus huge positives. **Fix:** when `ms_organic_only_for` includes YT, only trust `engagements_organic` if it's sane (≤ `engagements_total`). Otherwise fall back to `engagements_total`.

**`ms_organic_only_for` logic.** *Clarified:*

When a platform is listed in a campaign's `ms_organic_only_for` list, the MS export's totals for that platform are **reduced to just the organic portion** at parse time. The paid columns are then nulled out.

**Why:** if MS reports a total of 1,500,000 X impressions and X Ads (the dedicated paid source) reports 1,200,000 paid impressions on the same campaign, MS's total **already includes those paid impressions**. Adding them together produces a double-count. So we trim MS to its organic share (≈300,000) and let X Ads provide the 1,200,000 paid number.

**This applies to:** any platform where we also pull paid data from a dedicated source — currently `x` (X Ads), `youtube` (Google Ads YT Paid), and going forward will apply to `meta` / `instagram` / `facebook` / `tiktok` if/when we layer dark-post exports on top of MS exports for those platforms. Add the relevant platforms to `ms_organic_only_for` in `campaigns.yaml` when this happens.

**Carousel vs Story classification.** Post Type `Carousels & Saved Stories` was being miscounted as IG Stories. Fixed by checking `carousel` / `photo` keywords before `story` in `_classify_format`.

---

### 3b. Google Ads YouTube Paid

**Encoding/delimiter auto-detection.** First 2 bytes determine encoding (UTF-16 if BOM, else UTF-8). Header row tab-count determines delimiter (tab if ≥3 tabs, else comma).

**Impressions — explicit column preferred, derived only as fallback.** The parser reads `Impressions` (or its older shorthand `Impr.`) directly from the export when present — Google Ads' authoritative number is what shows up in the dashboard. If neither column is in the export, the parser falls back to:

```
Impressions = TrueView views ÷ (TrueView view rate ÷ 100)
```

The view-rate column that's populated tells us which subtype the ad served as (In-stream / In-feed / Shorts) and is the divisor.

When the fallback fires, a warning is emitted listing the file and row count — visible in the `python -m app.viewer.refresh` console output. To silence it, add the `Impressions` column to your Google Ads campaign-report export template.

**Subtype detection priority:**
1. Whichever `TrueView view rate (...)` column is populated → tells us the subtype directly.
2. Fallback: campaign-name suffix (`(pre-roll)`, `(in-feed)`, `(Shorts)`, etc.)
3. Fallback to fallback: if name contains `cutdown`, treat as Shorts (see naming convention §4).

**Cutdowns are Shorts.** When `Cutdown` appears in the Google Ads campaign name, the ad is running as Shorts. The view-rate column is the most reliable indicator (Google fills in `TrueView view rate (Shorts)` for these), but the cutdown-name convention is the fallback when the export is partial.

**ER is stored as a decimal.** Export shows `64.98%`; parser stores `0.6498`. Render code multiplies by 100 when displaying.

**GAds `Engagements` ≠ social engagements.** Google's count includes clicks + watch progress (25/50/75/100%) + earned views. This is fine to display as Google's official metric, but **we exclude Pre-roll from aggregate ER calcs entirely** because its ER scale (60-77%) is incompatible with social ER (see §9).

---

### 3c. X Ads

CSV export from Apple Numbers. Maps platform = `X`, source = `X_ADS`, boosting = `DARK`.

For E\*TRADE: `ms_organic_only_for: [x, youtube]` prevents MS X totals from being summed with X Ads paid (would otherwise double-count ~$251K in impressions, originally spotted in the Repole audit).

---

### 3d. Meta Ads — **NEW**

Standard UTF-8 CSV from Meta Ads Manager. We use this when running **dark posts as paid media** — Measure Studio can't see dark posts, so this is the only place that data lives.

**Per-row mapping:**
- `Campaign name` → `post_title` + `post_id_native`
- `Impressions` → `impressions_paid` (and `impressions_total`, since dark posts are 100% paid)
- `Reach` → `reach_paid` / `reach_total`
- `Post engagements` → `engagements_paid` / `engagements_total`
- `Amount spent (USD)` → `ad_spend`
- ER = engagements ÷ impressions (Meta doesn't export an ER column)

**Platform from `(IG)` / `(FB)` suffix** on `Campaign name`. Default = Instagram if no suffix.

**Boosting = DARK** for every Meta Ads row (dark posts only — if you ever import a Meta export of *organic* posts, we'd need a separate code path).

**Meta + MS double-count caveat.** When/if you also pull MS organic Instagram data into the same campaign, you'd want to add `instagram` and `facebook` to `ms_organic_only_for` so MS organic gets isolated from Meta paid. Right now US Bank only has Meta (no MS yet), so no overlap.

---

### 3e. TikTok Ads — **NEW (placeholder)**

Parser is in flexible mode — it tries several candidate column names. Once you share a real export, replace `CANDIDATE_COLS` with hard `REQUIRED_COLS` and lock in the exact schema (mirroring how Meta works above).

Same `ms_organic_only_for` note applies: when MS data starts including TikTok organic alongside TikTok Ads paid, add `tiktok` to `ms_organic_only_for`.

---

## 4. Naming convention best practices (paid exports)

The dashboard's episode-attribution magic depends entirely on what you can put in the **campaign name** column of paid exports. MS organic posts get attributed via `User Tags` (the social team's tag), but Google Ads / X Ads / Meta Ads / TikTok Ads only give us the campaign name. **Set up your campaigns with these patterns** and attribution is automatic.

### Universal pattern

```
<Series>_<Episode tag>_<Variant> (<Platform>)
```

Where `<Episode tag>` is your internal tag — usually `PP Episode N` (Portfolio Players) or `FOS Episode N` (Future of Sports). This is the SAME string that goes in the MS `User Tags` column, so all sources route through the same attribution rule.

### Google Ads (YouTube)

```
Portfolio Players S3 Ep5: Assia Grazioli-Venier (pre-roll)
Portfolio Players S3 Ep5: Assia Grazioli-Venier (in-feed)
Portfolio Players S3 Ep5: Assia Grazioli-Venier Cutdown 1 (Shorts)
ADP_Future of Sports_Full Episode 1 (pre-roll)
ADP_Future of Sports_Episode 1 Cutdown 1
```

**Required tokens:**
- `<Series> <Episode N>: <Guest>` so the parser can match `PP Episode 5 -` or `Episode 1` against the episode keyword list
- Format suffix in parentheses: `(pre-roll)` / `(in-feed)` / `(Shorts)` — important for subtype display when view-rate columns are missing
- `Cutdown` token if it's a cutdown (defaults to Shorts/In-feed depending on view-rate)

### X Ads

X campaign names are typically short. Best practice:

```
PP Episode 5 - Assia Grazioli-Venier (X)
ADP Episode 1: Kim Ng (X)
```

The `PP Episode N -` prefix is the magic token — same as MS User Tags.

### Meta Ads (dark posts)

```
<Partner>_<Series>_<Component>_<Variant> (<Platform>)

US Bank_NFL Draft_The Come Up_Video 1 (IG)
US Bank_NFL Draft_The Come Up_Video 1 (FB)
US Bank_NFL Draft_Red Carpet_Video 2 (IG)
ADP_Future of Sports_Episode 1 Cutdown 1 (FB)
E*TRADE_Portfolio Players_PP Episode 5 - Assia Grazioli-Venier (IG)
```

**Required:**
- Platform suffix `(IG)` or `(FB)` — drives platform attribution
- For social campaigns (no episodes), component + variant labels for tile/table grouping
- For content campaigns, include the `PP Episode N -` token so episode attribution can pick it up

### TikTok Ads

Same Meta-style naming, with `(TT)` suffix (or just no suffix if TikTok is the only platform):

```
US Bank_NFL Draft_The Come Up_Video 1 (TT)
E*TRADE_Portfolio Players_PP Episode 5 - Assia (TT)
```

### General rules

1. **Include the episode tag verbatim** wherever attribution matters: `PP Episode 5 -` or `Episode 1` should appear in the campaign name *exactly* as it does in the YAML's `match` list.
2. **Use underscores or colons consistently** as separators — both work, but stay consistent within a campaign so partners can scan exports.
3. **Platform suffix in parens** — `(IG)`, `(FB)`, `(TT)`, `(X)`, `(Shorts)`, `(pre-roll)`, `(in-feed)`. Helps both the parser and humans.
4. **Avoid generic terms** like "Women's Soccer" or "NWSL" in the campaign name if multiple episodes touch on the same topic — they'll route to whichever episode has those keywords first. Stick to the explicit episode tag.

---

## 5. Campaign config (`config/campaigns.yaml`)

The single config file driving every campaign.

### 5a. Required fields

| Field | Type | Purpose |
|---|---|---|
| `id` | string (lowercase, no spaces) | Internal key — URL slug, file references |
| `partner` | string | Display name |
| `series` | string | Display series |
| `series_italic` | string | Word(s) rendered italic |
| `type` | `content` \| `social` | Episode-based vs post-based |
| `flight_start`, `flight_end` | ISO date | Pacing / elapsed math |
| `impression_goal` | int | Headline delivery vs goal |
| `budget_goal` | float | Headline spend vs goal |
| `color` | `ft-1`..`ft-5` | Accent color |
| `blurb` | string | Card description |
| `sources` | dict | Source kind → fixture file list (see 5d) |

### 5b. Optional fields

| Field | Default | Purpose |
|---|---|---|
| `benchmark_category` | `""` | One of the 12 FOS Social Benchmark categories |
| `lifecycle` | `"active"` | `active` or `wrapped` |
| `ms_post_groups` | `[]` | Filter MS rows by `Post Group(s)` |
| `ms_organic_only_for` | `[]` | Platforms whose MS totals are reduced to organic share to avoid double-count with dedicated paid sources |
| `episodes` | `[]` | Episode definitions (content campaigns) |

### 5c. Lifecycle states

```yaml
lifecycle: active    # default — Active campaigns grid + sidebar Content/Social
lifecycle: wrapped   # Recently Wrapped grid + sidebar Wrapped section
```

### 5d. Sources (May 2026 — supports 6 kinds)

```yaml
sources:
  measure_studio:        # MS wide-format exports (.csv)
    - portfolio_players_ms.csv
  google_ads_campaign:   # Google Ads YT Paid — legacy alias
    - adp_yt_paid.tsv
  youtube_paid:          # Google Ads YT Paid (same parser, preferred name)
    - portfolio_players_yt_paid.tsv
  x_ads:                 # X Ads CSV
    - portfolio_players_x_ads.csv
  meta_ads:              # Meta Ads Manager CSV (for dark posts)   ← NEW
    - usbank_meta_ads.csv
  tiktok_ads:            # TikTok Ads Manager CSV                  ← NEW (placeholder)
    - example_tt_ads.csv
```

### 5e. Current campaign roster

| ID | Partner | Type | Lifecycle | Benchmark Category |
|---|---|---|---|---|
| adp | ADP | content | active | Original Content |
| etrade | E\*TRADE | content | active | Original Content |
| spectrum | Spectrum | social | active | Custom Social |
| mm | Morgan & Morgan | social | active | Social - IP/Franchise |
| usbank | US Bank | social | wrapped | Social Coverage Partner |

---

## 6. Episode attribution

Content campaigns split into episodes. Every parsed post lands in *at most one* episode.

### 6a. Algorithm

For each post:

1. **Manual override wins.** If `post_id_native` is in any episode's `manual_posts`, that episode gets it.
2. **Build match text** by joining (all normalized, lowercased, curly quotes flattened):
   - `post_title`, `post_description`
   - `raw["AI - Categories"]`
   - `raw["User Tags"]` ← the most reliable signal
   - `raw["Post Tags"]`
3. **Reject by exclude.** Any of an episode's `exclude` keywords in the match text disqualifies that episode.
4. **Collect candidates.** For each remaining episode, check `match` keywords. At least one must hit (or all, with `all_match: true`).
5. **Score by total keyword length.** Longer + more matches = higher score.
6. **Longest match wins.**

### 6b. Why `User Tags` (column M) is the most reliable signal

The social team tags each MS post with `PP Episode N - Guest Name`. Putting `"PP Episode 5 -"` in an episode's match list is 15 characters — wins on score against any name keyword. Cross-posts with generic narratives (Michele Kang, Women's Soccer) still ride the explicit tag to the correct episode.

### 6c. Unattributed reporter

After every refresh, MS-source posts that didn't land in any episode are listed in the console output. Goal is zero unattributed posts.

---

## 7. Aggregation formulas (the math)

**Every aggregate ER in the system uses the same formula:**

```
Aggregate ER = Total Engagements ÷ Total Impressions × 100
```

Impression-weighted, **not** an average of post ERs. A post with 100K impressions weighs 100× more than a post with 1K.

**Used in:**
- `rollup_campaign` — campaign card header ER
- `per_campaign_channels` — per-channel ER on the campaign page
- `channel_rollups` — cross-campaign portfolio channels
- `rollup_episode` — episode header + per-channel within an episode

**One exception, applied everywhere:** the calculation excludes YouTube Pre-roll posts entirely — see §9.

### 7a. Impressions

```python
# YouTube special case: prefer impressions_paid (ad-renders) over views_total
if platform is YOUTUBE:
    return impressions_total or impressions_paid or views_total or views_paid
return impressions_total or views_total or reach_total or impressions_paid or views_paid
```

### 7b. Engagements

```python
eng = p.engagements_total or p.engagements_paid or 0
```

Fallback to `engagements_paid` for paid-only sources (GAds, X Ads, Meta Ads).

### 7c. CPM

```
CPM = total_spend ÷ paid_impressions × 1000
```

Only paid impressions in the denominator (organic delivery is free).

### 7d. Per-post ER (`_post_er_pct`)

Used by top-posts ranking (NOT aggregate calcs). Trusts the source's own ER column.

---

## 8. YouTube ad subtype handling

YouTube is three channels with different mechanics:

| Subtype | What it is | Typical ER | Typical CPM |
|---|---|---|---|
| **In-feed** | Discovery ads in YT feed/browse | 0.3-1% | $0.55 |
| **In-stream (Pre-roll)** | Skippable/non-skip pre-content video | 60-77% | $14 |
| **Shorts** | Ads in the Shorts feed | 9-45% | $3.25 |

Pre-roll's 70% includes watch-progress metrics (25/50/75/100% video plays counted as engaged). In-feed's 0.5% measures click-through. Different definitions — cannot be blended.

`youtube_subtype_from_post(post)` — prefers GAds view-rate signal, falls back to name parsing.

---

## 9. Pre-roll exclusion rule

**Rule:** YouTube Pre-roll posts are excluded from every rolled-up Engagement Rate calculation.

**Why:** Google reports In-stream "Engagement rate" as watch-progress. Not comparable to social ER. Blending the two gives a misleading aggregate.

### 9a. Where it fires

`_is_yt_preroll_post(p)` checked in:
- `rollup_campaign` — campaign card ER
- `channel_rollups` — cross-campaign YouTube line
- `rollup_episode` — episode header ER
- `top_posts_by_er` — Pre-roll never in top-posts rankings
- Episode-level top posts

### 9b. What is NOT excluded

- Pre-roll still shows in per-channel breakdowns with its own metrics
- Pre-roll impressions still count toward campaign delivery
- Pre-roll engagement count still appears in headlines

The only thing excluded is **Pre-roll's contribution to *aggregate* ER**.

---

## 10. Benchmarks

### 10a. FOS Social Benchmarks (12 categories)

Stored in `config/social_benchmarks.csv`, parsed into `BENCHMARKS_DATA`:

| Category | Use for |
|---|---|
| Social Coverage Partner | US Bank-style coverage of a tentpole / partner |
| Social - IP/Franchise | Franchise-driven social-only series (The Case Study) |
| Custom Social | One-off custom social like Spectrum Fueling Dreams |
| Multimedia Reporter-Led - IP/Franchise | Reporter-led franchise series |
| Custom Multimedia Reporter-Led (Tentpole Event, Custom Series, etc.) | One-off reporter-led custom |
| Creator-Led - IP/Franchise | Franchise creator-led series |
| Custom Creator-Led | One-off creator-led custom |
| Shows (Cutdowns & Custom Integrations) | Sponsored cutdowns inside other shows |
| Original Content | Longform interview series (ADP, E\*TRADE) |
| Branded Content | Sponsored branded series |
| FOS Event - Custom Social | FOS-owned event coverage |
| FOS Event - Presenting Partner | Single presenting partner for a FOS event |

Campaigns reference one via `benchmark_category` in YAML.

### 10b. Per-platform Sponsored benchmarks (`PLATFORM_BENCHMARKS`)

Hardcoded values used by Channel cards (delta vs benchmark) and the WIN callout's "X.X× benchmark" math:

```python
"youtube_preroll":  ChannelBenchmark(er=72.00, cpm=14.00)   # data-derived, n=11
"youtube_infeed":   ChannelBenchmark(er=0.50,  cpm=0.55)    # data-derived, n=11
"youtube_shorts":   ChannelBenchmark(er=20.00, cpm=3.25)    # data-derived, n=20
"instagram":        ChannelBenchmark(er=3.31, cpm=5.10)
"tiktok":           ChannelBenchmark(er=2.03, cpm=2.40)
"linkedin":         ChannelBenchmark(er=3.76, cpm=0.00)
"x":                ChannelBenchmark(er=0.92, cpm=1.10)
"facebook":         ChannelBenchmark(er=1.53, cpm=4.80)
```

---

## 11. Callouts logic (WIN / OPPORTUNITY / WATCH)

`compute_campaign_callouts` produces up to 3 callouts per campaign. The best of each kind across all campaigns surfaces on the Overview as Pulse Check signals via `aggregate_portfolio_signals`.

### 11a. WIN — "we're crushing it"

A specific post or channel with ER ≥ **1.5× its FOS benchmark**, with meaningful volume:
- Channels: ≥10K impressions
- Posts: ≥5K reach

Whichever has the larger benchmark multiplier wins. Headline: `"{Platform} post at 6.7% ER — 3.3× the benchmark."`

### 11b. OPPORTUNITY — "audience resonance"

A channel where **≥60% of delivery is organic** AND **total channel impressions ≥100K**.

Framing leans into platform resonance: *"the algorithm is rewarding this content."*

**LinkedIn special case:** LinkedIn is always organic for us (paid is too expensive), so being 100% organic isn't news. Only surface LinkedIn when at least one LinkedIn post has hit **250K+ impressions** on its own.

Headline: `"{Channel} resonating — 100% of delivery is organic."`

### 11c. WATCH — "needs attention"

Fires on:
1. **Pacing miss:** `pacing_ratio < 0.75` AND flight is past 25% elapsed. Pacing always outranks CPM when both fire.
2. **CPM over benchmark:** any channel where CPM ≥ **2× the FOS benchmark**.

Headlines:
- Pacing: `"74% behind pacing with 18 days left."`
- CPM: `"{Channel} CPM at $X.XX — N.N× the benchmark."`

### 11d. Cross-campaign aggregation

Picks the most impressive WIN, OPPORTUNITY, and WATCH across all campaigns. Scoring:
- WIN: highest `N×` benchmark multiplier in headline
- OPPORTUNITY: highest `N%` organic in headline
- WATCH: pacing miss scores `1000 + N%`; otherwise CPM multiplier

---

## 12. Top posts ranking

### 12a. Top posts by ER

- Filters: `min_views=1000`, `min_er=1.0%`
- **YouTube Pre-roll excluded** (see §9)
- Ranked by `_post_er_pct(p)`

### 12b. Top posts by organic reach

- Filter: organic reach **≥ 100,000** *(was 1,000 — raised to surface only standouts)*
- Ranked by `views_organic` / `reach_organic` / `impressions_organic` (whichever is set)

### 12c. Click-through to actual post

Both lists carry `url = p.post_url` and render as `<a href={url} target="_blank">`. Episode-level top posts also carry URLs.

---

## 13. UI display rules

### 13a. Per-episode breakdown table

- Full integer formatting (`1,267,601`) via `fmt.numFull`
- Full dollar formatting with cents (`$1,497.32`) via `fmt.moneyFull`
- **Total row** at the bottom — ER pulled from backend (already Pre-roll-excluded)

### 13b. Social campaigns hide "Episodes"

In the campaign detail page top-right card, the `Episodes` row only renders when `c.type !== 'social'`.

### 13c. Wrapped vs Active grids

Overview renders two sections:
- **Active campaigns** — 3-across full-size `CampaignCard`s
- **Recently wrapped** — 4-across compact black `WrappedCard`s (only when at least one wrapped campaign exists)

### 13d. Sidebar grouping

Active campaigns grouped by type:
- `Content` section: type=content + lifecycle=active
- `Social` section: type=social + lifecycle=active
- `Wrapped` section: lifecycle=wrapped (across both types)

Top-level nav: Overview, Benchmarks, Add Campaign Data, **Data Archive**.

### 13e. Top post tiles link out

Episode and campaign-level top-posts use `href={p.url}` with `target="_blank" rel="noreferrer"`.

---

## 14. Lifecycle: active vs wrapped (and how to wrap a campaign)

### 14a. What changes when a campaign is wrapped

| Behavior | `active` | `wrapped` |
|---|---|---|
| Sidebar group | Content / Social | Wrapped |
| Overview placement | Active campaigns (3-across full card) | Recently wrapped (4-across compact black card) |
| Pulse Check signals | Eligible | Not eligible |
| Status pill | Live status (On Track / Behind Pace / etc.) | "Goal Exceeded" (or final status) — locked in |
| `flight_end` | Future date | Should be set to the actual end date |

### 14b. How to wrap a campaign (the button)

Go to the campaign's detail page. **In the top-right card, click "Mark as wrapped."** A modal appears with:
- The exact two-line YAML edit needed
- A date picker for the actual end date
- A **Copy YAML edit** button that puts the snippet on your clipboard

The dashboard is read-only (it can't write to `config/campaigns.yaml` directly), so you'll paste the snippet into the YAML, save, and run `python -m app.viewer.refresh`. On the next refresh:
- The campaign disappears from Active campaigns
- It appears as a black card under Recently Wrapped on Overview
- The sidebar groups it under Wrapped

**What the YAML edit looks like:**

```yaml
# Edit config/campaigns.yaml — find the entry for id: usbank
# Change these two lines:

    lifecycle: wrapped       # was: active
    flight_end: 2026-05-15   # set to actual end date
```

That's it. The button is the safe way to do this without remembering the exact field names.

---

## 15. Inputs page (data capture)

Two tabs:

### 15a. Add new campaign

Form captures every YAML field. Persists draft to `localStorage` so refreshes don't lose work.

Includes upload zones for all source kinds: Measure Studio, Google Ads (YT Paid), X Ads, **Meta Ads**, **TikTok Ads**.

**Generate YAML** button: produces a YAML snippet for you to paste into `config/campaigns.yaml`.

#### What is YAML and why are we generating a snippet?

**YAML** is a plain-text format for structured data. `config/campaigns.yaml` is the file the Python pipeline reads to know what campaigns exist, what their flight dates are, where their export files live, and what episode rules apply. The dashboard's read-only nature means it can't write to that file directly — so the Inputs page does the heavy lifting (form fields → properly formatted YAML text) and the operator copies the result into the file.

A generated snippet looks like:

```yaml
  - id: etrade_portfolio_players
    partner: E*TRADE
    series: Portfolio Players
    type: content
    benchmark_category: Original Content
    lifecycle: active
    flight_start: 2026-01-01
    flight_end: 2026-06-30
    impression_goal: 45000000
    budget_goal: 50000
    color: ft-3
    blurb: "Sports ownership & investing series."
    sources:
      measure_studio:
        - portfolio_players_ms.csv
      youtube_paid:
        - portfolio_players_yt_paid.tsv
    episodes:
      - id: ep1
        n: "Ep. 01"
        title: "Mike Repole on Sports Ownership"
        date: "Feb 3"
        match: ["PP Episode 1 -", "Repole", "Tom Brady"]
        exclude: []
```

You paste this under the `campaigns:` line in `config/campaigns.yaml`, save the file, and run `python -m app.viewer.refresh`. The dashboard picks up the new campaign on the next refresh.

### 15b. Update ongoing campaign

One card per active campaign. Each has a compact upload zone (with source-type dropdown) and a free-text notes field. Both persist in localStorage.

---

## 16. Data Archive page (audit trail) — **NEW**

A dedicated page that shows every source file currently feeding the dashboard, with:
- Campaign it belongs to
- Source kind (Measure Studio / Google Ads / X Ads / Meta Ads / TikTok Ads)
- Filename
- Posts contributed
- Last modified date
- File size
- OK / Missing status

Generated by `_build_data_archive` in `refresh.py` and emitted to `window.DATA_ARCHIVE`. The page lives at `viewer/archive.jsx`.

**Use it to audit:**
- Whether every YAML reference points to a real file
- When each export was last refreshed
- How many parsed posts came from each source (per campaign)
- What's missing (red badge highlights files in YAML that aren't in `tests/fixtures/`)

**Long-term storage** — the dashboard reads from `tests/fixtures/`. For real backup/safekeeping, mirror each export to a shared Google Sheet (one tab per campaign × source). Slot the Sheet URL into the placeholder button on the Data Archive page when ready.

---

## 17. End-to-end data flow

```
1. Operator: drop files in tests/fixtures/ + edit config/campaigns.yaml
                              │
                              ▼ python -m app.viewer.refresh
2. refresh.py loads YAML
                              │
                              ▼
3. For each campaign, parse all configured sources:
   ├─ parse_ms             (Measure Studio CSV)
   ├─ parse_gads_campaign  (Google Ads YT Paid — TSV or CSV)
   ├─ parse_x_ads          (X Ads CSV)
   ├─ parse_meta_ads       (Meta Ads CSV)
   └─ parse_tiktok_ads     (TikTok Ads CSV — placeholder schema)
                              │
                              ▼ filter by ms_post_groups, reduce ms_organic_only_for
4. posts_by_campaign[campaign_id] = [NormalizedPost, ...]
                              │
                              ▼
5. rollup_campaign         → CampaignSummary  (header KPIs, Pre-roll-excluded ER)
   per_campaign_channels   → list[Channel]    (per-channel cards + YT subtype split)
   top_posts_by_er         → list[TopPost]    (no Pre-roll)
   top_posts_by_organic_reach → list[TopPostOrganic]  (100K+ filter)
   compute_campaign_callouts → [WIN, OPPORTUNITY, WATCH]
                              │
                              ▼
6. attribute_posts_to_episodes  → episode buckets
   rollup_episode              → per-episode breakdown
                              │
                              ▼
7. channel_rollups          → cross-campaign portfolio channels
   aggregate_portfolio_signals → Pulse Check signals
   _build_data_archive      → source manifest for Data Archive page
                              │
                              ▼
8. render.py serializes PulsePayload → viewer/data.js
                              │
                              ▼
9. refresh.py reports per-campaign counts + unattributed warnings
                              │
                              ▼
10. open viewer/index.html — or rebundle Pulse_Dashboard_Standalone.html
```

### 17a. Refresh command

```bash
cd ~/Documents/Claude/campaign-tracker
python -m app.viewer.refresh
```

Options:
- `--today YYYY-MM-DD` — override "today" for pacing math
- `--config path/to/campaigns.yaml`
- `--output path/to/data.js`

---

## 18. Known special cases & manual overrides

### 18a. Manual post attribution (`manual_posts`)

When a post can't auto-match (no name in title/desc/AI cats/User Tags), list its `post_id_native` under an episode's `manual_posts`. Manual override wins over every other rule. Current usages:

- E\*TRADE Ep. 2 Patricof: `2024266065409098028` (threaded tweet, empty title)
- E\*TRADE Ep. 3 Osborne: `2026779233784136168`
- E\*TRADE Ep. 5 Assia: `3865980741240680183`, `3860862608219404966` (IG paid cross-posts)
- E\*TRADE Ep. 6 Allyson: `3870854760043974001` (IG Story, no text)

### 18b. Exclude keywords for teaser-only episodes

Cuban and Donovan have placeholder episodes (haven't aired). Their `exclude` lists protect them from being mismatched:

```yaml
- id: ep9   # Cuban placeholder
  match: ["Mark Cuban", "Cuban"]
  exclude: ["Repole", "Marshall", "Checketts", "Allyson",
            "PP Episode 1", "PP Episode 7", "PP Episode 8", "PP Episode 6"]
```

### 18c. organic_only_for double-count prevention

E\*TRADE config: `ms_organic_only_for: [x, youtube]`. Prevents MS X and YT totals (which already include paid impressions) from being summed with X Ads and Google Ads YT Paid (dedicated paid sources). MS is reduced to its organic share; paid columns are nulled.

### 18d. YouTube cutdown subtype detection

ADP and PP cutdowns without a `(Shorts)` suffix in the campaign name are auto-detected as Shorts via Google Ads view-rate columns. Cutdowns are running as Shorts in production.

---

## 19. Test coverage

`tests/` contains 30 passing tests covering:

- **Parser fidelity:** wide MS, GAds new TSV + legacy CSV, X Ads CSV
- **Edge cases:** negative-export bug, curly quotes, `organic_only_for` reduction, Carousel vs Story classification, view-rate subtype detection
- **Attribution:** longest-match wins, manual_posts priority, exclude disqualification, User Tags / AI Categories / Post Tags feeding match text
- **Rollups:** Pre-roll exclusion, ER formula consistency, YT subtype split, IG feed vs Stories split

Run:

```bash
.venv/bin/python -m pytest tests/ -q
```

---

## 20. Auditing checklist

When reviewing whether the dashboard is doing what you expect:

1. [ ] **Data Archive page** shows every source file accounted for and no missing files? *(visit the Data Archive tab)*
2. [ ] **Per-campaign post counts** look right? *(`refresh.py` prints them after each run)*
3. [ ] **Unattributed warnings empty?** *(if not, add a keyword or `manual_posts`)*
4. [ ] **Each episode's post count is reasonable?** *(inspect EPISODES_BY_CAMPAIGN in `viewer/data.js`)*
5. [ ] **Per-channel ER on the campaign card matches eng/impr math (excl. Pre-roll)?**
6. [ ] **Pre-roll only appears in its own channel row, never blended into aggregate ER?**
7. [ ] **Top posts by ER has no YouTube Pre-roll?**
8. [ ] **Top posts by organic reach only shows ≥100K posts?**
9. [ ] **Top posts links open the actual post on the platform?**
10. [ ] **Campaign's `benchmark_category` matches one of the 12 cohort names?**
11. [ ] **WIN callout's "N× benchmark" multiplier uses the right per-platform benchmark?**
12. [ ] **OPPORTUNITY only fires on channels with ≥100K impressions AND ≥60% organic?**
13. [ ] **OPPORTUNITY isn't firing on LinkedIn unless a single LinkedIn post hit 250K+?**
14. [ ] **WATCH pacing fires only when pacing ratio < 0.75 past 25% elapsed?**
15. [ ] **Social campaigns hide the "Episodes" row in the top-right card?**
16. [ ] **Wrapped campaigns show on Overview's "Recently wrapped" grid and in the sidebar's "Wrapped" section?**
17. [ ] **Meta Ads dark posts surface correctly in the right campaign?** *(filename listed in Data Archive)*
18. [ ] **Naming convention consistent across Google Ads / X Ads / Meta Ads campaign names?** *(see §4)*
19. [ ] **30 tests pass (`pytest tests/ -q`)?**

If any of these is off, the file/function names in each section above are the place to look.
