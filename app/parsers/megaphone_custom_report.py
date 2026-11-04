"""Parser for Megaphone **Custom report** exports (per-episode delivery).

This is the richest Megaphone export: one row per episode that delivered in the
report's date range, including the **back catalog** (older episodes still being
listened to — and, when Streaming Ad Insertion is on, still carrying the
dynamically-inserted ad read). Columns:

    EPISODE TITLE, PUBLISHED DATE, EPISODE DURATION, PODCAST TITLE,
    SPOTIFY AUDIENCE NETWORK OPT-IN, STREAMING AD INSERTION OPT-IN,
    TOTAL DELIVERY, DOWNLOADS, STREAMS

For a presenting partner whose read runs via DAI across the whole catalog, the
campaign's "Listens" = downloads + streams for the podcast across all episodes
(new + back catalog) in the flight window. `to_delivery_rows()` turns a parsed
report into `DeliveryRow`s on the "Megaphone Listens" channel: one per in-window
episode (so the campaign page shows episode count + avg listens/episode), plus a
single "(back catalog)" aggregate for pre-window episodes' in-flight listens.
Those rows feed the same pacing path as the hand-kept delivery log.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import IO

from app.parsers.delivery_log import DeliveryRow

# Canonical header -> the normalized key we read by.
_WANTED = {
    "episode title": "title",
    "published date": "published",
    "episode duration": "duration",
    "podcast title": "podcast",
    "spotify audience network opt-in": "san_optin",
    "streaming ad insertion opt-in": "sai_optin",
    "total delivery": "total_delivery",
    "downloads": "downloads",
    "streams": "streams",
}


def _norm_key(k: str) -> str:
    return re.sub(r"\s+", " ", (k or "").strip().lower())


def _int(v) -> int:
    # Keep digits, sign and decimal point, then round — so "7,655", "7655.0"
    # and 7655.0 all parse to 7655 (never 76550 from a stripped dot).
    s = re.sub(r"[^0-9.\-]", "", str(v if v is not None else "")).strip()
    if s in ("", "-", ".", "-."):
        return 0
    try:
        return int(round(float(s)))
    except ValueError:
        return 0


def _bool(v) -> bool:
    return str(v or "").strip().lower() in ("yes", "true", "1", "y")


def _parse_pub(s) -> date | None:
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _as_date(v) -> date | None:
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        try:
            return date.fromisoformat(v)
        except ValueError:
            return _parse_pub(v)
    return None


@dataclass
class EpisodeRow:
    title: str
    published: date | None
    podcast: str
    sai_optin: bool                 # Streaming Ad Insertion opt-in (DAI eligible)
    downloads: int
    streams: int
    total_delivery: int
    raw: dict = field(default_factory=dict)


@dataclass
class CustomReportResult:
    rows: list[EpisodeRow]
    warnings: list[str] = field(default_factory=list)


def _materialize(file: IO[bytes] | str | bytes) -> str | None:
    if isinstance(file, str):
        try:
            with open(file, "r", encoding="utf-8-sig") as fh:
                return fh.read()
        except OSError:
            return None
    data = file.read() if hasattr(file, "read") else file
    if isinstance(data, bytes):
        return data.decode("utf-8-sig", "replace")
    return data


def parse(file: IO[bytes] | str | bytes) -> CustomReportResult:
    text = _materialize(file)
    if text is None:
        return CustomReportResult(rows=[], warnings=["custom report: could not read file"])

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return CustomReportResult(rows=[], warnings=["custom report: empty / no header"])

    # Map the file's headers to our normalized keys.
    keymap: dict[str, str] = {}
    for raw in reader.fieldnames:
        nk = _WANTED.get(_norm_key(raw))
        if nk:
            keymap[raw] = nk

    warnings: list[str] = []
    for need in ("title", "podcast", "total_delivery", "downloads", "streams"):
        if need not in keymap.values():
            warnings.append(f"custom report: missing expected column for '{need}'")

    rows: list[EpisodeRow] = []
    for r in reader:
        rec = {keymap[k]: v for k, v in r.items() if k in keymap}
        if not (rec.get("title") or "").strip() and not (rec.get("podcast") or "").strip():
            continue
        downloads = _int(rec.get("downloads"))
        streams = _int(rec.get("streams"))
        total = _int(rec.get("total_delivery")) or (downloads + streams)
        rows.append(EpisodeRow(
            title=(rec.get("title") or "").strip(),
            published=_parse_pub(rec.get("published")),
            podcast=(rec.get("podcast") or "").strip(),
            sai_optin=_bool(rec.get("sai_optin")),
            downloads=downloads,
            streams=streams,
            total_delivery=total,
            raw=dict(r),
        ))
    return CustomReportResult(rows=rows, warnings=warnings)


def _slug(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (title or "").lower()).strip("-")
    return s[:48] or "episode"


def to_delivery_rows(
    result: CustomReportResult,
    podcast_title: str,
    flight_start,
    *,
    dai_only: bool = True,
    channel: str = "Megaphone Listens",
) -> list[DeliveryRow]:
    """Convert a parsed Custom report into DeliveryRows on `channel`.

    - Filters to `podcast_title` (case-insensitive) and, when `dai_only`, to
      episodes with Streaming Ad Insertion on (the ones that carry the DAI read).
    - One row per episode published on/after `flight_start` (in-window), plus one
      "(back catalog)" aggregate for episodes published before it.
    - `delivered` for each row comes from `listens_attributed` (= total delivery).
    """
    want = (podcast_title or "").strip().lower()
    start = _as_date(flight_start)

    eps = [e for e in result.rows if e.podcast.strip().lower() == want]
    if dai_only:
        eps = [e for e in eps if e.sai_optin]

    def _mk(episode_id: str, episode_date: str, listens: int, title: str) -> DeliveryRow:
        return DeliveryRow(
            episode_id=episode_id,
            episode_date=episode_date,
            channel=channel,
            copilot_tagged=True,
            paid_spend_usd=0.0,
            impressions=0,
            listens_attributed=int(listens),
            post_url="",
            post_type="podcast",
            raw={"source": "megaphone_custom_report", "episode_title": title},
        )

    rows: list[DeliveryRow] = []
    back_total = 0
    back_n = 0
    for e in eps:
        in_window = start is None or (e.published is not None and e.published >= start)
        if in_window:
            iso = e.published.isoformat() if e.published else ""
            eid = f"ep-{iso}" if iso else f"ep-{_slug(e.title)}"
            rows.append(_mk(eid, iso, e.total_delivery, e.title))
        else:
            back_total += e.total_delivery
            back_n += 1

    if back_n:
        rows.append(DeliveryRow(
            episode_id="(back catalog)",
            episode_date="",
            channel="Back Catalog",
            copilot_tagged=True,
            paid_spend_usd=0.0,
            impressions=0,
            listens_attributed=int(back_total),
            post_url="",
            post_type="podcast",
            raw={"source": "megaphone_custom_report",
                 "episode_count": back_n,
                 "note": f"{back_n} pre-window episodes still carrying the DAI read"},
        ))
    return rows
