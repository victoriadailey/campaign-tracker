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
