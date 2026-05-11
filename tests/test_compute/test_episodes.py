"""Episode attribution + rollup tests."""

from __future__ import annotations

from app.compute.episodes import EpisodeDef, attribute_posts_to_episodes, rollup_episode
from app.parsers.base import (
    Boosting,
    NormalizedPost,
    Platform,
    PostFormat,
    Source,
)


def _post(title: str, impr: int = 10_000, eng: int = 100, er: float = 1.0) -> NormalizedPost:
    return NormalizedPost(
        source=Source.MEASURE_STUDIO,
        platform=Platform.LINKEDIN,
        post_id_native=title[:20],
        post_title=title,
        post_format=PostFormat.STATIC,
        boosting=Boosting.ORGANIC,
        impressions_total=impr,
        views_total=impr,
        engagements_total=eng,
        er=er,
    )


def test_simple_match():
    """Posts with matching keyword land in the right episode."""
    eps = [
        EpisodeDef(id="ep1", n="Ep. 01", title="Repole", date="", match=["Repole"], exclude=[]),
        EpisodeDef(id="ep2", n="Ep. 02", title="Patricof", date="", match=["Patricof"], exclude=[]),
    ]
    posts = [
        _post("Mike Repole on sports ownership"),
        _post("Jon Patricof on Athletes Unlimited"),
        _post("Some other random post"),
    ]
    out = attribute_posts_to_episodes(posts, eps)
    assert len(out["ep1"]) == 1
    assert len(out["ep2"]) == 1


def test_exclude_rule_prevents_cross_attribution():
    """Repole post mentioning Cuban should stay with Repole, not get attributed to Cuban."""
    eps = [
        EpisodeDef(id="repole", n="01", title="Repole", date="", match=["Repole"], exclude=[]),
        EpisodeDef(id="cuban",  n="02", title="Cuban",  date="", match=["Cuban"],  exclude=["Repole"]),
    ]
    posts = [
        _post("Mike Repole and Mark Cuban talk sports ownership"),  # mentions both
        _post("Mark Cuban on owning the Mavs"),                       # Cuban only
    ]
    out = attribute_posts_to_episodes(posts, eps)
    # Repole post should land in Repole (exclude rule on Cuban kicks in)
    assert len(out["repole"]) == 1
    assert "Repole" in out["repole"][0].post_title
    # Cuban-only post lands in Cuban
    assert len(out["cuban"]) == 1
    assert "Mavs" in out["cuban"][0].post_title


def test_longest_match_wins():
    """When multiple episodes could match, the most-specific (longest match) wins."""
    eps = [
        EpisodeDef(id="generic", n="01", title="Sports", date="", match=["sports"], exclude=[]),
        EpisodeDef(id="specific", n="02", title="Women's Sports", date="", match=["women's sports"], exclude=[]),
    ]
    posts = [_post("Why women's sports have a higher ROI than men's sports")]
    out = attribute_posts_to_episodes(posts, eps)
    # Longer match string ("women's sports") wins over the shorter "sports"
    assert len(out["specific"]) == 1
    assert len(out["generic"]) == 0


def test_unmatched_posts_dropped():
    """Posts that don't match any episode are not bucketed anywhere."""
    eps = [EpisodeDef(id="ep1", n="01", title="A", date="", match=["foo"], exclude=[])]
    posts = [_post("nothing relevant here")]
    out = attribute_posts_to_episodes(posts, eps)
    assert out["ep1"] == []


def test_episode_rollup_computes_totals():
    """Episode rollup sums impressions and computes blended ER."""
    ep = EpisodeDef(id="ep1", n="01", title="Test", date="", match=["foo"], exclude=[])
    posts = [
        _post("foo post one", impr=10_000, eng=500, er=5.0),
        _post("foo post two", impr=20_000, eng=300, er=1.5),
    ]
    out = rollup_episode(ep, posts)
    assert out is not None
    assert out["total"]["impr"] == 30_000
    assert out["total"]["eng"] == 800
    # Blended ER = 800 / 30000 * 100 = 2.67%
    assert abs(out["total"]["er"] - 2.67) < 0.05


def test_episode_rollup_returns_none_for_empty():
    ep = EpisodeDef(id="ep1", n="01", title="Test", date="", match=[], exclude=[])
    assert rollup_episode(ep, []) is None
