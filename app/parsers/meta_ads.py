"""Meta Ads Manager export parser.

Used when we run dark posts as paid media on Meta — Measure Studio can't see
dark posts, so the spend/impressions/engagements live only in this export.

Required columns (Meta Ads Manager → Export columns):

    Campaign name            — required. We parse `(IG)` / `(FB)` suffix to
                               infer platform. Without a suffix, defaults to
                               Instagram (Meta's typical primary placement).
    Impressions              — required. Total paid impressions.
    Reach                    — required. Unique users reached.
    Post engagements         — required. Total post engagements (Meta's
                               equivalent of likes + comments + shares + saves
                               + clicks-on-the-post — NOT clicks to a landing
                               page).
    Amount spent (USD)       — required. Total media spend.
    Reporting starts / ends  — optional. Used only for display.
    Campaign delivery        — optional. Used as a status hint.

The parser tolerates the Meta export's quoted column names. Output:

  • platform = INSTAGRAM if name ends in `(IG)`, FACEBOOK if `(FB)`,
    else INSTAGRAM as default.
  • source = META_ADS, boosting = DARK (these are paid dark posts).
  • impressions_paid, views_paid (=impressions for video posts; Meta doesn't
    split views from impressions on this report), engagements_paid, ad_spend.
  • er = engagements / impressions (Meta doesn't expose a separate ER column).
"""

from __future__ import annotations

import io
import re
from typing import IO, Any

import pandas as pd

from app.parsers.base import (
    Boosting,
    NormalizedPost,
    ParseResult,
    Platform,
    PostFormat,
    Source,
)


# Required columns the parser expects. If any are missing, we return an error.
# "Post engagements" is optional — Reach-objective exports don't include it.
# In that case we fall back to "Clicks (all)" as the engagement count.
REQUIRED_COLS = {
    "Campaign name",
    "Impressions",
    "Reach",
    "Amount spent (USD)",
}


def parse(file: IO[bytes] | str | bytes) -> ParseResult:
    df = _read_csv(file)
    if df is None or df.empty:
        return ParseResult(
            rows=[],
            detected_source=Source.META_ADS,
            errors=["Could not parse Meta Ads export — file empty or unreadable."],
        )

    # Different export levels name the row column differently: ad-level uses
    # "Ad name" (e.g. Sport Clips Off the Pitch), platform-broken-out ad-set
    # exports use "Ad set name". Normalize any of them to "Campaign name".
    if "Campaign name" not in df.columns:
        for _alt in ("Ad name", "Ad set name"):
            if _alt in df.columns:
                df = df.rename(columns={_alt: "Campaign name"})
                break

    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        return ParseResult(
            rows=[],
            detected_source=Source.META_ADS,
            errors=[
                f"Meta Ads export is missing required columns: {sorted(missing)}. "
                f"Got: {list(df.columns)}"
            ],
        )

    rows: list[NormalizedPost] = []
    for raw in df.to_dict("records"):
        campaign_name = (raw.get("Campaign name") or "").strip()
        if not campaign_name:
            continue

        impressions = _to_int(raw.get("Impressions"))
        reach = _to_int(raw.get("Reach"))
        # Engagements: prefer "Post engagements" (engagement-objective exports),
        # fall back to "Clicks (all)" (reach-objective exports don't expose
        # post engagements). Returns None if neither is present.
        engagements = (
            _to_int(raw.get("Post engagements"))
            or _to_int(raw.get("Clicks (all)"))
        )
        spend = _to_float(raw.get("Amount spent (USD)"))

        # Skip truly empty rows (no impressions AND no spend)
        if not impressions and not spend:
            continue

        # Platform-broken-out exports carry an explicit "Platform" column
        # (Facebook / Instagram) — one row per platform per ad set. Prefer it
        # over guessing from the name suffix.
        plat_col = str(raw.get("Platform") or "").strip().lower()
        if plat_col == "facebook":
            platform = Platform.FACEBOOK
        elif plat_col == "instagram":
            platform = Platform.INSTAGRAM
        else:
            platform = _detect_platform(campaign_name)
        # With a platform split, two rows share the same ad-set name — make
        # the native id unique per platform so they stay distinct posts.
        post_id = f"{campaign_name} ({platform.value})" if plat_col else campaign_name

        er = None
        if engagements is not None and impressions:
            er = engagements / impressions  # store as 0.0–1.0 fraction

        post = NormalizedPost(
            source=Source.META_ADS,
            platform=platform,
            post_id_native=post_id,
            post_title=campaign_name,
            post_format=_detect_format(campaign_name),
            boosting=Boosting.DARK,  # Meta Ads = dark/paid by definition
            impressions_paid=impressions,
            impressions_total=impressions,  # paid is the total for dark posts
            reach_paid=reach,
            reach_total=reach,
            views_paid=impressions,  # Meta doesn't split views; videos in feed
            engagements_paid=engagements,
            engagements_total=engagements,
            ad_spend=spend,
            er=er,
            raw=raw,
        )
        rows.append(post)

    rows = _consolidate_placements(rows)
    return ParseResult(rows=rows, detected_source=Source.META_ADS)


