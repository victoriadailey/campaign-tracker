# Campaign Tracker — New Machine Setup + Operating Notes

You're holding `campaign-tracker.tar.gz`. This is the entire project minus the things that get rebuilt by `pip install`: no `.venv`, no caches, no `*.egg-info`.

This file has two parts:
1. **Setup** — get a fresh machine running in ~5 minutes
2. **Operating notes** — every data rule, quirk, and bug fix you'd otherwise have to rediscover. Read it once.

---

## Part 1 — Setup

### 1. Untar somewhere sensible

Match the old path so absolute paths in commit notes still resolve:

```bash
mkdir -p ~/Documents/Claude
cd ~/Documents/Claude
tar -xzf ~/Desktop/campaign-tracker.tar.gz
cd campaign-tracker
```

You should see: `app/`, `config/`, `docs/`, `tests/`, `viewer/`, `pyproject.toml`, `README.md`, `Dockerfile`, `HANDOFF.md` (this file), `refresh.sh`.

### 2. Install Python 3.12

```bash
python3 --version
```

If it says **3.12.x**, you're fine. Otherwise:

```bash
brew install python@3.12
```

### 3. Create venv + install deps

```bash
cd ~/Documents/Claude/campaign-tracker
python3.12 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -e ".[dev]"
```

`.[dev]` installs runtime deps (pandas, pyyaml, requests, python-dotenv) plus pytest + ruff. ~90 seconds.

### 4. Restore your `.env` (carries the MS API token)

The tarball **does not contain `.env`** — that file holds your Measure Studio API token and is gitignored. You need to bring it over yourself.

On the OLD machine:
```bash
cat ~/Documents/Claude/campaign-tracker/.env
```
Copy the line `MEASURE_STUDIO_API_TOKEN=...` over via 1Password / secure note / Signal-to-self.

On the NEW machine:
```bash
cp .env.example .env
# Edit .env, paste the MS API token
```

Without `.env`, the MS API call in `refresh.sh` will fail with a clear error and the dashboard will be stale.

### 5. Verify it works

```bash
.venv/bin/pytest tests/ -q
```

Should report **all passing** in ~1.5s. If anything fails, stop and investigate.

### 6. Refresh + open Pulse

```bash
./refresh.sh
open viewer/Pulse_Dashboard_Standalone.html
```

`refresh.sh` does the full pipeline: live MS API pull → merge all ad-platform CSVs → write `viewer/data.js` → bundle into the standalone HTML → copy to Desktop.

If MS API fails after retries the script returns exit code 2 and **skips the rebundle**, so the last-good dashboard stays on Desktop. That's intentional — re-run after a minute or drop a fresh manual CSV.

### 7. Daily workflow

```bash
./refresh.sh              # full refresh + rebundle + Desktop copy
./refresh.sh --quiet      # suppresses the per-campaign summary
```

After a new CSV drops into `tests/fixtures/`, you just rerun `./refresh.sh`. No config changes needed unless the filename or campaign mapping is new.

---

## Part 2 — Operating Notes

These are the rules, quirks, and gotchas baked into the pipeline. They explain WHY the code does what it does. Skim once, refer back when something looks off.

### Pipeline architecture

```
config/campaigns.yaml                   ← campaign metadata + source file mappings
       │
       ▼
MS API call (per group) + CSV parsers   → list of NormalizedPost per campaign
       │
       ▼
Cross-group manual_posts fetch          ← pulls pinned posts from any MS account
       │
       ▼
Platform-specific merges:               ← combine same-creative duplicates
   • _merge_x_ads_spend_into_ms
   • _merge_youtube_paid_spend_into_ms
   • _merge_linkedin_ads_into_ms
   • _merge_facebook_organic_paid_pairs
       │
       ▼
rollup_campaign + episode rollups       → CampaignSummary, episode breakdowns
       │
       ▼
render.py → viewer/data.js              → bundle.py → Pulse_Dashboard_Standalone.html
```

### Data sources by campaign

Every active campaign as of 6/2:

