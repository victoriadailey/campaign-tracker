# Measure Studio API integration

**The data architecture: MS API is the base; ad-platform CSVs fill the gaps.**

Measure Studio covers most of what the dashboard needs:
- Organic performance across **every** platform (IG, FB, TT, LI, X, YT, Snap)
- Paid performance for IG, FB, TT, LI — accurate, no supplement needed

But MS has known gaps that we backfill with platform-native CSV exports:

| Gap | Why it matters | Filled by |
|---|---|---|
| **X paid spend + impressions** | MS doesn't track X Ads at all | `x_ads:` CSV → merged onto MS X post via tweet URL |
| **YT in-feed paid impressions** | MS under-counts (e.g. Mike Repole: MS shows 158K, GAds shows 1.03M) | `youtube_paid:` CSV → replaces MS's value on the matched YT post |
| **Dark posts MS can't see** | True dark X / Meta / TikTok / LinkedIn ads with no organic counterpart | the relevant ad CSV → kept as own paid-only row |
| **LinkedIn paid spend** | MS surfaces LI dark posts' organic-side data but not spend | `linkedin_ads:` CSV → merged onto MS LI post by title match |

So every campaign typically combines:
1. **MS API** (`measure_studio_group_id`) — the base layer
2. **GAds CSV** (`youtube_paid`) — supplements YT in-feed paid impressions
3. **X Ads CSV** (`x_ads`) — supplements X paid (MS gap) + true dark X
4. **Meta / TikTok / LinkedIn Ads CSVs** — only when those platforms have dark posts that MS can't see

The CSV `measure_studio:` source is only used as a fallback when the API
call fails. Once the API is working it's effectively dead.

---

## 1. Get an API token

In Measure Studio: **Settings → API / Integrations → Personal Access Token**.
Copy the token; it's only shown once.

If your account is gated, ask Erin or your MS admin.

## 2. Configure `.env`

```bash
cp .env.example .env
# Open .env and fill in:
#   MEASURE_STUDIO_API_BASE=<base URL from API docs>
#   MEASURE_STUDIO_API_TOKEN=<paste token>
```

