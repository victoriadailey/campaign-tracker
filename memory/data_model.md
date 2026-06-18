# Data Model

## Firestore collections

### `campaigns/{campaign_id}`

```
{
  partner: "U.S. Bank",
  series: "The Come Up — NFL Draft",
  type: "social" | "longform" | "hybrid",
  status: "planned" | "live" | "complete" | "archived",

  flight_start: Timestamp,
  flight_end: Timestamp,

  impression_goal: int,
  budget_goal: float,
  budget_currency: "USD",

  // Join keys for source matching
  ms_post_groups: ["The Come Up"],          // exact match against MS "Post Group(s)" column
  gads_name_patterns: [                     // substrings to match Google Ads "Campaign" column
    "US Bank_NFL Draft_The Come Up",
    "US Bank: NFL Draft"
  ],

  tags: ["NFL", "Draft 2026"],
  notes: "...",                             // freeform notes shown on detail page

  latest_snapshot_id: "snap_2026-04-27_a1b2",
  created_at, updated_at, created_by
}
```

### `campaigns/{campaign_id}/snapshots/{snapshot_id}`

```
{
  captured_at: Timestamp,
  uploaded_by: "victoria@frontofficesports.com",

  source_files: [
    {
      kind: "measure_studio" | "google_ads_ad" | "google_ads_campaign" | "meta" | "tiktok" | "x" | "native",
      filename: "USB The Come Up 4.27.csv",
      gcs_path: "gs://fos-campaigns/usb_come_up/snap_2026-04-27_a1b2/ms.csv",
      sha256: "...",
      row_count: 87
    },
    ...
  ],

  computed_metrics: {
    total_impressions: 4_213_889,
    total_engagements: 307_293,
    total_spend: 4_980.02,
    blended_er: 0.0729,
    by_platform: { ... },
    by_format: { ... },              // longform: full_episode | cutdown
    pacing: {
      pct_impressions: 0.638,
      pct_budget: 0.498,
      pct_elapsed: 1.0,
      status: "goal_hit" | "on_track" | "behind" | "exceeded"
    }
  },

  is_latest: bool                    // only one true per campaign
}
```

### `benchmarks/q1_2026`

```
{
  source: "Social Benchmarks Dashboard Q1 2026.xlsx",
  loaded_at: Timestamp,
  by_platform_content_type: {
    "instagram_all": 0.036,
    "instagram_sponsored_sprout": 0.038,
    "instagram_sponsored_all": 0.0331,
    "youtube_all": 0.01,
    ...
  }
}
```

## BigQuery tables

For trend analysis and cross-campaign queries. Every successful snapshot upload appends here.

### `posts` (normalized — melted from MS wide format)

```
post_uid               STRING    PK = sha256(source + post_id_native + platform)
campaign_id            STRING
snapshot_id            STRING
captured_at            TIMESTAMP

source                 STRING    measure_studio | google_ads_* | meta_ads | ...
platform               STRING    instagram | facebook | youtube | tiktok | x | linkedin

post_id_native         STRING
post_url               STRING
post_title             STRING
posted_at              TIMESTAMP

format                 STRING    feed_video | reels_shorts | story | full_episode | cutdown | static
boosting               STRING    organic | boosted | dark
duration_sec           FLOAT64

// Normalized metrics (null if not applicable)
views_total            INT64
views_organic          INT64
views_paid             INT64
impressions_total      INT64
impressions_organic    INT64
impressions_paid       INT64
reach                  INT64
engagements_total      INT64
engagements_organic    INT64
engagements_paid       INT64
er                     FLOAT64
watch_time_min         FLOAT64
avg_watch_time_sec     FLOAT64

// Paid only
ad_spend               FLOAT64
cpm                    FLOAT64
cpv                    FLOAT64
cpc                    FLOAT64
ctr                    FLOAT64

// Original raw row preserved for audit
raw_row_json           JSON
```

### `snapshots`

Lightweight metadata table. One row per snapshot. Joins to `posts` on `snapshot_id`.

### Why both Firestore AND BigQuery

- **Firestore** — operational layer. Sub-100ms reads for the app's per-campaign queries; native real-time updates if needed; easy SDK in Python.
- **BigQuery** — analytical layer. Cross-campaign aggregations, trend windows, "show me all posts above benchmark for this partner across all flights" — queries that would melt Firestore.

The tool can ship v1 with Firestore only. BigQuery comes online when trend/benchmark queries become a need.

## Parser contract

Every parser implements the same shape so the upload page is source-agnostic:

```python
def parse(file: BytesIO) -> ParseResult:
    return ParseResult(
        rows: List[NormalizedPost],     # Pydantic model
        warnings: List[str],            # "5 rows missing Post Group"
        errors: List[str],              # "Column 'Cost' missing"
        detected_source: str,           # "measure_studio_v2"
        suggested_campaign_ids: List[str],  # via Post Group / name pattern matching
    )
```

This contract is what makes adding Meta/TikTok/X parsers later trivial — same upload UI, swap the parser based on detection.
