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

from app.compute.episodes import EpisodeDef, attribute_posts_to_episodes, rollup_episode
from app.compute.rollup import (
    CampaignConfig,
    aggregate_portfolio_signals,
    channel_rollups,
    compute_campaign_callouts,
    hero_post_from_top,
    per_campaign_channels,
    portfolio_cpm_by_channel,
    rollup_campaign,
    top_posts_by_er,
    top_posts_by_organic_reach,
)
from app.parsers import NormalizedPost, ParseResult, Platform, Source
from app.parsers.google_ads_campaign import parse as parse_gads_campaign
from app.parsers.measure_studio import parse as parse_ms
from app.parsers.linkedin_ads import parse as parse_linkedin_ads
from app.parsers.meta_ads import parse as parse_meta_ads
from app.parsers.tiktok_ads import parse as parse_tiktok_ads
from app.parsers.x_ads import parse as parse_x_ads
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
    parser.add_argument(
        "--exclude",
        help="Comma-separated campaign ids to exclude from this build "
             "(e.g. --exclude usbank to drop US Bank from the main dashboard).",
    )
    parser.add_argument(
        "--only",
        help="Comma-separated campaign ids to KEEP (everything else is excluded). "
             "Use for single-campaign builds, e.g. --only usbank.",
    )
    args = parser.parse_args()

    today = date.fromisoformat(args.today) if args.today else date.today()

    cfg = yaml.safe_load(args.config.read_text())

    # Filter campaigns based on --only / --exclude flags. --only takes precedence.
    if args.only:
        keep = {x.strip() for x in args.only.split(",") if x.strip()}
        cfg["campaigns"] = [c for c in cfg["campaigns"] if c["id"] in keep]
    elif args.exclude:
        drop = {x.strip() for x in args.exclude.split(",") if x.strip()}
        cfg["campaigns"] = [c for c in cfg["campaigns"] if c["id"] not in drop]
    exports_root = REPO_ROOT / cfg.get("exports_root", "tests/fixtures")
    sample = _load_design_sample(REPO_ROOT / "viewer" / "data.sample.js")

    # ---------- Parse ----------
    posts_by_campaign: dict[str, list[NormalizedPost]] = defaultdict(list)
    parse_warnings: list[str] = []

    _PLATFORM_FROM_KEY = {p.value: p for p in Platform}

    # Try to spin up a Measure Studio API client once, reused across campaigns.
    ms_client = None
    ms_unavailable_cls = None
    try:
        from app.sources.measure_studio_api import (
            MeasureStudioClient,
            MeasureStudioUnavailable,
        )
        ms_unavailable_cls = MeasureStudioUnavailable
        try:
            ms_client = MeasureStudioClient.from_env()
        except MeasureStudioUnavailable as e:
            print(f"  ℹ  Measure Studio API not configured ({e}); CSV mode for any "
                  f"campaign without `measure_studio_group_id`.")
    except ImportError:
        pass  # API module not available; CSV only.

    ms_fetch_errors: list[str] = []
    for c in cfg["campaigns"]:
        c_id = c["id"]
        organic_only = {_PLATFORM_FROM_KEY[k.lower()] for k in c.get("ms_organic_only_for", [])
                        if k.lower() in _PLATFORM_FROM_KEY}
        # Platforms to drop entirely from Measure Studio for this campaign —
        # used when an ad-platform export is the authoritative source for that
        # platform and MS would otherwise double-count the same dark posts
        # (e.g. Sport Clips: TikTok + X come from their exports, not MS).
        ms_exclude = {k.lower() for k in (c.get("ms_exclude_platforms") or [])}

        # ---------- Measure Studio ----------
        # When `measure_studio_group_id(s)` is configured the API IS the
        # source — no silent CSV fallback. The client retries transient
        # 5xx/429 errors up to 5 times internally; if it still fails after
        # that, we surface a loud error and leave the campaign's MS posts
        # out of the refresh entirely. Operator drops a fresh CSV manually
        # and removes the `measure_studio_group_id` line if they want to
        # use the file instead.
        group_ids = c.get("sources", {}).get("measure_studio_group_ids") or []
        single = c.get("sources", {}).get("measure_studio_group_id")
        if single:
            group_ids = [single, *group_ids]

        if group_ids:
            if ms_client is None:
                ms_fetch_errors.append(
                    f"[{c_id}] MS API not configured but `measure_studio_group_id` is set. "
                    f"Add MEASURE_STUDIO_API_TOKEN to .env."
                )
            else:
                try:
                    for gid in group_ids:
                        rows = ms_client.fetch_group(gid)
                        if ms_exclude:
                            rows = [p for p in rows if p.platform.value not in ms_exclude]
                        posts_by_campaign[c_id].extend(rows)
                except Exception as e:  # noqa: BLE001
                    ms_fetch_errors.append(
                        f"[{c_id}] MS API fetch failed after retries: {e}. "
                        f"DATA IS INCOMPLETE for this campaign — re-run, or drop a fresh "
                        f"manual CSV in tests/fixtures/ and comment out `measure_studio_group_id`."
                    )
        else:
            # No API group configured — pure CSV path (still used by campaigns
            # that haven't been migrated to the API yet).
            for ms_file in c.get("sources", {}).get("measure_studio", []) or []:
                path = exports_root / ms_file
                if not path.exists():
                    parse_warnings.append(f"[{c_id}] missing MS file: {path}")
                    continue
                result: ParseResult = parse_ms(str(path), organic_only_for=organic_only)
                if not result.ok:
                    parse_warnings.extend(f"[{c_id}] {path.name}: {e}" for e in result.errors)
                    continue
                # Every row in a per-campaign MS export belongs to that campaign.
                posts_by_campaign[c_id].extend(result.rows)

        for gads_file in c.get("sources", {}).get("google_ads_campaign", []) or []:
            path = exports_root / gads_file
            if not path.exists():
                parse_warnings.append(f"[{c_id}] missing Google Ads file: {path}")
                continue
            result = parse_gads_campaign(str(path))
            if result.warnings:
                parse_warnings.extend(f"[{c_id}] {path.name}: {w}" for w in result.warnings)
            posts_by_campaign[c_id].extend(result.rows)

        for yt_file in c.get("sources", {}).get("youtube_paid", []) or []:
            path = exports_root / yt_file
            if not path.exists():
                parse_warnings.append(f"[{c_id}] missing YouTube Paid file: {path}")
                continue
            # Same format as google_ads_campaign export
            result = parse_gads_campaign(str(path))
            if result.warnings:
                parse_warnings.extend(f"[{c_id}] {path.name}: {w}" for w in result.warnings)
            posts_by_campaign[c_id].extend(result.rows)

        # Some Google Ads exports drop the "(shorts)" tag from campaign names,
        # so the parser can't tell a Shorts placement from in-feed. A
        # campaign-level `youtube_paid_shorts` keyword list lets the operator
        # mark which Google Ads campaigns are Shorts; force those posts to
        # REELS_SHORTS here (before the YT-paid → MS merge) so their paid spend
        # attaches to the matching Shorts post instead of floating as in-feed.
        _shorts_kw = [str(k).strip().lower() for k in (c.get("youtube_paid_shorts") or []) if str(k).strip()]
        if _shorts_kw:
            for _p in posts_by_campaign[c_id]:
                if _p.source is not Source.GOOGLE_ADS_CAMPAIGN:
                    continue
                _low = (_p.post_title or _p.post_id_native or "").lower()
                if "short" in _low or not any(k in _low for k in _shorts_kw):
                    continue
                # The export dropped the operator's "(shorts)" tag; re-append it
                # so the YT-paid → MS merge (which derives subtype from the name,
                # not post_format) classifies the campaign as Shorts and merges
                # its spend onto the matching Shorts post.
                if _p.post_title:
                    _p.post_title = f"{_p.post_title} (shorts)"
                if _p.post_id_native:
                    _p.post_id_native = f"{_p.post_id_native} (shorts)"

        for x_file in c.get("sources", {}).get("x_ads", []) or []:
            path = exports_root / x_file
            if not path.exists():
                parse_warnings.append(f"[{c_id}] missing X Ads file: {path}")
                continue
            result = parse_x_ads(str(path))
            if not result.ok:
                parse_warnings.extend(f"[{c_id}] {path.name}: {e}" for e in result.errors)
                continue
            posts_by_campaign[c_id].extend(result.rows)

        for meta_file in c.get("sources", {}).get("meta_ads", []) or []:
            path = exports_root / meta_file
            if not path.exists():
                parse_warnings.append(f"[{c_id}] missing Meta Ads file: {path}")
                continue
            result = parse_meta_ads(str(path))
            if not result.ok:
                parse_warnings.extend(f"[{c_id}] {path.name}: {e}" for e in result.errors)
                continue
            posts_by_campaign[c_id].extend(result.rows)

        # ---------- Manual rows (operator-entered performance) ----------
        # For components whose actuals live in a wrap report rather than an
        # export (e.g. Sport Clips MLB Minute — per-platform totals from the
        # 4/21 report). Each YAML row becomes a dark/paid NormalizedPost:
        #   - title: "MLB Minute Video 1 — Instagram"
        #     platform: instagram          # Platform enum value
        #     format: reels_shorts         # PostFormat value (default reels_shorts)
        #     impressions: 80633
        #     views: 77023                 # optional
        #     clicks: 35                   # optional
        #     spend: 239.17                # optional
        for row in c.get("sources", {}).get("manual_rows", []) or []:
            from app.parsers.base import Boosting as _MB, PostFormat as _MPF
            _impr = int(row.get("impressions") or 0)
            _spend = float(row.get("spend") or 0)
            _views = row.get("views")
            _clicks = row.get("clicks")
            _plat = {p.value: p for p in Platform}.get(
                str(row.get("platform", "")).strip().lower(), Platform.UNKNOWN)
            _fmt = {f.value: f for f in _MPF}.get(
                str(row.get("format", "reels_shorts")).strip().lower(), _MPF.OTHER)
            posts_by_campaign[c_id].append(NormalizedPost(
                source=Source.MANUAL,
                platform=_plat,
                post_id_native=f"manual:{c_id}:{row.get('title', '')}",
                post_title=str(row.get("title") or ""),
                post_format=_fmt,
                boosting=_MB.DARK,
                impressions_total=_impr or None,
                impressions_paid=_impr or None,
                views_total=int(_views) if _views is not None else None,
                views_paid=int(_views) if _views is not None else None,
                clicks_paid=int(_clicks) if _clicks is not None else None,
                ad_spend=_spend or None,
                cpm=(_spend / _impr * 1000) if _impr and _spend else None,
                ctr=(int(_clicks) / _impr) if _impr and _clicks is not None else None,
                raw=dict(row),
            ))

        for tt_file in c.get("sources", {}).get("tiktok_ads", []) or []:
            path = exports_root / tt_file
            if not path.exists():
                parse_warnings.append(f"[{c_id}] missing TikTok Ads file: {path}")
                continue
            result = parse_tiktok_ads(str(path))
            if not result.ok:
                parse_warnings.extend(f"[{c_id}] {path.name}: {e}" for e in result.errors)
                continue
            if result.warnings:
                parse_warnings.extend(f"[{c_id}] {path.name}: {w}" for w in result.warnings)
            posts_by_campaign[c_id].extend(result.rows)

        for li_file in c.get("sources", {}).get("linkedin_ads", []) or []:
            path = exports_root / li_file
            if not path.exists():
                parse_warnings.append(f"[{c_id}] missing LinkedIn Ads file: {path}")
                continue
            result = parse_linkedin_ads(str(path))
            if not result.ok:
                parse_warnings.extend(f"[{c_id}] {path.name}: {e}" for e in result.errors)
                continue
            posts_by_campaign[c_id].extend(result.rows)

        # ---------- Apply ad_title_overrides ----------
        # Substring-match: each generic export name like
        # "US Bank_NFL Draft_The Come Up_Video 1 (IG)" picks up its mapping
        # via the "US Bank_NFL Draft_The Come Up_Video 1" key, so both (IG)
        # and (FB) variants get the same friendly title.
        title_overrides = c.get("ad_title_overrides") or {}
        if title_overrides:
            for p in posts_by_campaign[c_id]:
                if not p.post_title:
                    continue
                for needle, friendly in title_overrides.items():
                    if needle in p.post_title:
                        p.post_title = friendly
                        break

        # ---------- Merge paid-source spend into MS performance posts ----------
        # Same idea for X and YouTube: Measure Studio is the authoritative source
        # for per-post performance (impressions, engagements, organic/paid split,
        # plus the descriptive post title). The ad-platform exports (X Ads,
        # Google Ads YT Paid) supply spend.
        #
        # For each ad row, find the matching MS post by impressions_paid value
        # (exact match first, then closest within ±5%), copy the spend over,
        # then drop the ad row. Posts show as a single row in the per-episode
        # table using MS's descriptive title. Unmatched ad rows (true dark
        # posts MS can't see) stay as their own row.
        # ---------- Operator-defined post merges ----------
        # `merge_posts` combines several MS posts into one display post — e.g.
        # Sport Clips runs the same dark TikTok creative as 3 ad variants that
        # MS reports as 3 separate posts. Stats are summed, identity comes from
        # the first listed id, and the configured title replaces the post text.
        #   merge_posts:
        #     - ids: [111, 222, 333]
        #       title: "Off the Pitch Video 1 — TikTok"
        for spec in c.get("merge_posts") or []:
            _ids = {str(x) for x in (spec.get("ids") or [])}
            if not _ids:
                continue
            bucket = [p for p in posts_by_campaign[c_id] if str(p.post_id_native) in _ids]
            if len(bucket) < 2:
                continue
            rest = [p for p in posts_by_campaign[c_id] if str(p.post_id_native) not in _ids]
            base = bucket[0]
            def _sum(attr):
                vals = [getattr(p, attr) or 0 for p in bucket]
                return sum(vals) if any(getattr(p, attr) is not None for p in bucket) else None
            for attr in ("impressions_total", "impressions_paid", "impressions_organic",
                         "views_total", "views_paid", "views_organic",
                         "reach_total", "reach_paid", "reach_organic",
                         "engagements_total", "engagements_paid", "engagements_organic",
                         "clicks_paid", "link_clicks_paid", "ad_spend",
                         "video_views_p100_paid", "video_views_3s_paid"):
                setattr(base, attr, _sum(attr))
            if spec.get("title"):
                base.post_title = str(spec["title"])
            base.posted_at = min((p.posted_at for p in bucket if p.posted_at), default=base.posted_at)
            base.er = ((base.engagements_total / base.impressions_total)
                       if base.engagements_total and base.impressions_total else None)
            base.cpm = ((base.ad_spend / base.impressions_paid * 1000)
                        if base.ad_spend and base.impressions_paid else None)
            base.post_groups = sorted({g for p in bucket for g in (p.post_groups or [])})
            posts_by_campaign[c_id] = rest + [base]

        x_pairings = c.get("x_ads_pairings") or {}
        posts_by_campaign[c_id] = _merge_x_ads_spend_into_ms(posts_by_campaign[c_id], manual_pairings=x_pairings)
        posts_by_campaign[c_id] = _merge_youtube_paid_spend_into_ms(
            posts_by_campaign[c_id],
            pair_by_sort=bool(c.get("yt_paired_by_sort")),
        )
        # LinkedIn Ads CSV may overlap with an MS-API LinkedIn dark post. MS
        # gives the post's organic-side view count + URN; the LI Ads CSV gives
        # the paid spend MS can't see. Merge them so the dashboard shows one row.
        posts_by_campaign[c_id] = _merge_linkedin_ads_into_ms(posts_by_campaign[c_id])
        # Facebook surfaces the organic post and its dark-ad promotion as two
        # SEPARATE post IDs (the dark ad has its own platform_id since FB ads
        # don't appear on the page feed). MS reports them as two rows — one
        # paid-only, one organic-only — sharing the same copy + page. Pair
        # them so the dashboard reads as a single organic+boosted row.
        posts_by_campaign[c_id] = _merge_facebook_organic_paid_pairs(posts_by_campaign[c_id])

    # ---------- Cross-group manual_posts re-merge ----------
    # The cross-group manual_posts fetch above ran AFTER the per-campaign
    # merge passes for X/YT/LinkedIn/FB, so any cross-group MS post that
    # arrived (e.g. Heineken's YT Short pulled from the main FOS YT channel
    # rather than MS group 7587) never had a chance to pair with its GAds
    # row. Re-run the YT merge for any campaign that gained a YT post in
    # the cross-group step.
    #
    # Note: the cross-group fetch itself happens earlier in the per-campaign
    # loop section below this comment in the original ordering — moved up
    # here so it can re-feed the merge step. See `cross_group_added` below.
    # ---------- Cross-group manual_posts (early) ----------
    cross_group_added: dict[str, list[NormalizedPost]] = {}
    if ms_client is not None:
        # Platform hints by native-ID shape — speeds up the per-account scan.
        import re as _re
        def _platform_hint(pid: str) -> Platform | None:
            # LinkedIn URNs are the one id the MS query index doesn't match
            # (they resolve via URL, not platform_id), so they hit the account
            # scan — hint LinkedIn so that scan stays narrow.
            if pid.startswith("urn:li:"):
                return Platform.LINKEDIN
            # YT video IDs are 11 chars of [A-Za-z0-9_-].
            if _re.fullmatch(r"[A-Za-z0-9_-]{11}", pid):
                return Platform.YOUTUBE
            return None  # let the lookup scan all accounts as a fallback

        for c in cfg["campaigns"]:
            c_id = c["id"]
            existing_native_ids = {
                str(p.post_id_native) for p in posts_by_campaign.get(c_id, [])
                if p.post_id_native
            }
            added_here: list[NormalizedPost] = []
            for ep in c.get("episodes", []) or []:
                for pinned in (ep.get("manual_posts") or []):
                    pinned_str = str(pinned)
                    if pinned_str in existing_native_ids:
                        continue
                    hint = _platform_hint(pinned_str)
                    found = ms_client.find_post_by_native_id(pinned_str, platform_hint=hint)
                    if found is not None:
                        posts_by_campaign[c_id].append(found)
                        existing_native_ids.add(pinned_str)
                        added_here.append(found)
                    # If still not found, the attribute_posts_to_episodes step
                    # will silently skip — that's fine; the unattributed-posts
                    # warning at the end of refresh surfaces any drift.
            if added_here:
                cross_group_added[c_id] = added_here

    # Re-run platform-specific merges for any campaign that gained a cross-
    # group post, so the new MS post can pair with its already-loaded ad-
    # platform counterpart (e.g. Heineken: cross-group YT Short ↔ Heineken
    # GAds row).
    for c_id, added in cross_group_added.items():
        platforms_added = {p.platform for p in added}
        c_cfg = next((c for c in cfg["campaigns"] if c["id"] == c_id), None)
        if c_cfg is None:
            continue
        if Platform.YOUTUBE in platforms_added:
            posts_by_campaign[c_id] = _merge_youtube_paid_spend_into_ms(
                posts_by_campaign[c_id],
                pair_by_sort=bool(c_cfg.get("yt_paired_by_sort")),
            )
        if Platform.LINKEDIN in platforms_added:
            posts_by_campaign[c_id] = _merge_linkedin_ads_into_ms(posts_by_campaign[c_id])
        if Platform.FACEBOOK in platforms_added:
            posts_by_campaign[c_id] = _merge_facebook_organic_paid_pairs(posts_by_campaign[c_id])

    # ---------- Campaign-level exclude ----------
    # Drop posts matching a campaign's `exclude` keyword list from the campaign
    # entirely — totals, per-post table, and episode rollups alike. Used to keep
    # stray campaigns out (e.g. Spectrum's X "Branded article Promo"). Applied
    # after all sources, merges, and cross-group pins are assembled, and matches
    # against post title + native id (case-insensitive substring).
    for c in cfg["campaigns"]:
        _ex = [str(x).strip().lower() for x in (c.get("exclude") or []) if str(x).strip()]
        if not _ex:
            continue
        _cid = c["id"]
        _before = posts_by_campaign.get(_cid, [])
        _kept = [
            p for p in _before
            if not any(
                k in f"{getattr(p, 'post_title', None) or ''} {getattr(p, 'post_id_native', None) or ''}".lower()
                for k in _ex
            )
        ]
        if len(_kept) != len(_before):
            posts_by_campaign[_cid] = _kept
            parse_warnings.append(
                f"[{_cid}] excluded {len(_before) - len(_kept)} post(s) via campaign exclude {c.get('exclude')}"
            )

    # ---------- Campaign rollups (with sample fallback for empty campaigns) ----------
    campaigns: list[CampaignSummary] = []
    for c in cfg["campaigns"]:
      try:
        cc = CampaignConfig(
            id=c["id"], partner=c["partner"], series=c["series"],
            # series_italic / lead_format are cosmetic — default them so a
            # campaign added via the dashboard (which may omit them) never
            # crashes the whole refresh. series_italic falls back to the last
            # word of the series (matches the hand-authored convention).
            series_italic=c.get("series_italic") or (c.get("series", "").split() or [""])[-1],
            type=c.get("type", "social"),
            flight_start=c.get("flight_start"), flight_end=c.get("flight_end"),
            impression_goal=int(c.get("impression_goal") or 0),
            budget_goal=float(c.get("budget_goal") or 0),
            color=c.get("color", "ft-1"), lead_format=c.get("lead_format", ""),
            blurb=c.get("blurb", ""),
            benchmark_category=c.get("benchmark_category", ""),
            lifecycle=c.get("lifecycle", "active"),
            goal_split_full_ep=c.get("goal_split_full_ep"),
            goal_split_cutdowns=c.get("goal_split_cutdowns"),
            brandx_objective=c.get("brandx_objective", ""),
            brandx_secondary_objective=c.get("brandx_secondary_objective", ""),
            paid_only=bool(c.get("paid_only", False)),
            paid_only_post_ids=[str(x) for x in (c.get("paid_only_post_ids") or [])],
            flight_tbd=bool(c.get("flight_tbd", False)),
            # Match keywords of any component flagged `added_value: true` —
            # excluded from the campaign's goal-delivered totals (still shown
            # in the component cards + per-post table).
            # Group-defined added-value components contribute their group IDs
            # (precise); keyword-defined ones contribute their match keywords.
            added_value_match=[
                kw
                for ep in (c.get("episodes") or [])
                if ep.get("added_value") and not ep.get("group_ids")
                for kw in (ep.get("match") or [])
            ],
            added_value_groups=[
                int(g)
                for ep in (c.get("episodes") or [])
                if ep.get("added_value")
                for g in (ep.get("group_ids") or [])
            ],
            budget_includes_added_value=bool(c.get("budget_includes_added_value", False)),
        )
        ms_ts, exports_ts = _campaign_last_updated(c, exports_root)
        posts = posts_by_campaign.get(cc.id, [])
        if posts:
            summary = rollup_campaign(cc, posts, today=today)
            summary.last_updated_ms = ms_ts
            summary.last_updated_exports = exports_ts
            # Attach per-campaign channels + top posts + auto-generated callouts
            summary.channels = per_campaign_channels(posts)
            partners_one = {cc.id: cc.partner}
            summary.top_posts = top_posts_by_er({cc.id: posts}, partners_one, n=10)
            summary.top_posts_organic = top_posts_by_organic_reach({cc.id: posts}, partners_one, n=10)
            summary.callouts = compute_campaign_callouts(
                summary,
                summary.channels,
                summary.top_posts,
                today=today,
                organic_by_design_for=set(c.get("organic_by_design_for") or []),
            )
            campaigns.append(summary)
        else:
            _sample_summary = _sample_campaign_or_compute(cc, sample, today)
            _sample_summary.last_updated_ms = ms_ts
            _sample_summary.last_updated_exports = exports_ts
            campaigns.append(_sample_summary)
      except Exception as e:
        # A single malformed campaign (e.g. one just added via the dashboard
        # with a missing/typo'd field) must NEVER blank the whole dashboard.
        # Skip it with a loud warning and keep everyone else's data flowing.
        parse_warnings.append(
            f"[{c.get('id', '??')}] SKIPPED — campaign config error: {type(e).__name__}: {e}"
        )

    # ---------- Cross-campaign ----------
    partners = {c.id: c.partner for c in campaigns}
    top_er = top_posts_by_er(dict(posts_by_campaign), partners, n=8)
    top_org = top_posts_by_organic_reach(dict(posts_by_campaign), partners, n=6)
    hero = hero_post_from_top(top_er)
    channels = channel_rollups(dict(posts_by_campaign))

    # ---------- Static from config + aggregated signals ----------
    sources = [DataSource(name=s["name"], date=s["date"], stale=bool(s.get("stale"))) for s in cfg.get("sources", [])]

    # Pulse Check signals: aggregate the highest-impact WIN/OPPORTUNITY/WATCH from
    # per-campaign callouts. Falls back to YAML-defined signals if no callouts computed.
    aggregated = aggregate_portfolio_signals(campaigns)
    if aggregated:
        signals = aggregated
    else:
        signals = [Signal(kind=s["kind"], title=s["title"], body=s["body"]) for s in cfg.get("signals", [])]

    # ---------- Passthrough from design sample ----------
    ub_components = sample.get("UB_COMPONENTS", [])

    # ---------- Episode rollups ----------
    # Compute per-campaign episodes from real posts using user-defined episode rules.
    # Falls back to design sample for campaigns we can't compute.
    sample_episodes = sample.get("EPISODES_BY_CAMPAIGN", {})
    episodes_by_campaign: dict[str, list] = {}
    for c in cfg["campaigns"]:
        c_id = c["id"]
        ep_defs = [
            EpisodeDef(
                id=e["id"], n=e["n"], title=e["title"], date=e.get("date", ""),
                match=e.get("match", []), exclude=e.get("exclude", []),
                all_match=e.get("all_match", False),
                group_ids=[int(g) for g in (e.get("group_ids") or [])],
                impression_goal=e.get("impression_goal"),
                budget_goal=e.get("budget_goal"),
                manual_posts=[str(p) for p in (e.get("manual_posts") or [])],
                yt_organic_impressions=e.get("yt_organic_impressions"),
            )
            for e in c.get("episodes", []) or []
        ]
        posts = posts_by_campaign.get(c_id, [])
        if ep_defs and posts:
            attributed = attribute_posts_to_episodes(posts, ep_defs)
            # Apply hardcoded YT organic-impressions overrides to the in-feed
            # long-form video in each episode. These are pulled from YouTube
            # Studio directly because MS / GAds don't surface a reliable
            # organic-impressions count for YT long-form posts.
            for ep in ep_defs:
                _apply_yt_organic_override(ep, attributed.get(ep.id, []))
            computed = [rollup_episode(ep, attributed[ep.id]) for ep in ep_defs]
            real_episodes = [e for e in computed if e]
            episodes_by_campaign[c_id] = real_episodes
            # Reflect live episode count on the campaign card
            for summary in campaigns:
                if summary.id == c_id:
                    summary.episodes = len(real_episodes)
                    break

            # Pacing-by-component buckets: aggregate episode delivery into the
            # configured buckets and track each vs its own impression goal.
            pc_cfg = c.get("pacing_components") or []
            if pc_cfg:
                delivered_by_ep = {
                    ep.id: int((comp or {}).get("total", {}).get("impr", 0))
                    for ep, comp in zip(ep_defs, computed)
                }
                buckets = []
                for b in pc_cfg:
                    delivered = sum(delivered_by_ep.get(eid, 0) for eid in (b.get("episode_ids") or []))
                    buckets.append({
                        "label": b["label"],
                        "impressions": {"delivered": int(delivered), "goal": int(b.get("impression_goal", 0))},
                    })
                for summary in campaigns:
                    if summary.id == c_id:
                        summary.pacing_components = buckets
                        break
        else:
            # Fallback: use sample (E*TRADE has Kim Ng/Repole/Osborne placeholders in design)
            episodes_by_campaign[c_id] = sample_episodes.get(c_id, [])
            # If using sample episodes (e.g., US Bank), reflect that count on the card too
            for summary in campaigns:
                if summary.id == c_id and episodes_by_campaign[c_id]:
                    summary.episodes = len(episodes_by_campaign[c_id])
                    break

    # Fallback hero / top posts from sample if we computed nothing real
    if not top_er:
        sample_top = sample.get("TOP_POSTS", [])
        sample_hero = sample.get("HERO_POST")
        sample_org = sample.get("TOP_POSTS_ORGANIC", [])
    else:
        sample_top = None
        sample_hero = None
        sample_org = None

    # Per-post breakdown for SOCIAL campaigns (post-by-post table instead of
    # episode rollups). Content campaigns get this data inside each episode
    # via rollup_episode's `posts` field.
    from app.compute.episodes import _display_platform as _disp_plat
    from app.parsers.google_ads_campaign import youtube_subtype_from_post
    from app.parsers import Platform as _Plat, PostFormat as _PF, Source as _Src, Boosting as _Boost

    def _post_rows_for(posts_list, ep_defs_order=None):
        """Build display rows for one campaign's posts.

        For social campaigns with both MS-organic and Google-Ads-paid coverage of
        the same content (e.g. Spectrum NASCAR DITL — boosted on YT, also showing
        up in MS YT Shorts organic data), we merge the two into a single
        "organic + boosted" row using:
          • MS's title (more descriptive than the GAds campaign name)
          • GAds's paid impressions / spend
          • MS's organic impressions
          • Combined eng (different metrics by source, but that's the totalshown)
        Pairing heuristic: within each YT subtype, pair MS rows (boosting=BOOSTED)
        with GAds rows by sorted-by-impressions index. Works cleanly when the
        number of GAds campaigns matches the number of MS boosted videos on that
        subtype (the common case for social campaigns).
        """
        # Component ordering: when the campaign defines episodes/components,
        # attribute each post and stamp its component index so the table groups
        # MLB Minute first, then Off the Pitch, etc. (YAML order). Posts that
        # match no component sort last.
        ep_rank: dict[int, int] = {}
        if ep_defs_order:
            _rank_of = {e.id: i for i, e in enumerate(ep_defs_order)}
            for ep_id, ep_posts in attribute_posts_to_episodes(posts_list, ep_defs_order).items():
                for p in ep_posts:
                    ep_rank[id(p)] = _rank_of.get(ep_id, 998)

        rows = []
        for p in posts_list:
            if p.platform is _Plat.YOUTUBE:
                if p.source is _Src.GOOGLE_ADS_CAMPAIGN:
                    sub = youtube_subtype_from_post(p)
                    plat_key = ("youtube_preroll" if sub == "in-stream"
                                else "youtube_shorts" if sub == "shorts"
                                else "youtube_infeed")
                else:
                    plat_key = "youtube_shorts" if p.post_format is _PF.REELS_SHORTS else "youtube_infeed"
            elif p.platform is _Plat.INSTAGRAM and p.post_format is _PF.STORY:
                plat_key = "instagram_stories"
            else:
                plat_key = p.platform.value
            if plat_key == "unknown":
                continue
            from app.compute.rollup import _pick_impressions as _pi, _pick_views as _pi_views
            impr = _pi(p) or 0
            paid = p.impressions_paid or p.views_paid or 0
            # No views_organic fallback on YouTube / X / LinkedIn — on those
            # platforms views_organic is video plays, not impressions, and
            # mislabels the Organic Impressions column. Same guard as the
            # equivalent rule in episodes.py + rollup.per_campaign_channels.
            if p.platform in (_Plat.YOUTUBE, _Plat.X, _Plat.LINKEDIN):
                organic = p.impressions_organic or p.reach_organic or 0
            else:
                organic = p.impressions_organic or p.views_organic or p.reach_organic or 0
            if organic == 0 and impr > paid:
                organic = impr - paid
            eng_paid_p = p.engagements_paid or 0
            eng_tot_p = p.engagements_total or eng_paid_p or 0
            er_pct = round((eng_tot_p / impr * 100) if impr else 0.0, 2)
            # Only treat as "paid" when there's actual paid delivery (impressions
            # or spend). A BOOSTED/DARK tag with 0 paid metrics is effectively
            # organic — paused/cancelled boost or scheduled-but-not-running.
            has_paid = paid > 0 or (p.ad_spend or 0) > 0
            # See episodes.py — YT-aware organic signal. MS's broken organic-
            # impressions math collapses to None for paid YT Shorts, but
            # `organic_views` stays positive. Treat any positive organic
            # field (views, engagements, reach) as proof of organic activity.
            has_org = (
                organic > 0
                or (p.views_organic or 0) > 0
                or (p.engagements_organic or 0) > 0
                or (p.reach_organic or 0) > 0
                or p.boosting is _Boost.ORGANIC
                or not has_paid
            )
            dist = ("organic+boosted" if has_paid and has_org
                    else "paid" if has_paid
                    else "organic")
            # BrandX-specific fields. Pulled even on social campaigns so the
            # data is available everywhere — JSX picks which columns to show
            # based on campaign type. None for posts where MS doesn't report them.
            clicks = p.clicks_paid if p.clicks_paid is not None else p.link_clicks_paid
            # CTR / CPC: prefer MS-reported, else compute. MS sometimes gives
            # ctr as a fraction (0.001327) and sometimes as a percent (1.33%);
            # normalize to percent for display.
            ctr_val = p.ctr
            if ctr_val is None and impr and clicks:
                ctr_val = (clicks / impr) * 100
            elif ctr_val is not None and ctr_val < 1:
                # Looks like a fraction — convert to percent
                ctr_val = ctr_val * 100
            cpc_val = p.cpc
            if cpc_val is None and clicks and (p.ad_spend or 0) > 0:
                cpc_val = (p.ad_spend or 0) / clicks
            cpm_val = p.cpm
            if cpm_val is None and paid and (p.ad_spend or 0) > 0:
                cpm_val = (p.ad_spend or 0) / paid * 1000

            rows.append({
                "title":    (p.post_title or p.post_description or "")[:120].replace("\n", " "),
                "platform": _disp_plat(plat_key),
                # Friendly account/page name from MS (e.g. "Front Office
                # Sports" vs "Front Office Sports Today"). Lets the per-post
                # UI label which page posted when multiple FOS pages share
                # the same campaign copy.
                "accountName": p.account_name,
                "distKind": dist,
                "impr":     int(impr),
                "paidImpr": int(paid),
                "orgImpr":  int(organic),
                "views":    int(_pi_views(p)),
                "reach":    int(p.reach_total or p.reach_paid or 0),
                "eng":      int(eng_tot_p),
                "er":       er_pct,
                "spend":    round(p.ad_spend or 0, 2),
                "watchTimeMin": round(p.watch_time_min, 1) if p.watch_time_min is not None else None,
                "clicks":   int(clicks) if clicks is not None else None,
                "ctr":      round(ctr_val, 2) if ctr_val is not None else None,
                "cpc":      round(cpc_val, 2) if cpc_val is not None else None,
                "cpm":      round(cpm_val, 2) if cpm_val is not None else None,
                "videoViews100Pct": int(p.video_views_p100_paid) if p.video_views_p100_paid is not None else None,
                "videoViews3s":   int(p.video_views_3s_paid) if p.video_views_3s_paid is not None else None,
                "url":      p.post_url,
                "postedAt": p.posted_at.isoformat() if p.posted_at else None,
                # Internal hints used only by the merge pass below; removed before emit.
                "_source":  p.source.value,
                "_plat_key": plat_key,
                "_boost":   p.boosting.value if p.boosting else None,
                "_ep_rank": ep_rank.get(id(p), 999),
            })

        # ---- Merge MS-organic + GAds-paid for the same underlying post ----
        # Pair them up within each YT subtype, sorted by impressions descending,
        # so the biggest MS post merges with the biggest GAds campaign.
        for subtype in ("youtube_shorts", "youtube_infeed", "youtube_preroll"):
            ms_boosted = [r for r in rows
                          if r["_plat_key"] == subtype
                          and r["_source"] == "measure_studio"
                          and r["_boost"] in ("boosted", "dark")]
            gads = [r for r in rows
                    if r["_plat_key"] == subtype
                    and r["_source"] == "google_ads_campaign"]
            # Sort both by impressions desc; merge index-by-index.
            ms_boosted.sort(key=lambda r: r["impr"], reverse=True)
            gads.sort(key=lambda r: r["impr"], reverse=True)
            for ms_row, gads_row in zip(ms_boosted, gads):
                # MS row absorbs GAds paid metrics; GAds row gets removed.
                ms_row["paidImpr"] = int(gads_row["paidImpr"] or gads_row["impr"])
                ms_row["impr"]     = int((ms_row["orgImpr"] or 0) + ms_row["paidImpr"])
                ms_row["eng"]      = int((ms_row["eng"] or 0) + (gads_row["eng"] or 0))
                ms_row["spend"]    = round((ms_row["spend"] or 0) + (gads_row["spend"] or 0), 2)
                ms_row["distKind"] = "organic+boosted"
                ms_row["er"]       = round((ms_row["eng"] / ms_row["impr"] * 100) if ms_row["impr"] else 0.0, 2)
                # mark gads_row for removal
                gads_row["_drop"] = True

        rows = [r for r in rows if not r.get("_drop")]
        # Strip internal-only keys before emit
        for r in rows:
            for k in ("_source", "_plat_key", "_boost"):
                r.pop(k, None)

        # YouTube per-post view subtraction. MS reports the in-feed asset's
        # view count as the total plays of that underlying video, which
        # INCLUDES plays surfaced as pre-rolls. The GAds pre-roll row is its
        # own line, so the in-feed row's view count needs the pre-roll subset
        # subtracted off — otherwise the per-post table double-counts plays.
        # Same logic that runs at the episode and campaign-channel aggregates.
        preroll_views_total = sum(
            r["views"] for r in rows if r.get("platform") == "YouTube Pre-roll"
        )
        if preroll_views_total:
            infeed_rows = sorted(
                (r for r in rows if r.get("platform") == "YouTube In-feed"),
                key=lambda r: -(r.get("views") or 0),
            )
            remaining = preroll_views_total
            for r in infeed_rows:
                sub = min(remaining, r.get("views") or 0)
                r["views"] = (r.get("views") or 0) - sub
                remaining -= sub
                if remaining <= 0:
                    break

        # YT In-feed + Pre-roll on top, then everything else by post date asc
        # (campaign rollout sequence). Mirrors the episode-level sort.
        _FAR_FUTURE = "9999-12-31T00:00:00"
        def _sort_key(r):
            name = r.get("platform", "")
            date = r.get("postedAt") or _FAR_FUTURE
            if name == "YouTube In-feed":
                return (0, 0, date)
            if name == "YouTube Pre-roll":
                return (0, 1, date)
            return (1, 0, date, -r["impr"])
        # Component index leads the sort (MLB Minute before Off the Pitch, etc.);
        # within a component, the platform/date ordering above applies.
        rows.sort(key=lambda r: (r.get("_ep_rank", 999),) + _sort_key(r))
        for r in rows:
            r.pop("_ep_rank", None)
        return rows

    posts_by_campaign_display: dict[str, list] = {}
    for c in cfg["campaigns"]:
        # Social + BrandX campaigns are post-driven (no episode rollup);
        # surface per-post rows so the campaign page can render its table.
        # Content campaigns get it too — the page shows the flat post table when
        # a content campaign has no episode breakdown (e.g. Microsoft, State Farm).
        if c["type"] in ("social", "brandx", "content"):
            _ep_order = [
                EpisodeDef(
                    id=e["id"], n=e["n"], title=e["title"], date=e.get("date", ""),
                    match=e.get("match", []), exclude=e.get("exclude", []),
                    all_match=e.get("all_match", False),
                    group_ids=[int(g) for g in (e.get("group_ids") or [])],
                    manual_posts=[str(x) for x in (e.get("manual_posts") or [])],
                )
                for e in (c.get("episodes") or [])
            ]
            posts_by_campaign_display[c["id"]] = _post_rows_for(
                posts_by_campaign.get(c["id"], []), ep_defs_order=_ep_order or None)

    # Data archive manifest — one row per source file actually loaded, for the
    # Data Archive page. Audit trail of what's flowing into the dashboard.
    data_archive = _build_data_archive(cfg, exports_root, posts_by_campaign, today)

    # Average CPM by channel (active campaigns only, YT subtype-split)
    cpm_channels, cpm_blend = portfolio_cpm_by_channel(dict(posts_by_campaign), campaigns)

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
        data_archive=data_archive,
        posts_by_campaign=posts_by_campaign_display,
        portfolio_cpm_by_channel=cpm_channels,
        portfolio_cpm_blend=cpm_blend,
    )

    # ---------- Benchmarks (optional) ----------
    benchmarks_data = None
    bench_csv = REPO_ROOT / "config" / "social_benchmarks.csv"
    if bench_csv.exists():
        try:
            from app.compute.benchmarks import parse_benchmarks_csv
            benchmarks_data = parse_benchmarks_csv(bench_csv)
        except Exception as e:
            parse_warnings.append(f"benchmarks CSV: {e}")

    # ---------- Upload targets ----------
    # Per-campaign list of configured file sources, so the dashboard upload
    # form can target the exact filename refresh.py reads (e.g. E*TRADE's file
    # is portfolio_players_x_ads.csv, not etrade_x_ads.csv; ADP has two yt_paid
    # files). Without this the form guessed a name that silently no-ops.
    _FILE_SOURCE_LABELS = {
        "measure_studio": "Measure Studio",
        "youtube_paid":   "Google Ads",
        "x_ads":          "X Ads",
        "meta_ads":       "Meta Ads",
        "tiktok_ads":     "TikTok Ads",
        "linkedin_ads":   "LinkedIn Ads",
    }
    upload_targets: dict[str, list[dict]] = {}
    _all_referenced: set[str] = set()
    for c in cfg["campaigns"]:
        files: list[dict] = []
        srcs = c.get("sources", {}) or {}
        for key, label in _FILE_SOURCE_LABELS.items():
            for fn in (srcs.get(key) or []):
                files.append({"file": fn, "label": label})
        # Track every filename any campaign reads (across ALL source keys) so we
        # can flag fixture CSVs that no campaign references (orphans).
        for key in ("measure_studio", *_FILE_SOURCE_LABELS.keys(), "google_ads_campaign"):
            for fn in (srcs.get(key) or []):
                _all_referenced.add(str(fn))
        upload_targets[c["id"]] = files

    # ---------- Data Health ----------
    # Fixture CSVs that no campaign reads — usually a dashboard upload that
    # landed under an off-convention name (e.g. "BetMGM_-_Google_Ads_-_7.14.csv")
    # and never got wired. Surfaced so the team can see + fix instead of
    # wondering why an upload "did nothing".
    # Intentionally-unused fixtures we should NOT flag: manual MS CSV fallbacks
    # (API is the live source), catch-all "_other" uploads, and the legacy
    # gads_campaign fallback name. Everything else that no campaign reads is a
    # genuine orphan — usually an ad export that landed off-convention.
    _IGNORE_ORPHAN_SUFFIXES = ("_ms.csv", "_other.csv", "_gads_campaign.csv")
    orphan_files: list[str] = []
    try:
        for f in sorted(exports_root.glob("*.csv")):
            n = f.name
            if n in _all_referenced:
                continue
            if any(n.lower().endswith(s) for s in _IGNORE_ORPHAN_SUFFIXES):
                continue
            orphan_files.append(n)
    except Exception:  # noqa: BLE001
        pass

    # ---------- Measure Studio group directory ----------
    # Bake the list of MS post-groups (id + name) into data.js so the "Add
    # campaign" form can offer a name→id picker — the team picks a group by
    # name and the config gets the numeric group id it actually needs.
    ms_groups: list[dict] = []
    if ms_client is not None:
        try:
            for g in ms_client.list_groups():
                gid = g.get("id")
                name = g.get("name") or g.get("title")
                if gid is not None and name:
                    ms_groups.append({"id": int(gid), "name": str(name)})
            ms_groups.sort(key=lambda x: x["name"].lower())
        except Exception as e:
            parse_warnings.append(f"could not list MS groups for picker: {e}")

    data_health = {
        "generated_warnings": list(parse_warnings),
        "ms_errors": list(ms_fetch_errors),
        "orphan_files": orphan_files,
    }

    out_path = write_data_js(
        payload, args.output, benchmarks=benchmarks_data,
        upload_targets=upload_targets, ms_groups=ms_groups,
        data_health=data_health,
    )

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

    if ms_fetch_errors:
        # Loud, visually-distinct block at the top of attention. These are
        # NOT just warnings — campaigns are missing MS data and the operator
        # needs to act (re-run or upload fresh CSV).
        print()
        print("  " + "=" * 60)
        print("  ✗  MEASURE STUDIO FETCH ERRORS — DATA INCOMPLETE")
        print("  " + "=" * 60)
        for err in ms_fetch_errors:
            print(f"    ✗ {err}")
        print()

    # ---------- Report unattributed posts per content campaign ----------
    # MS posts that didn't match any episode (and aren't covered by manual_posts).
    # We surface these prominently because the team's mandate is: every MS post
    # must be accounted for.
    unattrib_report: list[tuple[str, list[NormalizedPost]]] = []
    for c in cfg["campaigns"]:
        c_id = c["id"]
        if not c.get("episodes"):
            continue
        posts = posts_by_campaign.get(c_id, [])
        if not posts:
            continue
        # Only check MS-source posts (Google Ads / X Ads don't go through episode attribution
        # the same way — their attribution comes from campaign-name patterns).
        ms_posts = [p for p in posts if p.source.value == "measure_studio"]
        if not ms_posts:
            continue
        ep_defs_for = [
            EpisodeDef(
                id=e["id"], n=e["n"], title=e["title"], date=e.get("date", ""),
                match=e.get("match", []), exclude=e.get("exclude", []),
                all_match=e.get("all_match", False),
                # Keep group-based attribution in sync with the real episode
                # build — without this, group-attributed posts false-flag as
                # unattributed (e.g. Sport Clips' no-text TikTok dark posts).
                group_ids=[int(g) for g in (e.get("group_ids") or [])],
                manual_posts=[str(x) for x in (e.get("manual_posts") or [])],
            )
            for e in c["episodes"]
        ]
        attributed = attribute_posts_to_episodes(ms_posts, ep_defs_for)
        attributed_ids = {p.post_id_native for posts in attributed.values() for p in posts}
        missed = [p for p in ms_posts if p.post_id_native not in attributed_ids]
        if missed:
            unattrib_report.append((c["partner"], missed))

    if unattrib_report:
        print()
        print("  ⚠  Unattributed MS posts (need manual_posts override or new keyword):")
        for partner, missed in unattrib_report:
            print(f"     [{partner}] {len(missed)} post(s):")
            for p in missed:
                title = (p.post_title or p.post_description or "(no text)")[:65].replace("\n", " ")
                print(f"       · post_id={p.post_id_native}  platform={p.platform.value}  url={p.post_url}")
                print(f"         title/desc: \"{title}\"")
    else:
        print()
        print("  ✓ All MS posts attributed to an episode.")

    # ---------- Post-count sanity check ----------
    # Per the spec: dark-only campaigns (On Location, BrandX) have a fixed
    # creative count. If a platform shows more than the expected ceiling
    # something has fan-out problems — usually an ad-platform export that
    # got broken out by daily performance, creating one row per ad-day
    # instead of one row per ad. Flag it loudly so the operator catches it
    # before the dashboard is shared.
    POST_COUNT_CEILINGS: dict[str, dict[str, int]] = {
        # campaign_id → { "platform key": ceiling }. Use lowercase keys.
        "onlocation": {  # 1 FOS Explains full episode + 3 cutdowns per platform = 4.
                          # YT gets extra slots for in-feed + pre-roll variants
                          # on the full episode plus per-cutdown YT Shorts —
                          # 6 total observed in the GAds export.
            "facebook": 4, "instagram": 4, "linkedin": 4,
            "tiktok": 4, "x": 4, "youtube": 6,
        },
    }
    from collections import Counter as _Counter
    sanity_warnings: list[str] = []
    for c in cfg["campaigns"]:
        ceilings = POST_COUNT_CEILINGS.get(c["id"])
        if not ceilings:
            continue
        plat_counts: _Counter = _Counter()
        for p in posts_by_campaign.get(c["id"], []):
            plat_counts[p.platform.value] += 1
        for plat, count in plat_counts.items():
            ceiling = ceilings.get(plat.lower())
            if ceiling is not None and count > ceiling:
                sanity_warnings.append(
                    f"[{c['partner']}] {plat}: {count} posts (expected ≤ {ceiling}). "
                    f"Likely an ad-platform export broken out by daily performance — "
                    f"re-export aggregated by ad, not by day."
                )
    if sanity_warnings:
        print()
        print("  ⚠  Per-platform post-count anomalies:")
        for w in sanity_warnings:
            print(f"     · {w}")

    print(f"\n  Open viewer/index.html to view.")
    # Non-zero exit when MS fetches failed so the shell wrapper (refresh.sh)
    # can skip the rebundle step — better to keep the last-good standalone
    # than to publish a half-empty dashboard.
    return 2 if ms_fetch_errors else 0


