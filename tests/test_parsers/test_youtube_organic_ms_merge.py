"""YouTube Studio export rows fold into their Measure Studio twin (by video ID)."""

from __future__ import annotations

from app.parsers import Boosting, NormalizedPost, Platform, PostFormat, Source
from app.viewer.refresh import _merge_youtube_organic_export_into_ms

VID = "DZdl2qc76Is"


def _ms(stats: dict, impr=None, views=830, eng=4) -> NormalizedPost:
    # Organic Shorts: the MS client's views-as-impressions floor sets impr=views.
    return NormalizedPost(
        source=Source.MEASURE_STUDIO, platform=Platform.YOUTUBE, post_id_native=VID,
        post_url=f"https://www.youtube.com/shorts/{VID}", post_format=PostFormat.REELS_SHORTS,
        boosting=Boosting.ORGANIC, impressions_total=impr if impr is not None else views,
        impressions_organic=impr if impr is not None else views, views_total=views,
        engagements_total=eng, raw={"stats": stats},
    )


def _export(impr=497, views=829, eng=4, vid=VID) -> NormalizedPost:
    return NormalizedPost(
        source=Source.YOUTUBE_ORGANIC, platform=Platform.YOUTUBE, post_id_native=vid,
        post_url=f"https://www.youtube.com/shorts/{vid}", boosting=Boosting.ORGANIC,
        impressions_total=impr, impressions_organic=impr, views_total=views,
        views_organic=views, engagements_total=eng, engagements_organic=eng,
    )


def test_export_thumbnail_impressions_fill_in_when_ms_has_none():
    out = _merge_youtube_organic_export_into_ms([_ms({"views": 830}), _export()])
    assert len(out) == 1 and out[0].source is Source.MEASURE_STUDIO
    assert out[0].impressions_total == 497      # export thumbnail impressions, not views
    assert out[0].views_total == 830            # MS stays the source for views
    assert out[0].engagements_total == 4


def test_ms_impressions_win_when_ms_reports_them():
    out = _merge_youtube_organic_export_into_ms(
        [_ms({"views": 830, "impressions": 1200}, impr=1200), _export()])
    assert len(out) == 1 and out[0].impressions_total == 1200


def test_export_row_without_ms_twin_is_kept():
    other = _export(vid="zzzzzzzzzzz")
    out = _merge_youtube_organic_export_into_ms([_ms({"views": 830}), other])
    assert other in out and len(out) == 2
