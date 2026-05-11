"""Google Ads — Campaign-level report parser."""

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
        return ParseResult(
            rows=[],
            detected_source=Source.GOOGLE_ADS_CAMPAIGN,
            errors=["Could not parse Google Ads campaign report"],
        )

    if "Campaign" not in df.columns:
        return ParseResult(
            rows=[],
            detected_source=Source.GOOGLE_ADS_CAMPAIGN,
            errors=[f"Expected 'Campaign' column. Got: {list(df.columns)}"],
        )

    rows: list[NormalizedPost] = []
    for raw in df.to_dict("records"):
        campaign_name = (raw.get("Campaign") or "").strip()
        if not campaign_name:
            continue

        watch_time = _to_float(raw.get("Watch time"))
        post_format = _detect_youtube_format(campaign_name)
        post = NormalizedPost(
            source=Source.GOOGLE_ADS_CAMPAIGN,
            platform=Platform.YOUTUBE,
            post_id_native=campaign_name,
            post_title=campaign_name,
            post_format=post_format,
            boosting=Boosting.DARK,
            impressions_paid=_to_int(raw.get("Impr.")),
            ad_spend=_to_float(raw.get("Cost")),
            cpm=_to_float(raw.get("Avg. CPM")),
            cpv=_to_float(raw.get("TrueView avg. CPV")),
            views_paid=_to_int(raw.get("TrueView views") or raw.get("YouTube public views")),
            engagements_paid=_to_int(raw.get("Engagements")),
            watch_time_min=(watch_time / 60.0) if watch_time is not None else None,
            raw=raw,
        )
        rows.append(post)

    return ParseResult(rows=rows, detected_source=Source.GOOGLE_ADS_CAMPAIGN)


def _detect_youtube_format(name: str) -> PostFormat:
    """Infer ad format from the Google Ads campaign name suffix."""
    lower = name.lower()
    if "shorts" in lower or "cutdown" in lower or "trailer" in lower:
        return PostFormat.REELS_SHORTS
    if "(in-feed)" in lower or " in-feed" in lower or "_in-feed" in lower:
        return PostFormat.YOUTUBE_LONG
    if "(pre-roll)" in lower or "(preroll)" in lower or "pre-roll" in lower:
        return PostFormat.YOUTUBE_LONG
    return PostFormat.YOUTUBE_LONG


def youtube_ad_subtype(name: str) -> str:
    """Returns 'in-feed', 'in-stream', 'shorts', or 'other' for downstream channel split."""
    lower = (name or "").lower()
    if "(in-feed)" in lower or "_in-feed" in lower or " in-feed" in lower:
        return "in-feed"
    if "(pre-roll)" in lower or "(preroll)" in lower or "pre-roll" in lower or "in-stream" in lower:
        return "in-stream"
    if "shorts" in lower or "(shorts)" in lower:
        return "shorts"
    if "cutdown" in lower:
        return "in-feed"  # cutdowns typically served as in-feed
    return "in-feed"


def _read_csv(file: IO[bytes] | str | bytes) -> pd.DataFrame | None:
    if isinstance(file, bytes):
        file = io.BytesIO(file)
    try:
        return pd.read_csv(
            file, skiprows=METADATA_ROWS, dtype=str, keep_default_na=False, low_memory=False
        )
    except Exception:
        return None


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
