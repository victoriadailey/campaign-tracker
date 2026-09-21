# Campaign Pulse — Operator Onboarding

You're covering manual updates to the **FOS Campaign Pulse** dashboard while Victoria
(victoria@frontofficesports.com) is out. This guide gets you doing the common tasks
safely in Claude Code. When in doubt, ask Claude to follow this file.

---

## What this repo is

A static React dashboard that reports on sponsored campaigns. The data pipeline:

```
config/campaigns.yaml  →  python -m app.viewer.refresh  →  viewer/data.js
   (+ Measure Studio API + uploaded CSV exports)            →  viewer/Pulse_Dashboard_Standalone.html (bundled)
```

- **`config/campaigns.yaml`** is the source of truth — campaigns, episodes, goals, sources.
- **`./refresh.sh`** regenerates `viewer/data.js` (data) and the standalone HTML (what Netlify serves).
- **Netlify** serves the standalone at `/`. A **GitHub Action** (`.github/workflows/refresh.yml`)
  auto-regenerates on every push to `config/campaigns.yaml` or `tests/fixtures/**`, and once daily.
- Exports live in **`tests/fixtures/`** as `<campaign_id>_<kind>.csv`
  (kinds: `yt_paid`, `x_ads`, `meta_ads`, `tiktok_ads`).

## Most requests don't need you — they're self-serve on the dashboard

Point people here first. On the live site, the team can already:
- **Upload exports** — each campaign's card on **Add Campaign Data** (needs the team upload password).
  Uploads auto-wire into config; the **Data Health** banner on Overview flags anything unread.
- **Mark a campaign wrapped** — button on the campaign page.
- **Add a new campaign** — the Add Campaign form.
- **Refresh now** — sidebar button.

You're only needed for **config-level** work: adding episodes, fixing attribution/pairing,
and diagnosing "X isn't populating."

---

## ⚠️ Golden rules (read before committing anything)

1. **Never hand-push a stale `viewer/data.js`.** It's regenerated from live CSVs the team
   uploads — pushing an old copy reverts their data. Prefer committing **source only**
   (`config/campaigns.yaml` + any `app/`/`viewer/*.jsx`) and letting the GitHub Action
   regenerate `data.js` + the standalone. The Action runs whenever `config/campaigns.yaml`
   changes.
2. **Always sync before you commit.** The team pushes uploads constantly, so `origin/main`
   moves under you:
   ```bash
   git checkout -- viewer/data.js viewer/Pulse_Dashboard_Standalone.html   # drop local generated files
   git stash push config/campaigns.yaml    # (and any other source files you edited)
   git merge --ff-only origin/main
   git stash pop                            # your edits land on top of latest
   ```
3. **Run the tests** before pushing config/code changes: `.venv/bin/pytest tests/ -q`
4. **Confirm on the live site** — after pushing config, the Action regenerates in ~2 min.
   Watch it: `gh run watch $(gh run list --limit 1 --json databaseId -q '.[0].databaseId')`

---

## Common tasks

### Add a new episode (e.g. a new Portfolio Players guest)
Episodes live under a campaign's `episodes:` list. Add an entry:
```yaml
      - id: ep17
        n: "Ep. 17"
        title: "Guest Name"
        date: "TBD"
        match: ["PP Episode 17 -", "Guest Name", "LastName"]
        exclude: []
```
- The **`PP Episode N -`** token is the User Tag the social team applies — most reliable.
- Add the **guest name** and a distinctive **handle/company** so named posts match.
- Cutdowns are often **quote-titled without the guest's name** — if some show up
  unattributed after a refresh, add a distinctive **quote fragment** to `match`
  (that's how Kerri's "sleeping on couches" and Drew's "private capital" got caught).
- Matching folds accents automatically ("Lomelí" matches "Lomeli").

To find a guest's Measure posts and craft keywords:
```bash
.venv/bin/python -c "
from app.sources.measure_studio_api import MeasureStudioClient
c=MeasureStudioClient.from_env()
for p in c.search_posts(group_ids=[6197]):   # 6197 = Portfolio Players S3 x E*TRADE
    d=p if isinstance(p,dict) else p.__dict__
    t=(str(d.get('title') or '')+' '+str(d.get('description') or '')).lower()
    if 'lastname' in t: print(d.get('account_type'), repr(str(d.get('title') or d.get('description'))[:70]))
"
```

### Wrap a campaign
Find its block in `config/campaigns.yaml` and set `lifecycle: wrapped`. It drops off the
active Overview/sidebar and moves to the **Wrapped** page.

### A new export "isn't importing" (orphaned upload)
Usually the campaign's `sources:` doesn't reference the uploaded file. Uploads via the
dashboard now auto-wire, but if a file landed off-convention, add it under `sources:`
with a stable name (`<campaign_id>_<kind>.csv`) and copy the file to that name in
`tests/fixtures/`. The Data Health banner lists orphaned files.

### Google Ads shorts mis-pairing (spend on the wrong post / "$0")
When Google Ads campaigns have **generic names** ("Cutdown 1/2/3", "Video 2/3") the
guest-name pairing can't tell them apart. Add `yt_paired_by_sort: true` to the campaign —
it pairs each Google Ads row to its Measure post by sorted paid impressions. (See SSIM,
UBS, 3M for examples.)

### An organic post and its boosted ad show as two rows (should be one)
For X, pair them with `x_ads_pairings: { "<X ad campaign name>": "<MS tweet id>" }`.
The X parser also auto-pairs when the export has a Post Link column.

### A paid post shows the wrong account (e.g. "fostonight" vs "@fos")
Add `account_overrides: { fostonight: "Front Office Sports" }` to the campaign.

---

## Handy references
- **Measure group IDs**: baked into `viewer/data.js` as `window.MS_GROUPS`, and the Add
  Campaign form has a name→ID picker. Or list them: `.venv/bin/python -m app.sources`
- **Which file a campaign reads**: `window.UPLOAD_TARGETS` in `data.js`, or the `sources:`
  block in config.
- **BrandX** campaigns are exports-only (paid-social performance) — no Measure group.
- **Env**: `.env` holds `MEASURE_STUDIO_API_TOKEN` (needed for `./refresh.sh` locally).
  The Netlify functions use a `GITHUB_TOKEN` env var set in Netlify (not in the repo).

## Typical flow for a config change
```bash
git fetch origin -q && git merge --ff-only origin/main     # sync
# edit config/campaigns.yaml
.venv/bin/pytest tests/ -q                                  # tests pass
./refresh.sh                                                # regenerate + eyeball the campaign
# verify the change in viewer/data.js, then commit SOURCE ONLY:
git checkout -- viewer/data.js viewer/Pulse_Dashboard_Standalone.html
git add config/campaigns.yaml
git commit -m "…"        # end with: Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
git push origin main     # the Action regenerates data.js + standalone
```

Anything bigger or ambiguous (goals changing, a campaign behaving strangely, budgets that
don't reconcile) — park it for Victoria rather than guessing.