def _merge_x_ads_spend_into_ms(
    posts: list[NormalizedPost],
    manual_pairings: dict[str, str] | None = None,
) -> list[NormalizedPost]:
    """Pair X Ads posts with their corresponding MS X post and merge spend
    → MS post. Drops matched X Ads posts.

    Matching strategy (in order):
      0. MANUAL pairings from YAML — `x_ads_pairings: {<x_ads_name_substring>: <ms_tweet_id>}`.
         Runs first so explicit overrides always win. Case-insensitive substring match.
      1. EXACT match on `impressions_paid` — handles the common case where MS
         and X Ads report identical paid impression counts.
      2. CLOSEST match within ±5% — handles minor attribution/reporting drift.
      3. Unmatched X Ads rows (true dark posts MS can't see) are kept as own row.

    Spend is added (not replaced) on the MS post.
    """
    ms_x = [p for p in posts
            if p.platform == Platform.X
            and p.source == Source.MEASURE_STUDIO]
    x_ads = [p for p in posts if p.source == Source.X_ADS]

    if not ms_x or not x_ads:
        return posts

    drop_ids: set[int] = set()
    matched_ms_ids: set[int] = set()

    # Pre-aggregate X Ads rows that share the SAME tweet URL. Some exports emit
    # one row per ad flight even when several flights boost the same organic
    # tweet (e.g. PFP Donovan Cutdown1 + Cutdown2 both point at tweet …506).
    # Folding is single-shot per MS post, so without this only the first flight
    # merges and the rest are orphaned (their paid impressions + spend vanish).
    # Sum the duplicates into the first row; mark the others for removal.
    def _tweet_id(p):
        return (p.raw or {}).get("_tweet_id") if isinstance(p.raw, dict) else None

    _by_tweet: dict[str, list] = {}
    for xa in x_ads:
        tid = _tweet_id(xa)
        if tid:
            _by_tweet.setdefault(str(tid), []).append(xa)
    for tid, group in _by_tweet.items():
        if len(group) < 2:
            continue
        base = group[0]
        for dup in group[1:]:
            for attr in ("impressions_paid", "impressions_total",
                         "engagements_paid", "engagements_total", "ad_spend"):
                if getattr(dup, attr) is not None:
                    setattr(base, attr, (getattr(base, attr) or 0) + getattr(dup, attr))
            drop_ids.add(id(dup))   # remove the now-folded duplicate from output

    def _fold_x_ads_into_ms(t, xa) -> None:
        """Merge an X Ads campaign row's delivery numbers into MS post `t`.

        Three cases:

        1. MS already has paid (paid>0) — only add X Ads spend, nothing else
           changes. MS captured the breakdown.

        2. MS has total but NO paid breakdown (paid=0, total>0). This is the
           "post-API-break" case where MS knows the combined impressions
           but can't see what was paid vs organic. The total IS the source
           of truth — keep it. Compute organic = max(0, total − xa_paid).
           Set paid from X Ads. DO NOT add xa_paid on top of total (that
           was the old bug — Patricof/Repole/etc. were double-counting paid).

        3. MS has nothing (paid=0, no total). The boost was fully dark to MS.
           Take everything from X Ads — paid impressions become both paid and
           total, with zero organic.
        """
        xa_paid = xa.impressions_paid or 0
        xa_eng = xa.engagements_paid or 0
        ms_paid = t.impressions_paid or 0
        ms_total = t.impressions_total or 0

        if ms_paid > 0:
            # Case 1 — MS captured the breakdown. Just add spend.
            pass
        elif ms_total >= xa_paid * 0.7 and xa_paid > 0:
            # Case 2 — MS has combined total but missed the paid split.
            # ms_total is at least 70% of xa_paid → MS clearly saw the full
            # delivery (paid + organic combined) but couldn't break out the
            # paid portion. Trust ms_total; derive organic as gap.
            t.impressions_paid = xa_paid
            t.impressions_organic = max(0, ms_total - xa_paid)
            # impressions_total stays put — MS already had the right combined number.
            # Engagements: MS captured combined eng total too, so back-fill
            # paid from X Ads and derive organic from the gap.
            if xa_eng > 0:
                t.engagements_paid = xa_eng
                ms_eng_total = t.engagements_total or 0
                if ms_eng_total > 0:
                    t.engagements_organic = max(0, ms_eng_total - xa_eng)
                else:
                    t.engagements_total = xa_eng
            if t.impressions_total and t.impressions_total > 0:
                t.er = (t.engagements_total or 0) / t.impressions_total
        elif xa_paid > 0:
            # Case 3 — MS saw only the organic side (or nothing at all). The
            # X Ads boost numbers are additive on top of whatever MS reported.
            ms_org_carry = ms_total  # MS's number is the organic baseline
            t.impressions_paid = xa_paid
            t.impressions_organic = ms_org_carry if ms_org_carry > 0 else None
            t.impressions_total = (ms_org_carry or 0) + xa_paid
            if xa_eng > 0:
                t.engagements_total = (t.engagements_total or 0) + xa_eng
                t.engagements_paid = xa_eng
            if t.impressions_total and t.impressions_total > 0:
                t.er = (t.engagements_total or 0) / t.impressions_total

        t.ad_spend = (t.ad_spend or 0) + (xa.ad_spend or 0)

    # Build MS-by-tweet-ID lookup once — used by Pass 0 (URL auto-pair) and
    # Pass 0' (manual pairings).
    ms_by_id: dict[str, list] = {}
    for m in ms_x:
        if m.post_id_native:
            ms_by_id.setdefault(str(m.post_id_native), []).append(m)

    # Pass 0 — AUTO pairing via Original Tweet URL from the X Ads export.
    # When the export includes the URL column (modern X Ads exports do), the
    # parser extracts the tweet ID into raw["_tweet_id"]. Pair the X Ads row
    # directly to the MS post with that same post_id_native (tweet ID).
    # No guessing, no manual YAML pairings needed.
    for xa in x_ads:
        if id(xa) in drop_ids:          # skip duplicates already folded above
            continue
        tweet_id = (xa.raw or {}).get("_tweet_id") if isinstance(xa.raw, dict) else None
        if not tweet_id:
            continue
        targets = ms_by_id.get(str(tweet_id), [])
        unmatched = [t for t in targets if id(t) not in matched_ms_ids]
        if unmatched:
            t = unmatched[0]
            _fold_x_ads_into_ms(t, xa)
            matched_ms_ids.add(id(t))
            drop_ids.add(id(xa))

    # Pass 0' — manual pairings (YAML override). Match each X Ads row against
    # the pairings keys by case-insensitive substring, then find the MS post
    # by post_id_native (tweet ID). Runs after Pass 0 so URL pairings always
    # win when both signals are present.
    pairings = manual_pairings or {}
    if pairings:
        for xa in x_ads:
            if id(xa) in drop_ids:
                continue
            xa_name = (xa.post_title or "").lower()
            for needle, tweet_id in pairings.items():
                if needle.lower() in xa_name:
                    targets = ms_by_id.get(str(tweet_id), [])
                    unmatched = [t for t in targets if id(t) not in matched_ms_ids]
                    if unmatched:
                        t = unmatched[0]
                        _fold_x_ads_into_ms(t, xa)
                        matched_ms_ids.add(id(t))
                        drop_ids.add(id(xa))
                    break

    # For passes 1-2, MS pool is posts with paid impressions > 0 (boosted MS posts).
    ms_x_boosted = [p for p in ms_x if (p.impressions_paid or 0) > 0]
    ms_by_paid: dict[int, list] = {}
    for p in ms_x_boosted:
        ms_by_paid.setdefault(p.impressions_paid or 0, []).append(p)

    # Pass 1 — EXACT impressions_paid match
    for xa in x_ads:
        if id(xa) in drop_ids:
            continue
        xa_paid = xa.impressions_paid or 0
        if xa_paid == 0:
            continue
        candidates = [m for m in ms_by_paid.get(xa_paid, []) if id(m) not in matched_ms_ids]
        if candidates:
            target = candidates[0]
            target.ad_spend = (target.ad_spend or 0) + (xa.ad_spend or 0)
            matched_ms_ids.add(id(target))
            drop_ids.add(id(xa))

    # Pass 2 — CLOSEST within ±5%
    for xa in x_ads:
        if id(xa) in drop_ids:
            continue
        xa_paid = xa.impressions_paid or 0
        if xa_paid == 0:
            continue
        best, best_diff = None, float("inf")
        for m in ms_x_boosted:
            if id(m) in matched_ms_ids:
                continue
            m_paid = m.impressions_paid or 0
            if m_paid == 0:
                continue
            diff = abs(xa_paid - m_paid) / max(xa_paid, m_paid)
            if diff <= 0.05 and diff < best_diff:
                best, best_diff = m, diff
        if best is not None:
            best.ad_spend = (best.ad_spend or 0) + (xa.ad_spend or 0)
            matched_ms_ids.add(id(best))
            drop_ids.add(id(xa))

    return [p for p in posts if id(p) not in drop_ids]


