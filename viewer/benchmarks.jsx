/* global React, BENCHMARKS_DATA, PageHead */
const { useState: useStateB } = React;

// ============================================================
// BENCHMARKS PAGE
// FOS social ER benchmarks across content categories.
// Source: config/social_benchmarks.csv
// ============================================================

function BenchmarksPage() {
  const data = window.BENCHMARKS_DATA || {};
  const categories = data.categories || [];
  const platformSummary = data.platformSummary || data.platform_summary || [];
  const lastUpdated = data.lastUpdated || data.last_updated || '—';
  const [openIdx, setOpenIdx] = useStateB(0);

  const hasLive = !!(data.live && (data.live.campaigns || []).length);

  return (
    <>
      <LiveBenchmarks/>

      {!hasLive && (
        <PageHead
          overline={`FOS Internal · Last updated ${lastUpdated}`}
          title="Benchmarks"
          italic="by category."
          sub={<>Engagement rate benchmarks across content types, drawn from completed FOS campaigns. <strong>Sponsored-only</strong> is the true benchmark for current work; <strong>all-content</strong> shown as a broader reference.</>}
        />
      )}

      {/* PLATFORM SUMMARY */}
      <div className="sec">
        <div className="sec-h">
          <div>
            <div className="sec-title">Platform <em>benchmarks (2025)</em></div>
            <div className="sec-sub" style={{marginTop:6}}>Aggregate ER% across all FOS social activity.</div>
          </div>
        </div>
        <PlatformSummaryTable rows={platformSummary}/>
      </div>

      {/* CATEGORY NAV CHIPS */}
      <div className="sec">
        <div className="sec-h">
          <div>
            <div className="sec-title">By <em>category</em></div>
            <div className="sec-sub" style={{marginTop:6}}>Click a category to jump to its detail.</div>
          </div>
        </div>
        <div style={{display:'flex', flexWrap:'wrap', gap:8, marginBottom:24}}>
          {categories.map((cat, i) => (
            <button
              key={i}
              onClick={() => { setOpenIdx(i); document.getElementById(`cat-${i}`)?.scrollIntoView({behavior:'smooth', block:'start'}); }}
              style={{
                fontFamily:'inherit', fontSize:12, fontWeight:500,
                padding:'7px 14px', borderRadius:999,
                background: i === openIdx ? 'var(--liquorice)' : 'var(--surface)',
                color: i === openIdx ? 'var(--cream)' : 'var(--ink)',
                border:`1px solid ${i === openIdx ? 'var(--liquorice)' : 'var(--line)'}`,
                cursor:'pointer'
              }}
            >
              {shortCategoryName(cat.name)}
            </button>
          ))}
        </div>
      </div>

      {/* CATEGORY SECTIONS */}
      {categories.map((cat, i) => (
        <CategorySection key={i} cat={cat} idx={i}/>
      ))}
    </>
  );
}

// ══════════════════════════════════════════════════════════
// LIVE BENCHMARKS — filterable dashboard (window.BENCHMARKS_DATA.live)
// Video/Static · Custom/Franchise · Paid-only/Organic+Boosted
// ══════════════════════════════════════════════════════════
const LIVE_PLATFORMS = ['Instagram', 'Facebook', 'X', 'TikTok', 'LinkedIn', 'YouTube Shorts', 'YouTube', 'Meta (Dark)'];

function pctOrDash(v) { return (v === null || v === undefined) ? '—' : `${v.toFixed(2)}%`; }

function avgLive(vals) {
  const xs = vals.filter(v => v !== null && v !== undefined);
  if (!xs.length) return null;
  return Math.round((xs.reduce((a, b) => a + b, 0) / xs.length) * 100) / 100;
}

