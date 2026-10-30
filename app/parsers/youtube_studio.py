"""YouTube Studio — organic content export parser.

For channels Measure Studio can't connect (e.g. the FOS Tonight YouTube
account), the team exports the per-video table straight from YouTube Studio
(Analytics → Content → export) and uploads it. One row per video, plus a
leading "Total" row that we skip.

Columns used:
  - Content                  — YouTube video ID
  - Video title
  - Post Link                — watch / shorts URL (also a fallback source of the ID)
  - Video publish time       — e.g. "Oct 9, 2026"
  - Views                    — video plays
  - Thumbnail impressions    — the organic impression count (same convention as
                               config/youtube_organic_impressions.csv)
  - Engagements, Likes, Shares, Comments added — engagement counts

Every row resolves to an organic YouTube NormalizedPost: no paid delivery, no
spend. Impressions are Thumbnail impressions; views are plays.
"""

from __future__ import annotations

import io
import re
from datetime import datetime
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

REQUIRED_COLUMNS = ("Content", "Views", "Thumbnail impressions")

_VIDEO_ID_RE = re.compile(r"(?:v=|/shorts/|youtu\.be/)([A-Za-z0-9_-]{11})")


def parse(file: IO[bytes] | str | bytes) -> ParseResult:
    df = _read_table(file)
    if df is None or df.empty:
        return ParseResult(
            rows=[],
            detected_source=Source.YOUTUBE_ORGANIC,
            errors=["Could not parse YouTube Studio export"],
        )

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        return ParseResult(
            rows=[],
            detected_source=Source.YOUTUBE_ORGANIC,
            errors=[f"Not a YouTube Studio content export (missing columns: {', '.join(missing)})"],
        )

    rows: list[NormalizedPost] = []
    for rec in df.to_dict("records"):
        content = str(rec.get("Content", "")).strip()
        if not content or content.lower() == "total":
            continue
        link = str(rec.get("Post Link", "")).strip() or None
        vid = content if re.fullmatch(r"[A-Za-z0-9_-]{11}", content) else _video_id(link)
        if not vid:
            continue
        url = link or f"https://www.youtube.com/watch?v={vid}"

        impressions = _to_int(rec.get("Thumbnail impressions"))
        views = _to_int(rec.get("Views"))
        engagements = _to_int(rec.get("Engagements"))
        is_short = "/shorts/" in url

        rows.append(NormalizedPost(
            source=Source.YOUTUBE_ORGANIC,
            platform=Platform.YOUTUBE,
            post_id_native=vid,
            post_url=url,
            post_title=str(rec.get("Video title", "")).strip() or None,
            posted_at=_parse_date(rec.get("Video publish time")),
            post_format=PostFormat.REELS_SHORTS if is_short else PostFormat.YOUTUBE_LONG,
            boosting=Boosting.ORGANIC,
            impressions_total=impressions,
            impressions_organic=impressions,
            views_total=views,
            views_organic=views,
            engagements_total=engagements,
            engagements_organic=engagements,
            er=(engagements / impressions) if engagements is not None and impressions else None,
            raw={k: v for k, v in rec.items() if v not in (None, "")},
        ))

    return ParseResult(rows=rows, detected_source=Source.YOUTUBE_ORGANIC)


def _read_table(file: IO[bytes] | str | bytes) -> pd.DataFrame | None:
    """Read the export as UTF-8 or UTF-16 text; comma- or tab-delimited."""
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

    encoding = "utf-16" if data[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8-sig"
    try:
        text = data.decode(encoding, errors="replace")
    except Exception:
        return None

    first = text.splitlines()[0] if text.strip() else ""
    delimiter = "\t" if first.count("\t") >= 3 else ","
    try:
        return pd.read_csv(
            io.StringIO(text), dtype=str, keep_default_na=False,
            sep=delimiter, engine="python",
        )
    except Exception:
        return None


def _video_id(url: str | None) -> str | None:
    m = _VIDEO_ID_RE.search(url or "")
    return m.group(1) if m else None


def _to_int(value: Any) -> int | None:
    s = str(value if value is not None else "").replace(",", "").strip()
    if s in ("", "--"):
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def _parse_date(value: Any) -> datetime | None:
    s = str(value if value is not None else "").strip()
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None
