"""X Ads CSV parser.

Handles two real-world export shapes:
  - **Native X Ads export** (per-campaign, used for ADP):
      Time period, On/Off, Campaign ID, Campaign name, Objective, Delivery status,
      Campaign start, Campaign end, Impressions, Spend, Link clicks, CTR, CPM,
      Cost per link click, Engagements
  - **Pre-combined export** (multi-campaign rollup, used for Portfolio Players):
      Period, Campaign, Channel, Campaign Start, Campaign End, Spend, Impressions,
      Engagements, Link Clicks, CPM

Both are flattened into the same NormalizedPost rows (platform=X, boosting=dark).
"""

from __future__ import annotations

import io
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


def parse(file: IO[bytes] | str | bytes) -> ParseResult:
    df = _read_csv(file)
    if df is None or df.empty:
        return ParseResult(rows=[], detected_source=Source.X_ADS, errors=["Could not parse X Ads CSV"])

    cols = set(df.columns)
    if "Campaign name" in cols and "Time period" in cols:
        rows = _parse_native(df)
    elif "Campaign" in cols and "Period" in cols:
        rows = _parse_combined(df)
    else:
        return ParseResult(rows=[], detected_source=Source.X_ADS,
                           errors=[f"Unknown X Ads export format. Got columns: {sorted(cols)[:10]}"])

    return ParseResult(rows=rows, detected_source=Source.X_ADS)


def _parse_native(df: pd.DataFrame) -> list[NormalizedPost]:
    """Native X Ads Manager CSV — one row per campaign."""
    rows: list[NormalizedPost] = []
    for raw in df.to_dict("records"):
        name = (raw.get("Campaign name") or "").strip()
        if not name:
            continue
        impr = _to_int(raw.get("Impressions"))
        spend = _to_float(raw.get("Spend"))
        if (impr is None or impr == 0) and (spend is None or spend == 0.0):
            continue

        rows.append(NormalizedPost(
            source=Source.X_ADS,
            platform=Platform.X,
            post_id_native=str(raw.get("Campaign ID") or name),
            post_title=name,
            post_format=PostFormat.OTHER,
            boosting=Boosting.DARK,
            impressions_paid=impr,
            impressions_total=impr,
            ad_spend=spend,
            cpm=_to_float(raw.get("CPM")),
            ctr=_to_float(raw.get("CTR")),
            engagements_paid=_to_int(raw.get("Engagements")),
            engagements_total=_to_int(raw.get("Engagements")),
            raw=raw,
        ))
    return rows


def _parse_combined(df: pd.DataFrame) -> list[NormalizedPost]:
    """Pre-combined / Sprout-style multi-period rollup."""
    rows: list[NormalizedPost] = []
    for raw in df.to_dict("records"):
        name = (raw.get("Campaign") or "").strip()
        channel = (raw.get("Channel") or "").strip().lower()
        if not name or (channel and channel != "x"):
            continue
        impr = _to_int(raw.get("Impressions"))
        spend = _to_float(raw.get("Spend"))
        if (impr is None or impr == 0) and (spend is None or spend == 0.0):
            continue

        rows.append(NormalizedPost(
            source=Source.X_ADS,
            platform=Platform.X,
            post_id_native=name,
            post_title=name,
            post_format=PostFormat.OTHER,
            boosting=Boosting.DARK,
            impressions_paid=impr,
            impressions_total=impr,
            ad_spend=spend,
            cpm=_to_float(raw.get("CPM")),
            engagements_paid=_to_int(raw.get("Engagements")),
            engagements_total=_to_int(raw.get("Engagements")),
            raw=raw,
        ))
    return rows


def _read_csv(file: IO[bytes] | str | bytes) -> pd.DataFrame | None:
    if isinstance(file, bytes):
        file = io.BytesIO(file)
    try:
        return pd.read_csv(file, dtype=str, keep_default_na=False, low_memory=False)
    except Exception:
        return None


def _to_int(value: Any) -> int | None:
    if value is None or value == "" or value in ("N/A", "-", "--"):
        return None
    try:
        return int(float(str(value).replace(",", "")))
    except (ValueError, TypeError):
        return None


def _to_float(value: Any) -> float | None:
    if value is None or value == "" or value in ("N/A", "-", "--"):
        return None
    try:
        return float(str(value).replace(",", "").replace("%", "").replace("$", ""))
    except (ValueError, TypeError):
        return None
