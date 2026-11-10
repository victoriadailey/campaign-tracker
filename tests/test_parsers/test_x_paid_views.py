"""Paid X video views: read from the X Ads export, added on top of MS's (organic-only) views."""

from __future__ import annotations

from app.parsers import Boosting, NormalizedPost, Platform, Source
from app.parsers.x_ads import parse
from app.viewer.refresh import _merge_x_ads_spend_into_ms

TWEET = "2116636334555070822"

CSV = (
    "Time period,On/Off,Campaign ID,Campaign name,Post link,Impressions,Spend,Link clicks,"
    "Video starts,Video views 3s,Engagements\n"
    f"x,On,1,Paid A,https://x.com/FOS/status/{TWEET},100000,500,10,4000,9999,50\n"
    "x,On,2,Paid B (dark),,50000,300,5,,7777,20\n"
)


def test_parser_reads_video_starts_not_3s_views(tmp_path):
    f = tmp_path / "x.csv"
    f.write_text(CSV)
    rows = parse(str(f)).rows
    assert [r.views_paid for r in rows] == [4000, None]


def test_paid_views_added_to_ms_organic_views():
    ms = NormalizedPost(
        source=Source.MEASURE_STUDIO, platform=Platform.X, post_id_native=TWEET,
        boosting=Boosting.BOOSTED, impressions_total=9000,
        views_total=1200, views_organic=1200, raw={"stats": {}},
    )
    xa = NormalizedPost(
        source=Source.X_ADS, platform=Platform.X, post_id_native="1",
        impressions_paid=100000, impressions_total=100000, views_paid=4000,
        ad_spend=500, raw={"_tweet_id": TWEET},
    )
    out = _merge_x_ads_spend_into_ms([ms, xa])
    assert len(out) == 1
    assert out[0].views_paid == 4000
    assert out[0].views_organic == 1200
    assert out[0].views_total == 5200


def test_paid_views_when_ms_has_no_views():
    ms = NormalizedPost(
        source=Source.MEASURE_STUDIO, platform=Platform.X, post_id_native=TWEET,
        boosting=Boosting.ORGANIC, impressions_total=9000, raw={"stats": {}},
    )
    xa = NormalizedPost(
        source=Source.X_ADS, platform=Platform.X, post_id_native="1",
        impressions_paid=100000, impressions_total=100000, views_paid=4000,
        raw={"_tweet_id": TWEET},
    )
    assert _merge_x_ads_spend_into_ms([ms, xa])[0].views_total == 4000


def test_engagements_net_of_3s_views_in_new_format(tmp_path):
    f = tmp_path / "x.csv"
    f.write_text(CSV)
    a, b = parse(str(f)).rows
    # Paid A: 50 engagements, 9,999 3s views -> floored at 0; Paid B: 20 - 7,777 -> 0
    assert a.engagements_paid == 0 and a.engagements_total == 0
    assert b.engagements_paid == 0


def test_engagements_net_subtracts_3s_views(tmp_path):
    f = tmp_path / "x.csv"
    f.write_text(
        "Time period,On/Off,Campaign ID,Campaign name,Impressions,Spend,Link clicks,"
        "Video starts,Video views 3s,Engagements\n"
        "x,On,1,Paid A,100000,500,10,4000,3000,3500\n"
    )
    (row,) = parse(str(f)).rows
    assert row.engagements_paid == 500 and row.engagements_total == 500
    assert row.views_paid == 4000


def test_old_format_engagements_untouched(tmp_path):
    f = tmp_path / "x.csv"
    f.write_text(
        "Time period,On/Off,Campaign ID,Campaign name,Impressions,Spend,Link clicks,"
        "Video views 3s,Engagements\n"
        "x,On,1,Paid A,100000,500,10,3000,1384\n"
    )
    (row,) = parse(str(f)).rows
    assert row.engagements_paid == 1384
    assert row.views_paid is None
