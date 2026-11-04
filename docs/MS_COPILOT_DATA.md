# Microsoft Copilot × FOS Today — data entry

How the Copilot presenting-partner campaign gets its numbers. Unlike the
social campaigns (Measure Studio API), this one runs off a **delivery log
CSV** the team updates from Megaphone + platform exports.

- **Config:** `config/campaigns.yaml` → `id: microsoft_copilot`
- **Data file:** `tests/fixtures/microsoft_copilot_delivery_log.csv`
- **Parser:** `app/parsers/delivery_log.py`

Editing the CSV and pushing it auto-triggers the refresh (it's on the CI
`tests/fixtures/**` path), so the live dashboard rebuilds on its own.

---

## The two groups

The campaign page splits into two sections. The goal (14,346,300) is the sum.

| Group | What counts | Goal |
|---|---|---|
| **Impressions** | Any placement where Microsoft is mentioned / in the key art — promo posts, podcast discovery, .com units | 14,155,000 |
| **Listens** | Downloads + streams of the episodes (audio) | 225,500 |

Because Copilot **presents every FOS Today episode**, 100% of the show's
downloads/streams/discovery in the flight window are Copilot-attributed —
no per-episode tagging math. The show-level totals *are* the campaign numbers.

### The ad read runs on the back catalog too

The Copilot ad read + branding isn't only in the 36 new in-window episodes —
it's placed across the **back catalog** (dynamic ad insertion / baked-in
branding). So if someone listens to an **October** episode *during the flight*,
they hear the Copilot read and it counts. Two consequences:

1. **Listens ≠ sum of the 36 new episodes.** Delivery is *all* FOS Today
   listens during the flight, across the whole catalog (new + back catalog).
2. **There's a tail** — in-window episodes keep earning listens after Dec 31.
   Check with the partner whether there's a measurement window (podcast deals
   often count a +30-day download tail per episode).

**This is why the show-level export is the source of truth.** A date-ranged
`analytics-overview` / `DiscoveryEvents` export already counts every episode
played in that range — new *and* back catalog — automatically. The per-episode
rows below only see the 36 new episodes, so the delivery log carries a separate
**`(back catalog)`** row to capture the rest:

```
total Megaphone Listens = Σ(36 new-episode rows) + (back catalog row)
                        = show-level window Downloads     ← reconciliation check
```

Set the back-catalog row = show-level window Downloads **minus** the sum of the
36 new-episode rows, so nothing is double-counted. If you don't have per-episode
numbers, just put the whole show-level window total on the back-catalog row and
leave the 36 at zero — the campaign total is identical either way.

The **authoritative** cross-catalog number is the Megaphone **campaign /
DAI delivery report** (impressions served for the Copilot campaign), which
aggregates across the whole catalog by design — see API ask B.

---

## Where each number comes from

### Listens (downloads + streams) — Megaphone

Megaphone → **Analytics → Overview**, set the date range to the flight window,
**Export**. You get one summary row like:

```
Plays, Confirmed reach by plays, Episode completion %, Streams, …, Downloads, Downloads reach
3458,  689,                      33,                    3316,    …, 40141,     19205
```

- **Downloads** → the headline listens number. This is host-side and
  **platform-agnostic — it already includes Apple, Spotify, Overcast, etc.**
- **Streams** → on-platform plays (mostly Spotify). Add to downloads for total
  "listens," or keep as its own line.

Enter into the delivery log:
- `Megaphone Listens` row → `listens_attributed` = Downloads
- (optional) a `Megaphone Listens` or `Other` row for Streams if you track it
  separately.

#### Better: auto-ingest the Custom report (per-episode + back catalog)

Instead of hand-keying, export Megaphone's **Custom report** for the flight
window (Analytics → Custom report → per-episode, with Downloads + Streams +
Streaming Ad Insertion opt-in). Drop it in `tests/fixtures/` and uncomment the
`megaphone_custom_report:` source in `campaigns.yaml`. On refresh it:

- filters to the podcast (`megaphone.podcast_title`) and, by default, to
  episodes with Streaming Ad Insertion on (the ones carrying the DAI read);
