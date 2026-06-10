# Pulse — Export Specification

The exact columns each export needs to ingest cleanly into the dashboard. Hand this to anyone configuring an export template — Google Ads, Meta Ads Manager, X Ads, TikTok Ads, or Measure Studio.

**Last updated:** May 2026

---

## Quick reference

| Source | File format | Required ID columns | Required metric columns |
|---|---|---|---|
| Measure Studio | `.csv`, UTF-8 (wide format) | Account, Post ID, Post URL, Post Title, Post Description, Post Platform, Post Type, Date/Time Published, Organic/Boosted/Dark, Post Group(s), User Tags, Post Tags, AI - Categories | Per platform: Impressions, Views, Engagements, Engagement Rate, Ad Spend (paid platforms) |
| Google Ads (YouTube Paid) | `.tsv`, UTF-16 LE w/ BOM *(or `.csv`, UTF-8)* | Campaign | **Impressions** *(or Impr.)*, TrueView views, Cost, Engagement rate, Engagements, TrueView view rate (In-stream / In-feed / Shorts) |
| Meta Ads | `.csv`, UTF-8 | Campaign name | Impressions, Reach, Post engagements, Amount spent (USD) |
| X Ads | `.csv` exported from Apple Numbers | Tweet text *or* Ad name | Impressions, Engagements, Spend |
| TikTok Ads | `.csv`, UTF-8 *(schema confirmation pending)* | Campaign name *or* Ad name | Impressions, Video views, Engagements, Cost (USD) |

---

## 1. Measure Studio (`.csv`, UTF-8 wide format)

The full per-platform wide export. The dashboard reads native columns per platform — every metric column has the platform name as a prefix (e.g., `YouTube Views - Total`, `Instagram Engagement Rate - Views - Total`).

### Required on every row

**Identity:**
| Column | Purpose |
|---|---|
| `Account Name` / `Account Handle` | Display & filtering |
| `Post ID` | Native platform id — used as the key for `manual_posts` overrides in `campaigns.yaml` |
| `Post URL` | Click-through target for top-posts links |
| `Post Title` | Used for display + episode attribution |
| `Post Description` | Used for episode attribution (cross-posts often only mention the guest by name in the description) |
| `Post Platform` | One of: Instagram, Facebook, Twitter (X), TikTok, YouTube, LinkedIn, Snapchat |
| `Post Type` | Drives carousel/story/reel/short classification |
| `Date Published` / `Time Published` | Used for date sorting (no business logic depends on it yet) |
| `Organic / Boosted / Dark` | Determines paid vs organic attribution |
| `Post Group(s)` | Buckets each row into the right campaign (`ms_post_groups` in YAML matches against this) |

**Episode attribution (essential for content campaigns):**
| Column | Purpose |
|---|---|
| `User Tags` ⭐ | **The most reliable attribution signal.** Tag posts with `PP Episode N - Guest Name`. The parser scores keyword matches by length, so the longer `PP Episode 5 -` string wins over any generic name keyword. |
| `Post Tags` | Secondary attribution match text |
| `AI - Categories` | Topical fallback — useful when title/desc is empty or generic |

### Required per-platform metrics

For each platform present in the export, include this column set (replace `<Platform>` with the actual platform name — `YouTube`, `Instagram`, `Facebook`, `LinkedIn`, `TikTok`, `X`, `Snapchat`):

| Column | Purpose |
|---|---|
| `<Platform> Impressions - Total` | Total impressions (organic + paid) |
| `<Platform> Impressions - Paid` | Paid impressions only |
| `<Platform> Views - Total` | Total views |
| `<Platform> Views - Organic` | Organic views |
| `<Platform> Views - Paid` | Paid views |
| `<Platform> Total Engagements - Total` | Total engagements (likes + comments + shares + saves, platform-dependent) |
| `<Platform> Total Engagements - Organic` | Organic engagements |
| `<Platform> Total Engagements - Paid` | Paid engagements |
| `<Platform> Engagement Rate - Total` | ER as `0.0-1.0` fraction (e.g., `0.0345` = 3.45%) |
| `<Platform> Ad Spend - Paid` *(paid platforms only)* | Total spend in USD |

