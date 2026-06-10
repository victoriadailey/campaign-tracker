/* global React, CAMPAIGNS, fmt, Ic, PlatformPill, PageHead */
const { useState: useStateUB } = React;

// ============================================================
// US BANK x NFL DRAFT — bespoke layout
// 3 social components, no episodes/cutdowns
// ============================================================

const UB_COMPONENTS = window.UB_COMPONENTS || [];

const PLATFORM_CPMS = window.UB_PLATFORM_CPMS || [];

// ── Distribution badge ─────────────────────────────────────
function DistBadge({ kind }) {
  const styles = {
    'organic+paid': { bg:'rgba(80,135,230,0.16)', fg:'#3450a8', label:'ORGANIC + PAID' },
    'organic':      { bg:'rgba(143,199,102,0.18)', fg:'#2f7a3f', label:'ORGANIC' },
    'paid':         { bg:'rgba(255,153,71,0.22)',  fg:'#a04a14', label:'PAID' },
  };
  const s = styles[kind] || styles.organic;
  return (
    <span style={{
      background: s.bg, color: s.fg, padding:'2px 8px', borderRadius:999,
      fontSize:9, fontFamily:'var(--mono)', fontWeight:600, letterSpacing:'0.06em', whiteSpace:'nowrap'
    }}>{s.label}</span>
  );
}

// ── Component summary card (top-of-page) ─────────────────────
function ComponentCard({ comp, onClick, active }) {
  const impPct = (comp.impressions.delivered / comp.impressions.goal) * 100;
  const budPct = (comp.budget.delivered / comp.budget.goal) * 100 || 0;
  return (
    <div onClick={onClick} style={{
      background: comp.color, color: comp.fg,
      borderRadius: 'var(--r-lg)', padding: 22, cursor:'pointer',
      border: active ? '2px solid var(--ink)' : '2px solid transparent',
      display:'flex', flexDirection:'column', gap:14,
      transition:'transform .15s', transform: active ? 'translateY(-2px)' : 'none',
      position:'relative', overflow:'hidden'
    }}>
      <div style={{display:'flex', justifyContent:'space-between', alignItems:'flex-start'}}>
        <div style={{
          fontFamily:'var(--mono)', fontSize:10, letterSpacing:'0.16em',
          fontWeight:600, opacity:0.7
        }}>COMPONENT {comp.n}</div>
        <span style={{
          background: comp.statusKind==='on' ? 'rgba(255,255,255,0.85)' : 'rgba(31,26,21,0.12)',
          color: comp.statusKind==='on' ? '#2f7a3f' : comp.fg,
          padding:'3px 10px', borderRadius: 999, fontSize: 10, fontFamily:'var(--mono)',
          fontWeight:600, letterSpacing:'0.06em'
        }}>{comp.status}</span>
      </div>
      <div>
        <div style={{fontFamily:'var(--serif)', fontSize:30, fontWeight:300, lineHeight:1.05, letterSpacing:'-0.02em'}}>
          {comp.title.replace(comp.italic, '').trim()} <em style={{fontStyle:'italic'}}>{comp.italic}</em>
        </div>
        <div style={{fontSize:12, opacity:0.75, marginTop:6}}>{comp.sub}</div>
      </div>
      <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:10, paddingTop:14, borderTop:`1px solid ${comp.fg === 'var(--paper)' ? 'rgba(250,247,239,0.2)' : 'rgba(31,26,21,0.18)'}`}}>
        <div>
          <div style={{fontSize:10, letterSpacing:'0.1em', textTransform:'uppercase', fontWeight:600, opacity:0.7, marginBottom:4}}>Impressions</div>
          <div style={{fontFamily:'var(--serif)', fontSize:26, fontWeight:300, lineHeight:1}}>{fmt.num(comp.impressions.delivered)}</div>
          <div style={{fontSize:11, opacity:0.7, marginTop:4}}>{impPct.toFixed(1)}% of {fmt.num(comp.impressions.goal)}</div>
        </div>
        <div>
          <div style={{fontSize:10, letterSpacing:'0.1em', textTransform:'uppercase', fontWeight:600, opacity:0.7, marginBottom:4}}>Spend</div>
          <div style={{fontFamily:'var(--serif)', fontSize:26, fontWeight:300, lineHeight:1}}>{fmt.money(comp.budget.delivered)}</div>
          <div style={{fontSize:11, opacity:0.7, marginTop:4}}>{budPct.toFixed(1)}% of {fmt.money(comp.budget.goal)}</div>
        </div>
      </div>
    </div>
  );
}

