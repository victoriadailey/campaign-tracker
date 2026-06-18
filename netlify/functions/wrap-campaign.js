// Netlify Function: mark a campaign as "wrapped" with one click.
//
// Edits config/campaigns.yaml in the GitHub repo — flips the target
// campaign's `lifecycle:` line from `active` to `wrapped` — and commits it.
// That commit lands on a path the refresh workflow watches
// (`config/campaigns.yaml` is in refresh.yml's on-push paths), so it
// auto-regenerates data.js + the standalone bundle and Netlify redeploys.
// End-to-end: click → live in ~2 min, no local YAML edit needed.
//
// Required env vars (same ones upload-csv / refresh-now already use):
//   GITHUB_TOKEN     — fine-grained PAT with `Contents: Read & write`
//   GITHUB_REPO      — "owner/repo" (e.g. "victoriadailey/campaign-tracker")
//   GITHUB_BRANCH    — typically "main"
//   UPLOAD_PASSWORD  — shared team password
//
// Request body (JSON):
//   { password: "...", campaign_id: "adp" }

const YAML_PATH = 'config/campaigns.yaml';

function escapeRe(s) {
  return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// Flip the `lifecycle:` line to `wrapped` inside the block for `campaignId`,
// preserving the rest of the file (comments and all). Returns:
//   { lines }            — edited file lines
//   { unchanged: true }  — campaign was already wrapped (no commit needed)
//   { error }            — campaign id not found
function wrapCampaign(yamlText, campaignId, todayISO) {
  const lines = yamlText.split('\n');
  const idRe = new RegExp(`^\\s*-\\s*id:\\s*["']?${escapeRe(campaignId)}["']?\\s*$`);
  const nextIdRe = /^\s*-\s*id:\s*/;

  let start = -1;
  for (let i = 0; i < lines.length; i++) {
    if (idRe.test(lines[i])) { start = i; break; }
  }
  if (start === -1) return { error: `campaign id "${campaignId}" not found in ${YAML_PATH}` };

  let end = lines.length;
  for (let i = start + 1; i < lines.length; i++) {
    if (nextIdRe.test(lines[i])) { end = i; break; }
  }

  const lcRe = /^(\s*)lifecycle:\s*(\S+)(.*)$/;
  for (let i = start; i < end; i++) {
    const m = lines[i].match(lcRe);
    if (m) {
      const current = m[2].replace(/["']/g, '');
      if (current === 'wrapped') return { unchanged: true };
      lines[i] = `${m[1]}lifecycle: wrapped     # wrapped via dashboard ${todayISO}`;
      return { lines };
    }
  }

  // No lifecycle line in the block — insert one. Indent matches sibling fields
  // (the line right after `- id:`), defaulting to 4 spaces.
  const sibling = lines[start + 1] || '';
  const indent = (sibling.match(/^(\s*)\S/) || [, '    '])[1];
  lines.splice(start + 1, 0, `${indent}lifecycle: wrapped     # wrapped via dashboard ${todayISO}`);
  return { lines };
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

  const { password, campaign_id } = body;
  if (password !== UPLOAD_PASSWORD) {
    return { statusCode: 401, body: JSON.stringify({ error: 'Wrong password' }) };
  }
  if (!campaign_id || !/^[a-z0-9_]+$/i.test(campaign_id)) {
    return { statusCode: 400, body: JSON.stringify({ error: 'Missing or invalid campaign_id' }) };
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

  // 2. Apply the edit.
  const todayISO = new Date().toISOString().slice(0, 10);
  const result = wrapCampaign(yamlText, campaign_id, todayISO);
  if (result.error) {
    return { statusCode: 404, body: JSON.stringify({ error: result.error }) };
  }
  if (result.unchanged) {
    return { statusCode: 200, body: JSON.stringify({ ok: true, already: true, message: 'Already wrapped — nothing to do.' }) };
  }

  // 3. Commit the edited file. The push triggers refresh.yml (config/
  //    campaigns.yaml is in its on-push paths) → data regenerates → Netlify
  //    redeploys.
  const newContent = Buffer.from(result.lines.join('\n'), 'utf8').toString('base64');
  const putRes = await fetch(apiUrl, {
    method: 'PUT',
    headers: { ...ghHeaders, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: `Wrap ${campaign_id} via dashboard`,
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
        message: 'Wrapped. Dashboard will refresh in ~2 min.',
      }),
    };
  }

  const errText = await putRes.text();
  return { statusCode: putRes.status, body: JSON.stringify({ error: `GitHub PUT failed: ${errText}` }) };
};
