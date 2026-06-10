/* global React, CAMPAIGNS, TOP_POSTS, HERO_POST, CHANNELS, FORMATS, MONTHLY_DELIVERY, SOURCES, fmt */
// Use React.useState etc. directly — top-level destructuring collides across Babel scripts.

// ============================================================
// ICONS (minimal, hand-drawn vibe)
// ============================================================
const Ic = {
  arrow: (p) => <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M3 8h10M9 4l4 4-4 4"/></svg>,
  arrowUp: (p) => <svg viewBox="0 0 16 16" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M3 12l5-5 3 3 2-2"/><path d="M10 8h3v3"/></svg>,
  arrowDn: (p) => <svg viewBox="0 0 16 16" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M3 4l5 5 3-3 2 2"/><path d="M10 8h3v-3"/></svg>,
  search: (p) => <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.6" {...p}><circle cx="7" cy="7" r="4.5"/><path d="M11 11l3 3" strokeLinecap="round"/></svg>,
  bell: (p) => <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" {...p}><path d="M4 11h8l-1-2V7a3 3 0 0 0-6 0v2L4 11z"/><path d="M7 13a1 1 0 0 0 2 0"/></svg>,
  cal: (p) => <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.6" {...p}><rect x="2" y="3" width="12" height="11" rx="1.5"/><path d="M2 6h12M5 1.5v3M11 1.5v3" strokeLinecap="round"/></svg>,
  download: (p) => <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M8 2v8M5 7l3 3 3-3M3 13h10"/></svg>,
  filter: (p) => <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" {...p}><path d="M2 4h12M4 8h8M6 12h4"/></svg>,
  back: (p) => <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M13 8H3M7 4L3 8l4 4"/></svg>,
  dot: () => <svg viewBox="0 0 16 16" width="14" height="14" fill="currentColor"><circle cx="8" cy="8" r="3"/></svg>,
  grid: () => <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.4"><rect x="2" y="2" width="5" height="5"/><rect x="9" y="2" width="5" height="5"/><rect x="2" y="9" width="5" height="5"/><rect x="9" y="9" width="5" height="5"/></svg>,
  campaign: () => <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"><path d="M2 6l11-3v10L2 10V6z"/><path d="M5 11v2"/></svg>,
  posts: () => <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.4"><rect x="2" y="2" width="12" height="12" rx="1.5"/><path d="M2 6h12M5 9h6M5 11h4"/></svg>,
  bench: () => <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"><path d="M2 13h12M4 13V8M7 13V5M10 13V9M13 13V3"/></svg>,
  ext: () => <svg viewBox="0 0 16 16" width="11" height="11" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d="M6 3H3v10h10V10"/><path d="M9 3h4v4M13 3l-6 6"/></svg>,
  settings: () => <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.4"><circle cx="8" cy="8" r="2"/><path d="M8 1v2M8 13v2M3.5 3.5l1.4 1.4M11.1 11.1l1.4 1.4M1 8h2M13 8h2M3.5 12.5l1.4-1.4M11.1 4.9l1.4-1.4"/></svg>,
  plus: () => <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"><path d="M8 3v10M3 8h10"/></svg>,
  upload: () => <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d="M8 11V3M5 6l3-3 3 3M3 13h10"/></svg>,
  trash: () => <svg viewBox="0 0 16 16" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M3 4h10M6 4V2.5h4V4M5 4l1 9h4l1-9"/></svg>,
  copy: () => <svg viewBox="0 0 16 16" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><rect x="5" y="5" width="9" height="9" rx="1.5"/><path d="M11 5V3a1 1 0 0 0-1-1H3a1 1 0 0 0-1 1v7a1 1 0 0 0 1 1h2"/></svg>,
};

// ============================================================
// PLATFORM PILLS
// ============================================================
const PLATFORM_COLORS = {
  'LinkedIn': '#0A66C2', 'Instagram': '#E4405F', 'TikTok': '#000000',
  'X': '#1d1d1f', 'YouTube': '#E00922', 'Facebook': '#1877F2',
  'Snapchat': '#FFFC00',
};
function PlatformPill({ name }) {
  return (
    <span className="post-plat">
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: PLATFORM_COLORS[name] || '#666' }}/>
      {name}
    </span>
  );
}

