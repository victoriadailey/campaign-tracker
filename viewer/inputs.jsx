/* global React, CAMPAIGNS, BENCHMARKS_DATA, fmt, Ic, PageHead */
// ============================================================
// INPUTS PAGE
// Two modes:
//   • New campaign  — capture client/series/format/flight/goals/budget/episodes,
//                     plus a drop-zone for the initial export files.
//   • Ongoing campaign — per-campaign upload boxes + a notes textarea.
//
// This is a static dashboard, so "uploads" here are captured client-side
// (file names + sizes + chosen target campaign) and surfaced in a "queue"
// the operator copies into tests/fixtures/ alongside the YAML edits.
// Form drafts persist in localStorage so a half-finished entry isn't lost
// on refresh.
// ============================================================

function InputsPage() {
  const [tab, setTab] = React.useState('new'); // 'new' | 'ongoing'

  return (
    <>
      <PageHead
        overline={`Sponsored campaigns · ${new Date().toLocaleString('en-US', { month: 'long', year: 'numeric' })}`}
        title="Add Campaign"
        italic="Data"
        sub="Add a new campaign or upload new data to an existing one. Drafts save locally and persist between refreshes."
      />

      {/* Tab strip */}
      <div style={{
        display:'flex', gap:0, marginBottom:24, borderBottom:'1px solid var(--line)'
      }}>
        {[
          { id:'new',     label:'Add new campaign' },
          { id:'ongoing', label:'Update ongoing campaign' },
        ].map(t => (
          <button key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              background:'transparent', border:'none',
              padding:'14px 22px', fontFamily:'inherit', fontSize:14,
              fontWeight: tab === t.id ? 600 : 500,
              color: tab === t.id ? 'var(--ink)' : 'var(--ink-3)',
              borderBottom: tab === t.id ? '2px solid var(--liquorice)' : '2px solid transparent',
              marginBottom:-1, cursor:'pointer', letterSpacing:'-0.01em'
            }}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'new' ? <NewCampaignForm/> : <OngoingCampaignForm/>}
    </>
  );
}

// ============================================================
// NEW CAMPAIGN — full form
// ============================================================
const DRAFT_KEY = 'inputs.newCampaign.draft';

function _emptyEpisode() {
  return { n: '', title: '', date: '', match: '' };
}

function _emptyDraft() {
  return {
    id: '',
    partner: '',
    series: '',
    type: 'content',
    benchmark_category: 'Original Content',
    lifecycle: 'active',
    flight_start: '',
    flight_end: '',
    impression_goal: '',
    budget_goal: '',
    color: 'ft-1',
    blurb: '',
    ms_post_groups: '',
    content_planner_url: '',
    sources_note: '',  // free-form notes about which export file maps where
    episodes: [],
    uploads: [],  // [{name, size, type, target}]
  };
}

