"""Shared types every parser produces.

All parsers must return a `ParseResult`. The upload UI shows warnings/errors,
the commit step writes `rows` to Firestore + BigQuery, and `suggested_campaign_ids`
auto-selects which FOS campaign(s) the upload belongs to.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class Source(str, Enum):
    MEASURE_STUDIO = "measure_studio"
    GOOGLE_ADS_AD = "google_ads_ad"
    GOOGLE_ADS_CAMPAIGN = "google_ads_campaign"
    YOUTUBE_PAID = "youtube_paid"           # alias for google_ads_campaign when used as YT paid source
    META_ADS = "meta_ads"
    TIKTOK_ADS = "tiktok_ads"
    X_ADS = "x_ads"
    LINKEDIN_ADS = "linkedin_ads"           # paid LinkedIn (Campaign Manager export)
    NATIVE_LINKEDIN = "native_linkedin"
    NATIVE_INSTAGRAM = "native_instagram"
    NATIVE_FACEBOOK = "native_facebook"
    NATIVE_TIKTOK = "native_tiktok"
    NATIVE_X = "native_x"


class Platform(str, Enum):
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    X = "x"
    LINKEDIN = "linkedin"
    SNAPCHAT = "snapchat"
    UNKNOWN = "unknown"


class PostFormat(str, Enum):
    REELS_SHORTS = "reels_shorts"
    FEED_VIDEO = "feed_video"
    YOUTUBE_LONG = "youtube_long"
    STATIC = "static"
    STORY = "story"
    TEXT = "text"
    OTHER = "other"


class Boosting(str, Enum):
    ORGANIC = "organic"
    BOOSTED = "boosted"
    DARK = "dark"
    UNKNOWN = "unknown"


@dataclass
class NormalizedPost:
    """One (post, platform) row, platform-agnostic. The unit BigQuery stores."""

    source: Source
    platform: Platform
    post_id_native: str | None = None
    internal_reference_id: str | None = None
    post_url: str | None = None

    account_name: str | None = None
    account_handle: str | None = None
    post_title: str | None = None
    post_description: str | None = None
    posted_at: datetime | None = None
    duration_sec: float | None = None

    post_format: PostFormat = PostFormat.OTHER
    boosting: Boosting = Boosting.UNKNOWN
    post_groups: list[str] = field(default_factory=list)

    views_total: int | None = None
    views_organic: int | None = None
    views_paid: int | None = None
    impressions_total: int | None = None
    impressions_organic: int | None = None
    impressions_paid: int | None = None
    reach_total: int | None = None
    reach_organic: int | None = None
    reach_paid: int | None = None
    engagements_total: int | None = None
    engagements_organic: int | None = None
    engagements_paid: int | None = None
    er: float | None = None

    watch_time_min: float | None = None
    avg_watch_time_sec: float | None = None

    ad_spend: float | None = None
    cpm: float | None = None
    cpv: float | None = None
    cpc: float | None = None
    ctr: float | None = None

    # Click + completion metrics — primary signals for paid-performance
    # (BrandX) campaigns. Click counts are paid-side only since organic
    # platforms either don't track them or aren't comparable.
    clicks_paid: int | None = None           # generic paid click count (all click types)
    link_clicks_paid: int | None = None      # link-out clicks specifically
    video_views_p100_paid: int | None = None # paid video views that watched to completion
    video_views_3s_paid: int | None = None   # paid 3-second video views (Meta's "view started" denominator for VCR)

    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParseResult:
    rows: list[NormalizedPost]
    detected_source: Source
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    suggested_campaign_ids: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def row_count(self) -> int:
        return len(self.rows)

    def platforms(self) -> set[Platform]:
        return {r.platform for r in self.rows}

    def post_groups(self) -> set[str]:
        groups: set[str] = set()
        for r in self.rows:
            groups.update(r.post_groups)
        return groups