// ============================================================
// SIDEBAR
// ============================================================
function Sidebar({ active, onNav, campaigns }) {
  return (
    <aside className="sidebar">
      <div className="sb-brand">
        <span className="name" style={{fontFamily:'var(--serif)', fontSize:20, letterSpacing:'0.18em', fontWeight:400, textTransform:'uppercase', fontStyle:'normal'}}>
          <em style={{fontStyle:'italic', fontWeight:300}}>Campaign</em> Pulse
        </span>
      </div>

      <button className={"sb-item " + (active === 'overview' ? 'active' : '')} onClick={() => onNav({ view: 'overview' })}>
        <Ic.grid/> Overview
      </button>
      <button className={"sb-item " + (active === 'benchmarks' ? 'active' : '')} onClick={() => onNav({ view: 'benchmarks' })}>
        <Ic.bench/> Benchmarks
      </button>
      <button className={"sb-item " + (active === 'inputs' ? 'active' : '')} onClick={() => onNav({ view: 'inputs' })}>
        <Ic.plus/> Add Campaign Data
      </button>
      <button className={"sb-item " + (active === 'archive' ? 'active' : '')} onClick={() => onNav({ view: 'archive' })}>
        <Ic.posts/> Data Archive
      </button>

      {(() => {
        const active_only = campaigns.filter(c => (c.lifecycle || 'active') === 'active');
        const wrapped = campaigns.filter(c => c.lifecycle === 'wrapped');
        // Three buckets — Content (longform / series), Social (post-driven),
        // BrandX (paid-performance dark social).
        const content = active_only.filter(c => c.type === 'content');
        const social  = active_only.filter(c => c.type === 'social');
        const brandx  = active_only.filter(c => c.type === 'brandx');
        const renderItem = (c) => (
          <button key={c.id}
            className={"sb-item " + (active === 'campaign' && window.__activeCampaignId === c.id ? 'active' : '')}
            onClick={() => onNav({ view: 'campaign', id: c.id })}>
            <Ic.campaign/>
            <span style={{flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'}}>{c.partner}</span>
            <span className="dot" style={{
              background: c.statusKind === 'on' ? '#8FC766' : c.statusKind === 'warn' ? '#FF9947' : '#DE6B38'
            }}/>
          </button>
        );
        return (
          <>
            {content.length > 0 && <div className="sb-section">Content</div>}
            {content.map(renderItem)}
            {social.length > 0 && <div className="sb-section">Social</div>}
            {social.map(renderItem)}
            {brandx.length > 0 && <div className="sb-section">BrandX</div>}
            {brandx.map(renderItem)}
            {wrapped.length > 0 && <div className="sb-section">Wrapped</div>}
            {wrapped.map(renderItem)}
          </>
        );
      })()}

      {/* Sidebar footer — last-refreshed timestamp + manual trigger.
          Anyone on the team can click Refresh now without bothering the
          operator; it just triggers the GitHub Action that the 2-hourly cron
          would have run anyway. */}
      <RefreshFooter/>

    </aside>
  );
}

// ============================================================
// REFRESH FOOTER — shows last refresh time + "Refresh now" button
// ============================================================
function RefreshFooter() {
  const [status, setStatus] = React.useState({ kind: 'idle' });
  const last = window.LAST_REFRESHED || null;

  // Render an absolute timestamp like "Jun 3, 8:47pm UTC" — relative
  // ("2 min ago") is friendlier but stale after page-load, and the team
  // shares this dashboard across timezones so an explicit timezone helps.
  const lastLabel = (() => {
    if (!last) return 'Last refresh: unknown';
    try {
      const d = new Date(last);
      const opts = { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZone: 'UTC' };
      return `Last refresh: ${d.toLocaleString('en-US', opts)} UTC`;
    } catch {
      return 'Last refresh: ' + String(last);
    }
  })();

  const trigger = async () => {
    let password = sessionStorage.getItem('inputs.upload.password');
    if (!password) {
      password = window.prompt('Team refresh password:') || '';
      if (!password) return;
      sessionStorage.setItem('inputs.upload.password', password);
    }
    setStatus({ kind: 'pending' });
    try {
      const res = await fetch('/.netlify/functions/refresh-now', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      });
      const j = await res.json().catch(() => ({}));
      if (res.ok) {
        setStatus({ kind: 'queued', message: j.message || 'Refresh queued.' });
      } else {
        if (res.status === 401) sessionStorage.removeItem('inputs.upload.password');
        setStatus({ kind: 'error', message: j.error || `HTTP ${res.status}` });
      }
    } catch (e) {
      setStatus({ kind: 'error', message: String(e?.message || e) });
    }
  };

  return (
    <div style={{
      marginTop: 'auto',
      padding: '14px 16px 12px',
      borderTop: '1px solid var(--line)',
      display: 'flex',
      flexDirection: 'column',
      gap: 8,
    }}>
      <div style={{fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--ink-3)', letterSpacing: '0.04em'}}>
        {lastLabel}
      </div>
      <button
        onClick={trigger}
        disabled={status.kind === 'pending'}
        style={{
          background: status.kind === 'pending' ? 'var(--ink-3)' : 'var(--liquorice)',
          color: 'var(--cream)',
          border: 'none', borderRadius: 6,
          padding: '7px 12px', fontSize: 11, fontWeight: 600,
          fontFamily: 'inherit', letterSpacing: '0.04em',
          cursor: status.kind === 'pending' ? 'wait' : 'pointer',
          width: '100%',
        }}>
        {status.kind === 'pending' ? 'Triggering…'
          : status.kind === 'queued' ? '✓ Queued — ~2 min'
          : status.kind === 'error' ? '⚠ Try again'
          : 'Refresh now'}
      </button>
      {status.kind === 'error' && (
        <div style={{fontSize: 10, color: 'var(--danger, #b8392b)', lineHeight: 1.3}}>{status.message}</div>
      )}
    </div>
  );
}

// ============================================================
// HEADER
// ============================================================
function PageHead({ overline, title, italic, sub, actions }) {
  return (
    <div className="head">
      <div>
        {overline && <div style={{
          fontSize: 11, letterSpacing: '0.12em', textTransform: 'uppercase',
          color: 'var(--ink-3)', fontWeight: 600, marginBottom: 12
        }}>{overline}</div>}
        <h1 className="head-title">
          {title}{italic && <> <em>{italic}</em></>}
        </h1>
        {sub && <div className="head-sub" style={{marginTop: 10}}>{sub}</div>}
      </div>
      <div className="head-actions">{actions}</div>
    </div>
  );
}

// ============================================================
// PROGRESS BAR (svg)
// ============================================================
function PaceBar({ pct, onLight = true }) {
  return (
    <div className="pace-bar" style={{ background: onLight ? 'rgba(36,28,23,0.18)' : 'rgba(252,247,219,0.2)' }}>
      <i style={{ width: Math.min(100, pct) + '%', background: onLight ? 'var(--liquorice)' : 'var(--cream)' }}/>
    </div>
  );
}

// ============================================================
// WRAP-CAMPAIGN BUTTON — pinned to the campaign detail header. The viewer
// is read-only (can't write to YAML directly), so this button:
//   • toggles a pending "wrap" intent in localStorage
//   • shows a modal explaining what will change + the YAML edits required
//   • surfaces a copy-paste YAML snippet so the operator can apply the change
//
// On the next refresh the operator updates campaigns.yaml manually and the
// dashboard re-renders with the campaign in the Wrapped section.
// ============================================================
function WrapCampaignButton({ campaign }) {
  const c = campaign;
  const isWrapped = c.lifecycle === 'wrapped';
  const [open, setOpen] = React.useState(false);
  const [endDate, setEndDate] = React.useState(() => new Date().toISOString().slice(0, 10));

  if (isWrapped) {
    return (
      <div style={{
        padding:'8px 12px', borderRadius:'var(--r-md)',
        background:'var(--liquorice)', color:'var(--cream)',
        fontSize:11, letterSpacing:'0.06em', fontFamily:'var(--mono)',
        textAlign:'center', fontWeight:600, textTransform:'uppercase'
      }}>
        ✓ Wrapped
      </div>
    );
  }

  // Generate the YAML edit instructions
  const snippet =
    `# Edit config/campaigns.yaml — find the entry for id: ${c.id}\n` +
    `# Change these two lines:\n` +
    `\n` +
    `    lifecycle: wrapped       # was: active\n` +
    `    flight_end: ${endDate}   # set to actual end date\n` +
    `\n` +
    `# Then run: python -m app.viewer.refresh`;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(snippet);
      alert('Copied to clipboard. Paste into config/campaigns.yaml.');
    } catch {
      // ignore
    }
  };

  return (
    <>
      <button onClick={() => setOpen(true)} style={{
        padding:'8px 14px', borderRadius:'var(--r-md)',
        background:'var(--bg)', border:'1px solid var(--line)',
        color:'var(--ink-2)', fontSize:12, fontFamily:'inherit', fontWeight:500,
        cursor:'pointer', display:'inline-flex', alignItems:'center', gap:6,
        justifyContent:'center'
      }}>
        Mark as wrapped
      </button>

      {open && (
        <div style={{
          position:'fixed', inset:0, zIndex:9999,
          background:'rgba(31,26,21,0.55)', backdropFilter:'blur(4px)',
          display:'flex', alignItems:'center', justifyContent:'center', padding:24
        }} onClick={() => setOpen(false)}>
          <div onClick={(e) => e.stopPropagation()} style={{
            background:'var(--surface)', borderRadius:12, padding:28,
            maxWidth:560, width:'100%', boxShadow:'0 20px 60px rgba(0,0,0,0.3)'
          }}>
            <div style={{fontSize:11, letterSpacing:'0.12em', textTransform:'uppercase', color:'var(--ink-3)', fontWeight:600, marginBottom:8}}>
              Wrap campaign
            </div>
            <div style={{fontFamily:'var(--serif)', fontSize:26, fontWeight:300, letterSpacing:'-0.01em', marginBottom:14}}>
              Mark <em>{c.partner}</em> as wrapped?
            </div>
            <div style={{fontSize:13, color:'var(--ink-2)', lineHeight:1.6, marginBottom:18}}>
              The dashboard is read-only, so it can't edit the config file directly.
              When you confirm, we'll generate the exact two-line YAML edit for you to
              paste into <code>config/campaigns.yaml</code>. On the next refresh,
              this campaign moves from <strong>Active</strong> to <strong>Recently wrapped</strong>:
              the sidebar groups it under Wrapped, and Overview shows a smaller black card
              with only final delivery numbers.
            </div>

            <div style={{
              display:'flex', alignItems:'center', gap:10, marginBottom:18,
              padding:'12px 14px', background:'var(--bg-soft)',
              border:'1px solid var(--line)', borderRadius:8
            }}>
              <span style={{fontSize:11, fontWeight:600, color:'var(--ink-3)', letterSpacing:'0.06em', textTransform:'uppercase', fontFamily:'var(--mono)'}}>Actual end date</span>
              <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)}
                style={{
                  flex:1, padding:'6px 10px', border:'1px solid var(--line)',
                  borderRadius:6, fontSize:13, fontFamily:'inherit', background:'var(--bg)'
                }}/>
            </div>

            <pre style={{
              background:'var(--liquorice)', color:'var(--cream)',
              padding:16, borderRadius:8, fontSize:11, lineHeight:1.55,
              fontFamily:'var(--mono)', whiteSpace:'pre-wrap', wordBreak:'break-word',
              margin:'0 0 18px 0', maxHeight:200, overflowY:'auto'
            }}>{snippet}</pre>

            <div style={{display:'flex', gap:10, justifyContent:'flex-end'}}>
              <button onClick={() => setOpen(false)} style={{
                background:'transparent', border:'1px solid var(--line)', borderRadius:6,
                padding:'9px 16px', fontSize:13, fontFamily:'inherit', cursor:'pointer',
                color:'var(--ink-2)'
              }}>Cancel</button>
              <button onClick={copy} className="btn btn-acc">
                <Ic.copy/> Copy YAML edit
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

// ============================================================
// WRAPPED CAMPAIGN CARD — compact black card for Recently Wrapped section.
// Shows partner / series / status / posts / impressions / flight only.
// ============================================================
function WrappedCard({ c, onClick }) {
  const dateRangeFromFlight = (flight) => {
    // The flight label is already formatted (e.g., "Apr 21 — May 15, 2026"). Use as-is.
    return flight;
  };
  return (
    <div
      onClick={onClick}
      style={{
        background: 'var(--liquorice)', color: 'var(--cream)',
        borderRadius: 'var(--r-md)', padding: '20px 22px',
        cursor: 'pointer', display: 'flex', flexDirection: 'column', gap: 12,
        transition: 'transform 0.15s, box-shadow 0.15s',
        border: '1px solid rgba(252,247,219,0.08)',
        minHeight: 0,
      }}
      onMouseEnter={(e) => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = '0 6px 18px rgba(0,0,0,0.18)'; }}
      onMouseLeave={(e) => { e.currentTarget.style.transform = ''; e.currentTarget.style.boxShadow = ''; }}
    >
      <div>
        <div style={{
          fontSize: 13, fontWeight: 600, letterSpacing: '0.04em',
          color: 'var(--cream)', textTransform: 'uppercase', marginBottom: 2
        }}>{c.partner}</div>
        <div style={{
          fontFamily: 'var(--serif)', fontSize: 22, fontWeight: 300,
          letterSpacing: '-0.01em', lineHeight: 1.15, color: 'var(--cream)'
        }}>
          {c.series.replace(c.seriesItalic, '')}<em>{c.seriesItalic}</em>
        </div>
      </div>
      <div style={{
        display: 'inline-flex', alignItems: 'center', gap: 6, alignSelf: 'flex-start',
        padding: '4px 10px', borderRadius: 999,
        background: 'rgba(143,199,102,0.16)', color: '#a4d77e',
        fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.06em', fontWeight: 600
      }}>
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#a4d77e' }}/>
        {c.status}
      </div>
      <div style={{ display: 'flex', gap: 24, marginTop: 4 }}>
        <div>
          <div style={{ fontFamily: 'var(--serif)', fontSize: 22, fontWeight: 300, color: 'var(--cream)' }}>
            {c.posts}
          </div>
          <div style={{ fontSize: 9, color: 'rgba(252,247,219,0.55)', letterSpacing: '0.1em', textTransform: 'uppercase', fontWeight: 600 }}>Posts</div>
        </div>
        <div>
          <div style={{ fontFamily: 'var(--serif)', fontSize: 22, fontWeight: 300, color: 'var(--cream)' }}>
            {fmt.num(c.impressions.delivered)}
          </div>
          <div style={{ fontSize: 9, color: 'rgba(252,247,219,0.55)', letterSpacing: '0.1em', textTransform: 'uppercase', fontWeight: 600 }}>Impressions</div>
        </div>
      </div>
      <div style={{
        fontSize: 10, fontFamily: 'var(--mono)', color: 'rgba(252,247,219,0.45)',
        letterSpacing: '0.06em', marginTop: 4
      }}>{dateRangeFromFlight(c.flight)}</div>
    </div>
  );
}

// ============================================================
// CAMPAIGN CARD (overview)
// ============================================================
function CampaignCard({ c, onClick }) {
  const impPct = (c.impressions.delivered / c.impressions.goal) * 100;
  const budPct = (c.budget.delivered / c.budget.goal) * 100;
  return (
    <div className={"cmp-card " + c.color} onClick={onClick}>
      <div className="arrow"><Ic.arrow/></div>
      <div>
        <div className="partner-row">
          <span className="partner">{c.partner}</span>
        </div>
        <div className="series">
          {c.series.replace(c.seriesItalic, '')}
          <em>{c.seriesItalic}</em>
        </div>
        <div style={{ display: 'flex', gap: 8, marginBottom: 4, flexWrap: 'wrap' }}>
          <span className="pill" style={{
            background: 'rgba(36,28,23,0.12)', border: 'none', color: 'var(--liquorice)',
            fontWeight: 600
          }}>
            <span className="dot" style={{
              background: c.statusKind === 'on' ? '#2f7a3f' : c.statusKind === 'warn' ? '#b8392b' : '#b8392b'
            }}/>
            {c.status}
          </span>
          <span className="pill" style={{
            background: 'rgba(36,28,23,0.08)', border: 'none', color: 'var(--liquorice)'
          }}>{c.type === 'social'
              ? `${c.posts} ${c.posts === 1 ? 'post' : 'posts'}`
              : `${c.episodes} eps · ${c.posts} posts`}</span>
        </div>
      </div>
      <div className="cmp-pacing">
        <div className="pace-row">
          <div className="pace-meta">
            <span className="pl">Impressions</span>
            <span className="pv">{fmt.num(c.impressions.delivered)} / {fmt.num(c.impressions.goal)}</span>
          </div>
          <PaceBar pct={impPct} onLight={c.color !== 'ft-ink'}/>
        </div>
        <div className="pace-row">
          <div className="pace-meta">
            <span className="pl">Budget</span>
            <span className="pv">{fmt.money(c.budget.delivered)} / {fmt.money(c.budget.goal)}</span>
          </div>
          <PaceBar pct={budPct} onLight={c.color !== 'ft-ink'}/>
        </div>
      </div>
      <div className="meta-foot">
        <span>{c.flight}</span>
        <span>{c.elapsedPct.toFixed(0)}% elapsed · {c.daysLeft}d left</span>
      </div>
    </div>
  );
}

// ============================================================
// SVG LINE CHART
// ============================================================
function MultiLineChart({ data, series, height = 220 }) {
  const W = 760, H = height, P = { t: 18, r: 18, b: 28, l: 36 };
  const xs = data.map((_, i) => i);
  const allVals = data.flatMap(d => series.map(s => d[s.key]));
  const yMax = Math.max(...allVals) * 1.12;
  const x = (i) => P.l + (i * (W - P.l - P.r)) / Math.max(1, data.length - 1);
  const y = (v) => H - P.b - (v / yMax) * (H - P.t - P.b);

  const yTicks = 4;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{width:'100%',height:'100%',display:'block'}}>
      {/* gridlines */}
      {[...Array(yTicks + 1)].map((_, i) => {
        const v = (yMax / yTicks) * i;
        const yy = y(v);
        return (
          <g key={i}>
            <line x1={P.l} x2={W - P.r} y1={yy} y2={yy} stroke="currentColor" strokeOpacity="0.08"/>
            <text x={P.l - 8} y={yy + 3} fontSize="9" textAnchor="end" fill="currentColor" opacity="0.5">{fmt.num(v)}</text>
          </g>
        );
      })}
      {/* x labels */}
      {data.map((d, i) => (
        <text key={i} x={x(i)} y={H - 8} fontSize="10" textAnchor="middle" fill="currentColor" opacity="0.6">{d.m}</text>
      ))}
      {/* lines */}
      {series.map(s => {
        const pts = data.map((d, i) => `${x(i)},${y(d[s.key])}`).join(' ');
        return (
          <g key={s.key}>
            <polyline points={pts} fill="none" stroke={s.color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            {data.map((d, i) => (
              <circle key={i} cx={x(i)} cy={y(d[s.key])} r="3" fill={s.color}/>
            ))}
          </g>
        );
      })}
    </svg>
  );
}

