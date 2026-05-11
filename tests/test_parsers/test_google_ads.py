"""Google Ads parser tests against real fixture exports."""

from __future__ import annotations

from pathlib import Path

from app.parsers import Boosting, ParseResult, Platform, Source
from app.parsers.google_ads_campaign import parse as parse_campaign

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_adp_cutdown_gads_parses():
    result: ParseResult = parse_campaign(str(FIXTURES / "adp_cutdown_gads_campaign.csv"))
    assert result.ok, f"errors: {result.errors}"
    assert result.row_count > 0
    assert result.detected_source is Source.GOOGLE_ADS_CAMPAIGN


def test_gads_rows_youtube_paid():
    result = parse_campaign(str(FIXTURES / "adp_cutdown_gads_campaign.csv"))
    for post in result.rows:
        assert post.platform is Platform.YOUTUBE
        assert post.boosting is Boosting.DARK


def test_gads_metrics_populated():
    result = parse_campaign(str(FIXTURES / "adp_cutdown_gads_campaign.csv"))
    for post in result.rows:
        has_metric = any([
            post.impressions_paid is not None,
            post.ad_spend is not None,
            post.views_paid is not None,
        ])
        assert has_metric, f"No metrics on row: {post.post_title}"


def test_gads_title_is_campaign_name():
    result = parse_campaign(str(FIXTURES / "adp_cutdown_gads_campaign.csv"))
    titles = [p.post_title for p in result.rows]
    assert any("ADP" in t and "Future of Sports" in t for t in titles if t)
