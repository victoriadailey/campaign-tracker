# API access asks — Copilot × FOS Today automation

Two short, forwardable requests to close the two gaps blocking a fully
automated refresh. Send A to the Spotify Ad Analytics account rep, B to
Megaphone support.

---

## A. Spotify Ad Analytics — API base URL + docs

**To:** our Spotify Ad Analytics rep
**Subject:** Spotify Ad Analytics — API access for a Service Account Key

> Hi [name],
>
> We're automating a partner reporting dashboard and want to pull our
> campaign/promo delivery (impressions, reach, spend for AudienceLift audio and
> paid podcast spots) programmatically from Spotify Ad Analytics.
>
> We already have a **Service Account Key** (key + secret) generated under
> Manage → API key. Could you point us to:
>
> 1. The **API base URL** and **developer docs** for programmatic access with
>    that Service Account Key.
> 2. The **auth format** — do we send the key/secret as a header, or exchange
>    them for a bearer token at a token endpoint? An example request would be
>    ideal.
> 3. The **endpoints** for campaign / promo delivery metrics (impressions,
>    reach, spend), ideally with a date-range filter.
>
> For context: `api.podsights.com` no longer resolves, and
> `adanalytics.spotify.com/api/*` only returns the web app, so we can't find the
> REST host on our own. Anything you can share — docs link, Postman collection,
> or the base URL — gets us the rest of the way.
>
> Thanks!

---

## B. Megaphone — analytics-scoped API token

**To:** Megaphone support (support@megaphone.fm) / our account manager
**Subject:** API token with analytics + organization scope

> Hi,
>
> Our current API token (CMS/content scope) works for the content endpoints —
> we can list podcasts and episodes fine. But we'd like to pull **analytics**
> programmatically and are hitting walls:
>
> 1. **Campaign / DAI delivery report** — our highest priority. We run a
>    presenting partnership whose ad read is dynamically inserted across the
>    **whole catalog** (new + back-catalog episodes), so we need the
>    impressions served *for that campaign* across all episodes in a date range,
>    not just new-episode downloads. Is there a campaign/ad delivery report
>    endpoint for this? (It likely lives under the Organization API — see #3.)
> 2. **Show / per-episode downloads + streams** — every analytics path we try
>    (e.g. `/networks/{id}/podcasts/{id}/analytics`, `/metrics`, `/downloads`)
>    returns **404** with our token. Is there an **analytics-scoped token** or a
>    different endpoint/report API for download & stream counts? We'd want
>    downloads, streams, and discovery events by date range (show-level and,
>    ideally, per-episode).
> 3. **Organization API** (campaigns / promos for paid spots + AudienceLift) —
>    `/organizations/{id}` and its sub-paths return **403** with our token, so
>    it appears to lack org scope. Can you issue a token with organization
>    access, or tell us how to authorize the existing one?
>
> Network ID: `0839aeca-f930-11ec-8a88-e3b56f71adad`
> Organization ID: `f926b7d4-f92f-11ec-99a7-2b87d2fee883`
>
> If downloads analytics is only available via the Spotify Ad Analytics
> integration rather than the Megaphone API directly, just let us know and
> we'll go that route.
>
> Thanks!

---

### What each unlocks

| Ask | Unblocks |
|---|---|
| A (Spotify Ad Analytics API) | Auto-pull of paid promo + AudienceLift audio delivery |
| B (Megaphone analytics token) | Auto-pull of the campaign/DAI delivery report (ad reads across the whole catalog, incl. back catalog) + organic downloads/streams + discovery events (replaces the dashboard export step) |

Until either lands, the dashboard runs off the Megaphone dashboard exports →
`microsoft_copilot_delivery_log.csv` (see `MS_COPILOT_DATA.md`).