// ============================================================
// SVG DONUT
// ============================================================
function Donut({ data, size = 180, thickness = 28, centerLabel, centerValue }) {
  const total = data.reduce((s, d) => s + d.value, 0);
  const r = (size - thickness) / 2;
  const C = 2 * Math.PI * r;
  let acc = 0;
  return (
    <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size}>
      <g transform={`translate(${size/2},${size/2}) rotate(-90)`}>
        {data.map((d, i) => {
          const len = (d.value / total) * C;
          const dasharray = `${len} ${C - len}`;
          const dashoffset = -acc;
          acc += len;
          return (
            <circle key={i} r={r} fill="none" stroke={d.color}
              strokeWidth={thickness} strokeDasharray={dasharray} strokeDashoffset={dashoffset}/>
          );
        })}
      </g>
      <text x={size/2} y={size/2 - 4} textAnchor="middle"
        fontFamily="var(--serif)" fontSize="32" fill="currentColor">{centerValue}</text>
      <text x={size/2} y={size/2 + 16} textAnchor="middle"
        fontSize="10" fill="currentColor" opacity="0.6"
        style={{textTransform:'uppercase', letterSpacing:'0.1em', fontWeight:600}}>{centerLabel}</text>
    </svg>
  );
}

// ============================================================
// SVG BAR CHART
// ============================================================
function BarChart({ data, height = 220, valKey = 'value' }) {
  const W = 600, H = height, P = { t: 16, r: 16, b: 36, l: 16 };
  const max = Math.max(...data.map(d => d[valKey])) * 1.1;
  const bw = (W - P.l - P.r) / data.length - 8;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{width:'100%',height:'100%',display:'block'}}>
      {data.map((d, i) => {
        const x = P.l + i * ((W - P.l - P.r) / data.length) + 4;
        const h = (d[valKey] / max) * (H - P.t - P.b);
        const y = H - P.b - h;
        return (
          <g key={i}>
            <rect x={x} y={y} width={bw} height={h} rx="6" fill={d.color || 'var(--ink)'} opacity={d.dim ? 0.3 : 1}/>
            <text x={x + bw/2} y={H - 18} fontSize="11" textAnchor="middle" fill="currentColor" opacity="0.7">{d.label}</text>
            <text x={x + bw/2} y={H - 6} fontSize="10" textAnchor="middle" fill="currentColor" opacity="0.5">{d.sub || ''}</text>
            <text x={x + bw/2} y={y - 6} fontSize="11" textAnchor="middle" fill="currentColor" fontWeight="600">{fmt.num(d[valKey])}</text>
          </g>
        );
      })}
    </svg>
  );
}

