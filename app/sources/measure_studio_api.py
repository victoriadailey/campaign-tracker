"""Measure Studio Enterprise API v1 client.

Replaces the manual CSV-export workflow. One paginated call to
`GET /posts?group_ids=...&period=lifetime` returns every post in a group
(organic + boosted + dark) with full inline stats — impressions_paid,
engagements_paid, ad_spend, CPM, etc. — covering everything that previously
required separate X Ads / Google Ads / Meta / LinkedIn / TikTok CSV exports.

Auth + base URL come from environment variables (loaded from `.env` at the
repo root):

    MEASURE_STUDIO_API_BASE=https://app.measure.studio/enterprise_api/v1
    MEASURE_STUDIO_API_TOKEN=<bearer token from MS dashboard>

If either var is missing or any call fails, refresh.py silently falls back
to the CSV pipeline.

Docs: https://app.measure.studio/docs/enterprise_api  (OpenAPI 3.0 spec at
/docs/enterprise_api_v1.json)

Typical use:

    from app.sources.measure_studio_api import MeasureStudioClient
    client = MeasureStudioClient.from_env()
    posts = client.fetch_group(6197)        # NormalizedPost list, ready to use
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Iterator

import requests
from dotenv import load_dotenv

from app.parsers.base import (
    Boosting,
    NormalizedPost,
    Platform,
    PostFormat,
    Source,
)


logger = logging.getLogger(__name__)

DEFAULT_BASE = "https://app.measure.studio/enterprise_api/v1"
DEFAULT_PERIOD = "lifetime"
PAGE_SIZE = 30          # API caps max_results at 30


class MeasureStudioUnavailable(RuntimeError):
    """Raised when the API is misconfigured or unreachable. Caller should
    fall back to CSV-based ingestion."""


# ---------------------------------------------------------------------------
# Platform / format mapping
# ---------------------------------------------------------------------------
_PLATFORM_FROM_MS: dict[str, Platform] = {
    "instagram":         Platform.INSTAGRAM,
    "facebook":          Platform.FACEBOOK,
    "twitter":           Platform.X,
    "youtube":           Platform.YOUTUBE,
    "tiktok":            Platform.TIKTOK,
    "linkedin":          Platform.LINKEDIN,
    "snapchat":          Platform.SNAPCHAT,
    "snapchat_profile":  Platform.SNAPCHAT,
}

_BOOSTING_FROM_MS: dict[str, Boosting] = {
    "organic":  Boosting.ORGANIC,
    "boosted":  Boosting.BOOSTED,
    "dark":     Boosting.DARK,
}

# Meta CTA button labels. MS returns these in the `title` field on FB / IG
# ad posts that use a Messenger or link-out CTA, masking the real ad copy.
# Match (case/whitespace-insensitive) and treat as empty so the dashboard
# falls back to `description`.
_META_CTA_LABELS: frozenset[str] = frozenset({
    "apply now", "book now", "chat with us", "contact us", "donate now",
    "download", "get directions", "get offer", "get quote", "get showtimes",
    "learn more", "listen now", "message us", "order now", "play game",
    "request time", "save", "see menu", "send message", "shop now", "sign up",
    "subscribe", "use app", "view event", "view shop", "watch more",
    "watch video", "buy now", "open link", "send whatsapp message", "swipe up",
})


def _format_from_ms(post_type: str | None, platform: Platform, duration_sec: float | None) -> PostFormat:
    pt = (post_type or "").lower()
    if pt in ("clips", "short", "reel", "spotlight"):
        return PostFormat.REELS_SHORTS
    if pt == "story":
        return PostFormat.STORY
    if pt in ("photo", "image", "carousel"):
        return PostFormat.STATIC
    if pt == "text":
        return PostFormat.TEXT
    if pt == "video":
        if platform is Platform.YOUTUBE:
            if duration_sec is not None and duration_sec < 90:
                return PostFormat.REELS_SHORTS
            return PostFormat.YOUTUBE_LONG
        return PostFormat.FEED_VIDEO
    return PostFormat.OTHER


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------
@dataclass
class MeasureStudioClient:
    base_url: str
    token: str

    def __post_init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Accept":        "application/json",
            "User-Agent":    "fos-campaign-tracker/0.1",
        })

    @classmethod
    def from_env(cls, dotenv_path: str | None = None) -> "MeasureStudioClient":
        """Build a client from env vars. Loads .env at repo root by default.
        Raises MeasureStudioUnavailable if either var is missing."""
        load_dotenv(dotenv_path)
        base = (os.environ.get("MEASURE_STUDIO_API_BASE") or DEFAULT_BASE).rstrip("/")
        token = (os.environ.get("MEASURE_STUDIO_API_TOKEN") or "").strip()
        if not token:
            raise MeasureStudioUnavailable(
                "MEASURE_STUDIO_API_TOKEN must be set in .env or the environment. "
                "See .env.example for the template."
            )
        return cls(base_url=base, token=token)

    # ----- low-level -----
    # Transient-error retry config. MS occasionally throws 5xx mid-pagination
    # on a healthy account; retrying with backoff almost always recovers.
    _RETRY_STATUSES = {429, 500, 502, 503, 504}
    _MAX_RETRIES = 4                # 5 total attempts (1 initial + 4 retries)
    _RETRY_BACKOFF = (2, 4, 8, 16)  # seconds between attempts

    def _get(self, path: str, **params) -> dict | list:
        import time

        url = self.base_url + path
        # Strip None params so they don't appear as "key=None" in the query.
        clean = {k: v for k, v in params.items() if v is not None}

        last_err: str | None = None
        for attempt in range(self._MAX_RETRIES + 1):
            try:
                resp = self.session.get(url, params=clean, timeout=30)
            except requests.exceptions.RequestException as e:
                last_err = f"Network error: {e}"
                if attempt < self._MAX_RETRIES:
                    time.sleep(self._RETRY_BACKOFF[attempt])
                    continue
                raise MeasureStudioUnavailable(f"{last_err} hitting {url}") from e

            # Auth / endpoint errors — don't retry, fail fast.
            if resp.status_code == 401:
                raise MeasureStudioUnavailable(
                    f"401 from {url} — check MEASURE_STUDIO_API_TOKEN is valid + unexpired."
                )
            if resp.status_code == 404:
                raise MeasureStudioUnavailable(
                    f"404 from {url} — endpoint path may be wrong."
                )

            # Transient errors — sleep + retry.
            if resp.status_code in self._RETRY_STATUSES:
                last_err = f"{resp.status_code} from {url}"
                if attempt < self._MAX_RETRIES:
                    time.sleep(self._RETRY_BACKOFF[attempt])
                    continue
                raise MeasureStudioUnavailable(
                    f"{last_err} — gave up after {self._MAX_RETRIES + 1} attempts."
                )

            resp.raise_for_status()
            return resp.json()

        # Defensive — loop should always either return or raise.
        raise MeasureStudioUnavailable(last_err or f"Unknown failure on {url}")

    # ----- discovery -----
    def info(self) -> dict:
        return self._get("/info")            # type: ignore[return-value]

    def list_accounts(self) -> list[dict]:
        return self._get("/accounts")        # type: ignore[return-value]

    def list_groups(self) -> list[dict]:
        return self._get("/groups")          # type: ignore[return-value]

    def list_tags(self) -> list[dict]:
        return self._get("/tags")            # type: ignore[return-value]

    # ----- posts -----
    def posts_page(
        self,
        group_ids: list[int] | None = None,
        account_ids: list[int] | None = None,
        post_status: list[str] | None = None,
        types: list[str] | None = None,
        period: str | None = DEFAULT_PERIOD,
        published_after: str | None = None,
        published_before: str | None = None,
        page_token: str | None = None,
        max_results: int = PAGE_SIZE,
    ) -> dict:
        """One page of /posts. The response is `{posts: [...], metadata: {...}}`.

        With `period` set, each post includes inline `stats` — that's the
        whole point of this integration (no separate /posts/{id}/stats calls).
        """
        params: dict = {
            "max_results": max_results,
            "period":      period,
            "page_token":  page_token,
        }
        if group_ids:    params["group_ids"]   = ",".join(str(g) for g in group_ids)
        if account_ids:  params["account_ids"] = ",".join(str(a) for a in account_ids)
        if post_status:  params["post_status"] = ",".join(post_status)
        if types:        params["types"]       = ",".join(types)
        if published_after:  params["published_after"]  = published_after
        if published_before: params["published_before"] = published_before
        return self._get("/posts", **params)   # type: ignore[return-value]

    def search_posts(
        self,
        group_ids: list[int] | None = None,
        period: str | None = DEFAULT_PERIOD,
        **filters,
    ) -> Iterator[dict]:
        """Yield every post matching the filters, auto-paginating."""
        token: str | None = None
        while True:
            page = self.posts_page(
                group_ids=group_ids, period=period, page_token=token, **filters,
            )
            for p in page.get("posts", []):
                yield p
            token = (page.get("metadata") or {}).get("next_page_token")
            if not token:
                return

    # ----- the one method refresh.py calls -----
    def fetch_group(
        self,
        group_id: int | list[int],
        period: str = DEFAULT_PERIOD,
    ) -> list[NormalizedPost]:
        """Returns every post in a group (or list of groups) as a list of
        NormalizedPost rows, ready to merge with the existing pipeline.

        Single API request per page (max 30 posts) with inline stats — no
        per-post follow-up calls.

        Side effect: builds a UID → display_name map from /accounts so each
        NormalizedPost carries a human-readable account_name (e.g. "Front
        Office Sports" vs "Front Office Sports Today") for the per-post UI.
        """
        gids = group_id if isinstance(group_id, list) else [group_id]
        account_names = self._account_uid_to_name()
        out: list[NormalizedPost] = []
        for raw in self.search_posts(group_ids=gids, period=period):
            try:
                p = _to_normalized_post(raw, account_names=account_names)
            except Exception:  # noqa: BLE001 - skip individual bad rows, don't fail the campaign
                logger.exception("Failed to map MS post id=%s", raw.get("id"))
                continue
            if p is not None:
                out.append(p)
        return out

    def find_post_by_native_id(
        self,
        native_id: str,
        platform_hint: Platform | None = None,
        lookback_days: int = 365,
    ) -> NormalizedPost | None:
        """Resolve a single post by its platform-native id (tweet id, YT video
        id, IG shortcode, LinkedIn URN, …).

        Used by manual_posts pins where the operator wants to attach a post
        from a different MS group (e.g. a FOS-main YT Short being promoted by
        a partner campaign whose MS group only tracks IG/FB).

        Fast path: MS indexes `platform_id`, so `/posts?query=<id>` returns the
        post in one sub-second request. Fallback (e.g. LinkedIn URNs, which
        match via URL not platform_id): scan the relevant accounts — windowed to
        `lookback_days` and cached so many pins share one scan per account. The
        original implementation scanned every account's ENTIRE lifetime history
        per pin, so 19 pins took ~18 min and blew the CI refresh budget.
        """
        account_names = self._account_uid_to_name()

        # ---- fast path: direct text query (MS indexes platform_id) ----
        # Resolves the vast majority of pins (YT / X / FB / IG / …) in one
        # sub-second request. We still require an exact native-id match so a
        # fuzzy content hit can't return the wrong post.
        try:
            page = self._get("/posts", query=native_id, period=DEFAULT_PERIOD,
                             max_results=PAGE_SIZE)
            posts = page.get("posts", []) if isinstance(page, dict) else (page or [])
            for raw in posts:
                if _native_post_id(raw) == native_id:
                    try:
                        return _to_normalized_post(raw, account_names=account_names)
                    except Exception:  # noqa: BLE001
                        logger.exception("Failed to normalise queried post %s", native_id)
                        return None
        except Exception:  # noqa: BLE001
            logger.exception("MS query lookup failed for %s; falling back to scan", native_id)

        # ---- fallback: windowed, cached account scan ----
        # Decide which accounts to scan. With a hint we filter to that
        # platform only; without it we scan every account that's authorised.
        try:
            accounts = self.list_accounts()
        except Exception:  # noqa: BLE001
            logger.exception("MS account list failed during cross-group post lookup")
            return None

        if platform_hint is not None:
            wanted_types = {k for k, v in _PLATFORM_FROM_MS.items() if v is platform_hint}
            accounts = [a for a in accounts if (a.get("account_type") or "").lower() in wanted_types]

        # Bound how far back we paginate so a missing or old pin can't trigger a
        # full lifetime-history scan of every account.
        published_after = None
        if lookback_days:
            from datetime import datetime, timedelta, timezone
            published_after = (
                datetime.now(timezone.utc) - timedelta(days=lookback_days)
            ).strftime("%Y-%m-%d")

        # Per-account cache (keyed by account + window) so resolving many pins
        # in one run scans each account at most once, instead of re-paginating
        # it per pin. Persists for the client's lifetime.
        cache = getattr(self, "_xacct_post_cache", None)
        if cache is None:
            cache = {}
            self._xacct_post_cache = cache

        # Pre-warm: fetch (windowed) and cache every candidate account up front,
        # THEN search. Returning on the first match would leave later accounts
        # unscanned, so the next pin whose post lives in a later account would
        # rescan from scratch — that's what made resolving 19 pins take ~18 min.
        # Pre-warming makes the first lookup pay for each account once and every
        # later pin an O(1) cache hit.
        ckeys: list[tuple] = []
        for acct in accounts:
            acct_id = acct.get("id")
            if acct_id is None:
                continue
            ckey = (acct_id, published_after)
            ckeys.append(ckey)
            if ckey not in cache:
                try:
                    cache[ckey] = list(
                        self.search_posts(account_ids=[acct_id], published_after=published_after)
                    )
                except Exception:  # noqa: BLE001
                    logger.exception("Cross-account fetch failed for MS account %s", acct_id)
                    cache[ckey] = []

        for ckey in ckeys:
            for raw in cache[ckey]:
                # Match against the native ID used in NormalizedPost — must
                # mirror _native_post_id's logic since pinned IDs are written
                # against that representation.
                if _native_post_id(raw) == native_id:
                    try:
                        return _to_normalized_post(raw, account_names=account_names)
                    except Exception:  # noqa: BLE001
                        logger.exception("Failed to normalise cross-account post %s", native_id)
                        return None
        return None

    def _account_uid_to_name(self) -> dict[str, str]:
        """Cached UID → display_name lookup for human-readable account labels.

        MS posts carry `account_uid` (a numeric platform ID) but not the
        display name. The /accounts endpoint has the name. We fetch it once
        per process so per-post merge work doesn't keep hitting the API.
        """
        cache = getattr(self, "_acct_cache", None)
        if cache is None:
            cache = {}
            try:
                for a in self.list_accounts():
                    uid = str(a.get("uid") or "")
                    name = a.get("display_name") or ""
                    if uid and name:
                        cache[uid] = name
            except Exception:  # noqa: BLE001 - account name is nice-to-have, not required
                logger.exception("Failed to fetch MS accounts; per-post account_name will be empty")
            self._acct_cache = cache
        return cache


# ---------------------------------------------------------------------------
# Conversion: MS post JSON → NormalizedPost
# ---------------------------------------------------------------------------
def _to_normalized_post(
    raw: dict,
    account_names: dict[str, str] | None = None,
) -> NormalizedPost | None:
    account_type = (raw.get("account_type") or "").lower()
    platform = _PLATFORM_FROM_MS.get(account_type, Platform.UNKNOWN)
    if platform is Platform.UNKNOWN:
        return None

    duration_sec = _float(raw.get("video_duration"))
    post_format = _format_from_ms(raw.get("type"), platform, duration_sec)
    boosting = _BOOSTING_FROM_MS.get((raw.get("status") or "organic").lower(), Boosting.UNKNOWN)

    stats = raw.get("stats") or {}

    # MS quirk: on YouTube (and sometimes TikTok), the export reports
    # `*_organic = *_total - *_paid` but uses Google Ads' interaction count
    # for `*_paid`, which is much larger than the real total. The math goes
    # negative. We discard negative organic values as None — the downstream
    # pipeline can derive what it needs from paid + total.
    def _nz_org(v):
        n = _int(v)
        return n if (n is not None and n >= 0) else None

    # Views (video platforms — captured first so impressions logic can fall
    # back to them on platforms where MS doesn't split impressions separately)
    views_paid = _int(stats.get("views_paid") or stats.get("paid_views") or stats.get("plays_paid"))
    views_organic = _nz_org(stats.get("views_organic") or stats.get("organic_views"))
    views_total = _int(stats.get("views_total") or stats.get("views"))

    # Impressions: paid is direct; total can be paid + organic when both are
    # sane, or just `impressions` when neither paid nor organic are usable.
    impressions_paid = _int(stats.get("impressions_paid"))
    impressions_organic = _nz_org(stats.get("impressions_organic"))
    raw_impressions = _int(stats.get("impressions_total") or stats.get("impressions")
                           or stats.get("organic_impression_count"))

    # For YouTube specifically: MS computes `impressions_organic` as
    # total - paid, but since `paid` uses GAds-imported counting that exceeds
    # the real total it goes negative. The RAW `impressions` field, however,
    # is the actual YT-reported organic impressions count and is correct.
    # Use it as the organic-side number on YT.
    if platform is Platform.YOUTUBE and impressions_organic is None and raw_impressions is not None:
        impressions_organic = raw_impressions

    # On IG / FB / TikTok / Snapchat, MS doesn't surface impressions_organic
    # separately — but it does report views_organic, and on those platforms
    # views ≈ impressions per FOS's data model (autoplay video, in-feed
    # counting). Synthesize so the dashboard math works.
    #
    # X and LinkedIn are NOT in this group:
    #   • X: tweet impressions ≠ video views (impressions count tweet-render,
    #     views require playback)
    #   • LinkedIn: a "view" is a 3-second watch, not a render
    # Facebook impressions come from `page_media_views_*` (Meta's actual
    # ad-served / page-render counts), NOT `plays_*` (which counts 3-sec
    # video plays — a strictly smaller engagement metric that's the wrong
    # source for an "impressions" column).
    #
    # This block runs BEFORE the generic VIEWS_AS_IMPRESSIONS fallback so
    # FB's page-media fields take precedence over `plays_paid` for impressions.
    # Reproducer: Heineken FB Champions League post had page_media_views_paid
    # = 86,116 but plays_paid = 76,317. The dashboard was showing 77K
    # (plays + organic) instead of MS's true 86,845 (page_media_views total).
    #
    # plays_paid is still captured separately into `video_views_3s_paid` for
    # VCR math (see further down), so this change doesn't affect video-
    # completion calculations — only the impression count.
    if platform is Platform.FACEBOOK:
        if impressions_paid is None:
            impressions_paid = _int(stats.get("page_media_views_paid"))
        if impressions_organic is None:
            impressions_organic = _nz_org(stats.get("page_media_views_organic"))

    VIEWS_AS_IMPRESSIONS = (Platform.INSTAGRAM, Platform.FACEBOOK, Platform.TIKTOK, Platform.SNAPCHAT)
    if platform in VIEWS_AS_IMPRESSIONS:
        # IG Stories + Snapchat Spotlight + Snapchat Highlight only expose
        # `views_total` (no organic/paid split). For these all-organic surfaces,
        # views_total IS the organic view count — treat it like views_organic.
        if impressions_organic is None and views_organic:
            impressions_organic = views_organic
        elif impressions_organic is None and impressions_paid is None and views_total and not views_paid:
            impressions_organic = views_total
        if impressions_paid is None and views_paid:
            impressions_paid = views_paid

    # YouTube Shorts views-as-impressions floor. Only fires for PURELY ORGANIC
    # Shorts (no paid count, no negative-organic signal). The earlier looser
    # rule incorrectly fired on dark/paid Shorts where MS reports a real
    # `impressions_paid` and `impressions_organic = -<paid>` (which collapses
    # to None via `_nz_org`) — the rule would then set
    # `impressions_organic = views_total`, doubling the paid view count into
    # the organic column. Reproducer: On Location FOS Explains Cutdown 1
    # (paid=108,923 / org=-108,884 from MS / views=106,155 from TrueView) was
    # rendering as `paid + organic = 215,078 impressions` instead of just paid.
    #
    # The fix: require BOTH `impressions_paid is None` and `impressions_organic
    # is None` before falling back to views. Paid Shorts trust MS's paid count
    # alone. Truly organic Shorts (no paid spend, no negative-organic signal)
    # still get the views-as-impressions floor they need.
    if (platform is Platform.YOUTUBE and post_format == PostFormat.REELS_SHORTS
            and impressions_paid is None
            and impressions_organic is None
            and views_total):
        impressions_organic = views_total

    if impressions_paid is not None and impressions_organic is not None:
        impressions_total = impressions_paid + impressions_organic
    elif impressions_paid is not None and (raw_impressions is None or raw_impressions < impressions_paid):
        # The raw total is suspect (e.g. YT's "553" while paid=160K) — paid is more reliable.
        impressions_total = impressions_paid
    elif impressions_organic is not None and (raw_impressions is None or raw_impressions < impressions_organic):
        # Organic-only posts (IG Stories, Snapchat Spotlight, dark social with no
        # paid spend). `raw_impressions` is often missing on these surfaces — fall
        # back to organic so impressions_total isn't lost downstream.
        impressions_total = impressions_organic
    else:
        impressions_total = raw_impressions

    # Reach (Meta / IG)
    reach_total = _int(stats.get("reach_total") or stats.get("reach"))
    reach_organic = _nz_org(stats.get("reach_organic"))
    reach_paid = _int(stats.get("reach_paid"))

    # Engagements. MS's `engagements` field is the canonical total (likes +
    # comments + shares + saves, however the platform counts engagement).
    # On YouTube + TikTok, MS's `engagements_paid` is imported from the ad
    # platform and uses a different counting model (clicks + watch progress
    # for YT, ad-platform's claimed paid eng for TT) — adding it to organic
    # double-counts. So we always trust MS's `engagements` as total and only
    # use the paid/organic split when MS itself reports them as a clean pair.
    raw_eng_total = _int(stats.get("engagements_total")) or _int(stats.get("engagements"))
    engagements_organic_raw = _nz_org(stats.get("engagements_organic"))
    engagements_paid_raw = _int(stats.get("engagements_paid"))

    engagements_total = raw_eng_total
    engagements_organic = engagements_organic_raw
    engagements_paid = engagements_paid_raw

    # Only derive missing sides when they're consistent with the total.
    # If paid + organic disagrees with the canonical total by more than ~5%,
    # trust the total and recompute paid from the gap. This catches the YT
    # / TT inflation where MS's paid is much larger than the real number.
    if (engagements_total is not None
            and engagements_organic is not None
            and engagements_paid is not None):
        computed_total = engagements_paid + engagements_organic
        if computed_total > engagements_total * 1.05:
            # Paid is inflated relative to the canonical total — derive it.
            engagements_paid = max(0, engagements_total - engagements_organic)

    # Fill missing organic from total - paid when sane.
    if engagements_organic is None and engagements_total is not None and engagements_paid is not None:
        engagements_organic = max(0, engagements_total - engagements_paid)
    # Fill missing total only if we have both sides.
    if engagements_total is None:
        if engagements_paid is not None and engagements_organic is not None:
            engagements_total = engagements_paid + engagements_organic
        elif engagements_paid is not None:
            engagements_total = engagements_paid
        elif engagements_organic is not None:
            engagements_total = engagements_organic

    # Spend / rates — paid only
    ad_spend = _float(stats.get("spend"))
    cpm = _float(stats.get("cpm"))
    cpv = _float(stats.get("cpv"))
    cpc = _float(stats.get("cpc"))
    ctr = _float(stats.get("ctr"))

    # Click + completion metrics — primary signals for paid-performance
    # campaigns. `clicks_paid` is MS's "all clicks" total. `link_clicks_paid`
    # is the link-out subset. `total_clicks` is sometimes present too.
    clicks_paid = (
        _int(stats.get("clicks_paid"))
        or _int(stats.get("total_clicks"))
    )
    link_clicks_paid = _int(stats.get("link_clicks_paid")) or _int(stats.get("link_clicks"))
    video_views_p100_paid = _int(stats.get("video_p100_watched_views"))
    # 3-second video views = Meta's standard "view started" metric. The right
    # denominator for VCR (a video that watched <3s never really started). MS
    # exposes it under different keys per platform:
    #   • IG: `three_second_views`
    #   • TikTok: `video_watched_2s_paid` (TT's analog is 2s)
    #   • FB (Reels/Clips): no separate 3-sec field — `plays_paid` is the
    #     paid play count, which is FB's "video views" denominator. (FB Reels
    #     autoplay so plays ≈ impressions, but it's the semantically correct
    #     denominator for blended VCR across IG+FB.)
    video_views_3s_paid = (
        _int(stats.get("three_second_views"))
        or _int(stats.get("video_watched_2s_paid"))
        or _int(stats.get("video_views_2s_paid"))
        or _int(stats.get("plays_paid"))
    )

    # ER: always compute fresh as engagements_total / impressions_total so
    # cross-dashboard math stays consistent.
    #
    # MS exposes several ER fields (engagement_rate, engagement_rate_reach,
    # engagement_rate_by_views_total, etc.) but each uses a different
    # denominator — `engagement_rate_reach` for TikTok runs in the 15-25%
    # range because it divides by organic unique reach (often ~1K) instead
    # of impressions. Trusting it would make WIN callouts disagree with the
    # per-post table (which always uses eng/impr). Recompute ourselves.
    er = None
    if engagements_total is not None and impressions_total:
        er = engagements_total / impressions_total

    # (impressions_total fallback handled in the block above)

    # Watch time (already in minutes for LinkedIn; seconds for Reels — TODO
    # platform-specific normalize later if needed).
    watch_time_min = _float(stats.get("watch_time_minutes"))
    if watch_time_min is None:
        secs = _float(stats.get("reels_watch_time") or stats.get("watch_time"))
        if secs is not None:
            watch_time_min = secs / 60.0

    # Estimate watch time from the quartile retention ladder when MS doesn't
    # report it directly. IG ads in particular: MS exposes p25/p50/p75/p95/p100
    # but no watch_time_minutes. We approximate via trapezoidal integration of
    # the retention curve × video duration. The estimate is rough (assumes
    # linear drop-off between quartiles) but close enough for blended
    # cross-platform avg-view-duration math on BrandX.
    if watch_time_min is None and duration_sec:
        p25 = _int(stats.get("video_p25_watched_views")) or 0
        p50 = _int(stats.get("video_p50_watched_views")) or 0
        p75 = _int(stats.get("video_p75_watched_views")) or 0
        p95 = _int(stats.get("video_p95_watched_views")) or 0
        p100 = _int(stats.get("video_p100_watched_views")) or 0
        starts = (
            _int(stats.get("three_second_views"))
            or _int(stats.get("video_watched_2s_paid"))
            or _int(stats.get("plays_paid"))
            or 0
        )
        if starts > 0 and (p25 + p50 + p75 + p95 + p100) > 0:
            # Retention at each milestone (fraction of starts who reached it)
            r0   = 1.0
            r25  = p25 / starts
            r50  = p50 / starts
            r75  = p75 / starts
            r95  = p95 / starts
            r100 = p100 / starts
            # Trapezoidal integration of retention curve (output: avg fraction
            # of the video watched per start).
            avg_fraction = (
                0.25 * (r0 + r25) / 2 +
                0.25 * (r25 + r50) / 2 +
                0.25 * (r50 + r75) / 2 +
                0.20 * (r75 + r95) / 2 +
                0.05 * (r95 + r100) / 2
            )
            total_watch_sec = avg_fraction * duration_sec * starts
            watch_time_min = total_watch_sec / 60.0

    avg_watch_time_sec = _float(
        stats.get("average_watch_time")
        or stats.get("reels_average_watch_time")
    )

    # CTA-label cleanup: for FB ads with a Messenger / link CTA, MS returns
    # the CTA button text (e.g. "Chat with us", "Sign Up", "Learn More") in
    # the `title` field instead of the post body. Clear those so the
    # dashboard falls back to `description` (the real ad copy). Matched
    # against the full set of Meta CTA labels.
    title = raw.get("title")
    if title and title.strip().lower() in _META_CTA_LABELS:
        title = None

    # Friendly account name (e.g. "Front Office Sports" vs "Front Office
    # Sports Today") so the per-post UI can label which page/handle posted
    # it. MS only carries `account_uid` here — the display name comes from
    # the /accounts map fetched at the top of `fetch_group`.
    account_uid = raw.get("account_uid")
    account_display_name = None
    if account_uid and account_names:
        account_display_name = account_names.get(str(account_uid))

    return NormalizedPost(
        source=Source.MEASURE_STUDIO,
        platform=platform,
        post_id_native=_native_post_id(raw),
        post_url=raw.get("url"),
        post_title=title,
        post_description=raw.get("description"),
        account_name=account_display_name,
        account_handle=str(account_uid) if account_uid else None,
        post_format=post_format,
        boosting=boosting,
        posted_at=_parse_dt(raw.get("published_at")),
        duration_sec=duration_sec,
        impressions_total=impressions_total,
        impressions_paid=impressions_paid,
        impressions_organic=impressions_organic,
        engagements_total=engagements_total,
        engagements_paid=engagements_paid,
        engagements_organic=engagements_organic,
        views_total=views_total,
        views_paid=views_paid,
        views_organic=views_organic,
        reach_total=reach_total,
        reach_paid=reach_paid,
        reach_organic=reach_organic,
        ad_spend=ad_spend,
        cpm=cpm,
        cpv=cpv,
        cpc=cpc,
        ctr=ctr,
        er=er,
        clicks_paid=clicks_paid,
        link_clicks_paid=link_clicks_paid,
        video_views_p100_paid=video_views_p100_paid,
        video_views_3s_paid=video_views_3s_paid,
        watch_time_min=watch_time_min,
        avg_watch_time_sec=avg_watch_time_sec,
        post_groups=[str(g) for g in (raw.get("groups") or [])],
        raw=raw,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _native_post_id(raw: dict) -> str:
    """Prefer the platform-native ID (tweet ID, YouTube video ID, IG shortcode,
    LinkedIn URN) so cross-source joining (X Ads pairings, manual_posts)
    keeps working. Fall back to the MS internal id."""
    # MS exposes platform_id directly — use it when available.
    pid = raw.get("platform_id")
    if pid:
        return str(pid)
    url = (raw.get("url") or "").strip()
    if url:
        import re
        if m := re.search(r"/status/(\d+)", url):
            return m.group(1)
        if m := re.search(r"/p/([^/?#]+)", url):
            return m.group(1)
        if m := re.search(r"(urn:li:[\w:]+)", url):
            return m.group(1)
        if m := re.search(r"/shorts/([^/?#]+)", url):
            return m.group(1)
        if m := re.search(r"v=([^/?&#]+)", url):
            return m.group(1)
    return str(raw.get("id") or "")


def _parse_dt(value) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _int(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def _float(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
