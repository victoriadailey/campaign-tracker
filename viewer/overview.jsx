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

  return (
    <>
      <PageHead
        overline="Branded content · April 2026"
        title="Good morning,"
        italic="Jordan."
        sub={<>You're tracking <strong>6 active campaigns</strong> across {CAMPAIGNS.reduce((s,c)=>s+c.episodes,0)} episodes. <strong>1 needs attention</strong> — E*TRADE is 39% behind impression pacing with 56 days left.</>}
        actions={<>
          <div className="search">
            <Ic.search/><input placeholder="Search campaigns, posts, partners…"/>
          </div>
          <button className="btn btn-icon" title="Notifications"><Ic.bell/></button>
          <button className="btn btn-acc"><Ic.download/> Export</button>
        </>}
      />

      {/* SOURCES STRIP */}
      <div className="src-strip">
        <span className="src-lbl">Data sources</span>
        {SOURCES.map(s => (
          <span className="src-item" key={s.name}>
            <span className={"dot " + (s.stale ? 'stale' : '')}/>
            <span className="nm">{s.name}</span>
            <span className="dt">· {s.date}</span>
          </span>
        ))}
        <span style={{marginLeft: 'auto', display:'flex', alignItems:'center', gap:6, fontSize:11, color:'var(--ink-3)'}}>
          <Ic.dot/> All systems synced
        </span>
      </div>

      {/* TOP-OF-DASH CALLOUTS — what to celebrate, fix, watch */}
      <div className="sec" style={{marginTop: 4}}>
        <div className="sec-h">
          <div>
            <div className="sec-title">Pulse <em>check</em></div>
            <div className="sec-sub" style={{marginTop:6}}>Three things to know before you dive in — a win to share, a problem to fix, a campaign to watch.</div>
          </div>
        </div>
        <div style={{display:'grid', gridTemplateColumns:'repeat(3, 1fr)', gap:14}}>
          {[
            { tag:'WIN', kind:'pos', headline:'McLaren ER leads the portfolio at 6.2% on TikTok.', body:'F1-adjacent youth content is over-indexing. Worth amplifying in your weekly partner update — strong proof point for renewal.', meta:'McLaren · TikTok', cta:'Open campaign' },
            { tag:'OPPORTUNITY', kind:'info', headline:'X paid is the lowest social CPM at $0.71 blended.', body:'~12× more efficient than Instagram. Strong candidate for E*TRADE and ADP catch-up spend over the next two weeks.', meta:'Portfolio · X', cta:'See benchmarks' },
            { tag:'WATCH', kind:'warn', headline:'E*TRADE is 39% behind impression pacing with 56 days left.', body:'31.2M impressions still needed with $27.2K budget remaining. Mark Cuban teaser is building organic — fast-track the YT launch.', meta:'E*TRADE · Behind', cta:'Open campaign' }
          ].map((co, i) => {
            const tone = co.kind === 'pos' ? { bar:'var(--pear)', tag:'#2f7a3f' } :
              co.kind === 'warn' ? { bar:'var(--orange)', tag:'#b8392b' } :
              { bar:'var(--sky)', tag:'var(--ink)' };
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
                <a href="#" style={{marginTop:'auto', fontSize:12, color:'var(--ink)', textDecoration:'none', display:'inline-flex', alignItems:'center', gap:6, fontWeight:500, paddingTop:6}}>{co.cta} <Ic.arrow/></a>
              </div>
            );
          })}
        </div>
      </div>

      {/* CAMPAIGN GRID */}
      <div className="sec">
        <div className="sec-h">
          <div>
            <div className="sec-title">Active <em>campaigns</em></div>
            <div className="sec-sub" style={{marginTop:6}}>Pacing across impressions and budget for every live flight.</div>
          </div>
          <div className="seg">
            <button className="active">All</button>
            <button>On track</button>
            <button>Watch</button>
            <button>Behind</button>
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
          <div style={{display:'grid', gridTemplateColumns:'repeat(6, 1fr)', gap:0, borderTop:'1px solid var(--line)'}}>
            {[
              { plat:'YouTube', cpm:'$0.52', delta:'-12%', good:true, vol:'56% of imp.', color:'#E00922' },
              { plat:'X', cpm:'$0.71', delta:'-8%', good:true, vol:'5% of imp.', color:'#1d1d1f' },
              { plat:'TikTok', cpm:'$1.84', delta:'-3%', good:true, vol:'12% of imp.', color:'#000000' },
              { plat:'LinkedIn', cpm:'$2.14', delta:'+2%', good:false, vol:'9% of imp.', color:'#0A66C2' },
              { plat:'Facebook', cpm:'$3.92', delta:'+6%', good:false, vol:'—', color:'#1877F2' },
              { plat:'Instagram', cpm:'$8.46', delta:'+11%', good:false, vol:'18% of imp.', color:'#E4405F' },
            ].map((r, i) => (
              <div key={r.plat} style={{
                padding:'18px 16px',
                borderRight: i < 5 ? '1px solid var(--line)' : 'none',
                display:'flex', flexDirection:'column', gap:6
              }}>
                <div style={{display:'flex', alignItems:'center', gap:8}}>
                  <span style={{width:8, height:8, borderRadius:'50%', background:r.color}}/>
                  <span style={{fontSize:11, color:'var(--ink-2)', fontWeight:500}}>{r.plat}</span>
                </div>
                <div style={{fontFamily:'var(--serif)', fontSize:28, fontWeight:300, color:'var(--ink)', letterSpacing:'-0.02em', lineHeight:1}}>{r.cpm}</div>
                <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', fontSize:10, fontFamily:'var(--mono)', letterSpacing:'0.04em'}}>
                  <span style={{color: r.good ? '#2f7a3f' : '#b8392b', fontWeight:600}}>{r.delta} vs Q1</span>
                  <span style={{color:'var(--ink-3)'}}>{r.vol}</span>
                </div>
              </div>
            ))}
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
    </>
  );
}

window.OverviewPage = OverviewPage;
