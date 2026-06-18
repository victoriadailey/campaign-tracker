# Measure Studio API — Status & Notes

## Status (as of May 2026)

User has Measure Studio enterprise tier. API access **not yet provisioned**. Working on it via Comscore rep. The tool is being built with CSV upload as the input surface — designed so the MS parser becomes an MS API client later **without changing user workflow** (uploads either way; one path manual, one path automated).

## Key facts

- Measure Studio's backend is the old **Shareablee API**, now hosted under **Comscore** (Comscore acquired Shareablee).
- Docs URL `api.shareablee.com/v1.4/docs/` 302-redirects to `core.comscore.com/api/docs/v1.4/`.
- The redirected docs URL is gated behind Comscore SSO at `auth2.comscore.com/Authenticate.aspx` — you can't read the spec without credentials.
- Public API specs (rate limits, endpoint list, auth scheme) are **not published** anywhere; the API Tracker entry is empty.

## What this means

- **No self-serve path** for credentials. Comscore must provision them — not Measure Studio support directly.
- Auth model is **likely bearer token** for machine-to-machine (consistent with how Shareablee historically operated), but OAuth 2.0 is possible. Confirm with rep.

## Email template for the Comscore/MS rep

> We're on Measure Studio enterprise and want to build an automated pipeline (GCP Cloud Run → internal dashboard) that pulls **Post Group-level** and **post-level** metrics for our sponsored campaigns. Please provision:
> 1. API credentials (service account preferred, not a named user) with read access to the Post Groups and Posts endpoints.
> 2. Access to the v1.4 API docs at `core.comscore.com/api/docs/v1.4/`.
> 3. Confirmation of the auth scheme (bearer token vs. OAuth 2.0) and rate limits.
> 4. A sample response for `GET /post-groups` and `GET /post-groups/{id}/posts` so we can design the schema.

## When credentials land

1. Add `parsers/measure_studio_api.py` implementing the same `parse()` contract as the CSV parser.
2. Add a "Sync from Measure Studio" button on the upload page that calls the API and produces the same normalized output the CSV parser produces.
3. Manual CSV upload stays as a fallback — useful when MS API has gaps (like the current YouTube paid issue).
4. Optional: add a Cloud Scheduler job that auto-syncs Live campaigns daily.

No data model changes needed. The MS API just becomes an alternate source for the same pipeline.