function NewCampaignForm() {
  const [draft, setDraft] = React.useState(() => {
    try {
      const saved = localStorage.getItem(DRAFT_KEY);
      return saved ? { ..._emptyDraft(), ...JSON.parse(saved) } : _emptyDraft();
    } catch {
      return _emptyDraft();
    }
  });
  const [showYaml, setShowYaml] = React.useState(false);

  // Save draft on every change (debounced via React's batching).
  React.useEffect(() => {
    try { localStorage.setItem(DRAFT_KEY, JSON.stringify(draft)); } catch {}
  }, [draft]);

  const set = (k, v) => setDraft(d => ({ ...d, [k]: v }));

  const benchmarkCategories = (BENCHMARKS_DATA && BENCHMARKS_DATA.categories)
    ? BENCHMARKS_DATA.categories.map(c => c.name)
    : ['Original Content', 'Custom Social', 'Social - IP/Franchise',
       'Social Coverage Partner', 'Branded Content'];

  const yaml = _generateYaml(draft);

  const reset = () => {
    if (confirm('Discard this draft and start over?')) {
      setDraft(_emptyDraft());
      try { localStorage.removeItem(DRAFT_KEY); } catch {}
    }
  };

  return (
    <>
      {/* CAMPAIGN DETAILS */}
      <div className="sec">
        <div className="sec-h"><div>
          <div className="sec-title">Campaign <em>details</em></div>
          <div className="sec-sub" style={{marginTop:6}}>Fill these in from the content planner. Required fields are marked.</div>
        </div></div>

        <div className="card" style={{padding:24}}>
          <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:18}}>
            <Field label="Client / partner" required>
              <Input value={draft.partner} onChange={v => set('partner', v)} placeholder="ADP"/>
            </Field>
            <Field label="Internal campaign id" required
              hint="lowercase, no spaces — used as the file & URL key. e.g., E*TRADE + Portfolio Players → etrade_portfolio_players">
              <Input value={draft.id} onChange={v => set('id', v.toLowerCase().replace(/[^a-z0-9_]/g,''))} placeholder="etrade_portfolio_players"/>
            </Field>
            <Field label="Series name" required>
              <Input value={draft.series} onChange={v => set('series', v)} placeholder="Future of Sports"/>
            </Field>
            <Field label="Campaign type" required>
              <Select value={draft.type} onChange={v => set('type', v)} options={[
                { v:'content', l:'Content (episode-based)' },
                { v:'social',  l:'Social (post-based)' },
              ]}/>
            </Field>
            <Field label="Benchmark category" required hint="determines which FOS cohort this campaign is compared against">
              <Select value={draft.benchmark_category} onChange={v => set('benchmark_category', v)}
                options={benchmarkCategories.map(n => ({ v:n, l:n }))}/>
            </Field>
            <Field label="Accent color">
              <Select value={draft.color} onChange={v => set('color', v)} options={[
                { v:'ft-1', l:'Flame (orange)' },
                { v:'ft-2', l:'Pear (green)' },
                { v:'ft-3', l:'Sky (blue)' },
                { v:'ft-4', l:'Sunshine (yellow)' },
                { v:'ft-5', l:'Lilac (purple)' },
              ]}/>
            </Field>
            <Field label="Flight start" required>
              <Input type="date" value={draft.flight_start} onChange={v => set('flight_start', v)}/>
            </Field>
            <Field label="Flight end" required>
              <Input type="date" value={draft.flight_end} onChange={v => set('flight_end', v)}/>
            </Field>
            <Field label="Impressions goal" required hint="total contracted impressions across all platforms">
              <Input type="number" value={draft.impression_goal} onChange={v => set('impression_goal', v)} placeholder="6600000"/>
            </Field>
            <Field label="Budget" required hint="total media spend, USD">
              <Input type="number" step="0.01" value={draft.budget_goal} onChange={v => set('budget_goal', v)} placeholder="10916"/>
            </Field>
            <Field label="MS Post Group(s)" hint="comma-separated — used to bucket Measure Studio rows into this campaign" full>
              <Input value={draft.ms_post_groups} onChange={v => set('ms_post_groups', v)} placeholder="Future of Sports, Future of Sports: Full Ep"/>
            </Field>
            <Field label="Content planner link" hint="URL to the content planner doc — kept for reference, not displayed in the viewer" full>
              <Input value={draft.content_planner_url} onChange={v => set('content_planner_url', v)} placeholder="https://docs.google.com/..."/>
            </Field>
            <Field label="Blurb" hint="2 sentences max — shown on the campaign card" full>
              <TextArea value={draft.blurb} onChange={v => set('blurb', v)} rows={2} placeholder="Three-episode interview series with HR & sports execs. Strong organic resonance on LinkedIn."/>
            </Field>
          </div>
        </div>
      </div>

      {/* EPISODES (content only) */}
      {draft.type === 'content' && (
        <div className="sec">
          <div className="sec-h" style={{display:'flex', alignItems:'center', justifyContent:'space-between'}}>
            <div>
              <div className="sec-title">Episodes</div>
              <div className="sec-sub" style={{marginTop:6}}>Add each episode and the keywords that will auto-attribute its posts. 'PP Episode N -' style tags from Measure Studio's User Tags column are the most reliable signal.</div>
            </div>
            <button className="btn btn-acc" onClick={() => set('episodes', [...draft.episodes, _emptyEpisode()])}>
              <Ic.plus/> Add episode
            </button>
          </div>

          {draft.episodes.length === 0 && (
            <div className="card" style={{padding:32, textAlign:'center', color:'var(--ink-3)', fontSize:13}}>
              No episodes yet. Click "Add episode" to start.
            </div>
          )}

          {draft.episodes.map((ep, i) => (
            <div key={i} className="card" style={{padding:20, marginBottom:12}}>
              <div style={{display:'grid', gridTemplateColumns:'120px 1fr 140px auto', gap:14, alignItems:'end'}}>
                <Field label={`Episode # (Ep. ${String(i+1).padStart(2,'0')})`}>
                  <Input value={ep.n} onChange={v => {
                    const next = [...draft.episodes]; next[i] = { ...next[i], n: v };
                    set('episodes', next);
                  }} placeholder={`Ep. ${String(i+1).padStart(2,'0')}`}/>
                </Field>
                <Field label="Title">
                  <Input value={ep.title} onChange={v => {
                    const next = [...draft.episodes]; next[i] = { ...next[i], title: v };
                    set('episodes', next);
                  }} placeholder="Kim Ng on Building Competence"/>
                </Field>
                <Field label="Air date">
                  <Input value={ep.date} onChange={v => {
                    const next = [...draft.episodes]; next[i] = { ...next[i], date: v };
                    set('episodes', next);
                  }} placeholder="Mar 5"/>
                </Field>
                <button onClick={() => set('episodes', draft.episodes.filter((_, j) => j !== i))}
                  style={{
                    background:'transparent', border:'1px solid var(--line)', borderRadius:6,
                    padding:'8px 10px', cursor:'pointer', color:'var(--ink-3)', height:36
                  }} title="Remove episode">
                  <Ic.trash/>
                </button>
              </div>
              <Field label="Match keywords" hint="comma-separated; longer/more-specific keywords win on attribution ties" full>
                <Input value={ep.match} onChange={v => {
                  const next = [...draft.episodes]; next[i] = { ...next[i], match: v };
                  set('episodes', next);
                }} placeholder="Kim Ng, Building Competence"/>
              </Field>
            </div>
          ))}
        </div>
      )}

      {/* INITIAL UPLOADS */}
      <div className="sec">
        <div className="sec-h"><div>
          <div className="sec-title">Initial <em>uploads</em></div>
          <div className="sec-sub" style={{marginTop:6}}>Drop the first export files for this campaign. Once the Measure Studio API is connected, we'll pull these automatically.</div>
        </div></div>
        <UploadGrid draft={draft} setDraft={setDraft}/>
      </div>

      {/* ACTIONS */}
      <div className="sec" style={{marginBottom:32}}>
        <div className="card" style={{padding:20, display:'flex', justifyContent:'space-between', alignItems:'center', gap:16}}>
          <div style={{fontSize:13, color:'var(--ink-2)'}}>
            Draft saved automatically. The "Generate YAML" button copies a config snippet you paste into <code>config/campaigns.yaml</code>, then run <code>python -m app.viewer.refresh</code>.
          </div>
          <div style={{display:'flex', gap:10}}>
            <button onClick={reset} style={btnGhost}>
              Reset
            </button>
            <button onClick={() => setShowYaml(s => !s)} className="btn btn-acc">
              {showYaml ? 'Hide YAML' : 'Generate YAML'}
            </button>
          </div>
        </div>
      </div>

      {showYaml && <YamlOutput yaml={yaml}/>}
    </>
  );
}

