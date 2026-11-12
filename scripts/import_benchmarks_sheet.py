"""Rebuild config/benchmarks_campaigns.csv from the "Pulse Benchmarks - Campaign
Review" Google Sheet (tabs: In-Feed, Dark, Organic Franchise).

The sheet is the source of truth for the campaign rows and their ER values.
Fields the sheet doesn't carry (Franchise / IP, Tentpole, Program, Meta (Dark),
Tags to Confirm, Original Location) are carried over from the existing CSV row
for the same campaign; new campaigns get sensible defaults.

Usage:
    python scripts/import_benchmarks_sheet.py INFEED.csv DARK.csv ORGANIC.csv
(each file = that tab exported via File > Download > CSV)
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TARGET = REPO / "config" / "benchmarks_campaigns.csv"

PLATFORMS = ["Instagram", "Facebook", "X", "TikTok", "LinkedIn",
             "YouTube Shorts", "YouTube"]
OUT_COLS = [
    "Campaign", "Client", "Benchmark Category", "Franchise / IP", "Content Type",
    "Distribution", "Tentpole?", "Tentpole Moment", "Year", "Program",
    *PLATFORMS, "Meta (Dark)", "All Platforms", "Spend ($)",
    "Include in Benchmarks", "Tags to Confirm", "Notes", "Original Location",
    "Group",
]


def _frac(s: str) -> str:
    """'2.26%' or '2.26' (percentage points) -> '0.0226'. Blank stays blank."""
    s = (s or "").strip().replace("%", "")
    if not s:
        return ""
    try:
        return repr(round(float(s) / 100, 6))
    except ValueError:
        return ""


def _money(s: str) -> str:
    s = (s or "").strip().replace("$", "").replace(",", "")
    try:
        return repr(float(s)) if s else ""
    except ValueError:
        return ""


def _is_dark(group: str, distribution: str, category: str) -> bool:
    blob = " ".join([group, distribution, category]).lower()
    return "dark" in blob or "paid only" in blob or "paid-only" in blob


def _norm_category(cat: str) -> str:
    cat = re.sub(r"\s+", " ", (cat or "").strip())
    cat = re.sub(r"(?i)\bdark only\b", "Dark Only", cat)
    return cat


def _norm_distribution(dist: str, dark: bool) -> str:
    d = (dist or "").strip().lower()
    if dark or d in ("paid only", "dark only", "dark"):
        return "Dark Only"
    if d.startswith("organic only") or d == "organic":
        return "Organic"
    return "Organic + Boosted" if "boost" in d else (dist or "").strip()


def main(infeed: str, dark: str, organic: str) -> None:
    old = list(csv.DictReader(TARGET.open())) if TARGET.exists() else []
    by_campaign: dict[str, dict] = {}
    by_key: dict[tuple, dict] = {}
    for r in old:
        by_campaign.setdefault(r["Campaign"].strip().lower(), r)
        by_key[(r["Campaign"].strip().lower(), r["Distribution"].strip())] = r

    out = []
    for path, default_group in ((infeed, "In-feed"), (dark, "Dark"), (organic, "In-feed")):
        for r in csv.DictReader(open(path, newline="")):
            name = (r.get("Campaign") or "").strip()
            if not name:
                continue
            is_dark = _is_dark(r.get("Group", ""), r.get("Distribution", ""), r.get("Category", ""))
            dist = _norm_distribution(r.get("Distribution", ""), is_dark)
            cat = _norm_category(r.get("Category", ""))
            exact = by_key.get((name.lower(), dist))
            prev = exact or by_campaign.get(name.lower()) or {}
            organic_tab = path == organic
            row = {
                "Campaign": name,
                "Client": (r.get("Client") or prev.get("Client") or "").strip(),
                "Benchmark Category": cat,
                "Franchise / IP": prev.get("Franchise / IP") or ("None (Alignment)" if cat == "Social Coverage Partner" else "None (Custom)"),
                "Content Type": (r.get("Content Type") or "").strip(),
                "Distribution": dist,
                "Tentpole?": prev.get("Tentpole?", ""),
                "Tentpole Moment": prev.get("Tentpole Moment", "None"),
                "Year": (r.get("Year") or "").strip(),
                "Program": "Organic" if organic_tab else (prev.get("Program") or "Sponsored"),
                # Only carry Meta (Dark) when the same campaign + distribution row existed;
                # never leak a dark row's value onto the campaign's in-feed row.
                "Meta (Dark)": (exact or {}).get("Meta (Dark)", ""),
                "All Platforms": _frac(r.get("All Platforms", "")),
                "Spend ($)": _money(r.get("Spend ($)", "")),
                "Include in Benchmarks": "Yes" if (r.get("Include in Benchmarks") or "").strip().lower() == "yes" else "No",
                "Tags to Confirm": prev.get("Tags to Confirm", ""),
                "Notes": (r.get("Notes") or "").strip(),
                "Original Location": prev.get("Original Location", ""),
                "Group": "Dark" if is_dark else "In-feed",
            }
            for p in PLATFORMS:
                row[p] = _frac(r.get(p, ""))
            out.append(row)

    with TARGET.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=OUT_COLS)
        w.writeheader()
        w.writerows(out)
    n_dark = sum(1 for r in out if r["Group"] == "Dark")
    print(f"wrote {len(out)} rows ({len(out) - n_dark} in-feed, {n_dark} dark) -> {TARGET}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