// ── Pacing pill ─────────────────────────────────────────────
function PaceBarUB({ pct, color, track }) {
  return (
    <div style={{height:8, background: track || 'rgba(31,26,21,0.12)', borderRadius:999, overflow:'hidden', position:'relative'}}>
      <div style={{height:'100%', width: Math.min(100,pct)+'%', background: color, borderRadius:999}}/>
      {pct > 100 && (
        <div style={{position:'absolute', top:0, right:0, height:'100%', width:'4px', background:'var(--liquorice)'}}/>
      )}
    </div>
  );
}

// ── Master pacing — stacked bar ─────────────────────────────
function MasterPacing() {
  const total = UB_COMPONENTS.reduce((s,c) => s + c.impressions.delivered, 0);
  const goal = UB_COMPONENTS.reduce((s,c) => s + c.impressions.goal, 0);
  const spent = UB_COMPONENTS.reduce((s,c) => s + c.budget.delivered, 0);
  const budget = UB_COMPONENTS.reduce((s,c) => s + c.budget.goal, 0);
  const overall = (total / goal) * 100;
  const overallBud = (spent / budget) * 100;

  return (
    <div className="card" style={{marginBottom:24, padding:28}}>
      <div className="card-h" style={{marginBottom:18}}>
        <div>
          <div className="card-title-serif">Total <em>campaign pacing</em></div>
          <div className="card-sub">Combined progress across all 3 social components toward 14M impression goal.</div>
        </div>
        <span className="pill" style={{
          background:'rgba(143,199,102,0.18)', color:'#2f7a3f', border:'none', fontWeight:600
        }}>
          <span className="dot" style={{background:'#2f7a3f'}}/>Goal Exceeded
        </span>
      </div>

      {/* Stacked bar */}
      <div style={{position:'relative', marginBottom:10}}>
        <div style={{height:36, background:'var(--bg-soft)', borderRadius:8, overflow:'hidden', display:'flex'}}>
          {UB_COMPONENTS.map(c => {
            const pct = (c.impressions.delivered / goal) * 100;
            return (
              <div key={c.id} style={{width: pct+'%', background: c.color, height:'100%', position:'relative'}}>
                {pct > 8 && (
                  <div style={{
                    position:'absolute', inset:0, display:'flex', alignItems:'center', padding:'0 12px',
                    color: c.fg, fontSize: 11, fontWeight:600, fontFamily:'var(--mono)', letterSpacing:'0.05em'
                  }}>{fmt.num(c.impressions.delivered)}</div>
                )}
              </div>
            );
          })}
        </div>
        {/* Goal marker */}
        <div style={{position:'absolute', top:-6, bottom:-6, left:'100%', width:2, background:'var(--ink)', opacity:0.7}}>
          <span style={{position:'absolute', top:-18, right:0, fontSize:10, fontFamily:'var(--mono)', fontWeight:600, color:'var(--ink)', whiteSpace:'nowrap'}}>14M GOAL</span>
        </div>
      </div>

      <div style={{display:'flex', justifyContent:'space-between', fontSize:12, color:'var(--ink-2)', marginBottom:18}}>
        <span><strong style={{color:'var(--ink)'}}>{fmt.num(total)}</strong> of {fmt.num(goal)} impressions
          (<strong style={{color:'#2f7a3f'}}>{overall.toFixed(1)}% — Goal Exceeded</strong>)</span>
        <span style={{color:'var(--ink-3)'}}>{fmt.money(spent)} of {fmt.money(budget)} spent · {overallBud.toFixed(1)}%</span>
      </div>

      {/* Legend */}
      <div style={{display:'flex', gap:20, flexWrap:'wrap', fontSize:12, paddingTop:16, borderTop:'1px solid var(--line)'}}>
        {UB_COMPONENTS.map(c => (
          <div key={c.id} style={{display:'flex', alignItems:'center', gap:8}}>
            <div style={{width:12, height:12, borderRadius:3, background:c.color}}/>
            <span><strong style={{color:'var(--ink)'}}>Component {c.n}:</strong> {c.title} — {fmt.num(c.impressions.delivered)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Platform performance table ──────────────────────────────
function PlatformTable({ comp }) {
  const totals = comp.platforms.reduce((acc, p) => ({
    posts: acc.posts + p.posts,
    organic: acc.organic + (p.organic || 0),
    paid: acc.paid + (p.paid || 0),
    total: acc.total + p.total,
    eng: acc.eng + p.eng,
    spend: acc.spend + p.spend,
    est: acc.est + (p.est || 0)
  }), { posts:0, organic:0, paid:0, total:0, eng:0, spend:0, est:0 });
  const totalEr = (totals.eng / totals.total) * 100;
  const totalPct = totals.est > 0 ? (totals.spend / totals.est) * 100 : null;

  return (
    <div style={{overflowX:'auto', border:'1px solid var(--line)', borderRadius:'var(--r-lg)', background:'var(--surface)'}}>
      <table style={{width:'100%', borderCollapse:'collapse', fontSize:12}}>
        <thead>
          <tr style={{background:'var(--bg-soft)', borderBottom:'1px solid var(--line)'}}>
            {['Platform','Posts','Organic','Paid','Total','Eng.','ER','Spend','Est.','% Spent'].map((h, i) => (
              <th key={h} style={{
                padding:'12px 14px', textAlign: i === 0 ? 'left' : 'right',
                fontSize:10, letterSpacing:'0.1em', textTransform:'uppercase',
                fontWeight:600, color:'var(--ink-3)'
              }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {comp.platforms.map((p, idx) => (
            <tr key={p.name} style={{borderBottom:'1px solid var(--line)'}}>
              <td style={{padding:'12px 14px', fontWeight:500}}>{p.name}</td>
              <td style={{padding:'12px 14px', textAlign:'right', fontVariantNumeric:'tabular-nums'}}>{p.posts}</td>
              <td style={{padding:'12px 14px', textAlign:'right', fontVariantNumeric:'tabular-nums', color:'var(--ink-2)'}}>{fmt.num(p.organic)}</td>
              <td style={{padding:'12px 14px', textAlign:'right', fontVariantNumeric:'tabular-nums', color:'var(--ink-2)'}}>{p.paid === null ? '—' : fmt.num(p.paid)}</td>
              <td style={{padding:'12px 14px', textAlign:'right', fontVariantNumeric:'tabular-nums', fontWeight:600}}>{fmt.num(p.total)}</td>
              <td style={{padding:'12px 14px', textAlign:'right', fontVariantNumeric:'tabular-nums'}}>{fmt.num(p.eng)}</td>
              <td style={{padding:'12px 14px', textAlign:'right', fontVariantNumeric:'tabular-nums', color: p.er >= 5 ? '#2f7a3f' : 'var(--ink-2)', fontWeight: p.er >= 5 ? 600 : 400}}>{p.er.toFixed(p.er < 1 ? 2 : 1)}%</td>
              <td style={{padding:'12px 14px', textAlign:'right', fontVariantNumeric:'tabular-nums'}}>{p.spend === 0 ? '—' : '$'+fmt.num(Math.round(p.spend))}</td>
              <td style={{padding:'12px 14px', textAlign:'right', fontVariantNumeric:'tabular-nums', color:'var(--ink-3)'}}>{!p.est ? '—' : '$'+fmt.num(p.est)}</td>
              <td style={{padding:'12px 14px', textAlign:'right', fontVariantNumeric:'tabular-nums', color: p.pct === null ? 'var(--ink-3)' : p.pct > 110 ? '#b8392b' : p.pct < 80 ? '#a06b14' : 'var(--ink-2)', fontWeight: p.pct !== null && (p.pct > 110 || p.pct < 80) ? 600 : 400}}>{p.pct === null ? '—' : p.pct.toFixed(1)+'%'}</td>
            </tr>
          ))}
          <tr style={{background:'var(--liquorice)', color:'var(--cream)'}}>
            <td style={{padding:'14px', fontWeight:600, fontFamily:'var(--mono)', fontSize:11, letterSpacing:'0.08em', textTransform:'uppercase'}}>Total</td>
            <td style={{padding:'14px', textAlign:'right', fontVariantNumeric:'tabular-nums', fontWeight:600}}>{totals.posts}</td>
            <td style={{padding:'14px', textAlign:'right', fontVariantNumeric:'tabular-nums'}}>{fmt.num(totals.organic)}</td>
            <td style={{padding:'14px', textAlign:'right', fontVariantNumeric:'tabular-nums'}}>{fmt.num(totals.paid)}</td>
            <td style={{padding:'14px', textAlign:'right', fontVariantNumeric:'tabular-nums', fontWeight:600}}>{fmt.num(totals.total)}</td>
            <td style={{padding:'14px', textAlign:'right', fontVariantNumeric:'tabular-nums'}}>{fmt.num(totals.eng)}</td>
            <td style={{padding:'14px', textAlign:'right', fontVariantNumeric:'tabular-nums', fontWeight:600}}>{totalEr.toFixed(1)}%</td>
            <td style={{padding:'14px', textAlign:'right', fontVariantNumeric:'tabular-nums', fontWeight:600}}>${fmt.num(Math.round(totals.spend))}</td>
            <td style={{padding:'14px', textAlign:'right', fontVariantNumeric:'tabular-nums'}}>{totals.est === 0 ? '—' : '$'+fmt.num(totals.est)}</td>
            <td style={{padding:'14px', textAlign:'right', fontVariantNumeric:'tabular-nums', fontWeight:600, color: totalPct && totalPct > 110 ? '#ffcccb' : 'var(--cream)'}}>{totalPct === null ? '—' : totalPct.toFixed(1)+'%'}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

// ── Story card with expandable platform rows ──────────────
function StoryCard({ story, accentColor }) {
  const [open, setOpen] = useStateUB(false);
  return (
    <div style={{
      background:'var(--surface)', border:'1px solid var(--line)',
      borderRadius:'var(--r-lg)', overflow:'hidden'
    }}>
      <div onClick={() => setOpen(!open)} style={{
        padding:'18px 22px', cursor:'pointer', display:'grid',
        gridTemplateColumns:'1fr 110px 110px 110px 30px', gap:16, alignItems:'center'
      }}>
        <div>
          <div style={{display:'flex', alignItems:'center', gap:10, marginBottom:4}}>
            <div style={{fontFamily:'var(--serif)', fontSize:24, fontWeight:300, letterSpacing:'-0.01em'}}>{story.name}</div>
            <span style={{
              fontFamily:'var(--mono)', fontSize:9, letterSpacing:'0.12em', fontWeight:600,
              padding:'2px 8px', borderRadius:999,
              background: story.kind === 'Collab' ? 'rgba(80,135,230,0.16)' : 'rgba(31,26,21,0.08)',
              color: story.kind === 'Collab' ? '#3450a8' : 'var(--ink-2)'
            }}>{story.kind.toUpperCase()}</span>
            <span style={{fontSize:10, color:'var(--ink-3)', fontFamily:'var(--mono)'}}>· Pub {story.published}</span>
          </div>
          <div style={{fontSize:12, color:'var(--ink-3)'}}>{story.sub}</div>
        </div>
        <div style={{textAlign:'right'}}>
          <div style={{fontFamily:'var(--serif)', fontSize:22, fontWeight:300, color: accentColor}}>{fmt.num(story.reach)}</div>
          <div style={{fontSize:9, color:'var(--ink-3)', textTransform:'uppercase', letterSpacing:'0.1em', fontWeight:600}}>Reach</div>
        </div>
        <div style={{textAlign:'right'}}>
          <div style={{fontFamily:'var(--serif)', fontSize:22, fontWeight:300}}>{fmt.num(story.eng)}</div>
          <div style={{fontSize:9, color:'var(--ink-3)', textTransform:'uppercase', letterSpacing:'0.1em', fontWeight:600}}>Eng.</div>
        </div>
        <div style={{textAlign:'right'}}>
          <div style={{fontFamily:'var(--serif)', fontSize:22, fontWeight:300}}>${fmt.num(Math.round(story.spend))}</div>
          <div style={{fontSize:9, color:'var(--ink-3)', textTransform:'uppercase', letterSpacing:'0.1em', fontWeight:600}}>Spend</div>
        </div>
        <div style={{color:'var(--ink-3)', textAlign:'right', transform: open ? 'rotate(180deg)' : 'none', transition:'transform .2s'}}>▾</div>
      </div>
      {open && (
        <div style={{borderTop:'1px solid var(--line)', background:'var(--bg-soft)'}}>
          <table style={{width:'100%', borderCollapse:'collapse', fontSize:12}}>
            <thead>
              <tr>
                {['Platform','Type','Impressions','Engagements','ER','Spend'].map((h, i) => (
                  <th key={h} style={{
                    padding:'10px 14px', textAlign: i < 2 ? 'left' : 'right',
                    fontSize:10, letterSpacing:'0.1em', textTransform:'uppercase',
                    fontWeight:600, color:'var(--ink-3)'
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {story.rows.map(r => (
                <tr key={r.plat} style={{borderTop:'1px solid var(--line)'}}>
                  <td style={{padding:'10px 14px', fontWeight:500}}>{r.plat}</td>
                  <td style={{padding:'10px 14px'}}><DistBadge kind={r.dist}/></td>
                  <td style={{padding:'10px 14px', textAlign:'right', fontVariantNumeric:'tabular-nums'}}>{fmt.num(r.impr)}</td>
                  <td style={{padding:'10px 14px', textAlign:'right', fontVariantNumeric:'tabular-nums'}}>{fmt.num(r.eng)}</td>
                  <td style={{padding:'10px 14px', textAlign:'right', fontVariantNumeric:'tabular-nums', color: r.er >= 5 ? '#2f7a3f' : 'var(--ink-2)', fontWeight: r.er >= 5 ? 600 : 400}}>{r.er.toFixed(r.er < 1 ? 2 : 1)}%</td>
                  <td style={{padding:'10px 14px', textAlign:'right', fontVariantNumeric:'tabular-nums'}}>{r.spend === 0 ? '—' : '$'+fmt.num(Math.round(r.spend))}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div style={{padding:'14px 22px', background:'rgba(255,153,71,0.10)', borderTop:'1px solid var(--line)', fontSize:12, color:'var(--ink-2)', lineHeight:1.5}}>
            <strong style={{color:'var(--ink)'}}>Highlight: </strong>{story.highlight}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Video card (Red Carpet) ─────────────────────────────────
function VideoCard({ video, accentColor }) {
  return (
    <div style={{
      background:'var(--surface)', border:'1px solid var(--line)',
      borderRadius:'var(--r-lg)', overflow:'hidden'
    }}>
      <div style={{padding:'18px 22px', borderBottom:'1px solid var(--line)', display:'flex', justifyContent:'space-between', alignItems:'center'}}>
        <div>
          <div style={{display:'flex', alignItems:'center', gap:10, marginBottom:4}}>
            <div style={{fontFamily:'var(--serif)', fontSize:24, fontWeight:300}}>{video.name}</div>
            <span style={{
              fontFamily:'var(--mono)', fontSize:9, letterSpacing:'0.12em', fontWeight:600,
              padding:'2px 8px', borderRadius:999,
              background: video.dist.includes('Paid Only') ? 'rgba(255,153,71,0.22)' : 'rgba(80,135,230,0.16)',
              color: video.dist.includes('Paid Only') ? '#a04a14' : '#3450a8'
            }}>{video.dist.toUpperCase()}</span>
          </div>
          <div style={{fontSize:13, color:'var(--ink-2)', fontStyle:'italic'}}>{video.quote}</div>
        </div>
        <div style={{display:'grid', gridTemplateColumns:'repeat(4, auto)', gap:24}}>
          <div style={{textAlign:'right'}}>
            <div style={{fontFamily:'var(--serif)', fontSize:22, fontWeight:300, color: accentColor}}>{fmt.num(video.subtotal.impr)}</div>
            <div style={{fontSize:9, color:'var(--ink-3)', textTransform:'uppercase', letterSpacing:'0.1em', fontWeight:600}}>Impr.</div>
          </div>
          <div style={{textAlign:'right'}}>
            <div style={{fontFamily:'var(--serif)', fontSize:22, fontWeight:300}}>{fmt.num(video.subtotal.eng)}</div>
            <div style={{fontSize:9, color:'var(--ink-3)', textTransform:'uppercase', letterSpacing:'0.1em', fontWeight:600}}>Eng.</div>
          </div>
          <div style={{textAlign:'right'}}>
            <div style={{fontFamily:'var(--serif)', fontSize:22, fontWeight:300}}>{video.subtotal.er.toFixed(1)}<span style={{fontSize:13, color:'var(--ink-3)'}}>%</span></div>
            <div style={{fontSize:9, color:'var(--ink-3)', textTransform:'uppercase', letterSpacing:'0.1em', fontWeight:600}}>ER</div>
          </div>
          <div style={{textAlign:'right'}}>
            <div style={{fontFamily:'var(--serif)', fontSize:22, fontWeight:300}}>${fmt.num(Math.round(video.subtotal.spend))}</div>
            <div style={{fontSize:9, color:'var(--ink-3)', textTransform:'uppercase', letterSpacing:'0.1em', fontWeight:600}}>Spend</div>
          </div>
        </div>
      </div>
      <table style={{width:'100%', borderCollapse:'collapse', fontSize:12}}>
        <thead>
          <tr style={{background:'var(--bg-soft)'}}>
            {['Platform','Type','Impressions','Engagements','ER','Spend'].map((h, i) => (
              <th key={h} style={{
                padding:'10px 14px', textAlign: i < 2 ? 'left' : 'right',
                fontSize:10, letterSpacing:'0.1em', textTransform:'uppercase',
                fontWeight:600, color:'var(--ink-3)'
              }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {video.rows.map(r => (
            <tr key={r.plat} style={{borderTop:'1px solid var(--line)'}}>
              <td style={{padding:'10px 14px', fontWeight:500}}>{r.plat}</td>
              <td style={{padding:'10px 14px'}}><DistBadge kind={r.dist}/></td>
              <td style={{padding:'10px 14px', textAlign:'right', fontVariantNumeric:'tabular-nums'}}>{fmt.num(r.impr)}</td>
              <td style={{padding:'10px 14px', textAlign:'right', fontVariantNumeric:'tabular-nums'}}>{fmt.num(r.eng)}</td>
              <td style={{padding:'10px 14px', textAlign:'right', fontVariantNumeric:'tabular-nums', color: r.er >= 5 ? '#2f7a3f' : 'var(--ink-2)', fontWeight: r.er >= 5 ? 600 : 400}}>{r.er.toFixed(r.er < 1 ? 2 : 1)}%</td>
              <td style={{padding:'10px 14px', textAlign:'right', fontVariantNumeric:'tabular-nums'}}>{r.spend === 0 ? '—' : '$'+fmt.num(Math.round(r.spend))}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Callout block (Win / Watch / Opportunity) ──────────────
function Callout({ co }) {
  const tone = co.kind === 'pos' ? { bar: 'var(--pear)', tag: '#2f7a3f', bg:'rgba(143,199,102,0.12)' } :
    co.kind === 'warn' ? { bar: 'var(--orange)', tag: '#b8392b', bg:'rgba(255,153,71,0.14)' } :
    { bar: 'var(--sky)', tag: 'var(--ink)', bg:'rgba(80,135,230,0.08)' };
  return (
    <div style={{
      background:'var(--surface)', border:'1px solid var(--line)', borderRadius:'var(--r-lg)',
      padding: 22, position:'relative', overflow:'hidden',
      display:'flex', flexDirection:'column', gap:10
    }}>
      <div style={{position:'absolute', left:0, top:0, bottom:0, width:4, background: tone.bar}}/>
      <span style={{
        fontFamily:'var(--mono)', fontSize:10, letterSpacing:'0.14em',
        fontWeight:600, color: tone.tag, alignSelf:'flex-start',
        padding:'3px 8px', background: tone.bg, borderRadius: 4
      }}>{co.tag}</span>
      <div style={{fontFamily:'var(--serif)', fontSize:20, fontWeight:300, lineHeight:1.25, letterSpacing:'-0.01em', color:'var(--ink)'}}>{co.headline}</div>
      <div style={{fontSize:13, lineHeight:1.55, color:'var(--ink-2)'}}>{co.body}</div>
    </div>
  );
}

// ── Component section (full detail per component) ─────────
function ComponentSection({ comp }) {
  const impPct = (comp.impressions.delivered / comp.impressions.goal) * 100;
  const budPct = comp.budget.goal > 0 ? (comp.budget.delivered / comp.budget.goal) * 100 : 0;
  const accentColor = comp.color;

  return (
    <div id={`comp-${comp.id}`} className="sec" style={{scrollMarginTop:24}}>
      <div className="sec-h">
        <div>
          <div style={{fontFamily:'var(--mono)', fontSize:11, letterSpacing:'0.16em', fontWeight:600, color:'var(--ink-3)', marginBottom:8, textTransform:'uppercase'}}>
            Social Component {comp.n}
          </div>
          <div className="sec-title">{comp.title.replace(comp.italic, '').trim()} <em>{comp.italic}</em></div>
          <div className="sec-sub" style={{marginTop:6}}>{comp.sub} · Goal: {fmt.num(comp.impressions.goal)} impr · Budget: {fmt.money(comp.budget.goal)}</div>
        </div>
        <span className="pill" style={{
          background: comp.statusKind === 'on' ? 'rgba(143,199,102,0.18)' : 'rgba(255,153,71,0.18)',
          color: comp.statusKind === 'on' ? '#2f7a3f' : '#b8392b',
          border:'none', fontWeight:600
        }}>
          <span className="dot" style={{background: comp.statusKind === 'on' ? '#2f7a3f' : '#b8392b'}}/>
          {comp.status}{comp.statusKind === 'watch' ? ` — ${impPct.toFixed(1)}%` : ''}
        </span>
      </div>

      {/* Pacing strip — 2 bars */}
      <div className="card" style={{marginBottom:18, padding:22}}>
        <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:24}}>
          <div>
            <div style={{display:'flex', justifyContent:'space-between', marginBottom:8}}>
              <span style={{fontSize:11, fontFamily:'var(--mono)', letterSpacing:'0.1em', textTransform:'uppercase', fontWeight:600, color:'var(--ink-3)'}}>Impressions</span>
              <span style={{fontSize:12, color:'var(--ink-2)'}}>
                <strong style={{color:'var(--ink)'}}>{fmt.num(comp.impressions.delivered)}</strong> of {fmt.num(comp.impressions.goal)}
                <span style={{marginLeft:8, color: impPct >= 100 ? '#2f7a3f' : '#a06b14', fontWeight:600}}>{impPct.toFixed(1)}%</span>
              </span>
            </div>
            <PaceBarUB pct={impPct} color={accentColor}/>
          </div>
          <div>
            <div style={{display:'flex', justifyContent:'space-between', marginBottom:8}}>
              <span style={{fontSize:11, fontFamily:'var(--mono)', letterSpacing:'0.1em', textTransform:'uppercase', fontWeight:600, color:'var(--ink-3)'}}>Spend</span>
              <span style={{fontSize:12, color:'var(--ink-2)'}}>
                <strong style={{color:'var(--ink)'}}>{fmt.money(comp.budget.delivered)}</strong> of {fmt.money(comp.budget.goal)}
                <span style={{marginLeft:8, color: budPct > 110 ? '#b8392b' : budPct < 50 ? '#a06b14' : 'var(--ink-2)', fontWeight:600}}>{budPct.toFixed(1)}%</span>
              </span>
            </div>
            <PaceBarUB pct={budPct} color={budPct > 110 ? 'var(--flame)' : 'var(--liquorice)'}/>
          </div>
        </div>
        {comp.budgetNote && (
          <div style={{
            marginTop:14, padding:'10px 14px',
            background:'rgba(255,206,0,0.14)', border:'1px solid rgba(255,206,0,0.3)',
            borderRadius:8, fontSize:12, color:'var(--ink-2)', lineHeight:1.5
          }}>
            <strong style={{color:'var(--ink)'}}>Budget note: </strong>{comp.budgetNote}
          </div>
        )}
      </div>

      {/* KPIs */}
      <div className="kpi-row" style={{gridTemplateColumns:'repeat(5, 1fr)'}}>
        <div className="kpi"><div className="kpi-lbl">Posts Live</div><div className="kpi-val">{comp.posts}</div><div className="kpi-foot"><span className="muted">{comp.sub.split('·')[0].trim().toLowerCase()}</span></div></div>
        <div className="kpi"><div className="kpi-lbl">Impressions</div><div className="kpi-val">{fmt.num(comp.impressions.delivered)}</div><div className="kpi-foot"><span className="muted">{impPct.toFixed(1)}% of goal</span></div></div>
        <div className="kpi"><div className="kpi-lbl">Engagements</div><div className="kpi-val">{fmt.num(comp.engagements)}</div><div className="kpi-foot"><span className="muted">cross-platform</span></div></div>
        <div className="kpi"><div className="kpi-lbl">Eng. Rate</div><div className="kpi-val">{comp.er}<span className="unit">%</span></div><div className="kpi-foot"><span className="muted">blended</span></div></div>
        <div className="kpi"><div className="kpi-lbl">Spend</div><div className="kpi-val">{fmt.money(comp.budget.delivered)}</div><div className="kpi-foot"><span className="muted">of {fmt.money(comp.budget.goal)} ({budPct.toFixed(0)}%)</span></div></div>
      </div>

      {/* Platform performance table */}
      {comp.platforms && (
        <div style={{marginTop:24, marginBottom:18}}>
          <div style={{fontFamily:'var(--serif)', fontSize:22, fontWeight:300, marginBottom:6}}>Platform <em>performance</em></div>
          <div style={{fontSize:12, color:'var(--ink-3)', marginBottom:14, maxWidth:720, lineHeight:1.5}}>
            Engagements = MS social engagements + Google Ads YT Shorts engagements combined. Paid impressions sourced from Meta Ads Manager (IG/FB), X Ads Manager, and Google Ads (YT Shorts). Organic from Measure Studio.
          </div>
          <PlatformTable comp={comp}/>
        </div>
      )}

      {/* Stories (Come Up) or Videos (Red Carpet) */}
      {comp.stories && (
        <div style={{marginTop:24}}>
          <div style={{fontFamily:'var(--serif)', fontSize:22, fontWeight:300, marginBottom:6}}>Story <em>performance</em></div>
          <div style={{fontSize:12, color:'var(--ink-3)', marginBottom:14}}>4 stories × 5 platforms = 20 posts. Click any row to see the platform breakdown.</div>
          <div style={{display:'flex', flexDirection:'column', gap:10}}>
            {comp.stories.map(s => <StoryCard key={s.name} story={s} accentColor={accentColor}/>)}
          </div>
        </div>
      )}

      {comp.videos && (
        <div style={{marginTop:24}}>
          <div style={{fontFamily:'var(--serif)', fontSize:22, fontWeight:300, marginBottom:6}}>Per-video <em>detail</em></div>
          <div style={{fontSize:12, color:'var(--ink-3)', marginBottom:14, maxWidth:720, lineHeight:1.5}}>2 videos across 5 platforms. Video 1 is organic boosted with paid amplification. Video 2 is paid-only (dark) — no organic delivery anywhere.</div>
          <div style={{display:'flex', flexDirection:'column', gap:14}}>
            {comp.videos.map(v => <VideoCard key={v.name} video={v} accentColor={accentColor}/>)}
          </div>
        </div>
      )}

      {/* Callouts */}
      <div style={{marginTop:24}}>
        <div style={{fontFamily:'var(--serif)', fontSize:22, fontWeight:300, marginBottom:14}}>What we're <em>seeing</em></div>
        <div style={{display:'grid', gridTemplateColumns: comp.callouts.length === 1 ? '1fr' : `repeat(${comp.callouts.length}, 1fr)`, gap:14}}>
          {comp.callouts.map((co, i) => <Callout key={i} co={co}/>)}
        </div>
      </div>
    </div>
  );
}

// ── Main page ───────────────────────────────────────────────
function UsBankPage({ campaignId, onBack }) {
  const c = CAMPAIGNS.find(x => x.id === 'usbank');
  const [activeComp, setActiveComp] = useStateUB(null);

  const scrollTo = (id) => {
    const el = document.getElementById(`comp-${id}`);
    if (el) el.scrollIntoView({behavior:'smooth', block:'start'});
    setActiveComp(id);
  };

  return (
    <>
      <PageHead
        overline={onBack ? (
          <>
            <span style={{cursor:'pointer'}} onClick={onBack}><Ic.back/> Overview</span>
            <span style={{margin:'0 8px', opacity:0.4}}>/</span>
            <span>{c.partner}</span>
          </>
        ) : (
          // Standalone US Bank document — no Overview to navigate back to.
          // Show the partner alone, no breadcrumb.
          <span style={{
            fontSize:11, letterSpacing:'0.16em', textTransform:'uppercase',
            fontWeight:600, color:'var(--ink-3)'
          }}>{c.partner}</span>
        )}
        title="NFL"
        italic="Draft"
        sub={<>Partner: <strong>US Bank</strong> · Flight: {c.flight} · 3 social components · <strong>38 posts live</strong> across IG, FB, X, LinkedIn, YouTube Shorts</>}
        actions={<>
          <button className="btn btn-acc"><Ic.download/> Export</button>
        </>}
      />

      {/* Hero — 3-component overview */}
      <div style={{marginBottom:24}}>
        <div style={{display:'flex', justifyContent:'space-between', alignItems:'flex-end', marginBottom:14}}>
          <div>
            <div style={{fontFamily:'var(--mono)', fontSize:11, letterSpacing:'0.16em', fontWeight:600, color:'var(--ink-3)', marginBottom:6, textTransform:'uppercase'}}>
              Three Social Components
            </div>
            <div style={{fontFamily:'var(--serif)', fontSize:28, fontWeight:300, letterSpacing:'-0.01em'}}>
              Each tracked <em>independently.</em>
            </div>
          </div>
          <div style={{fontSize:12, color:'var(--ink-3)', maxWidth:380, textAlign:'right', lineHeight:1.5}}>
            Click a component to jump to its full breakdown. Each has its own goal, budget, and post inventory.
          </div>
        </div>
        <div style={{display:'grid', gridTemplateColumns:'repeat(3, 1fr)', gap:14}}>
          {UB_COMPONENTS.map(comp => (
            <ComponentCard key={comp.id} comp={comp} active={activeComp === comp.id} onClick={() => scrollTo(comp.id)}/>
          ))}
        </div>
      </div>

      {/* Master pacing — stacked */}
      <MasterPacing/>

      {/* Component sections */}
      {UB_COMPONENTS.map((comp, idx) => (
        <React.Fragment key={comp.id}>
          {idx > 0 && <div style={{height:1, background:'var(--line)', margin:'32px 0'}}/>}
          <ComponentSection comp={comp}/>
        </React.Fragment>
      ))}

      {/* Data sources footer */}
      <div className="sec" style={{marginTop:32}}>
        <div className="card" style={{padding:22, background:'var(--bg-soft)'}}>
          <div style={{fontFamily:'var(--mono)', fontSize:11, letterSpacing:'0.16em', fontWeight:600, color:'var(--ink-3)', marginBottom:8, textTransform:'uppercase'}}>Data Sources</div>
          <div style={{fontSize:12, color:'var(--ink-2)', lineHeight:1.6}}>
            Social metrics from Measure Studio export (April 27, 2026) — 20 Come Up posts, 10 Native Social Coverage posts, 6 Red Carpet posts (+ 2 dark posts via Ads Managers).
            Paid data from Meta Ads Manager (IG/FB), X Ads Manager, Google Ads (YT Shorts). Organic from Measure Studio.
            Total spend: <strong style={{color:'var(--ink)'}}>$30,986 of $31,375 (98.8%)</strong>.
            Total delivery: <strong style={{color:'var(--ink)'}}>14.51M of 14.0M (103.6% — Goal Exceeded)</strong>.
          </div>
        </div>
      </div>
    </>
  );
}

window.UsBankPage = UsBankPage;
