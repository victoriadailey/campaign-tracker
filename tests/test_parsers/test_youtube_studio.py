"""YouTube Studio organic export parser tests."""

from __future__ import annotations

from pathlib import Path

from app.parsers import Boosting, Platform, PostFormat, Source
from app.parsers.youtube_studio import parse

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_stifel_export_parses_one_organic_post_per_video():
    result = parse(str(FIXTURES / "stifel_fostonight_yt_organic.csv"))
    assert result.ok, f"errors: {result.errors}"
    assert result.detected_source is Source.YOUTUBE_ORGANIC
    # The leading "Total" row is skipped.
    assert result.row_count == 5
    for post in result.rows:
        assert post.platform is Platform.YOUTUBE
        assert post.boosting is Boosting.ORGANIC
        assert not post.ad_spend
        assert post.impressions_paid is None


def test_thumbnail_impressions_are_organic_impressions():
    result = parse(str(FIXTURES / "stifel_fostonight_yt_organic.csv"))
    by_id = {p.post_id_native: p for p in result.rows}
    vonn = by_id["DZdl2qc76Is"]
    assert vonn.impressions_total == 497
    assert vonn.impressions_organic == 497
    assert vonn.views_total == 829
    assert vonn.engagements_total == 4
    assert vonn.post_url == "https://www.youtube.com/watch?v=DZdl2qc76Is"
    assert vonn.posted_at.strftime("%Y-%m-%d") == "2026-10-09"
    assert vonn.post_format is PostFormat.YOUTUBE_LONG
    assert sum(p.impressions_total for p in result.rows) == 4168
    assert sum(p.views_total for p in result.rows) == 1390


def test_shorts_link_is_flagged_as_shorts():
    data = (
        "Content,Video title,Post Link,Video publish time,Engagements,Views,Thumbnail impressions\n"
        "abcDEFghiJK,A short,https://www.youtube.com/shorts/abcDEFghiJK,\"Oct 9, 2026\",3,\"1,200\",\"4,500\"\n"
    ).encode()
    result = parse(data)
    assert result.ok
    assert result.rows[0].post_format is PostFormat.REELS_SHORTS
    assert result.rows[0].views_total == 1200
    assert result.rows[0].impressions_total == 4500


def test_google_ads_export_is_rejected_with_a_clear_error():
    result = parse(str(FIXTURES / "heinz_stadiumeats_yt_paid.csv"))
    assert not result.ok
    assert result.row_count == 0
    assert "YouTube Studio" in result.errors[0]
