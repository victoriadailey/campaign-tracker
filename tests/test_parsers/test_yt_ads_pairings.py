"""Manual Google Ads -> YouTube pairings (campaign key yt_ads_pairings)."""

from __future__ import annotations

from app.parsers import Boosting, NormalizedPost, Platform, Source
from app.parsers.base import PostFormat
from app.viewer.refresh import _merge_youtube_paid_spend_into_ms


def _ms(vid: str, paid: int) -> NormalizedPost:
    return NormalizedPost(
        source=Source.MEASURE_STUDIO, platform=Platform.YOUTUBE, post_id_native=vid,
        post_format=PostFormat.REELS_SHORTS, boosting=Boosting.BOOSTED,
        impressions_paid=paid, impressions_total=paid, raw={"stats": {}},
    )


def _gads(name: str, impr: int, spend: float) -> NormalizedPost:
    return NormalizedPost(
        source=Source.GOOGLE_ADS_CAMPAIGN, platform=Platform.YOUTUBE, post_id_native=name,
        post_title=name, impressions_paid=impr, ad_spend=spend, raw={},
    )


def _posts():
    # Preston (no Google Ads row in the export window) would shift a rank pairing.
    return [
        _ms("PRESTON", 201_636), _ms("FARAH", 120_581), _ms("NIL", 80_057),
        _gads("Huntington Bank: FOSN Farah Interview (Shorts)", 120_581, 417.56),
        _gads("Huntington Bank: FOSN NIL (shorts)", 87_125, 192.88),
    ]


def test_manual_pairings_attach_spend_to_the_named_videos():
    out = _merge_youtube_paid_spend_into_ms(
        _posts(), pair_by_sort=True,
        manual_pairings={"FOSN NIL": "NIL", "FOSN Farah": "FARAH"},
    )
    by_id = {p.post_id_native: p for p in out}
    assert by_id["NIL"].ad_spend == 192.88 and by_id["NIL"].impressions_paid == 87_125
    assert by_id["FARAH"].ad_spend == 417.56
    assert not by_id["PRESTON"].ad_spend
    assert len(out) == 3   # both Google Ads rows folded in


def test_without_manual_pairings_rank_pairing_shifts():
    out = _merge_youtube_paid_spend_into_ms(_posts(), pair_by_sort=True)
    by_id = {p.post_id_native: p for p in out}
    # the failure mode the pairings fix: Preston takes Farah's row
    assert by_id["PRESTON"].ad_spend == 417.56
