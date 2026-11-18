"""GA4 Data API source — total screen/page Views for configured app screens,
fed into a delivery channel (e.g. Microsoft Copilot's "FOS App").

Why REST (not the google-analytics-data client): we only need one `runReport`
call, and `google.oauth2` (already available) can mint the access token, so no
heavy client dependency is required.

Auth: a Google **service-account** key with GA4 *Viewer* access on the property.
The key is read from the environment, NEVER from config or the repo:
  - GA4_SA_JSON       — the service-account JSON, inline (GitHub Actions secret)
  - GA4_SA_JSON_FILE  — path to the JSON on disk (local .env convenience)
If neither is set, fetch_screen_views() returns a 0 result with a warning and
the caller keeps whatever was entered manually — nothing breaks.

Property: 543910325 (front-office-sports-app), GCP project fos-app-analytics.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

import requests

_RUN_REPORT = "https://analyticsdata.googleapis.com/v1beta/properties/{pid}:runReport"
_SCOPE = "https://www.googleapis.com/auth/analytics.readonly"


@dataclass
class GA4Result:
    total: int
    per_screen: dict          # {screen value: views}
    dimension: str
    warnings: list = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.warnings


def _credentials():
    """Service-account creds from GA4_SA_JSON (inline) or GA4_SA_JSON_FILE (path),
    or None when neither is configured."""
    raw = os.environ.get("GA4_SA_JSON")
    path = os.environ.get("GA4_SA_JSON_FILE")
    info = None
    if raw and raw.strip():
        info = json.loads(raw)
    elif path and os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            info = json.load(fh)
    if not info:
        return None
    from google.oauth2 import service_account  # lazy: only when GA4 is enabled
    return service_account.Credentials.from_service_account_info(info, scopes=[_SCOPE])


def _access_token(creds) -> str:
    from google.auth.transport.requests import Request
    creds.refresh(Request())
    return creds.token


def fetch_screen_views(
    property_id: str,
    screens: list[str],
    start_date,
    end_date="today",
    *,
    dimension: str = "unifiedScreenName",
    metric: str = "screenPageViews",
    timeout: int = 30,
) -> GA4Result:
    """Sum `metric` (default Views) for `screens` over [start_date, end_date].

    `dimension` is the field the screen identifiers live on — for an app
    property that is usually `unifiedScreenName` / `screenName`; if the values
    turn out to be web paths, switch to `pagePath`. Dates accept YYYY-MM-DD or
    GA4 relative dates ("today", "yesterday", "NdaysAgo").
    """
    creds = _credentials()
    if creds is None:
        return GA4Result(0, {}, dimension,
                         ["credentials not set (GA4_SA_JSON / GA4_SA_JSON_FILE) — skipped"])
    try:
        token = _access_token(creds)
    except Exception as e:  # noqa: BLE001 — surface auth failures as a warning, don't crash the build
        return GA4Result(0, {}, dimension, [f"token error: {e}"])

    body = {
        "dateRanges": [{"startDate": str(start_date), "endDate": str(end_date)}],
        "dimensions": [{"name": dimension}],
        "metrics": [{"name": metric}],
        "dimensionFilter": {
            "filter": {"fieldName": dimension, "inListFilter": {"values": list(screens)}}
        },
        "limit": 1000,
    }
    try:
        r = requests.post(
            _RUN_REPORT.format(pid=property_id),
            headers={"Authorization": f"Bearer {token}"},
            json=body, timeout=timeout,
        )
    except requests.RequestException as e:
        return GA4Result(0, {}, dimension, [f"request failed: {e}"])
    if r.status_code != 200:
        return GA4Result(0, {}, dimension, [f"runReport {r.status_code}: {r.text[:200]}"])

    per: dict[str, int] = {}
    for row in (r.json().get("rows") or []):
        name = row["dimensionValues"][0]["value"]
        try:
            val = int(row["metricValues"][0]["value"])
        except (ValueError, KeyError, IndexError):
            val = 0
        per[name] = per.get(name, 0) + val
    warnings = []
    missing = [s for s in screens if s not in per]
    if missing:
        warnings.append(f"no rows for {missing} on dimension {dimension!r} "
                        f"(wrong dimension? try pagePath)")
    return GA4Result(sum(per.values()), per, dimension, warnings)


def to_delivery_row(result: GA4Result, channel: str = "FOS App"):
    """Wrap a GA4Result as a DeliveryRow for the given impressions channel."""
    from app.parsers.delivery_log import DeliveryRow
    return DeliveryRow(
        episode_id="(ga4)", episode_date="", channel=channel,
        copilot_tagged=True, paid_spend_usd=0.0,
        impressions=int(result.total), listens_attributed=0,
        raw={"source": "ga4", "dimension": result.dimension, "per_screen": result.per_screen},
    )