def _apply_yt_organic_override(ep, posts: list[NormalizedPost]) -> None:
    """Apply the hardcoded YT organic-impressions override (from
    `yt_organic_impressions` in `campaigns.yaml`) to the in-feed long-form
    YouTube video in this episode. Mutates posts in place.

    MS exports a bogus-negative organic impressions count for YT long-form
    (it computes `Total - Paid` but uses GAds' interaction count for Paid,
    which exceeds the real total). GAds doesn't track YouTube's organic
    discovery impressions at all. So the operator pulls the right number
    from YouTube Studio directly and lists it in the YAML.

    Only applies to ONE post per episode: the YT long-form full-episode
    video (the in-feed post — shorts/cutdowns are excluded). After applying,
    the post is forced to render as `organic + boosted` in the dashboard.
    """
    from app.parsers.base import PostFormat, Boosting as _Boost
    if ep.yt_organic_impressions is None:
        return
    org_impr = int(ep.yt_organic_impressions)
    # Find the YT long-form video in this episode. There's exactly one per
    # episode for PFP / ADP structure (the full-episode in-feed video).
    yt_longs = [p for p in posts
                if p.platform == Platform.YOUTUBE
                and p.post_format == PostFormat.YOUTUBE_LONG]
    if not yt_longs:
        return
    # If multiple match (shouldn't happen), pick the one with the highest
    # paid impressions — that's the boosted full episode.
    target = max(yt_longs, key=lambda p: p.impressions_paid or 0)

    # Hardcoded organic count. Recompute totals so paid + organic add up.
    target.impressions_organic = org_impr
    paid = target.impressions_paid or 0
    target.impressions_total = paid + org_impr
    # Null out the views_organic / reach_organic fallbacks so the dashboard's
    # "organic impr" column doesn't pull a stale MS value when this hardcoded
    # number is the source of truth (e.g. a dark campaign with org=0).
    target.views_organic = org_impr or None
    target.reach_organic = org_impr or None
    # Force the boosting tag so downstream logic + audit tooling reads it
    # as boosted (it has both organic discovery and paid promotion).
    target.boosting = _Boost.BOOSTED


