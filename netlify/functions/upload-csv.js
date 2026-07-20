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
const YAML_PATH = 'config/campaigns.yaml';

// Map an uploaded fixture's filename suffix to the `sources:` key refresh.py
// reads. Returns null for anything unrecognized (e.g. *_other.csv) → no wiring.
function sourceKeyForFilename(name) {
  const n = String(name || '').toLowerCase();
  if (n.endsWith('_yt_paid.csv')) return 'youtube_paid';
  if (n.endsWith('_meta_ads.csv')) return 'meta_ads';
  if (n.endsWith('_x_ads.csv')) return 'x_ads';
  if (n.endsWith('_tiktok_ads.csv')) return 'tiktok_ads';
  if (n.endsWith('_linkedin_ads.csv')) return 'linkedin_ads';
  return null;
}

function escapeReUp(s) {
  return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// Ensure `filename` is listed under `sources: <key>:` inside the block for
// `campaignId`, preserving the rest of the file. Pure/text-based so it can be
// unit-tested. Returns { lines } on edit, { unchanged: true } if already
// present, or { skip: reason } when the structure isn't what we expect (caller
// treats skip as non-fatal — the CSV is already committed and the Data Health
// panel will surface any still-unwired file).
function wireSourceIntoYaml(yamlText, campaignId, key, filename) {
  const lines = yamlText.split('\n');
  const idRe = new RegExp(`^(\\s*)-\\s*id:\\s*["']?${escapeReUp(campaignId)}["']?\\s*(#.*)?$`);

  let start = -1, listIndent = '';
  for (let i = 0; i < lines.length; i++) {
    const m = lines[i].match(idRe);
    if (m) { start = i; listIndent = m[1]; break; }
  }
  if (start === -1) return { skip: `campaign "${campaignId}" not found` };

  // Block ends at the next CAMPAIGN-level `- id:` (same indent). Must NOT match
  // episode `- id:` lines (deeper indent), or a campaign whose sources: sits
  // after its episodes: would be truncated and we'd inject mid-episode-list.
  const nextItemRe = new RegExp(`^${listIndent}-\\s*id:\\s*`);
  let end = lines.length;
  for (let i = start + 1; i < lines.length; i++) {
    if (nextItemRe.test(lines[i])) { end = i; break; }
  }

  const fieldIndent = listIndent + '  ';           // fields under "- id:" (e.g. 4 spaces)
  const subIndent = fieldIndent + '  ';            // source keys under "sources:" (6)
  const itemIndent = subIndent + '  ';             // list items under a key (8)

  // Find `sources:` within the block.
  const srcRe = new RegExp(`^${fieldIndent}sources:\\s*$`);
  let srcLine = -1;
  for (let i = start + 1; i < end; i++) {
    if (srcRe.test(lines[i])) { srcLine = i; break; }
  }

  // No sources: block — add one at the end of the campaign block.
  if (srcLine === -1) {
    const insertAt = end;
    const block = [`${fieldIndent}sources:`, `${subIndent}${key}:`, `${itemIndent}- ${filename}`];
    lines.splice(insertAt, 0, ...block);
    return { lines };
  }

  // Find the end of the sources: sub-block (next line at <= fieldIndent depth).
  let srcEnd = end;
  for (let i = srcLine + 1; i < end; i++) {
    const line = lines[i];
    if (line.trim() === '') continue;
    const indent = (line.match(/^(\s*)/) || [, ''])[1];
    if (indent.length <= fieldIndent.length) { srcEnd = i; break; }
  }

  // Is `key:` already present under sources?
  const keyRe = new RegExp(`^${subIndent}${escapeReUp(key)}:\\s*$`);
  let keyLine = -1;
  for (let i = srcLine + 1; i < srcEnd; i++) {
    if (keyRe.test(lines[i])) { keyLine = i; break; }
  }

  if (keyLine === -1) {
    // Add the key + item right after `sources:`.
    lines.splice(srcLine + 1, 0, `${subIndent}${key}:`, `${itemIndent}- ${filename}`);
    return { lines };
  }

  // Key exists — find its list items; bail (unchanged) if filename already listed.
  let keyEnd = srcEnd;
  for (let i = keyLine + 1; i < srcEnd; i++) {
    const line = lines[i];
    if (line.trim() === '') continue;
    const indent = (line.match(/^(\s*)/) || [, ''])[1];
    if (indent.length <= subIndent.length) { keyEnd = i; break; }
  }
  const itemRe = new RegExp(`^\\s*-\\s*["']?${escapeReUp(filename)}["']?\\s*(#.*)?$`);
  for (let i = keyLine + 1; i < keyEnd; i++) {
    if (itemRe.test(lines[i])) return { unchanged: true };
  }
  // Append the item at the end of this key's list.
  lines.splice(keyEnd, 0, `${itemIndent}- ${filename}`);
  return { lines };
}

module.exports._wireSourceIntoYaml = wireSourceIntoYaml;
module.exports._sourceKeyForFilename = sourceKeyForFilename;

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

    // ---------- Auto-wire the upload into the campaign's sources ----------
    // A file that isn't referenced in config/campaigns.yaml is silently ignored
    // by the refresh — the #1 recurring failure. When this upload used a
    // convention-named fixture (not an exact_target, which is already wired),
    // ensure the campaign's `sources:` references it. Best-effort: any failure
    // here does NOT fail the upload (the CSV is committed; the dashboard's Data
    // Health panel surfaces anything still unwired).
    let wired = null;
    const wireKey = exact_target ? null : sourceKeyForFilename(finalName);
    if (wireKey) {
      try {
        const yamlApi = `https://api.github.com/repos/${GITHUB_REPO}/contents/${YAML_PATH}`;
        const gh = { Authorization: `Bearer ${GITHUB_TOKEN}`, Accept: 'application/vnd.github+json' };
        const getRes = await fetch(`${yamlApi}?ref=${encodeURIComponent(GITHUB_BRANCH)}`, { headers: gh });
        if (getRes.status === 200) {
          const cfg = await getRes.json();
          const yamlText = Buffer.from(cfg.content, 'base64').toString('utf8');
          const result = wireSourceIntoYaml(yamlText, campaign_id, wireKey, finalName);
          if (result.lines) {
            const newContent = Buffer.from(result.lines.join('\n'), 'utf8').toString('base64');
            const wr = await fetch(yamlApi, {
              method: 'PUT',
              headers: { ...gh, 'Content-Type': 'application/json' },
              body: JSON.stringify({
                message: `Wire ${finalName} into ${campaign_id} sources (auto)`,
                content: newContent, branch: GITHUB_BRANCH, sha: cfg.sha,
              }),
            });
            wired = wr.ok ? 'added' : `failed (${wr.status})`;
          } else if (result.unchanged) {
            wired = 'already-wired';
          } else {
            wired = `skipped (${result.skip})`;
          }
        }
      } catch (e) {
        wired = `error (${e.message})`;
      }
    }

    return {
      statusCode: 200,
      body: JSON.stringify({
        ok: true,
        path,
        wired,
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
