"""X Ads CSV parser.

Handles three real-world export shapes:
  - **Native X Ads export — long form** (with Time period column, used for ADP):
      Time period, On/Off, Campaign ID, Campaign name, Objective, Delivery status,
      Campaign start, Campaign end, Impressions, Spend, Link clicks, CTR, CPM,
      Cost per link click, Engagements
  - **Native X Ads export — short form** (no Time period / Objective columns):
      Campaign ID, Campaign name, On/Off, Delivery status, Campaign start,
      Campaign end, Spend, Impressions, CPM, Link clicks, CTR, Cost per link click,
      Engagements
  - **Pre-combined export** (multi-campaign rollup, used for Portfolio Players):
      Period, Campaign, Channel, Campaign Start, Campaign End, Spend, Impressions,
      Engagements, Link Clicks, CPM

All flatten into the same NormalizedPost rows (platform=X, boosting=dark).

Paid video views: when the export carries a "Video starts" column, it is read
into `views_paid`. Measure Studio does not report promoted X views, so this is
the only source of paid X views. The "Video views 3s" column is not used as
views — video starts are the agreed paid-views metric for X.

Engagements: X Ads' "Engagements" includes 3-second video views. In exports
that carry a "Video starts" column (the new raw format) the 3s views are
subtracted so engagements are interactions only (floored at 0). Older exports
without "Video starts" were already adjusted by hand and are left untouched.
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

    # Ad-level exports (X Ads Manager "Ads" view) use "Ad name"/"Ad ID" instead
    # of "Campaign name"/"Campaign ID". Normalize so the native parser handles
    # both. Only rename when the campaign-level columns aren't already present.
    if "Campaign name" not in df.columns and "Ad name" in df.columns:
        df = df.rename(columns={"Ad name": "Campaign name", "Ad ID": "Campaign ID"})

    cols = set(df.columns)
    # The native Campaign Manager export always has "Campaign name" + "Campaign ID";
    # the combined Sprout-style export uses "Campaign" + "Period". The "Time period"
    # column exists only on the longer native variant.
    if "Campaign name" in cols and ("Campaign ID" in cols or "Time period" in cols):
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

        # If the export includes a tweet-URL column, extract the tweet ID —
        # downstream merge uses it for direct pairing with MS posts (no
        # impression-count guessing needed). X Ads exports use either
        # "Original Tweet URL" (one variant) or "Post Link" (another) — accept
        # whichever is present.
        # X exports vary the URL column casing ("Post Link" vs "Post link") and
        # sometimes use "Original Tweet URL" — accept any, case-insensitively.
        tweet_url = ""
        for _k, _v in raw.items():
            if str(_k).strip().lower() in ("original tweet url", "post link", "post url"):
                tweet_url = str(_v or "").strip()
                if tweet_url:
                    break
        tweet_id = _extract_tweet_id(tweet_url) if tweet_url else None

        # Link clicks drive Clicks/CTR/CPC. X's own "CTR" column is unreliable
        # (sometimes a fraction like 1.03e-05, sometimes a "0.03%" string), so
        # we don't trust it — populate link clicks and let the serializer derive
        # CTR (clicks÷impressions) and CPC (spend÷clicks) in consistent units.
        link_clicks = _to_int(raw.get("Link clicks"))

        rows.append(NormalizedPost(
            source=Source.X_ADS,
            platform=Platform.X,
            post_id_native=str(raw.get("Campaign ID") or name),
            post_title=name,
            post_url=tweet_url or None,
            post_format=PostFormat.OTHER,
            boosting=Boosting.DARK,
            impressions_paid=impr,
            impressions_total=impr,
            ad_spend=spend,
            cpm=_to_float(raw.get("CPM")),
            link_clicks_paid=link_clicks,
            engagements_paid=_net_engagements(raw),
            engagements_total=_net_engagements(raw),
            views_paid=_paid_video_views(raw),
            raw={**raw, "_tweet_id": tweet_id} if tweet_id else raw,
        ))
    return rows


def _paid_video_views(raw: dict) -> int | None:
    """Paid X video views = the export's "Video starts" column, or None when
    the export has no such column. "Video views 3s" is intentionally not used."""
    for k, v in raw.items():
        if str(k).strip().lower() == "video starts":
            return _to_int(v)
    return None


def _net_engagements(raw: dict) -> int | None:
    """Engagements with 3s video views removed (new-format exports only).

    Applies when the row has a "Video starts" column — the marker of the raw
    export format — and a "Video views 3s" value. Otherwise the Engagements
    column is returned as-is (older exports were adjusted manually)."""
    eng = _to_int(raw.get("Engagements"))
    if eng is None:
        return None
    keys = {str(k).strip().lower(): v for k, v in raw.items()}
    if "video starts" not in keys:
        return eng
    v3 = _to_int(keys.get("video views 3s"))
    return max(0, eng - v3) if v3 else eng


def _extract_tweet_id(url: str) -> str | None:
    """Pull the tweet ID out of an x.com / twitter.com URL.

    Handles: https://x.com/FOS/status/1234567890?s=20
             https://twitter.com/FOS/status/1234567890
    """
    if not url:
        return None
    import re
    m = re.search(r"/status/(\d+)", url)
    return m.group(1) if m else None


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
            engagements_paid=_net_engagements(raw),
            engagements_total=_net_engagements(raw),
            views_paid=_paid_video_views(raw),
            raw=raw,
        ))
    return rows


def _read_csv(file: IO[bytes] | str | bytes) -> pd.DataFrame | None:
    # Shared reader also handles exports saved as Excel (.xlsx) but uploaded
    # with a .csv name — a common Ads Manager mistake.
    from app.parsers.base import read_ads_table

    # Some X exports prepend a report-title row (e.g. "PFP X Ads Export 7:28")
    # ABOVE the real header, which would be read as the column names and drop
    # every post (E*TRADE would fall back to organic-only). If the first read
    # doesn't surface a recognizable header, retry skipping leading rows.
    _HEADER_TOKENS = {"Campaign name", "Campaign", "Ad name"}
    for skip in (0, 1, 2, 3):
        df = read_ads_table(file, skiprows=skip)
        if df is not None and (_HEADER_TOKENS & set(df.columns)):
            return df
    return read_ads_table(file)


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