def _merge_facebook_organic_paid_pairs(posts: list[NormalizedPost]) -> list[NormalizedPost]:
    """Pair MS-reported organic + dark-ad posts of the same creative.

    Facebook, Instagram, and LinkedIn all treat organic page posts and paid
    dark ads as distinct posts — each gets its own platform_id, and MS
    surfaces them as two rows:
      • the organic post (likes/comments/shares/etc., *_organic populated,
        *_paid = 0)
      • the dark ad (*_paid populated, no organic engagement)

    The dashboard wants them as a SINGLE organic+boosted row.

    Pairing signal: same MS account (`account_handle`, which holds the
    page/account UID) AND same first ~80 chars of description AND one is
    paid-only while the other is organic-only. Conservative — won't merge
    if both candidates have any paid or any organic activity (those are
    already boosted posts, not separate organic/dark pairs).

    Originally FB-only; extended to IG + LinkedIn after the Heineken refresh
    surfaced an IG FOSN organic post (114K) sitting next to its dark-ad
    twin (also 114K, paid) as two separate rows.
    """
    if not posts:
        return posts

    PAIRING_PLATFORMS = (Platform.FACEBOOK, Platform.INSTAGRAM, Platform.LINKEDIN)
    candidates = [
        p for p in posts
        if p.platform in PAIRING_PLATFORMS
        and p.source is Source.MEASURE_STUDIO
    ]
    if len(candidates) < 2:
        return posts

    def _norm(text: str | None) -> str:
        # Collapse whitespace + lowercase the first 80 chars for grouping.
        s = (text or "").replace("\n", " ").strip().lower()
        return " ".join(s.split())[:80]

    # Group by (platform, account_handle, normalized description prefix).
    # Platform is included so an FB and IG post with the same caption don't
    # falsely merge — those are legit cross-platform posts that should each
    # render their own row.
    from collections import defaultdict as _dd
    groups: dict[tuple, list[NormalizedPost]] = _dd(list)
    for p in candidates:
        if not p.post_description:
            continue  # need text to pair
        key = (p.platform, p.account_handle or "", _norm(p.post_description))
        groups[key].append(p)

    def _has_any_metrics(p: NormalizedPost) -> bool:
        """True when MS has populated ANY delivery metric for this post.

        Used to detect the "empty placeholder twin" case — IG often surfaces
        an organic feed post and a paid Reel for the same caption as two
        separate platform_ids, and one of them may have all-None metrics
        if it hasn't synced yet. We want to drop the empty one so the live
        row stands alone.
        """
        return any([
            (p.impressions_paid or 0) > 0,
            (p.impressions_organic or 0) > 0,
            (p.impressions_total or 0) > 0,
            (p.views_paid or 0) > 0,
            (p.views_organic or 0) > 0,
            (p.views_total or 0) > 0,
            (p.reach_total or 0) > 0,
            (p.ad_spend or 0) > 0,
        ])

    drop_ids: set[int] = set()
    for key, bucket in groups.items():
        if len(bucket) != 2:
            continue  # only pair clean 1:1 cases

        # Case A: empty placeholder + live twin. IG sometimes surfaces the
        # same caption as two posts (e.g. Heineken's Champions League IG
        # post sits at DY78N3oAMwd with all-None metrics next to DY-KOIKKDNE
        # which has the real paid+organic delivery). Drop the empty one so
        # the dashboard renders one row instead of a phantom duplicate.
        with_data = [p for p in bucket if _has_any_metrics(p)]
        without_data = [p for p in bucket if not _has_any_metrics(p)]
        if len(with_data) == 1 and len(without_data) == 1:
            drop_ids.add(id(without_data[0]))
            continue

        # Case B: organic-only + paid-only pair. Identify each side. Treat
        # any organic count below a 50-impression floor as effectively zero
        # — covers the incidental-fold-over case where a dark ad picks up a
        # handful of organic impressions because the page owns it (e.g.
        # Spectrum's two FB Reels with org=2 and org=5). Without this floor
        # those would tag "organic+boosted" but the organic side is noise.
        NOISE_FLOOR = 50
        paid_only = [
            p for p in bucket
            if (p.impressions_paid or 0) > 0
            and (p.impressions_organic or 0) <= NOISE_FLOOR
        ]
        organic_only = [
            p for p in bucket
            if (p.impressions_paid or 0) == 0
            and (p.impressions_organic or 0) > 0
        ]
        if len(paid_only) != 1 or len(organic_only) != 1:
            continue  # not a clean organic+dark pair

        org_p = organic_only[0]
        paid_p = paid_only[0]

        # Merge: keep the ORGANIC post as the surviving row (it has the
        # likes/comments/shares engagement metadata that gets dropped from
        # dark ads). Copy paid impressions/spend/etc. onto it.
        org_p.impressions_paid = paid_p.impressions_paid
        org_p.impressions_total = (org_p.impressions_organic or 0) + (paid_p.impressions_paid or 0)
        org_p.views_paid = paid_p.views_paid or 0
        if (org_p.views_total or 0) < (org_p.views_paid or 0) + (org_p.views_organic or 0):
            org_p.views_total = (org_p.views_paid or 0) + (org_p.views_organic or 0)
        org_p.reach_paid = paid_p.reach_paid
        if org_p.reach_total is None or (paid_p.reach_total or 0) > (org_p.reach_total or 0):
            # Keep the larger reach (paid usually has larger reach than organic).
            org_p.reach_total = paid_p.reach_total
        # Spend, clicks, CTR: only the paid side has these.
        org_p.ad_spend = (org_p.ad_spend or 0) + (paid_p.ad_spend or 0)
        org_p.clicks_paid = (org_p.clicks_paid or 0) + (paid_p.clicks_paid or 0)
        org_p.link_clicks_paid = (org_p.link_clicks_paid or 0) + (paid_p.link_clicks_paid or 0)
        # Paid engagements add to the organic side's count.
        org_p.engagements_paid = (paid_p.engagements_paid or 0)
        org_p.engagements_total = (org_p.engagements_total or 0) + (paid_p.engagements_paid or 0)

        drop_ids.add(id(paid_p))

    if not drop_ids:
        return posts
    return [p for p in posts if id(p) not in drop_ids]


