# API access ask — Spotify technical account manager

One combined email to our Spotify TAM covering both gaps blocking a fully
automated Copilot × FOS Today reporting feed: Spotify Ad Analytics API access
and Megaphone analytics access. (Spotify owns Megaphone, so one rep can route
both.) Copy-paste below; fill in [name].

---

**To:** our Spotify technical account manager
**Subject:** API access for automated reporting — Spotify Ad Analytics + Megaphone

> Hi [name],
>
> We're automating a partner-reporting dashboard for a presenting-sponsor
> campaign on our Megaphone-hosted show (FOS Today), and we'd like to pull
> delivery data programmatically from both Spotify Ad Analytics and Megaphone.
> Could you point us to the right API docs/credentials — or loop in the right
> people — for the following?
>
> **1. Spotify Ad Analytics API**
> We have a **Service Account Key** (key + secret) generated under Manage → API
> key. We need:
>   - the **API base URL** and **developer docs** for programmatic access with
>     that key;
>   - the **auth format** — do we pass the key/secret as a header, or exchange
>     them for a bearer token at a token endpoint? An example request would help;
>   - the **endpoints** for campaign / promo delivery (impressions, reach, spend)
>     with a date-range filter.
>
>   For context: `api.podsights.com` no longer resolves, and
>   `adanalytics.spotify.com/api/*` only returns the web app, so we can't locate
>   the REST host on our own.
>
> **2. Megaphone analytics API**
> Our current Megaphone token works for the content API (podcasts/episodes) but
> not analytics. We need:
>   - a **campaign / DAI delivery report** — our ad read is dynamically inserted
>     across the **whole catalog** (new + back-catalog episodes), so we need the
>     impressions served *for that campaign* across all episodes in a date range,
>     not just new-episode downloads;
>   - **downloads + streams + discovery events** by date range (show-level and,
>     ideally, per-episode) — every analytics path we try
>     (`/networks/{id}/podcasts/{id}/analytics`, `/metrics`, `/downloads`)
>     returns **404** with our token;
>   - **organization-scoped access** — `/organizations/{id}` and its sub-paths
>     (campaigns/promos for paid spots + AudienceLift) return **403**, so our
>     token appears to lack org scope. Can you issue an analytics/org-scoped
>     token, or tell us how to authorize the existing one?
>
>   Megaphone Network ID: `0839aeca-f930-11ec-8a88-e3b56f71adad`
>   Megaphone Organization ID: `f926b7d4-f92f-11ec-99a7-2b87d2fee883`
>
> If Megaphone download/campaign analytics is only exposed through the Spotify
> Ad Analytics API rather than Megaphone directly, just let us know and we'll
> consolidate there.
>
> Thanks so much!

---

### What this unlocks

| Gap | Unblocks |
|---|---|
| Spotify Ad Analytics API | Auto-pull of paid promo + AudienceLift audio delivery |
| Megaphone campaign/DAI report | Ad-read delivery across the whole catalog (incl. back catalog) |
| Megaphone analytics token | Downloads/streams/discovery by date range — replaces the dashboard-export step |

Until these land, the dashboard runs off: **Measure Studio** (social impressions),
the **Megaphone Custom report** export (listens — see `MS_COPILOT_DATA.md`), and
manual entry for paid audio.
