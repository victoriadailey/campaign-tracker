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


def attribute_posts_to_episodes(
    posts: list[NormalizedPost], episodes: list[EpisodeDef]
) -> dict[str, list[NormalizedPost]]:
    """Bucket each post into at most one episode. Posts that match no episode are dropped."""
    out: dict[str, list[NormalizedPost]] = {e.id: [] for e in episodes}
    for p in posts:
        title = (p.post_title or "").lower()
        if not title:
            continue
        # Find all matching episodes
        candidates = []
        for ep in episodes:
            if any(ex.lower() in title for ex in ep.exclude):
                continue
            matches = [m for m in ep.match if m.lower() in title]
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
    total_eng = sum(p.engagements_total or 0 for p in posts)
    total_spend = round(sum(p.ad_spend or 0 for p in posts), 2)
    total_er = round((total_eng / total_impr * 100) if total_impr else 0.0, 2)

    # Per-channel aggregation
    by_channel: dict[str, dict[str, float]] = defaultdict(lambda: {
        "impr": 0, "paidImpr": 0, "orgImpr": 0,
        "eng": 0, "paidEng": 0, "orgEng": 0,
        "spend": 0.0, "posts": 0,
        "has_paid": False, "has_organic": False,
    })
    for p in posts:
        key = p.platform.value
        impr = _pick_impressions(p) or 0
        paid = p.impressions_paid or p.views_paid or 0
        organic = p.impressions_organic or p.views_organic or p.reach_organic or 0
        # Infer organic if not explicit: total minus paid
        if organic == 0 and impr > paid:
            organic = impr - paid
        eng_total = p.engagements_total or 0
        eng_paid = p.engagements_paid or 0
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

    return {
        "n": ep.n,
        "title": ep.title,
        "date": ep.date,
        "total": {"impr": total_impr, "er": total_er, "eng": total_eng, "spend": total_spend},
        "perChannel": per_channel,
        "topPosts": top_posts,
        "callouts": callouts,
    }


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
    return p.impressions_total or p.views_total or p.reach_total


def _display_platform(key: str) -> str:
    return {
        "youtube": "YouTube",
        "instagram": "Instagram",
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