- emits **one `Megaphone Listens` row per in-window episode** (so the card shows
  episode count + avg listens/episode) **plus one `(back catalog)` row** for
  pre-window episodes' in-flight listens;
- **supersedes** any hand-kept `Megaphone Listens` rows in the delivery log.

Verified against October data: the Custom report sums **exactly** to the
Downloads (40,141) + Streams (3,316) reports — 43,457 total delivery, of which
~9.3% came from back catalog. One export replaces the manual listens entry.

> Note: the `(back catalog)` row currently counts as one "episode" in the card's
> episode count/average (26 vs 25 for October). Minor; tell me if you'd rather
> it render as its own separate card under Listens.

### Impressions — Spotify discovery (Megaphone "Discovery Events")

Megaphone → **Discovery Events** export gives daily Spotify impressions:

```
DATE,        DISCOVERY EVENTS
2026-10-01,  2,087
2026-10-02,  2,280
…
```

Sum the window → enter on the `Megaphone` row (impressions group),
`impressions` column.

> **Apple note:** Discovery events are **Spotify-only**. Apple Podcasts does
> **not** report impression/discovery data to *any* host platform — it doesn't
> exist as a pullable metric. (Your Apple *listens* are already inside the
> Downloads total above, so nothing is missing on the listens side.)

### Promo impressions (X, LinkedIn, Threads, IG, .com, Baker & Dan)

These come from the usual places (Measure Studio / native platform / .com
analytics). Enter each channel's cumulative impressions on its row, or add one
row per post for a true post count + avg/post.

### Paid (AudienceLift audio, Paid Promo, :30 spots)

From the media partner / Spotify Ad Analytics UI. Enter on `AudienceLift`,
`AudienceLift Audio`, and `Paid Promo` rows. (Auto-pull is blocked — see
"Spotify Ad Analytics API" below.)

---

## The delivery log format

One row per placement. Columns that matter:

| Column | Notes |
|---|---|
| `episode_id` | `ep-YYYY-MM-DD` for episode rows; `(flight)` for aggregates |
| `episode_date` | ISO date (episode rows) |
| `channel` | **must match a `channel_targets` label** (parser canonicalizes common aliases — see `CHANNEL_ALIASES`) |
| `copilot_tagged` | `TRUE` to count. Untagged placements don't carry the logo → not delivered, but still tracked for % compliance |
| `impressions` | impressions-group delivery |
| `listens_attributed` | listens-group delivery (used when `impressions` is blank) |

The file is **pre-seeded** with 36 weekday episode rows (Nov 9–Dec 31, minus
Thanksgiving/day-after/Christmas) plus one scaffold row per channel. Just paste
numbers into the blank metric columns — or split a scaffold row into per-post
rows for a real post count.

### Two ways to log a channel
- **Cumulative:** keep the one scaffold row, drop the window total in. Card
  shows "1 post."
- **Per-post / per-episode:** add a row per post. Card shows the real count +
  avg/post (or avg listens/episode for the podcast).

---

## Spotify Ad Analytics API — status (blocked)

We have the Service Account Key (key + secret) in `.env`
(`SPOTIFY_AD_ANALYTICS_CLIENT_ID` / `_SECRET`). But:

- The old Podsights API host (`api.podsights.com`) is dead.
- `adanalytics.spotify.com/api/*` only serves the web-app shell — the real
  REST host is **undocumented and issued through an account rep**.
- Even working, Spotify Ad Analytics is a **paid-attribution** platform — it
  would give paid promo/AudienceLift impressions, **not** organic downloads
  (those come from Megaphone, above).

**To unblock:** ask the Spotify Ad Analytics rep for the API base URL + docs
(draft in `docs/MS_COPILOT_API_ASK.md`). Until then, paid numbers are entered
by hand from the UI.

## Megaphone API — status (content only)

`MEGAPHONE_API_TOKEN` works for the **content** API (episode list, titles,
dates — FOS Today UUID `0eccb792-8223-11ed-8ea9-4b4b76c4d47c`) but **not**
analytics: every downloads/metrics endpoint 404s, and the Organization API
(paid promos) returns 403 (token isn't org-scoped). So downloads come from the
dashboard export, not the API. An org/analytics-scoped token would change this.
