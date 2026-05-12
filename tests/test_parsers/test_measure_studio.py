"""MS parser tests against real fixture exports."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.parsers import Boosting, ParseResult, Platform, Source
from app.parsers.measure_studio import parse

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture()
def adp_cutdown_result() -> ParseResult:
    return parse(str(FIXTURES / "adp_cutdown_ms.csv"))


@pytest.fixture()
def adp_full_episode_result() -> ParseResult:
    return parse(str(FIXTURES / "adp_full_episode_ms.csv"))


@pytest.fixture()
def portfolio_players_result() -> ParseResult:
    return parse(str(FIXTURES / "portfolio_players_ms.csv"))


def test_adp_cutdown_parses(adp_cutdown_result):
    assert adp_cutdown_result.ok, f"errors: {adp_cutdown_result.errors}"
    assert adp_cutdown_result.row_count > 0


def test_adp_full_episode_parses(adp_full_episode_result):
    assert adp_full_episode_result.ok
    assert adp_full_episode_result.row_count > 0


def test_portfolio_players_parses(portfolio_players_result):
    assert portfolio_players_result.ok
    assert portfolio_players_result.row_count > 0


def test_detected_source(adp_cutdown_result):
    assert adp_cutdown_result.detected_source is Source.MEASURE_STUDIO


def test_adp_cutdown_multi_platform(adp_cutdown_result):
    platforms = adp_cutdown_result.platforms()
    assert Platform.UNKNOWN not in platforms
    assert len(platforms) >= 2


def test_no_unknown_platforms(adp_cutdown_result, adp_full_episode_result, portfolio_players_result):
    for r in (adp_cutdown_result, adp_full_episode_result, portfolio_players_result):
        for post in r.rows:
            assert post.platform is not Platform.UNKNOWN


def test_adp_cutdown_post_groups(adp_cutdown_result):
    groups = adp_cutdown_result.post_groups()
    assert groups
    combined = " | ".join(groups).lower()
    assert any(token in combined for token in ("future of sports", "cutdown", "adp"))


def test_portfolio_players_post_groups_field(portfolio_players_result):
    """post_groups is always a list, even for the simple summary export."""
    for p in portfolio_players_result.rows:
        assert isinstance(p.post_groups, list)


def test_identity_fields(adp_cutdown_result):
    for post in adp_cutdown_result.rows:
        assert post.source is Source.MEASURE_STUDIO
        assert post.platform is not Platform.UNKNOWN
        assert post.post_id_native


def test_engagement_metrics(adp_cutdown_result):
    with_metrics = [
        p for p in adp_cutdown_result.rows
        if any([p.views_total is not None, p.impressions_total is not None,
                p.engagements_total is not None, p.reach_total is not None])
    ]
    assert len(with_metrics) >= len(adp_cutdown_result.rows) * 0.5


def test_boosting_state(adp_cutdown_result):
    states = {p.boosting for p in adp_cutdown_result.rows}
    assert Boosting.ORGANIC in states or Boosting.BOOSTED in states


def test_timestamps(adp_cutdown_result):
    with_ts = [p for p in adp_cutdown_result.rows if p.posted_at is not None]
    assert len(with_ts) > 0


def test_missing_columns_error():
    fake_csv = b"\n".join([b"meta1,x"] * 7) + b"\nA,B,C\n1,2,3\n"
    result = parse(fake_csv)
    assert not result.ok
    assert any("required columns" in e.lower() for e in result.errors)


def test_empty_file_error():
    assert not parse(b"").ok


# ============================================================
# Regression: organic_only_for must reduce *_total to organic share
# ============================================================
# Why this matters: when we combine an MS export with a dedicated paid source
# (X Ads, Google Ads YT), MS '*_Total' columns are organic+paid and the paid
# portion would be counted twice — once by MS, again by the dedicated source.
# This test guards against that regression. Real example: E*TRADE Repole X
# posts where MS shows X Impressions - Total = 103,644, Organic = 11,878,
# Paid = 91,766. After organic_only_for={X}, impressions_total must equal
# 11,878 (organic), NOT 103,644.

def test_organic_only_for_x_reduces_totals_to_organic_share():
    """X posts under organic_only_for={Platform.X} must drop paid from totals."""
    result_default = parse(str(FIXTURES / "portfolio_players_ms.csv"))
    result_org_only = parse(
        str(FIXTURES / "portfolio_players_ms.csv"),
        organic_only_for={Platform.X},
    )

    # Find the same X post in both parses (deterministic via post_id_native)
    def x_posts_with_paid(r):
        return [
            p for p in r.rows
            if p.platform is Platform.X
            and p.impressions_paid is not None
            and p.impressions_paid > 0
        ]

    default_paid_posts = {p.post_id_native: p for p in x_posts_with_paid(result_default)}
    assert default_paid_posts, "fixture should have at least one X paid post"

    # In the organic-only result, find the same posts and verify totals dropped
    for org_post in result_org_only.rows:
        if org_post.platform is not Platform.X:
            continue
        if org_post.post_id_native not in default_paid_posts:
            continue
        default_post = default_paid_posts[org_post.post_id_native]
        paid_share = default_post.impressions_paid or 0
        if paid_share == 0:
            continue
        # The organic-only version must NOT include the paid portion
        assert (org_post.impressions_total or 0) < (default_post.impressions_total or 0), (
            f"organic_only_for didn't reduce impressions_total for X post "
            f"{org_post.post_id_native!r}: "
            f"default={default_post.impressions_total}, "
            f"organic_only={org_post.impressions_total}"
        )
        # Paid fields must be zeroed
        assert org_post.impressions_paid is None
        assert org_post.ad_spend is None


def test_organic_only_for_x_strips_paid_from_ms_totals():
    """After organic_only_for={Platform.X}, the sum of MS X impressions_total
    must equal the sum of MS X organic impressions — meaning all MS-reported
    paid impressions have been removed. This is THE invariant that prevents
    double-counting with the X Ads file."""
    ms_org_only = parse(
        str(FIXTURES / "portfolio_players_ms.csv"),
        organic_only_for={Platform.X},
    )
    ms_default = parse(str(FIXTURES / "portfolio_players_ms.csv"))

    org_only_x_total = sum(
        p.impressions_total or 0
        for p in ms_org_only.rows
        if p.platform is Platform.X
    )
    default_x_organic = sum(
        p.impressions_organic or 0
        for p in ms_default.rows
        if p.platform is Platform.X
    )
    default_x_paid = sum(
        p.impressions_paid or 0
        for p in ms_default.rows
        if p.platform is Platform.X
    )

    # Critical: the organic_only totals must match the organic share — they
    # must NOT include any of the paid share that's already captured by X Ads.
    assert org_only_x_total == default_x_organic, (
        f"organic_only_for didn't fully strip paid from totals. "
        f"organic-only total: {org_only_x_total:,}, "
        f"sum of organic: {default_x_organic:,}, "
        f"sum of paid (should have been removed): {default_x_paid:,}."
    )
