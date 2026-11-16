"""Measure export (CSV) mode: renamed Instagram column + frozen-campaign carry-forward."""
import datetime as dt
import json
from dataclasses import dataclass, field
from types import SimpleNamespace

from app.parsers.measure_studio import parse
from app.viewer.refresh import _carry_forward_frozen

_META = "Period,Lifetime\nAccounts,x\nGroups,\"\"\nDates Published, - \nSorted by,x\nKeyword search,\"\"\n\n"


def test_instagram_views_new_column_name_is_read(tmp_path):
    hdr = ("Account Name,Post ID,Date Published,Time Published,Post Platform,Post Type,"
           "Post Title,Post Group(s),Organic / Boosted / Dark,Instagram Views - Instagram - Total,"
           "Instagram Reach - Total")
    row = "FOS,123,2026-11-01,10:00,Instagram,Reels,Hello,G,Boosted,1441,900"
    f = tmp_path / "ms.csv"
    f.write_text(_META + hdr + "\n" + row + "\n")
    res = parse(str(f))
    assert res.ok and len(res.rows) == 1
    assert res.rows[0].views_total == 1441


@dataclass
class _Camp:
    id: str
    partner: str
    channels: list = field(default_factory=list)


def _prev_js():
    camps = [
        {"id": "old", "partner": "Old", "channels": [{"name": "Instagram", "impressions": 100, "eng": 10, "views": 0, "organicImpressions": 0}]},
        {"id": "live", "partner": "Live", "channels": [{"name": "Instagram", "impressions": 50, "eng": 5, "views": 0, "organicImpressions": 0}]},
    ]
    chans = [{"name": "Instagram", "impressions": 150, "eng": 15, "er": 10.0, "cpm": 1.0, "views": 0,
              "organicImpressions": 0, "bench": {"er": 5.0}, "delta": 100.0}]
    return "\n".join([
        'window.LAST_REFRESHED = "2026-11-16T14:54:21Z";',
        "window.CAMPAIGNS = " + json.dumps(camps) + ";",
        "window.CHANNELS = " + json.dumps(chans) + ";",
        "window.EPISODES_BY_CAMPAIGN = " + json.dumps({"old": [{"id": "e1"}]}) + ";",
        "window.POSTS_BY_CAMPAIGN = " + json.dumps({"old": [{"id": "p1"}]}) + ";",
    ])


def test_frozen_campaign_keeps_last_published_blocks_and_totals():
    live = _Camp("live", "Live", channels=[])
    payload = SimpleNamespace(
        campaigns=[_Camp("old", "Old"), live], channels=[],
        episodes_by_campaign={}, posts_by_campaign={},
        portfolio_cpm_by_channel=[], portfolio_cpm_blend=0.0,
    )
    report = _carry_forward_frozen(payload, {"old"}, _prev_js(), dt.date(2026, 11, 17))
    old = payload.campaigns[0]
    assert old["partner"] == "Old" and old["measureFrozenAsOf"] == "2026-11-16"
    assert payload.episodes_by_campaign["old"] == [{"id": "e1"}]
    assert payload.posts_by_campaign["old"] == [{"id": "p1"}]
    assert report == [{"id": "old", "partner": "Old", "asOf": "2026-11-16"}]
    # The live campaign lost its 50 impressions / 5 eng this run (now has none), so the
    # portfolio total drops by exactly that, while the frozen campaign's 100 stays.
    ch = payload.channels[0]
    assert ch["impressions"] == 100 and ch["eng"] == 10 and ch["er"] == 10.0


def test_x_export_maps_views_to_delivery_and_video_views_to_plays(tmp_path):
    hdr = ("Account Name,Post ID,Date Published,Time Published,Post Platform,Post Type,"
           "Post Title,Post Group(s),Organic / Boosted / Dark,X Views - Total,X Views - Organic,"
           "X Views - Paid,X Total Engagements - Total")
    f = tmp_path / "ms.csv"
    f.write_text(_META + hdr + "\nFOS,9,2026-11-01,10:00,X,Videos,Hi,G,Dark,1000,100,900,5\n")
    p = parse(str(f)).rows[0]
    assert (p.impressions_total, p.impressions_organic, p.impressions_paid) == (1000, 100, 900)
    assert p.views_total is None and p.views_paid is None   # no "X Video Views" columns selected
    hdr2 = hdr + ",X Video Views - Total,X Video Views - Organic,X Video Views - Paid"
    f.write_text(_META + hdr2 + "\nFOS,9,2026-11-01,10:00,X,Videos,Hi,G,Dark,1000,100,900,5,300,30,270\n")
    p = parse(str(f)).rows[0]
    assert (p.views_total, p.views_organic, p.views_paid) == (300, 30, 270)


def test_x_organic_engagements_are_summed_from_organic_columns(tmp_path):
    hdr = ("Account Name,Post ID,Date Published,Time Published,Post Platform,Post Type,Post Title,"
           "Post Group(s),Organic / Boosted / Dark,X Views - Total,X Views - Organic,X Views - Paid,"
           "X Total Engagements - Total,X Likes - Organic,X Replies - Organic,X Retweets - Organic,"
           "X Profile Clicks - Organic,X Link Clicks - Organic")
    f = tmp_path / "ms.csv"
    f.write_text(_META + hdr + "\nFOS,9,2026-11-01,10:00,X,Videos,Hi,G,Dark,1000,100,900,50,5,1,2,3,4\n")
    assert parse(str(f)).rows[0].engagements_organic == 15


def test_meta_impressions_are_paid_plus_organic_views(tmp_path):
    hdr = ("Account Name,Post ID,Date Published,Time Published,Post Platform,Post Type,Post Title,"
           "Post Group(s),Organic / Boosted / Dark,Instagram Views - Organic,Instagram Impressions - Paid,"
           "Facebook Views - Organic,Facebook Impressions - Paid")
    f = tmp_path / "ms.csv"
    f.write_text(_META + hdr + "\nFOS,1,2026-11-01,10:00,Instagram,Reels,A,G,Boosted,43481,90608,,\n"
                 "FOS,2,2026-11-01,10:00,Facebook,Reels,B,G,Boosted,,,409,183589\n")
    ig, fb = parse(str(f)).rows
    assert ig.impressions_total == 134089 and fb.impressions_total == 183998