def _consolidate_placements(rows: list[NormalizedPost]) -> list[NormalizedPost]:
    """Collapse placement/device-broken rows back into one post per ad+platform.

    Meta Ads Manager can export with a "Placement & Device" (or "Day")
    breakdown turned on, which splits a single creative into one row per
    placement/device combo (Facebook Reels, IG Feed, IG Stories, …) — most of
    them trivial slivers. That inflates the post count and litters the table.

    Every row already carries a `post_id_native` that encodes ad name +
    platform, so we group on it and sum the additive metrics. Groups of one
    (a normal, un-broken export) pass through unchanged — so this is a no-op
    for correctly-exported files and only kicks in when a breakdown was left on.

    Note: impressions / views / engagements / spend are additive and stay
    exact. Reach is summed too, which slightly over-counts unique reach across
    placements — there's no way to recover the de-duplicated figure from a
    broken export, and reach isn't a headline metric for these dark posts.
    """
    from collections import OrderedDict

    groups: "OrderedDict[str, list[NormalizedPost]]" = OrderedDict()
    for p in rows:
        groups.setdefault(p.post_id_native, []).append(p)

    out: list[NormalizedPost] = []
    for grp in groups.values():
        if len(grp) == 1:
            out.append(grp[0])
            continue

        def _sum(attr: str) -> int | float | None:
            vals = [getattr(g, attr) for g in grp]
            nonnull = [v for v in vals if v is not None]
            return sum(nonnull) if nonnull else None

        base = grp[0]
        base.impressions_paid = _sum("impressions_paid")
        base.impressions_total = _sum("impressions_total")
        base.reach_paid = _sum("reach_paid")
        base.reach_total = _sum("reach_total")
        base.views_paid = _sum("views_paid")
        base.engagements_paid = _sum("engagements_paid")
        base.engagements_total = _sum("engagements_total")
        base.ad_spend = _sum("ad_spend")
        impr = base.impressions_paid
        eng = base.engagements_paid
        base.er = (eng / impr) if (eng is not None and impr) else None
        out.append(base)

    return out


def _detect_platform(name: str) -> Platform:
    """Pull platform from `(IG)` / `(FB)` suffix in campaign name.

    Required naming convention for Meta exports:
      <Partner>_<Series>_<Component>_<Variant> (IG)
      <Partner>_<Series>_<Component>_<Variant> (FB)

    Without a suffix, defaults to Instagram (Meta's typical primary placement).
    """
    n = name.strip()
    if n.endswith("(FB)") or " (Facebook)" in n.lower() or "_fb" in n.lower():
        return Platform.FACEBOOK
    if n.endswith("(IG)") or " (Instagram)" in n.lower() or "_ig" in n.lower():
        return Platform.INSTAGRAM
    return Platform.INSTAGRAM  # safe default


def _detect_format(name: str) -> PostFormat:
    """Best-effort format detection from naming convention. Story/Reel hints
    if present, else default to feed video (Meta dark posts are usually video)."""
    lower = name.lower()
    if "story" in lower or "stories" in lower:
        return PostFormat.STORY
    if "reel" in lower:
        return PostFormat.REELS_SHORTS
    if "static" in lower or "image" in lower or "carousel" in lower:
        return PostFormat.STATIC
    return PostFormat.FEED_VIDEO


def _read_csv(file: IO[bytes] | str | bytes) -> pd.DataFrame | None:
    # Shared reader also handles exports saved as Excel (.xlsx) but uploaded
    # with a .csv name — a common Ads Manager mistake.
    from app.parsers.base import read_ads_table
    return read_ads_table(file)


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    s = str(value).strip()
    if s in ("", "--", " --", "Using ad set budget"):
        return None
    try:
        return int(float(s.replace(",", "")))
    except (ValueError, TypeError):
        return None


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    s = str(value).strip()
    if s in ("", "--", " --", "Using ad set budget"):
        return None
    try:
        return float(s.replace(",", "").replace("$", ""))
    except (ValueError, TypeError):
        return None