def _merge_linkedin_ads_into_ms(posts: list[NormalizedPost]) -> list[NormalizedPost]:
    """Pair LinkedIn Ads CSV rows with their MS LinkedIn post counterpart.

    MS API surfaces a LinkedIn dark/sponsored post with its organic-side
    metrics (views, viewers, watch time) and the post's URN as `post_id_native`.
    The LinkedIn Ads CSV holds the paid spend + impressions MS can't see.

    Matching strategy (in order):
      1. Exact title / headline match (LI Ads "Ad Name" or "Ad Headline" ==
         MS post title). Most reliable — LinkedIn ad operators tend to mirror
         the headline of the post they're promoting.
      2. Same-campaign 1:1 fallback — if a campaign has exactly one MS LI
         post and exactly one LI Ads row, pair them.
    """
    ms_li = [p for p in posts
             if p.platform == Platform.LINKEDIN
             and p.source == Source.MEASURE_STUDIO]
    li_ads = [p for p in posts if p.source == Source.LINKEDIN_ADS]
    if not ms_li or not li_ads:
        return posts

    drop: set[int] = set()
    matched_ms: set[int] = set()

    def _norm(s: str | None) -> str:
        return (s or "").strip().lower()

    def _fold(ms_post, ad):
        """LinkedIn Ads is paid-only. Fold its paid impressions + spend +
        engagement count onto the MS post.

        Organic side comes from MS's explicit organic fields ONLY. We do
        NOT fall back to `impressions_total` because for dark LI posts
        MS sets views=N (the paid render count, since dark = no organic)
        and the converter copies that into impressions_total — treating
        it as "organic" would double-count paid impressions onto the
        post when we then fold the ad's paid count on top.
        """
        ad_paid = ad.impressions_paid or 0
        ad_eng = ad.engagements_paid or ad.engagements_total or 0
        # Only use explicit organic fields. For a true dark post these are
        # None / 0 — and that's the correct answer (no organic).
        ms_org_impr = ms_post.impressions_organic or 0
        ms_org_eng = ms_post.engagements_organic or 0
        if ad_paid > 0:
            ms_post.impressions_paid = ad_paid
            ms_post.impressions_organic = ms_org_impr or None
            ms_post.impressions_total = ms_org_impr + ad_paid
        if ad_eng > 0:
            ms_post.engagements_paid = ad_eng
            ms_post.engagements_total = ms_org_eng + ad_eng
        ms_post.ad_spend = ad.ad_spend or 0
        ms_post.cpm = ad.cpm if ad.cpm is not None else ms_post.cpm
        if ms_post.impressions_total and ms_post.impressions_total > 0:
            ms_post.er = (ms_post.engagements_total or 0) / ms_post.impressions_total

    # Pass 1 — exact title match
    for ad in li_ads:
        ad_titles = {_norm(ad.post_title)}
        # LinkedIn ad parser stores Ad Headline / Ad Name; both end up as post_title
        # variants in raw; keep this defensive.
        raw = ad.raw if isinstance(ad.raw, dict) else {}
        for k in ("Ad Headline", "Ad Name", "Campaign Name"):
            v = raw.get(k)
            if v:
                ad_titles.add(_norm(v))
        ad_titles.discard("")
        for m in ms_li:
            if id(m) in matched_ms:
                continue
            if _norm(m.post_title) in ad_titles:
                _fold(m, ad)
                matched_ms.add(id(m))
                drop.add(id(ad))
                break

    # Pass 2 — 1:1 fallback: exactly one MS LI post + one unmatched LI Ads
    unmatched_ads = [a for a in li_ads if id(a) not in drop]
    unmatched_ms = [m for m in ms_li if id(m) not in matched_ms]
    if len(unmatched_ads) == 1 and len(unmatched_ms) == 1:
        _fold(unmatched_ms[0], unmatched_ads[0])
        drop.add(id(unmatched_ads[0]))
        matched_ms.add(id(unmatched_ms[0]))

    return [p for p in posts if id(p) not in drop]


