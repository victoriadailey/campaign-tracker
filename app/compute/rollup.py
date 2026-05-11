"""Aggregations: parsed posts → Pulse rollups."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from app.parsers import Boosting, NormalizedPost, Platform, Source
from app.parsers.google_ads_campaign import youtube_ad_subtype
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
    "youtube":   ChannelBenchmark(er=4.2, cpm=4.50),
    "instagram": ChannelBenchmark(er=1.8, cpm=5.10),
    "tiktok":    ChannelBenchmark(er=2.0, cpm=2.40),
    "linkedin":  ChannelBenchmark(er=3.5, cpm=0.0),
    "x":         ChannelBenchmark(er=1.1, cpm=1.10),
    "facebook":  ChannelBenchmark(er=1.2, cpm=4.80),
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


def rollup_campaign(
    config: CampaignConfig,
    posts: list[NormalizedPost],
    today: date | None = None,
) -> CampaignSummary:
    today = today or date.today()

    total_impressions = sum(_pick_impressions(p) or 0 for p in posts)
    total_engagements = sum(p.engagements_total or 0 for p in posts)
    total_spend = sum(p.ad_spend or 0 for p in posts)
    er = (total_engagements / total_impressions * 100) if total_impressions else 0.0
    paid_impressions = sum(p.impressions_paid or 0 for p in posts)
    cpm = (total_spend / paid_impressions * 1000) if paid_impressions else 0.0

    elapsed_pct = _elapsed_pct(config.flight_start, config.flight_end, today)
    days_left = max(0, (config.flight_end - today).days)
    impressions_pct = (total_impressions / config.impression_goal * 100) if config.impression_goal else 0.0
    status_kind, status_label = _status(elapsed_pct, impressions_pct)

    by_platform = _group_impressions_by_platform(posts)
    top_channel = max(by_platform.items(), key=lambda kv: kv[1])[0] if by_platform else "unknown"

    return CampaignSummary(
        id=config.id,
        partner=config.partner,
        series=config.series,
        series_italic=config.series_italic,
        type=config.type,  # type: ignore[arg-type]
        flight=_flight_label(config.flight_start, config.flight_end),
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
    )


def top_posts_by_er(
    posts_by_campaign: dict[str, list[NormalizedPost]],
    partners: dict[str, str],
    n: int = 8,
    min_views: int = 1000,
) -> list[TopPost]:
    candidates = []
    for campaign_id, posts in posts_by_campaign.items():
        for p in posts:
            views = p.views_total or p.impressions_total or 0
            if p.er is None or views < min_views:
                continue
            candidates.append((campaign_id, p))

    ranked = sorted(candidates, key=lambda x: x[1].er or 0, reverse=True)[:n]

    out: list[TopPost] = []
    for rank, (campaign_id, p) in enumerate(ranked, start=1):
        out.append(TopPost(
            id=p.post_id_native or f"post_{rank}",
            rank=rank,
            partner=partners.get(campaign_id, campaign_id),
            platform=PLATFORM_DISPLAY.get(p.platform.value, p.platform.value.title()),
            format=_format_label(p.post_format.value),
            quote=_truncate_quote(p.post_title or p.post_description or ""),
            er=round((p.er or 0) * 100 if (p.er or 0) <= 1.0 else (p.er or 0), 2),
            eng=p.engagements_total or 0,
            reach=p.views_total or p.reach_total or p.impressions_total or 0,
            organic=_organic_pct(p),
            metric="er",
            insight="",
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
            organic = p.views_organic or p.reach_organic or p.impressions_organic or 0
            total = p.views_total or p.reach_total or p.impressions_total or organic
            if organic < 1000:
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
            er=round((p.er or 0) * 100 if (p.er or 0) <= 1.0 else (p.er or 0), 2),
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
        "impressions": 0, "eng": 0, "spend": 0.0, "paid_impressions": 0
    })
    for p in posts:
        key = p.platform.value
        if p.platform is Platform.YOUTUBE:
            # Split YouTube into In-feed vs Pre-roll using the ad subtype
            if p.source is Source.GOOGLE_ADS_CAMPAIGN:
                subtype = youtube_ad_subtype(p.post_title or "")
                if subtype == "in-stream":
                    key = "youtube_preroll"
                elif subtype == "shorts":
                    key = "youtube_infeed"  # shorts roll up with in-feed for CPM purposes
                else:
                    key = "youtube_infeed"
            else:
                # MS organic / non-Google-Ads YT posts → in-feed bucket
                key = "youtube_infeed"
        by_key[key]["impressions"] += _pick_impressions(p) or 0
        by_key[key]["eng"] += p.engagements_total or 0
        by_key[key]["spend"] += p.ad_spend or 0
        by_key[key]["paid_impressions"] += p.impressions_paid or 0

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
        ))

    out.sort(key=lambda c: c.impressions, reverse=True)
    return out


def compute_campaign_callouts(
    summary: CampaignSummary,
    channels: list[Channel],
) -> list[dict]:
    """Produce 3 simple rule-based callouts (WIN / OPPORTUNITY / WATCH) for one campaign.

    Replaces the hardcoded mock callouts on the campaign detail page. As the team writes
    real callouts manually (or AI-assisted later), these become editable in admin.
    """
    callouts: list[dict] = []

    # ---------- WIN: best ER channel with non-trivial reach ----------
    eligible = [c for c in channels if c.impressions >= 10_000 and c.er > 0]
    if eligible:
        best = max(eligible, key=lambda c: c.er)
        callouts.append({
            "tag": "WIN",
            "kind": "pos",
            "headline": f"{best.name} leading at {best.er:.1f}% ER.",
            "body": (
                f"{_short(best.impressions)} impressions with {_short(best.eng)} engagements "
                f"({best.er:.1f}% ER) — strongest performer this campaign. "
                f"Worth featuring in the weekly partner update."
            ),
            "meta": f"{summary.partner} · {best.name}",
        })

    # ---------- OPPORTUNITY: largest organic-leaning channel or biggest reach driver ----------
    by_reach = sorted(channels, key=lambda c: c.impressions, reverse=True)
    if by_reach:
        top = by_reach[0]
        callouts.append({
            "tag": "OPPORTUNITY",
            "kind": "info",
            "headline": f"{top.name} is the top reach driver at {_short(top.impressions)} impressions.",
            "body": (
                f"{(top.impressions / max(summary.impressions.delivered, 1) * 100):.0f}% of campaign delivery "
                f"comes from {top.name} at ${top.cpm:.2f} CPM. "
                f"{'Lean in for catch-up pacing.' if summary.status_kind != 'on' else 'Continue the current allocation.'}"
            ),
            "meta": f"{summary.partner} · {top.name}",
        })

    # ---------- WATCH: pacing or CPM-over-benchmark issue ----------
    pacing_ratio = (summary.impressions.delivered / summary.impressions.goal * 100) / max(summary.elapsed_pct, 1) if summary.impressions.goal else 1.0
    over_bench = [c for c in channels if c.bench.cpm > 0 and c.cpm > c.bench.cpm * 1.2]
    if pacing_ratio < 0.85:
        gap = summary.impressions.goal - summary.impressions.delivered
        callouts.append({
            "tag": "WATCH",
            "kind": "warn",
            "headline": f"{(100 - pacing_ratio * 100):.0f}% behind impression pacing with {summary.days_left} days left.",
            "body": (
                f"{_short(gap)} impressions still needed to hit the {_short(summary.impressions.goal)} goal. "
                f"Current trajectory ends below target — consider reallocating budget to highest-efficiency channels."
            ),
            "meta": f"{summary.partner} · Pacing",
        })
    elif over_bench:
        worst = max(over_bench, key=lambda c: c.cpm / max(c.bench.cpm, 0.01))
        over_pct = (worst.cpm - worst.bench.cpm) / worst.bench.cpm * 100
        callouts.append({
            "tag": "WATCH",
            "kind": "warn",
            "headline": f"{worst.name} CPM is {over_pct:+.0f}% over benchmark.",
            "body": (
                f"${worst.cpm:.2f} CPM vs. ${worst.bench.cpm:.2f} benchmark. "
                f"Tighten targeting or pause under-performing creative."
            ),
            "meta": f"{summary.partner} · {worst.name}",
        })

    return callouts


def _short(n: float) -> str:
    n = int(n)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return str(n)


def _channel_display(key: str) -> tuple[str, str, ChannelBenchmark, str]:
    """Map an internal channel key (with YouTube subtype) to display info + benchmark."""
    # Default: platform-key lookup
    if key == "youtube_infeed":
        return ("YouTube In-feed", "In-feed", ChannelBenchmark(er=4.2, cpm=0.50), "#E00922")
    if key == "youtube_preroll":
        return ("YouTube Pre-roll", "Pre-roll", ChannelBenchmark(er=4.2, cpm=9.50), "#B0061B")
    return (
        PLATFORM_DISPLAY.get(key, key.title()),
        PLATFORM_ITALIC.get(key, key.title()),
        PLATFORM_BENCHMARKS.get(key, ChannelBenchmark(er=0.0, cpm=0.0)),
        PLATFORM_COLORS.get(key, "#666666"),
    )


def channel_rollups(posts_by_campaign: dict[str, list[NormalizedPost]]) -> list[Channel]:
    by_platform = defaultdict(lambda: {"impressions": 0, "eng": 0, "spend": 0.0, "paid_impressions": 0})
    for posts in posts_by_campaign.values():
        for p in posts:
            key = p.platform.value
            by_platform[key]["impressions"] += _pick_impressions(p) or 0
            by_platform[key]["eng"] += p.engagements_total or 0
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
        ))
    out.sort(key=lambda c: c.impressions, reverse=True)
    return out


# ---------- helpers ----------

def _pick_impressions(p: NormalizedPost) -> int | None:
    return p.impressions_total or p.views_total or p.reach_total


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
    if elapsed_pct >= 100 and impressions_pct >= 100:
        return ("on", "Goal Exceeded" if impressions_pct > 105 else "Goal Hit")
    if elapsed_pct >= 100:
        return ("danger", "Goal Missed")
    pacing_ratio = (impressions_pct / elapsed_pct) if elapsed_pct else 1.0
    if pacing_ratio >= 1.0:
        return ("on", "On Track")
    if pacing_ratio >= 0.85:
        return ("warn", "At Risk")
    return ("danger", "Behind Pace")


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
