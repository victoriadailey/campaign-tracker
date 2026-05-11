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

  return (
    <>
      <PageHead
        overline={`FOS Internal · Last updated ${lastUpdated}`}
        title="Benchmarks"
        italic="by category."
        sub={<>Engagement rate benchmarks across content types, drawn from completed FOS campaigns. <strong>Sponsored-only</strong> is the true benchmark for current work; <strong>all-content</strong> shown as a broader reference.</>}
      />

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
