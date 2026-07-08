"""JSON contract between the Python data layer and the Pulse viewer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal  # noqa: F401  (used by Literal types below)


StatusKind = Literal["on", "warn", "watch", "danger"]
CampaignType = Literal["content", "social", "brandx"]
# brandx = paid-social performance campaigns. Optimized for clicks /
# efficiency (CPM, CPC, CTR) rather than engagement / organic reach.
# Lifecycle: "active" campaigns are still flighting, "wrapped" ones have ended
# and live in a separate sidebar/overview section.
CampaignLifecycle = Literal["active", "wrapped"]


@dataclass
class Goal:
    delivered: float
    goal: float


@dataclass
class CampaignSummary:
    id: str
    partner: str
    series: str
    series_italic: str
    type: CampaignType
    flight: str
    elapsed_pct: float
    days_left: int
    status: str
    status_kind: StatusKind
    impressions: Goal
    budget: Goal
    color: str
    lead_format: str
    top_channel: str
    er: float
    cpm: float
    episodes: int
    posts: int
    blurb: str
    # Total views across the campaign — universal "people who watched" metric.
    # Equals impressions on IG/TikTok/Snapchat (autoplay video) but is meaningfully
    # smaller than impressions on YouTube (ad-renders vs video plays) and X.
    views: int = 0
    # Actual total engagements across every post (matches the sum of the
    # per-episode engagement totals). The header KPI uses this directly instead
    # of the old impressions×ER approximation, which under/over-counted because
    # ER excludes YT pre-roll while impressions include it.
    engagements: int = 0
    # Optional Full-Episodes-vs-Cutdowns split for campaigns that run separate
    # impression / budget goals across the two content tiers (e.g. ADP).
    # When present, the campaign detail page renders two side-by-side cards
    # above the per-episode breakdown. List of:
    #   {label: str, impressions: {delivered, goal}, budget: {delivered, goal}, posts: int}
    goal_split: list = field(default_factory=list)
    # Benchmark category from FOS Social Benchmarks (e.g., "Original Content",
    # "Custom Social - Non-Franchise"). Used to compare ER vs the right cohort.
    benchmark_category: str = ""
    # Active vs wrapped (display in different sidebar/overview sections).
    lifecycle: CampaignLifecycle = "active"
    # Per-campaign breakdowns (used by campaign detail page)
    channels: list = field(default_factory=list)            # list[Channel] for THIS campaign — YouTube split by subtype
    top_posts: list = field(default_factory=list)            # list[TopPost] ranked by ER, this campaign only
    top_posts_organic: list = field(default_factory=list)    # list[TopPostOrganic] ranked by organic reach, this campaign only
    callouts: list = field(default_factory=list)             # auto-generated WIN/OPPORTUNITY/WATCH for this campaign's What We're Seeing
    # BrandX-only fields. Objective drives which CPM/CTR benchmark applies
    # (impressions/awareness uses a lower CPM bar, clicks tolerates higher CPM
    # because click-optimized inventory costs more). `secondary_objective`
    # tracks the other metric the team is watching (e.g. E*TRADE awareness
    # campaigns are primarily measured on impressions but clicks matter too).
    brandx_objective: str = ""           # awareness | clicks | app_install | etc.
    brandx_secondary_objective: str = ""
    # Pacing-by-component buckets (Spectrum). Each entry aggregates one or more
    # episode components and tracks delivery vs its own impression goal:
    #   {label: str, impressions: {delivered: int, goal: int}}
    # Rendered as a dedicated "pacing by component" section on the campaign page.
    pacing_components: list = field(default_factory=list)
    # Freshness timestamps shown in the campaign header (ISO 8601 UTC, "" when
    # n/a). Split by source so each reflects when THAT data actually changed:
    #   last_updated_ms      — Measure Studio pull time (= refresh time; MS is
    #                          re-fetched every run). Empty when no MS group.
    #   last_updated_exports — git commit time of the campaign's uploaded
    #                          ad-platform exports; only moves on a real upload.
    last_updated_ms: str = ""
    last_updated_exports: str = ""


@dataclass
class TopPost:
    id: int | str
    rank: int
    partner: str
    platform: str
    format: str
    quote: str
    er: float
    eng: int
    reach: int
    organic: int
    metric: str
    insight: str
    url: str | None = None
    posted_at: str | None = None   # ISO datetime — used for WIN-callout recency filter


@dataclass
class HeroPost:
    partner: str
    platform: str
    format: str
    quote: str
    attribution: str
    er: str
    eng: str
    reach: str
    organic: str


@dataclass
class TopPostOrganic:
    id: str
    rank: int
    partner: str
    platform: str
    format: str
    quote: str
    organic_reach: int
    total_reach: int
    organic_pct: float
    er: float
    insight: str
    url: str | None = None


@dataclass
class ChannelBenchmark:
    er: float
    cpm: float


@dataclass
class Channel:
    name: str
    italic: str
    impressions: int
    eng: int
    er: float
    cpm: float
    color: str
    delta: float
    bench: ChannelBenchmark
    organic_impressions: int = 0
    views: int = 0  # video playback count (≈ impressions on IG/TikTok, much lower on YT/X)


@dataclass
class DataSource:
    name: str
    date: str
    stale: bool


SignalKind = Literal["win", "watch", "opportunity"]


@dataclass
class Signal:
    kind: SignalKind
    title: str
    body: str


@dataclass
class PulsePayload:
    campaigns: list[CampaignSummary]
    top_posts: list[TopPost]
    hero_post: HeroPost | None
    top_posts_organic: list[TopPostOrganic]
    channels: list[Channel]
    sources: list[DataSource]
    signals: list[Signal]
    episodes_by_campaign: dict                 # passthrough from sample
    ub_components: list                        # passthrough from sample
    data_archive: list = field(default_factory=list)  # source-file manifest (Data Archive page)
    posts_by_campaign: dict = field(default_factory=dict)  # per-post rows (social campaigns)
    # Average CPM by channel (active campaigns only) — drives the "Average
    # CPM by channel" card on the overview. Splits YouTube into in-feed /
    # in-stream / shorts. Each entry: { name, cpm, impressions, paid_impressions,
    # pct_of_total, color }. Plus a portfolio-blend CPM in `portfolio_cpm_blend`.
    portfolio_cpm_by_channel: list = field(default_factory=list)
    portfolio_cpm_blend: float = 0.0
