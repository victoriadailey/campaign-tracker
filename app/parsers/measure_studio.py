"""Measure Studio CSV parser. Wide table → long normalized rows."""

from __future__ import annotations

import io
from datetime import datetime
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

METADATA_ROWS = 7

PLATFORM_LABEL_MAP: dict[str, Platform] = {
    "Instagram": Platform.INSTAGRAM,
    "Facebook": Platform.FACEBOOK,
    "YouTube": Platform.YOUTUBE,
    "TikTok": Platform.TIKTOK,
    "X": Platform.X,
    "Twitter": Platform.X,
    "LinkedIn": Platform.LINKEDIN,
    "Snapchat": Platform.SNAPCHAT,
}

PLATFORM_METRIC_MAPS: dict[Platform, dict[str, str]] = {
    Platform.YOUTUBE: {
        "views_total": "YouTube Views - Total",
        "views_organic": "YouTube Views - Organic",
        "views_paid": "YouTube Views - Paid",
        "impressions_paid": "YouTube Impressions - Paid",
        "engagements_total": "YouTube Total Engagements - Total",
        "engagements_organic": "YouTube Total Engagements - Organic",
        "engagements_paid": "YouTube Total Engagements - Paid",
        "er": "YouTube Engagement Rate - Total",
        "ad_spend": "YouTube Ad Spend - Paid",
        "cpm": "YouTube CPM - Paid",
        "cpv": "YouTube CPV - Paid",
        "cpc": "YouTube CPC - Paid",
        "ctr": "YouTube CTR - Paid",
        "watch_time_min": "YouTube Watch Time (minutes) - Total",
        "avg_watch_time_sec": "YouTube Average Watch Time - Total",
    },
    Platform.INSTAGRAM: {
        "views_total": "Instagram Views - Total",
        "views_organic": "Instagram Views - Organic",
        "views_paid": "Instagram Video Views - 3s - Paid",
        "reach_total": "Instagram Reach - Total",
        "reach_organic": "Instagram Reach - Organic",
        "reach_paid": "Instagram Reach - Paid",
        "impressions_paid": "Instagram Impressions - Paid",
        "engagements_total": "Instagram Total Engagements - Total",
        "engagements_organic": "Instagram Total Engagements - Organic",
        "er": "Instagram Engagement Rate - Views - Total",
        "ad_spend": "Instagram Ad Spend - Paid",
        "cpm": "Instagram CPM - Paid",
        "cpc": "Instagram CPC - Paid",
        "ctr": "Instagram CTR - Paid",
    },
    Platform.FACEBOOK: {
        "views_total": "Facebook Views - Total",
        "views_organic": "Facebook Views - Organic",
        "views_paid": "Facebook Views - Paid",
        "reach_total": "Facebook Reach - Total",
        "reach_organic": "Facebook Reach - Organic",
        "reach_paid": "Facebook Reach - Paid",
        "engagements_total": "Facebook Total Engagements - Total",
        "er": "Facebook Engagement Rate - Views - Total",
        "ad_spend": "Facebook Ad Spend - Paid",
        "cpm": "Facebook CPM - Paid",
        "cpc": "Facebook CPC - Paid",
        "ctr": "Facebook CTR - Paid",
        "watch_time_min": "Facebook Watch Time (minutes) - Total",
        "avg_watch_time_sec": "Facebook Average Watch Time - Total",
    },
    Platform.X: {
        "views_total": "X Views - Total",
        "views_organic": "X Views - Organic",
        "views_paid": "X Views - Paid",
        "impressions_total": "X Impressions - Total",
        "impressions_organic": "X Impressions - Organic",
        "impressions_paid": "X Impressions - Paid",
        "engagements_total": "X Total Engagements - Total",
        "er": "X Engagement Rate - Total",
    },
    Platform.TIKTOK: {
        "views_total": "TikTok Views - Total",
        "views_organic": "TikTok Views - Organic",
        "views_paid": "TikTok Views - Paid",
        "reach_total": "TikTok Reach - Total",
        "impressions_paid": "TikTok Impressions - Paid",
        "engagements_total": "TikTok Total Engagements - Total",
        "engagements_organic": "TikTok Total Engagements - Organic",
        "engagements_paid": "TikTok Total Engagements - Paid",
        "er": "TikTok Engagement Rate - Total",
        "ad_spend": "TikTok Ad Spend - Paid",
        "cpm": "TikTok CPM - Paid",
        "cpc": "TikTok CPC - Paid",
        "ctr": "TikTok CTR - Paid",
        "watch_time_min": "TikTok Watch Time (minutes) - Total",
        "avg_watch_time_sec": "TikTok Average Watch Time - Total",
    },
    Platform.LINKEDIN: {
        "views_total": "LinkedIn Views - Total",
        "impressions_total": "LinkedIn Impressions - Total",
        "engagements_total": "LinkedIn Total Engagements - Total",
        "er": "LinkedIn Engagement Rate - Total",
    },
    Platform.SNAPCHAT: {
        "views_total": "Snapchat Publisher Views - Total",
        "engagements_total": "Snapchat Publisher Total Engagements - Total",
        "er": "Snapchat Publisher Engagement Rate - Total",
    },
}

