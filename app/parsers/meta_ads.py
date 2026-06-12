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

    # Ad-level exports name their row column "Ad name" instead of
    # "Campaign name" (e.g. Sport Clips Off the Pitch). Same shape otherwise —
    # normalize the column so both export levels parse.
    if "Campaign name" not in df.columns and "Ad name" in df.columns:
        df = df.rename(columns={"Ad name": "Campaign name"})

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

        platform = _detect_platform(campaign_name)

        er = None
        if engagements is not None and impressions:
            er = engagements / impressions  # store as 0.0–1.0 fraction

        post = NormalizedPost(
            source=Source.META_ADS,
            platform=platform,
            post_id_native=campaign_name,
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

    return ParseResult(rows=rows, detected_source=Source.META_ADS)


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
    if isinstance(file, bytes):
        file = io.BytesIO(file)
    try:
        return pd.read_csv(file, dtype=str, keep_default_na=False, low_memory=False)
    except Exception:
        return None


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