// ============================================================
// EPISODE PERFORMANCE TABLE — collapsible per-platform breakdown
// ============================================================
function EpisodePerformanceTable({ episodes, channels }) {
  const [open, setOpen] = React.useState(null); // episode index

  const distLabel = (k) =>
    k === 'organic' ? { txt: 'Organic only', bg: 'rgba(143,199,102,0.18)', fg: '#2f7a3f' } :
    k === 'paid'    ? { txt: 'Paid only',    bg: 'rgba(36,28,23,0.10)',    fg: 'var(--liquorice)' } :
                      { txt: 'Organic + Boosted', bg: 'rgba(92,181,242,0.20)', fg: '#0a4f7a' };

  const chColor = (name) => (channels.find(c => c.name === name) || {}).color || '#666';

  return (
    // overflow-x:auto lets the per-channel detail table scroll horizontally
    // on narrow viewports rather than clipping the Spend column.
    <div className="card" style={{ padding: 0, overflow: 'hidden', overflowX: 'auto' }}>
      {episodes.map((e, idx) => {
        const isOpen = open === idx;
        return (
          <div key={e.n} style={{ borderBottom: idx < episodes.length - 1 ? '1px solid var(--line)' : 'none' }}>
            {/* Summary row */}
            <button
              onClick={() => setOpen(isOpen ? null : idx)}
              style={{
                width: '100%', background: 'transparent', border: 'none',
                cursor: 'pointer', textAlign: 'left',
                display: 'grid', gridTemplateColumns: '24px 1fr repeat(5, 100px) 30px',
                gap: 14, padding: '20px 24px', alignItems: 'center', fontFamily: 'inherit',
                color: 'inherit', borderTop: idx === 0 ? 'none' : '1px solid transparent'
              }}
            >
              <span style={{
                width: 22, height: 22, borderRadius: '50%',
                border: '1px solid var(--line-2)',
                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 11, transition: 'transform 0.2s',
                transform: isOpen ? 'rotate(90deg)' : 'rotate(0deg)',
                color: 'var(--ink-3)'
              }}>›</span>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                <span style={{ fontSize: 11, color: 'var(--ink-3)', letterSpacing: '0.08em', textTransform: 'uppercase', fontWeight: 600 }}>{e.n} · {e.date}</span>
                <span style={{ fontFamily: 'var(--serif)', fontSize: 19, fontWeight: 300, letterSpacing: '-0.01em' }}>{e.title}</span>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontFamily: 'var(--serif)', fontSize: 22, fontWeight: 300 }}>{fmt.num(e.total.impr)}</div>
                <div style={{ fontSize: 10, color: 'var(--ink-3)', letterSpacing: '0.08em', textTransform: 'uppercase', fontWeight: 600 }}>Impr.</div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontFamily: 'var(--serif)', fontSize: 22, fontWeight: 300 }}>{fmt.num(e.total.views || 0)}</div>
                <div style={{ fontSize: 10, color: 'var(--ink-3)', letterSpacing: '0.08em', textTransform: 'uppercase', fontWeight: 600 }}>Views</div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontFamily: 'var(--serif)', fontSize: 22, fontWeight: 300 }}>{fmt.num(e.total.eng)}</div>
                <div style={{ fontSize: 10, color: 'var(--ink-3)', letterSpacing: '0.08em', textTransform: 'uppercase', fontWeight: 600 }}>Eng.</div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontFamily: 'var(--serif)', fontSize: 22, fontWeight: 300 }}>{e.total.er}<span style={{ fontSize: 13, color: 'var(--ink-3)' }}>%</span></div>
                <div style={{ fontSize: 10, color: 'var(--ink-3)', letterSpacing: '0.08em', textTransform: 'uppercase', fontWeight: 600 }}>ER</div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontFamily: 'var(--serif)', fontSize: 22, fontWeight: 300 }}>${fmt.num(e.total.spend)}</div>
                <div style={{ fontSize: 10, color: 'var(--ink-3)', letterSpacing: '0.08em', textTransform: 'uppercase', fontWeight: 600 }}>Spend</div>
              </div>
              <span/>
            </button>

            {/* Detail rows — every individual post in this episode (not
                aggregated per platform; the by-channel section already does
                that). POST column shows the post title/quote. */}
            {isOpen && (
              <PerPostRows
                rows={e.posts || []}
                total={e.total}
                distLabel={distLabel}
                chColor={chColor}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ============================================================
// PER-POST ROWS — used both inside EpisodePerformanceTable expansions and
// as a standalone table for social campaigns.
//
// Columns: POST | Platform | Distribution | Total impr | Paid impr |
//          Organic impr | % Organic | Eng | ER | Spend
//
// Note: no "Posts" column (every row IS one post, so count is implicit).
// The Total row at the bottom shows aggregates; ER uses backend total.er
// when available (Pre-roll-excluded) else recomputed locally.
// ============================================================
// Column layout: Post | Platform | Distribution | Total impr | Views | Paid impr | Organic impr | % Org | Eng | ER | Spend
const PER_POST_GRID = '1.4fr 120px 130px 88px 84px 84px 84px 60px 70px 62px 92px';

function PerPostRows({ rows, total, distLabel, chColor }) {
  if (!rows || rows.length === 0) {
    return (
      <div style={{
        borderTop:'1px solid var(--line)', padding:'24px',
        textAlign:'center', fontSize:13, color:'var(--ink-3)'
      }}>No post-level data available for this episode.</div>
    );
  }
  return (
    <div style={{ borderTop: '1px solid var(--line)' }}>
      <PerPostHeader/>
      {rows.map((p, idx) => (
        <PerPostRow key={idx} p={p} distLabel={distLabel} chColor={chColor}/>
      ))}
      <PerPostTotal rows={rows} total={total}/>
    </div>
  );
}

function PerPostTable({ rows, distLabel, chColor }) {
  // Standalone version used by social campaigns. No outer card here — caller wraps.
  if (!rows || rows.length === 0) {
    return (
      <div className="card" style={{padding:'24px', textAlign:'center', fontSize:13, color:'var(--ink-3)'}}>
        No posts loaded yet for this campaign.
      </div>
    );
  }
  // Compute synthetic total (eng/impr) since there's no episode-level total here.
  const sum = (k) => rows.reduce((a, r) => a + (r[k] || 0), 0);
  const totalImpr = sum('impr');
  const totalEng = sum('eng');
  const total = {
    impr: totalImpr,
    eng: totalEng,
    spend: sum('spend'),
    er: totalImpr ? (totalEng / totalImpr * 100) : 0,
  };
  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden', overflowX: 'auto' }}>
      <PerPostHeader/>
      {rows.map((p, idx) => (
        <PerPostRow key={idx} p={p} distLabel={distLabel} chColor={chColor}/>
      ))}
      <PerPostTotal rows={rows} total={total}/>
    </div>
  );
}

function PerPostHeader() {
  return (
    <div style={{
      display: 'grid', gridTemplateColumns: PER_POST_GRID,
      gap: 10, padding: '14px 16px 12px 24px',
      fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--ink-3)',
      letterSpacing: '0.1em', fontWeight: 600, textTransform: 'uppercase',
      borderBottom: '1px solid var(--line)', background: 'var(--bg-soft)'
    }}>
      <div>Post</div>
      <div>Platform</div>
      <div>Distribution</div>
      <div style={{ textAlign: 'right' }}>Total impr.</div>
      <div style={{ textAlign: 'right' }}>Views</div>
      <div style={{ textAlign: 'right' }}>Paid impr.</div>
      <div style={{ textAlign: 'right' }}>Organic impr.</div>
      <div style={{ textAlign: 'right' }}>% Org</div>
      <div style={{ textAlign: 'right' }}>Eng.</div>
      <div style={{ textAlign: 'right' }}>ER</div>
      <div style={{ textAlign: 'right' }}>Spend</div>
    </div>
  );
}

