"""Parser for presenting-partner delivery-log CSVs (e.g. Microsoft Copilot x
FOS Today).

Unlike the Measure/ad-platform parsers, a presenting-partner campaign isn't a
Measure post group — it's a manual delivery log the social team appends to, one
row per placement per episode, spanning channels that aren't all social
(.com, AudienceLift, podcast audio, the FOS app). The dashboard scores
cumulative impressions vs a contracted goal and per-channel delivery vs target.

Schema (one row per placement per episode):
    episode_id, episode_date, episode_title, channel, post_type, post_url,
    published_at, copilot_tagged, paid_boost, paid_spend_usd, impressions,
    engagements, link_clicks, listens_attributed, notes

Guardrail: only rows with copilot_tagged = TRUE count toward delivery — an
untagged placement doesn't carry the partner's logo, so it isn't delivered
against the commitment. Compliance (% tagged) is tracked separately.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from typing import IO

# Canonical channel labels (match the campaign's channel_targets in config), and
# the aliases a logger might type in the CSV `channel` column.
CHANNEL_ALIASES: dict[str, str] = {
    # --- Impressions group (promo placements) ---
    "x": "X", "twitter": "X",
    "linkedin": "LinkedIn",
    "threads": "Threads",
    "ig stories": "IG Stories", "instagram": "IG Stories", "ig": "IG Stories", "instagram stories": "IG Stories",
    "baker & dan": "Baker & Dan", "baker/dan": "Baker & Dan", "baker and dan": "Baker & Dan", "baker": "Baker & Dan",
    "megaphone": "Megaphone", "organic (mgphn)": "Megaphone", "mgphn": "Megaphone",  # organic promo impressions
    ".com homepage": ".com homepage", "homepage": ".com homepage", ".com home": ".com homepage",
    ".com display": ".com display", "display": ".com display",
    ".com": ".com homepage",  # bare ".com" → homepage unless specified
    "audiencelift": "AudienceLift", "audiencelift - pref apps": "AudienceLift", "audiencelift pref apps": "AudienceLift", "pref apps": "AudienceLift",
    "fos app": "FOS App", "app": "FOS App", "fos app (now & listen)": "FOS App", "fos app (now&lstn)": "FOS App",
    "other": "Other", "spotify": "Other", "overcast": "Other", "other (spotify/overcast)": "Other",
    # --- Listens group (downloads + streams) ---
    "megaphone listens": "Megaphone Listens", "organic (megaphone)": "Megaphone Listens",
    "megaphone downloads": "Megaphone Listens", "podcast downloads": "Megaphone Listens",
    "audiencelift audio": "AudienceLift Audio", "audiencelift audio web players": "AudienceLift Audio", "audio web players": "AudienceLift Audio",
    "paid promo": "Paid Promo", "paid promo (above)": "Paid Promo",
    "organic app": "Organic App", "organic (app)": "Organic App", "app listens": "Organic App", "fos app listens": "Organic App",
}


def _bool(v: str) -> bool:
    return str(v or "").strip().lower() in ("true", "1", "yes", "y", "t")


def _int(v) -> int:
    s = str(v or "").replace(",", "").strip()
    if not s:
        return 0
    try:
        return int(float(s))
    except ValueError:
        return 0


def _float(v) -> float:
    s = str(v or "").replace(",", "").replace("$", "").strip()
    if not s:
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


@dataclass
class DeliveryRow:
    episode_id: str
    episode_date: str
    channel: str              # canonical label (or raw if unrecognized)
    copilot_tagged: bool
    paid_spend_usd: float
    impressions: int
    listens_attributed: int
    post_url: str = ""
    post_type: str = ""
    raw: dict = field(default_factory=dict)

    @property
    def delivered(self) -> int:
        """Impression-equivalent delivery for this row. Audio placements carry
        listens/downloads (the goal counts ~225.5K audio listens as impressions),
        so fall back to listens_attributed when there are no impressions."""
        return self.impressions or self.listens_attributed


@dataclass
class DeliveryLogResult:
    rows: list[DeliveryRow]
    warnings: list[str] = field(default_factory=list)

    @property
    def tagged_rows(self) -> list[DeliveryRow]:
        return [r for r in self.rows if r.copilot_tagged]


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


def parse(file: IO[bytes] | str | bytes) -> DeliveryLogResult:
    text = _materialize(file)
    if text is None:
        return DeliveryLogResult(rows=[], warnings=["delivery log: could not read file"])

    reader = csv.DictReader(io.StringIO(text))
    rows: list[DeliveryRow] = []
    warnings: list[str] = []
    unknown_channels: set[str] = set()

    for i, r in enumerate(reader, start=2):
        raw_channel = (r.get("channel") or "").strip()
        if not raw_channel and not (r.get("episode_id") or "").strip():
            continue  # blank line
        canon = CHANNEL_ALIASES.get(raw_channel.lower())
        if canon is None:
            canon = raw_channel or "Other"
            if raw_channel:
                unknown_channels.add(raw_channel)
        rows.append(DeliveryRow(
            episode_id=(r.get("episode_id") or "").strip(),
            episode_date=(r.get("episode_date") or "").strip(),
            channel=canon,
            copilot_tagged=_bool(r.get("copilot_tagged")),
            paid_spend_usd=_float(r.get("paid_spend_usd")),
            impressions=_int(r.get("impressions")),
            listens_attributed=_int(r.get("listens_attributed")),
            post_url=(r.get("post_url") or "").strip(),
            post_type=(r.get("post_type") or "").strip(),
            raw=dict(r),
        ))

    if unknown_channels:
        warnings.append(
            "delivery log: unrecognized channel(s) %s — counted toward campaign "
            "total but not matched to a channel target." % sorted(unknown_channels)
        )
    return DeliveryLogResult(rows=rows, warnings=warnings)