// ============================================================
// ONGOING CAMPAIGN — list every active campaign with uploads + notes
// ============================================================
const NOTES_KEY = 'inputs.ongoing.notes';
const UPLOAD_QUEUE_KEY = 'inputs.ongoing.queue';

function OngoingCampaignForm() {
  const [notes, setNotes] = React.useState(() => {
    try { return JSON.parse(localStorage.getItem(NOTES_KEY)) || {}; }
    catch { return {}; }
  });
  const [queues, setQueues] = React.useState(() => {
    try { return JSON.parse(localStorage.getItem(UPLOAD_QUEUE_KEY)) || {}; }
    catch { return {}; }
  });

  React.useEffect(() => {
    try { localStorage.setItem(NOTES_KEY, JSON.stringify(notes)); } catch {}
  }, [notes]);
  React.useEffect(() => {
    try { localStorage.setItem(UPLOAD_QUEUE_KEY, JSON.stringify(queues)); } catch {}
  }, [queues]);

  const setNote = (id, v) => setNotes({ ...notes, [id]: v });
  const setQueue = (id, q) => setQueues({ ...queues, [id]: q });

  const activeCampaigns = CAMPAIGNS.filter(c => (c.lifecycle || 'active') === 'active');

  return (
    <>
      {activeCampaigns.map(c => (
        <div key={c.id} className="sec">
          <div className="card" style={{padding:0, overflow:'hidden'}}>
            {/* Header */}
            <div style={{
              padding:'20px 24px', borderBottom:'1px solid var(--line)',
              display:'flex', justifyContent:'space-between', alignItems:'flex-start', gap:20
            }}>
              <div>
                <div style={{fontSize:11, letterSpacing:'0.1em', textTransform:'uppercase', color:'var(--ink-3)', fontWeight:600, marginBottom:4}}>
                  {c.partner}
                </div>
                <div style={{fontFamily:'var(--serif)', fontSize:22, fontWeight:300, letterSpacing:'-0.01em'}}>
                  {c.series.replace(c.seriesItalic, '')}<em>{c.seriesItalic}</em>
                </div>
                <div style={{fontSize:11, color:'var(--ink-3)', marginTop:6}}>
                  {c.flight} · {c.type === 'social' ? 'Social' : 'Content'} · {c.benchmarkCategory || 'Uncategorized'}
                </div>
              </div>
              <div style={{display:'flex', gap:14, fontSize:11, color:'var(--ink-3)'}}>
                <div style={{textAlign:'right'}}>
                  <div style={{fontFamily:'var(--serif)', fontSize:18, fontWeight:300, color:'var(--ink)'}}>{fmt.num(c.impressions.delivered)}</div>
                  <div style={{letterSpacing:'0.08em', textTransform:'uppercase', fontWeight:600}}>Delivered</div>
                </div>
                <div style={{textAlign:'right'}}>
                  <div style={{fontFamily:'var(--serif)', fontSize:18, fontWeight:300, color:'var(--ink)'}}>{c.posts}</div>
                  <div style={{letterSpacing:'0.08em', textTransform:'uppercase', fontWeight:600}}>Posts</div>
                </div>
              </div>
            </div>

            {/* Uploads + notes side-by-side */}
            <div style={{display:'grid', gridTemplateColumns:'1.3fr 1fr', gap:0}}>
              <div style={{padding:20, borderRight:'1px solid var(--line)'}}>
                <div style={{fontSize:10, fontFamily:'var(--mono)', letterSpacing:'0.1em', color:'var(--ink-3)', fontWeight:600, marginBottom:10, textTransform:'uppercase'}}>
                  New uploads
                </div>
                <CompactDropZone
                  queue={queues[c.id] || []}
                  onChange={q => setQueue(c.id, q)}
                  sources={uploadSourcesFor(c.id)}
                />
              </div>
              <div style={{padding:20}}>
                <div style={{fontSize:10, fontFamily:'var(--mono)', letterSpacing:'0.1em', color:'var(--ink-3)', fontWeight:600, marginBottom:10, textTransform:'uppercase'}}>
                  Notes
                </div>
                <TextArea
                  value={notes[c.id] || ''}
                  onChange={v => setNote(c.id, v)}
                  rows={6}
                  placeholder="Anything the team should know about this update — new launch slots, creative direction changes, manual_posts to add, etc."
                />
              </div>
            </div>
            {/* Submit row — pushes queued files to the backend, which
                commits them to GitHub and triggers a refresh. The pipeline
                only runs when there are files queued. */}
            <SubmitQueueRow
              campaignId={c.id}
              queue={queues[c.id] || []}
              onClear={() => setQueue(c.id, [])}
            />
          </div>
        </div>
      ))}
    </>
  );
}

