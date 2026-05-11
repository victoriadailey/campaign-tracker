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
};

// ============================================================
// PLATFORM PILLS
// ============================================================
const PLATFORM_COLORS = {
  'LinkedIn': '#0A66C2', 'Instagram': '#E4405F', 'TikTok': '#000000',
  'X': '#1d1d1f', 'YouTube': '#E00922', 'Facebook': '#1877F2'
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
        <span className="name" style={{fontFamily:'var(--serif)', fontSize:22, letterSpacing:'0.22em', fontWeight:400, textTransform:'uppercase', fontStyle:'normal'}}>PULSE</span>
      </div>

      <button className={"sb-item " + (active === 'overview' ? 'active' : '')} onClick={() => onNav({ view: 'overview' })}>
        <Ic.grid/> Overview
      </button>
      <button className="sb-item">
        <Ic.bench/> Benchmarks
      </button>

      <div className="sb-section">Campaigns</div>
      {campaigns.map(c => (
        <button key={c.id}
          className={"sb-item " + (active === 'campaign' && window.__activeCampaignId === c.id ? 'active' : '')}
          onClick={() => onNav({ view: 'campaign', id: c.id })}>
          <Ic.campaign/>
          <span style={{flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'}}>{c.partner}</span>
          <span className="dot" style={{
            background: c.statusKind === 'on' ? '#8FC766' : c.statusKind === 'warn' ? '#FF9947' : '#DE6B38'
          }}/>
        </button>
      ))}

      <div className="sb-section">Workspace</div>
      <button className="sb-item"><Ic.download/> Exports</button>
      <button className="sb-item"><Ic.settings/> Settings</button>

      <div className="sb-foot">
        <div className="sb-avatar">JG</div>
        <div className="who">
          <div className="nm">Jordan G.</div>
          <div className="em">Branded Content</div>
        </div>
      </div>
    </aside>
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
          }}>{c.episodes} eps</span>
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
    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
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
                display: 'grid', gridTemplateColumns: '24px 1fr repeat(4, 110px) 30px',
                gap: 18, padding: '20px 24px', alignItems: 'center', fontFamily: 'inherit',
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

            {/* Detail rows — clean tabular style matching the dashboard */}
            {isOpen && (
              <div style={{ borderTop: '1px solid var(--line)' }}>
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: '180px 140px 110px 110px 90px 90px 90px 100px',
                  gap: 14, padding: '14px 24px 12px 64px',
                  fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--ink-3)',
                  letterSpacing: '0.1em', fontWeight: 600, textTransform: 'uppercase',
                  borderBottom: '1px solid var(--line)', background: 'var(--bg-soft)'
                }}>
                  <div>Platform</div>
                  <div>Distribution</div>
                  <div style={{ textAlign: 'right' }}>Paid impr.</div>
                  <div style={{ textAlign: 'right' }}>Organic impr.</div>
                  <div style={{ textAlign: 'right' }}>% Organic</div>
                  <div style={{ textAlign: 'right' }}>Eng.</div>
                  <div style={{ textAlign: 'right' }}>ER</div>
                  <div style={{ textAlign: 'right' }}>Spend</div>
                </div>
                {e.perChannel.map(p => {
                  const dist = distLabel(p.distKind);
                  const total = p.paidImpr + p.orgImpr;
                  const orgPct = total ? (p.orgImpr / total) * 100 : 0;
                  return (
                    <div key={p.name} style={{
                      display: 'grid',
                      gridTemplateColumns: '180px 140px 110px 110px 90px 90px 90px 100px',
                      gap: 14, padding: '14px 24px 14px 64px', alignItems: 'center',
                      borderBottom: '1px solid var(--line)',
                      fontSize: 13, background: 'var(--bg)'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <span style={{ width: 8, height: 8, borderRadius: '50%', background: chColor(p.name) }}/>
                        <span style={{ fontWeight: 500 }}>{p.name}</span>
                      </div>
                      <span style={{
                        background: dist.bg, color: dist.fg,
                        fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '0.08em',
                        fontWeight: 600, padding: '3px 7px', borderRadius: 3,
                        justifySelf: 'start', textTransform: 'uppercase'
                      }}>{dist.txt}</span>
                      <div style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums', fontWeight: 500 }}>{p.paidImpr ? fmt.num(p.paidImpr) : '—'}</div>
                      <div style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums', fontWeight: 500, color: '#2f7a3f' }}>{p.orgImpr ? fmt.num(p.orgImpr) : '—'}</div>
                      <div style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums', fontWeight: 500 }}>{total ? orgPct.toFixed(0) + '%' : '—'}</div>
                      <div style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums', fontWeight: 500 }}>{fmt.num(p.eng)}</div>
                      <div style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums', fontWeight: 500 }}>{p.er}%</div>
                      <div style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums', fontWeight: 500 }}>{p.spend ? '$' + fmt.num(p.spend) : '—'}</div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// expose
Object.assign(window, {
  Ic, PlatformPill, Sidebar, PageHead, PaceBar, CampaignCard,
  MultiLineChart, Donut, BarChart, PLATFORM_COLORS, EpisodePerformanceTable
});
