# Pulse — Tier 2 deployment guide

How to take the dashboard from "Victoria runs refresh.sh locally" to a live,
team-accessible site with self-serve CSV uploads and a 2-hourly MS data
refresh cycle.

End-to-end round trip after a CSV upload: **~2 minutes**.
Background MS API refresh: **every 2 hours** (keeps the repo under GitHub's
2,000-min/month free Actions cap for private repos; on-demand triggers are
unaffected).

---

## Architecture (one paragraph)

The React dashboard is a static site on Netlify. A GitHub Action runs every
2 hours, calls the Measure Studio API, regenerates `viewer/data.js` +
`viewer/Pulse_Dashboard_Standalone.html`, and commits them back to the repo.
Netlify auto-deploys on commit. For CSV uploads, a Netlify Function
(`netlify/functions/upload-csv.js`) accepts a file from the dashboard form,
commits it to `tests/fixtures/` via the GitHub API, and that push retriggers
the same refresh workflow. A second function (`refresh-now.js`) lets anyone
on the team trigger an immediate refresh by clicking a button instead of
waiting for the next cron.

```
Browser  →  Netlify Function  →  GitHub commit  →  GitHub Action  →  Netlify auto-deploy
(upload form)  (upload-csv.js)   (tests/fixtures)   (refresh.yml)    (~30s after commit)
```

---

## Setup checklist (one-time, ~20 min)

### 1. Push the repo to GitHub
If the project isn't already on GitHub, push it now. Note the `owner/repo`
slug — you'll use it twice below.

### 2. Create a GitHub fine-grained PAT
Personal Access Tokens → Fine-grained → New token.
- Resource owner: your org or personal account
- Repository access: select the dashboard repo only
- Permissions:
  - **Contents: Read and write** (for committing CSVs + auto-refresh)
  - **Actions: Read and write** (for the Refresh now button)
- Expiration: pick something reasonable; calendar a renewal

Copy the token — you'll need it in two places (GitHub secret + Netlify env).

### 3. Add GitHub secrets
Repo → Settings → Secrets and variables → Actions → New repository secret.
- `MEASURE_STUDIO_API_TOKEN` — your MS API token
- `MEASURE_STUDIO_API_BASE` — only if you use a non-default base URL,
  otherwise skip

Note: `GITHUB_TOKEN` is auto-injected by Actions, no need to add it.

### 4. Connect Netlify to the repo
Netlify → Add new site → Import from Git → pick the dashboard repo.

Build settings (Netlify should pick these up from `netlify.toml`):
- Publish directory: `viewer`
- Functions directory: `netlify/functions`
- Build command: none (the standalone HTML is pre-built by the workflow)

### 5. Add Netlify environment variables
Netlify → Site settings → Environment variables → Add a variable.

| Key | Value | Notes |
|---|---|---|
| `GITHUB_TOKEN` | (the PAT from step 2) | Used by both functions to commit + dispatch |
| `GITHUB_REPO` | `owner/repo` | e.g. `fos-team/campaign-tracker` |
| `GITHUB_BRANCH` | `main` | Whatever your default branch is |
| `UPLOAD_PASSWORD` | (pick one) | Share with the team via 1Password or a Slack DM |

### 6. Trigger the first refresh
Actions tab → "Refresh Pulse dashboard" → Run workflow → main.

After ~3 min you should see a `auto-refresh: ...` commit on the repo and the
Netlify deploy go live with fresh data.

### 7. Test the upload flow
- Open the dashboard's "Add Campaign Data" page
- Drop a CSV onto any campaign card
- Click **Submit & refresh**
- Enter the upload password when prompted
- You should see "✓ N files uploaded — dashboard refresh in ~2 min"
- Watch the Actions tab — a new workflow run should kick off, finish, commit,
  and Netlify will redeploy

---

## How the team uses it

### Adding new CSV data
1. Open the dashboard → "Add Campaign Data" in the sidebar
2. Scroll to the campaign card you want to update
3. Drag the CSV into the drop zone (or click to browse)
4. Pick the source from the dropdown (X Ads / Google Ads / etc.)
5. Click **Submit & refresh**
6. Wait ~2 minutes — dashboard auto-updates

If they get the password wrong, the form clears it and they'll be prompted
again on the next attempt.

### Forcing an immediate refresh
Sidebar footer → click **Refresh now**. Useful when they know MS just got
fresh data and don't want to wait up to 2 hours for the next cron run.

The "Last refresh" timestamp in the sidebar footer shows when the dashboard
data was last regenerated (UTC).

---

## What happens if something goes wrong

### Auto-refresh fails on schedule
- Check Actions tab → look for a red run
- Most common cause: MS API returned a 5xx that didn't recover within 4
  retries. The workflow exits non-zero and skips the commit, so the
  dashboard keeps the last-good data. Next 2-hourly run will retry.

### Upload returns "Wrong password"
- Password mismatch. Refresh the page, try again. The function clears the
  cached password automatically on a 401.

### Upload returns "GitHub PUT failed"
- The PAT has expired, lost permissions, or doesn't see this repo. Mint a
  new one (step 2 above) and update both the GitHub secret and the Netlify
  env var.

### Refresh runs successfully but dashboard doesn't update
- The Action only commits when data actually changed (`git diff --cached
  --quiet` check). If MS returned identical data and no CSVs changed, no
  commit happens. The "Last refresh" timestamp won't advance, but that's
  correct — there's nothing new to ship.

---

## Files added for Tier 2

- `netlify/functions/upload-csv.js` — accepts dashboard uploads, commits to repo
- `netlify/functions/refresh-now.js` — triggers workflow_dispatch
- `netlify/functions/wrap-campaign.js` — one-click "Mark as wrapped": commits a
  `lifecycle: wrapped` edit to `config/campaigns.yaml`, which auto-triggers the
  refresh workflow (that path is in refresh.yml's on-push filter)
- `.github/workflows/refresh.yml` — 2-hourly cron + dispatch + on-push refresh
- `netlify.toml` — Netlify build + function config
- `requirements.txt` — Python deps for the CI workflow
- `viewer/inputs.jsx` — `SubmitQueueRow` + real file-content upload logic
- `viewer/components.jsx` — `RefreshFooter` (last-updated + Refresh now button)
- `app/viewer/render.py` — emits `window.LAST_REFRESHED` in data.js

---

## Upgrade path if shared password isn't enough

Swap to Netlify Identity when you need per-user accounts + audit trail:
1. Site settings → Identity → Enable Identity
2. Invite team members by email
3. In both functions, replace the password check with `context.clientContext.user`
   identity validation
4. Replace the password prompt in the JSX with a Netlify Identity widget
   sign-in flow

Same architecture, just better auth. Maybe an afternoon of work when the
team is at 8-10 members and the shared password starts feeling sketchy.