function FilterSelect({ label, value, options, onChange }) {
  return (
    <label style={{display:'flex', flexDirection:'column', gap:4, minWidth:0}}>
      <span style={{fontSize:9, fontFamily:'var(--mono)', letterSpacing:'0.12em', fontWeight:600, color:'var(--ink-3)', textTransform:'uppercase'}}>{label}</span>
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        style={{
          fontFamily:'inherit', fontSize:12, fontWeight:500, color:'var(--ink)',
          padding:'7px 10px', borderRadius:8, border:`1px solid ${value === 'All' ? 'var(--line)' : 'var(--flame)'}`,
          background:'var(--surface)', cursor:'pointer', maxWidth:200,
        }}
      >
        <option value="All">All</option>
        {options.map(o => <option key={o} value={o}>{o}</option>)}
      </select>
    </label>
  );
}

function LiveBenchmarks() {
  const live = (window.BENCHMARKS_DATA && window.BENCHMARKS_DATA.live) || null;
  const F = {
    category: useStateB('All'), content_type: useStateB('All'), distribution: useStateB('All'),
    tentpole: useStateB('All'), year: useStateB('All'), program: useStateB('All'),
    client: useStateB('All'), franchise: useStateB('All'), platform: useStateB('All'),
  };
  const [compareTo, setCompareTo] = useStateB((live && live.platformSets && live.platformSets[0] && live.platformSets[0].name) || 'All');
  if (!live || !(live.campaigns || []).length) return null;

  const filters = live.filters || {};
  const plat = F.platform[0];                       // selected platform, or 'All'
  const onePlatform = plat !== 'All';

  // Apply the campaign filters (platform narrows the metric shown, not the set).
  const matches = (c) =>
    (F.category[0] === 'All' || c.category === F.category[0]) &&
    (F.content_type[0] === 'All' || c.contentType === F.content_type[0]) &&
    (F.distribution[0] === 'All' || c.distribution === F.distribution[0]) &&
    (F.tentpole[0] === 'All' || c.tentpole === F.tentpole[0]) &&
    (F.year[0] === 'All' || c.year === F.year[0]) &&
    (F.program[0] === 'All' || c.program === F.program[0]) &&
    (F.client[0] === 'All' || c.client === F.client[0]) &&
    (F.franchise[0] === 'All' || c.franchise === F.franchise[0]);
  const filtered = live.campaigns.filter(matches);
  const included = filtered.filter(c => c.include);

  // Category benchmark table, recomputed over the filtered+included set.
  const catOrder = (live.categoryOrder || []).filter(name => included.some(c => c.category === name));
  const cols = onePlatform ? [plat] : LIVE_PLATFORMS;
  const catRows = catOrder.map(name => {
    const members = included.filter(c => c.category === name);
    const platforms = {};
    cols.forEach(p => { platforms[p] = avgLive(members.map(c => c.platforms[p])); });
    return { name, platforms, all: avgLive(members.map(c => c.all)), n: members.length };
  });

  // Compare-To FOS benchmark set (for blue highlighting).
  const fos = (live.platformSets || []).find(s => s.name === compareTo) || null;
  const fosVal = (p) => fos ? (p === 'All' ? fos.all : fos.platforms[p]) : null;

  const anyActive = Object.values(F).some(([v]) => v !== 'All');
  const clearAll = () => Object.values(F).forEach(([, set]) => set('All'));

  // Campaign list metric helpers.
  const erOf = (c) => onePlatform ? c.platforms[plat] : c.all;
  const catBenchOf = (c) => {
    const r = catRows.find(cr => cr.name === c.category);
    if (!r) return null;
    return onePlatform ? r.platforms[plat] : r.all;
  };
  const listRows = filtered
    .map(c => ({ c, er: erOf(c) }))
    .sort((a, b) => (b.er ?? -1) - (a.er ?? -1));

  const cell = (v, fosBench) => {
    const blue = (v != null && fosBench != null && v >= fosBench);
    return (
      <td className="num" style={{fontWeight: blue ? 700 : 400, color: blue ? 'var(--flame)' : 'var(--ink)'}}>
        {pctOrDash(v)}
      </td>
    );
  };

  return (
    <>
      <PageHead
        overline="FOS Internal · Live benchmarks"
        title="Benchmarks"
        italic="by content type."
        sub={<>Engagement-rate benchmarks across every tracked campaign, sliced by <strong>video vs. static</strong>, <strong>custom vs. franchise-led</strong>, and <strong>paid-only vs. organic + boosted</strong>. Only wrapped campaigns (Include = Yes) count toward an average.</>}
      />

      {/* FILTER BAR */}
      <div className="sec">
        <div className="card" style={{padding:16}}>
          <div style={{display:'flex', flexWrap:'wrap', gap:14, alignItems:'flex-end'}}>
            <FilterSelect label="Category" value={F.category[0]} options={filters.category || []} onChange={F.category[1]}/>
            <FilterSelect label="Content type" value={F.content_type[0]} options={filters.contentType || []} onChange={F.content_type[1]}/>
            <FilterSelect label="Distribution" value={F.distribution[0]} options={filters.distribution || []} onChange={F.distribution[1]}/>
            <FilterSelect label="Tentpole" value={F.tentpole[0]} options={filters.tentpole || []} onChange={F.tentpole[1]}/>
            <FilterSelect label="Year" value={F.year[0]} options={filters.year || []} onChange={F.year[1]}/>
            <FilterSelect label="Program" value={F.program[0]} options={filters.program || []} onChange={F.program[1]}/>
            <FilterSelect label="Client" value={F.client[0]} options={filters.client || []} onChange={F.client[1]}/>
            <FilterSelect label="Franchise / IP" value={F.franchise[0]} options={filters.franchise || []} onChange={F.franchise[1]}/>
            <FilterSelect label="Platform" value={F.platform[0]} options={filters.platform || []} onChange={F.platform[1]}/>
            <label style={{display:'flex', flexDirection:'column', gap:4}}>
              <span style={{fontSize:9, fontFamily:'var(--mono)', letterSpacing:'0.12em', fontWeight:600, color:'var(--ink-3)', textTransform:'uppercase'}}>Compare to</span>
              <select value={compareTo} onChange={e => setCompareTo(e.target.value)}
                style={{fontFamily:'inherit', fontSize:12, fontWeight:500, color:'var(--ink)', padding:'7px 10px', borderRadius:8, border:'1px solid var(--line)', background:'var(--surface)', cursor:'pointer', maxWidth:200}}>
                {(live.platformSets || []).map(s => <option key={s.name} value={s.name}>{s.name}</option>)}
              </select>
            </label>
            {anyActive && (
              <button onClick={clearAll} style={{fontFamily:'inherit', fontSize:11, fontWeight:600, padding:'8px 14px', borderRadius:8, border:'1px solid var(--line)', background:'var(--surface)', color:'var(--ink-2)', cursor:'pointer'}}>Clear filters</button>
            )}
          </div>
          <div style={{marginTop:12, fontSize:11, color:'var(--ink-3)', display:'flex', gap:16, flexWrap:'wrap'}}>
            <span><strong style={{color:'var(--flame)'}}>■</strong> at / above FOS benchmark</span>
            <span><strong style={{color:'var(--positive)'}}>▲</strong> above category · <strong style={{color:'var(--danger)'}}>▼</strong> below category</span>
            <span>{included.length} wrapped · {filtered.length - included.length} in progress</span>
          </div>
        </div>
      </div>

      {/* CATEGORY TABLE (filtered) */}
      <div className="sec">
        <div className="sec-h">
          <div>
            <div className="sec-title">Benchmarks by <em>category</em></div>
            <div className="sec-sub" style={{marginTop:6}}>Average ER of wrapped campaigns in each category. These are the numbers to quote.</div>
          </div>
        </div>
        <div className="card" style={{padding:0, overflow:'auto'}}>
          <table className="tbl" style={{width:'100%', fontSize:13}}>
            <thead>
              <tr>
                <th style={{textAlign:'left'}}>Category</th>
                {cols.map(p => <th key={p} className="num" style={{textAlign:'right'}}>{p}</th>)}
                <th className="num" style={{textAlign:'right', borderLeft:'1px solid var(--line)'}}>All</th>
                <th className="num" style={{textAlign:'right'}}>#</th>
              </tr>
            </thead>
            <tbody>
              {catRows.length === 0 && (
                <tr><td colSpan={cols.length + 3} style={{color:'var(--ink-3)', padding:'16px'}}>No wrapped campaigns match these filters yet.</td></tr>
              )}
              {catRows.map((r, i) => (
                <tr key={i}>
                  <td style={{fontWeight:500, maxWidth:320}}>{r.name} <span style={{color:'var(--ink-3)', fontWeight:400}}>({r.n})</span></td>
                  {cols.map(p => cell(r.platforms[p], fosVal(p)))}
                  <td className="num" style={{fontWeight:600, borderLeft:'1px solid var(--line)'}}>{pctOrDash(r.all)}</td>
                  <td className="num" style={{color:'var(--ink-3)'}}>{r.n}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* CAMPAIGN LIST (filtered) */}
      <div className="sec">
        <div className="sec-h">
          <div>
            <div className="sec-title">Campaigns <em>({filtered.length})</em></div>
            <div className="sec-sub" style={{marginTop:6}}>
              ER shown is {onePlatform ? plat : 'the campaign-level (All Platforms) rate'}. In-progress campaigns are greyed until they wrap.
            </div>
          </div>
        </div>
        <div className="card" style={{padding:0, overflow:'auto'}}>
          <table className="tbl" style={{width:'100%', fontSize:13}}>
            <thead>
              <tr>
                <th style={{textAlign:'left'}}>Campaign</th>
                <th className="num" style={{textAlign:'right'}}>ER</th>
                <th className="num" style={{textAlign:'right'}}>Category bench</th>
                <th style={{textAlign:'left'}}>Content</th>
                <th style={{textAlign:'left'}}>Distribution</th>
                <th style={{textAlign:'left'}}>Franchise / IP</th>
                <th style={{textAlign:'left'}}>Year</th>
                <th className="num" style={{textAlign:'right'}}>Spend</th>
              </tr>
            </thead>
            <tbody>
              {listRows.map(({ c, er }, i) => {
                const cb = catBenchOf(c);
                const color = (er != null && cb != null) ? (er > cb ? 'var(--positive)' : er < cb ? 'var(--danger)' : 'var(--ink)') : 'var(--ink)';
                const arrow = (er != null && cb != null) ? (er > cb ? ' ▲' : er < cb ? ' ▼' : '') : '';
                return (
                  <tr key={i} style={{opacity: c.include ? 1 : 0.5}}>
                    <td style={{fontWeight:500, maxWidth:260, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}}>
                      {c.campaign}{!c.include && <span style={{marginLeft:6, fontSize:9, fontFamily:'var(--mono)', color:'var(--ink-3)'}}>IN PROGRESS</span>}
                    </td>
                    <td className="num" style={{fontWeight:600, color}}>{pctOrDash(er)}{arrow}</td>
                    <td className="num" style={{color:'var(--ink-3)'}}>{pctOrDash(cb)}</td>
                    <td style={{color:'var(--ink-2)'}}>{c.contentType || '—'}</td>
                    <td style={{color:'var(--ink-2)'}}>{c.distribution || '—'}</td>
                    <td style={{color:'var(--ink-2)', maxWidth:160, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}}>{c.franchise || '—'}</td>
                    <td style={{color:'var(--ink-3)'}}>{c.year || '—'}</td>
                    <td className="num" style={{color:'var(--ink-3)'}}>{c.spend != null ? `$${c.spend.toLocaleString()}` : '—'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <PaidBenchmarks/>

      <div className="sec" style={{marginTop:8, marginBottom:8}}>
        <div style={{borderTop:'1px solid var(--line)', paddingTop:20}}>
          <div style={{fontFamily:'var(--mono)', fontSize:10, letterSpacing:'0.16em', fontWeight:600, color:'var(--ink-3)', textTransform:'uppercase'}}>Reference · manual tables below</div>
        </div>
      </div>
    </>
  );
}

// ══════════════════════════════════════════════════════════
// PAID SOCIAL BENCHMARKS (window.BENCHMARKS_DATA.paid)
// BrandX + Dark Posts + In-Feed/Boosted — CPM / CTR / VCR, weighted by impr.
// ══════════════════════════════════════════════════════════
const PAID_MONEY = v => (v == null ? '—' : `$${v.toFixed(2)}`);
const PAID_PCT = v => (v == null ? '—' : `${v.toFixed(2)}%`);
const PAID_INT = v => (v == null ? '—' : v.toLocaleString());
const PAID_SPEND = v => (v == null ? '—' : `$${Math.round(v).toLocaleString()}`);

function PaidTable({ label, rows, cols, overall }) {
  if (!rows || !rows.length) return null;
  return (
    <div style={{marginBottom:20}}>
      {label && <div style={{fontSize:10, fontFamily:'var(--mono)', letterSpacing:'0.12em', fontWeight:600, color:'var(--ink-3)', marginBottom:8, textTransform:'uppercase'}}>{label}</div>}
      <div className="card" style={{padding:0, overflow:'auto'}}>
        <table className="tbl" style={{width:'100%', fontSize:13}}>
          <thead>
            <tr>
              <th style={{textAlign:'left'}}>{cols[0].head}</th>
              {cols.slice(1).map(c => <th key={c.key} className="num" style={{textAlign:'right'}}>{c.head}</th>)}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                <td style={{fontWeight:500}}>{r.name}</td>
                {cols.slice(1).map(c => <td key={c.key} className="num">{c.fmt(r[c.key])}</td>)}
              </tr>
            ))}
            {overall && (
              <tr style={{background:'var(--bg-soft)', borderTop:'2px solid var(--line)'}}>
                <td style={{fontWeight:700}}>Overall</td>
                {cols.slice(1).map(c => <td key={c.key} className="num" style={{fontWeight:700}}>{c.fmt(overall[c.key])}</td>)}
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PaidBenchmarks() {
  const paid = (window.BENCHMARKS_DATA && window.BENCHMARKS_DATA.paid) || null;
  if (!paid || (!paid.brandx && !(paid.distributions || []).length)) return null;

  const distCols = [
    { key: 'name', head: '' },
    { key: 'campaigns', head: 'n', fmt: PAID_INT },
    { key: 'spend', head: 'Spend', fmt: PAID_SPEND },
    { key: 'impressions', head: 'Impressions', fmt: PAID_INT },
    { key: 'cpm', head: 'CPM', fmt: PAID_MONEY },
    { key: 'ctr', head: 'CTR', fmt: PAID_PCT },
    { key: 'vcr', head: 'VCR', fmt: PAID_PCT },
  ];
  const brandxCols = [
    { key: 'name', head: '' },
    { key: 'campaigns', head: 'n', fmt: PAID_INT },
    { key: 'spend', head: 'Spend', fmt: PAID_SPEND },
    { key: 'impressions', head: 'Impressions', fmt: PAID_INT },
    { key: 'cpm', head: 'CPM', fmt: PAID_MONEY },
    { key: 'ctr', head: 'CTR', fmt: PAID_PCT },
    { key: 'er', head: 'ER', fmt: PAID_PCT },
    { key: 'cpc', head: 'CPC', fmt: PAID_MONEY },
  ];

  return (
    <>
      <div className="sec" style={{marginTop:28}}>
        <div className="sec-h" style={{borderBottom:'1px solid var(--line)', paddingBottom:14}}>
          <div>
            <div style={{fontFamily:'var(--mono)', fontSize:10, letterSpacing:'0.16em', fontWeight:600, color:'var(--ink-3)', marginBottom:6, textTransform:'uppercase'}}>Paid social</div>
            <div className="sec-title">Paid <em>benchmarks</em></div>
            <div className="sec-sub" style={{marginTop:6}}>CPM, CTR and VCR for paid distribution, <strong>weighted by impressions</strong> (pooled CPM = total spend ÷ total impressions). Separate from the ER benchmarks above.</div>
          </div>
        </div>
      </div>

      {paid.brandx && (
        <div className="sec">
          <div className="sec-h"><div><div className="sec-title" style={{fontSize:18}}>BrandX</div><div className="sec-sub" style={{marginTop:4}}>Paid-performance campaigns by objective.</div></div></div>
          <PaidTable label="By objective" rows={paid.brandx.byObjective} cols={brandxCols} overall={paid.brandx.overall}/>
          <PaidTable label="By creative" rows={paid.brandx.byCategory} cols={brandxCols}/>
        </div>
      )}

      {(paid.distributions || []).map((d, i) => (
        <div className="sec" key={i}>
          <div className="sec-h"><div><div className="sec-title" style={{fontSize:18}}>{d.name}</div></div></div>
          <PaidTable label="By platform" rows={d.byPlatform} cols={distCols} overall={d.overall}/>
          <PaidTable label="By creative category" rows={d.byCategory} cols={distCols}/>
        </div>
      ))}
    </>
  );
}

// ──────────────────────────────────────────────────────────
// Platform summary — top 3-row table
// ──────────────────────────────────────────────────────────
function PlatformSummaryTable({ rows }) {
  if (!rows.length) return null;
  // Get unique platforms across all rows, preserving canonical order
  const order = ['Instagram', 'Facebook', 'X', 'TikTok', 'LinkedIn', 'YouTube'];
  const platforms = order.filter(p => rows.some(r => r.platforms && r.platforms[p] !== undefined));

  return (
    <div className="card" style={{padding:0, overflow:'hidden'}}>
      <table className="tbl" style={{width:'100%', fontSize:13}}>
        <thead>
          <tr>
            <th style={{textAlign:'left'}}>Row</th>
            {platforms.map(p => <th key={p} className="num" style={{textAlign:'right'}}>{p}</th>)}
            <th className="num" style={{textAlign:'right', borderLeft:'1px solid var(--line)'}}>All (AVG)</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => {
            const isPrimary = row.row.toLowerCase().includes('all content in this doc') || row.row.toLowerCase().includes('all content');
            return (
              <tr key={i} style={{background: i === rows.length - 1 ? 'rgba(222,107,56,0.06)' : undefined}}>
                <td style={{fontWeight: i === rows.length - 1 ? 600 : 500, fontSize: 13}}>
                  {row.row}
                  {i === rows.length - 1 && <span style={{marginLeft:8, fontSize:9, fontFamily:'var(--mono)', letterSpacing:'0.1em', color:'var(--flame)', fontWeight:700}}>FOS</span>}
                </td>
                {platforms.map(p => (
                  <td key={p} className="num">
                    {row.platforms && row.platforms[p] !== undefined ? `${row.platforms[p].toFixed(2)}%` : '—'}
                  </td>
                ))}
                <td className="num" style={{fontWeight:600, borderLeft:'1px solid var(--line)'}}>
                  {(() => {
                    const v = row.allAvg !== undefined ? row.allAvg : row.all_avg;
                    return v !== null && v !== undefined ? `${v.toFixed(2)}%` : '—';
                  })()}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ──────────────────────────────────────────────────────────
// Category section — overall ER + per-campaign table
// ──────────────────────────────────────────────────────────
function CategorySection({ cat, idx }) {
  const overall = cat.overall || {};
  // Get the platform columns that appear in the campaigns / overall
  const PLATFORM_ORDER = ['YouTube', 'Instagram', 'Facebook', 'X', 'TikTok', 'LinkedIn', 'Shorts'];
  const platforms = PLATFORM_ORDER.filter(p =>
    overall[p] !== undefined || (cat.campaigns || []).some(c => c.platforms && c.platforms[p] !== undefined)
  );

  return (
    <div id={`cat-${idx}`} className="sec" style={{marginBottom:36, scrollMarginTop:24}}>
      <div className="sec-h" style={{borderBottom:'1px solid var(--line)', paddingBottom:14}}>
        <div>
          <div style={{fontFamily:'var(--mono)', fontSize:10, letterSpacing:'0.16em', fontWeight:600, color:'var(--ink-3)', marginBottom:6, textTransform:'uppercase'}}>
            Category {String(idx + 1).padStart(2, '0')}
          </div>
          <div className="sec-title">{cat.name}</div>
        </div>
        {overall.All !== null && overall.All !== undefined && (
          <span style={{
            display:'inline-flex', alignItems:'center', gap:6,
            padding:'5px 12px', borderRadius:999,
            background:'var(--bg-soft)', border:'1px solid var(--line)',
            fontSize:11, fontFamily:'var(--mono)', letterSpacing:'0.06em', fontWeight:600, color:'var(--ink-2)'
          }}>
            CATEGORY AVG <strong style={{color:'var(--ink)', marginLeft:4}}>{overall.All.toFixed(2)}%</strong>
          </span>
        )}
      </div>

      {/* Overall ER per platform — category benchmark row */}
      <div style={{marginTop:18, marginBottom:18}}>
        <div style={{fontSize:10, fontFamily:'var(--mono)', letterSpacing:'0.12em', fontWeight:600, color:'var(--ink-3)', marginBottom:10, textTransform:'uppercase'}}>
          Category benchmark · ER by platform
        </div>
        <div className="card" style={{padding:0, overflow:'hidden'}}>
          <div style={{display:'grid', gridTemplateColumns:`repeat(${platforms.length}, minmax(0, 1fr))`, borderTop:'none'}}>
            {platforms.map((p, i) => (
              <div key={p} style={{
                padding:'14px 12px',
                borderRight: i < platforms.length - 1 ? '1px solid var(--line)' : 'none',
                display:'flex', flexDirection:'column', gap:4
              }}>
                <span style={{fontSize:10, color:'var(--ink-3)', textTransform:'uppercase', letterSpacing:'0.1em', fontWeight:600}}>{p}</span>
                <span style={{fontFamily:'var(--serif)', fontSize:22, fontWeight:300, color:'var(--ink)', letterSpacing:'-0.02em'}}>
                  {overall[p] !== null && overall[p] !== undefined ? `${overall[p].toFixed(2)}%` : '—'}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Per-campaign breakdown */}
      {(cat.campaigns || []).length > 0 && (
        <div>
          <div style={{fontSize:10, fontFamily:'var(--mono)', letterSpacing:'0.12em', fontWeight:600, color:'var(--ink-3)', marginBottom:10, textTransform:'uppercase'}}>
            By campaign — green ▲ above category bench · red ▼ below
          </div>
          <div className="card" style={{padding:0, overflow:'auto'}}>
            <table className="tbl" style={{width:'100%', fontSize:13}}>
              <thead>
                <tr>
                  <th style={{textAlign:'left'}}>Campaign</th>
                  {platforms.map(p => <th key={p} className="num" style={{textAlign:'right'}}>{p}</th>)}
                  <th className="num" style={{textAlign:'right', borderLeft:'1px solid var(--line)'}}>All</th>
                  <th className="num" style={{textAlign:'right'}}>Spend</th>
                </tr>
              </thead>
              <tbody>
                {cat.campaigns.map((camp, i) => (
                  <tr key={i}>
                    <td style={{fontWeight:500, maxWidth:280, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}}>{camp.name}</td>
                    {platforms.map(p => {
                      const v = camp.platforms && camp.platforms[p];
                      const bench = overall[p];
                      const color = (v != null && bench != null)
                        ? (v > bench ? 'var(--positive)' : v < bench ? 'var(--danger)' : 'var(--ink-2)')
                        : 'var(--ink-3)';
                      const weight = (v != null && bench != null && (v > bench || v < bench)) ? 600 : 400;
                      return (
                        <td key={p} className="num" style={{color, fontWeight:weight}}>
                          {v != null ? `${v.toFixed(2)}%` : '—'}
                        </td>
                      );
                    })}
                    <td className="num" style={{fontWeight:600, borderLeft:'1px solid var(--line)'}}>
                      {camp.all != null ? `${camp.all.toFixed(2)}%` : '—'}
                    </td>
                    <td className="num" style={{fontVariantNumeric:'tabular-nums', color:'var(--ink-3)'}}>
                      {camp.spend || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function shortCategoryName(name) {
  if (!name) return '';
  // Strip trailing "(parenthetical detail)" for chips
  return name.replace(/\s*\([^)]*\)\s*$/, '').trim();
}

window.BenchmarksPage = BenchmarksPage;
