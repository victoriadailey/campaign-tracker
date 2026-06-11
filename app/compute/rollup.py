"""Aggregations: parsed posts → Pulse rollups."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from app.parsers import Boosting, NormalizedPost, Platform, PostFormat, Source
from app.parsers.google_ads_campaign import youtube_ad_subtype, youtube_subtype_from_post
from app.viewer.data_contract import (
    CampaignSummary,
    Channel,
    ChannelBenchmark,
    Goal,
    HeroPost,
    StatusKind,
    TopPost,
    TopPostOrganic,
)


PLATFORM_BENCHMARKS: dict[str, ChannelBenchmark] = {
    # FOS Sponsored benchmarks.
    #
    # YouTube is split by ad subtype because Google's "Engagement rate" has very
    # different scales per format (Pre-roll counts watch-progress, In-feed counts
    # clicks/interactions, Shorts is somewhere between). The plain "youtube" key
    # is rarely used in the UI now that we report per-subtype — kept as a coarse
    # default for any code path that lacks subtype context.
    #
    # YouTube benchmarks derived from the May 2026 Portfolio Players + ADP +
    # Spectrum Google Ads exports (n=42 live campaigns) — median values, rounded.
    #   Pre-roll (In-stream): median ER 74%, CPM $14
    #   In-feed:              median ER 0.5%, CPM $0.55
    #   Shorts:               median ER 24%, CPM $3.25
    "youtube":          ChannelBenchmark(er=20.00, cpm=3.50),   # coarse fallback
    "youtube_preroll":  ChannelBenchmark(er=72.00, cpm=14.00),  # In-stream (TrueView)
    "youtube_infeed":   ChannelBenchmark(er=0.50,  cpm=0.55),
    "youtube_shorts":   ChannelBenchmark(er=20.00, cpm=3.25),
    # Non-YouTube benchmarks unchanged from FOS Platform Benchmarks 2025 (updated 3/5).
    "instagram": ChannelBenchmark(er=3.31, cpm=5.10),
    "instagram_stories": ChannelBenchmark(er=3.31, cpm=5.10),
    "tiktok":    ChannelBenchmark(er=2.03, cpm=2.40),
    "linkedin":  ChannelBenchmark(er=3.76, cpm=0.0),
    "x":         ChannelBenchmark(er=0.92, cpm=1.10),
    "facebook":  ChannelBenchmark(er=1.53, cpm=4.80),
}

# All-content benchmarks (organic + sponsored) — shown as secondary reference.
PLATFORM_BENCHMARKS_ALL_CONTENT: dict[str, float] = {
    "youtube":   1.00,
    "instagram": 3.60,
    "tiktok":    4.90,
    "linkedin":  5.20,
    "x":         2.30,
    "facebook":  4.00,
}

PLATFORM_COLORS: dict[str, str] = {
    "youtube":   "#E00922",
    "instagram": "#E4405F",
    "tiktok":    "#000000",
    "linkedin":  "#0A66C2",
    "x":         "#1d1d1f",
    "facebook":  "#1877F2",
}

PLATFORM_DISPLAY: dict[str, str] = {
    "youtube":   "YouTube",
    "instagram": "Instagram",
    "tiktok":    "TikTok",
    "linkedin":  "LinkedIn",
    "x":         "X",
    "facebook":  "Facebook",
}

PLATFORM_ITALIC: dict[str, str] = {
    "youtube":   "Tube",
    "instagram": "gram",
    "tiktok":    "Tok",
    "linkedin":  "LinkedIn",
    "x":         "X",
    "facebook":  "book",
}


@dataclass
class CampaignConfig:
    id: str
    partner: str
    series: str
    series_italic: str
    type: str
    flight_start: date
    flight_end: date
    impression_goal: int
    budget_goal: float
    color: str
    lead_format: str
    blurb: str
    benchmark_category: str = ""
    lifecycle: str = "active"  # "active" or "wrapped"
    # Optional Full Episodes vs Cutdowns goal split.
    # Each entry: {"label": str, "impression_goal": int, "budget_goal": float}
    # When set, campaign card renders two side-by-side cards with separate
    # delivery + goal tracking per tier.
    goal_split_full_ep: dict | None = None
    goal_split_cutdowns: dict | None = None
    # BrandX objective drives which CPM benchmark applies (impressions /
    # awareness uses $2.63, clicks uses $5.46, etc.). Synonyms map to the
    # canonical key — see `_normalize_brandx_objective`.
    brandx_objective: str = ""
    brandx_secondary_objective: str = ""
    # Fully-dark / paid-only campaigns. When set, all organic-side metrics
    # are zeroed in the rollup so the dashboard reads as 100% paid — the
    # team's reporting standard for dark campaigns where any incidental
    # organic exposure (post URLs shared, profile-page browsers) isn't
    # part of the contracted delivery. Also suppresses OPPORTUNITY callouts
    # since "X% organic resonance" is meaningless for a paid-only campaign.
    paid_only: bool = False
    # Per-post "treat as paid-only" override. Use for individual dark posts
    # whose campaign isn't paid-only overall but which happen to pick up a
    # token amount of incidental organic impressions (e.g. a handful of
    # views from the FB page owning the post). Listing the post's
    # `post_id_native` here forces its organic side to zero so the row
    # renders as "Paid only" instead of "Organic+boosted" against noise.
    # Spectrum uses this for two Vintage Flying Museum FB Reels where MS
    # reports org=2 and org=5 against ~300K paid impressions.
    paid_only_post_ids: list[str] = field(default_factory=list)
    # New / pending campaigns where flight + goals are still being negotiated.
    # When True, the dashboard renders "TBD" in place of flight dates,
    # impression %, budget %, and elapsed time — the campaign still shows up
    # on the overview with whatever delivery numbers are in flight, but pacing
    # math is suppressed because there's no goal to pace against.
    flight_tbd: bool = False


_BRANDX_OBJECTIVE_SYNONYMS = {
    "awareness":   "impressions",
    "impressions": "impressions",
    "reach":       "impressions",
    "clicks":      "clicks",
    "traffic":     "clicks",
    "link clicks": "clicks",
    "app install": "app_install",
    "app installs": "app_install",
    "conversions": "conversions",
}


def _normalize_brandx_objective(obj: str) -> str:
    """Map operator-friendly labels (awareness, traffic, etc.) to the
    canonical keys used in BRANDX_BENCHMARK_CPM_BY_OBJECTIVE."""
    return _BRANDX_OBJECTIVE_SYNONYMS.get((obj or "").strip().lower(), obj or "")


def rollup_campaign(
    config: CampaignConfig,
    posts: list[NormalizedPost],
    today: date | None = None,
) -> CampaignSummary:
    today = today or date.today()

    # For paid-only / fully-dark campaigns (e.g. On Location), zero out all
    # organic-side delivery so the dashboard reads as 100% paid. This is the
    # team's reporting standard — any incidental organic exposure on a dark
    # post isn't part of the contracted delivery. Mutates posts in place
    # so downstream channel-rollups + per-post tables also reflect 0 organic.
    #
    # Also backfill impressions_paid / engagements_paid from totals when MS
    # didn't surface them explicitly (some FB / Snap dark posts only report
    # `reach` or `page_media_views_paid`). Without this, the dashboard's
    # `organic = total − paid` synthesis kicks in and mis-attributes the
    # paid delivery as organic.
    def _force_paid_only(p: NormalizedPost) -> None:
        """Strip the organic side of a single post.

        Used by both `paid_only: true` (whole campaign) and
        `paid_only_post_ids:` (individual posts). Also collapses
        `impressions_total` down to `impressions_paid` — otherwise the
        episodes.py `organic = impr - paid` fallback synthesizes the
        organic count right back from the gap. (E.g. Spectrum FB Reels
        where MS reports paid=230,548 + org=2, total=230,550; zeroing
        org alone leaves total at 230,550 and the synthesizer reconstructs
        org=2 downstream.)
        """
        p.impressions_organic = None
        p.views_organic = None
        p.reach_organic = None
        p.engagements_organic = None
        if not p.impressions_paid:
            total = _pick_impressions(p)
            if total:
                p.impressions_paid = total
        if not p.engagements_paid and p.engagements_total:
            p.engagements_paid = p.engagements_total
        if not p.views_paid and p.views_total:
            p.views_paid = p.views_total
        if not p.reach_paid and p.reach_total:
            p.reach_paid = p.reach_total
        # Pull totals down to match the paid side so downstream code can't
        # back-derive an organic value from the leftover gap.
        if p.impressions_paid is not None:
            p.impressions_total = p.impressions_paid
        if p.engagements_paid is not None:
            p.engagements_total = p.engagements_paid
        if p.views_paid is not None:
            p.views_total = p.views_paid
        if p.reach_paid is not None:
            p.reach_total = p.reach_paid

    if config.paid_only:
        for p in posts:
            _force_paid_only(p)

    # Per-post "treat as paid-only" overrides — same zeroing as the
    # campaign-level flag but applied only to specific post IDs the
    # operator marked in YAML. See `paid_only_post_ids` docstring on
    # CampaignConfig for the use case.
    if config.paid_only_post_ids:
        override_ids = {str(pid) for pid in config.paid_only_post_ids}
        for p in posts:
            if p.post_id_native and str(p.post_id_native) in override_ids:
                _force_paid_only(p)

    total_impressions = sum(_pick_impressions(p) or 0 for p in posts)
    # Views is the universal "people who watched / saw the content" metric.
    # On YT and X it differs meaningfully from impressions; on IG / TikTok /
    # Snapchat it's nearly identical (those platforms autoplay video).
    # YouTube subtraction rule: MS's view count on the long-form video
    # already includes pre-roll ad views (same underlying asset). Subtract
    # the GAds pre-roll views so the campaign total doesn't double-count.
    raw_total_views = sum(_pick_views(p) for p in posts)
    yt_preroll_views = sum(_pick_views(p) for p in posts if _is_yt_preroll_post(p))
    total_views = max(0, raw_total_views - yt_preroll_views)
    # Paid-only sources (Google Ads campaign, X Ads) set engagements_paid not _total;
    # include them so campaign-level engagement totals aren't under-counted.
    total_engagements = sum((p.engagements_total or p.engagements_paid or 0) for p in posts)
    total_spend = sum(p.ad_spend or 0 for p in posts)
    # ER: total eng ÷ total impressions across all posts, EXCLUDING YT Pre-roll
    # (its eng/impr is a watch-progress metric, not social engagement — see
    # `_is_yt_preroll_post`). Pre-roll's impr and eng are still in the headline
    # counts above, but ER reflects only social-comparable engagement.
    er_eng = sum(
        (p.engagements_total or p.engagements_paid or 0)
        for p in posts if not _is_yt_preroll_post(p)
    )
    er_impr = sum(_pick_impressions(p) or 0 for p in posts if not _is_yt_preroll_post(p))
    er = (er_eng / er_impr * 100) if er_impr else 0.0
    paid_impressions = sum(p.impressions_paid or 0 for p in posts)
    cpm = (total_spend / paid_impressions * 1000) if paid_impressions else 0.0

    # Flight-TBD campaigns: suppress pacing math. The campaign still shows
    # whatever delivery exists (e.g. early posts that ran before the contract
    # was finalised), but elapsed_pct / days_left / status are emitted as
    # neutral "TBD" markers so the dashboard doesn't render a false pace.
    if config.flight_tbd:
        elapsed_pct = 0.0
        days_left = 0
        status_kind, status_label = "tbd", "Flight TBD"
    else:
        elapsed_pct = _elapsed_pct(config.flight_start, config.flight_end, today)
        days_left = max(0, (config.flight_end - today).days)
        if not config.impression_goal:
            # No impression goal set — campaign tracked as added-value delivery
            # (e.g. the split-out Morgan & Morgan). Impressions still count in
            # totals/per-post; we just don't score it against a target or flag
            # it "Goal Missed".
            status_kind, status_label = "tbd", "Added Value"
        else:
            impressions_pct = total_impressions / config.impression_goal * 100
            status_kind, status_label = _status(elapsed_pct, impressions_pct)

    by_platform = _group_impressions_by_platform(posts)
    top_channel = max(by_platform.items(), key=lambda kv: kv[1])[0] if by_platform else "unknown"

    # Full Episodes vs Cutdowns split (only when YAML defines goals for both).
    goal_split: list = []
    if config.goal_split_full_ep and config.goal_split_cutdowns:
        full_posts = [p for p in posts if _is_full_episode_content(p)]
        cut_posts = [p for p in posts if not _is_full_episode_content(p)]
        for label_cfg, bucket in (
            (config.goal_split_full_ep, full_posts),
            (config.goal_split_cutdowns, cut_posts),
        ):
            bucket_impr = sum(_pick_impressions(p) or 0 for p in bucket)
            bucket_spend = sum(p.ad_spend or 0 for p in bucket)
            goal_split.append({
                "label": label_cfg["label"],
                "impressions": {
                    "delivered": int(bucket_impr),
                    "goal": int(label_cfg.get("impression_goal", 0)),
                },
                "budget": {
                    "delivered": round(bucket_spend, 2),
                    "goal": float(label_cfg.get("budget_goal", 0)),
                },
                "posts": len(bucket),
            })

    return CampaignSummary(
        id=config.id,
        partner=config.partner,
        series=config.series,
        series_italic=config.series_italic,
        type=config.type,  # type: ignore[arg-type]
        flight=("TBD" if config.flight_tbd
                else _flight_label(config.flight_start, config.flight_end)),
        elapsed_pct=round(elapsed_pct, 1),
        days_left=days_left,
        status=status_label,
        status_kind=status_kind,
        impressions=Goal(delivered=total_impressions, goal=config.impression_goal),
        budget=Goal(delivered=round(total_spend, 2), goal=config.budget_goal),
        color=config.color,
        lead_format=config.lead_format,
        top_channel=PLATFORM_DISPLAY.get(top_channel, top_channel.title()),
        er=round(er, 1),
        cpm=round(cpm, 2),
        episodes=0,
        posts=len(posts),
        blurb=config.blurb,
        benchmark_category=config.benchmark_category,
        lifecycle=config.lifecycle,  # type: ignore[arg-type]
        views=int(total_views),
        goal_split=goal_split,
        brandx_objective=_normalize_brandx_objective(config.brandx_objective),
        brandx_secondary_objective=_normalize_brandx_objective(config.brandx_secondary_objective),
    )


def _is_full_episode_content(p: NormalizedPost) -> bool:
    """A post counts as 'Full Episode' delivery (vs 'Cutdown') when it's the
    long-form video itself or a paid ad driving viewers to it:
      • YouTube long-form video (MS source)
      • YouTube In-feed Google Ads (promotes the long-form)
      • YouTube Pre-roll Google Ads (TrueView in-stream ad for the long-form)
      • Any post with "Full Episode" / "Full Ep" in its title

    Everything else (Shorts, all social-platform cutdown clips) = 'Cutdown'.
    """
    title = (p.post_title or "").lower()
    if "full episode" in title or "full ep" in title:
        return True
    if p.platform is not Platform.YOUTUBE:
        return False
    if p.source is Source.GOOGLE_ADS_CAMPAIGN:
        from app.parsers.google_ads_campaign import youtube_subtype_from_post
        subtype = youtube_subtype_from_post(p)
        return subtype in ("in-feed", "in-stream")
    # MS YT: long-form post_format = YOUTUBE_LONG
    return p.post_format is PostFormat.YOUTUBE_LONG


def _is_yt_preroll_post(p: NormalizedPost) -> bool:
    """Identify YouTube Pre-roll (In-stream) posts.

    Pre-roll ER is calculated by Google as a watch-progress metric (eng counts
    25%/50%/75%/100% video plays). That's incompatible with the social ER on
    other platforms (likes/comments/shares ÷ impressions). To keep aggregate
    ER honest, Pre-roll posts are excluded from EVERY rolled-up ER calculation
    (campaign-level, channel-level, episode-level).

    Pre-roll still appears as its own row in per-channel breakdowns with its
    own metrics — we just don't blend it into anything else.
    """
    if p.platform is not Platform.YOUTUBE:
        return False
    return youtube_subtype_from_post(p) == "in-stream"


def _post_er_pct(p: NormalizedPost) -> float | None:
    """Engagement rate (in % points) for a single post.

    Trusts the source's own ER column (`p.er`) — MS's "Engagement Rate - Total"
    for MS posts, Google Ads' "Engagement rate" for paid YouTube. Normalized
    to a 0-100 scale if the source stored it as a 0.0-1.0 fraction.
    """
    er = p.er
    if er is None:
        return None
    return (er * 100) if er <= 1.0 else er


def top_posts_by_er(
    posts_by_campaign: dict[str, list[NormalizedPost]],
    partners: dict[str, str],
    n: int = 8,
    min_views: int = 1000,
    min_er: float = 2.0,
) -> list[TopPost]:
    """Top posts ranked by ER. ER must be at or above min_er (in percentage points)
    to count — a post with 0.0% ER isn't useful as a 'top performer'.

    Excluded from top-post rankings (each has an artificially inflated ER that
    isn't comparable to social ER):
      • YouTube Pre-roll — Google Ads' "Engagement rate" is watch-progress (60-75%).
      • YouTube Shorts — Google Ads counts video views as engagements, which
        produces 30-45% ER for any decent short; not meaningful next to feed posts.
      • Snapchat — engagements include watch-time interactions, producing 50-90% ER.
    """
    candidates = []
    for campaign_id, posts in posts_by_campaign.items():
        for p in posts:
            # Skip YouTube Pre-roll AND YouTube Shorts — both have ER inflated
            # by Google Ads counting views as engagements. Check post_format
            # for Shorts (covers MS posts) and subtype for Pre-roll (GAds-only).
            if p.platform is Platform.YOUTUBE:
                if p.post_format is PostFormat.REELS_SHORTS:
                    continue
                if youtube_subtype_from_post(p) in ("in-stream", "shorts"):
                    continue
            # Skip Snapchat — its ER (engagements ÷ views) runs in the 50-90%
            # range for any successful post because Snapchat counts watch-time
            # interactions as engagement. Not comparable to social ER.
            if p.platform is Platform.SNAPCHAT:
                continue
            views = p.views_total or p.impressions_total or 0
            er_pct = _post_er_pct(p)
            if er_pct is None or views < min_views or er_pct < min_er:
                continue
            candidates.append((campaign_id, p, er_pct))

    ranked = sorted(candidates, key=lambda x: x[2], reverse=True)[:n]

    out: list[TopPost] = []
    for rank, (campaign_id, p, er_pct) in enumerate(ranked, start=1):
        out.append(TopPost(
            id=p.post_id_native or f"post_{rank}",
            rank=rank,
            partner=partners.get(campaign_id, campaign_id),
            platform=PLATFORM_DISPLAY.get(p.platform.value, p.platform.value.title()),
            format=_format_label(p.post_format.value),
            quote=_truncate_quote(p.post_title or p.post_description or ""),
            er=round(er_pct, 2),
            eng=p.engagements_total or 0,
            reach=p.views_total or p.reach_total or p.impressions_total or 0,
            organic=_organic_pct(p),
            metric="er",
            insight="",
            posted_at=p.posted_at.isoformat() if p.posted_at else None,
            url=p.post_url,
        ))
    return out


def hero_post_from_top(top: list[TopPost]) -> HeroPost | None:
    if not top:
        return None
    p = top[0]
    return HeroPost(
        partner=p.partner,
        platform=p.platform,
        format=f"{p.organic}% organic {p.format.lower()}",
        quote=p.quote,
        attribution=f"{p.partner} — top performer",
        er=f"{p.er:.2f}%",
        eng=f"{p.eng:,}",
        reach=f"{p.reach:,}",
        organic=f"{p.organic}%",
    )


def top_posts_by_organic_reach(
    posts_by_campaign: dict[str, list[NormalizedPost]],
    partners: dict[str, str],
    n: int = 6,
) -> list[TopPostOrganic]:
    candidates = []
    for campaign_id, posts in posts_by_campaign.items():
        for p in posts:
            # Exclude YouTube. MS's organic vs paid split for YT is unreliable
            # (views_total uses YouTube's own counting, views_paid is
            # GAds-imported using different methodology — the two metrics
            # don't reconcile, so "% organic" math becomes misleading e.g.
            # a Short with 228K MS views + 461K GAds paid impressions reads
            # as 96% organic because the denominator drops paid impressions).
            if p.platform is Platform.YOUTUBE:
                continue
            organic = p.views_organic or p.reach_organic or p.impressions_organic or 0
            total = p.views_total or p.reach_total or p.impressions_total or organic
            # 100K+ organic reach threshold — anything below isn't a "standout"
            # in the sense the user wants to see surfaced.
            if organic < 100_000:
                continue
            candidates.append((campaign_id, p, organic, total))

    ranked = sorted(candidates, key=lambda x: x[2], reverse=True)[:n]

    out: list[TopPostOrganic] = []
    for rank, (campaign_id, p, organic, total) in enumerate(ranked, start=1):
        organic_pct = (organic / total * 100) if total else 100.0
        out.append(TopPostOrganic(
            id=f"o{rank}",
            rank=rank,
            partner=partners.get(campaign_id, campaign_id),
            platform=PLATFORM_DISPLAY.get(p.platform.value, p.platform.value.title()),
            format=_format_label(p.post_format.value),
            quote=_truncate_quote(p.post_title or p.post_description or ""),
            organic_reach=organic,
            total_reach=total,
            organic_pct=round(organic_pct, 1),
            er=round(_post_er_pct(p) or 0.0, 2),
            insight="",
            url=p.post_url,
        ))
    return out


def per_campaign_channels(posts: list[NormalizedPost]) -> list[Channel]:
    """Per-campaign channel rollup with YouTube split into In-feed and Pre-roll.

    Uses Google Ads campaign-name subtype (`youtube_ad_subtype()`) to bucket YouTube
    posts. MS-source YouTube posts (organic) bucket as "in-feed" since they show in
    YouTube's feed/browse experience.
    """
    by_key: dict[str, dict[str, float]] = defaultdict(lambda: {
        "impressions": 0, "views": 0, "eng": 0, "spend": 0.0,
        "paid_impressions": 0, "organic_impressions": 0,
    })
    for p in posts:
        key = p.platform.value
        if p.platform is Platform.YOUTUBE:
            # Split YouTube into In-feed / Pre-roll / Shorts
            if p.source is Source.GOOGLE_ADS_CAMPAIGN:
                subtype = youtube_subtype_from_post(p)
                if subtype == "in-stream":
                    key = "youtube_preroll"
                elif subtype == "shorts":
                    key = "youtube_shorts"
                else:
                    key = "youtube_infeed"
            else:
                # MS-source YT post — classify by post_format
                key = "youtube_shorts" if p.post_format is PostFormat.REELS_SHORTS else "youtube_infeed"
        elif p.platform is Platform.INSTAGRAM and p.post_format is PostFormat.STORY:
            # Instagram Stories tracked separately from feed posts (different format,
            # different audience behavior, different metrics — auto-expire, no reach).
            key = "instagram_stories"

        # Organic impressions fallback chain. EXCLUDES views_organic on
        # YouTube — there `views_organic` (MS field: `organic_views`) is the
        # count of organic video PLAYS, not impressions. Treating it as an
        # impression equivalent double-counts video plays as feed impressions
        # — e.g. RBC's "Evelyn Shores" YT Short reports impressions_paid=970K
        # with impressions_organic=-963K (collapses to None) AND
        # organic_views=392K (the real organic play count). Folding 392K into
        # the organic-impressions bucket implies 392K extra impressions on top
        # of the paid 970K, doubling the campaign's reach claim. The same
        # guard already lives in episodes.py per-post emit; this brings the
        # per-channel rollup in line.
        # Same guard as episodes.py — YT, X, LinkedIn all have views ≠
        # impressions, so excluding views_organic from the fallback chain
        # prevents organic video plays from being mis-rendered as organic
        # impressions on those platforms.
        if p.platform in (Platform.YOUTUBE, Platform.X, Platform.LINKEDIN):
            organic = p.impressions_organic or p.reach_organic or 0
        else:
            organic = p.impressions_organic or p.views_organic or p.reach_organic or 0
        # If we don't have an explicit organic field but the post is non-paid, total is organic
        if not organic and not (p.impressions_paid or p.views_paid):
            organic = _pick_impressions(p) or 0

        by_key[key]["impressions"] += _pick_impressions(p) or 0
        by_key[key]["views"] += _pick_views(p)
        by_key[key]["eng"] += (p.engagements_total or p.engagements_paid or 0)
        by_key[key]["spend"] += p.ad_spend or 0
        by_key[key]["paid_impressions"] += p.impressions_paid or 0
        by_key[key]["organic_impressions"] += organic

    out: list[Channel] = []
    for key, agg in by_key.items():
        if key == "unknown":
            continue
        impressions = int(agg["impressions"])
        eng = int(agg["eng"])
        spend = agg["spend"]
        paid = agg["paid_impressions"]
        er = (eng / impressions * 100) if impressions else 0.0
        cpm = (spend / paid * 1000) if paid else 0.0

        display_name, italic, bench, color = _channel_display(key)
        delta = round(((er - bench.er) / bench.er * 100) if bench.er else 0.0, 1)
        out.append(Channel(
            name=display_name, italic=italic,
            impressions=impressions, eng=eng,
            er=round(er, 2), cpm=round(cpm, 2),
            color=color, delta=delta, bench=bench,
            organic_impressions=int(agg["organic_impressions"]),
            views=int(agg["views"]),
        ))

    # YouTube views adjustment: MS's view count on the long-form video
    # ALREADY includes pre-roll ad views (those count as views of the same
    # underlying video). To avoid double-counting, the "in-feed + organic"
    # view total subtracts the GAds pre-roll views from the In-feed bucket.
    # Pre-roll bucket views stay as Google Ads reports them.
    infeed = next((c for c in out if c.name == "YouTube In-feed"), None)
    preroll = next((c for c in out if c.name == "YouTube Pre-roll"), None)
    if infeed is not None and preroll is not None and preroll.views:
        infeed.views = max(0, (infeed.views or 0) - preroll.views)

    out.sort(key=lambda c: c.impressions, reverse=True)

    # Keep YouTube In-feed + Pre-roll tiles adjacent in the by-channel grid.
    infeed_idx = next((i for i, c in enumerate(out) if c.name == "YouTube In-feed"), None)
    preroll_idx = next((i for i, c in enumerate(out) if c.name == "YouTube Pre-roll"), None)
    if infeed_idx is not None and preroll_idx is not None and abs(infeed_idx - preroll_idx) > 1:
        if infeed_idx < preroll_idx:
            preroll = out.pop(preroll_idx)
            out.insert(infeed_idx + 1, preroll)
        else:
            infeed = out.pop(infeed_idx)
            out.insert(preroll_idx + 1, infeed)
    return out


def _post_platform_benchmark(platform_display: str) -> ChannelBenchmark:
    """Map a display platform name (possibly with subtype) to its FOS benchmark.

    YouTube has subtype-specific benchmarks (In-feed / Pre-roll / Shorts) since
    Google's Engagement rate has very different scales per format. Instagram
    Stories falls back to the Instagram benchmark.
    """
    p = (platform_display or "").lower()
    if "youtube" in p:
        if "in-feed" in p or "infeed" in p:
            return PLATFORM_BENCHMARKS["youtube_infeed"]
        if "pre-roll" in p or "preroll" in p or "in-stream" in p:
            return PLATFORM_BENCHMARKS["youtube_preroll"]
        if "shorts" in p:
            return PLATFORM_BENCHMARKS["youtube_shorts"]
        return PLATFORM_BENCHMARKS["youtube"]
    if "instagram" in p:
        return PLATFORM_BENCHMARKS["instagram"]
    if p in PLATFORM_BENCHMARKS:
        return PLATFORM_BENCHMARKS[p]
    return ChannelBenchmark(er=0.0, cpm=0.0)


def compute_campaign_callouts(
    summary: CampaignSummary,
    channels: list[Channel],
    top_posts: list[TopPost] | None = None,
    today: "date | datetime | None" = None,
    organic_by_design_for: set[str] | None = None,
    win_recency_days: int = 7,
) -> list[dict]:
    """Produce up to 3 callouts (WIN / OPPORTUNITY / WATCH) for one campaign.

    Spec (May 2026):
      • WIN — a specific post or channel with ER meaningfully above its FOS benchmark.
        Pick whichever has the largest benchmark multiplier. Posts must be
        FRESH (≤ win_recency_days old) — a TikTok post from 3 weeks ago that's
        still topping the cross-campaign chart isn't a "win" worth surfacing now.
      • OPPORTUNITY — a channel where audience resonance is clearest: high % organic
        delivery on real volume. Framing leans into 'content is resonating' rather
        than 'free reach.' Channels listed in `organic_by_design_for` are skipped —
        e.g. clients who explicitly mandate organic-only on a platform (E*TRADE
        on TikTok) shouldn't trigger an "organic resonance" callout because it
        was a contract requirement, not an algorithmic signal.
      • WATCH — CPM ≥ 2× benchmark (budget risk) OR pacing < 85% past 25% elapsed
        (needs immediate optimization). Pacing wins when both fire.
    """
    callouts: list[dict] = []
    top_posts = top_posts or []
    organic_by_design_for = {p.lower() for p in (organic_by_design_for or set())}

    # Resolve "today" for the recency filter.
    from datetime import date as _date, datetime as _dt, timedelta as _td
    if today is None:
        today_d = _date.today()
    elif isinstance(today, _dt):
        today_d = today.date()
    else:
        today_d = today
    win_cutoff = today_d - _td(days=win_recency_days)

    def _is_fresh(post_obj) -> bool:
        """Posts must have been published within `win_recency_days` to be
        eligible as a WIN. Posts without a `posted_at` are skipped (we'd
        rather under-surface than re-surface a stale post that lost its date
        in the data pipeline)."""
        pa = getattr(post_obj, "posted_at", None)
        if not pa:
            return False
        try:
            d = _dt.fromisoformat(str(pa).replace("Z", "+00:00")).date()
        except (ValueError, TypeError):
            return False
        return d >= win_cutoff

    # ---------- WIN: best benchmark-beating post or channel ----------
    # YouTube is excluded from WIN consideration (any subtype). Google Ads
    # reports ER that conflates views with engagements — Shorts show 20-40%,
    # Pre-roll 60-75%, even In-feed sits higher than the FOS YT benchmark.
    # Surfacing those as "WINs" misleads partners about which assets are
    # actually outperforming social benchmarks.
    #
    # Posts must also be FRESH — see _is_fresh above. WINs should reflect
    # what's working RIGHT NOW, not a long-dominant post that won the chart
    # weeks ago. Channel-level WINs aren't recency-gated because they
    # represent rolling-campaign aggregate performance, not a single asset.
    win_candidates: list[tuple[str, object, float]] = []
    # Channels above benchmark with meaningful volume
    for c in channels:
        if "youtube" in c.name.lower():
            continue
        if c.name.lower() in organic_by_design_for:
            # Client-mandated organic platforms aren't really "wins" to flag —
            # they're contract requirements (e.g. E*TRADE TikTok).
            continue
        bench_er = c.bench.er if c.bench and c.bench.er > 0 else 0.0
        if bench_er > 0 and c.impressions >= 10_000 and c.er >= bench_er * 1.5:
            win_candidates.append(("channel", c, c.er / bench_er))
    # Posts above benchmark AND posted in the last N days. Reach floor is
    # lower than the all-time view (1K vs. the 5K the older code used)
    # because recent posts haven't had time to accumulate reach — a
    # fresh post 1.5× above its platform benchmark IS news, even if it
    # only has 2K reach yet.
    for p in top_posts[:12]:
        if "youtube" in p.platform.lower():
            continue
        if p.platform.lower() in organic_by_design_for:
            continue
        if not _is_fresh(p):
            continue
        bench_er = _post_platform_benchmark(p.platform).er
        if bench_er > 0 and p.reach >= 1_000 and p.er >= bench_er * 1.5:
            win_candidates.append(("post", p, p.er / bench_er))

    if win_candidates:
        kind, obj, mult = max(win_candidates, key=lambda x: x[2])
        if kind == "post":
            quote = obj.quote[:80] + ("…" if len(obj.quote) > 80 else "")  # type: ignore[union-attr]
            callouts.append({
                "tag": "WIN",
                "kind": "pos",
                "headline": f"{obj.platform} post at {obj.er:.1f}% ER — {mult:.1f}× the benchmark.",  # type: ignore[union-attr]
                "body": (
                    f"\"{quote}\" — {_short(obj.reach)} reach, "  # type: ignore[union-attr]
                    f"{_short(obj.eng)} engagements ({obj.organic}% organic). "  # type: ignore[union-attr]
                    f"Strongest single asset on the campaign and well clear of the {obj.platform} benchmark. "  # type: ignore[union-attr]
                    f"Feature it in the partner update."
                ),
                # Drop format from meta — "TikTok · Reels/Shorts" reads redundant
                # (TikTok IS short-form), and partner + platform carries the context.
                "meta": f"{summary.partner} · {obj.platform}",  # type: ignore[union-attr]
            })
        else:
            callouts.append({
                "tag": "WIN",
                "kind": "pos",
                "headline": f"{obj.name} at {obj.er:.1f}% ER — {mult:.1f}× the benchmark.",  # type: ignore[union-attr]
                "body": (
                    f"{_short(obj.impressions)} impressions, {_short(obj.eng)} engagements at "  # type: ignore[union-attr]
                    f"{obj.er:.1f}% ER vs. the {obj.bench.er:.1f}% {obj.name} FOS benchmark. "  # type: ignore[union-attr]
                    f"Strongest channel this campaign — feature in the partner update."
                ),
                "meta": f"{summary.partner} · {obj.name}",  # type: ignore[union-attr]
            })

    # ---------- OPPORTUNITY: audience-resonance signal (high % organic on volume) ----------
    # The algorithm is rewarding this content — high organic delivery on real
    # volume means the platform's recommendation surface is picking it up
    # without us paying for the reach.
    #
    # Threshold: ≥60% organic share AND ≥100K total impressions on the channel
    # (anything below 100K is too small to read as a real signal).
    #
    # LinkedIn special case: it's always organic for us (paid is too expensive),
    # so being 100% organic isn't news. Only surface LinkedIn when a single
    # post has broken out (250K+ impressions on that post).
    max_li_post = max(
        (p.reach for p in top_posts if p.platform.lower() == "linkedin"),
        default=0,
    )
    org_candidates = []
    for c in channels:
        if c.impressions < 100_000 or c.organic_impressions <= 0:
            continue
        if c.name.lower() == "linkedin" and max_li_post < 250_000:
            continue  # No standout LinkedIn post — skip the channel callout.
        # Skip channels the client mandates organic-only on — being 100%
        # organic there is a contract requirement, not an algorithmic
        # signal worth celebrating (e.g. E*TRADE forbids TikTok boosting).
        if c.name.lower() in organic_by_design_for:
            continue
        org_pct = c.organic_impressions / c.impressions * 100
        if org_pct >= 60:
            org_candidates.append((c, org_pct))

    if org_candidates:
        # Rank by absolute organic reach — the channel where the audience is most
        # actively engaging with our content.
        c, org_pct = max(org_candidates, key=lambda x: x[0].organic_impressions)
        callouts.append({
            "tag": "OPPORTUNITY",
            "kind": "info",
            "headline": f"{c.name} resonating — {org_pct:.0f}% of delivery is organic.",
            "body": (
                f"{_short(c.organic_impressions)} organic impressions on {c.name} "
                f"({c.er:.1f}% ER) — the algorithm is rewarding this content. "
                f"Strong signal that the creative direction and cadence fit {c.name}; "
                f"lean into more of the same."
            ),
            "meta": f"{summary.partner} · {c.name}",
        })

    # ---------- WATCH: budget risk (CPM ≥ 2× benchmark) or pacing miss ----------
    # Pacing = a forecast: at the current delivery rate, will we hit goal?
    # `pacing_forecast()` gives us projected_final, gap_to_goal, and the
    # daily-rate lift required to recover. All headlines below speak in
    # forecast terms ("projected to deliver X% of goal") rather than the
    # old static framing ("N% behind pacing").
    forecast = pacing_forecast(
        summary.impressions.delivered,
        summary.impressions.goal,
        summary.elapsed_pct,
        summary.days_left,
    )
    pacing_ratio = forecast["projected_pct"]  # kept for older threshold checks below
    # Tighter threshold: only flag CPM when it's at least 2× the FOS benchmark —
    # that's the level where budget can genuinely get blown.
    over_bench = [c for c in channels if c.bench.cpm > 0 and c.cpm >= c.bench.cpm * 2.0]

    # Spend / delivery progress as a 0-100 share of goal
    impr_pct = (
        (summary.impressions.delivered / summary.impressions.goal * 100)
        if summary.impressions.goal else 0
    )
    budget_pct = (
        (summary.budget.delivered / summary.budget.goal * 100)
        if summary.budget.goal else 0
    )

    # Pacing WATCH fires when the FORECAST falls below 85% of goal — i.e. at
    # the current daily delivery rate, we'd land 15%+ short by flight end.
    # 85% mirrors the existing "At Risk / Behind Pace" status threshold so
    # the callout matches what the status badge shows.
    if summary.elapsed_pct >= 25 and forecast["is_behind"] and forecast["projected_pct"] < 0.85:
        proj_pct_int = int(round(forecast["projected_pct"] * 100))
        # Build a "what it takes" sentence using the daily-rate lift.
        lift = forecast["pace_multiplier_needed"]
        if forecast["current_daily_rate"] > 0 and lift > 1:
            lift_phrase = (
                f"Need to deliver {_short(forecast['required_daily_rate'])} impr/day "
                f"({lift:.1f}× the current {_short(forecast['current_daily_rate'])}/day) "
                f"to hit goal."
            )
        else:
            lift_phrase = f"Need to ramp delivery significantly to hit the {_short(summary.impressions.goal)} goal."
        callouts.append({
            "tag": "WATCH",
            "kind": "warn",
            "headline": (
                f"On pace for {proj_pct_int}% of goal "
                f"({_short(forecast['projected_final'])} of {_short(summary.impressions.goal)}) "
                f"with {summary.days_left} days left."
            ),
            "body": (
                f"At the current rate the campaign will fall ~{_short(forecast['gap_to_goal'])} impressions "
                f"short of the {_short(summary.impressions.goal)} goal. "
                f"{lift_phrase} "
                f"Optimize the highest-efficiency channels or extend the flight before launch slots disappear."
            ),
            "meta": f"{summary.partner} · Pacing",
        })
    # NEW — budget-surplus watch. End-of-flight + impressions almost / over
    # delivered + meaningful budget unspent. Action: pause boosting once goal
    # is reached to bank the surplus instead of overspending into surplus.
    elif (
        summary.elapsed_pct >= 75
        and impr_pct >= 85
        and budget_pct + 10 < impr_pct   # at least 10 pp gap between impressions% and budget%
        and (summary.budget.goal - summary.budget.delivered) > 500  # > $500 leftover to be worth flagging
    ):
        budget_remaining = summary.budget.goal - summary.budget.delivered
        budget_remaining_pct = 100 - budget_pct
        impr_gap = max(0, summary.impressions.goal - summary.impressions.delivered)
        gap_phrase = (
            f"only {_short(impr_gap)} impressions left to hit goal"
            if impr_gap > 0
            else f"already {impr_pct - 100:.0f}% past the goal"
        )
        callouts.append({
            "tag": "WATCH",
            "kind": "warn",
            "headline": (
                f"On pace to over-deliver — ${_short(budget_remaining)} ({budget_remaining_pct:.0f}%) "
                f"of budget unspent with {summary.days_left} days left."
            ),
            "body": (
                f"Impressions are {impr_pct:.0f}% delivered while only {budget_pct:.0f}% of budget has been spent — "
                f"{gap_phrase}. Pause boosting on the lowest-performing cutdowns once the impression goal hits "
                f"to bank the surplus instead of overspending into already-delivered territory."
            ),
            "meta": f"{summary.partner} · Budget surplus",
        })
    elif summary.type == "brandx":
        # BrandX-specific per-platform CPM WATCH. Blended CPM hides where the
        # money is leaking — operators need to know WHICH platforms are
        # over-spending so they can reallocate. Fires for each channel that's
        # delivering at ≥ 1.5× its BrandX platform benchmark (FOS Paid Social
        # Benchmarks workbook). Multiple platforms can fire individually.
        for ch in channels:
            if not ch.cpm or ch.cpm <= 0:
                continue
            if (ch.impressions or 0) < 10_000:
                continue  # Volume floor — small samples drift too easily
            # Match the channel's platform to the BrandX benchmark dict.
            key = ch.name.lower().replace(" ", "_")
            bx_bench = BRANDX_BENCHMARK_CPM_BY_PLATFORM.get(key)
            if bx_bench is None:
                # Try a camelCased variant (e.g. "youtube_shorts" → "youtube_shorts" already).
                continue
            if ch.cpm >= bx_bench * 1.5:
                mult = ch.cpm / bx_bench
                callouts.append({
                    "tag": "WATCH",
                    "kind": "warn",
                    "headline": (
                        f"{ch.name} CPM at ${ch.cpm:.2f} — {mult:.1f}× the BrandX benchmark."
                    ),
                    "body": (
                        f"${ch.cpm:.2f} CPM vs. ${bx_bench:.2f} BrandX {ch.name} benchmark "
                        f"on {_short(ch.impressions)} paid impressions. {ch.name} is paying a premium — "
                        f"reallocate spend to lower-CPM platforms in this campaign, tighten targeting, "
                        f"or swap the worst-performing creative on this channel."
                    ),
                    "meta": f"{summary.partner} · {ch.name}",
                })
    elif over_bench:
        worst = max(over_bench, key=lambda c: c.cpm / max(c.bench.cpm, 0.01))
        mult = worst.cpm / worst.bench.cpm
        callouts.append({
            "tag": "WATCH",
            "kind": "warn",
            "headline": f"{worst.name} CPM at ${worst.cpm:.2f} — {mult:.1f}× the benchmark.",
            "body": (
                f"${worst.cpm:.2f} CPM vs. ${worst.bench.cpm:.2f} FOS benchmark. "
                f"At {mult:.1f}× over, this is on track to throw the campaign budget off. "
                f"Tighten targeting or pause the highest-CPM creative now."
            ),
            "meta": f"{summary.partner} · {worst.name}",
        })

    # ---------- WATCH (independent): campaign-average ER below 1% ----------
    # Fires regardless of which pacing/CPM/surplus watch is already firing,
    # because under-1% ER is a structural performance issue (creative isn't
    # resonating) separate from pacing or budget. Surfaces as a second WATCH
    # when needed so the operator can re-evaluate spend allocation.
    #
    # Skip if the campaign has no real delivery yet — a 0% ER with 0
    # impressions just means it hasn't started. Skip entirely for BrandX
    # campaigns: low ER is by design (paid-performance optimizes for clicks /
    # CPM efficiency, not engagement).
    if (summary.type != "brandx"
            and summary.impressions.delivered >= 10_000
            and 0 < (summary.er or 0) < 1.0):
        callouts.append({
            "tag": "WATCH",
            "kind": "warn",
            "headline": f"Campaign averaging {summary.er:.2f}% ER — below the 1% floor.",
            "body": (
                f"{summary.er:.2f}% engagement rate across {_short(summary.impressions.delivered)} "
                f"impressions is under the 1% threshold FOS uses as a healthy baseline. "
                f"If engagement is a partner priority, consider reallocating spend toward the "
                f"highest-ER channels (or pausing the lowest-ER placements) before the next push."
            ),
            "meta": f"{summary.partner} · Engagement",
        })

    return callouts


def _short(n: float) -> str:
    n = int(n)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return str(n)


# Media Valuation Model (MVM) benchmark CPMs. These are the per-platform
# rates FOS uses to estimate campaign performance before launch — every
# proposal's projected impressions ÷ budget rolls up through these. Keeping
# the dashboard's actual delivered CPM compared against these benchmarks
# closes the loop: we can see in real time whether the campaigns are
# delivering at the rates the MVM promised.
MVM_BENCHMARK_CPM: dict[str, float] = {
    "youtube_infeed":   0.53,
    "youtube_preroll":  11.91,
    "youtube_shorts":   3.20,
    "instagram":        5.62,
    "facebook":         4.20,
    "x":                1.24,
    "tiktok":           2.24,
}

# BrandX (paid-social performance) benchmarks. Source: FOS Paid Social
# Benchmarks (Dashboard).xlsx — weighted averages across all BrandX
# campaigns. These drive the BrandX-only CPM WATCH callout and the
# per-channel benchmark display on the BrandX campaign page.
#
# Overall covers any BrandX campaign blend; by-objective splits help for
# CPC-optimized vs awareness-optimized runs. Per-platform numbers come from
# the "Dark Posts by Platform" tab and apply when comparing channel mix
# inside a BrandX campaign.
BRANDX_BENCHMARK_CPM_OVERALL = 3.34
BRANDX_BENCHMARK_CPM_BY_OBJECTIVE = {
    "impressions": 2.63,
    "clicks":      5.46,
}
BRANDX_BENCHMARK_CTR_OVERALL = 0.57   # percent (0.57%)
BRANDX_BENCHMARK_CTR_BY_OBJECTIVE = {
    "impressions": 0.04,
    "clicks":      2.14,
}
BRANDX_BENCHMARK_CPM_BY_PLATFORM = {
    "facebook":       3.34,
    "instagram":      2.93,
    "instagram_stories": 2.93,
    "tiktok":         2.75,
    "youtube_shorts": 3.26,
    "x":              0.68,
}
# Video Completion Rate benchmark for BrandX = % of paid impressions that
# watched the video to 100%. Sourced from FOS Paid Social Benchmarks
# workbook ("Dark Posts" overall — closest cohort to BrandX paid video).
# Computed as `sum(video_p100_watched_views) / sum(impressions_paid)`.
BRANDX_BENCHMARK_VCR_OVERALL = 0.36   # percent (0.36% of impressions reach 100% watch)
# Platforms to exclude from the portfolio CPM card. We never boost on these
# so a "CPM" line for them is misleading — they show up as $0/— and clutter
# the row.
PORTFOLIO_CPM_EXCLUDE = {"instagram_stories", "snapchat"}


def portfolio_cpm_by_channel(
    posts_by_campaign: dict[str, list[NormalizedPost]],
    campaigns: list[CampaignSummary],
) -> tuple[list[dict], float]:
    """Per-channel CPM rollup across all ACTIVE campaigns. Splits YouTube
    into in-feed / in-stream / shorts so the overview card shows the same
    granularity that per-campaign channels do.

    Returns (channel_list, portfolio_blend_cpm). Each list entry:
        { name, cpm, impressions, paid_impressions, pct_of_total, color }
    Sorted by total impressions desc. Wrapped campaigns excluded — Pulse
    Check + the overview CPM card are about live work.
    """
    from collections import defaultdict
    from app.parsers.base import PostFormat

    active_ids = {c.id for c in campaigns if getattr(c, "lifecycle", "active") == "active"}
    by_key: dict[str, dict] = defaultdict(lambda: {"impressions": 0, "paid_impressions": 0, "spend": 0.0})

    for cid, posts in posts_by_campaign.items():
        if cid not in active_ids:
            continue
        for p in posts:
            if p.platform is Platform.YOUTUBE:
                subtype = youtube_subtype_from_post(p)
                if subtype == "in-stream":
                    key = "youtube_preroll"
                elif subtype == "shorts" or p.post_format is PostFormat.REELS_SHORTS:
                    key = "youtube_shorts"
                else:
                    key = "youtube_infeed"
            elif p.platform is Platform.INSTAGRAM and p.post_format is PostFormat.STORY:
                key = "instagram_stories"
            else:
                key = p.platform.value

            by_key[key]["impressions"] += _pick_impressions(p) or 0
            by_key[key]["paid_impressions"] += p.impressions_paid or 0
            by_key[key]["spend"] += p.ad_spend or 0

    total_impr = sum(v["impressions"] for v in by_key.values())
    total_spend = sum(v["spend"] for v in by_key.values())
    total_paid_impr = sum(v["paid_impressions"] for v in by_key.values())

    out: list[dict] = []
    for key, agg in by_key.items():
        if key == "unknown":
            continue
        if key in PORTFOLIO_CPM_EXCLUDE:
            # We don't boost on these platforms — a CPM line for them is
            # meaningless. Drop entirely to keep the card focused.
            continue
        name, _italic, _bench, color = _channel_display(key)
        cpm = (agg["spend"] / agg["paid_impressions"] * 1000) if agg["paid_impressions"] else 0.0
        mvm = MVM_BENCHMARK_CPM.get(key)
        delta_pct = None
        if mvm is not None and mvm > 0 and cpm > 0:
            # Negative delta = under the MVM benchmark (good, more efficient).
            # Positive = over the benchmark (less efficient than projected).
            delta_pct = round((cpm - mvm) / mvm * 100, 1)
        out.append({
            "name": name,
            "cpm": round(cpm, 2),
            "impressions": int(agg["impressions"]),
            "paid_impressions": int(agg["paid_impressions"]),
            "pct_of_total": round(agg["impressions"] / total_impr * 100, 1) if total_impr else 0.0,
            "mvm_cpm": mvm,                    # benchmark from the Media Valuation Model
            "mvm_delta_pct": delta_pct,        # actual vs MVM, % (negative = under-spending)
            "color": color,
        })

    out.sort(key=lambda x: x["impressions"], reverse=True)
    blend = round((total_spend / total_paid_impr * 1000) if total_paid_impr else 0.0, 2)
    return out, blend


def _channel_display(key: str) -> tuple[str, str, ChannelBenchmark, str]:
    """Map an internal channel key (with YouTube subtype) to display info + benchmark.

    All benchmarks are sourced from PLATFORM_BENCHMARKS so there's one place to
    maintain them.
    """
    if key == "youtube_infeed":
        return ("YouTube In-feed", "YouTube In-feed", PLATFORM_BENCHMARKS["youtube_infeed"], "#E00922")
    if key == "youtube_preroll":
        return ("YouTube Pre-roll", "YouTube Pre-roll", PLATFORM_BENCHMARKS["youtube_preroll"], "#B0061B")
    if key == "youtube_shorts":
        return ("YouTube Shorts", "YouTube Shorts", PLATFORM_BENCHMARKS["youtube_shorts"], "#FF0033")
    if key == "instagram_stories":
        return ("Instagram Stories", "Instagram Stories", PLATFORM_BENCHMARKS["instagram_stories"], "#C13584")
    return (
        PLATFORM_DISPLAY.get(key, key.title()),
        PLATFORM_ITALIC.get(key, key.title()),
        PLATFORM_BENCHMARKS.get(key, ChannelBenchmark(er=0.0, cpm=0.0)),
        PLATFORM_COLORS.get(key, "#666666"),
    )


def aggregate_portfolio_signals(campaigns: list[CampaignSummary]) -> list[dict]:
    """Pick the most impactful WIN/OPPORTUNITY/WATCH across active campaigns
    for the overview's Pulse Check strip. Wrapped campaigns are excluded —
    they live in their own Recently Wrapped section and shouldn't compete for
    Pulse Check slots with live work.

    WATCH rules:
      • Every behind-pace campaign gets its own pacing WATCH in the Pulse
        Check (multiple WATCH tiles will render when ≥2 campaigns are
        behind, so partners can see at-a-glance which ones need attention).
      • The best non-pacing WATCH (e.g. budget surplus, CPM blow-up, low-ER)
        is also surfaced as a single additional tile so pacing doesn't crowd
        out the other kinds of trouble.
    """
    import re

    # Collect all callouts from ACTIVE campaigns, tagged with campaign id.
    pool: dict[str, list[dict]] = {"WIN": [], "OPPORTUNITY": [], "WATCH": []}
    for c in campaigns:
        if getattr(c, "lifecycle", "active") != "active":
            continue
        for co in (c.callouts or []):
            tag = co.get("tag")
            if tag in pool:
                pool[tag].append({**co, "campaignId": c.id, "campaignPartner": c.partner})

    # WIN — biggest "N× benchmark" multiplier in headline (post or channel)
    def _win_score(co: dict) -> float:
        match = re.search(r"([\d.]+)\s*[×x]", co.get("headline", ""))
        return float(match.group(1)) if match else 0.0

    # OPPORTUNITY — highest "N% organic" share in headline
    def _opp_score(co: dict) -> float:
        match = re.search(r"(\d+)\s*%\s*of\s*delivery\s*is\s*organic", co.get("headline", ""))
        if match:
            return float(match.group(1))
        match = re.search(r"(\d+)\s*%", co.get("headline", ""))
        return float(match.group(1)) if match else 0.0

    def _is_pacing_watch(co: dict) -> bool:
        # Matches either the new framing ("On pace for N% of goal") or any
        # leftover instances of the old text ("N% behind pacing").
        h = co.get("headline", "")
        return bool(re.search(r"on pace for\s*\d+\s*%", h, re.I)) or bool(
            re.search(r"\d+\s*%\s*behind", h, re.I)
        )

    def _pacing_severity(co: dict) -> float:
        """Bigger number = bigger problem. For new format
        ("On pace for 56% of goal"), severity = 100 − projected_pct so
        the worst pacing case scores highest."""
        h = co.get("headline", "")
        m_new = re.search(r"on pace for\s*(\d+)\s*%", h, re.I)
        if m_new:
            return 100.0 - float(m_new.group(1))
        m_old = re.search(r"(\d+)\s*%\s*behind", h, re.I)
        return float(m_old.group(1)) if m_old else 0.0

    def _other_watch_score(co: dict) -> float:
        """Ranking for non-pacing WATCHes. CPM (N×) > anything else."""
        m_cpm = re.search(r"([\d.]+)\s*[×x]\s*the\s*benchmark", co.get("headline", ""))
        return float(m_cpm.group(1)) if m_cpm else 0.0

    out: list[dict] = []
    if pool["WIN"]:
        out.append(max(pool["WIN"], key=_win_score))
    if pool["OPPORTUNITY"]:
        out.append(max(pool["OPPORTUNITY"], key=_opp_score))

    # WATCH: surface EVERY behind-pace campaign + best non-pacing WATCH.
    pacing_watches = [co for co in pool["WATCH"] if _is_pacing_watch(co)]
    other_watches = [co for co in pool["WATCH"] if not _is_pacing_watch(co)]
    # Behind-pace WATCHes — sorted by severity (largest gap first)
    for co in sorted(pacing_watches, key=_pacing_severity, reverse=True):
        out.append(co)
    # Plus the best non-pacing WATCH (e.g. budget surplus, low-ER, CPM)
    if other_watches:
        out.append(max(other_watches, key=_other_watch_score))

    return out


def channel_rollups(posts_by_campaign: dict[str, list[NormalizedPost]]) -> list[Channel]:
    """Cross-campaign portfolio channel rollup. One row per platform.

    YouTube Pre-roll posts are excluded from this bucket entirely — they roll
    into their own per-campaign row, but the cross-campaign "YouTube" line
    shouldn't blend a watch-progress ER with in-feed/Shorts social ER.
    """
    by_platform = defaultdict(lambda: {"impressions": 0, "views": 0, "eng": 0, "spend": 0.0, "paid_impressions": 0})
    for posts in posts_by_campaign.values():
        for p in posts:
            if _is_yt_preroll_post(p):
                continue
            key = p.platform.value
            by_platform[key]["impressions"] += _pick_impressions(p) or 0
            by_platform[key]["views"] += _pick_views(p)
            by_platform[key]["eng"] += (p.engagements_total or p.engagements_paid or 0)
            by_platform[key]["spend"] += p.ad_spend or 0
            by_platform[key]["paid_impressions"] += p.impressions_paid or 0

    out: list[Channel] = []
    for platform_key, agg in by_platform.items():
        if platform_key == "unknown":
            continue
        impressions = int(agg["impressions"])
        eng = int(agg["eng"])
        spend = agg["spend"]
        paid = agg["paid_impressions"]
        er = (eng / impressions * 100) if impressions else 0.0
        cpm = (spend / paid * 1000) if paid else 0.0
        bench = PLATFORM_BENCHMARKS.get(platform_key, ChannelBenchmark(er=0.0, cpm=0.0))
        delta = round(((er - bench.er) / bench.er * 100) if bench.er else 0.0, 1)
        out.append(Channel(
            name=PLATFORM_DISPLAY.get(platform_key, platform_key.title()),
            italic=PLATFORM_ITALIC.get(platform_key, platform_key.title()),
            impressions=impressions, eng=eng,
            er=round(er, 2), cpm=round(cpm, 2),
            color=PLATFORM_COLORS.get(platform_key, "#666666"),
            delta=delta, bench=bench,
            views=int(agg["views"]),
        ))
    out.sort(key=lambda c: c.impressions, reverse=True)
    return out


# ---------- helpers ----------

def _pick_views(p: NormalizedPost) -> int:
    """Best-effort view count per post.

    On YouTube, views and impressions are wildly different — impressions count
    ad-renders, views count actual video playbacks. We want video plays here.
    On X, video views are also lower than impressions (a tweet impression doesn't
    require playback). On IG / TikTok / Snapchat, views ≈ impressions because
    those platforms autoplay video in-feed.

    Falls back from views_total → views_paid + views_organic → 0. Paid sources
    (Google Ads YT, Meta Ads) sometimes only set views_paid; combine paid +
    organic if total isn't directly available.
    """
    if p.views_total is not None:
        return p.views_total
    combined = (p.views_paid or 0) + (p.views_organic or 0)
    return combined


def _pick_impressions(p: NormalizedPost) -> int | None:
    """Best-effort impression count.

    For paid-only sources (Google Ads campaign reports, X Ads), `impressions_total`
    is never set — only `impressions_paid`. Fall back so those posts contribute to
    channel rollups instead of getting silently dropped.

    YouTube special case: prefer `impressions_paid` over `views_total`. On YT, an
    'impression' is an ad-render (how many times rendered); a 'view' is a video
    play. Impressions >> views and campaign goals track impressions. MS Checketts
    boosted Short has views_total=48K but impressions_paid=84K — the 84K is the
    correct campaign-pacing number.
    """
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


def _organic_pct(p: NormalizedPost) -> int:
    organic = p.views_organic or p.impressions_organic or p.reach_organic or 0
    total = p.views_total or p.impressions_total or p.reach_total or 0
    if total > 0 and organic > 0:
        return round(organic / total * 100)
    if p.boosting is Boosting.ORGANIC:
        return 100
    if p.boosting is Boosting.DARK:
        return 0
    return 0


def _elapsed_pct(start: date, end: date, today: date) -> float:
    if today <= start:
        return 0.0
    if today >= end:
        return 100.0
    total = (end - start).days
    elapsed = (today - start).days
    return (elapsed / total * 100) if total else 100.0


def _status(elapsed_pct: float, impressions_pct: float) -> tuple[StatusKind, str]:
    """Status is a forecast: at the current pace, will we hit the goal?

    Math: projected_final/goal == impressions_pct/elapsed_pct (algebraically
    equivalent). If the projection is ≥ 100% we're on track; under 85% means
    we'd need a meaningful course-correction to land at goal.
    """
    if elapsed_pct >= 100 and impressions_pct >= 100:
        return ("on", "Goal Exceeded" if impressions_pct > 105 else "Goal Hit")
    if elapsed_pct >= 100:
        return ("danger", "Goal Missed")
    # forecast_pct = projected_final / goal
    forecast_pct = (impressions_pct / elapsed_pct) if elapsed_pct else 1.0
    if forecast_pct >= 1.0:
        return ("on", "On Track")
    if forecast_pct >= 0.85:
        return ("warn", "At Risk")
    return ("danger", "Behind Pace")


def pacing_forecast(
    delivered: float,
    goal: float,
    elapsed_pct: float,
    days_left: int,
) -> dict:
    """Project end-of-flight delivery based on current pace.

    Returns a dict so callers can reach for whichever number drives the
    message they're constructing.

    Fields:
        projected_final         — int, projected total delivery at flight end
        projected_pct           — float (0.0–∞), projected_final / goal
        gap_to_goal             — int, max(0, goal − projected_final)
        is_behind               — bool, True if projected_pct < 0.95
        is_ahead                — bool, True if projected_pct > 1.05
        current_daily_rate      — int, delivered / days_elapsed
        required_daily_rate     — int, (goal − delivered) / days_left
        pace_multiplier_needed  — float, required / current (1.0 = on pace)
    """
    out = {
        "projected_final": int(delivered),
        "projected_pct": 1.0,
        "gap_to_goal": 0,
        "is_behind": False,
        "is_ahead": False,
        "current_daily_rate": 0,
        "required_daily_rate": 0,
        "pace_multiplier_needed": 1.0,
    }
    if not goal or elapsed_pct <= 0:
        return out
    elapsed_frac = elapsed_pct / 100.0
    projected_final = int(delivered / elapsed_frac)
    projected_pct = projected_final / goal
    gap = max(0, int(goal - projected_final))
    # Days elapsed isn't a stored field; back it out from elapsed_pct + days_left.
    if elapsed_frac < 1.0 and days_left > 0:
        flight_total = days_left / (1 - elapsed_frac)
        days_elapsed = flight_total - days_left
    else:
        days_elapsed = 1
    days_elapsed = max(1, days_elapsed)
    current_daily_rate = delivered / days_elapsed
    required_daily_rate = ((goal - delivered) / days_left) if days_left > 0 else 0
    pace_mult = (required_daily_rate / current_daily_rate) if current_daily_rate > 0 else 1.0

    out.update(
        projected_final=projected_final,
        projected_pct=projected_pct,
        gap_to_goal=gap,
        is_behind=projected_pct < 0.95,
        is_ahead=projected_pct > 1.05,
        current_daily_rate=int(current_daily_rate),
        required_daily_rate=int(required_daily_rate),
        pace_multiplier_needed=pace_mult,
    )
    return out


def _flight_label(start: date, end: date) -> str:
    fmt = "%b %-d"
    if start.year == end.year:
        return f"{start.strftime(fmt)} — {end.strftime(fmt)}, {end.year}"
    return f"{start.strftime(fmt)}, {start.year} — {end.strftime(fmt)}, {end.year}"


def _group_impressions_by_platform(posts: list[NormalizedPost]) -> dict[str, int]:
    out: dict[str, int] = defaultdict(int)
    for p in posts:
        out[p.platform.value] += _pick_impressions(p) or 0
    return dict(out)


def _format_label(fmt_value: str) -> str:
    return {
        "reels_shorts":  "Reels/Shorts",
        "feed_video":    "Feed video",
        "youtube_long":  "Longform video",
        "static":        "Image post",
        "story":         "Story",
        "text":          "Text post",
    }.get(fmt_value, fmt_value.replace("_", " ").title())


def _truncate_quote(text: str, max_len: int = 100) -> str:
    text = " ".join(text.split())
    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit(" ", 1)[0] + "…"