def _merge_youtube_paid_spend_into_ms(
    posts: list[NormalizedPost],
    pair_by_sort: bool = False,
) -> list[NormalizedPost]:
    """Pair Google Ads YT campaigns with their corresponding MS YT post and
    copy spend → MS post. Drops matched Google Ads posts.

    Matching strategy — within each subtype (in-feed / shorts), require a
    **guest match** first to avoid cross-season false-pairing (the GAds export
    can carry historical S1/S2 campaigns whose paid_impr coincidentally lines
    up with current MS S3 posts):

      • MS guest comes from User Tags column `PP Episode N - <Guest>`
      • GAds guest comes from the campaign name segment after the last colon
        (e.g. "Portfolio Players S3 Ep1: Mike Repole (in-feed)" → Mike Repole)

    Pass 1 — same guest + exact paid_impr (most confident, common for shorts).
    Pass 2 — same guest + closest paid_impr (handles in-feed reporting drift).
    Pass 3 — same guest only, 1:1 unambiguous (handles cases like the original
             Repole episode where MS and GAds report very different paid counts).

    Pre-roll GAds campaigns don't have an MS counterpart and stay as their own
    rows. MS's native `ad_spend` for YT is zeroed before merging — Google Ads
    is the only trusted spend source for YouTube.
    """
    from app.parsers.google_ads_campaign import youtube_subtype_from_post
    from app.parsers.base import PostFormat
    import re as _re

    # All MS YouTube posts — including 0-paid ones. Pre-fix this filter
    # required `impressions_paid > 0`, which excluded freshly-published
    # organic YT Shorts (no paid delivery yet) from being paired with a
    # GAds row that promotes them. Pass 6's same-subtype cross-pair branch
    # needs 0-paid MS posts in the pool to fire; earlier passes 1-5 still
    # skip 0-paid posts via their own `paid > 0` checks so this doesn't
    # introduce false matches.
    ms_yt = [p for p in posts
             if p.platform == Platform.YOUTUBE
             and p.source == Source.MEASURE_STUDIO]
    # Drop dead GAds rows (0 paid impressions AND 0 spend) — these are
    # paused/cancelled campaigns that shouldn't be in the table at all
    # (e.g. the original "Allyson Felix (pre-roll)" which was superseded by
    # a "(pre-roll) - REDO" run).
    dead_gads = {id(p) for p in posts
                 if p.platform == Platform.YOUTUBE
                 and p.source == Source.GOOGLE_ADS_CAMPAIGN
                 and (p.impressions_paid or 0) == 0
                 and (p.ad_spend or 0) == 0}
    gads_yt = [p for p in posts
               if p.platform == Platform.YOUTUBE
               and p.source == Source.GOOGLE_ADS_CAMPAIGN
               and id(p) not in dead_gads]

    # Trust GAds as the only YT spend source — zero out MS's partial figure.
    for p in ms_yt:
        p.ad_spend = 0

    # Even if no MS↔GAds merge will happen, dead GAds rows should still drop.
    if not ms_yt or not gads_yt:
        return [p for p in posts if id(p) not in dead_gads]

    def _ms_subtype(p):
        return "shorts" if p.post_format is PostFormat.REELS_SHORTS else "in-feed"

    def _gads_guest(p) -> str:
        """GAds guest: campaign name segment AFTER ':', with format/tag
        suffixes stripped. Handles all of these naming conventions:
            "Portfolio Players S3 Ep1: Mike Repole (in-feed)"          → mike repole
            "Portfolio Players S3 Ep1: Mike Repole (in-feed) - REDO"   → mike repole
            "Portfolio Players S3 Ep2: Patricof Cutdown 2"             → patricof
            "Portfolio Players S3 Ep1 Trailer: Mike Repole (Short)"    → mike repole
            "PFP_S3Ep5_Assia_Cutdown1"                                 → assia
        """
        if not p.post_title:
            return ""
        # Strip parens anywhere (not just trailing) so "(in-feed)" / "(Short)" don't leak.
        t = _re.sub(r"\s*\([^)]*\)\s*", " ", p.post_title)
        # Strip " - TAG" markers (e.g. "- REDO", "- v2") at end.
        t = _re.sub(r"\s+-\s+[\w\s]+$", "", t).strip()
        # Try splitting on ":" first; if that yields nothing usable, fall back
        # to underscore-delimited shorthand like "PFP_S3Ep5_Assia_Cutdown1".
        candidates = []
        if ":" in t:
            candidates.append(t.split(":")[-1].strip())
        if "_" in t:
            # Take the underscore segment that looks like a name (skip prefixes
            # like "PFP" / "S3Ep5" and trailing tokens like "Cutdown1").
            for seg in t.split("_"):
                seg = seg.strip()
                if seg and len(seg) >= 3 and not _re.search(r"\d", seg) \
                   and seg.lower() not in ("pfp", "pp", "trailer", "cutdown", "short", "shorts", "redo"):
                    candidates.append(seg)
                    break

        for seg in candidates:
            # Strip trailing tokens like "Cutdown N", "Trailer", "Short[s]",
            # "v\d+" — anything that comes after the actual name. Repeats until
            # nothing left to strip.
            cleaned = seg
            while True:
                prev = cleaned
                cleaned = _re.sub(
                    r"\s+(Cutdown|Trailer|Short|Shorts|REDO|v)\s*\d*\s*$",
                    "", cleaned, flags=_re.IGNORECASE
                ).strip()
                cleaned = _re.sub(r"\s+\d+\s*$", "", cleaned).strip()  # bare trailing digits
                if cleaned == prev:
                    break
            words = cleaned.split()
            if 1 <= len(words) <= 4 and not any(_re.search(r"\d", w) for w in words):
                return cleaned.lower()
        return ""

    # Collect all GAds guest keys first so we can search MS posts for any of
    # them (more robust than guessing from the MS title alone).
    known_guests: set[str] = set()
    for gp in gads_yt:
        gk = _gads_guest(gp)
        if gk:
            known_guests.add(gk)

    def _ms_guest(p) -> str:
        """MS guest, derived from any signal we have. Search order matters —
        title-first so a cleanly-titled post doesn't lose to a chapter-list
        mention of another guest pasted into the description.

        Sources in priority order:
          1. Explicit `PP Episode N - Guest` in User Tags (CSV exports only)
          2. Title alone
          3. user_tags / hashtags / tags / ai_tags arrays (MS API list-of-strings)
          4. Description (last resort — chapter lists routinely mention other guests)
        """
        raw = p.raw if isinstance(p.raw, dict) else {}

        def _search(text: str) -> str | None:
            text_lc = (text or "").lower()
            for guest in known_guests:
                if guest and guest in text_lc:
                    return guest
            return None

        # 1. CSV-style "PP Episode N - Guest"
        ut_str = raw.get("User Tags") if isinstance(raw.get("User Tags"), str) else ""
        m = _re.search(r"PP Episode\s*\d+\s*-\s*([^,]+)", ut_str or "")
        if m:
            return m.group(1).strip().lower()

        # 2. Title alone — cleanest signal
        if hit := _search(p.post_title or ""):
            return hit

        # 3. Tag arrays from MS API (list-of-strings) or CSV (single string)
        def _flatten_tags(key: str) -> str:
            v = raw.get(key)
            if isinstance(v, list):
                return " ".join(str(x) for x in v)
            return str(v or "")

        tag_blob = " ".join([
            _flatten_tags("user_tags"),   # API
            _flatten_tags("hashtags"),    # API
            _flatten_tags("tags"),        # API
            _flatten_tags("ai_tags"),     # API (numeric ids — ignored but cheap)
            _flatten_tags("Post Tags"),   # CSV
            _flatten_tags("AI - Categories"),  # CSV
        ])
        if hit := _search(tag_blob):
            return hit

        # 4. Description — last resort. Often contains chapter lists that
        # mention guests from other episodes, so we save it for after title/tags.
        if hit := _search(p.post_description or ""):
            return hit

        # 5. Title-segment-before-colon fallback (e.g. "Mike Repole: How I Built…")
        title = p.post_title or ""
        if ":" in title:
            seg = title.split(":")[0].strip()
            words = seg.split()
            if 1 <= len(words) <= 4 and not any(_re.search(r"\d", w) for w in words):
                return seg.lower()
        return ""

    def _guest_match(a: str, b: str) -> bool:
        """True if these two guest keys refer to the same person. Handles:
            "jon patricof"          ↔ "patricof"             (last-name match)
            "leslie osborne"        ↔ "osborne"              (last-name match)
            "mike repole"           ↔ "mike repole"          (exact)
            "assia grazioli-venier" ↔ "assia"                (first-name match)
        """
        if not a or not b:
            return False
        if a == b:
            return True
        # Reject if either is too short to avoid spurious matches.
        if len(a) < 4 or len(b) < 4:
            return False
        a_words = a.split()
        b_words = b.split()
        # Last-name match: same last word, ≥ 4 chars.
        a_last, b_last = a_words[-1], b_words[-1]
        if a_last == b_last and len(a_last) >= 4:
            return True
        # First-name match: same first word, ≥ 4 chars.
        # Catches cases like "Assia Grazioli-Venier" ↔ "Assia" where one side
        # only has the first name (e.g. cutdown campaigns named just "Assia").
        a_first, b_first = a_words[0], b_words[0]
        if a_first == b_first and len(a_first) >= 4:
            return True
        return False

    drop_ids: set[int] = set()
    matched_ms_ids: set[int] = set()

    # Helpers at function scope so Pass 6 (cross-subtype fallback) can call
    # them after the per-subtype for-loop completes.
    def _absorb_gads(ms_post, gp):
        """Replace MS YT paid metrics with the more-accurate GAds values.
        Preserves MS's organic side so the merged row reads as
        organic+boosted in the dashboard instead of paid-only.

        Bug fixed: previously used `ms_post.views_total` as the organic-side
        baseline. On YouTube, MS's `views` field is total video plays
        (organic + paid combined per YT's counting), NOT the organic
        component — adding GAds paid to it double-counts paid views.
        Now use `views_organic` and `impressions_organic` directly (the
        converter populates them from MS's organic_views and `impressions`
        fields). For posts where MS doesn't expose organic-side data
        (e.g. true-dark), organic = 0 — no fallback to total.
        """
        gp_paid = gp.impressions_paid or 0
        gp_eng = gp.engagements_paid or gp.engagements_total or 0
        gp_views = gp.views_paid or 0

        # Organic side: use the explicit organic fields the converter set.
        # For YT long-form posts, MS reports both `organic_views` (the real
        # organic video plays — small but accurate) and `impressions` (the
        # real organic impressions count). The converter pulls both. For
        # truly-dark YT posts, organic_views = 0 and we keep it that way.
        ms_org_views = ms_post.views_organic or 0
        ms_org_impr = ms_post.impressions_organic or 0
        ms_org_eng = ms_post.engagements_organic or 0

        ms_post.ad_spend = gp.ad_spend or 0
        ms_post.cpm = gp.cpm
        ms_post.cpv = gp.cpv

        ms_post.impressions_paid = gp_paid
        ms_post.impressions_organic = ms_org_impr or None
        ms_post.impressions_total = gp_paid + ms_org_impr

        ms_post.engagements_paid = gp_eng
        ms_post.engagements_organic = ms_org_eng or None
        ms_post.engagements_total = gp_eng + ms_org_eng

        # views_total stays as MS reported it — that's the YouTube view count
        # of the underlying video (combined across organic, in-feed, pre-roll).
        # Used downstream for the "MS total YT views − GAds pre-roll views =
        # in-feed + organic" calculation. Only update paid/organic splits.
        ms_post.views_paid = gp_views
        ms_post.views_organic = ms_org_views or None
        # Don't overwrite ms_post.views_total — keep MS's number.
        if not ms_post.views_total:
            ms_post.views_total = gp_views + ms_org_views

        if gp.er is not None:
            ms_post.er = gp.er
        elif ms_post.impressions_total:
            ms_post.er = ms_post.engagements_total / ms_post.impressions_total

    def _add_gads(ms_post, gp):
        """Additively fold a SECOND GAds row into an already-merged MS post.
        Used in Pass 4 when one episode ran multiple GAds campaigns for the
        same format (e.g. original + REDO).
        """
        ms_post.ad_spend = (ms_post.ad_spend or 0) + (gp.ad_spend or 0)
        ms_post.impressions_paid = (ms_post.impressions_paid or 0) + (gp.impressions_paid or 0)
        ms_post.impressions_total = ms_post.impressions_paid + (ms_post.impressions_organic or 0)

        add_eng = gp.engagements_paid or gp.engagements_total or 0
        ms_post.engagements_paid = (ms_post.engagements_paid or 0) + add_eng
        ms_post.engagements_total = ms_post.engagements_paid + (ms_post.engagements_organic or 0)

        ms_post.views_paid = (ms_post.views_paid or 0) + (gp.views_paid or 0)
        ms_post.views_total = ms_post.views_paid + (ms_post.views_organic or 0)

        if ms_post.impressions_total and ms_post.impressions_total > 0:
            ms_post.er = (ms_post.engagements_total or 0) / ms_post.impressions_total

    for subtype in ("in-feed", "shorts"):
        ms_bucket = [p for p in ms_yt if _ms_subtype(p) == subtype]
        gads_bucket = [p for p in gads_yt if youtube_subtype_from_post(p) == subtype]
        if not ms_bucket or not gads_bucket:
            continue

        ms_guest = {id(p): _ms_guest(p) for p in ms_bucket}
        gads_guest = {id(p): _gads_guest(p) for p in gads_bucket}

        # Pass 1 — same guest + EXACT paid_impr
        for gp in gads_bucket:
            if id(gp) in drop_ids:
                continue
            gg = gads_guest[id(gp)]
            if not gg:
                continue
            gp_paid = gp.impressions_paid or 0
            cands = [m for m in ms_bucket
                     if id(m) not in matched_ms_ids
                     and _guest_match(ms_guest[id(m)], gg)
                     and (m.impressions_paid or 0) == gp_paid
                     and gp_paid > 0]
            if cands:
                _absorb_gads(cands[0], gp)
                matched_ms_ids.add(id(cands[0]))
                drop_ids.add(id(gp))

        # Pass 2 — same guest + CLOSEST paid_impr ±5%, matched GLOBALLY.
        #
        # Build every (gads, ms) candidate pair within the 5% threshold, then
        # pick them in ascending-diff order so the tightest match wins. Greedy
        # per-GAds was wrong: for RBC, GAds Panel Content (970,066) and GAds
        # ChrisPaul (974,672) were BOTH within 5% of MS Evelyn (970,131). The
        # greedy loop grabbed Evelyn for whichever GAds row was iterated first
        # (ChrisPaul, ~0.47% diff) — leaving Panel Content (~0.007% diff) to
        # fall through to Pass 5 sort and mis-pair with Legacy. Global-best
        # picks the 0.007% pair first, then ChrisPaul falls through correctly
        # to Pass 5 to pair with Legacy.
        candidate_pairs = []
        for gp in gads_bucket:
            if id(gp) in drop_ids:
                continue
            gg = gads_guest[id(gp)]
            if not gg:
                continue
            gp_paid = gp.impressions_paid or 0
            if gp_paid == 0:
                continue
            for m in ms_bucket:
                if not _guest_match(ms_guest[id(m)], gg):
                    continue
                m_paid = m.impressions_paid or 0
                if m_paid == 0:
                    continue
                diff = abs(gp_paid - m_paid) / max(gp_paid, m_paid)
                if diff <= 0.05:
                    candidate_pairs.append((diff, gp, m))
        # Sort by diff ascending; greedily consume best pairs that haven't
        # used either side yet.
        candidate_pairs.sort(key=lambda t: t[0])
        for diff, gp, m in candidate_pairs:
            if id(gp) in drop_ids or id(m) in matched_ms_ids:
                continue
            _absorb_gads(m, gp)
            matched_ms_ids.add(id(m))
            drop_ids.add(id(gp))

        # Pass 3 — same guest only (1:1 unambiguous, ignore paid_impr).
        # Handles the Repole-like case where MS and GAds disagree wildly on paid.
        for gp in gads_bucket:
            if id(gp) in drop_ids:
                continue
            gg = gads_guest[id(gp)]
            if not gg:
                continue
            cands = [m for m in ms_bucket
                     if id(m) not in matched_ms_ids
                     and _guest_match(ms_guest[id(m)], gg)]
            if len(cands) == 1:
                _absorb_gads(cands[0], gp)
                matched_ms_ids.add(id(cands[0]))
                drop_ids.add(id(gp))

        # Pass 4 — sweep remaining GAds rows. If there's an already-matched MS
        # post for the same guest, ADD (not replace) the GAds delivery onto
        # it. Handles cases like an original + REDO campaign or two parallel
        # runs against the same creative — both delivered real impressions.
        #
        # SKIPPED when `pair_by_sort` is enabled. Pass 4 assumes "same guest"
        # is a strong identity signal — true for PFP-style campaigns where
        # each episode has a unique guest name, but FALSE for partner
        # campaigns whose GAds rows all resolve to the same generic guest
        # (e.g. "rbc" for every RBC_TST_* row). Without this guard, Pass 4
        # dumped ChrisPaul + Cabana onto Evelyn just because Pass 2 happened
        # to match Evelyn first — inflating one row's impressions to 2.28M
        # and zeroing the spend on the other two. With `pair_by_sort` set,
        # the operator is signaling "guest matching is unreliable here, use
        # sort instead" — so we skip Pass 4 and let Pass 5 do the work.
        if not pair_by_sort:
            for gp in gads_bucket:
                if id(gp) in drop_ids:
                    continue
                gg = gads_guest[id(gp)]
                if not gg:
                    continue
                matched_with_guest = [m for m in ms_bucket
                                      if id(m) in matched_ms_ids
                                      and _guest_match(ms_guest[id(m)], gg)]
                if len(matched_with_guest) == 1:
                    _add_gads(matched_with_guest[0], gp)
                    drop_ids.add(id(gp))

        # Pass 5 — SORTED-POSITION FALLBACK (opt-in via `yt_paired_by_sort` YAML).
        # For campaigns whose GAds names are episode-numbered rather than
        # guest-named (e.g. ADP "Full Episode 1"), guest extraction yields the
        # series name on both sides and pass 3/4 can't disambiguate. When the
        # opt-in flag is set, pair remaining MS and GAds within this subtype
        # by sorted impressions descending.
        if pair_by_sort:
            ms_left = sorted(
                [m for m in ms_bucket if id(m) not in matched_ms_ids],
                key=lambda p: p.impressions_paid or 0, reverse=True,
            )
            gads_left = sorted(
                [g for g in gads_bucket if id(g) not in drop_ids],
                key=lambda p: p.impressions_paid or 0, reverse=True,
            )
            for m, g in zip(ms_left, gads_left):
                _absorb_gads(m, g)
                matched_ms_ids.add(id(m))
                drop_ids.add(id(g))

    # Pass 6 — Cross-subtype 1:1 fallback (no opt-in). When all subtype-bucketed
    # passes leave exactly one unmatched MS YT post AND one unmatched GAds YT
    # campaign across the whole campaign, they're almost certainly the same
    # video. Handles cases like M&M where MS classifies the post as Shorts
    # (the actual content) but the GAds campaign is named generically
    # ("M&M: Video 1") so it falls into the in-feed subtype bucket.
    unmatched_ms = [m for m in ms_yt if id(m) not in matched_ms_ids]
    unmatched_gads = [g for g in gads_yt if id(g) not in drop_ids]
    # A pre-roll (in-stream) buy is a paid ad format Measure never carries as a
    # post, so it must NEVER fold onto a Short/in-feed via this cross-subtype
    # fallback — it stays a standalone paid YT post. Without this guard the lone
    # pre-roll pairs with a lone MS Short when their impressions happen to be
    # within 50% (Prudential's "Hero (pre-roll)" was hiding inside a cutdown).
    if (len(unmatched_ms) == 1 and len(unmatched_gads) == 1
            and youtube_subtype_from_post(unmatched_gads[0]) == "in-stream"):
        unmatched_gads = []  # skip the fallback; leave pre-roll standalone
    if len(unmatched_ms) == 1 and len(unmatched_gads) == 1:
        # Belt-and-suspenders: impressions should be in the same ballpark
        # (within ±50%) to avoid pairing genuinely unrelated content.
        m_paid = unmatched_ms[0].impressions_paid or 0
        g_paid = unmatched_gads[0].impressions_paid or 0
        if m_paid and g_paid:
            diff = abs(m_paid - g_paid) / max(m_paid, g_paid)
            if diff <= 0.5:
                _absorb_gads(unmatched_ms[0], unmatched_gads[0])
                matched_ms_ids.add(id(unmatched_ms[0]))
                drop_ids.add(id(unmatched_gads[0]))
        elif m_paid == 0 and g_paid > 0:
            # Freshly-published organic MS post being promoted by a GAds
            # campaign — common when a Short drops just before the ad goes
            # live and MS hasn't accumulated paid delivery yet. With only
            # one remaining MS post AND one remaining GAds row in the whole
            # campaign, a same-subtype match is enough signal to pair them.
            # (Heineken's "Y1A4YYmNyc0" Short + "Heineken: UEFA (FOSN) -
            # Video 1 (shorts)" GAds row hit this case.)
            ms_subtype = "shorts" if unmatched_ms[0].post_format is PostFormat.REELS_SHORTS else "in-feed"
            gads_subtype_str = youtube_subtype_from_post(unmatched_gads[0])
            if ms_subtype == gads_subtype_str or (
                ms_subtype == "shorts" and gads_subtype_str == "shorts"
            ):
                _absorb_gads(unmatched_ms[0], unmatched_gads[0])
                matched_ms_ids.add(id(unmatched_ms[0]))
                drop_ids.add(id(unmatched_gads[0]))

    # Drop matched GAds rows AND any dead GAds rows (0 impressions + 0 spend).
    skip = drop_ids | dead_gads
    return [p for p in posts if id(p) not in skip]