// ============================================================
// SUBMIT QUEUE ROW — posts queued files to /.netlify/functions/upload-csv
// ============================================================
// Authentication: shared team password, prompted once per session and
// cached in sessionStorage so the team doesn't have to re-enter it for
// every campaign card upload.
const PASSWORD_KEY = 'inputs.upload.password';

function getUploadPassword() {
  let p = sessionStorage.getItem(PASSWORD_KEY);
  if (!p) {
    p = window.prompt('Team upload password:') || '';
    if (p) sessionStorage.setItem(PASSWORD_KEY, p);
  }
  return p;
}

function clearUploadPassword() {
  sessionStorage.removeItem(PASSWORD_KEY);
}

function SubmitQueueRow({ campaignId, queue, onClear }) {
  const [status, setStatus] = React.useState({ kind: 'idle' });
  // Don't render the row at all when there's nothing queued — avoids visual
  // noise on the dozen-plus campaign cards on the page.
  if (queue.length === 0) return null;

  const submit = async () => {
    const password = getUploadPassword();
    if (!password) {
      setStatus({ kind: 'error', message: 'Password required.' });
      return;
    }
    setStatus({ kind: 'uploading', done: 0, total: queue.length });

    const results = [];
    for (let i = 0; i < queue.length; i++) {
      const file = queue[i];
      if (!file.content_base64) {
        results.push({ name: file.name, ok: false, error: 'Missing file content (re-add the file).' });
        setStatus({ kind: 'uploading', done: i + 1, total: queue.length });
        continue;
      }
      // file.target is now the EXACT configured filename to overwrite (chosen
      // from UPLOAD_TARGETS), so the upload lands where refresh.py actually
      // reads it. Only the "other" escape hatch falls back to the file's own
      // (backend-namespaced) name — those are genuinely new sources that still
      // need wiring into config/campaigns.yaml before they'll be parsed.
      const filename = (file.target && file.target !== 'other')
        ? file.target
        : file.name;

      try {
        const res = await fetch('/.netlify/functions/upload-csv', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            password,
            campaign_id: campaignId,
            filename,
            content_base64: file.content_base64,
          }),
        });
        const j = await res.json().catch(() => ({}));
        if (!res.ok) {
          if (res.status === 401) clearUploadPassword();
          results.push({ name: file.name, ok: false, error: j.error || `HTTP ${res.status}` });
        } else {
          results.push({ name: file.name, ok: true });
        }
      } catch (e) {
        results.push({ name: file.name, ok: false, error: String(e?.message || e) });
      }
      setStatus({ kind: 'uploading', done: i + 1, total: queue.length });
    }

    const failed = results.filter(r => !r.ok);
    if (failed.length === 0) {
      setStatus({ kind: 'success', uploaded: results.length });
      onClear();
    } else {
      setStatus({ kind: 'partial', results });
    }
  };

  return (
    <div style={{
      padding: '14px 20px',
      borderTop: '1px solid var(--line)',
      background: 'var(--bg-soft)',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      gap: 14,
    }}>
      <div style={{fontSize: 11, color: 'var(--ink-3)', fontFamily: 'var(--mono)', letterSpacing: '0.04em'}}>
        {status.kind === 'uploading'
          ? `Uploading ${status.done}/${status.total}…`
          : status.kind === 'success'
            ? `✓ ${status.uploaded} file${status.uploaded === 1 ? '' : 's'} uploaded — dashboard refresh in ~2 min`
            : status.kind === 'partial'
              ? `⚠ Some uploads failed — see below`
              : `${queue.length} file${queue.length === 1 ? '' : 's'} ready to submit`}
      </div>
      <button
        onClick={submit}
        disabled={status.kind === 'uploading'}
        style={{
          background: status.kind === 'uploading' ? 'var(--ink-3)' : 'var(--liquorice)',
          color: 'var(--cream)',
          border: 'none', borderRadius: 6,
          padding: '8px 18px', fontSize: 12, fontWeight: 600,
          fontFamily: 'inherit', letterSpacing: '0.04em',
          cursor: status.kind === 'uploading' ? 'wait' : 'pointer',
        }}>
        {status.kind === 'uploading' ? 'Uploading…' : 'Submit & refresh'}
      </button>
      {/* Inline error detail when one or more files failed. Kept compact so
          the per-campaign card doesn't blow up vertically. */}
      {status.kind === 'partial' && (
        <div style={{flexBasis: '100%', marginTop: 8, fontSize: 11, color: 'var(--danger, #b8392b)'}}>
          {status.results.filter(r => !r.ok).map((r, i) => (
            <div key={i}>• {r.name}: {r.error}</div>
          ))}
        </div>
      )}
    </div>
  );
}