| Campaign | Type | MS Group | Ad-platform CSVs |
|---|---|---:|---|
| ADP | content | (legacy) | `adp_*_x_ads.csv`, `adp_*_yt_paid.csv` |
| E\*TRADE Portfolio Players (PFP) | content | 6197 | `portfolio_players_x_ads.csv`, `portfolio_players_yt_paid.csv` |
| E\*TRADE BrandX | brandx | 7445 | (MS-only) |
| Spectrum Fueling Dreams | social | 7172 | `spectrum_yt_paid.csv`, `spectrum_x_ads.csv` |
| Morgan & Morgan Case Study | social | 7176 | `morgan_morgan_yt_paid.csv` |
| On Location FIFA | content (paid_only) | 7433 | `onlocation_fifa_yt_paid.csv`, `onlocation_fifa_x_ads.csv`, `onlocation_fifa_linkedin_ads.csv`, `onlocation_fifa_meta_ads.csv` |
| Heineken World Cup | content | 7587 | `heineken_yt_paid.csv` |
| RBC TST | content | 7565 | `rbc_tst_yt_paid.csv`, `rbc_tst_x_ads.csv` |
| Thrivent AFHU | social | 7515 | `thrivent_x_ads.csv` |

### Key YAML flags (`config/campaigns.yaml`)

| Flag | What it does |
|---|---|
| `paid_only: true` | Zeroes all organic-side metrics; backfills paid from totals when MS only reports one combined number. Use for fully-dark campaigns (e.g. On Location). |
| `flight_tbd: true` | Renders flight as "TBD"; zeroes elapsed-time math; status pill reads "Flight TBD" instead of pace status. Use for new campaigns with no confirmed dates. |
| `brandx_objective` / `brandx_secondary_objective` | Selects which CPM/CTR benchmark applies for BrandX campaigns (awareness / clicks / app_install). |
| `ms_organic_only_for: [youtube]` | Reduces MS YT data to its organic share — prevents MS+GAds YT double-counting when Google Ads is the paid source. |
| `organic_by_design_for: [tiktok]` | Suppresses "TikTok resonating" callout when paid is forbidden by contract (e.g. E\*TRADE). |
| `yt_paired_by_sort: true` | Opt into Pass 5 of the YT merge: sort MS+GAds by paid_impr desc within each subtype, zip 1:1. Use when guest-matching can't pair (Spectrum: "NASCAR DITL" GAds vs MS posts titled "From the garage to pit road"). |
| `x_ads_pairings` | Manual MS-tweet-ID overrides for X Ads campaigns whose names don't include the tweet number. |
| `ad_title_overrides` | Substring → friendly title (US Bank uses this to convert "US Bank_NFL Draft_The Come Up_Video 1" → "Mauigoa"). |

### Episode `manual_posts` — three behaviors

