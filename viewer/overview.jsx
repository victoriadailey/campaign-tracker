/* global React, CAMPAIGNS, TOP_POSTS, TOP_POSTS_ORGANIC, HERO_POST, CHANNELS, FORMATS, MONTHLY_DELIVERY, SOURCES, fmt,
   Ic, PlatformPill, PageHead, CampaignCard, MultiLineChart, Donut, BarChart, PLATFORM_COLORS, PaceBar */
const { useState: useStateO } = React;

// ============================================================
// OVERVIEW PAGE
// ============================================================
function OverviewPage({ onOpenCampaign }) {
  const [period, setPeriod] = useStateO('Q2');
  const [filter, setFilter] = useStateO('All campaigns');

  // Aggregate KPIs
  const totals = {
    impressions: CAMPAIGNS.reduce((s, c) => s + c.impressions.delivered, 0),
    budget: CAMPAIGNS.reduce((s, c) => s + c.budget.delivered, 0),
    er: 4.7,
    cpm: 0.71,
    posts: 184
  };

  // Time-based greeting — morning / afternoon / evening
  const hour = new Date().getHours();
  const greetItalic = hour < 12 ? 'morning.' : hour < 17 ? 'afternoon.' : 'evening.';
  const activeCount = CAMPAIGNS.filter(c => c.statusKind !== 'on' || c.status !== 'Goal Exceeded').length;
  const needsAttn = CAMPAIGNS.filter(c => c.statusKind === 'danger' || c.statusKind === 'warn').length;

  return (
    <>
      <PageHead
        overline={`Sponsored campaigns · ${new Date().toLocaleString('en-US', { month: 'long', year: 'numeric' })}`}
        title="Good"
        italic={greetItalic}
        sub={<>{CAMPAIGNS.length} active campaigns · <strong>{needsAttn} need{needsAttn === 1 ? 's' : ''} attention</strong>.</>}
        actions={<>
          <div className="search">
            <Ic.search/><input placeholder="Search campaigns, posts, partners…"/>
          </div>
          <button className="btn btn-acc"><Ic.download/> Export</button>
        </>}
      />

      {/* TOP-OF-DASH CALLOUTS — pulled from per-campaign auto-callouts */}
      {(SIGNALS && SIGNALS.length > 0) && (
      <div className="sec" style={{marginTop: 4}}>
        <div className="sec-h">
          <div>
            <div className="sec-title">Pulse <em>check</em></div>
            <div className="sec-sub" style={{marginTop:6}}>The most important things to know across your active campaigns — auto-flagged from current performance.</div>
          </div>
        </div>
        <div style={{display:'grid', gridTemplateColumns:`repeat(${Math.min(SIGNALS.length, 3)}, minmax(0, 1fr))`, gap:14}}>
          {SIGNALS.map((co, i) => {
            const kind = co.kind || (co.tag === 'WIN' ? 'pos' : co.tag === 'WATCH' ? 'warn' : 'info');
            const tone = kind === 'pos' ? { bar:'var(--pear)', tag:'#2f7a3f' } :
              kind === 'warn' ? { bar:'var(--orange)', tag:'#b8392b' } :
              { bar:'var(--sky)', tag:'var(--ink)' };
            const tag = co.tag || (kind === 'pos' ? 'WIN' : kind === 'warn' ? 'WATCH' : 'OPPORTUNITY');
            const headline = co.headline || co.title;
            return (
              <div key={i} style={{
                background:'var(--surface)', border:'1px solid var(--line)', borderRadius:'var(--r-lg)',
                padding: 22, position:'relative', overflow:'hidden',
                display:'flex', flexDirection:'column', gap:10, minWidth: 0
              }}>
                <div style={{position:'absolute', left:0, top:0, bottom:0, width:4, background: tone.bar}}/>
                <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
                  <span style={{
                    fontFamily:'var(--mono)', fontSize:10, letterSpacing:'0.14em',
                    fontWeight:600, color: tone.tag,
                    padding:'3px 8px', background: tone.bar+'33', borderRadius: 4
                  }}>{tag}</span>
                  {co.meta && <span style={{fontSize:10, color:'var(--ink-3)', fontFamily:'var(--mono)', letterSpacing:'0.06em'}}>{co.meta}</span>}
                </div>
                <div style={{fontFamily:'var(--serif)', fontSize:22, fontWeight:300, lineHeight:1.2, letterSpacing:'-0.01em', color:'var(--ink)'}}>{headline}</div>
                <div style={{fontSize:13, lineHeight:1.5, color:'var(--ink-2)'}}>{co.body}</div>
                {co.campaignId && (
                  <a href="#" onClick={(ev) => { ev.preventDefault(); onOpenCampaign(co.campaignId); }}
                     style={{marginTop:'auto', fontSize:12, color:'var(--ink)', textDecoration:'none', display:'inline-flex', alignItems:'center', gap:6, fontWeight:500, paddingTop:6}}>
                    Open {co.campaignPartner || 'campaign'} <Ic.arrow/>
                  </a>
                )}
              </div>
            );
          })}
        </div>
      </div>
      )}

      {/* CAMPAIGN GRID */}
      <div className="sec">
        <div className="sec-h">
          <div>
            <div className="sec-title">Active <em>campaigns</em></div>
            <div className="sec-sub" style={{marginTop:6}}>Pacing across impressions and budget for every live flight.</div>
          </div>
        </div>
        <div style={{display:'grid', gridTemplateColumns:'repeat(3, 1fr)', gap:16}}>
          {CAMPAIGNS.map(c => (
            <CampaignCard key={c.id} c={c} onClick={() => onOpenCampaign(c.id)}/>
          ))}
        </div>
      </div>



      {/* TOP POSTS — TWO TABLES */}
      <div className="sec">
        <div className="sec-h">
          <div>
            <div className="sec-title">Top <em>performing</em> posts</div>
            <div className="sec-sub" style={{marginTop:6}}>Highest engagement rate and highest organic reach across every active campaign.</div>
          </div>
        </div>

        <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:16}}>
          {/* TABLE 1 — TOP BY ER */}
          <div className="card" style={{padding:0, overflow:'hidden'}}>
            <div style={{padding:'20px 24px 16px', borderBottom:'1px solid var(--line)'}}>
              <div className="card-title-serif" style={{fontSize:22}}>By <em>engagement rate</em></div>
              <div className="card-sub" style={{marginTop:4}}>Min 1K views · all campaigns</div>
            </div>
            <div style={{
              display:'grid',
              gridTemplateColumns:'24px 1fr 90px 70px',
              gap:10, padding:'12px 24px',
              fontSize:10, fontFamily:'var(--mono)', color:'var(--ink-3)',
              letterSpacing:'0.1em', fontWeight:600, textTransform:'uppercase',
              borderBottom:'1px solid var(--line)', background:'var(--bg-soft)'
            }}>
              <div>#</div>
              <div>Post</div>
              <div style={{textAlign:'right'}}>Reach</div>
              <div style={{textAlign:'right'}}>ER</div>
            </div>
            {TOP_POSTS.slice(0, 6).map(p => (
              <a key={p.id} href="#" style={{
                display:'grid',
                gridTemplateColumns:'24px 1fr 90px 70px',
                gap:10, padding:'14px 24px', alignItems:'center',
                borderBottom:'1px solid var(--line)',
                textDecoration:'none', color:'inherit', fontSize:13
              }}>
                <div style={{fontFamily:'var(--mono)', fontSize:11, color:'var(--ink-3)', fontWeight:600}}>{String(p.rank).padStart(2,'0')}</div>
                <div style={{display:'flex', flexDirection:'column', gap:4, minWidth:0}}>
                  <div style={{display:'flex', alignItems:'center', gap:8}}>
                    <strong style={{fontSize:11, color:'var(--ink)'}}>{p.partner}</strong>
                    <PlatformPill name={p.platform}/>
                  </div>
                  <div style={{fontSize:12, color:'var(--ink-2)', lineHeight:1.35, overflow:'hidden', textOverflow:'ellipsis', display:'-webkit-box', WebkitLineClamp:2, WebkitBoxOrient:'vertical'}}>{p.quote}</div>
                </div>
                <div style={{textAlign:'right', fontVariantNumeric:'tabular-nums', fontWeight:500}}>{fmt.num(p.reach)}</div>
                <div style={{textAlign:'right', fontFamily:'var(--serif)', fontSize:18, fontWeight:300, color:'var(--flame)'}}>{p.er.toFixed(2)}<span style={{fontSize:11, color:'var(--ink-3)'}}>%</span></div>
              </a>
            ))}
          </div>

          {/* TABLE 2 — TOP BY ORGANIC REACH */}
          <div className="card" style={{padding:0, overflow:'hidden'}}>
            <div style={{padding:'20px 24px 16px', borderBottom:'1px solid var(--line)'}}>
              <div className="card-title-serif" style={{fontSize:22}}>By <em>organic reach</em></div>
              <div className="card-sub" style={{marginTop:4}}>Highest organic views with no or minimal paid support</div>
            </div>
            <div style={{
              display:'grid',
              gridTemplateColumns:'24px 1fr 100px 70px',
              gap:10, padding:'12px 24px',
              fontSize:10, fontFamily:'var(--mono)', color:'var(--ink-3)',
              letterSpacing:'0.1em', fontWeight:600, textTransform:'uppercase',
              borderBottom:'1px solid var(--line)', background:'var(--bg-soft)'
            }}>
              <div>#</div>
              <div>Post</div>
              <div style={{textAlign:'right'}}>Organic</div>
              <div style={{textAlign:'right'}}>% Org</div>
            </div>
            {TOP_POSTS_ORGANIC.slice(0, 6).map(p => (
              <a key={p.id} href="#" style={{
                display:'grid',
                gridTemplateColumns:'24px 1fr 100px 70px',
                gap:10, padding:'14px 24px', alignItems:'center',
                borderBottom:'1px solid var(--line)',
                textDecoration:'none', color:'inherit', fontSize:13
              }}>
                <div style={{fontFamily:'var(--mono)', fontSize:11, color:'var(--ink-3)', fontWeight:600}}>{String(p.rank).padStart(2,'0')}</div>
                <div style={{display:'flex', flexDirection:'column', gap:4, minWidth:0}}>
                  <div style={{display:'flex', alignItems:'center', gap:8}}>
                    <strong style={{fontSize:11, color:'var(--ink)'}}>{p.partner}</strong>
                    <PlatformPill name={p.platform}/>
                  </div>
                  <div style={{fontSize:12, color:'var(--ink-2)', lineHeight:1.35, overflow:'hidden', textOverflow:'ellipsis', display:'-webkit-box', WebkitLineClamp:2, WebkitBoxOrient:'vertical'}}>{p.quote}</div>
                </div>
                <div style={{textAlign:'right', fontFamily:'var(--serif)', fontSize:18, fontWeight:300}}>{fmt.num(p.organicReach)}</div>
                <div style={{textAlign:'right', fontVariantNumeric:'tabular-nums', fontWeight:500, color:'#2f7a3f'}}>{p.organicPct.toFixed(0)}%</div>
              </a>
            ))}
          </div>
        </div>
      </div>

      {/* INSIGHTS */}
      <div className="sec">
        <div className="sec-h">
          <div>
            <div className="sec-title">What we're <em>seeing</em></div>
            <div className="sec-sub" style={{marginTop:6}}>Auto-generated callouts and channel benchmarks based on the last 30 days.</div>
          </div>
        </div>

        {/* CPM BY CHANNEL — bench strip */}
        <div className="card" style={{padding:24, marginBottom:14}}>
          <div className="card-h" style={{marginBottom: 18}}>
            <div>
              <div className="card-title-serif">Average CPM by channel</div>
              <div className="card-sub">Blended across all active campaigns. Lower is more efficient.</div>
            </div>
            <div style={{fontSize:11, fontFamily:'var(--mono)', color:'var(--ink-3)', letterSpacing:'0.06em'}}>
              PORTFOLIO BLEND · $0.71
            </div>
          </div>
          <div style={{display:'grid', gridTemplateColumns:'repeat(7, 1fr)', gap:0, borderTop:'1px solid var(--line)'}}>
            {[
              { plat:'YT In-feed',   cpm:'$0.49', vol:'34% of imp.', color:'#E00922' },
              { plat:'YT In-stream', cpm:'$9.20', vol:'22% of imp.', color:'#B0061B' },
              { plat:'X',            cpm:'$0.71', vol:'5% of imp.',  color:'#1d1d1f' },
              { plat:'TikTok',       cpm:'$1.84', vol:'12% of imp.', color:'#000000' },
              { plat:'LinkedIn',     cpm:'$2.14', vol:'9% of imp.',  color:'#0A66C2' },
              { plat:'Facebook',     cpm:'$3.92', vol:'—',           color:'#1877F2' },
              { plat:'Instagram',    cpm:'$8.46', vol:'18% of imp.', color:'#E4405F' },
            ].map((r, i, arr) => (
              <div key={r.plat} style={{
                padding:'18px 14px',
                borderRight: i < arr.length - 1 ? '1px solid var(--line)' : 'none',
                display:'flex', flexDirection:'column', gap:6
              }}>
                <div style={{display:'flex', alignItems:'center', gap:8}}>
                  <span style={{width:8, height:8, borderRadius:'50%', background:r.color}}/>
                  <span style={{fontSize:11, color:'var(--ink-2)', fontWeight:500}}>{r.plat}</span>
                </div>
                <div style={{fontFamily:'var(--serif)', fontSize:26, fontWeight:300, color:'var(--ink)', letterSpacing:'-0.02em', lineHeight:1}}>{r.cpm}</div>
                <div style={{fontSize:10, fontFamily:'var(--mono)', letterSpacing:'0.04em', color:'var(--ink-3)'}}>{r.vol}</div>
              </div>
            ))}
          </div>
        </div>

        {/* ER BENCHMARKS BY CHANNEL — FOS 2025 sponsored + all-content reference */}
        <div className="card" style={{padding:24, marginBottom:14}}>
          <div className="card-h" style={{marginBottom: 18}}>
            <div>
              <div className="card-title-serif">FOS ER benchmarks by channel</div>
              <div className="card-sub">Sponsored is the true benchmark for these campaigns. All-content shown for reference.</div>
            </div>
            <div style={{fontSize:11, fontFamily:'var(--mono)', color:'var(--ink-3)', letterSpacing:'0.06em'}}>
              SPONSORED AVG · 2.47%
            </div>
          </div>
          <div style={{display:'grid', gridTemplateColumns:'repeat(6, minmax(0, 1fr))', gap:0, borderTop:'1px solid var(--line)'}}>
            {[
              { plat:'YouTube',   sponsored:'3.30%', all:'1.00%', color:'#E00922' },
              { plat:'Instagram', sponsored:'3.31%', all:'3.60%', color:'#E4405F' },
              { plat:'Facebook',  sponsored:'1.53%', all:'4.00%', color:'#1877F2' },
              { plat:'TikTok',    sponsored:'2.03%', all:'4.90%', color:'#000000' },
              { plat:'LinkedIn',  sponsored:'3.76%', all:'5.20%', color:'#0A66C2' },
              { plat:'X',         sponsored:'0.92%', all:'2.30%', color:'#1d1d1f' },
            ].map((r, i, arr) => (
              <div key={r.plat} style={{
                padding:'18px 14px',
                borderRight: i < arr.length - 1 ? '1px solid var(--line)' : 'none',
                display:'flex', flexDirection:'column', gap:6
              }}>
                <div style={{display:'flex', alignItems:'center', gap:8}}>
                  <span style={{width:8, height:8, borderRadius:'50%', background:r.color}}/>
                  <span style={{fontSize:11, color:'var(--ink-2)', fontWeight:500}}>{r.plat}</span>
                </div>
                <div style={{fontFamily:'var(--serif)', fontSize:26, fontWeight:300, color:'var(--ink)', letterSpacing:'-0.02em', lineHeight:1}}>{r.sponsored}</div>
                <div style={{fontSize:10, fontFamily:'var(--mono)', letterSpacing:'0.04em', color:'var(--ink-3)'}}>
                  ALL · {r.all}
                </div>
              </div>
            ))}
          </div>
          <div style={{marginTop:12, fontSize:11, color:'var(--ink-3)', fontStyle:'italic', display:'flex', justifyContent:'space-between'}}>
            <span>Sponsored benchmark = sponsored-only. All-content benchmark = organic + sponsored (avg 3.50%).</span>
            <span>Last updated: 3/5 1pm EST</span>
          </div>
        </div>

        <div style={{display:'grid', gridTemplateColumns:'repeat(2, 1fr)', gap:14}}>
          {[
            { tag: 'WIN', kind: 'pos', headline: 'YouTube in-feed is the efficiency champion at $0.52 avg CPM.', body: 'E*TRADE Ep 3 hit $0.46 — the lowest across all campaigns. In-feed is the #1 lever for catching pacing.', meta: 'Portfolio · YouTube' },
            { tag: 'WIN', kind: 'pos', headline: 'LinkedIn organic ER averaging 4.2% across the portfolio.', body: '100% organic distribution. Increasing posting frequency is the highest-ROI zero-cost tactic available right now.', meta: '6 campaigns · Organic' },
            { tag: 'OPPORTUNITY', kind: 'info', headline: 'Pre-roll completion rates are up to 78% on E*TRADE.', body: 'Despite higher $14+ CPMs, brand recall studies are showing 22% lift. Reserve for awareness-led campaigns only.', meta: 'YouTube · Pre-roll' },
            { tag: 'WATCH', kind: 'warn', headline: 'Instagram CPM up 11% QoQ at $8.46 — the highest in the mix.', body: 'Algorithm changes hitting Reels reach. Lean on TikTok or YT Shorts for short-form pacing until Q3 reset.', meta: 'Portfolio · Instagram' },
          ].map((co, i) => {
            const tone = co.kind === 'pos' ? { bar: 'var(--pear)', tag: '#2f7a3f' } :
              co.kind === 'warn' ? { bar: 'var(--orange)', tag: '#b8392b' } :
              { bar: 'var(--sky)', tag: 'var(--ink)' };
            return (
              <div key={i} style={{
                background:'var(--surface)', border:'1px solid var(--line)', borderRadius:'var(--r-lg)',
                padding: 22, position:'relative', overflow:'hidden',
                display:'flex', flexDirection:'column', gap:10
              }}>
                <div style={{position:'absolute', left:0, top:0, bottom:0, width:4, background: tone.bar}}/>
                <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
                  <span style={{
                    fontFamily:'var(--mono)', fontSize:10, letterSpacing:'0.14em',
                    fontWeight:600, color: tone.tag,
                    padding:'3px 8px', background: tone.bar+'33', borderRadius: 4
                  }}>{co.tag}</span>
                  <span style={{fontSize:10, color:'var(--ink-3)', fontFamily:'var(--mono)', letterSpacing:'0.06em'}}>{co.meta}</span>
                </div>
                <div style={{fontFamily:'var(--serif)', fontSize:22, fontWeight:300, lineHeight:1.2, letterSpacing:'-0.01em', color:'var(--ink)'}}>{co.headline}</div>
                <div style={{fontSize:13, lineHeight:1.5, color:'var(--ink-2)'}}>{co.body}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* SOURCES STRIP — moved to bottom, one line */}
      <div className="src-strip" style={{marginTop:32, marginBottom:8, flexWrap:'nowrap', overflowX:'auto', fontSize:11}}>
        <span className="src-lbl" style={{whiteSpace:'nowrap'}}>Data sources</span>
        {SOURCES.map(s => (
          <span className="src-item" key={s.name} style={{whiteSpace:'nowrap'}}>
            <span className={"dot " + (s.stale ? 'stale' : '')}/>
            <span className="nm">{s.name}</span>
            <span className="dt">· {s.date}</span>
          </span>
        ))}
      </div>
    </>
  );
}

window.OverviewPage = OverviewPage;