### Gotchas

- **Curly apostrophes**: MS exports use right single quote (`'`) in titles like `Women's`. The parser normalizes these to straight quotes during episode attribution — no action needed on your side, just be aware that `Women's` in YAML still matches `Women's` in the export.
- **YouTube negative-export bug**: MS sometimes exports YT columns as negative numbers (e.g., `YouTube Total Engagements - Organic = -6325`). The parser takes `abs()` to normalize.
- **MS "Engagements - Organic" YT trap**: when MS treats `YT Engagements - Organic` as `Total - Paid`, the "Paid" column on cross-posted videos can contain Google Ads' inflated interaction count, making "Organic" go large-negative. The parser falls back to `engagements_total` when `engagements_organic` is implausible (> total).
- **Carousel vs Story**: post type `Carousels & Saved Stories` is classified as a carousel (not a story) — the parser checks `carousel`/`photo` keywords before `story`.

---

## 2. Google Ads YouTube Paid (`.tsv`, UTF-16 LE w/ BOM or `.csv`)

Standard Google Ads campaign-report export. Both encodings work; the parser auto-detects.

### Required columns

| Column | Purpose |
|---|---|
| `Campaign` | Campaign name. Drives subtype detection and episode attribution (must include `PP Episode N -` prefix — see [Naming conventions](#naming-conventions) below) |
| `Impressions` *(or `Impr.`)* ⭐ | **Total ad-renders.** Use the explicit Google Ads value — only auto-derived as fallback when this column is missing entirely. |
| `TrueView views` | View count (TrueView definition) |
| `Cost` | Total spend, USD |
| `Engagement rate` | Google Ads' official ER as a percentage value (e.g., `64.98%`) |
| `Engagements` | Google Ads' engagement count (includes clicks + watch progress + earned views — NOT just L+C+S) |

### Required for subtype detection (Google Ads auto-fills these)

| Column | Populated when |
|---|---|
| `TrueView view rate (In-stream)` | Campaign ran as Pre-roll |
| `TrueView view rate (In-feed)` | Campaign ran as In-feed |
| `TrueView view rate (Shorts)` | Campaign ran as Shorts (including cutdowns) |

Only one of these three will be populated per row — the dashboard uses that signal to bucket the campaign into the right YouTube channel (YouTube In-feed / YouTube Pre-roll / YouTube Shorts).

### Optional but useful

- `Avg. CPM`
- `TrueView avg. CPV`
- `Video played to 25% / 50% / 75% / 100%`
- `Interactions` / `Interaction rate`
- `Conversions` / `Cost / conv.`

### Fallback behavior

If `Impressions` (or `Impr.`) is **missing** from a row, the parser derives it as:

```
Impressions = TrueView views ÷ (TrueView view rate ÷ 100)
```

…and emits a warning in the refresh output naming the file + row count. Always include the Impressions column to silence this — Google Ads' own number is authoritative.

### Gotchas

- **Pre-roll ER (In-stream) is huge** (60–77%). Google counts watch-progress as engagement, which makes Pre-roll incompatible with social ER. The dashboard **excludes Pre-roll from every aggregate ER calculation**. It still shows in its own channel row.
- **Cutdowns are typically Shorts**. Even when the campaign name doesn't have a `(Shorts)` suffix, Google fills `TrueView view rate (Shorts)` — the parser trusts the view-rate signal first.

---

## 3. Meta Ads (`.csv`, UTF-8)

From Meta Ads Manager. Used when we run **dark posts as paid media** — Measure Studio can't see dark posts, so this is the only place that data lives.

### Required columns

| Column | Purpose |
|---|---|
| `Campaign name` | Campaign name; platform inferred from `(IG)` / `(FB)` suffix (see [Naming conventions](#naming-conventions)) |
| `Impressions` | Paid impressions |
| `Reach` | Unique users reached |
| `Post engagements` | Meta's total post-engagement count (reactions + comments + shares + saves + post clicks) |
| `Amount spent (USD)` | Total spend |

### Optional

- `Reporting starts` / `Reporting ends` — for display only
- `Campaign delivery` — status hint
- `Result indicator`, `Results` — primary KPI value

### Per-row treatment

- `boosting = DARK` on every row
- Platform = Instagram if name ends `(IG)`, Facebook if `(FB)`, else defaults to Instagram
- ER computed as `Post engagements ÷ Impressions` (Meta doesn't export an ER column)

### Gotchas

- **Meta "Post engagements" includes more than L+C+S** (clicks on the post, photo views, video plays). For dark video posts the ER can land at 60–70% — comparable to YT Pre-roll territory. We do not currently exclude Meta from aggregate ER, but flag this when comparing across platforms.
- **Double-count caveat**: if you ever also ingest MS organic Instagram data for the same campaign, add `instagram` and `facebook` to that campaign's `ms_organic_only_for` list in `campaigns.yaml` so MS totals get reduced to their organic share.

---

## 4. X Ads (`.csv` from Apple Numbers `.numbers`)

Export both Full + Cutdown sheets into one combined CSV.

### Required columns

| Column | Purpose |
|---|---|
| `Tweet text` *or* `Ad name` | Campaign name — needs `PP Episode N -` prefix for episode attribution |
| `Impressions` | Paid impressions |
| `Engagements` | Total engagements |
| `Spend` | Total spend, USD |

### Optional

- `Engagement rate` — parser computes it from eng/impr if missing
- `Clicks` / `Link clicks` — for display

### Treatment

- `boosting = DARK` on every row
- Platform = X
- For E\*TRADE specifically, `ms_organic_only_for: [x, youtube]` in YAML prevents MS X totals from being summed with X Ads (would otherwise double-count ~$251K in impressions)

---

## 5. TikTok Ads (`.csv`, UTF-8) — placeholder schema

The parser is in **flexible mode** until a real TikTok export confirms the column names. It tries several known candidates per logical field.

### Tentative required columns

| Logical field | Tried in order |
|---|---|
| Campaign name | `Campaign name`, `Ad name`, `Ad group name`, `Name` |
| Impressions | `Impressions`, `Impr.`, `Impressions (paid)` |
| Video views | `Video views`, `Views`, `2-second video views` |
| Engagements | `Engagements`, `Total engagements`, `Post engagements` |
| Spend | `Cost (USD)`, `Cost`, `Amount spent (USD)`, `Spend` |

### When you share a real TikTok export

The flexible-mode CANDIDATE_COLS will be replaced with a strict `REQUIRED_COLS` set matching the actual column names — mirroring how Meta is configured today. Until then, the parser surfaces a warning if it can't find what it needs.

### Treatment

- `boosting = DARK` on every row
- Platform = TikTok
- `post_format = REELS_SHORTS` (TikTok is vertical short-form by default)

---

## Naming conventions

The dashboard's episode-attribution magic depends on what you put in the **campaign name** column. MS organic posts route via `User Tags`, but Google Ads / X Ads / Meta Ads / TikTok Ads only give us the campaign name. **Set up your campaigns with these patterns and attribution is automatic.**

### Universal pattern

```
<Series>_<Episode tag>_<Variant> (<Platform>)
```

Where `<Episode tag>` is your internal tag — usually `PP Episode N` (Portfolio Players) or `FOS Episode N` (Future of Sports). This is the **same string** that goes in the MS `User Tags` column, so every source routes through the same attribution rule.

### Per-source examples

**Google Ads (YouTube)**
```
Portfolio Players S3 Ep5: Assia Grazioli-Venier (pre-roll)
Portfolio Players S3 Ep5: Assia Grazioli-Venier (in-feed)
Portfolio Players S3 Ep5: Assia Grazioli-Venier Cutdown 1 (Shorts)
ADP_Future of Sports_Full Episode 1 (pre-roll)
ADP_Future of Sports_Episode 1 Cutdown 1
```

Required tokens:
- `<Series> <Episode N>: <Guest>` — so the parser can match `PP Episode 5 -` or `Episode 1` against the episode keyword list
- Format suffix in parens: `(pre-roll)` / `(in-feed)` / `(Shorts)` — important for subtype display when view-rate columns are partial
- `Cutdown` token if it's a cutdown (defaults to Shorts via view-rate, falls back to in-feed)

**X Ads**
```
PP Episode 5 - Assia Grazioli-Venier (X)
ADP Episode 1: Kim Ng (X)
```

The `PP Episode N -` prefix is the magic token — same as MS User Tags.

**Meta Ads (dark posts)**
```
<Partner>_<Series>_<Component>_<Variant> (<Platform>)

US Bank_NFL Draft_The Come Up_Video 1 (IG)
US Bank_NFL Draft_The Come Up_Video 1 (FB)
US Bank_NFL Draft_Red Carpet_Video 2 (IG)
ADP_Future of Sports_Episode 1 Cutdown 1 (FB)
E*TRADE_Portfolio Players_PP Episode 5 - Assia Grazioli-Venier (IG)
```

Required:
- Platform suffix `(IG)` or `(FB)` — drives platform attribution
- For social campaigns (no episodes), component + variant labels for tile/table grouping
- For content campaigns, include the `PP Episode N -` token so episode attribution can pick it up

**TikTok Ads**
```
US Bank_NFL Draft_The Come Up_Video 1 (TT)
E*TRADE_Portfolio Players_PP Episode 5 - Assia (TT)
```

### General rules

1. **Include the episode tag verbatim** wherever attribution matters: `PP Episode 5 -` or `Episode 1` should appear in the campaign name *exactly* as it does in the YAML's `match` list.
2. **Use underscores or colons consistently** as separators — both work, but stay consistent within a campaign so partners can scan exports.
3. **Platform suffix in parens** — `(IG)`, `(FB)`, `(TT)`, `(X)`, `(Shorts)`, `(pre-roll)`, `(in-feed)`. Helps both the parser and humans.
4. **Avoid generic terms** like "Women's Soccer" or "NWSL" in the campaign name if multiple episodes touch the same topic — they'll route to whichever episode has those keywords. Stick to the explicit episode tag.

---

## Validating your export

After dropping a new export into `tests/fixtures/`, run:

```bash
python -m app.viewer.refresh
```

The console output prints per-campaign post counts plus any warnings. **Look for:**

| Output | What it means | Action |
|---|---|---|
| `✓ All MS posts attributed to an episode.` | Every Measure Studio row landed in an episode | None — perfect |
| `⚠ Unattributed MS posts:` | Some MS rows didn't match any episode keywords | Add keywords, or list the `Post ID` under an episode's `manual_posts` |
| `Google Ads export missing 'Impressions' column — derived from views ÷ view rate for N row(s)` | Auto-derivation fallback fired | Add `Impressions` column to the Google Ads export template |
| `missing Measure Studio file` (or any source) | YAML references a file not present in `tests/fixtures/` | Drop the file in, or remove the reference from YAML |
| `Meta Ads export is missing required columns: [...]` | Export doesn't have the required columns | Add them to the Meta Ads Manager export template |

The same data is surfaced visually in the dashboard's **Data Archive** tab — every source file is listed with its campaign, post count, last-modified date, and an OK/Missing badge.

---

## What happens if a column is missing?

- **Required columns missing** → the parser returns an error, no rows are added for that file, refresh continues with a clear warning.
- **Optional columns missing** → the parser uses sensible defaults (e.g., Meta ER is computed if not in the export).
- **Whole file missing** → refresh logs `[<campaign>] missing <source> file: <path>` and continues without that file's contribution.

The dashboard never silently drops data — every parse problem surfaces either in the console output or in the Data Archive page's MISSING badges.
