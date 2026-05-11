"""Google Ads — Ad-level report parser."""

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

METADATA_ROWS = 2


def parse(file: IO[bytes] | str | bytes) -> ParseResult:
    df = _read_csv(file)
    if df is None or df.empty:
        return ParseResult(rows=[], detected_source=Source.GOOGLE_ADS_AD,
                           errors=["Could not parse Google Ads ad report"])

    if "Ad name" not in df.columns and "Campaign" not in df.columns:
        return ParseResult(rows=[], detected_source=Source.GOOGLE_ADS_AD,
                           errors=[f"Expected 'Ad name' or 'Campaign' column. Got: {list(df.columns)[:10]}"])

    rows: list[NormalizedPost] = []
    for raw in df.to_dict("records"):
        ad_name = (raw.get("Ad name") or raw.get("Campaign") or "").strip()
        if not ad_name:
            continue

        cost = _to_float(raw.get("Cost"))
        impr = _to_int(raw.get("Impr."))
        if (cost is None or cost == 0.0) and (impr is None or impr == 0):
            continue

        name_lower = ad_name.lower()
        post_format = PostFormat.REELS_SHORTS if ("shorts" in name_lower or "cutdown" in name_lower) else PostFormat.FEED_VIDEO

        watch_time = _to_float(raw.get("Watch time"))
        rows.append(NormalizedPost(
            source=Source.GOOGLE_ADS_AD,
            platform=Platform.YOUTUBE,
            post_id_native=str(raw.get("Video ID") or ad_name),
            post_url=_str(raw.get("Final URL")),
            post_title=_str(raw.get("Headline")) or ad_name,
            post_description=_str(raw.get("Description 1")),
            post_format=post_format,
            boosting=Boosting.DARK,
            impressions_paid=impr,
            ad_spend=cost,
            cpm=_to_float(raw.get("Avg. CPM")),
            cpv=_to_float(raw.get("TrueView avg. CPV")),
            ctr=_to_percent(raw.get("Engagement rate")),
            views_paid=_to_int(raw.get("TrueView views") or raw.get("YouTube public views")),
            engagements_paid=_to_int(raw.get("Engagements")),
            watch_time_min=(watch_time / 60.0) if watch_time is not None else None,
            raw=raw,
        ))

    return ParseResult(rows=rows, detected_source=Source.GOOGLE_ADS_AD)


def _read_csv(file: IO[bytes] | str | bytes) -> pd.DataFrame | None:
    if isinstance(file, bytes):
        file = io.BytesIO(file)
    try:
        return pd.read_csv(file, skiprows=METADATA_ROWS, dtype=str, keep_default_na=False, low_memory=False)
    except Exception:
        return None


def _str(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s if s and s != "--" else None


def _to_int(value: Any) -> int | None:
    if value is None or value == "" or value == "--":
        return None
    try:
        return int(float(str(value).replace(",", "")))
    except (ValueError, TypeError):
        return None


def _to_float(value: Any) -> float | None:
    if value is None or value == "" or value == "--":
        return None
    try:
        return float(str(value).replace(",", "").replace("%", "").replace("$", ""))
    except (ValueError, TypeError):
        return None


def _to_percent(value: Any) -> float | None:
    f = _to_float(value)
    if f is None:
        return None
    return f / 100.0 if f > 1.0 else f
