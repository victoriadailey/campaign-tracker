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


def parse(
    file: IO[bytes] | str | bytes,
    organic_only_for: set[Platform] | None = None,
) -> ParseResult:
    """Parse a Measure Studio CSV.

    Args:
        file: file path / bytes / file-like
        organic_only_for: if provided, paid metrics are zeroed out for these platforms.
            Used by the Portfolio Players pipeline where dedicated X Ads + YT Paid exports
            provide the authoritative paid numbers — we don't want to double-count MS.
    """
    warnings: list[str] = []
    errors: list[str] = []
    organic_only_for = organic_only_for or set()

    df = _read_csv(file)
    if df is None:
        return ParseResult(
            rows=[],
            detected_source=Source.MEASURE_STUDIO,
            errors=["Could not parse file as Measure Studio CSV"],
        )

    # MS exports come in two shapes:
    #   - Wide (default): per-platform metric columns + Post Group(s) + Time Published + Post ID
    #   - Simple summary: platform-agnostic Impressions/Reach/Views/Engagements columns
    # Both have "Post Platform", "Post Title", and "Organic / Boosted / Dark".
    is_wide = "Post Group(s)" in df.columns
    minimum_required = {"Post Platform", "Post Title", "Organic / Boosted / Dark", "Date Published"}
    missing = minimum_required - set(df.columns)
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
        post = _row_to_post(raw, platform) if is_wide else _row_to_post_simple(raw, platform)
        if platform in organic_only_for:
            # MS reports `*_total` as organic + paid combined. For platforms whose paid
            # data we get from a dedicated source (X Ads, Google Ads YT), we have to
            # also reduce `*_total` to the organic share — otherwise paid impressions
            # get counted twice (once in MS total, once in the dedicated source).
            if post.impressions_organic is not None:
                post.impressions_total = post.impressions_organic
            elif post.impressions_paid:
                # No explicit organic but paid is set — total - paid = organic share
                post.impressions_total = max(0, (post.impressions_total or 0) - post.impressions_paid)
            if post.views_organic is not None:
                post.views_total = post.views_organic
            elif post.views_paid:
                post.views_total = max(0, (post.views_total or 0) - post.views_paid)
            if post.reach_organic is not None:
                post.reach_total = post.reach_organic
            if post.engagements_organic is not None:
                post.engagements_total = post.engagements_organic
            elif post.engagements_paid:
                post.engagements_total = max(0, (post.engagements_total or 0) - post.engagements_paid)
            # Now zero out the paid fields — they'll be supplied by the dedicated source.
            post.views_paid = None
            post.impressions_paid = None
            post.reach_paid = None
            post.engagements_paid = None
            post.ad_spend = None
            post.cpm = None
            post.cpv = None
            post.cpc = None
        rows.append(post)

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


def _row_to_post_simple(raw: dict[str, Any], platform: Platform) -> NormalizedPost:
    """Parse a row from the SIMPLE MS export shape (no Post Group, no per-platform blocks).

    Columns: Account Name, Account Handle, Post URL, Post Title, Post Platform, Post Type,
             Organic / Boosted / Dark, Date Published, Impressions, Reach, Views, Engagements
    """
    posted_at = _parse_timestamp(raw.get("Date Published"), raw.get("Time Published"))
    duration = _to_float(raw.get("Video Duration (seconds)"))
    boosting_label = (raw.get("Organic / Boosted / Dark") or "").strip()
    title = _str(raw.get("Post Title")) or ""
    # Synthetic Post ID when missing (most simple exports drop it)
    synthetic_id = _str(raw.get("Post ID")) or f"{platform.value}:{_str(raw.get('Post URL')) or title[:60]}"

    impressions = _to_int(raw.get("Impressions"))
    reach = _to_int(raw.get("Reach"))
    views = _to_int(raw.get("Views"))
    engagements = _to_int(raw.get("Engagements"))

    boosting = BOOSTING_MAP.get(boosting_label, Boosting.UNKNOWN)

    # Split into organic vs paid based on boosting state. The simple export doesn't
    # break this out — we infer: organic posts contribute fully to organic columns,
    # boosted/dark contribute fully to paid columns. Not perfectly accurate for
    # boosted (which has BOTH), but the most reasonable default.
    is_organic = boosting is Boosting.ORGANIC
    is_paid = boosting in (Boosting.BOOSTED, Boosting.DARK)

    post = NormalizedPost(
        source=Source.MEASURE_STUDIO,
        platform=platform,
        post_id_native=synthetic_id,
        post_url=_str(raw.get("Post URL")),
        account_name=_str(raw.get("Account Name")),
        account_handle=_str(raw.get("Account Handle")),
        post_title=title,
        posted_at=posted_at,
        duration_sec=duration,
        post_format=_classify_format(raw.get("Post Type"), duration, platform),
        boosting=boosting,
        post_groups=[],  # not in this export — caller filters by file, not by group
        impressions_total=impressions,
        impressions_organic=impressions if is_organic else None,
        impressions_paid=impressions if is_paid else None,
        reach_total=reach,
        views_total=views,
        views_organic=views if is_organic else None,
        views_paid=views if is_paid else None,
        engagements_total=engagements,
        engagements_organic=engagements if is_organic else None,
        engagements_paid=engagements if is_paid else None,
        er=(engagements / impressions * 100) if engagements is not None and impressions else None,
        raw=raw,
    )
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
    """Parse to int; take abs() to normalize MS export bug.

    Measure Studio exports negative numbers in some YouTube columns (e.g.,
    'YouTube Total Engagements - Organic = -6325'). These are data export bugs,
    not real negative metrics. We flip all negatives to positives at parse time.
    Metric values are inherently non-negative — views, impressions, engagements,
    spend, etc. cannot meaningfully be negative.
    """
    if value is None or value == "":
        return None
    try:
        return abs(int(float(str(value).replace(",", ""))))
    except (ValueError, TypeError):
        return None


def _to_float(value: Any) -> float | None:
    """Parse to float; take abs() — see _to_int doc for rationale."""
    if value is None or value == "":
        return None
    try:
        return abs(float(str(value).replace(",", "").replace("%", "")))
    except (ValueError, TypeError):
        return None
