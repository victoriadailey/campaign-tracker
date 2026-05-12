"""Episode detection + per-episode rollup.

An episode is defined in `campaigns.yaml` with:
    - id, n (display number), title, date
    - match: list of substrings that must appear in post_title
    - exclude: list of substrings that disqualify a post

Posts are attributed to at most one episode. If a post matches multiple episodes,
the episode with the longest match wins (most specific).

Output is the rich Episode shape the Pulse viewer's campaign.jsx expects:

    {
      n: 'Ep. 01', title: '...', date: '...',
      total: { impr, er, eng, spend },
      perChannel: [{ name, distKind, impr, paidImpr, orgImpr, eng, paidEng, orgEng, er, cpm, spend, posts }],
      topPosts: [{ quote, platform, er, reach }],
      callouts: [{ kind, text }]
    }
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from app.parsers import Boosting, NormalizedPost, Platform


@dataclass
class EpisodeDef:
    id: str
    n: str
    title: str
    date: str
    match: list[str]                     # substrings — at least one must appear in title
    exclude: list[str]                   # if any of these appear in title, post is rejected
    all_match: bool = False              # if True, ALL match strings must appear (default: any)
    impression_goal: int | None = None   # optional per-episode pacing target
    budget_goal: float | None = None     # optional per-episode budget
    manual_posts: list[str] = field(default_factory=list)
    # ↑ Explicit post_id_native values to force-attribute to this episode.
    # Use for posts where MS title/description/AI categories don't carry the
    # subject's name (e.g., a threaded tweet linking to the full episode, or
    # a Story with no text). Manual attribution wins over keyword matching.


def _normalize(s: str) -> str:
    """Lowercase + replace curly quotes with straight ones. MS exports use curly
    apostrophes ('Women's') while YAML config typically uses straight ('Women's')
    — without normalization the substring match silently misses these posts.
    """
    return (
        (s or "")
        .lower()
        .replace("’", "'")  # right single quote → '
        .replace("‘", "'")  # left single quote
        .replace("“", '"')  # left double quote
        .replace("”", '"')  # right double quote
    )


def attribute_posts_to_episodes(
    posts: list[NormalizedPost], episodes: list[EpisodeDef]
) -> dict[str, list[NormalizedPost]]:
    """Bucket each post into at most one episode. Posts that match no episode are dropped."""
    out: dict[str, list[NormalizedPost]] = {e.id: [] for e in episodes}

    # Build a lookup: post_id_native → episode_id (from manual_posts overrides).
    manual_index: dict[str, str] = {}
    for ep in episodes:
        for pid in ep.manual_posts:
            manual_index[str(pid)] = ep.id

    for p in posts:
        # Manual override wins
        if p.post_id_native and str(p.post_id_native) in manual_index:
            out[manual_index[str(p.post_id_native)]].append(p)
            continue
        # Match against title + description + AI categories.
        # Cross-posted media often has the host's name in the description even when
        # the title is generic ('What's the 2nd Biggest Sport in the US?' →
        # description mentions Mike Repole). And AI Categories give topical hints
        # for posts that are otherwise text-empty.
        ai_cats = ""
        if isinstance(p.raw, dict):
            ai_cats = p.raw.get("AI - Categories") or ""
        text = " ".join(filter(None, [
            _normalize(p.post_title),
            _normalize(p.post_description),
            _normalize(ai_cats),
        ]))
        if not text:
            continue
        # Find all matching episodes
        candidates = []
        for ep in episodes:
            if any(_normalize(ex) in text for ex in ep.exclude):
                continue
            matches = [m for m in ep.match if _normalize(m) in text]
            if ep.all_match:
                if len(matches) == len(ep.match) and matches:
                    candidates.append((ep, sum(len(m) for m in matches)))
            else:
                if matches:
                    candidates.append((ep, sum(len(m) for m in matches)))
        if not candidates:
            continue
        # Pick the most specific (longest match-keyword length)
        best = max(candidates, key=lambda c: c[1])[0]
        out[best.id].append(p)
    return out


def rollup_episode(
    ep: EpisodeDef, posts: list[NormalizedPost]
) -> dict[str, Any] | None:
    """Produce the rich Episode dict for one episode. Returns None if no posts."""
    if not posts:
        return None

    total_impr = sum(_pick_impressions(p) or 0 for p in posts)
    # Google Ads / X Ads sources only set engagements_paid (no engagements_total).
    # Fall back so paid-only sources still contribute to the episode engagement total.
    total_eng = sum((p.engagements_total or p.engagements_paid or 0) for p in posts)
    total_spend = round(sum(p.ad_spend or 0 for p in posts), 2)
    total_er = round((total_eng / total_impr * 100) if total_impr else 0.0, 2)

    # Per-channel aggregation
    by_channel: dict[str, dict[str, float]] = defaultdict(lambda: {
        "impr": 0, "paidImpr": 0, "orgImpr": 0,
        "eng": 0, "paidEng": 0, "orgEng": 0,
        "spend": 0.0, "posts": 0,
        "has_paid": False, "has_organic": False,
    })
    # Lazy imports to keep the module otherwise dependency-free
    from app.parsers import Platform, PostFormat, Source
    from app.parsers.google_ads_campaign import youtube_ad_subtype

    for p in posts:
        key = p.platform.value
        # YouTube split + Instagram Stories — mirror per_campaign_channels in rollup.py
        if p.platform is Platform.YOUTUBE:
            if p.source is Source.GOOGLE_ADS_CAMPAIGN:
                subtype = youtube_ad_subtype(p.post_title or "")
                if subtype == "in-stream":
                    key = "youtube_preroll"
                elif subtype == "shorts":
                    key = "youtube_shorts"
                else:
                    key = "youtube_infeed"
            else:
                key = "youtube_shorts" if p.post_format is PostFormat.REELS_SHORTS else "youtube_infeed"
        elif p.platform is Platform.INSTAGRAM and p.post_format is PostFormat.STORY:
            key = "instagram_stories"
        impr = _pick_impressions(p) or 0
        paid = p.impressions_paid or p.views_paid or 0
        organic = p.impressions_organic or p.views_organic or p.reach_organic or 0
        # Infer organic if not explicit: total minus paid
        if organic == 0 and impr > paid:
            organic = impr - paid
        eng_paid = p.engagements_paid or 0
        eng_total = p.engagements_total or eng_paid or 0  # paid-only sources still count
        eng_org = p.engagements_organic or max(0, eng_total - eng_paid)

        by_channel[key]["impr"] += impr
        by_channel[key]["paidImpr"] += paid
        by_channel[key]["orgImpr"] += organic
        by_channel[key]["eng"] += eng_total
        by_channel[key]["paidEng"] += eng_paid
        by_channel[key]["orgEng"] += eng_org
        by_channel[key]["spend"] += p.ad_spend or 0
        by_channel[key]["posts"] += 1
        if paid > 0 or p.boosting is Boosting.DARK or p.boosting is Boosting.BOOSTED:
            by_channel[key]["has_paid"] = True
        if organic > 0 or p.boosting is Boosting.ORGANIC:
            by_channel[key]["has_organic"] = True

    per_channel = []
    for platform_key, agg in by_channel.items():
        if platform_key == "unknown":
            continue
        impr = int(agg["impr"])
        eng = int(agg["eng"])
        er = round((eng / impr * 100) if impr else 0.0, 2)
        cpm = round((agg["spend"] / agg["paidImpr"] * 1000) if agg["paidImpr"] else 0.0, 2)
        dist_kind = (
            "organic+boosted" if agg["has_paid"] and agg["has_organic"]
            else "paid" if agg["has_paid"]
            else "organic"
        )
        per_channel.append({
            "name": _display_platform(platform_key),
            "distKind": dist_kind,
            "impr": impr,
            "paidImpr": int(agg["paidImpr"]),
            "orgImpr": int(agg["orgImpr"]),
            "eng": eng,
            "paidEng": int(agg["paidEng"]),
            "orgEng": int(agg["orgEng"]),
            "er": er,
            "cpm": cpm,
            "spend": round(agg["spend"], 2),
            "posts": int(agg["posts"]),
        })
    # Sort by impressions desc
    per_channel.sort(key=lambda c: c["impr"], reverse=True)

    # Top posts within this episode (by ER, min 1K views)
    candidates = [
        p for p in posts
        if p.er is not None and (p.views_total or p.impressions_total or 0) >= 1000
    ]
    candidates.sort(key=lambda p: p.er or 0, reverse=True)
    top_posts = [
        {
            "quote": (p.post_title or "")[:90].replace("\n", " "),
            "platform": _display_platform(p.platform.value),
            "er": round((p.er or 0) * 100 if (p.er or 0) <= 1.0 else (p.er or 0), 2),
            "reach": int(p.views_total or p.reach_total or p.impressions_total or 0),
        }
        for p in candidates[:2]
    ]

    # Auto-generate a couple of editorial callouts (best/worst channel by ER)
    callouts = _episode_callouts(per_channel)

    out = {
        "n": ep.n,
        "title": ep.title,
        "date": ep.date,
        "total": {"impr": total_impr, "er": total_er, "eng": total_eng, "spend": total_spend},
        "perChannel": per_channel,
        "topPosts": top_posts,
        "callouts": callouts,
    }
    if ep.impression_goal is not None:
        out["impressionGoal"] = ep.impression_goal
    if ep.budget_goal is not None:
        out["budgetGoal"] = ep.budget_goal
    return out


def _episode_callouts(per_channel: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Generate 1–2 short callouts based on the per-channel data."""
    if not per_channel:
        return []
    callouts: list[dict[str, str]] = []
    # Best ER channel
    by_er = [c for c in per_channel if c["er"] > 0]
    if by_er:
        best = max(by_er, key=lambda c: c["er"])
        callouts.append({"kind": "pos", "text": f"{best['name']} leading with {best['er']:.1f}% ER on {_short_num(best['impr'])} impr."})
    # Lowest CPM (efficiency)
    with_cpm = [c for c in per_channel if c["cpm"] > 0]
    if with_cpm:
        cheapest = min(with_cpm, key=lambda c: c["cpm"])
        callouts.append({"kind": "pos", "text": f"{cheapest['name']} CPM at ${cheapest['cpm']:.2f} — most efficient channel."})
    return callouts[:2]


def _pick_impressions(p: NormalizedPost) -> int | None:
    """Mirrors app.compute.rollup._pick_impressions — keep these in sync.

    YouTube: prefer impressions_paid (ad-renders) over views_total (video plays).
    Other platforms: prefer impressions_total → views_total → reach_total, then
    fall back to paid columns for ad-only sources (Google Ads campaign reports).
    """
    from app.parsers import Platform
    if p.platform is Platform.YOUTUBE:
        return (
            p.impressions_total
            or p.impressions_paid
            or p.views_total
            or p.views_paid
        )
    return (
        p.impressions_total
        or p.views_total
        or p.reach_total
        or p.impressions_paid
        or p.views_paid
    )


def _display_platform(key: str) -> str:
    return {
        "youtube": "YouTube",
        "youtube_infeed": "YouTube In-feed",
        "youtube_preroll": "YouTube Pre-roll",
        "youtube_shorts": "YouTube Shorts",
        "instagram": "Instagram",
        "instagram_stories": "Instagram Stories",
        "facebook": "Facebook",
        "tiktok": "TikTok",
        "x": "X",
        "linkedin": "LinkedIn",
        "snapchat": "Snapchat",
    }.get(key, key.title())


def _short_num(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)
