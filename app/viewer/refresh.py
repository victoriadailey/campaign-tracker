"""Refresh viewer/data.js from CSV exports.

Usage: python -m app.viewer.refresh [--config path] [--output path] [--today YYYY-MM-DD]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from app.compute.rollup import (
    CampaignConfig,
    channel_rollups,
    hero_post_from_top,
    rollup_campaign,
    top_posts_by_er,
    top_posts_by_organic_reach,
)
from app.parsers import NormalizedPost, ParseResult
from app.parsers.google_ads_campaign import parse as parse_gads_campaign
from app.parsers.measure_studio import parse as parse_ms
from app.viewer.data_contract import (
    CampaignSummary,
    DataSource,
    Goal,
    PulsePayload,
    Signal,
)
from app.viewer.render import write_data_js

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "config" / "campaigns.yaml"
DEFAULT_OUTPUT = REPO_ROOT / "viewer" / "data.js"


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenerate viewer/data.js from CSV exports.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--today", help="Override 'today' for pacing math (YYYY-MM-DD).")
    args = parser.parse_args()

    today = date.fromisoformat(args.today) if args.today else date.today()

    cfg = yaml.safe_load(args.config.read_text())
    exports_root = REPO_ROOT / cfg.get("exports_root", "tests/fixtures")
    sample = _load_design_sample(REPO_ROOT / "viewer" / "data.sample.js")

    # ---------- Parse ----------
    posts_by_campaign: dict[str, list[NormalizedPost]] = defaultdict(list)
    parse_warnings: list[str] = []

    for c in cfg["campaigns"]:
        c_id = c["id"]
        match_groups = {g.lower() for g in c.get("ms_post_groups", [])}

        for ms_file in c.get("sources", {}).get("measure_studio", []) or []:
            path = exports_root / ms_file
            if not path.exists():
                parse_warnings.append(f"[{c_id}] missing MS file: {path}")
                continue
            result: ParseResult = parse_ms(str(path))
            if not result.ok:
                parse_warnings.extend(f"[{c_id}] {path.name}: {e}" for e in result.errors)
                continue
            matched = [p for p in result.rows if any(g.lower() in match_groups for g in p.post_groups)]
            posts_by_campaign[c_id].extend(matched)

        for gads_file in c.get("sources", {}).get("google_ads_campaign", []) or []:
            path = exports_root / gads_file
            if not path.exists():
                parse_warnings.append(f"[{c_id}] missing Google Ads file: {path}")
                continue
            result = parse_gads_campaign(str(path))
            posts_by_campaign[c_id].extend(result.rows)

    # ---------- Campaign rollups (with sample fallback for empty campaigns) ----------
    campaigns: list[CampaignSummary] = []
    for c in cfg["campaigns"]:
        cc = CampaignConfig(
            id=c["id"], partner=c["partner"], series=c["series"],
            series_italic=c["series_italic"], type=c["type"],
            flight_start=c["flight_start"], flight_end=c["flight_end"],
            impression_goal=int(c["impression_goal"]),
            budget_goal=float(c["budget_goal"]),
            color=c["color"], lead_format=c["lead_format"], blurb=c["blurb"],
        )
        posts = posts_by_campaign.get(cc.id, [])
        if posts:
            campaigns.append(rollup_campaign(cc, posts, today=today))
        else:
            campaigns.append(_sample_campaign_or_compute(cc, sample, today))

    # ---------- Cross-campaign ----------
    partners = {c.id: c.partner for c in campaigns}
    top_er = top_posts_by_er(dict(posts_by_campaign), partners, n=8)
    top_org = top_posts_by_organic_reach(dict(posts_by_campaign), partners, n=6)
    hero = hero_post_from_top(top_er)
    channels = channel_rollups(dict(posts_by_campaign))

    # ---------- Static from config ----------
    sources = [DataSource(name=s["name"], date=s["date"], stale=bool(s.get("stale"))) for s in cfg.get("sources", [])]
    signals = [Signal(kind=s["kind"], title=s["title"], body=s["body"]) for s in cfg.get("signals", [])]

    # ---------- Passthrough from design sample ----------
    ub_components = sample.get("UB_COMPONENTS", [])
    episodes_by_campaign = sample.get("EPISODES_BY_CAMPAIGN", {})

    # Fallback hero / top posts from sample if we computed nothing real
    if not top_er:
        sample_top = sample.get("TOP_POSTS", [])
        sample_hero = sample.get("HERO_POST")
        sample_org = sample.get("TOP_POSTS_ORGANIC", [])
    else:
        sample_top = None
        sample_hero = None
        sample_org = None

    payload = PulsePayload(
        campaigns=campaigns,
        top_posts=top_er or sample_top or [],
        hero_post=hero or sample_hero,
        top_posts_organic=top_org or sample_org or [],
        channels=channels,
        sources=sources,
        signals=signals,
        episodes_by_campaign=episodes_by_campaign,
        ub_components=ub_components,
    )

    out_path = write_data_js(payload, args.output)

    print("=" * 60)
    print(f"  Pulse data refresh — {out_path}")
    print("=" * 60)
    for c in campaigns:
        post_count = len(posts_by_campaign.get(c.id, []))
        delivered = c.impressions.delivered
        print(
            f"  {c.partner:12} {c.series:25} "
            f"{post_count:>4} posts  "
            f"{int(delivered):>11,} impr  "
            f"({c.elapsed_pct:>5.1f}% elapsed, {c.status})"
        )
    print()
    if parse_warnings:
        print("  Warnings:")
        for w in parse_warnings:
            print(f"    - {w}")
    print(f"\n  Open viewer/index.html to view.")
    return 0


def _js_object_literal_to_json(js: str) -> str:
    """Convert a JS object/array literal to JSON-parseable string.

    Handles: numeric underscores (1_000_000), unquoted keys (id: → "id":),
    single-quoted strings, trailing commas, JS comments.
    Not a general JS parser — assumes data-shaped literals (no functions, regex, etc.).
    """
    # Strip // line comments
    js = re.sub(r'(?<!:)//[^\n]*', '', js)
    # Strip /* ... */ block comments
    js = re.sub(r'/\*[\s\S]*?\*/', '', js)
    # Numeric underscores: 5_910_000 → 5910000 (repeat until stable)
    while re.search(r'(\d)_(\d)', js):
        js = re.sub(r'(\d)_(\d)', r'\1\2', js)
    # Single-quoted strings → double-quoted (only outside of double-quotes; assume no
    # escaped double quotes inside single-quoted strings in our data).
    js = re.sub(r"'((?:[^'\\]|\\.)*)'", lambda m: json.dumps(m.group(1)), js)
    # Unquoted object keys: `id:` → `"id":` (after `{` or `,` or whitespace)
    js = re.sub(r'([\{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', js)
    # Trailing commas: `,]` `,}` → `]` `}`
    js = re.sub(r',(\s*[\]\}])', r'\1', js)
    return js


def _load_design_sample(path: Path) -> dict[str, Any]:
    """Extract JSON-shaped globals from data.sample.js for use as fallback."""
    if not path.exists():
        return {}
    text = path.read_text()
    out: dict[str, Any] = {}
    for name in ("CAMPAIGNS", "TOP_POSTS", "HERO_POST", "TOP_POSTS_ORGANIC",
                 "CHANNELS", "SOURCES", "SIGNALS", "UB_COMPONENTS",
                 "UB_PLATFORM_CPMS", "EPISODES_BY_CAMPAIGN"):
        m = re.search(rf'window\.{name}\s*=\s*(\[[\s\S]*?\n\]|\{{[\s\S]*?\n\}});\s*$', text, re.MULTILINE)
        if not m:
            continue
        try:
            cleaned = _js_object_literal_to_json(m.group(1))
            out[name] = json.loads(cleaned)
        except json.JSONDecodeError as e:
            print(f"  Warn: could not parse window.{name} from data.sample.js: {e}", file=sys.stderr)
    return out


def _sample_campaign_or_compute(cc: CampaignConfig, sample: dict, today: date) -> CampaignSummary:
    sample_campaigns = sample.get("CAMPAIGNS", [])
    row = next((c for c in sample_campaigns if c.get("id") == cc.id), None)
    if not row:
        return rollup_campaign(cc, [], today=today)
    return CampaignSummary(
        id=row["id"],
        partner=row["partner"],
        series=row["series"],
        series_italic=row.get("seriesItalic", ""),
        type=cc.type,  # type: ignore[arg-type]
        flight=row["flight"],
        elapsed_pct=row["elapsedPct"],
        days_left=row.get("daysLeft", 0),
        status=row["status"],
        status_kind=row["statusKind"],
        impressions=Goal(**row["impressions"]),
        budget=Goal(**row["budget"]),
        color=row["color"],
        lead_format=row.get("leadFormat", ""),
        top_channel=row.get("topChannel", ""),
        er=row.get("er", 0.0),
        cpm=row.get("cpm", 0.0),
        episodes=row.get("episodes", 0),
        posts=row.get("posts", 0),
        blurb=row.get("blurb", ""),
    )


if __name__ == "__main__":
    sys.exit(main())
