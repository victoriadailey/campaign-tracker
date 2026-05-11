"""JSON contract between the Python data layer and the Pulse viewer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal  # noqa: F401  (used by Literal types below)


StatusKind = Literal["on", "warn", "watch", "danger"]
CampaignType = Literal["content", "social"]


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
    # Per-campaign breakdowns (used by campaign detail page)
    channels: list = field(default_factory=list)            # list[Channel] for THIS campaign — YouTube split by subtype
    top_posts: list = field(default_factory=list)            # list[TopPost] ranked by ER, this campaign only
    top_posts_organic: list = field(default_factory=list)    # list[TopPostOrganic] ranked by organic reach, this campaign only
    callouts: list = field(default_factory=list)             # auto-generated WIN/OPPORTUNITY/WATCH for this campaign's What We're Seeing


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