// ============================================================
// Shared form primitives
// ============================================================
const fieldStyle = { display:'flex', flexDirection:'column', gap:6 };
const labelStyle = { fontSize:10, fontFamily:'var(--mono)', letterSpacing:'0.1em', color:'var(--ink-3)', fontWeight:600, textTransform:'uppercase' };
const hintStyle  = { fontSize:11, color:'var(--ink-3)', marginTop:-2, lineHeight:1.35 };
const inputStyle = {
  background:'var(--bg)', border:'1px solid var(--line)', borderRadius:6,
  padding:'9px 12px', fontSize:13, fontFamily:'inherit', color:'var(--ink)',
  outline:'none', transition:'border 0.15s',
};
const btnGhost = {
  background:'transparent', border:'1px solid var(--line)', borderRadius:6,
  padding:'9px 16px', fontSize:13, fontFamily:'inherit', cursor:'pointer',
  color:'var(--ink-2)',
};

function Field({ label, required, hint, full, children }) {
  return (
    <div style={{ ...fieldStyle, gridColumn: full ? '1 / -1' : 'auto' }}>
      <span style={labelStyle}>
        {label}{required && <span style={{color:'#b8392b', marginLeft:4}}>*</span>}
      </span>
      {children}
      {hint && <span style={hintStyle}>{hint}</span>}
    </div>
  );
}

function Input({ value, onChange, ...rest }) {
  return (
    <input
      style={inputStyle}
      value={value || ''}
      onChange={e => onChange(e.target.value)}
      onFocus={e => e.target.style.borderColor = 'var(--liquorice)'}
      onBlur={e => e.target.style.borderColor = 'var(--line)'}
      {...rest}
    />
  );
}

function TextArea({ value, onChange, rows = 3, ...rest }) {
  return (
    <textarea
      style={{ ...inputStyle, resize:'vertical', minHeight: rows * 22, lineHeight:1.45, fontFamily:'inherit' }}
      value={value || ''}
      rows={rows}
      onChange={e => onChange(e.target.value)}
      onFocus={e => e.target.style.borderColor = 'var(--liquorice)'}
      onBlur={e => e.target.style.borderColor = 'var(--line)'}
      {...rest}
    />
  );
}

function Select({ value, onChange, options }) {
  return (
    <select style={inputStyle} value={value} onChange={e => onChange(e.target.value)}>
      {options.map(o => <option key={o.v} value={o.v}>{o.l}</option>)}
    </select>
  );
}

