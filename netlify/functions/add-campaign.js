// Netlify Function: create a new campaign with one click.
//
// Appends a generated campaign block to config/campaigns.yaml in the GitHub
// repo and commits it. That commit lands on a path the refresh workflow
// watches (config/campaigns.yaml is in refresh.yml's on-push paths), so it
// auto-regenerates data.js + the standalone bundle and Netlify redeploys.
// End-to-end: click "Add campaign" → live in ~2 min, no local YAML edit and
// no copy/paste.
//
// The client (viewer/inputs.jsx) builds the YAML block from the form draft and
// sends it here; this function only validates, de-dupes on id, appends under
// `campaigns:` (which is the last top-level key, so appending at EOF is safe),
// and commits.
//
// Required env vars (same ones upload-csv / wrap-campaign already use):
//   GITHUB_TOKEN     — fine-grained PAT with `Contents: Read & write`
//   GITHUB_REPO      — "owner/repo" (e.g. "victoriadailey/campaign-tracker")
//   GITHUB_BRANCH    — typically "main"
//   UPLOAD_PASSWORD  — shared team password
//
// Request body (JSON):
//   { password: "...", campaign_id: "heineken", yaml_snippet: "  - id: heineken\n    partner: ..." }

const YAML_PATH = 'config/campaigns.yaml';

function escapeRe(s) {
  return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// True if a `- id: <campaignId>` entry already exists anywhere in the file.
function campaignExists(yamlText, campaignId) {
  const re = new RegExp(`^\\s*-\\s*id:\\s*["']?${escapeRe(campaignId)}["']?\\s*(#.*)?$`, 'm');
  return re.test(yamlText);
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
    return { statusCode: 500, body: JSON.stringify({ error: 'Server not configured. Missing env vars.' }) };
  }

  let body;
  try { body = JSON.parse(event.body || '{}'); }
  catch { return { statusCode: 400, body: JSON.stringify({ error: 'Invalid JSON' }) }; }

  const { password, campaign_id, yaml_snippet } = body;
  if (password !== UPLOAD_PASSWORD) {
    return { statusCode: 401, body: JSON.stringify({ error: 'Wrong password' }) };
  }
  if (!campaign_id || !/^[a-z0-9_]+$/i.test(campaign_id)) {
    return { statusCode: 400, body: JSON.stringify({ error: 'Missing or invalid campaign_id (letters, numbers, underscore only).' }) };
  }
  if (!yaml_snippet || typeof yaml_snippet !== 'string' || !yaml_snippet.trim()) {
    return { statusCode: 400, body: JSON.stringify({ error: 'Missing yaml_snippet' }) };
  }
  // The snippet must be a single campaign list item at the 2-space indent used
  // under `campaigns:`. Guard against anything that isn't.
  if (!/^\s*-\s*id:\s*/.test(yaml_snippet)) {
    return { statusCode: 400, body: JSON.stringify({ error: 'yaml_snippet must start with "- id:".' }) };
  }
  // The snippet's own id must match campaign_id (belt + suspenders).
  const idInSnippet = (yaml_snippet.match(/^\s*-\s*id:\s*["']?([a-z0-9_]+)["']?/i) || [])[1];
  if (idInSnippet !== campaign_id) {
    return { statusCode: 400, body: JSON.stringify({ error: `id in snippet ("${idInSnippet}") does not match campaign_id ("${campaign_id}").` }) };
  }

  const apiUrl = `https://api.github.com/repos/${GITHUB_REPO}/contents/${YAML_PATH}`;
  const ghHeaders = {
    Authorization: `Bearer ${GITHUB_TOKEN}`,
    Accept: 'application/vnd.github+json',
  };

  // 1. Fetch current campaigns.yaml (content + sha).
  let sha, yamlText;
  try {
    const getRes = await fetch(`${apiUrl}?ref=${encodeURIComponent(GITHUB_BRANCH)}`, { headers: ghHeaders });
    if (getRes.status !== 200) {
      const t = await getRes.text();
      return { statusCode: 502, body: JSON.stringify({ error: `GitHub GET failed (${getRes.status}): ${t}` }) };
    }
    const j = await getRes.json();
    sha = j.sha;
    yamlText = Buffer.from(j.content, 'base64').toString('utf8');
  } catch (e) {
    return { statusCode: 502, body: JSON.stringify({ error: `GitHub GET failed: ${e.message}` }) };
  }

  // 2. De-dupe: refuse if a campaign with this id already exists.
  if (campaignExists(yamlText, campaign_id)) {
    return { statusCode: 409, body: JSON.stringify({ error: `A campaign with id "${campaign_id}" already exists. Pick a different id, or use the "Update ongoing campaign" tab.` }) };
  }

  // 3. Append the new block at EOF (campaigns: is the last top-level key).
  //    Ensure exactly one blank line separates it from the previous campaign.
  const trimmed = yamlText.replace(/\s+$/, '');
  const block = yaml_snippet.replace(/\s+$/, '');
  const newText = `${trimmed}\n\n${block}\n`;

  const newContent = Buffer.from(newText, 'utf8').toString('base64');
  const putRes = await fetch(apiUrl, {
    method: 'PUT',
    headers: { ...ghHeaders, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: `Add campaign "${campaign_id}" via dashboard`,
      content: newContent,
      branch: GITHUB_BRANCH,
      sha,
    }),
  });

  if (putRes.status >= 200 && putRes.status < 300) {
    const j = await putRes.json();
    return {
      statusCode: 200,
      body: JSON.stringify({
        ok: true,
        commit_url: j.commit?.html_url,
        message: 'Campaign added. Dashboard will refresh in ~2 min.',
      }),
    };
  }

  const errText = await putRes.text();
  return { statusCode: putRes.status, body: JSON.stringify({ error: `GitHub PUT failed: ${errText}` }) };
};
