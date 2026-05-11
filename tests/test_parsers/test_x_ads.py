"""X Ads parser tests."""

from __future__ import annotations

from pathlib import Path

from app.parsers import Boosting, Platform, Source
from app.parsers.x_ads import parse

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_adp_native_x_ads_parses():
    """ADP X Ads CSV — native X Ads Manager export shape."""
    result = parse(str(FIXTURES / "adp_cutdown_x_ads.csv"))
    assert result.ok
    assert result.row_count > 0
    assert result.detected_source is Source.X_ADS


def test_native_x_rows_are_x_paid():
    result = parse(str(FIXTURES / "adp_cutdown_x_ads.csv"))
    for post in result.rows:
        assert post.platform is Platform.X
        assert post.boosting is Boosting.DARK


def test_pp_combined_x_ads_parses():
    """Portfolio Players X Ads — pre-combined (Sprout-style) export shape."""
    result = parse(str(FIXTURES / "portfolio_players_x_ads.csv"))
    assert result.ok
    assert result.row_count > 0


def test_x_ads_skips_empty_rows():
    """Rows with zero impressions and zero spend should be filtered out."""
    result = parse(str(FIXTURES / "adp_cutdown_x_ads.csv"))
    for post in result.rows:
        # At least one of these should be populated
        has_data = (post.impressions_paid or 0) > 0 or (post.ad_spend or 0) > 0
        assert has_data