1. **In-group pin**: post's `post_id_native` matches a pinned ID and the post is already in the campaign's MS group → matcher uses pin instead of keyword.
2. **Cross-group pin**: post isn't in the campaign's MS group but lives elsewhere in MS (e.g. Heineken's YT Short `Y1A4YYmNyc0` is on the main FOS YT channel, not in MS group 7587). The refresh's cross-group fetch finds it by native ID across all FOS-authed accounts and adds it to the campaign's post list.
3. **Re-merge after cross-group**: when a cross-group pin lands on YT/LinkedIn/FB, the relevant merge step runs again on that campaign so the new MS post can pair with its ad-platform counterpart.

Native ID format by platform:
- YouTube: video ID (11 chars `[A-Za-z0-9_-]`, e.g. `Y1A4YYmNyc0`)
- Instagram / Facebook: platform numeric ID (e.g. `3908614570004578420`)
- X / Twitter: tweet status ID
- Snapchat: long alphanumeric slug from URL (e.g. `W7_EDlXW...`)
- LinkedIn: `urn:li:ugcPost:XXXXX`

### Impressions rules (the source of many subtle bugs)

These rules live in `app/sources/measure_studio_api.py:_to_normalized_post`. Read them before changing anything about impressions.

1. **Negative organic collapses to None.** MS computes `impressions_organic = total − paid`. For paid-heavy YT Shorts and Reels, MS often reports `impressions_paid > MS-tracked total`, so organic goes negative. `_nz_org` returns `None` for any negative value; downstream code knows that means "MS's organic figure is unreliable, don't synthesize one."

2. **Views → impressions on IG / FB / TikTok / Snapchat.** These platforms autoplay video, so a "view" is functionally an impression. If MS doesn't report impressions_organic but does report views_organic, treat views_organic as impressions_organic. For Snapchat / IG Stories where only `views_total` exists (no organic/paid split), use views_total as the organic impressions floor.

3. **Facebook static-post fallback** (`page_media_views_paid`). For non-Reels FB ads, MS reports paid impressions under `page_media_views_paid` (not `plays_paid` — that's video-only). Without this fallback, Thrivent's static FB ads showed paid=0 even with real spend.

4. **YouTube Shorts views-as-impressions floor — tightened.** This rule originally fired for any YT Short where views_total > 0. That double-counted paid views as organic for dark YT Shorts (MS reports `impressions_paid=970K, impressions_organic=-963K, views_total=557K` for the Evelyn Shores RBC post — the rule was setting impressions_organic = 557K, doubling reach). Now the rule **only fires when BOTH `impressions_paid` and `impressions_organic` are None** — i.e., truly organic Shorts.

5. **YT views ≠ YT impressions.** `_pick_impressions` for YT prefers impressions over views (impressions = ad renders, views = video plays watched). The campaign-level channel rollup (`per_campaign_channels`) and per-post emit both have explicit YT guards that exclude `views_organic` from the organic-impressions fallback chain — using it on YT inflates organic impressions by the play count.

### `dist_kind` — YT-aware organic signal

`dist_kind` is the "Organic / Paid / Organic+Boosted" tag in the per-post table. The "has organic activity" check originally only looked at `impressions_organic`. For YT Shorts that's broken (see rule 4 above). The current logic:

```python
has_org = (
    organic > 0
    or (p.views_organic or 0) > 0
    or (p.engagements_organic or 0) > 0
    or (p.reach_organic or 0) > 0
    or p.boosting is Boosting.ORGANIC
    or not has_paid
)
```

Any positive organic signal flags the post as "has organic activity" → dist_kind becomes `organic+boosted` when there's also paid. Without this, RBC's "Evelyn Shores" Short (970K paid + 391K organic views) was tagged "paid only".

This logic is mirrored in both `app/compute/episodes.py` (per-episode tables) and `app/viewer/refresh.py:_post_rows_for` (BrandX + social post tables).

### YouTube pre-roll subtraction (applied at 4 grains)

MS's view count on the in-feed long-form video **already includes** plays surfaced as pre-rolls on other videos. To avoid double-counting, subtract GAds-reported pre-roll views from the in-feed view bucket. Applied at:

1. **Campaign total views** (`rollup_campaign` in `app/compute/rollup.py`)
2. **Campaign per-channel views** (`per_campaign_channels`)
3. **Episode total views** (`compute_episodes` in `app/compute/episodes.py`)
4. **Per-post row views** (both `episodes.py` posts_rows and `refresh.py` `_post_rows_for`)

The per-post fix was added after the team noticed Kim Ng Ep 1's in-feed row showing 44,196 views while the channel rollup correctly showed 20,200. All four grains now reconcile.

### Facebook organic + dark ad merge (`_merge_facebook_organic_paid_pairs`)

Facebook treats organic page posts and paid dark ads as distinct posts — each gets its own `platform_id`, and MS surfaces them as two rows. The merge step pairs them by `(account_handle, normalized description prefix)` when one is paid-only and the other is organic-only. Surviving row is the organic post (which carries likes/comments/shares engagement metadata).

This is FB-specific. Other platforms (IG, X, LinkedIn) merge the paid boost into the same MS post.

### YouTube paid merge (`_merge_youtube_paid_spend_into_ms`)

6 passes, executed in order until each GAds row is matched:

1. **Same guest + exact paid_impr** — most confident
2. **Same guest + closest paid_impr ±5%** — handles reporting drift
3. **Same guest, 1:1 unambiguous** — handles cases where MS and GAds disagree wildly
4. **Sweep — add second GAds row** to an already-merged post (original + REDO campaigns)
5. **Sorted-position fallback** (opt-in via `yt_paired_by_sort: true`) — sort by paid_impr desc, zip 1:1 within subtype
6. **Cross-subtype 1:1 fallback** — when exactly one unmatched MS post + one unmatched GAds row remain, same subtype + impressions in same ballpark OR one side has 0 paid (handles freshly-published organic posts being promoted)

The merge pool now includes 0-paid MS posts so freshly-published organic content can pair with its paid promotion before MS has accumulated delivery data.

### TBD / pending campaigns

Three independent "TBD" knobs:

| Field | YAML | Renders as |
|---|---|---|
| Flight TBD | `flight_tbd: true` | Status pill: "Flight TBD"; flight label: "TBD"; elapsed pct: 0 |
| Impression goal TBD | `impression_goal: 0` | Banner: "goal TBD"; subline: "Pacing pending" (when flight_tbd too) or "No impression goal set" |
| Budget TBD | `budget_goal: 0` | Banner: "budget TBD"; subline: "$X delivered · budget cap pending" when spend > 0 |

RBC TST currently has real flight + real impression goal but `budget_goal: 0` (client hasn't confirmed). Thrivent currently has `flight_tbd: true` + real goals (900K impr / $1K spend).

### Per-platform post-count ceilings

`POST_COUNT_CEILINGS` in `app/viewer/refresh.py` flags ad-platform exports that got broken out by daily performance (creating one row per ad-day instead of one row per ad). Currently only set for On Location:
- `facebook/instagram/linkedin/tiktok/x`: ≤4 (1 full episode + 3 cutdowns)
- `youtube`: ≤6 (full episode + in-feed + pre-roll variants + 3 cutdowns)

If a re-export blows past these, the refresh prints a warning. Update the ceiling if the creative count legitimately grew.

### Account name display (`account_name`)

MS posts now carry `account_name` (the FB page / IG handle's display name) and `account_handle` (the UID). Plumbed via `MeasureStudioClient.fetch_group`, which pre-fetches `/accounts` and builds a UID→name map. The per-post UI shows `@ Front Office Sports` / `@ Front Office Sports Today` / `@ Front Office Sports News` as a small subline under post titles. Distinguishes posts that share the same copy across pages (e.g. the Champions League content on FOS Main vs FOS Today).

### BrandX-specific UI

E\*TRADE BrandX (`type: brandx`) gets a completely different page treatment:
- **Status banner header** with three columns: impressions vs goal, spend vs budget, total clicks (no goal)
- **Secondary metrics row** (5 tiles): Blended CPC, Blended CTR vs benchmark, Video Completion (VCR), Avg View Duration, Frequency
- **Per-platform CPM benchmark table** (replaces blended-CPM WATCH callout)
- **Post-level table** with paid-performance columns: Reach, Spend, AVD, Clicks, CTR, CPC/CPM

VCR is computed as `100%-watched views / 3-second video starts` (Meta's standard "view started" denominator). AVD = `total watch time / 3-sec starts`. For Instagram ads where MS doesn't report watch_time_minutes, AVD is estimated by trapezoidal integration of the p25/p50/p75/p95/p100 retention ladder × video duration.

### MS API client (`app/sources/measure_studio_api.py`)

- Retries 5xx / 429 with exponential backoff (4 retries, 2/4/8/16s waits)
- 401 / 404 fail fast (no retry — config issue)
- Caches account list + cross-account post lookups for the lifetime of the client
- `find_post_by_native_id(post_id, platform_hint)` does cross-account scanning for cross-group manual_posts pins

### Heineken / On Location / Spectrum quirks

- **Heineken YT Short** is hosted on the main FOS YT channel (`Y1A4YYmNyc0`), not in MS group 7587. Pinned via `manual_posts` + cross-group fetch. The GAds row name has `(shorts)` suffix so it classifies as YT Shorts (not the default in-feed).
- **On Location is fully `paid_only`** — no organic anything. The "FOSN" / "FOS Today" / "FOS Main" Champions League FB posts are NOT On Location, they're Heineken.
- **Spectrum** uses `yt_paired_by_sort: true` + GAds names manually have `(shorts)` suffix because MS post titles ("From the garage…", "From the hangar…") share no tokens with GAds names ("NASCAR DITL", "NASCAR Small Biz").

### CTA-label cleanup (Meta dark ads)

MS returns FB ad CTA button text (e.g. "Chat with us", "Sign Up", "Learn More") in the post `title` field instead of the actual ad copy. `_META_CTA_LABELS` set in `measure_studio_api.py` covers all Meta CTA labels — when MS's title matches one, we null it and fall through to `description`.

---

## Part 3 — What's NOT in the tarball

- `.venv/` — recreated by Step 3
- `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `*.egg-info/` — recreated on first run
- `.DS_Store` — macOS clutter
- `.env` — sensitive (MS API token); bring over manually (Step 4)
- `.git/` — **included**; full commit history preserved

## What IS in the tarball (and shouldn't be public)

- `tests/fixtures/*.csv` — real campaign exports across all 9 active campaigns. Confidential.
- `config/campaigns.yaml` — internal goals, manual_posts pin IDs, X-Ads pairings.
- `viewer/data.js` — current refresh state (regenerate after first run).
- `viewer/Pulse_Dashboard_Standalone.html` — bundled dashboard (regenerate).

## Where to put new CSV exports

Drop in `tests/fixtures/`. The filename must match what's listed under each campaign's `sources:` block. Examples:

| Source | Filename pattern |
|---|---|
| X Ads | `<campaign>_x_ads.csv` |
| Google Ads (YT) | `<campaign>_yt_paid.csv` |
| Meta Ads | `<campaign>_meta_ads.csv` |
| TikTok Ads | `<campaign>_tiktok_ads.csv` |
| LinkedIn Ads | `<campaign>_linkedin_ads.csv` |

LinkedIn Ads exports are UTF-16 LE TSV from LinkedIn Campaign Manager — the parser auto-detects encoding. Google Ads exports start with three header rows ("FOS Reporting" / date range / column headers).

---

## Troubleshooting

| Symptom | Cause / Fix |
|---|---|
| `ModuleNotFoundError: No module named 'app'` | Forgot `pip install -e .[dev]` |
| `python3.12: command not found` on Apple Silicon | Use `/opt/homebrew/bin/python3.12 -m venv .venv` |
| Refresh fails: "MEASURE_STUDIO_API_TOKEN must be set" | `.env` is missing or not populated — see Step 4 |
| Refresh exits code 2, dashboard not rebundled | MS API failed after 5 attempts. Re-run after a minute, OR drop a manual CSV and comment out `measure_studio_group_id` for that campaign |
| Tests fail with pandas import errors | You're on Python 3.13+. Recreate venv with `python3.12` |
| Dashboard shows old data after refresh | Browser cache. Cmd+Shift+R |
| "Unattributed MS posts" warning | A post matches no episode keyword. Either (a) add a keyword to the episode's `match:` list, or (b) pin the post via `manual_posts: [<post_id_native>]`. The warning prints the post_id and title to copy/paste. |
| "Per-platform post-count anomalies" warning | Ad-platform export was broken out by daily performance. Re-export aggregated by ad, not by day. |

---

## Claude / conversation context

This dashboard has accumulated months of design decisions and bug fixes through conversation with Claude. Claude's memory is **tied to your Claude account**, not to a specific machine — when you log into Claude on the new machine, the conversation history and project memory come with you automatically.

Specifically these memory paths persist via your Claude account:
- `/Users/<you>/.claude/projects/-Users-victoriabaldwindailey-Documents-fos-dashboards/memory/` — long-form project memory
- `/Users/<you>/.claude/projects/-Users-victoriabaldwindailey-Google-Reports/memory/MEMORY.md` — user-level auto-memory

If you want a physical backup, copy those directories alongside the tarball, but they should restore automatically.