The base URL is `https://app.measure.studio/enterprise_api/v1` (Measure
Studio's Enterprise API v1). Docs: [app.measure.studio/docs/enterprise_api](https://app.measure.studio/docs/enterprise_api).
Auth is **`Authorization: Bearer <token>`**.

`.env` is gitignored — never commit it.

## 3. Verify auth + endpoints work

```bash
.venv/bin/python -m app.sources
```

Expected output:

```
→ Base URL: https://api.measure.studio
→ Token:    abcd1234…wxyz

Accounts (15):
  [9430] instagram          Front Office Sports
  [9427] youtube            Front Office Sports
  …

Post groups (28):
  [  6197] Portfolio Players S3 x E*TRADE      (183 posts)
  [  6217] Future of Sports: Cutdowns          (35 posts)
  [  6111] Future of Sports: Full Episodes     (8 posts)
  …
```

**If it fails:**
- **401** → token is wrong / expired. Re-issue from the MS dashboard.
- **404** → endpoint paths in `app/sources/measure_studio_api.py` (`ENDPOINTS`
  dict) don't match the real API. Update them to match the docs.
- **Network error** → check your VPN / firewall / DNS for the base URL.

## 4. Preview a single group's data

```bash
.venv/bin/python -m app.sources --group 6197
```

Prints the first 3 posts in raw form. Use `--posts 6197 --limit 5` to dump
them as NormalizedPost rows (post-conversion) so you can verify field mapping
before flipping a campaign over.

## 5. Activate the API for a campaign

In `config/campaigns.yaml`, add `measure_studio_group_id:` (or `_group_ids:`
for multi-group campaigns like ADP) under `sources:`. **Keep the ad-platform
CSV blocks** — they supplement MS's known gaps. Only the `measure_studio:`
CSV becomes redundant.

```yaml
- id: etrade
  …
  sources:
    measure_studio_group_id: 6197       # API — base layer
    youtube_paid:                       # GAds CSV — supplements YT in-feed paid
      - portfolio_players_yt_paid.csv
    x_ads:                              # X Ads CSV — supplements X paid + dark X
      - portfolio_players_x_ads.csv
    # measure_studio: …                 # CSV fallback only if the API fails
```

For ADP (two post groups: full eps + cutdowns) use the list form:

```yaml
measure_studio_group_ids: [6217, 6111]
```

### How the merges deduplicate

When the same boosted post shows up in both MS and a supplement CSV:

- **X Ads** → matched to MS X post by tweet URL (Pass 0) or impression count
  (Pass 1/2). `_merge_x_ads_spend_into_ms` folds spend + paid impressions on
  top of the MS post.
- **Google Ads YT** → matched to MS YT post by guest name + impressions
  (`_merge_youtube_paid_spend_into_ms`). For paired posts, GAds **replaces**
  MS's paid figures (because MS under-counts YT in-feed).
- **LinkedIn Ads** → matched to MS LI post by ad headline / post title
  (`_merge_linkedin_ads_into_ms`). Folds paid impressions + spend onto the
  MS post.

Anything that doesn't pair to an MS post stays as its own row — that's the
true-dark coverage.

## 6. Run refresh

```bash
.venv/bin/python -m app.viewer.refresh --exclude usbank --output viewer/data.js
.venv/bin/python -m app.viewer.bundle
```

The refresh script logs which campaigns hit the API vs. the CSV fallback.

---

## Pre-mapped campaign → MS group IDs

Copy these into `config/campaigns.yaml` when you're ready to switch each
campaign:

| Campaign  | MS Group | `sources:` entry                            |
|-----------|---------:|---------------------------------------------|
| ADP       |   6217 + 6111 | `measure_studio_group_ids: [6217, 6111]` |
| E\*TRADE  |     6197 | `measure_studio_group_id: 6197`            |
| Spectrum  |     7172 | `measure_studio_group_id: 7172`            |
| M&M       |     7176 | `measure_studio_group_id: 7176`            |
| On Location | 7433  | `measure_studio_group_id: 7433`            |
| US Bank   |     6494 | `measure_studio_group_id: 6494`            |

---

## How the integration is wired

```
.env                       ← MEASURE_STUDIO_API_BASE + _TOKEN
  │
  ▼
app/sources/measure_studio_api.py
  │  MeasureStudioClient.from_env()
  │  .fetch_group(group_id) → list[NormalizedPost]
  │
  ▼
app/viewer/refresh.py
  │  Reads YAML `sources.measure_studio_group_id(s)`
  │  Tries API first; on any failure, falls back to CSV.
  │
  ▼
viewer/data.js  (rest of pipeline unchanged)
```

### Endpoint surface (Enterprise API v1)

Base: `https://app.measure.studio/enterprise_api/v1`. All GET, Bearer auth.

| Method | Path | Purpose |
|---|---|---|
| GET | `/info` | Workspace owner / company |
| GET | `/accounts` | Connected social accounts |
| GET | `/groups` | Post groups (campaigns) |
| GET | `/tags` | User-created tags |
| GET | `/posts?group_ids=X&period=lifetime` | Paginated posts with inline stats |
| GET | `/posts/{id}` | Single post details |
| GET | `/posts/{id}/stats?metrics=X,Y&period=Z` | Per-post stats (alternative to inline) |
| GET | `/posts/{id}/audience` | Audience demographics (where available) |
| GET | `/accounts/{id}/stats` | Account-level stats |
| GET | `/groups/{id}/platforms/{p}/stats` | Group × platform aggregates |
| GET | `/platforms/{platform}/stats` | Workspace-wide platform stats |

The client only uses `/info`, `/accounts`, `/groups`, and `/posts` today.
The big win: when `period` is passed to `/posts`, each post carries inline
`stats` covering paid + organic metrics — no N+1 follow-up calls.

### Field mapping (MS → NormalizedPost)

| MS field                 | NormalizedPost field        |
|--------------------------|-----------------------------|
| `account_type`           | `platform`                  |
| `status`                 | `boosting` (organic/boosted/dark) |
| `type` / `post_type_label` | `post_format`              |
| `engagements`            | `engagements_total`         |
| `engagements_paid` (analytics) | `engagements_paid`    |
| `views` / `views_paid` / `views_organic` | views_* |
| `impressions_paid` / `impressions_organic` | impressions_* |
| `ad_spend` / analytics `spend` | `ad_spend`            |
| `cpm` / `cpv` / `cpc` / `ctr` (analytics) | rate fields |
| `engagement_rate_paid` (analytics) | `er` (boosted/dark only) |
| `url`                    | `post_url` + parsed native ID |
| `date`                   | `posted_at`                 |
| `groups`                 | `post_groups`               |

### Fallback behavior

If the API client raises `MeasureStudioUnavailable` at startup OR a specific
`fetch_group()` call raises any exception during refresh, the script:
- logs a warning to stdout (so you can see which campaigns fell back)
- continues with the CSV sources defined under `measure_studio:` /
  `youtube_paid:` / `x_ads:` / etc. for that campaign

This means an API outage doesn't break the dashboard refresh — you just need
to have a recent set of CSVs around. Drop them into `tests/fixtures/`
periodically as a backup.
