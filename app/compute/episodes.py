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
from dataclasses import dataclass, field
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

    # Authoritative organic-impressions count for the YouTube In-feed
    # full-episode video. MS / GAds don't surface this reliably for long-form
    # YT (MS exports a bogus negative value; GAds doesn't track YouTube's own
    # discovery impressions). Operators pull these from YouTube Studio
    # directly and hardcode here so the dashboard never zeroes them out.
    yt_organic_impressions: int | None = None


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
        # Match against title + description + AI categories + User Tags + Post Tags.
        # Cross-posted media often has the host's name in the description even when
        # the title is generic ('What's the 2nd Biggest Sport in the US?' →
        # description mentions Mike Repole). AI Categories give topical hints
        # for posts that are otherwise text-empty. User Tags (column M) is where
        # the social team explicitly tags the episode guest — most reliable signal.
        ai_cats = user_tags = post_tags = ""
        if isinstance(p.raw, dict):
            ai_cats = p.raw.get("AI - Categories") or ""
            user_tags = p.raw.get("User Tags") or ""
            post_tags = p.raw.get("Post Tags") or ""
        text = " ".join(filter(None, [
            _normalize(p.post_title),
            _normalize(p.post_description),
            _normalize(ai_cats),
            _normalize(user_tags),
            _normalize(post_tags),
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

    from app.compute.rollup import _is_yt_preroll_post, _pick_views  # local import to avoid cycle

    total_impr = sum(_pick_impressions(p) or 0 for p in posts)
    # Universal video view count — on YT it's plays (much smaller than impressions),
    # on X it's video views, on IG/TikTok/Snapchat it's ≈ impressions.
    # YouTube subtraction rule: MS's view count on the long-form video ALREADY
    # includes pre-roll ad views (same underlying asset). Subtract the
    # GAds pre-roll bucket so the episode total doesn't double-count.
    raw_total_views = sum(_pick_views(p) for p in posts)
    yt_preroll_views = sum(_pick_views(p) for p in posts if _is_yt_preroll_post(p))
    total_views = max(0, raw_total_views - yt_preroll_views)
    # Google Ads / X Ads sources only set engagements_paid (no engagements_total).
    # Fall back so paid-only sources still contribute to the engagement total.
    total_eng = sum((p.engagements_total or p.engagements_paid or 0) for p in posts)
    total_spend = round(sum(p.ad_spend or 0 for p in posts), 2)
    # ER excludes YT Pre-roll posts (watch-progress eng not comparable to social ER).
    er_eng = sum(
        (p.engagements_total or p.engagements_paid or 0)
        for p in posts if not _is_yt_preroll_post(p)
    )
    er_impr = sum(_pick_impressions(p) or 0 for p in posts if not _is_yt_preroll_post(p))
    total_er = round((er_eng / er_impr * 100) if er_impr else 0.0, 2)

    # Per-channel aggregation
    by_channel: dict[str, dict[str, float]] = defaultdict(lambda: {
        "impr": 0, "paidImpr": 0, "orgImpr": 0,
        "views": 0,
        "eng": 0, "paidEng": 0, "orgEng": 0,
        "spend": 0.0, "posts": 0,
        "has_paid": False, "has_organic": False,
    })
    # Lazy imports to keep the module otherwise dependency-free
    from app.parsers import Platform, PostFormat, Source
    from app.parsers.google_ads_campaign import youtube_subtype_from_post

    for p in posts:
        key = p.platform.value
        # YouTube split + Instagram Stories — mirror per_campaign_channels in rollup.py
        if p.platform is Platform.YOUTUBE:
            if p.source is Source.GOOGLE_ADS_CAMPAIGN:
                subtype = youtube_subtype_from_post(p)
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
        by_channel[key]["views"] += _pick_views(p)
        by_channel[key]["eng"] += eng_total
        by_channel[key]["paidEng"] += eng_paid
        by_channel[key]["orgEng"] += eng_org
        by_channel[key]["spend"] += p.ad_spend or 0
        by_channel[key]["posts"] += 1
        # Only tag the channel "has_paid" when there's actual paid delivery
        # (paid impressions or spend). The boosting tag alone isn't enough —
        # a BOOSTED post with 0 paid impressions and 0 spend is effectively
        # organic (paused/cancelled boost).
        if paid > 0 or (p.ad_spend or 0) > 0:
            by_channel[key]["has_paid"] = True
        # YT-aware organic signal: on YouTube, MS often reports
        # `impressions_organic` as negative (the broken total−paid math) so
        # it collapses to None — but `organic_views` is a healthy positive
        # number. Treat any positive organic signal (impressions, views,
        # engagements, reach) as proof that this post has organic activity.
        # Without this, paid YT Shorts with real organic plays render as
        # "paid only" instead of "organic+boosted".
        has_org_signal = (
            organic > 0
            or (p.views_organic or 0) > 0
            or (p.engagements_organic or 0) > 0
            or (p.reach_organic or 0) > 0
        )
        if has_org_signal or p.boosting is Boosting.ORGANIC or (paid == 0 and (p.ad_spend or 0) == 0):
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
            "views": int(agg["views"]),
            "eng": eng,
            "paidEng": int(agg["paidEng"]),
            "orgEng": int(agg["orgEng"]),
            "er": er,
            "cpm": cpm,
            "spend": round(agg["spend"], 2),
            "posts": int(agg["posts"]),
        })
    # YouTube views adjustment: MS counts pre-roll ad views as views of the
    # underlying long-form video (same asset), so MS-derived in-feed views
    # double-count pre-roll. Subtract the pre-roll bucket's views from the
    # in-feed bucket so total views per episode = organic + in-feed + pre-roll
    # without overlap.
    infeed_ch = next((c for c in per_channel if c["name"] == "YouTube In-feed"), None)
    preroll_ch = next((c for c in per_channel if c["name"] == "YouTube Pre-roll"), None)
    if infeed_ch and preroll_ch and preroll_ch["views"]:
        infeed_ch["views"] = max(0, infeed_ch["views"] - preroll_ch["views"])

    # Sort by impressions desc
    per_channel.sort(key=lambda c: c["impr"], reverse=True)

    # Per-post breakdown — every individual post in this episode as its own row.
    # The per-episode table renders these (not aggregated per platform — by-channel
    # section already does that). Each row has the same column set as per_channel
    # but represents one post.
    posts_rows = []
    for p in posts:
        # Determine display platform name with subtype splits
        if p.platform is Platform.YOUTUBE:
            if p.source is Source.GOOGLE_ADS_CAMPAIGN:
                subtype = youtube_subtype_from_post(p)
                if subtype == "in-stream":
                    plat_key = "youtube_preroll"
                elif subtype == "shorts":
                    plat_key = "youtube_shorts"
                else:
                    plat_key = "youtube_infeed"
            else:
                plat_key = "youtube_shorts" if p.post_format is PostFormat.REELS_SHORTS else "youtube_infeed"
        elif p.platform is Platform.INSTAGRAM and p.post_format is PostFormat.STORY:
            plat_key = "instagram_stories"
        else:
            plat_key = p.platform.value
        if plat_key == "unknown":
            continue

        impr = _pick_impressions(p) or 0
        paid = p.impressions_paid or p.views_paid or 0
        # Organic impressions fallback chain. EXCLUDES views_organic on
        # YouTube / X / LinkedIn — on those platforms `views_organic` is
        # video PLAYS, not impressions. Impressions = tweet-render (X) /
        # ad render (YT) / post-render (LI); views = 3-sec+ playback. They
        # are measured differently and substituting one for the other gives
        # nonsense in the Organic Impressions column (e.g. a Dave Checketts
        # X organic post showing 12,718 total impressions but only 3,834
        # under "Organic Impressions" because we'd been falling back to its
        # video view count).
        #
        # IG / FB / TikTok / Snapchat keep views_organic in the fallback
        # because on those platforms autoplay makes views ≈ impressions in
        # the dashboard's data model.
        if p.platform in (Platform.YOUTUBE, Platform.X, Platform.LINKEDIN):
            organic = p.impressions_organic or p.reach_organic or 0
        else:
            organic = p.impressions_organic or p.views_organic or p.reach_organic or 0
        if organic == 0 and impr > paid:
            organic = impr - paid
        eng_paid_p = p.engagements_paid or 0
        eng_tot_p = p.engagements_total or eng_paid_p or 0
        er_pct = round((eng_tot_p / impr * 100) if impr else 0.0, 2)

        # Only treat as "paid" when there's actual paid delivery (impressions
        # or spend). A BOOSTED/DARK boosting tag without any paid metric is
        # likely a paused/cancelled boost — show as organic instead.
        has_paid = paid > 0 or (p.ad_spend or 0) > 0
        # YT-aware organic signal: see by_channel block above. MS's broken
        # `total − paid` organic-impressions math goes negative for paid YT
        # Shorts (collapses to None), but `organic_views` is positive — so a
        # post can have real organic plays with no `impressions_organic`.
        # Without this fallback, paid YT Shorts with real organic activity
        # incorrectly label as "paid only" in the per-post table.
        has_org = (
            organic > 0
            or (p.views_organic or 0) > 0
            or (p.engagements_organic or 0) > 0
            or (p.reach_organic or 0) > 0
            or p.boosting is Boosting.ORGANIC
            or not has_paid
        )
        dist_kind = (
            "organic+boosted" if has_paid and has_org
            else "paid" if has_paid
            else "organic"
        )

        title = (p.post_title or p.post_description or "")[:120].replace("\n", " ")
        posts_rows.append({
            "title": title,
            "platform": _display_platform(plat_key),
            # Friendly account / page name (e.g. "Front Office Sports" vs
            # "Front Office Sports Today") so the UI can disambiguate posts
            # that share the same copy across pages. Only set for MS-sourced
            # posts; ad-platform-only rows leave it null.
            "accountName": p.account_name,
            "distKind": dist_kind,
            "impr": int(impr),
            "paidImpr": int(paid),
            "orgImpr": int(organic),
            "views": int(_pick_views(p)),
            "eng": int(eng_tot_p),
            "er": er_pct,
            "spend": round(p.ad_spend or 0, 2),
            "url": p.post_url,
            # ISO datetime so the frontend can render the date and the sort
            # below has a stable comparison key.
            "postedAt": p.posted_at.isoformat() if p.posted_at else None,
        })
    # YouTube views adjustment at the per-post-row level. MS reports the
    # in-feed asset's view count as the total plays of that underlying video,
    # which INCLUDES plays surfaced as pre-rolls on other videos. The GAds
    # pre-roll campaign is rendered as its own row with its own view count,
    # so if we don't subtract pre-roll views from in-feed view rows the per-
    # post table double-counts those plays.
    #
    # Apply the same subtraction we already do at the per_channel and
    # episode-total levels, so all three aggregation grains tell the same
    # story:
    #     in-feed views (rendered) = MS total views – GAds pre-roll views
    preroll_views_in_ep = sum(
        r["views"] for r in posts_rows if r["platform"] == "YouTube Pre-roll"
    )
    if preroll_views_in_ep:
        # Sort in-feed rows by view-count desc so the biggest in-feed asset
        # absorbs the subtraction first. In the typical case there's only one
        # in-feed row per episode (the long-form video), and the math just
        # subtracts the full pre-roll count from that single row.
        infeed_rows = sorted(
            (r for r in posts_rows if r["platform"] == "YouTube In-feed"),
            key=lambda r: -r["views"],
        )
        remaining = preroll_views_in_ep
        for r in infeed_rows:
            sub = min(remaining, r["views"])
            r["views"] -= sub
            remaining -= sub
            if remaining <= 0:
                break

    # Sort:
    #   1. YouTube In-feed first  (the long-form episode video itself)
    #   2. YouTube Pre-roll next  (paid promotion of that long-form)
    #   3. Everything else by post date ascending — earliest first, showing the
    #      campaign rollout sequence (long-form drops, then cutdowns over time).
    # Rows without a date fall to the end of group 3.
    _FAR_FUTURE = "9999-12-31T00:00:00"
    def _sort_key(r):
        name = r.get("platform", "")
        date = r.get("postedAt") or _FAR_FUTURE
        if name == "YouTube In-feed":
            return (0, 0, date)
        if name == "YouTube Pre-roll":
            return (0, 1, date)
        return (1, 0, date, -r["impr"])
    posts_rows.sort(key=_sort_key)

    # Top posts within this episode (by ER, min 1K views).
    # YouTube Pre-roll is intentionally excluded — its "Engagement rate" is a
    # watch-progress metric (often 60–75%) that isn't comparable to other
    # formats' social ER. Surfacing it as a "top post" misleads more than it
    # informs.
    from app.parsers.google_ads_campaign import youtube_subtype_from_post

    def _post_er(p: NormalizedPost) -> float | None:
        er = p.er
        if er is None:
            return None
        return (er * 100) if er <= 1.0 else er

    def _is_yt_preroll_or_shorts(p: NormalizedPost) -> bool:
        # Both YouTube Pre-roll and YouTube Shorts have Google-Ads-reported
        # ER that conflates views with engagements — Pre-roll's ER is
        # watch-progress (60-75%), Shorts' is views ÷ impressions (30-45%
        # on any decent short). Neither is comparable to social ER.
        # Check post_format for Shorts (covers MS posts where the title
        # doesn't carry a "(Shorts)" suffix) and subtype for Pre-roll.
        if p.platform is not Platform.YOUTUBE:
            return False
        if p.post_format is PostFormat.REELS_SHORTS:
            return True
        return youtube_subtype_from_post(p) in ("in-stream", "shorts")

    def _is_snapchat(p: NormalizedPost) -> bool:
        # Snapchat ER runs 50-90% on successful posts because the platform
        # counts watch-time interactions as engagements — not comparable to
        # social ER (likes/comments/shares ÷ impressions). Same rule as Pre-roll.
        return p.platform is Platform.SNAPCHAT

    # Same threshold as cross-campaign top posts: ER ≥ 2.0% to count as a
    # "top performer". A 0.3% post is not a top performer regardless of where
    # it ranks within the episode — we'd rather show nothing than misrepresent.
    EPISODE_TOP_POST_MIN_ER = 2.0
    scored = [
        (p, _post_er(p)) for p in posts
        if (p.views_total or p.impressions_total or 0) >= 1000
        and not _is_yt_preroll_or_shorts(p)
        and not _is_snapchat(p)
    ]
    scored = [(p, e) for p, e in scored if e is not None and e >= EPISODE_TOP_POST_MIN_ER]
    scored.sort(key=lambda pe: pe[1], reverse=True)
    top_posts = [
        {
            # MS API LinkedIn posts have no `title` — only `description`.
            # Fall back so the quote text isn't empty for those (or for any
            # platform that doesn't have a separate title field).
            "quote": ((p.post_title or p.post_description or "")[:90]).replace("\n", " "),
            "platform": _display_platform(p.platform.value),
            "er": round(er_pct, 2),
            "reach": int(p.views_total or p.reach_total or p.impressions_total or 0),
            "url": p.post_url,  # link out to the actual post on the platform
        }
        for p, er_pct in scored[:2]
    ]

    # Auto-generate a couple of editorial callouts (best/worst channel by ER)
    callouts = _episode_callouts(per_channel)

    out = {
        "n": ep.n,
        "title": ep.title,
        "date": ep.date,
        "total": {"impr": total_impr, "views": total_views, "er": total_er, "eng": total_eng, "spend": total_spend},
        "perChannel": per_channel,
        "posts": posts_rows,
        "topPosts": top_posts,
        "callouts": callouts,
    }
    if ep.impression_goal is not None:
        out["impressionGoal"] = ep.impression_goal
    if ep.budget_goal is not None:
        out["budgetGoal"] = ep.budget_goal
    return out


def _episode_callouts(per_channel: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Generate up to 2 WIN callouts for this episode.

    Rules (May 2026):
      • WIN = content that overperformed on either:
          – Engagement Rate above a meaningful threshold (≥2%), OR
          – Organic reach as a large share of total delivery (≥60% on real volume)
      • YouTube (any subtype) is NEVER eligible for ER WIN — Google Ads ER
        conflates views with engagements (Pre-roll 60-75%, Shorts 20-40%,
        In-feed inflated too), not comparable to true social ER.
      • Efficient CPM is NOT a WIN — WINs are about resonance, not unit economics.
      • If nothing crosses the bar, no WIN callouts (silence is fine).
    """
    if not per_channel:
        return []

    callouts: list[dict[str, str]] = []
    ER_FLOOR = 2.0          # Minimum ER% to qualify as a "leading with X% ER" WIN
    ORG_FLOOR_PCT = 60.0    # % organic of total to qualify as an organic-share WIN
    ORG_VOLUME_MIN = 10_000 # Minimum total channel impressions before we'll surface

    # ---------- ER WIN ----------
    # Skip any YouTube channel/subtype entirely; require ER ≥ floor.
    er_eligible = [
        c for c in per_channel
        if c["er"] >= ER_FLOOR and "youtube" not in c["name"].lower()
    ]
    if er_eligible:
        best = max(er_eligible, key=lambda c: c["er"])
        callouts.append({
            "kind": "pos",
            "text": f"{best['name']} leading with {best['er']:.1f}% ER on {_short_num(best['impr'])} impr.",
        })

    # ---------- ORGANIC SHARE WIN ----------
    # A channel where organic delivery is a high % of total impressions, on
    # non-trivial volume — signals the algorithm is rewarding this content.
    org_eligible = []
    for c in per_channel:
        impr = c.get("impr", 0)
        org = c.get("orgImpr", 0)
        if impr < ORG_VOLUME_MIN or org <= 0:
            continue
        pct = (org / impr) * 100
        if pct >= ORG_FLOOR_PCT:
            org_eligible.append((c, pct, org))
    if org_eligible:
        # Rank by absolute organic reach (biggest standout)
        c, pct, org = max(org_eligible, key=lambda x: x[2])
        # Avoid re-stating the same channel that won ER — vary the WIN
        if not callouts or callouts[0]["text"].split(" leading")[0] != c["name"]:
            callouts.append({
                "kind": "pos",
                "text": f"{c['name']} resonating — {pct:.0f}% organic share on {_short_num(org)} impr.",
            })

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