function PerPostRow({ p, distLabel, chColor }) {
  const dist = distLabel(p.distKind);
  const totalSplit = (p.paidImpr || 0) + (p.orgImpr || 0);
  const orgPct = totalSplit ? (p.orgImpr / totalSplit) * 100 : 0;
  // Account-name subline. Distinguishes posts that share the same copy but
  // ran from different FOS pages (e.g. Heineken Champions League content
  // on the main FOS FB page vs. FOS Today). Only shown when MS resolved a
  // display name (ad-platform-only rows fall through to no subline).
  const accountSubline = p.accountName ? (
    <div style={{
      fontSize: 10, color: 'var(--ink-3)',
      fontFamily: 'var(--mono)', letterSpacing: '0.04em',
      marginTop: 2, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'
    }} title={`Posted from: ${p.accountName}`}>
      @ {p.accountName}
    </div>
  ) : null;
  const TitleInner = (
    <>
      <div style={{
        overflow:'hidden', textOverflow:'ellipsis', display:'-webkit-box',
        WebkitLineClamp:2, WebkitBoxOrient:'vertical',
        fontSize:12, fontWeight:500, lineHeight:1.35,
      }} title={p.title}>
        {p.title || '—'}
      </div>
      {accountSubline}
    </>
  );
  const TitleCell = p.url ? (
    <a href={p.url} target="_blank" rel="noreferrer"
      style={{
        color:'inherit', textDecoration:'none',
        minWidth: 0, paddingRight: 8, display: 'block',
      }}>
      {TitleInner}
    </a>
  ) : (
    <div style={{minWidth: 0, paddingRight: 8}}>{TitleInner}</div>
  );
  return (
    <div style={{
      display: 'grid', gridTemplateColumns: PER_POST_GRID,
      gap: 10, padding: '12px 16px 12px 24px', alignItems: 'center',
      borderBottom: '1px solid var(--line)',
      fontSize: 13, background: 'var(--bg)'
    }}>
      {TitleCell}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
        <span style={{ width: 8, height: 8, borderRadius: '50%', background: chColor(p.platform), flexShrink:0 }}/>
        <span style={{ fontSize:12, fontWeight: 500, whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis' }}>{p.platform}</span>
      </div>
      <span style={{
        background: dist.bg, color: dist.fg,
        fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '0.06em',
        fontWeight: 600, padding: '3px 7px', borderRadius: 3,
        justifySelf: 'start', textTransform: 'uppercase', whiteSpace:'nowrap'
      }}>{dist.txt}</span>
      <div style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums', fontWeight: 600 }}>{p.impr ? fmt.numFull(p.impr) : '—'}</div>
      <div style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums', fontWeight: 500 }}>{p.views ? fmt.numFull(p.views) : '—'}</div>
      <div style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums', fontWeight: 500 }}>{p.paidImpr ? fmt.numFull(p.paidImpr) : '—'}</div>
      <div style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums', fontWeight: 500, color: '#2f7a3f' }}>{p.orgImpr ? fmt.numFull(p.orgImpr) : '—'}</div>
      <div style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums', fontWeight: 500 }}>{totalSplit ? orgPct.toFixed(0) + '%' : '—'}</div>
      <div style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums', fontWeight: 500 }}>{p.eng ? fmt.numFull(p.eng) : '—'}</div>
      <div style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums', fontWeight: 500 }}>{p.er ? p.er + '%' : '—'}</div>
      <div style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums', fontWeight: 500 }}>{p.spend ? fmt.moneyFull(p.spend) : '—'}</div>
    </div>
  );
}

function PerPostTotal({ rows, total }) {
  const sum = (k) => rows.reduce((a, r) => a + (r[k] || 0), 0);
  const totalImpr = sum('impr');
  const totalViews = sum('views');
  const totalPaid = sum('paidImpr');
  const totalOrg = sum('orgImpr');
  const totalEng = sum('eng');
  const totalSpend = sum('spend');
  const denom = totalPaid + totalOrg;
  const orgPct = denom ? (totalOrg / denom) * 100 : 0;
  const totalEr = total?.er ?? (totalImpr ? (totalEng / totalImpr) * 100 : 0);
  return (
    <div style={{
      display: 'grid', gridTemplateColumns: PER_POST_GRID,
      gap: 10, padding: '16px 16px 16px 24px', alignItems: 'center',
      fontSize: 13, background: 'var(--bg-soft)',
      borderTop: '2px solid var(--liquorice)',
      fontWeight: 700
    }}>
      <div style={{
        fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.1em',
        textTransform: 'uppercase', color: 'var(--ink-2)', fontWeight: 700
      }}>Total ({rows.length} post{rows.length === 1 ? '' : 's'})</div>
      <div/>
      <div/>
      <div style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums', fontWeight: 700 }}>{totalImpr ? fmt.numFull(totalImpr) : '—'}</div>
      <div style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>{totalViews ? fmt.numFull(totalViews) : '—'}</div>
      <div style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>{totalPaid ? fmt.numFull(totalPaid) : '—'}</div>
      <div style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums', color: '#2f7a3f' }}>{totalOrg ? fmt.numFull(totalOrg) : '—'}</div>
      <div style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>{denom ? orgPct.toFixed(0) + '%' : '—'}</div>
      <div style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>{totalEng ? fmt.numFull(totalEng) : '—'}</div>
      <div style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>{totalImpr ? totalEr.toFixed(2) + '%' : '—'}</div>
      <div style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>{totalSpend ? fmt.moneyFull(totalSpend) : '—'}</div>
    </div>
  );
}

// expose
Object.assign(window, {
  Ic, PlatformPill, Sidebar, PageHead, PaceBar, CampaignCard, WrappedCard,
  WrapCampaignButton, MultiLineChart, Donut, BarChart, PLATFORM_COLORS,
  EpisodePerformanceTable, PerPostTable
});
