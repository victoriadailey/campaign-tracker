// Netlify Function: receive a CSV upload from the dashboard, validate it,
// and commit it to the GitHub repo under tests/fixtures/. The commit triggers
// the GitHub Actions refresh workflow, which regenerates data.js and
// Netlify auto-redeploys. End-to-end round trip is ~2 minutes.
//
// Required env vars (set in Netlify → Site settings → Environment variables):
//   GITHUB_TOKEN        — fine-grained PAT with `Contents: Read & write` on the dashboard repo
//   GITHUB_REPO         — "owner/repo" (e.g. "fos-team/campaign-tracker")
//   GITHUB_BRANCH       — typically "main"
//   UPLOAD_PASSWORD     — shared team password the dashboard prompts for
//
// Request body (JSON):
//   {
//     password: "...",
//     campaign_id: "etrade",
//     source: "x_ads" | "yt_paid" | "meta_ads" | "tiktok_ads" | "linkedin_ads" | "other",
//     filename: "etrade_x_ads.csv",   // sanitized by the function
//     content_base64: "..."           // base64-encoded file content
//   }

const PATH_PREFIX = 'tests/fixtures/';

// Filename safety: only allow [A-Za-z0-9._-], cap at 80 chars, require .csv/.tsv/.txt.
function sanitizeFilename(name) {
  const clean = String(name || '').replace(/[^A-Za-z0-9._-]/g, '_').slice(0, 80);
  if (!/\.(csv|tsv|txt)$/i.test(clean)) return null;
  return clean;
}

// Force the filename to start with a known campaign_id prefix so a typo in
// the form can't overwrite an unrelated fixture.
function namespacedFilename(campaign_id, filename) {
  if (!filename) return null;
  if (!campaign_id || !/^[a-z0-9_]+$/i.test(campaign_id)) return null;
  // If the filename already starts with the campaign id, keep it; otherwise
  // prepend so uploads land in a predictable spot.
  if (filename.toLowerCase().startsWith(campaign_id.toLowerCase())) return filename;
  return `${campaign_id}_${filename}`;
}

exports.handler = async (event) => {
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: JSON.stringify({ error: 'POST only' }) };
  }

  const {
    GITHUB_TOKEN, GITHUB_REPO,
    GITHUB_BRANCH = 'main',
    UPLOAD_PASSWORD,
  } = process.env;

  if (!GITHUB_TOKEN || !GITHUB_REPO || !UPLOAD_PASSWORD) {
    return {
      statusCode: 500,
      body: JSON.stringify({ error: 'Server not configured. Missing env vars.' }),
    };
  }

  let body;
  try { body = JSON.parse(event.body || '{}'); }
  catch { return { statusCode: 400, body: JSON.stringify({ error: 'Invalid JSON' }) }; }

  const { password, campaign_id, filename: rawName, content_base64, exact_target } = body;

  if (password !== UPLOAD_PASSWORD) {
    return { statusCode: 401, body: JSON.stringify({ error: 'Wrong password' }) };
  }
  if (!campaign_id || !content_base64) {
    return { statusCode: 400, body: JSON.stringify({ error: 'Missing campaign_id or content_base64' }) };
  }

  const safe = sanitizeFilename(rawName);
  if (!safe) {
    return { statusCode: 400, body: JSON.stringify({ error: 'Filename must end in .csv, .tsv, or .txt' }) };
  }
  // `exact_target` means the dashboard resolved this name from the campaign's
  // configured sources (UPLOAD_TARGETS) — use it verbatim. Otherwise namespace
  // it under the campaign id so a stray upload can't clobber another fixture.
  // Without this, files whose configured name doesn't start with the campaign
  // id (e.g. etrade → portfolio_players_x_ads.csv) got a wrong "etrade_" prefix
  // and the refresh silently kept reading the old file.
  const finalName = exact_target ? safe : namespacedFilename(campaign_id, safe);
  if (!finalName) {
    return { statusCode: 400, body: JSON.stringify({ error: 'Invalid campaign_id' }) };
  }

  // Size sanity check on the base64 payload (raw bytes ~ 0.75x the b64 length).
  // Cap at 20 MB raw to avoid runaway uploads.
  const approxBytes = content_base64.length * 0.75;
  if (approxBytes > 20 * 1024 * 1024) {
    return { statusCode: 413, body: JSON.stringify({ error: 'File too large (20 MB cap)' }) };
  }

  const path = PATH_PREFIX + finalName;
  const apiUrl = `https://api.github.com/repos/${GITHUB_REPO}/contents/${encodeURIComponent(path)}`;

  // Get the file's current sha if it exists, so the PUT replaces in-place.
  let existingSha;
  try {
    const headRes = await fetch(`${apiUrl}?ref=${encodeURIComponent(GITHUB_BRANCH)}`, {
      headers: {
        Authorization: `Bearer ${GITHUB_TOKEN}`,
        Accept: 'application/vnd.github+json',
      },
    });
    if (headRes.status === 200) {
      const j = await headRes.json();
      existingSha = j.sha;
    }
    // 404 is fine — new file.
  } catch (e) {
    return { statusCode: 502, body: JSON.stringify({ error: `GitHub HEAD failed: ${e.message}` }) };
  }

  const commitMsg = existingSha
    ? `Update ${finalName} via dashboard upload`
    : `Add ${finalName} via dashboard upload`;

  const putBody = {
    message: commitMsg,
    content: content_base64,
    branch: GITHUB_BRANCH,
  };
  if (existingSha) putBody.sha = existingSha;

  const putRes = await fetch(apiUrl, {
    method: 'PUT',
    headers: {
      Authorization: `Bearer ${GITHUB_TOKEN}`,
      Accept: 'application/vnd.github+json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(putBody),
  });

  if (putRes.status >= 200 && putRes.status < 300) {
    const j = await putRes.json();
    return {
      statusCode: 200,
      body: JSON.stringify({
        ok: true,
        path,
        commit_url: j.commit?.html_url,
        message: 'Uploaded. Refresh will run in ~2 min.',
      }),
    };
  }

  const errText = await putRes.text();
  return {
    statusCode: putRes.status,
    body: JSON.stringify({ error: `GitHub PUT failed: ${errText}` }),
  };
};
