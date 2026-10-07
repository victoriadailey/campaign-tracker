"""Parse the FOS Social Benchmarks CSV into structured data for the viewer.

Source: config/social_benchmarks.csv (last updated 3/5/2025 1pm EST).

Shape of the output (JSON-friendly dicts → emitted as window.BENCHMARKS_DATA):

    {
        "last_updated": "3/5 @1pm EST",
        "platform_summary": [
            {"row": "All Content",                       "platforms": {"Instagram": 3.6, ...}, "all_avg": 3.5},
            {"row": "Sponsored (Sprout, No Paid)",       "platforms": {...}, "all_avg": 1.97},
            {"row": "Sponsored (All content in this doc)","platforms": {...}, "all_avg": 2.47}
        ],
        "categories": [
            {
                "name": "Social Coverage Partner",
                "overall": {"Instagram": 8.63, "Facebook": 2.36, ..., "All": 5.03},
                "campaigns": [
                    {"name": "Acura x Business of the Madness (2024)",
                     "platforms": {"Instagram": 11.32, "TikTok": 3.95, ...},
                     "all": 6.34, "spend": "$0"},
                    ...
                ]
            },
            ...
        ]
    }

Platform values are floats (percentage points). Spend strings preserved as written.
Missing cells render as None / null.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any


def parse_benchmarks_csv(path: Path) -> dict[str, Any]:
    rows = list(csv.reader(path.open()))

    out: dict[str, Any] = {
        "last_updated": _find_last_updated(rows),
        "platform_summary": _parse_platform_summary(rows),
        "categories": _parse_categories(rows),
    }
    return out


def _to_pct(s: str) -> float | None:
    """'3.60%' → 3.6 ;  '-%' → None ;  '' → None"""
    if not s or s.strip() in ("", "-%", "-", "—"):
        return None
    cleaned = s.replace("%", "").strip()
    try:
        return round(float(cleaned), 2)
    except ValueError:
        return None


def _clean(s: str) -> str:
    return (s or "").strip()


def _find_last_updated(rows: list[list[str]]) -> str:
    for r in rows[:10]:
        for cell in r:
            if cell and "Last Updated" in cell:
                # "Last Updated: 3/5 @1pm EST"
                m = re.search(r"Last Updated[:\s]+(.+)", cell)
                if m:
                    return m.group(1).strip()
    return ""


def _parse_platform_summary(rows: list[list[str]]) -> list[dict]:
    """Top 3 rows: All Content / Sponsored (Sprout, No Paid) / Sponsored (All content in this doc)."""
    summary: list[dict] = []
    # Header row contains the platform names
    header = None
    for i, r in enumerate(rows[:6]):
        if len(r) > 2 and r[1].startswith("Platform Benchmarks"):
            header = rows[i]
            break
    if not header:
        return summary
    platform_cols = {idx: header[idx] for idx in range(2, 9) if header[idx]}
    # Three rows follow with All Content / Sponsored variants
    for r in rows[2:6]:
        if not r or not r[1] or "Last Updated" in r[1]:
            continue
        row_label = _clean(r[1])
        platforms: dict[str, float | None] = {}
        all_avg = None
        for col_idx, plat in platform_cols.items():
            if plat == "All (AVG)":
                all_avg = _to_pct(r[col_idx])
            else:
                val = _to_pct(r[col_idx])
                if val is not None:
                    platforms[plat] = val
        if not platforms and all_avg is None:
            continue
        summary.append({"row": row_label, "platforms": platforms, "all_avg": all_avg})
    return summary


def _parse_categories(rows: list[list[str]]) -> list[dict]:
    categories: list[dict] = []
    # Find each "Benchmark Category:" row and parse the section following it
    boundaries: list[tuple[int, str]] = []
    for i, r in enumerate(rows):
        if len(r) > 1 and r[1].startswith("Benchmark Category:"):
            boundaries.append((i, _clean(r[2]) if len(r) > 2 else ""))

    for idx, (start, name) in enumerate(boundaries):
        end = boundaries[idx + 1][0] if idx + 1 < len(boundaries) else len(rows)
        section_rows = rows[start:end]
        categories.append(_parse_section(name, section_rows))
    return categories


def _parse_section(name: str, section: list[list[str]]) -> dict:
    """Parse one Benchmark Category block.

    Layout (approximate):
        Row 0: Benchmark Category: <name>
        Some blank rows
        Row labeled "Overall" — headers row (Instagram, Facebook, etc., All)
        Next row labeled "Engagement Rate" — the category benchmark values
        Blank
        Row labeled "By Campaign" — headers row (same shape)
        Following rows: campaign rows, each with name + platform ERs + spend
        Until end / blank / next section
    """
    overall_platforms: dict[str, float | None] = {}
    overall_headers: list[str] = []
    campaigns: list[dict] = []
    campaign_headers: list[str] = []

    state = "init"  # init -> seeking-overall -> overall-headers-seen -> seeking-campaigns -> campaign-headers-seen
    for r in section:
        if not r or all(not c.strip() for c in r):
            # Blank — stay in current state
            continue
        first = _clean(r[1]) if len(r) > 1 else ""

        if first.startswith("Benchmark Category:"):
            continue
        if first == "Overall":
            # This is the platform header row for the Overall section.
            # Read the full platform span (r[2:10], same width as the By
            # Campaign headers) — some categories (Original Content, Branded
            # Content) carry an extra YouTube column that pushes "All" out to
            # column J. Reading only r[2:9] dropped their "All" value.
            overall_headers = [_clean(c) for c in r[2:10]]
            state = "overall-headers-seen"
            continue
        if first == "Engagement Rate" and state == "overall-headers-seen":
            for idx, h in enumerate(overall_headers):
                if h and h not in ("All", "All (AVG)"):
                    overall_platforms[h] = _to_pct(r[2 + idx])
            # Capture "All" separately
            for idx, h in enumerate(overall_headers):
                if h in ("All", "All (AVG)"):
                    overall_platforms["All"] = _to_pct(r[2 + idx])
            state = "post-overall"
            continue
        if first == "By Campaign":
            campaign_headers = [_clean(c) for c in r[2:10]]
            state = "campaigns"
            continue
        # Some sections use blank label for the campaign headers row
        if state == "post-overall" and first == "" and len(r) > 2 and r[2] in ("Instagram", "YouTube"):
            campaign_headers = [_clean(c) for c in r[2:10]]
            state = "campaigns"
            continue

        if state == "campaigns" and first:
            campaign_name = first
            platforms: dict[str, float | None] = {}
            all_val: float | None = None
            for idx, h in enumerate(campaign_headers):
                if not h:
                    continue
                if 2 + idx >= len(r):
                    break
                val = _to_pct(r[2 + idx])
                if h in ("All", "All (AVG)"):
                    all_val = val
                else:
                    if val is not None:
                        platforms[h] = val
            # Spend is in the "Spend" column area — usually around col 11
            spend = ""
            for col_idx in range(11, min(13, len(r))):
                val = _clean(r[col_idx])
                if val and val.startswith("$"):
                    spend = val
                    break
            campaigns.append({
                "name": campaign_name,
                "platforms": platforms,
                "all": all_val,
                "spend": spend,
            })

    return {
        "name": name,
        "overall": overall_platforms,
        "campaigns": campaigns,
    }


# ============================================================================
# LIVE BENCHMARKS  (window.BENCHMARKS_DATA.live)
#
# A normalized, filterable benchmark model, imported from the cleaned
# "FOS Social Benchmarks" workbook (Campaign Data + Platform Benchmarks tabs).
# One row per campaign per benchmark category. The three content dimensions FOS
# tracks live in the tags: Content Type (Video/Static), Franchise / IP vs
# "None (Custom)", and Distribution (Organic + Boosted vs Dark Only).
#
# Category benchmark = simple average of each campaign's per-platform ER across
# rows with Include = Yes. A blank platform is skipped, NOT counted as zero.
# "All Platforms" = average of each campaign's own overall (wrap-report) ER.
# ============================================================================

# Display order for the category tables (matches the workbook).
LIVE_CATEGORY_ORDER = [
    "Social Coverage Partner",
    "Video: Social-First IP or Franchise (Organic or Boosted)",
    "Static: Social-First IP or Franchise (Organic or Boosted)",
    "Video: Custom Social (Organic + Boosted)",
    "Static: Custom Social (Organic + Boosted)",
    "Video: Custom Social (Dark Only)",
    "Static: Custom Social (Dark Only)",
    "Brand Integration / Sponsored Content (Longform + Cutdowns)",
    "Custom Branded Content (Longform + Cutdowns, Organic + Boosted)",
    "Custom Branded Content (Longform + Cutdowns, Dark Only)",
    "Custom Social Video: FOS Tentpole Event",
    "FOS Event: Presenting Partner",
    "FOS Custom Event: Tastemaker or Future of Sports",
    "Organic Franchise (Non-Sponsored)",
]

# Platform columns, in display order. Keys match the Campaign Data headers.
LIVE_PLATFORM_COLS = [
    "Instagram", "Facebook", "X", "TikTok", "LinkedIn",
    "YouTube Shorts", "YouTube", "Meta (Dark)",
]


def _pct(s: str) -> float | None:
    """Decimal fraction string ('0.0306') → percentage points (3.06). Blank → None."""
    s = (s or "").strip().replace("%", "")
    if not s:
        return None
    try:
        return round(float(s) * 100, 2)
    except ValueError:
        return None


def _num(s: str) -> float | None:
    s = (s or "").strip().replace("$", "").replace(",", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _avg(vals: list[float]) -> float | None:
    vals = [v for v in vals if v is not None]
    return round(sum(vals) / len(vals), 2) if vals else None


def _category_table(campaigns: list[dict], names: list[str]) -> list[dict]:
    """Per-category simple-average benchmark across Include=Yes campaigns.

    Blank platform cells are excluded from that platform's average (not zeroed),
    exactly as the workbook's Read Me specifies.
    """
    out: list[dict] = []
    for name in names:
        members = [c for c in campaigns if c["category"] == name and c["include"]]
        platforms = {
            col: _avg([c["platforms"].get(col) for c in members])
            for col in LIVE_PLATFORM_COLS
        }
        platforms = {k: v for k, v in platforms.items() if v is not None}
        out.append({
            "name": name,
            "platforms": platforms,
            "all": _avg([c["all"] for c in members]),
            "n_campaigns": len(members),
        })
    return out


def _parse_platform_benchmarks(path: Path) -> list[dict]:
    """Platform Benchmarks tab → the Compare-To benchmark sets."""
    sets: list[dict] = []
    if not path.exists():
        return sets
    for row in csv.DictReader(path.open()):
        name = (row.get("Benchmark Set") or "").strip()
        if not name:
            continue
        platforms = {col: _pct(row.get(col, "")) for col in LIVE_PLATFORM_COLS}
        platforms = {k: v for k, v in platforms.items() if v is not None}
        yt = _pct(row.get("YouTube", ""))
        if yt is not None:
            platforms.setdefault("YouTube", yt)
        sets.append({
            "name": name,
            "platforms": platforms,
            "all": _pct(row.get("All Platforms", "")),
            "last_updated": (row.get("Last Updated") or "").strip(),
        })
    return sets


def compute_live_benchmarks(campaigns_csv: Path, platforms_csv: Path) -> dict[str, Any]:
    """Build the filterable live-benchmark model emitted as BENCHMARKS_DATA.live."""
    campaigns: list[dict] = []
    if campaigns_csv.exists():
        for row in csv.DictReader(campaigns_csv.open()):
            if not (row.get("Campaign") or "").strip():
                continue
            platforms = {col: _pct(row.get(col, "")) for col in LIVE_PLATFORM_COLS}
            campaigns.append({
                "campaign": (row.get("Campaign") or "").strip(),
                "client": (row.get("Client") or "").strip(),
                "category": (row.get("Benchmark Category") or "").strip(),
                "franchise": (row.get("Franchise / IP") or "").strip(),
                "content_type": (row.get("Content Type") or "").strip(),
                "distribution": (row.get("Distribution") or "").strip(),
                "tentpole_moment": (row.get("Tentpole Moment") or "").strip(),
                "tentpole": "Tentpole" if (row.get("Tentpole Moment") or "").strip() not in ("", "None") else "Non-Tentpole",
                "year": (row.get("Year") or "").strip(),
                "program": (row.get("Program") or "").strip(),
                "platforms": {k: v for k, v in platforms.items() if v is not None},
                "all": _pct(row.get("All Platforms", "")),
                "spend": _num(row.get("Spend ($)", "")),
                "include": (row.get("Include in Benchmarks") or "").strip().lower() == "yes",
                "tags_to_confirm": (row.get("Tags to Confirm") or "").strip(),
                "notes": (row.get("Notes") or "").strip(),
            })

    # Category benchmarks (unfiltered — the numbers to quote).
    present = [n for n in LIVE_CATEGORY_ORDER if any(c["category"] == n for c in campaigns)]
    extra = sorted({c["category"] for c in campaigns if c["category"] not in LIVE_CATEGORY_ORDER})
    cat_names = present + extra
    categories = _category_table(campaigns, cat_names)

    # "All sponsored campaigns" aggregate row.
    sponsored = [c for c in campaigns if c["program"].lower() == "sponsored" and c["include"]]
    all_sponsored = {
        "name": "All sponsored campaigns",
        "platforms": {k: v for k, v in (
            {col: _avg([c["platforms"].get(col) for c in sponsored]) for col in LIVE_PLATFORM_COLS}
        ).items() if v is not None},
        "all": _avg([c["all"] for c in sponsored]),
        "n_campaigns": len(sponsored),
    }

    def _distinct(key: str) -> list[str]:
        vals = {c[key] for c in campaigns if c[key] and c[key] != "None"}
        return sorted(vals)

    platform_sets = _parse_platform_benchmarks(platforms_csv)

    return {
        "campaigns": campaigns,
        "categories": categories,
        "all_sponsored": all_sponsored,
        "platform_sets": platform_sets,
        "category_order": cat_names,
        "filters": {
            "category": cat_names,
            "content_type": _distinct("content_type"),
            "distribution": _distinct("distribution"),
            "tentpole": ["Tentpole", "Non-Tentpole"],
            "year": _distinct("year"),
            "program": _distinct("program"),
            "client": _distinct("client"),
            "franchise": _distinct("franchise"),
            "platform": list(LIVE_PLATFORM_COLS),
        },
    }


# ============================================================================
# PAID-SOCIAL BENCHMARKS  (window.BENCHMARKS_DATA.paid)
#
# A second benchmark family for PAID distribution — BrandX (paid-performance),
# Dark Posts, and In-Feed + Boosted — reporting CPM / CTR / VCR / ER / Avg Watch.
# Unlike the ER benchmarks (simple average of campaign ERs), these are weighted
# by impressions: pooled CPM = Σspend / Σimpressions, pooled CTR/ER from raw
# clicks/engagements where available, and impression-weighted means for the
# per-row CTR / VCR / Avg Watch that the dark/in-feed exports carry.
# ============================================================================

def _ratio(num: float, den: float) -> float | None:
    return round(num / den * 100, 3) if den else None


def _wavg_pct(rows: list[dict], key: str) -> float | None:
    """Impression-weighted mean of a per-row ratio, as percentage points."""
    num = den = 0.0
    for r in rows:
        x, im = r.get(key), r.get("impressions")
        if x is None or not im:
            continue
        num += x * im
        den += im
    return round(num / den * 100, 3) if den else None


def _paid_metrics(rows: list[dict], *, kind: str) -> dict:
    """Weighted metrics for a set of paid rows. kind: 'brandx' or 'dist'."""
    spend = sum(r["spend"] or 0 for r in rows)
    impr = sum(r["impressions"] or 0 for r in rows)
    out = {
        "campaigns": len(rows),
        "spend": round(spend, 2),
        "impressions": int(impr),
        "cpm": round(spend / impr * 1000, 3) if impr else None,
    }
    if kind == "brandx":
        clicks = sum(r.get("clicks") or 0 for r in rows)
        eng = sum(r.get("engagements") or 0 for r in rows)
        out["ctr"] = _ratio(clicks, impr)
        out["er"] = _ratio(eng, impr)
        out["cpc"] = round(spend / clicks, 3) if clicks else None
    else:
        # Only the impression-weighted metrics that reconcile with the team's
        # summary doc (CPM/CTR/VCR). Avg Watch is computed by a different method
        # in the source workbook, so it's intentionally omitted here rather than
        # shown as a figure that disagrees with the doc.
        out["ctr"] = _wavg_pct(rows, "ctr")
        out["vcr"] = _wavg_pct(rows, "vcr")
    return out


def _group(rows: list[dict], key: str, *, kind: str) -> list[dict]:
    order: list[str] = []
    buckets: dict[str, list[dict]] = {}
    for r in rows:
        k = r.get(key) or "—"
        if k not in buckets:
            buckets[k] = []
            order.append(k)
        buckets[k].append(r)
    return [dict(name=k, **_paid_metrics(buckets[k], kind=kind)) for k in order]


def compute_paid_benchmarks(brandx_csv: Path, dist_csv: Path) -> dict[str, Any]:
    """Build the paid-social benchmark model emitted as BENCHMARKS_DATA.paid."""
    def f(s):
        return _num(s)

    brandx: list[dict] = []
    if brandx_csv.exists():
        for row in csv.DictReader(brandx_csv.open()):
            if not (row.get("Campaign") or "").strip():
                continue
            brandx.append({
                "campaign": (row.get("Campaign") or "").strip(),
                "category": (row.get("Category") or "").strip(),
                "objective": (row.get("Objective") or "").strip(),
                "spend": f(row.get("Spend", "")), "impressions": f(row.get("Impressions", "")),
                "clicks": f(row.get("Clicks", "")), "engagements": f(row.get("Engagements", "")),
            })

    dist: list[dict] = []
    if dist_csv.exists():
        for row in csv.DictReader(dist_csv.open()):
            if not (row.get("Campaign") or "").strip():
                continue
            dist.append({
                "campaign": (row.get("Campaign") or "").strip(),
                "category": (row.get("Category") or "").strip(),
                "platform": (row.get("Platform") or "").strip(),
                "objective": (row.get("Objective") or "").strip(),
                "correspondent": (row.get("Correspondent") or "").strip(),
                "distribution": (row.get("Distribution") or "").strip(),
                "spend": f(row.get("Spend", "")), "impressions": f(row.get("Impressions", "")),
                "ctr": f(row.get("CTR", "")), "vcr": f(row.get("VCR", "")),
                "avg_watch": f(row.get("Avg Watch (s)", "")), "engagements": f(row.get("Engagements", "")),
            })

    distributions = []
    for dname in ["Dark Only", "In-Feed + Boosted"]:
        rows = [r for r in dist if r["distribution"] == dname]
        if not rows:
            continue
        distributions.append({
            "name": dname,
            "overall": _paid_metrics(rows, kind="dist"),
            "by_category": _group(rows, "category", kind="dist"),
            "by_platform": _group(rows, "platform", kind="dist"),
        })

    return {
        "brandx": {
            "overall": _paid_metrics(brandx, kind="brandx") if brandx else None,
            "by_objective": _group(brandx, "objective", kind="brandx"),
            "by_category": _group(brandx, "category", kind="brandx"),
        } if brandx else None,
        "distributions": distributions,
    }


if __name__ == "__main__":
    import json
    from pathlib import Path
    p = Path(__file__).resolve().parents[2] / "config" / "social_benchmarks.csv"
    data = parse_benchmarks_csv(p)
    print(f"Last updated: {data['last_updated']}")
    print(f"Platform summary rows: {len(data['platform_summary'])}")
    print(f"Categories: {len(data['categories'])}")
    for cat in data["categories"]:
        print(f"  {cat['name'][:50]:52} overall={cat['overall']}  campaigns={len(cat['campaigns'])}")
