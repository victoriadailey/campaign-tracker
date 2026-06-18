"""Google Ads — Campaign-level report parser.

Supports both column-name conventions for Impressions (`Impressions` or `Impr.`).
Google Ads' default campaign-report template no longer ships with an
impressions column, so make sure to **add it explicitly** when configuring the
export — see docs/OVERVIEW.md §2b. If neither column is present, we fall back
to deriving impressions from `TrueView views ÷ view rate` and emit a warning
so it's visible on the Data Archive page.

Required columns:
  - Campaign                           — campaign name
  - Impressions  *(or Impr.)*          — required; do not auto-derive when avail.
  - TrueView views                     — view count
  - Cost                               — total spend (USD)
  - Engagement rate                    — Google Ads' official ER (%)
  - Engagements                        — engagement count

Optional but useful:
  - TrueView view rate (In-stream | In-feed | Shorts)  — subtype detection
  - Avg. CPM, TrueView avg. CPV

All shapes resolve to the same NormalizedPost contract:
  - platform = YOUTUBE
  - views_paid = TrueView views
  - impressions_paid = explicit Impressions column (preferred) or derived
  - er = 'Engagement rate' as 0.0-1.0 decimal
  - engagements_paid = Engagements
  - ad_spend = Cost
  - post_format / subtype inferred from view rate columns first, then name
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

METADATA_ROWS = 2


def parse(file: IO[bytes] | str | bytes) -> ParseResult:
    df = _read_table(file)
    if df is None or df.empty:
        return ParseResult(
            rows=[],
            detected_source=Source.GOOGLE_ADS_CAMPAIGN,
            errors=["Could not parse Google Ads campaign report"],
        )

    if "Campaign" not in df.columns:
        return ParseResult(
            rows=[],
            detected_source=Source.GOOGLE_ADS_CAMPAIGN,
            errors=[f"Expected 'Campaign' column. Got: {list(df.columns)}"],
        )

    rows: list[NormalizedPost] = []
    derived_count = 0  # count rows where we had to derive impressions
    skipped_demand_gen: list[str] = []
    for raw in df.to_dict("records"):
        campaign_name = (raw.get("Campaign") or "").strip()
        # Skip empty rows, the "Total" footer row, and the " --" placeholder Google
        # Ads inserts for portfolio-budget summary lines.
        if not campaign_name or campaign_name.lower() == "total" or campaign_name == "--":
            continue

        # Demand Gen is not a YouTube/video placement and must NOT be counted in
        # these social/video campaign dashboards. Exclude it and flag it so the
        # operator knows it was dropped (rather than silently counted as video).
        campaign_type = (raw.get("Campaign type") or "").strip()
        if campaign_type.lower().replace(" ", "") == "demandgen":
            skipped_demand_gen.append(campaign_name)
            continue

        views_paid = _to_int(raw.get("TrueView views") or raw.get("YouTube public views"))
        # Impressions: prefer the explicit column. Accepts either "Impressions"
        # (Google Ads' newer column name) or "Impr." (older shorthand). If
        # neither is present, derive from views ÷ view rate and flag the row.
        impressions_paid = _to_int(raw.get("Impressions") or raw.get("Impr."))
        impressions_derived = False
        if impressions_paid is None and views_paid:
            impressions_paid = _derive_impressions(views_paid, raw)
            if impressions_paid is not None:
                impressions_derived = True
                derived_count += 1

        # Subtype: "cutdown"/"trailer" in the campaign name is an absolute
        # operator directive — those always run as Shorts, regardless of any
        # view-rate column. Otherwise prefer the view-rate signal (the column
        # that's populated tells us the actual served format), and fall back
        # to campaign-name parsing.
        name_lower = (campaign_name or "").lower()
        if "cutdown" in name_lower or "trailer" in name_lower:
            subtype = "shorts"
        else:
            subtype = _subtype_from_view_rates(raw) or _subtype_from_name(campaign_name)
        post_format = PostFormat.REELS_SHORTS if subtype == "shorts" else PostFormat.YOUTUBE_LONG

        watch_time = _to_float(raw.get("Watch time"))
        er_pct = _to_float(raw.get("Engagement rate"))  # arrives as e.g. 73.41
        post = NormalizedPost(
            source=Source.GOOGLE_ADS_CAMPAIGN,
            platform=Platform.YOUTUBE,
            post_id_native=campaign_name,
            post_title=campaign_name,
            post_format=post_format,
            boosting=Boosting.DARK,
            impressions_paid=impressions_paid,
            ad_spend=_to_float(raw.get("Cost")),
            cpm=_to_float(raw.get("Avg. CPM")),
            cpv=_to_float(raw.get("TrueView avg. CPV")),
            views_paid=views_paid,
            engagements_paid=_to_int(raw.get("Engagements")),
            # Store ER as a decimal fraction (0.0–1.0) to match the NormalizedPost
            # contract — downstream code multiplies by 100 when rendering.
            er=(er_pct / 100.0) if er_pct is not None else None,
            watch_time_min=(watch_time / 60.0) if watch_time is not None else None,
            raw=raw,
        )
        rows.append(post)

    warnings: list[str] = []
    if skipped_demand_gen:
        warnings.append(
            "⚠ Excluded {n} Demand Gen campaign(s) — Demand Gen is not a "
            "video/social post and is not counted in this campaign: {names}".format(
                n=len(skipped_demand_gen), names=", ".join(skipped_demand_gen)
            )
        )
    if derived_count > 0:
        warnings.append(
            f"Google Ads export missing 'Impressions' column — derived from "
            f"views ÷ view rate for {derived_count} row(s). Add an Impressions "
            f"column to the Google Ads campaign-report export to use the "
            f"explicit value."
        )
    return ParseResult(
        rows=rows,
        detected_source=Source.GOOGLE_ADS_CAMPAIGN,
        warnings=warnings,
    )


def _subtype_from_view_rates(raw: dict) -> str | None:
    """Pick the subtype from whichever 'TrueView view rate (X)' column is populated.

    This is more reliable than name parsing — the export only fills the rate column
    for the format the campaign actually ran as.
    """
    if _to_float(raw.get("TrueView view rate (In-stream)")) is not None:
        return "in-stream"
    if _to_float(raw.get("TrueView view rate (In-feed)")) is not None:
        return "in-feed"
    if _to_float(raw.get("TrueView view rate (Shorts)")) is not None:
        return "shorts"
    return None


def _subtype_from_name(name: str) -> str:
    """Subtype detection from campaign-name patterns.

    Rule (in priority order):
      1. Anything with "cutdown" / "trailer" in the name → ALWAYS Shorts.
         This is an explicit operator directive — cutdowns are produced as
         Shorts in production. Wins over any other suffix.
      2. Explicit (shorts) marker → Shorts.
      3. Explicit (in-feed) / _in-feed → In-feed.
      4. Explicit (pre-roll) / (preroll) / pre-roll / in-stream → Pre-roll.
      5. Default (full-episode campaigns without a format suffix) → In-feed.
    """
    lower = (name or "").lower()
    # Rule 1 — "cutdown" / "trailer" always means Shorts. Highest priority.
    if "cutdown" in lower or "trailer" in lower:
        return "shorts"
    if "(shorts)" in lower or " shorts" in lower:
        return "shorts"
    if "(in-feed)" in lower or "_in-feed" in lower or " in-feed" in lower:
        return "in-feed"
    if "(pre-roll)" in lower or "(preroll)" in lower or "pre-roll" in lower or "in-stream" in lower:
        return "in-stream"
    return "in-feed"


def _derive_impressions(views: int, raw: dict) -> int | None:
    """Impressions = views / view_rate. Uses whichever subtype rate column is set."""
    for col in (
        "TrueView view rate (In-stream)",
        "TrueView view rate (In-feed)",
        "TrueView view rate (Shorts)",
    ):
        rate_pct = _to_float(raw.get(col))
        if rate_pct and rate_pct > 0:
            return int(round(views / (rate_pct / 100.0)))
    return None


def _detect_youtube_format(name: str) -> PostFormat:
    """Public alias kept for backwards compat — used by older callers/tests."""
    return PostFormat.REELS_SHORTS if _subtype_from_name(name) == "shorts" else PostFormat.YOUTUBE_LONG


def youtube_ad_subtype(name: str) -> str:
    """Name-based subtype detection. Kept for backwards compatibility — prefer
    `youtube_subtype_from_post` when a NormalizedPost is available, since the
    view-rate signal is more reliable for cutdowns that don't carry a suffix."""
    return _subtype_from_name(name)