// ============================================================
// UPLOAD UI — big drop zones (new campaign), compact list (ongoing)
// ============================================================
function UploadGrid({ draft, setDraft }) {
  const sources = draft.type === 'content'
    ? [
        { id:'measure_studio',      label:'Measure Studio',        hint:'Wide export (.csv) — all platforms, all post groups' },
        { id:'youtube_paid',        label:'Google Ads (YT Paid)',  hint:'Campaign report (.tsv) — TrueView views + Engagement rate' },
        { id:'x_ads',               label:'X Ads',                 hint:'Apple Numbers export — full + cutdown sheets combined' },
        { id:'meta_ads',            label:'Meta Ads',              hint:'Ads Manager CSV — for dark posts MS can\'t see' },
        { id:'tiktok_ads',          label:'TikTok Ads',            hint:'TikTok Ads Manager export — coming soon' },
      ]
    : [
        { id:'measure_studio', label:'Measure Studio', hint:'Wide export (.csv) — all platforms' },
        { id:'meta_ads',       label:'Meta Ads',       hint:'Ads Manager CSV — for dark posts MS can\'t see' },
        { id:'tiktok_ads',     label:'TikTok Ads',     hint:'TikTok Ads Manager export — coming soon' },
      ];

  const addFile = (sourceId, file) => {
    setDraft(d => ({
      ...d,
      uploads: [...d.uploads, {
        name: file.name, size: file.size, target: sourceId,
        added: new Date().toISOString().slice(0, 10)
      }]
    }));
  };

  return (
    <div style={{display:'grid', gridTemplateColumns:`repeat(${sources.length}, 1fr)`, gap:14}}>
      {sources.map(s => {
        const queued = draft.uploads.filter(u => u.target === s.id);
        return (
          <DropZone key={s.id} label={s.label} hint={s.hint}
            files={queued}
            onAdd={file => addFile(s.id, file)}
            onRemove={idx => setDraft(d => ({
              ...d,
              uploads: d.uploads.filter((u, i) => !(u.target === s.id && queued[idx] === u))
            }))}/>
        );
      })}
    </div>
  );
}

