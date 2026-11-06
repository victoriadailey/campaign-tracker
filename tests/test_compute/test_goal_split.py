"""Full-episode vs cutdown classification, incl. the opt-in explicit rule
(goal_split_cutdowns: cutdown_platforms / cutdown_youtube_shorts)."""

from __future__ import annotations

from app.compute.rollup import _is_explicit_cutdown, _is_full_episode_content
from app.parsers import NormalizedPost, Platform, PostFormat, Source

RULE = {"label": "Cutdown", "cutdown_platforms": ["tiktok"], "cutdown_youtube_shorts": True}


def _post(platform, fmt=PostFormat.OTHER, title="") -> NormalizedPost:
    return NormalizedPost(source=Source.MEASURE_STUDIO, platform=platform,
                          post_format=fmt, post_title=title)


def test_explicit_rule_puts_short_and_tiktok_in_cutdown():
    assert _is_explicit_cutdown(_post(Platform.TIKTOK, PostFormat.REELS_SHORTS), RULE)
    assert _is_explicit_cutdown(_post(Platform.YOUTUBE, PostFormat.REELS_SHORTS), RULE)


def test_explicit_rule_keeps_fb_x_and_long_form_in_full_episode():
    # A Facebook Reel-format video and an X post promoting the episode are
    # Full Episode here even though they aren't titled "Full Episode".
    assert not _is_explicit_cutdown(_post(Platform.FACEBOOK, PostFormat.REELS_SHORTS, "NIL Toolkit"), RULE)
    assert not _is_explicit_cutdown(_post(Platform.X, PostFormat.TEXT), RULE)
    assert not _is_explicit_cutdown(_post(Platform.YOUTUBE, PostFormat.YOUTUBE_LONG), RULE)


def test_default_heuristic_unchanged_for_other_campaigns():
    assert not _is_full_episode_content(_post(Platform.FACEBOOK, PostFormat.REELS_SHORTS, "NIL Toolkit"))
    assert _is_full_episode_content(_post(Platform.YOUTUBE, PostFormat.YOUTUBE_LONG))