BOOSTING_MAP: dict[str, Boosting] = {
    "Organic": Boosting.ORGANIC,
    "Boosted": Boosting.BOOSTED,
    "Dark": Boosting.DARK,
    "": Boosting.UNKNOWN,
}


def parse(file: IO[bytes] | str | bytes) -> ParseResult:
    warnings: list[str] = []
    errors: list[str] = []

    df = _read_csv(file)
    if df is None:
        return ParseResult(
            rows=[],
            detected_source=Source.MEASURE_STUDIO,
            errors=["Could not parse file as Measure Studio CSV"],
        )

    required_cols = {
        "Post Platform", "Post Type", "Post ID", "Date Published",
        "Time Published", "Post Group(s)", "Organic / Boosted / Dark",
    }
    missing = required_cols - set(df.columns)
    if missing:
        errors.append(f"Missing required columns: {sorted(missing)}")
        return ParseResult(rows=[], detected_source=Source.MEASURE_STUDIO, errors=errors)

    rows: list[NormalizedPost] = []
    skipped = 0
    for raw in df.to_dict("records"):
        label = (raw.get("Post Platform") or "").strip()
        platform = PLATFORM_LABEL_MAP.get(label, Platform.UNKNOWN)
        if platform is Platform.UNKNOWN:
            skipped += 1
            continue
        rows.append(_row_to_post(raw, platform))

    if skipped:
        warnings.append(f"Skipped {skipped} rows with unknown Post Platform")

    suggested = sorted({g for r in rows for g in r.post_groups})

    return ParseResult(
        rows=rows,
        detected_source=Source.MEASURE_STUDIO,
        warnings=warnings,
        errors=errors,
        suggested_campaign_ids=suggested,
    )


def _read_csv(file: IO[bytes] | str | bytes) -> pd.DataFrame | None:
    if isinstance(file, bytes):
        file = io.BytesIO(file)
    try:
        return pd.read_csv(
            file, skiprows=METADATA_ROWS, dtype=str, keep_default_na=False, low_memory=False
        )
    except (pd.errors.ParserError, ValueError, FileNotFoundError):
        return None


def _row_to_post(raw: dict[str, Any], platform: Platform) -> NormalizedPost:
    posted_at = _parse_timestamp(raw.get("Date Published"), raw.get("Time Published"))
    duration = _to_float(raw.get("Video Duration (seconds)"))
    post_groups = _parse_post_groups(raw.get("Post Group(s)"))
    boosting_label = (raw.get("Organic / Boosted / Dark") or "").strip()

    post = NormalizedPost(
        source=Source.MEASURE_STUDIO,
        platform=platform,
        post_id_native=_str(raw.get("Post ID")),
        internal_reference_id=_str(raw.get("Internal Reference ID")),
        post_url=_str(raw.get("Post URL")),
        account_name=_str(raw.get("Account Name")),
        account_handle=_str(raw.get("Account Handle")),
        post_title=_str(raw.get("Post Title")),
        post_description=_str(raw.get("Post Description")),
        posted_at=posted_at,
        duration_sec=duration,
        post_format=_classify_format(raw.get("Post Type"), duration, platform),
        boosting=BOOSTING_MAP.get(boosting_label, Boosting.UNKNOWN),
        post_groups=post_groups,
        raw=raw,
    )

    for field_name, col_name in PLATFORM_METRIC_MAPS.get(platform, {}).items():
        value = raw.get(col_name)
        if value is None or value == "":
            continue
        if field_name in {"er", "ad_spend", "cpm", "cpv", "cpc", "ctr",
                          "watch_time_min", "avg_watch_time_sec"}:
            setattr(post, field_name, _to_float(value))
        else:
            setattr(post, field_name, _to_int(value))

    return post


def _classify_format(post_type: str | None, duration_sec: float | None, platform: Platform) -> PostFormat:
    pt = (post_type or "").lower()
    if "reel" in pt or "short" in pt or "spotlight" in pt:
        return PostFormat.REELS_SHORTS
    if "story" in pt or "stories" in pt:
        return PostFormat.STORY
    if "photo" in pt or "carousel" in pt or "image" in pt:
        return PostFormat.STATIC
    if "text" in pt:
        return PostFormat.TEXT
    if "video" in pt:
        if platform is Platform.YOUTUBE:
            if duration_sec is not None and duration_sec >= 90:
                return PostFormat.YOUTUBE_LONG
            return PostFormat.REELS_SHORTS
        return PostFormat.FEED_VIDEO
    return PostFormat.OTHER


def _parse_post_groups(value: Any) -> list[str]:
    if not value:
        return []
    return [p.strip() for p in str(value).split(",") if p.strip()]


def _parse_timestamp(date_str: Any, time_str: Any) -> datetime | None:
    if not date_str:
        return None
    try:
        date_part = str(date_str).strip()
        time_part = (str(time_str).strip() if time_str else "00:00")
        if len(time_part) == 5:
            time_part += ":00"
        return datetime.fromisoformat(f"{date_part}T{time_part}")
    except (ValueError, TypeError):
        return None


def _str(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def _to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(str(value).replace(",", "")))
    except (ValueError, TypeError):
        return None


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", "").replace("%", ""))
    except (ValueError, TypeError):
        return None
