"""TikTok Ads Manager export parser — placeholder.

Until we have a real TikTok export to align against, this parser accepts a
flexible schema and returns useful warnings if it can't find the columns it
needs. Once Victoria shares a sample export, refine REQUIRED_COLS and the
field-name lookups to match TikTok's actual column headers.

Expected eventual required columns (subject to confirmation):

    Campaign name      — partner/series/component/variant pattern (see naming
                         convention guidance in docs/OVERVIEW.md)
    Impressions        — paid impressions
    Video views        — paid views (TikTok usually reports both)
    Engagements        — likes + comments + shares (TikTok-defined)
    Cost (USD)         — total spend

Output post shape:
  • platform = TIKTOK
  • source = TIKTOK_ADS
  • boosting = DARK
  • impressions_paid, views_paid, engagements_paid, ad_spend
  • er = engagements / impressions (or use TikTok's reported rate if present)
"""

from __future__ import annotations

import io
import re
from typing import IO, Any

import pandas as pd

from app.parsers.base import (
    Boosting,
    NormalizedPost,
    ParseResult,
    Platform,
    PostFormat,
    Source,
)


# We try several candidate column names since TikTok's export varies.
# Once we lock in the real schema, replace this with a hard REQUIRED_COLS check.
CANDIDATE_COLS = {
    "name":        ["Campaign name", "Ad name", "Ad group name", "Name"],
    "impressions": ["Impressions", "Impr.", "Impressions (paid)"],
    "views":       ["Video views", "Views", "2-second video views"],
    "engagements": ["Engagements", "Total engagements", "Post engagements"],
    "spend":       ["Cost (USD)", "Cost", "Amount spent (USD)", "Spend"],
}


def parse(file: IO[bytes] | str | bytes) -> ParseResult:
    df = _read_csv(file)
    if df is None or df.empty:
        return ParseResult(
            rows=[],
            detected_source=Source.TIKTOK_ADS,
            warnings=["TikTok Ads export is empty or unreadable. (Parser is in placeholder mode — share a real export to finalize the schema.)"],
        )

    # Resolve each logical field to whichever column name actually exists.
    cols = {k: _resolve(df, candidates) for k, candidates in CANDIDATE_COLS.items()}
    missing = [k for k, c in cols.items() if c is None and k in ("name", "impressions", "spend")]
    if missing:
        return ParseResult(
            rows=[],
            detected_source=Source.TIKTOK_ADS,
            errors=[
                f"TikTok Ads export missing required field(s): {missing}. "
                f"Tried these column names: {[CANDIDATE_COLS[k] for k in missing]}. "
                f"Got columns: {list(df.columns)}"
            ],
        )

    rows: list[NormalizedPost] = []
    for raw in df.to_dict("records"):
        name = (raw.get(cols["name"]) or "").strip()
        if not name:
            continue
        # TikTok Ads exports append a summary row ("Total of N results") that
        # duplicates the sum of the real rows — skip it so it isn't counted.
        if re.match(r"^total of \d+ results?$", name, re.I):
            continue
        impressions = _to_int(raw.get(cols["impressions"]))
        views = _to_int(raw.get(cols["views"])) if cols["views"] else None
        engagements = _to_int(raw.get(cols["engagements"])) if cols["engagements"] else None
        spend = _to_float(raw.get(cols["spend"]))

        if not impressions and not engagements:
            continue

        er = None
        if engagements is not None and impressions:
            er = engagements / impressions

        rows.append(NormalizedPost(
            source=Source.TIKTOK_ADS,
            platform=Platform.TIKTOK,
            post_id_native=name,
            post_title=name,
            post_format=PostFormat.REELS_SHORTS,  # TikTok is vertical short-form
            boosting=Boosting.DARK,
            impressions_paid=impressions,
            impressions_total=impressions,
            views_paid=views or impressions,
            engagements_paid=engagements,
            engagements_total=engagements,
            ad_spend=spend,
            er=er,
            raw=raw,
        ))

    return ParseResult(rows=rows, detected_source=Source.TIKTOK_ADS)


def _resolve(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Return the first candidate column name that exists in df, or None."""
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _read_csv(file: IO[bytes] | str | bytes) -> pd.DataFrame | None:
    # Shared reader also handles exports saved as Excel (.xlsx) but uploaded
    # with a .csv name — a common Ads Manager mistake.
    from app.parsers.base import read_ads_table
    return read_ads_table(file)


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    s = str(value).strip()
    if s in ("", "--", " --"):
        return None
    try:
        return int(float(s.replace(",", "")))
    except (ValueError, TypeError):
        return None


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    s = str(value).strip()
    if s in ("", "--", " --"):
        return None
    try:
        return float(s.replace(",", "").replace("$", ""))
    except (ValueError, TypeError):
        return None
