# Data Sources — Real Shapes

Verified from sample exports the user shared on 2026-04-27.

## 1. Measure Studio CSV (primary source)

**The most important parser to get right.** Covers paid, organic, and boosted across all major platforms when MS is healthy. Same schema across all exports (verified across USB, ETRADE, Tastytrade samples).

**Sample files** (paths user shared):
- `~/Downloads/USB The Come Up 4.27.csv`
- `~/Downloads/ETRADE x Portfolio Players 4.9.csv`
- `~/Downloads/Tastytrade 4.9.csv`
- `~/Downloads/ADP Future of Sports Cutdown Measure Export 5-5-26.csv`
- `~/Downloads/ADP Future of Sports Full Episode Measure Export 5-5-26.csv`
- `~/Downloads/Portfolio Players - Measure Export.csv`
- `~/Downloads/Tastytrade - Campaign 4.2.zip` (zip exports also a thing)

**Format**:
- Skip rows 1–7 (metadata: Period, Accounts, Groups, Dates Published, Sorted by, Keyword search)
- Row 8 = headers (~320 columns)
- Rows 9+ = data; one row per (post, platform) combination

**Key columns**:
| Column | Purpose |
|---|---|
| `Account Name`, `Account Handle`, `Account ID` | Brand/handle |
| `Post ID`, `Internal Reference ID` | Unique IDs |
| `Date Published`, `Time Published` | Timestamp |
| `Post Platform` | instagram / facebook / youtube / tiktok / x / linkedin |
| `Post Type` | "Reels, Shorts, & Spotlights" / "Videos" / etc. |
| `Post Title`, `Post Description`, `Post URL` | Content |
| `Post Group(s)` | **The campaign join key** — e.g. "The Come Up", "Portfolio Players S3 x E*TRADE", "Tastytrade" |
| `Organic / Boosted / Dark` | Boosting state |
| `Video Duration (seconds)` | For longform/cutdown classification |
| `AI - Categories`, `AI - Video Transcript` | Content metadata; useful for callouts |

**Per-platform metric columns** (each platform has its own block, prefixed by platform name):
- Views (Total / Organic / Paid)
- Impressions (Total / Organic / Paid)
- Reach (where applicable)
- Engagements (Total / Organic / Paid)
- Engagement Rate (multiple denominators)
- Watch Time, Average Watch Time
- Paid: Ad Spend, CPM, CPC, CPV, CPP, CTR, CTE, CPA, Conversions
- Quartile views (25/50/75/100%)
- Platform-specific: Snapchat publisher metrics, Facebook reactions, etc.

**Critical data shape**: most platform columns are **null** for any given row — only the row's `Post Platform` block is populated. This means the CSV is a **wide table** that needs to be **melted into long format** during ingestion: one (post, platform) → one normalized record with platform-agnostic fields.

**Filtering**: each campaign export is pre-filtered by Post Group(s) at MS export time. The tool should also support multi-Post-Group campaigns (e.g., E*TRADE = "Portfolio Players S3" + "Portfolio Players S3 x E*TRADE").

## 2. Google Ads CSV (consistent #2)

Used because MS doesn't currently show paid YouTube metrics (issue MS is working to fix). Once fixed, this becomes redundant.

**Two report formats** (sample files):
- `~/Downloads/US Bank - YouTube (1).csv` — Ad-level by campaign-name pattern
- `~/Downloads/Google - Ad report (55).csv` — Full Ad report (per-ad detail)
- `~/Downloads/Google - Campaign report (17).csv` — Campaign-level rollup

**Format**:
- Skip rows 1–2 (header: report name + date range)
- Row 3 = headers
- Rows 4+ = data

**Ad-level columns** (Ad report): Status, Final URL, Headline, Description, Video, Video ID, Companion banner, Ad name, Path, Campaign, Ad group, Status reasons, Ad type, Ad strength, Cost, Impressions, Avg CPM, Engagements, Engagement rate, TrueView views, YouTube public views, TrueView avg CPV, Watch time

**Campaign-level columns**: Campaign status, Campaign, Budget, Budget type, Campaign type, CPM, Impressions, Cost, Engagements, YouTube public views, Watch time, Avg watch time/impr

**Campaign name conventions** (the join key to FOS campaigns):
- `Portfolio Players S3 Ep 4: Paul Rabil (in-feed)`
- `State Farm_The Family Assist_Full Ep (pre-roll)`
- `US Bank_NFL Draft_The Come Up_Video 1`
- `ADP_Future of Sports_Episode 1 Cutdown 2`

Pattern is `{Partner}_{Series}_{Episode/Asset}_{Format}` or `{Series} {Ep}: {Subject} ({format})`. Need a **gads_name_patterns** field per campaign — list of substrings/regex to match. Cutdown vs full vs pre-roll vs in-feed all need to be parsed out as the asset format.

## 3. Fallback sources (emergency only)

When MS is broken. User confirmed these are not the daily pattern but must be supported:
- **Meta Ads Manager** (Facebook + Instagram paid)
- **TikTok Ads Manager**
- **X Ads Manager**
- **In-platform exports** (LinkedIn, X, IG, FB, TikTok native)

Each will need its own parser. **Build deferred** — implement only when MS goes down or user prioritizes. MS-first is the right MVP scope.

## 4. Benchmarks XLSX

**File**: `~/Downloads/Social Benchmarks Dashboard Q1 2026.xlsx` (last updated March 2026)

**Structure**:
- 45+ tabs, **one per campaign** (confirms the 50+/year scale — Q1 alone)
- `BENCHMARK DASHBOARD` master tab — platform × content-type benchmarks (All Content / Sponsored — Sprout no-paid / Sponsored — All)
- Platform ER benchmarks (2025): IG 3.6%, FB 4.0%, X 2.3%, TT 4.9%, LI 5.2%, YT 1.0%
- Sponsored benchmarks (Sprout, no paid): IG 3.8%, FB 2.6%, X 1.1%, TT 0.9%, LI 2.4%, YT 1.0%
- `Full Data` tab — aggregated dataset

**Use in the tool**: load benchmarks at startup or as an admin-uploaded resource. Tag posts/campaigns as "above benchmark" / "below benchmark" automatically; surface as callouts. Per the user, this is a **nice-to-have** — benchmarks already live elsewhere — but a great long-term feature since all data will eventually be in this tool.