def youtube_subtype_from_post(p: NormalizedPost) -> str:
    """Best-effort YouTube ad subtype for a parsed post.

    Trusts the Google Ads view-rate signal (the column that's populated tells
    us how the ad actually served) and falls back to name-based parsing for
    legacy exports or non-Google-Ads YouTube posts.
    """
    if isinstance(p.raw, dict):
        from_view = _subtype_from_view_rates(p.raw)
        if from_view:
            return from_view
    return _subtype_from_name(p.post_title or "")


def _read_table(file: IO[bytes] | str | bytes) -> pd.DataFrame | None:
    """Read either a UTF-16 TSV (new export) or UTF-8 CSV (legacy export).

    Detects encoding via BOM. Detects delimiter by sniffing the first decoded
    header line for tabs.
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

    # Exported as Excel (.xlsx) but uploaded as .csv — read it as a workbook,
    # skipping the same metadata preamble rows the CSV path skips.
    if data[:4] == b"PK\x03\x04":
        try:
            return pd.read_excel(
                io.BytesIO(data), skiprows=METADATA_ROWS, dtype=str,
                keep_default_na=False, engine="openpyxl",
            )
        except Exception:
            return None

    # Encoding: UTF-16 if BOM, else UTF-8 with BOM-tolerant decode.
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        encoding = "utf-16"
    else:
        encoding = "utf-8-sig"

    try:
        text = data.decode(encoding, errors="replace")
    except Exception:
        return None

    # Delimiter: peek at the header row (3rd line, after 2 metadata rows).
    lines = text.splitlines()
    if len(lines) <= METADATA_ROWS:
        return None
    header = lines[METADATA_ROWS]
    delimiter = "\t" if header.count("\t") >= 3 else ","

    try:
        return pd.read_csv(
            io.StringIO(text),
            skiprows=METADATA_ROWS,
            dtype=str,
            keep_default_na=False,
            sep=delimiter,
            engine="python",  # python engine tolerates ragged TSV rows
        )
    except Exception:
        return None


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    s = str(value).strip()
    if s in ("", "--", " --"):
        return None
    try:
        return int(float(s.replace(",", "")))
    except (ValueError, TypeError):
        return None


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    s = str(value).strip()
    if s in ("", "--", " --"):
        return None
    try:
        return float(s.replace(",", "").replace("%", "").replace("$", ""))
    except (ValueError, TypeError):
        return None
