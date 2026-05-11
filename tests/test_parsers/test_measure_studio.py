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


def test_portfolio_players_multi_group(portfolio_players_result):
    for p in portfolio_players_result.rows:
        assert isinstance(p.post_groups, list)
    assert any(p.post_groups for p in portfolio_players_result.rows)


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