def _git_commit_time(path: Path) -> "datetime | None":
    """Last git commit time touching `path`, as a UTC datetime — or None.

    Used instead of file mtime because CI checkouts reset mtimes to checkout
    time (so mtime always reads as "now"). The commit time is when a CSV was
    actually uploaded/committed, which is what we want for "Additional data".
    Requires full git history (the workflow checks out with fetch-depth: 0).
    """
    import subprocess
    from datetime import datetime as _dt, timezone as _tz
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cI", "--", str(path)],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=15,
        )
        s = (out.stdout or "").strip()
        if not s:
            return None
        return _dt.fromisoformat(s).astimezone(_tz.utc)
    except Exception:
        return None


def _campaign_last_updated(c: dict, exports_root: Path) -> tuple[str, str]:
    """Two freshness timestamps for a campaign, as ISO 8601 UTC strings:

      (measure_studio_ts, additional_data_ts)

    - measure_studio_ts: the current run time IF the campaign pulls from a
      Measure Studio group — MS is re-fetched fresh on every refresh, so its
      data is as current as this run. "" when there's no MS group.
    - additional_data_ts: the most recent git COMMIT time among the campaign's
      uploaded ad-platform exports (X / Google Ads / Meta / TikTok / LinkedIn /
      manual MS CSVs). Only moves when a file is actually re-uploaded for THIS
      campaign — not on every refresh. Falls back to file mtime when git
      history isn't available (e.g. an uncommitted local file). "" when none.
    """
    from datetime import datetime as _dt, timezone as _tz

    sources_cfg = c.get("sources", {}) or {}
    has_ms_live = bool(
        sources_cfg.get("measure_studio_group_id")
        or sources_cfg.get("measure_studio_group_ids")
    )
    ms_ts = _dt.now(_tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if has_ms_live else ""

    file_kinds = (
        "measure_studio", "google_ads_campaign", "youtube_paid",
        "x_ads", "meta_ads", "tiktok_ads", "linkedin_ads",
    )
    times: list[_dt] = []
    for kind in file_kinds:
        for fname in sources_cfg.get(kind, []) or []:
            path = exports_root / fname
            if not path.exists():
                continue
            ts = _git_commit_time(path) or _dt.fromtimestamp(path.stat().st_mtime, tz=_tz.utc)
            times.append(ts)
    exports_ts = max(times).strftime("%Y-%m-%dT%H:%M:%SZ") if times else ""

    return ms_ts, exports_ts


def _build_data_archive(cfg: dict, exports_root: Path, posts_by_campaign: dict,
                        today: date) -> list[dict]:
    """One entry per source file referenced in campaigns.yaml.

    For each file we record:
      - campaign_id + partner
      - source kind (measure_studio / google_ads_campaign / youtube_paid / x_ads / meta_ads / tiktok_ads)
      - filename (relative to exports_root)
      - file_size_kb (or None if missing)
      - mtime (last modified, ISO date — or "missing")
      - posts_contributed: int (how many parsed posts came from this file)

    This drives the Data Archive page so the operator can audit what's loaded.
    """
    SOURCE_KINDS = (
        "measure_studio", "google_ads_campaign", "youtube_paid",
        "x_ads", "meta_ads", "tiktok_ads", "linkedin_ads",
    )
    SOURCE_LABEL = {
        "measure_studio":      "Measure Studio",
        "google_ads_campaign": "Google Ads (YT Paid)",
        "youtube_paid":        "Google Ads (YT Paid)",
        "x_ads":               "X Ads",
        "meta_ads":            "Meta Ads",
        "tiktok_ads":          "TikTok Ads",
        "linkedin_ads":        "LinkedIn Ads",
    }
    # Map source kind → expected NormalizedPost.source.value
    SOURCE_TO_POST = {
        "measure_studio":      "measure_studio",
        "google_ads_campaign": "google_ads_campaign",
        "youtube_paid":        "google_ads_campaign",  # same parser
        "x_ads":               "x_ads",
        "meta_ads":            "meta_ads",
        "tiktok_ads":          "tiktok_ads",
        "linkedin_ads":        "linkedin_ads",
    }

    archive: list[dict] = []
    for c in cfg["campaigns"]:
        c_id = c["id"]
        sources_cfg = c.get("sources", {}) or {}
        for kind in SOURCE_KINDS:
            for fname in sources_cfg.get(kind, []) or []:
                path = exports_root / fname
                exists = path.exists()
                size_kb = round(path.stat().st_size / 1024, 1) if exists else None
                mtime = ""
                if exists:
                    from datetime import datetime as _dt
                    mtime = _dt.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
                # Count posts that came from this kind of source for this campaign
                # (we don't track per-file origin on the post, so this is a
                # per-source-kind count — close enough for audit purposes).
                expected_source = SOURCE_TO_POST[kind]
                posts_contributed = sum(
                    1 for p in posts_by_campaign.get(c_id, [])
                    if p.source.value == expected_source
                )
                archive.append({
                    "campaign_id":     c_id,
                    "partner":         c["partner"],
                    "source_kind":     kind,
                    "source_label":    SOURCE_LABEL[kind],
                    "filename":        fname,
                    "file_size_kb":    size_kb,
                    "last_modified":   mtime or "missing",
                    "exists":          exists,
                    "posts_contributed": posts_contributed,
                })

    return archive


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
        benchmark_category=cc.benchmark_category,
        lifecycle=cc.lifecycle,  # type: ignore[arg-type]
    )


if __name__ == "__main__":
    sys.exit(main())
