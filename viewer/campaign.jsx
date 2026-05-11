/* global React, CAMPAIGNS, TOP_POSTS, CHANNELS, FORMATS, fmt,
   Ic, PlatformPill, PageHead, MultiLineChart, Donut, BarChart, PaceBar */
const { useState: useStateC } = React;

function CampaignPage({ campaignId, onBack }) {
  const c = CAMPAIGNS.find(x => x.id === campaignId) || CAMPAIGNS[0];
  const impPct = (c.impressions.delivered / c.impressions.goal) * 100;
  const budPct = (c.budget.delivered / c.budget.goal) * 100;
  const elapsedPct = c.elapsedPct;

  // Pacing health: are delivery + budget tracking with time elapsed?
  const impVsTime = impPct - elapsedPct;
  const budVsTime = budPct - elapsedPct;
  const paceHealth = (label, diff) => {
    if (diff > 5) return { label, status: 'ahead', text: `+${diff.toFixed(0)}% vs time` };
    if (diff < -5) return { label, status: 'behind', text: `${diff.toFixed(0)}% vs time` };
    return { label, status: 'on', text: 'in sync' };
  };
  const trackTime = paceHealth('Time', 0);
  const trackImp = paceHealth('Delivery', impVsTime);
  const trackBud = paceHealth('Budget', budVsTime);

  // Build campaign-specific channel data
  const scale = c.impressions.delivered / 13_780_000;
  const channels = CHANNELS.map(ch => ({
    ...ch,
    impressions: Math.round(ch.impressions * scale),
    eng: Math.round(ch.eng * scale)
  }));

  const totalPosts = c.episodes * 6 + 4;

  // Episode breakdown by channel
  // distKind: 'organic' | 'organic+boosted' | 'paid'
  const EPISODES = (window.EPISODES_BY_CAMPAIGN || {})[campaignId] || [];

  const cardTone = c.color === 'ft-ink' ? { bg: 'var(--liquorice)', fg: 'var(--cream)', dim: 'rgba(245,241,232,0.7)', track: 'rgba(245,241,232,0.2)', fill: 'var(--cream)' } :
    c.color === 'ft-1' ? { bg: 'var(--orange)', fg: 'var(--liquorice)', dim: 'rgba(31,26,21,0.7)', track: 'rgba(31,26,21,0.18)', fill: 'var(--liquorice)' } :
    c.color === 'ft-2' ? { bg: 'var(--blossom)', fg: 'var(--liquorice)', dim: 'rgba(31,26,21,0.7)', track: 'rgba(31,26,21,0.18)', fill: 'var(--liquorice)' } :
    c.color === 'ft-3' ? { bg: 'var(--sky)', fg: 'var(--liquorice)', dim: 'rgba(31,26,21,0.7)', track: 'rgba(31,26,21,0.18)', fill: 'var(--liquorice)' } :
    c.color === 'ft-4' ? { bg: 'var(--pear)', fg: 'var(--liquorice)', dim: 'rgba(31,26,21,0.7)', track: 'rgba(31,26,21,0.18)', fill: 'var(--liquorice)' } :
    c.color === 'ft-5' ? { bg: 'var(--lilac)', fg: 'var(--liquorice)', dim: 'rgba(31,26,21,0.7)', track: 'rgba(31,26,21,0.18)', fill: 'var(--liquorice)' } :
    c.color === 'ft-6' ? { bg: 'var(--flame)', fg: 'var(--paper)', dim: 'rgba(250,247,239,0.75)', track: 'rgba(250,247,239,0.2)', fill: 'var(--paper)' } :
    { bg: 'var(--liquorice)', fg: 'var(--cream)', dim: 'rgba(245,241,232,0.7)', track: 'rgba(245,241,232,0.2)', fill: 'var(--cream)' };

  return (
    <>
      <PageHead
        overline={<>
          <span style={{cursor:'pointer'}} onClick={onBack}><Ic.back/> Overview</span>
          <span style={{margin:'0 8px', opacity:0.4}}>/</span>
          <span>{c.partner}</span>
        </>}
        title={c.series.replace(c.seriesItalic, '').trim()}
        italic={c.seriesItalic}
        sub={<>Partner: <strong>{c.partner}</strong> · Flight: {c.flight} · {c.episodes} episodes · Lead format: <strong>{c.leadFormat}</strong></>}
        actions={<>
          <button className="btn btn-acc"><Ic.download/> Export</button>
        </>}
      />

      {/* HERO PACING BANNER */}
      <div style={{
        background: cardTone.bg, color: cardTone.fg,
        borderRadius: 'var(--r-lg)', padding: 28,
        marginBottom: 24, display: 'grid',
        gridTemplateColumns: '1.2fr 1fr 1fr', gap: 24,
        alignItems: 'center', position: 'relative', overflow: 'hidden'
      }}>
        <div>
          <div style={{fontSize:11, letterSpacing:'0.12em', textTransform:'uppercase', fontWeight:600, opacity:0.7, marginBottom:8}}>Status</div>
          <div style={{fontFamily:'var(--serif)', fontSize:44, lineHeight:1, fontWeight:300, letterSpacing:'-0.02em', marginBottom:14}}>
            {c.status === 'On Track' ? <>Pacing <em>well.</em></> :
             c.status === 'Behind Pace' ? <>Behind <em>pace.</em></> :
             c.status === 'Watch' ? <>Watch <em>closely.</em></> :
             <>Just <em>kicked off.</em></>}
          </div>
          <div style={{fontSize:14, lineHeight:1.5, maxWidth:380, opacity:0.85}}>{c.blurb}</div>
          <div style={{marginTop:16, fontSize:12, opacity:0.75}}>{c.flight}</div>
        </div>
        <div>
          <div style={{fontSize:11, letterSpacing:'0.12em', textTransform:'uppercase', fontWeight:600, opacity:0.7, marginBottom:10}}>Impression delivery</div>
          <div style={{display:'flex', alignItems:'baseline', gap:8, marginBottom:8}}>
            <span style={{fontFamily:'var(--serif)', fontSize:48, lineHeight:1, letterSpacing:'-0.02em', fontWeight:300}}>{fmt.num(c.impressions.delivered)}</span>
            <span style={{fontSize:14, opacity:0.7}}>of {fmt.num(c.impressions.goal)}</span>
          </div>
          <div style={{height:6, background: cardTone.track, borderRadius:999, overflow:'hidden', marginBottom:6}}>
            <div style={{height:'100%', width: Math.min(100,impPct)+'%', background: cardTone.fill, borderRadius:999}}/>
          </div>
          <div style={{fontSize:12, opacity:0.7}}>{impPct.toFixed(1)}% delivered · {elapsedPct.toFixed(0)}% time elapsed</div>
        </div>
        <div>
          <div style={{fontSize:11, letterSpacing:'0.12em', textTransform:'uppercase', fontWeight:600, opacity:0.7, marginBottom:10}}>Budget</div>
          <div style={{display:'flex', alignItems:'baseline', gap:8, marginBottom:8}}>
            <span style={{fontFamily:'var(--serif)', fontSize:48, lineHeight:1, letterSpacing:'-0.02em', fontWeight:300}}>{fmt.money(c.budget.delivered)}</span>
            <span style={{fontSize:14, opacity:0.7}}>of {fmt.money(c.budget.goal)}</span>
          </div>
          <div style={{height:6, background: cardTone.track, borderRadius:999, overflow:'hidden', marginBottom:6}}>
            <div style={{height:'100%', width: Math.min(100,budPct)+'%', background: cardTone.fill, borderRadius:999}}/>
          </div>
          <div style={{fontSize:12, opacity:0.7}}>{budPct.toFixed(1)}% spent · {fmt.money(c.budget.goal - c.budget.delivered)} remaining</div>
        </div>
      </div>

      {/* FLIGHT TRACKER — three-bar pacing alignment */}
      <div className="card" style={{marginBottom: 24}}>
        <div className="card-h">
          <div>
            <div className="card-title-serif">Flight <em>tracker</em></div>
            <div className="card-sub">Are time, delivery, and spend moving together?</div>
          </div>
          <span className="pill" style={{
            background: Math.abs(impVsTime) < 5 && Math.abs(budVsTime) < 5 ? 'rgba(143,199,102,0.18)' : 'rgba(255,153,71,0.18)',
            color: Math.abs(impVsTime) < 5 && Math.abs(budVsTime) < 5 ? '#2f7a3f' : '#b8392b',
            border:'none', fontWeight:600
          }}>
            <span className="dot" style={{background: Math.abs(impVsTime) < 5 && Math.abs(budVsTime) < 5 ? '#2f7a3f' : '#b8392b'}}/>
            {Math.abs(impVsTime) < 5 && Math.abs(budVsTime) < 5 ? 'Aligned' : impVsTime < -5 ? 'Delivery lagging' : budVsTime > 5 ? 'Spend ahead' : 'Watch'}
          </span>
        </div>
        <div style={{display:'flex', flexDirection:'column', gap:18, marginTop:8}}>
          {[
            { lbl: 'Time elapsed', pct: elapsedPct, sub: `${c.daysLeft} days remaining`, color: 'var(--ink-3)' },
            { lbl: 'Impressions delivered', pct: impPct, sub: `${impPct.toFixed(0)}% of ${fmt.num(c.impressions.goal)} goal`, color: cardTone.bg === 'var(--liquorice)' ? 'var(--ink)' : cardTone.bg },
            { lbl: 'Budget spent', pct: budPct, sub: `${budPct.toFixed(0)}% of ${fmt.money(c.budget.goal)}`, color: 'var(--pear)' },
          ].map(row => (
            <div key={row.lbl} style={{display:'grid', gridTemplateColumns:'180px 1fr 220px', gap:16, alignItems:'center'}}>
              <div>
                <div style={{fontSize:13, fontWeight:500, color:'var(--ink)'}}>{row.lbl}</div>
                <div style={{fontSize:11, color:'var(--ink-3)', marginTop:2}}>{row.sub}</div>
              </div>
              <div style={{position:'relative', height:10, background:'var(--bg-soft)', borderRadius:999, overflow:'hidden'}}>
                <div style={{position:'absolute', inset:0, width: row.pct + '%', background: row.color, borderRadius:999, transition:'width 0.4s'}}/>
                {/* time elapsed marker */}
                {row.lbl !== 'Time elapsed' && (
                  <div style={{position:'absolute', top:-3, bottom:-3, left: `calc(${elapsedPct}% - 1px)`, width:2, background:'var(--ink)', opacity:0.5}}/>
                )}
              </div>
              <div style={{textAlign:'right', fontFamily:'var(--serif)', fontSize:24, fontWeight:300, color:'var(--ink)'}}>
                {row.pct.toFixed(0)}<span style={{fontSize:13, color:'var(--ink-3)'}}>%</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* KPI ROW */}
      <div className="kpi-row">
        <div className="kpi">
          <div className="kpi-lbl">Total Reach / Impressions</div>
          <div className="kpi-val">{fmt.num(c.impressions.delivered)}</div>
          <div className="kpi-foot"><span className="kpi-delta up"><Ic.arrowUp/> 14%</span> last 30d</div>
        </div>
        <div className="kpi">
          <div className="kpi-lbl">Engagements</div>
          <div className="kpi-val">{fmt.num(Math.round(c.impressions.delivered * c.er / 100))}</div>
          <div className="kpi-foot"><span className="kpi-delta up"><Ic.arrowUp/> 18%</span> last 30d</div>
        </div>
        <div className="kpi">
          <div className="kpi-lbl">Engagement Rate</div>
          <div className="kpi-val">{c.er}<span className="unit">%</span></div>
          <div className="kpi-foot"><span className="muted">benchmark: 4.0%</span></div>
        </div>
        <div className="kpi">
          <div className="kpi-lbl">Avg CPM</div>
          <div className="kpi-val">${c.cpm}</div>
          <div className="kpi-foot"><span className="kpi-delta up"><Ic.arrowDn/> 8%</span> vs portfolio avg</div>
        </div>
        <div className="kpi">
          <div className="kpi-lbl">Episodes / Posts</div>
          <div className="kpi-val">{c.episodes}<span className="unit" style={{margin:'0 6px', color:'var(--ink-3)'}}>/</span>{totalPosts}</div>
          <div className="kpi-foot"><span className="muted">{c.topChannel} leading</span></div>
        </div>
      </div>

      {/* CHANNELS */}
      <div className="sec">
        <div className="sec-h">
          <div>
            <div className="sec-title">By <em>channel</em></div>
            <div className="sec-sub" style={{marginTop:6}}>Reach, engagement, and CPM with platform benchmarks.</div>
          </div>
        </div>

        <div style={{display:'grid', gridTemplateColumns:'repeat(5, 1fr)', gap:12, marginBottom:16}}>
          {channels.map(ch => {
            const erDiff = ch.er - ch.bench.er;
            const cpmDiff = ch.bench.cpm > 0 ? ((ch.bench.cpm - ch.cpm) / ch.bench.cpm) * 100 : 0;
            return (
              <div key={ch.name} className="chan">
                <div className="chan-h">
                  <div className="chan-name">
                    {ch.name === 'YouTube' ? <>You<em style={{fontStyle:'italic'}}>Tube</em></> :
                     ch.name === 'LinkedIn' ? <>Linked<em style={{fontStyle:'italic'}}>In</em></> :
                     ch.name === 'Instagram' ? <>Insta<em style={{fontStyle:'italic'}}>gram</em></> :
                     ch.name === 'TikTok' ? <>Tik<em style={{fontStyle:'italic'}}>Tok</em></> :
                     <em style={{fontStyle:'italic'}}>X</em>}
                  </div>
                  <span style={{ width: 12, height: 12, borderRadius: '50%', background: ch.color }}/>
                </div>
                <div className="chan-stats">
                  <div className="chan-stat"><div className="v">{fmt.num(ch.impressions)}</div><div className="l">Impr.</div></div>
                  <div className="chan-stat"><div className="v">{fmt.num(ch.eng)}</div><div className="l">Eng.</div></div>
                  <div className="chan-stat"><div className="v">{ch.er}<span style={{fontSize:11, color:'var(--ink-3)'}}>%</span></div><div className="l">ER</div></div>
                  <div className="chan-stat"><div className="v">{ch.cpm === 0 ? '—' : '$'+ch.cpm}</div><div className="l">CPM</div></div>
                </div>
                <div style={{
                  marginTop: 10, paddingTop: 10, borderTop: '1px solid var(--line)',
                  display:'flex', flexDirection:'column', gap: 5
                }}>
                  <div style={{display:'flex', justifyContent:'space-between', fontSize: 11}}>
                    <span style={{color:'var(--ink-3)'}}>ER bench</span>
                    <span style={{fontWeight:500, color:'var(--ink-2)'}}>
                      {ch.bench.er}% <span style={{color: erDiff > 0 ? 'var(--positive)' : 'var(--danger)', fontWeight:600, marginLeft:4}}>
                        {erDiff > 0 ? '+' : ''}{erDiff.toFixed(1)}
                      </span>
                    </span>
                  </div>
                  {ch.bench.cpm > 0 && (
                    <div style={{display:'flex', justifyContent:'space-between', fontSize: 11}}>
                      <span style={{color:'var(--ink-3)'}}>CPM bench</span>
                      <span style={{fontWeight:500, color:'var(--ink-2)'}}>
                        ${ch.bench.cpm.toFixed(2)} <span style={{color: cpmDiff > 0 ? 'var(--positive)' : 'var(--danger)', fontWeight:600, marginLeft:4}}>
                          {cpmDiff > 0 ? '+' : ''}{cpmDiff.toFixed(0)}%
                        </span>
                      </span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* PER-EPISODE PERFORMANCE — collapsible rich table */}
      <div className="sec">
        <div className="sec-h">
          <div>
            <div className="sec-title">Per-episode <em>performance</em></div>
            <div className="sec-sub" style={{marginTop:6}}>Click any episode row to expand the full platform breakdown — distribution type, paid vs organic split, spend, and ER.</div>
          </div>
        </div>
        <EpisodePerformanceTable episodes={EPISODES} channels={channels}/>
      </div>

      {/* EPISODE COMPARISON CARDS */}
      <div className="sec">
        <div className="sec-h">
          <div>
            <div className="sec-title">Episode <em>comparison</em></div>
            <div className="sec-sub" style={{marginTop:6}}>What worked, what didn't — episode by episode.</div>
          </div>
        </div>
        <div style={{display:'grid', gridTemplateColumns:'repeat(3, 1fr)', gap:14}}>
          {EPISODES.map((e, idx) => {
            const tones = ['ft-3', 'ft-4', 'ft-2'];
            const bgs = { 'ft-3': 'var(--sky)', 'ft-4': 'var(--pear)', 'ft-2': 'var(--blossom)' };
            return (
              <div key={e.n} style={{
                background: 'var(--surface)', border: '1px solid var(--line)',
                borderRadius: 'var(--r-lg)', padding: 22, display:'flex', flexDirection:'column', gap: 14
              }}>
                <div>
                  <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom: 10}}>
                    <span style={{fontSize:11, letterSpacing:'0.12em', textTransform:'uppercase', fontWeight:600, color:'var(--ink-3)'}}>{e.n}</span>
                    <span style={{
                      background: bgs[tones[idx]], padding:'3px 10px', borderRadius: 999,
                      fontSize:11, fontWeight:600, color:'var(--liquorice)'
                    }}>{e.date}</span>
                  </div>
                  <div style={{fontFamily:'var(--serif)', fontSize:20, fontWeight:300, lineHeight:1.2, letterSpacing:'-0.01em', color:'var(--ink)'}}>{e.title}</div>
                </div>
                <div style={{display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:8, paddingTop:12, borderTop:'1px solid var(--line)'}}>
                  <div>
                    <div style={{fontFamily:'var(--serif)', fontSize:24, fontWeight:300, color:'var(--ink)'}}>{fmt.num(e.total.impr)}</div>
                    <div style={{fontSize:10, color:'var(--ink-3)', textTransform:'uppercase', letterSpacing:'0.08em', fontWeight:600, marginTop:2}}>Impr.</div>
                  </div>
                  <div>
                    <div style={{fontFamily:'var(--serif)', fontSize:24, fontWeight:300, color:'var(--ink)'}}>{e.total.er}<span style={{fontSize:13, color:'var(--ink-3)'}}>%</span></div>
                    <div style={{fontSize:10, color:'var(--ink-3)', textTransform:'uppercase', letterSpacing:'0.08em', fontWeight:600, marginTop:2}}>ER</div>
                  </div>
                  <div>
                    <div style={{fontFamily:'var(--serif)', fontSize:24, fontWeight:300, color:'var(--ink)'}}>{fmt.num(e.total.eng)}</div>
                    <div style={{fontSize:10, color:'var(--ink-3)', textTransform:'uppercase', letterSpacing:'0.08em', fontWeight:600, marginTop:2}}>Eng.</div>
                  </div>
                </div>
                <div style={{display:'flex', flexDirection:'column', gap:8}}>
                  {e.callouts.map((co, i) => (
                    <div key={i} style={{
                      display:'flex', gap: 10, padding: '10px 12px',
                      background: co.kind === 'pos' ? 'rgba(143,199,102,0.12)' : 'rgba(255,153,71,0.14)',
                      borderRadius: 8, fontSize: 12, lineHeight: 1.45
                    }}>
                      <span style={{
                        fontFamily:'var(--mono)', fontSize:10, fontWeight:600,
                        color: co.kind === 'pos' ? '#2f7a3f' : '#b8392b',
                        flexShrink: 0, marginTop: 1, letterSpacing: '0.04em'
                      }}>{co.kind === 'pos' ? '↑ WIN' : '! WATCH'}</span>
                      <span style={{color:'var(--ink-2)'}}>{co.text}</span>
                    </div>
                  ))}
                </div>

                {/* TOP POSTS for this episode */}
                <div style={{paddingTop:14, borderTop:'1px solid var(--line)'}}>
                  <div style={{fontSize:10, fontFamily:'var(--mono)', letterSpacing:'0.12em', fontWeight:600, color:'var(--ink-3)', marginBottom:10, textTransform:'uppercase'}}>
                    Top posts · this episode
                  </div>
                  <div style={{display:'flex', flexDirection:'column', gap:8}}>
                    {e.topPosts.map((p, i) => (
                      <a key={i} href="#" style={{
                        textDecoration:'none', color:'inherit',
                        display:'flex', alignItems:'center', gap:10,
                        padding:'8px 10px', borderRadius:6,
                        background:'var(--bg-soft)', border:'1px solid var(--line)'
                      }}>
                        <span style={{
                          fontFamily:'var(--serif)', fontSize:18, fontWeight:300,
                          color:'var(--ink)', minWidth:48, fontVariantNumeric:'tabular-nums'
                        }}>{p.er.toFixed(2)}<span style={{fontSize:10, color:'var(--ink-3)'}}>%</span></span>
                        <span style={{flex:1, fontSize:12, color:'var(--ink-2)', lineHeight:1.4, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}}>"{p.quote}"</span>
                        <PlatformPill name={p.platform}/>
                        <span style={{color:'var(--ink-3)', display:'inline-flex'}}><Ic.ext/></span>
                      </a>
                    ))}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* TOP POSTS — linkable */}
      <div className="sec">
        <div className="sec-h">
          <div>
            <div className="sec-title">Top <em>posts</em></div>
            <div className="sec-sub" style={{marginTop:6}}>Highest-engagement assets on this campaign. Click to open the original.</div>
          </div>
          <a href="#" style={{fontSize:12, color:'var(--ink)', textDecoration:'none', fontWeight:500}}>See all posts →</a>
        </div>
        <div className="card" style={{padding:0, overflow:'hidden'}}>
          {TOP_POSTS.slice(0, 6).map((p, idx) => (
            <a key={idx} href={p.url || '#'} target="_blank" rel="noreferrer"
              style={{
                display:'grid', gridTemplateColumns:'40px 1fr 140px 90px 90px 30px', gap:18,
                padding:'16px 22px', alignItems:'center',
                borderBottom: idx < 5 ? '1px solid var(--line)' : 'none',
                textDecoration:'none', color:'inherit', cursor:'pointer',
                transition:'background 0.15s'
              }}
              onMouseEnter={(ev) => ev.currentTarget.style.background = 'var(--bg-soft)'}
              onMouseLeave={(ev) => ev.currentTarget.style.background = ''}>
              <div style={{fontFamily:'var(--serif)', fontStyle:'italic', fontSize:24, fontWeight:300, color:'var(--ink-3)'}}>{idx + 1}</div>
              <div style={{minWidth:0}}>
                <div style={{fontSize:14, fontWeight:500, marginBottom:4, lineHeight:1.4, overflow:'hidden', textOverflow:'ellipsis', display:'-webkit-box', WebkitLineClamp:1, WebkitBoxOrient:'vertical'}}>{p.quote}</div>
                <div style={{fontSize:11, color:'var(--ink-3)'}}>{p.format} · {p.partner}</div>
              </div>
              <div><PlatformPill name={p.platform}/></div>
              <div style={{textAlign:'right'}}>
                <div style={{fontFamily:'var(--serif)', fontSize:20, fontWeight:300}}>{fmt.num(p.reach)}</div>
                <div style={{fontSize:10, color:'var(--ink-3)', textTransform:'uppercase', letterSpacing:'0.08em', fontWeight:600}}>Reach</div>
              </div>
              <div style={{textAlign:'right'}}>
                <div style={{fontFamily:'var(--serif)', fontSize:20, fontWeight:300}}>{p.er.toFixed(1)}<span style={{fontSize:12, color:'var(--ink-3)'}}>%</span></div>
                <div style={{fontSize:10, color:'var(--ink-3)', textTransform:'uppercase', letterSpacing:'0.08em', fontWeight:600}}>ER</div>
              </div>
              <div style={{color:'var(--ink-3)', display:'flex', justifyContent:'flex-end'}}><Ic.ext/></div>
            </a>
          ))}
        </div>
      </div>

      {/* WHAT WE'RE SEEING — redesigned callouts */}
      <div className="sec">
        <div className="sec-h">
          <div>
            <div className="sec-title">What we're <em>seeing</em></div>
            <div className="sec-sub" style={{marginTop:6}}>Auto-flagged based on this campaign's recent activity.</div>
          </div>
        </div>
        <div style={{display:'grid', gridTemplateColumns:'repeat(3, 1fr)', gap:14}}>
          {[
            { tag: 'WIN', kind: 'pos', headline: 'YouTube CPM is 25% under benchmark.', body: `All three episodes averaging $0.49 CPM vs. $0.65 platform benchmark. Reserve $2–3K of remaining budget for an in-feed extension.`, meta: '3 episodes · YouTube' },
            { tag: 'OPPORTUNITY', kind: 'info', headline: 'LinkedIn organic ER averaging 5.4%.', body: `100% organic distribution across ${c.episodes * 3} posts. Increasing posting cadence is the highest-ROI lever for this flight.`, meta: 'LinkedIn · Organic' },
            { tag: 'WATCH', kind: 'warn', headline: 'Instagram CPM is trending up.', body: 'Up to $5.25 from $4.10 in March — 17% above benchmark. Consider tightening audience targeting or pausing under-performing creative.', meta: 'Instagram · Paid' },
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

// Tiny custom curve chart with goal line
function DeliveryCurve({ campaign }) {
  const W = 600, H = 240, P = { t: 16, r: 16, b: 30, l: 32 };
  const weeks = 16;
  const goal = campaign.impressions.goal;
  const progress = campaign.impressions.delivered / goal;
  const elapsed = campaign.elapsedPct / 100;

  const ideal = Array.from({length: weeks + 1}, (_, i) => (i / weeks) * goal);
  const actual = Array.from({length: weeks + 1}, (_, i) => {
    if (i / weeks > elapsed + 0.05) return null;
    const t = i / weeks / Math.max(0.01, elapsed);
    const noise = Math.sin(i * 1.3) * 0.04;
    return Math.min(goal, t * progress * goal + noise * goal);
  });

  const yMax = goal * 1.05;
  const x = (i) => P.l + (i * (W - P.l - P.r)) / weeks;
  const y = (v) => H - P.b - (v / yMax) * (H - P.t - P.b);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{width:'100%',height:'100%',display:'block'}}>
      {[0, 0.25, 0.5, 0.75, 1].map((p, i) => {
        const v = p * yMax;
        const yy = y(v);
        return (
          <g key={i}>
            <line x1={P.l} x2={W-P.r} y1={yy} y2={yy} stroke="currentColor" strokeOpacity="0.08"/>
            <text x={P.l-6} y={yy+3} fontSize="9" textAnchor="end" fill="currentColor" opacity="0.5">{fmt.num(v)}</text>
          </g>
        );
      })}
      <line x1={P.l} x2={W-P.r} y1={y(goal)} y2={y(goal)} stroke="var(--ink)" strokeWidth="1" strokeDasharray="3 3" opacity="0.5"/>
      <text x={W-P.r} y={y(goal)-6} fontSize="10" textAnchor="end" fill="currentColor" fontWeight="600">Goal {fmt.num(goal)}</text>
      <polyline points={ideal.map((v,i) => `${x(i)},${y(v)}`).join(' ')}
        fill="none" stroke="var(--ink-3)" strokeWidth="1.5" strokeDasharray="4 4" opacity="0.6"/>
      <polyline points={actual.filter(v => v !== null).map((v,i) => `${x(i)},${y(v)}`).join(' ')}
        fill="none" stroke="var(--flame)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
      <line x1={x(weeks * elapsed)} x2={x(weeks * elapsed)}
        y1={P.t} y2={H-P.b} stroke="var(--ink)" strokeWidth="1" opacity="0.4"/>
      <circle cx={x(weeks * elapsed)} cy={y(progress * goal)} r="5" fill="var(--flame)"/>
      <circle cx={x(weeks * elapsed)} cy={y(progress * goal)} r="9" fill="var(--flame)" opacity="0.2"/>
      {[0, 4, 8, 12, 16].map(w => (
        <text key={w} x={x(w)} y={H-12} fontSize="10" textAnchor="middle" fill="currentColor" opacity="0.6">W{w + 1}</text>
      ))}
      <text x={x(weeks * elapsed)} y={P.t-2} fontSize="9" textAnchor="middle" fill="currentColor" fontWeight="600">Today</text>
    </svg>
  );
}

window.CampaignPage = CampaignPage;
