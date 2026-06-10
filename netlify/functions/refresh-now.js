// Netlify Function: trigger the dashboard refresh GitHub Action immediately
// (workflow_dispatch event). Used by the "Refresh now" button in the
// dashboard header so the team doesn't have to wait for the next 2-hourly cron.
//
// Required env vars:
//   GITHUB_TOKEN     — same fine-grained PAT as upload-csv (needs `Actions: Read & write`)
//   GITHUB_REPO      — "owner/repo"
//   GITHUB_BRANCH    — typically "main"
//   UPLOAD_PASSWORD  — same shared password
//
// Request body:
//   { password: "..." }

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
      body: JSON.stringify({ error: 'Server not configured.' }),
    };
  }

  let body;
  try { body = JSON.parse(event.body || '{}'); }
  catch { return { statusCode: 400, body: JSON.stringify({ error: 'Invalid JSON' }) }; }

  if (body.password !== UPLOAD_PASSWORD) {
    return { statusCode: 401, body: JSON.stringify({ error: 'Wrong password' }) };
  }

  // The workflow filename must match `.github/workflows/refresh.yml` — see
  // that file for the workflow_dispatch trigger. Using filename instead of
  // workflow id keeps this resilient to GitHub renumbering.
  const url = `https://api.github.com/repos/${GITHUB_REPO}/actions/workflows/refresh.yml/dispatches`;

  const res = await fetch(url, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${GITHUB_TOKEN}`,
      Accept: 'application/vnd.github+json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ ref: GITHUB_BRANCH }),
  });

  if (res.status === 204) {
    // 204 No Content is GitHub's success response for workflow_dispatch.
    return {
      statusCode: 200,
      body: JSON.stringify({
        ok: true,
        message: 'Refresh triggered. Dashboard will redeploy in ~2 min.',
      }),
    };
  }

  const errText = await res.text();
  return {
    statusCode: res.status,
    body: JSON.stringify({ error: `GitHub dispatch failed: ${errText}` }),
  };
};
