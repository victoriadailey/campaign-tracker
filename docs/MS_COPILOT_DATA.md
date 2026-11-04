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
- emits **one `Megaphone Listens` row per in-window episode** (so that card shows
  episode count + true avg listens/episode for episodes *published in the flight*);
- emits a separate **`Back Catalog`** row (its own card) for pre-window episodes
  still earning in-flight listens — carrying the real back-catalog episode count;
- **supersedes** any hand-kept `Megaphone Listens` / `Back Catalog` rows in the
  delivery log.

**The Listens section rolls up into THREE cards** (via the `card:` key on each
channel_target), to keep it readable:

| Card | Rolls up | Goal |
|---|---|---|
| **Megaphone** | Megaphone Listens + Paid Promo + Back Catalog | 125,000 |
| **AudienceLift** | AudienceLift Audio | 100,000 |
| **App** | Organic App | 500 |

The underlying buckets stay separate in the data (so the campaign total and
back-catalog tracking are unaffected) — only the viewer merges them. The
Megaphone card's headline + % to goal use the **goal-bearing** members
(Megaphone Listens + Paid Promo); **Back Catalog** rides along as a sub-line
(`25 episodes · 1.6K avg listens/ep · back catalog = 4,057 listens`) with **no
contracted goal**, kept out of the % math so it doesn't distort contracted
pacing — but its listens **do** count toward the overall 14.3M campaign total.

### Pace-colored bars

Every pacing bar is colored by how far **% to goal** trails **% of flight
elapsed**: **≥20 pts behind = red**, **4–20 behind = orange**, **within 4 behind
or ahead = green**. (In a full-month back-test where elapsed = 100%, everything
reads red — that's expected; in-flight the colors track real dates.)

Verified against October data: the Custom report sums **exactly** to the
Downloads (40,141) + Streams (3,316) reports — 43,457 total delivery. Split:
**Megaphone Listens 39,400** (25 in-window episodes, avg 1,576/ep) + **Back
Catalog 4,057** (752 pre-window episodes). One export replaces manual listens entry.

### Impressions — Spotify discovery ("Spotify Discovery Events" card)

Megaphone → **Discovery Events** export gives daily Spotify impressions:

```
DATE,        DISCOVERY EVENTS
2026-10-01,  2,087
2026-10-02,  2,280
…
```

Sum the window → enter on the **`Spotify Discovery Events`** row (impressions
group), `impressions` column. (The parser also accepts `Megaphone`, `discovery
events`, etc. as aliases — see `CHANNEL_ALIASES`.) Goal: 125,000.

> **Apple note:** Discovery events are **Spotify-only**. Apple Podcasts does
> **not** report impression/discovery data to *any* host platform — it doesn't
> exist as a pullable metric. (Your Apple *listens* are already inside the
> Downloads total above, so nothing is missing on the listens side.)

### Promo impressions (X, LinkedIn, IG, YouTube/FB/TikTok) — Measure Studio

The social promo posts carrying Copilot branding come from **Measure Studio**,
like every other campaign — **not** hand-entered. Tag the Copilot promo posts
into a dedicated **Measure Studio post group** and put its id in
`sources: measure_studio_group_id:`. On refresh, those posts are **bucketed by
platform into the channel cards**:

| MS platform | Channel card |
|---|---|
| X | X |
| LinkedIn | LinkedIn |
| Instagram | IG Stories |

Each card shows the real post count + avg impressions/post. Threads isn't a
Measure Studio platform, so **Threads** (and `.com`, `Baker & Dan`, `FOS App`,
`Spotify Discovery Events`, `Spotify/Reddit/Overcast (Paid)`, `AudienceLift`)
stay on the delivery log / their own exports. The Copilot promo group only runs
on X / LinkedIn / Instagram; if a YouTube / Facebook / TikTok promo ever ships,
add a matching `channel_targets` label for it (the old catch-all "Other" card
was repurposed as the paid-audio bucket).

> **Config discipline:** a channel is fed by **either** the MS group **or**
> delivery-log rows — never both, or they'd sum. When the MS group feeds
> X / LinkedIn / IG Stories / Other, **remove those scaffold rows from the
> delivery log** so they don't add an empty placement. Keep the delivery-log
> rows only for the non-MS channels.

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