function DropZone({ label, hint, files, onAdd, onRemove }) {
  const [over, setOver] = React.useState(false);
  const inputRef = React.useRef(null);

  const handleFiles = (fl) => {
    if (!fl || fl.length === 0) return;
    for (const f of fl) onAdd(f);
  };

  return (
    <div style={{
      border: `2px dashed ${over ? 'var(--liquorice)' : 'var(--line-2)'}`,
      background: over ? 'rgba(36,28,23,0.04)' : 'var(--bg-soft)',
      borderRadius:8, padding:20, transition:'border 0.15s, background 0.15s',
      display:'flex', flexDirection:'column', gap:10, minHeight:160
    }}
      onDragEnter={(e) => { e.preventDefault(); setOver(true); }}
      onDragOver={(e) => { e.preventDefault(); setOver(true); }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault(); setOver(false);
        handleFiles(e.dataTransfer.files);
      }}
    >
      <div style={{fontSize:13, fontWeight:600, letterSpacing:'-0.01em'}}>{label}</div>
      <div style={{fontSize:11, color:'var(--ink-3)', lineHeight:1.4, marginTop:-4}}>{hint}</div>

      <button
        onClick={() => inputRef.current && inputRef.current.click()}
        style={{
          background:'var(--bg)', border:'1px solid var(--line)', borderRadius:6,
          padding:'8px 12px', cursor:'pointer', fontSize:12, fontFamily:'inherit',
          color:'var(--ink-2)', display:'inline-flex', alignItems:'center', gap:6,
          alignSelf:'flex-start'
        }}>
        <Ic.upload/> Choose file or drop here
      </button>
      <input
        ref={inputRef} type="file" multiple
        accept=".csv,.tsv,.numbers,.xlsx"
        onChange={e => handleFiles(e.target.files)}
        style={{display:'none'}}/>

      {files.length > 0 && (
        <div style={{display:'flex', flexDirection:'column', gap:4, marginTop:6}}>
          {files.map((f, i) => (
            <div key={i} style={{
              display:'flex', justifyContent:'space-between', alignItems:'center', gap:8,
              fontSize:11, padding:'6px 10px', background:'var(--bg)',
              border:'1px solid var(--line)', borderRadius:5
            }}>
              <span style={{overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap', minWidth:0}}>{f.name}</span>
              <span style={{color:'var(--ink-3)', whiteSpace:'nowrap', fontSize:10}}>{f.size < 1024 ? `${f.size} B` : `${(f.size/1024).toFixed(0)} KB`}</span>
              <button onClick={() => onRemove(i)} style={{
                background:'transparent', border:'none', cursor:'pointer',
                color:'var(--ink-3)', padding:0, display:'inline-flex'
              }} title="Remove"><Ic.trash/></button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Source-display-name → fixture filename suffix used by refresh.py.
// Keep in sync with config/campaigns.yaml `sources:` keys.
const SOURCE_KIND_FOR = {
  'Measure Studio':       'ms',          // rarely used (MS is API-driven), kept for manual CSV fallback
  'Google Ads (YT Paid)': 'yt_paid',
  'X Ads':                'x_ads',
  'Meta Ads':             'meta_ads',
  'TikTok Ads':           'tiktok_ads',
  'LinkedIn Ads':         'linkedin_ads',
  'Other':                'other',
};

// Read a File into a base64 string (without the data: prefix). Returns
// {b64, mime}.
function readFileAsBase64(file) {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => {
      const result = r.result || '';
      const comma = result.indexOf(',');
      resolve({ b64: comma >= 0 ? result.slice(comma + 1) : result, mime: file.type || '' });
    };
    r.onerror = () => reject(r.error || new Error('FileReader failed'));
    r.readAsDataURL(file);
  });
}

// Build the upload-source dropdown for a campaign from its ACTUAL configured
// files (window.UPLOAD_TARGETS, emitted by refresh.py). Each option's value is
// the exact filename the refresh reads, so an upload overwrites the right file
// instead of guessing a name that silently no-ops. "Other" stays as an escape
// hatch for genuinely new files (which still need wiring into campaigns.yaml).
function uploadSourcesFor(campaignId) {
  const targets = (window.UPLOAD_TARGETS || {})[campaignId] || [];
  const opts = targets.map(t => ({ v: t.file, l: `${t.label} · ${t.file}` }));
  opts.push({ v: 'other', l: 'Other — new file (needs config wiring)' });
  return opts;
}

function CompactDropZone({ queue, onChange, sources }) {
  const [over, setOver] = React.useState(false);
  const [target, setTarget] = React.useState(sources[0]?.v);
  const inputRef = React.useRef(null);

  const addFiles = async (fl) => {
    if (!fl || fl.length === 0) return;
    const next = [...queue];
    for (const f of fl) {
      try {
        const { b64 } = await readFileAsBase64(f);
        next.push({
          name: f.name,
          size: f.size,
          target,
          added: new Date().toISOString().slice(0, 10),
          // Stash the content base64 so the Submit button can POST it.
          // localStorage caps at ~5 MB so very large files won't survive a
          // page reload — but they're fine for the in-session upload path.
          content_base64: b64,
        });
      } catch (e) {
        console.error('Failed to read file', f.name, e);
      }
    }
    onChange(next);
  };

  return (
    <>
      <div style={{display:'flex', alignItems:'center', gap:8, marginBottom:10}}>
        <Select value={target} onChange={setTarget} options={sources}/>
      </div>
      <div style={{
        border: `2px dashed ${over ? 'var(--liquorice)' : 'var(--line-2)'}`,
        background: over ? 'rgba(36,28,23,0.04)' : 'var(--bg-soft)',
        borderRadius:6, padding:'14px 16px', transition:'border 0.15s',
        cursor:'pointer'
      }}
        onClick={() => inputRef.current && inputRef.current.click()}
        onDragEnter={(e) => { e.preventDefault(); setOver(true); }}
        onDragOver={(e) => { e.preventDefault(); setOver(true); }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => {
          e.preventDefault(); setOver(false);
          addFiles(e.dataTransfer.files);
        }}
      >
        <div style={{fontSize:12, color:'var(--ink-2)', display:'inline-flex', alignItems:'center', gap:6}}>
          <Ic.upload/> Drop file or click to browse
        </div>
        <input
          ref={inputRef} type="file" multiple
          accept=".csv,.tsv,.numbers,.xlsx"
          onChange={e => addFiles(e.target.files)}
          style={{display:'none'}}/>
      </div>

      {queue.length > 0 && (
        <div style={{display:'flex', flexDirection:'column', gap:4, marginTop:10}}>
          {queue.map((f, i) => (
            <div key={i} style={{
              display:'grid', gridTemplateColumns:'1fr auto auto 24px', gap:10, alignItems:'center',
              fontSize:11, padding:'6px 10px', background:'var(--bg)',
              border:'1px solid var(--line)', borderRadius:5
            }}>
              <span style={{overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap', minWidth:0}}>{f.name}</span>
              <span style={{color:'var(--ink-3)', fontSize:10}}>{f.target}</span>
              <span style={{color:'var(--ink-3)', fontSize:10}}>{f.size < 1024 ? `${f.size} B` : `${(f.size/1024).toFixed(0)} KB`}</span>
              <button onClick={() => onChange(queue.filter((_, j) => j !== i))} style={{
                background:'transparent', border:'none', cursor:'pointer',
                color:'var(--ink-3)', padding:0, display:'inline-flex', justifyContent:'flex-end'
              }} title="Remove"><Ic.trash/></button>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

// ============================================================
// YAML SNIPPET — generated from the new-campaign draft
// ============================================================
function _generateYaml(d) {
  if (!d.id || !d.partner) return '# Fill in campaign id and partner to generate.';

  const lines = [
    `  - id: ${d.id}`,
    `    partner: ${_yamlStr(d.partner)}`,
    `    series: ${_yamlStr(d.series)}`,
    `    type: ${d.type}`,
    d.benchmark_category ? `    benchmark_category: ${_yamlStr(d.benchmark_category)}` : null,
    `    lifecycle: ${d.lifecycle}`,
    d.flight_start ? `    flight_start: ${d.flight_start}` : null,
    d.flight_end ? `    flight_end: ${d.flight_end}` : null,
    d.impression_goal ? `    impression_goal: ${d.impression_goal}` : null,
    d.budget_goal ? `    budget_goal: ${d.budget_goal}` : null,
    `    color: ${d.color}`,
    d.blurb ? `    blurb: ${_yamlStr(d.blurb)}` : null,
  ].filter(Boolean);

  if (d.ms_post_groups && d.ms_post_groups.trim()) {
    lines.push(`    ms_post_groups:`);
    d.ms_post_groups.split(',').map(s => s.trim()).filter(Boolean).forEach(g => {
      lines.push(`      - ${_yamlStr(g)}`);
    });
  }

  // Sources placeholder — the operator fills in the actual file names after dropping them.
  if (d.uploads.length > 0) {
    lines.push(`    sources:`);
    const grouped = {};
    d.uploads.forEach(u => {
      if (!grouped[u.target]) grouped[u.target] = [];
      grouped[u.target].push(u.name);
    });
    Object.entries(grouped).forEach(([source, files]) => {
      lines.push(`      ${source}:`);
      files.forEach(f => lines.push(`        - ${f}`));
    });
  }

  if (d.type === 'content' && d.episodes.length > 0) {
    lines.push(`    episodes:`);
    d.episodes.forEach((ep, i) => {
      const id = `ep${i + 1}`;
      const matches = ep.match.split(',').map(s => s.trim()).filter(Boolean);
      lines.push(`      - id: ${id}`);
      lines.push(`        n: ${_yamlStr(ep.n || `Ep. ${String(i+1).padStart(2,'0')}`)}`);
      if (ep.title) lines.push(`        title: ${_yamlStr(ep.title)}`);
      if (ep.date) lines.push(`        date: ${_yamlStr(ep.date)}`);
      if (matches.length > 0) {
        lines.push(`        match: [${matches.map(_yamlStr).join(', ')}]`);
      }
      lines.push(`        exclude: []`);
    });
  }

  return lines.join('\n');
}

function _yamlStr(s) {
  if (s == null) return '""';
  const needsQuotes = /[:#\-?{}\[\]&*!|>'"%@`,\n]|^\s|\s$/.test(s);
  if (!needsQuotes) return s;
  // Use double quotes; escape backslashes and double quotes.
  return '"' + String(s).replace(/\\/g, '\\\\').replace(/"/g, '\\"') + '"';
}

function YamlOutput({ yaml }) {
  const [copied, setCopied] = React.useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(yaml);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback: select the text
      const ta = document.getElementById('yaml-output');
      if (ta) { ta.focus(); ta.select(); }
    }
  };

  return (
    <div className="sec" style={{marginBottom:48}}>
      <div className="sec-h" style={{display:'flex', justifyContent:'space-between', alignItems:'flex-end'}}>
        <div>
          <div className="sec-title">YAML <em>snippet</em></div>
          <div className="sec-sub" style={{marginTop:6}}>Paste this under <code>campaigns:</code> in <code>config/campaigns.yaml</code>, then run <code>python -m app.viewer.refresh</code>.</div>
        </div>
        <button onClick={copy} className="btn btn-acc">
          <Ic.copy/> {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre id="yaml-output" style={{
        background:'var(--liquorice)', color:'var(--cream)',
        padding:20, borderRadius:8, fontSize:12, lineHeight:1.55,
        fontFamily:'var(--mono)', overflowX:'auto', whiteSpace:'pre',
        margin:0
      }}>{yaml}</pre>
    </div>
  );
}

window.InputsPage = InputsPage;
