"""X Ads → MS merge with MS's organic split (campaign key x_use_ms_organic_split)."""

from __future__ import annotations

from app.parsers import Boosting, NormalizedPost, Platform, Source
from app.viewer.refresh import _merge_x_ads_spend_into_ms

TWEET = "2116636334555070822"


def _ms_post() -> NormalizedPost:
    # MS's combined total (126,069) lags the X Ads export (169,614 paid).
    return NormalizedPost(
        source=Source.MEASURE_STUDIO, platform=Platform.X, post_id_native=TWEET,
        boosting=Boosting.BOOSTED,
        impressions_total=126069, engagements_total=38,
        raw={"stats": {
            "organic_impression_count": 7054, "promoted_impression_count": 119025,
            "organic_like_count": 1, "organic_retweet_count": 1,
            "organic_user_profile_clicks": 2,
            "promoted_like_count": 3, "promoted_user_profile_clicks": 31,
        }},
    )


def _xa_post() -> NormalizedPost:
    return NormalizedPost(
        source=Source.X_ADS, platform=Platform.X, post_id_native="42930845",
        impressions_paid=169614, impressions_total=169614,
        engagements_paid=161, engagements_total=161, ad_spend=366.94,
        raw={"_tweet_id": TWEET},
    )


def _merged(**kw) -> NormalizedPost:
    out = _merge_x_ads_spend_into_ms([_ms_post(), _xa_post()], **kw)
    assert len(out) == 1
    return out[0]


def test_ms_organic_split_adds_paid_on_top_of_organic():
    p = _merged(use_ms_organic_split=True)
    assert p.impressions_organic == 7054
    assert p.impressions_paid == 169614
    assert p.impressions_total == 7054 + 169614
    # organic engagements (1 like + 1 RT + 2 profile clicks) + X Ads paid
    assert p.engagements_organic == 4
    assert p.engagements_paid == 161
    assert p.engagements_total == 165
    assert p.ad_spend == 366.94


def test_default_routing_unchanged():
    p = _merged()
    assert p.impressions_organic == 0
    assert p.impressions_total == 126069
    assert p.engagements_total == 38
