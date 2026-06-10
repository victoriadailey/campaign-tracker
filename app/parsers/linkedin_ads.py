"""LinkedIn Ads Manager export parser.

LinkedIn Campaign Manager → "Ad Performance Report" CSV (UTF-16, tab-delimited).
First 4 lines are metadata (Report title, Report Start, Report End, Date
Generated), line 5 is blank, line 6 is the column header row, line 7+ is data.

Used when we run dark posts as paid media on LinkedIn — Measure Studio can't
see dark/Sponsored Updates, so spend/impressions/engagements live only in this
export.

Required columns the parser reads:

    Campaign Name                — required.
    Ad Name                      — used as post_title (more specific).
    Impressions                  — required. Total paid impressions.
    Total Spent                  — required. Total media spend (USD).
    Total Engagements            — required. LinkedIn's combined engagement count.
    Reach                        — optional. Unique users reached.
    Click URL                    — optional. Stored as post_url.
    Video Views                  — optional. Stored as views_paid for video ads.
    Ad Headline                  — optional. Used as fallback title.

All rows resolve to:
  • platform = LINKEDIN
  • source = LINKEDIN_ADS, boosting = DARK
  • impressions_paid, engagements_paid, ad_spend, er = eng/impr
"""

from __future__ import annotations

import io
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


# Required columns. If any are missing, we return an error.
REQUIRED_COLS = {
    "Campaign Name",
    "Impressions",
    "Total Spent",
}


def parse(file: IO[bytes] | str | bytes) -> ParseResult:
    df = _read_csv(file)
    if df is None or df.empty:
        return ParseResult(
            rows=[],
            detected_source=Source.LINKEDIN_ADS,
            errors=["Could not parse LinkedIn Ads export — file empty or unreadable."],
        )

    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        return ParseResult(
            rows=[],
            detected_source=Source.LINKEDIN_ADS,
            errors=[
                f"LinkedIn Ads export is missing required columns: {sorted(missing)}. "
                f"Got: {list(df.columns)[:20]}..."
            ],
        )

    rows: list[NormalizedPost] = []
    for raw in df.to_dict("records"):
        campaign_name = (raw.get("Campaign Name") or "").strip()
        if not campaign_name:
            continue

        impressions = _to_int(raw.get("Impressions"))
        spend = _to_float(raw.get("Total Spent"))
        engagements = _to_int(raw.get("Total Engagements"))
        reach = _to_int(raw.get("Reach"))
        video_views = _to_int(raw.get("Video Views"))

        # Skip truly empty rows
        if not impressions and not spend:
            continue

        # Title preference: Ad Name > Ad Headline > Campaign Name
        post_title = (
            (raw.get("Ad Name") or "").strip()
            or (raw.get("Ad Headline") or "").strip()
            or campaign_name
        )

        # Engagement rate as 0-1 fraction
        er = None
        if engagements is not None and impressions:
            er = engagements / impressions

        # Native engagement-rate column comes as a percent string ("0.349%")
        # — only use it as a fallback if we couldn't compute from counts above.
        if er is None:
            er_raw = (raw.get("Engagement Rate") or "").strip().replace("%", "")
            try:
                er = float(er_raw) / 100.0 if er_raw else None
            except ValueError:
                er = None

        # Click URL: stored as post_url so the dashboard can link out.
        click_url = (raw.get("Click URL") or "").strip() or None

        rows.append(NormalizedPost(
            source=Source.LINKEDIN_ADS,
            platform=Platform.LINKEDIN,
            post_id_native=str(raw.get("Ad ID") or raw.get("Campaign ID") or campaign_name),
            post_title=post_title,
            post_url=click_url,
            post_format=_detect_format(post_title + " " + campaign_name),
            boosting=Boosting.DARK,
            impressions_paid=impressions,
            impressions_total=impressions,
            reach_paid=reach,
            reach_total=reach,
            views_paid=video_views or impressions,
            engagements_paid=engagements,
            engagements_total=engagements,
            ad_spend=spend,
            er=er,
            raw=raw,
        ))

    return ParseResult(rows=rows, detected_source=Source.LINKEDIN_ADS)


def _detect_format(text: str) -> PostFormat:
    """Best-effort format detection from naming."""
    lower = text.lower()
    if "story" in lower or "stories" in lower:
        return PostFormat.STORY
    if "reel" in lower:
        return PostFormat.REELS_SHORTS
    if "static" in lower or "image" in lower or "carousel" in lower:
        return PostFormat.STATIC
    return PostFormat.FEED_VIDEO


def _read_csv(file: IO[bytes] | str | bytes) -> pd.DataFrame | None:
    """Read LinkedIn Ads' UTF-16 tab-delimited CSV with 4-row metadata preamble.

    Falls back to UTF-8 + comma in case LinkedIn ever ships a saner format.
    """
    # Materialize as bytes so we can sniff encoding.
    if isinstance(file, str):
        try:
            with open(file, "rb") as f:
                data = f.read()
        except OSError:
            return None
    elif isinstance(file, bytes):
        data = file
    else:
        data = file.read()
        if isinstance(data, str):
            data = data.encode("utf-8")

    # UTF-16 has a 2-byte BOM; UTF-8 is BOM-tolerant.
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        encoding = "utf-16"
    else:
        encoding = "utf-8-sig"

    try:
        text = data.decode(encoding, errors="replace")
    except Exception:
        return None

    # The header is on line 5 (after 4 metadata lines + 1 blank). Skip first 5.
    # Sniff delimiter from the header row.
    lines = text.splitlines()
    if len(lines) < 6:
        return None
    header_line = lines[5]
    delimiter = "\t" if header_line.count("\t") >= 3 else ","

    try:
        return pd.read_csv(
            io.StringIO(text),
            skiprows=5,
            sep=delimiter,
            dtype=str,
            keep_default_na=False,
            engine="python",
        )
    except Exception:
        return None


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    s = str(value).strip()
    if s in ("", "--", " --", "-"):
        return None
    try:
        return int(float(s.replace(",", "")))
    except (ValueError, TypeError):
        return None


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    s = str(value).strip()
    if s in ("", "--", " --", "-"):
        return None
    try:
        return float(s.replace(",", "").replace("$", "").replace("%", ""))
    except (ValueError, TypeError):
        return None
