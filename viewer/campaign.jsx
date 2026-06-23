/* global React, CAMPAIGNS, TOP_POSTS, CHANNELS, FORMATS, fmt,
   Ic, PlatformPill, PageHead, MultiLineChart, Donut, BarChart, PaceBar */
const { useState: useStateC } = React;

// "Last Updated" label for the campaign header — when this campaign's freshest
// export was provided (c.lastUpdated, ISO UTC from the pipeline). Renders date
// + time so the team can see data recency at a glance.
function fmtLastUpdated(iso) {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    const opts = { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit', timeZone: 'UTC' };
    return d.toLocaleString('en-US', opts) + ' UTC';
  } catch {
    return String(iso);
  }
}

// Campaign card colours — one distinct hue per client (see styles.css
// --pal-* + .cmp-card.ft-*). Dark fills (denim, ink) use light text + tracks;
// the rest use dark text on the colour. Shared by the regular + BrandX heroes.
const _toneDark = (v) => ({ bg:`var(${v})`, fg:'var(--liquorice)', dim:'rgba(31,26,21,0.7)', track:'rgba(31,26,21,0.18)', fill:'var(--liquorice)' });
const _toneLight = (v) => ({ bg:`var(${v})`, fg:'var(--paper)', dim:'rgba(250,247,239,0.75)', track:'rgba(250,247,239,0.2)', fill:'var(--paper)' });
const CARD_TONES = {
  'ft-1':  _toneDark('--pal-orange'),
  'ft-2':  _toneDark('--pal-coral'),
  'ft-3':  _toneDark('--pal-sky'),
  'ft-4':  _toneDark('--pal-lime'),
  'ft-5':  _toneDark('--pal-periwinkle'),
  'ft-6':  _toneDark('--pal-terracotta'),
  'ft-7':  _toneDark('--pal-sunflower'),
  'ft-8':  _toneDark('--pal-aqua'),
  'ft-9':  _toneDark('--pal-orchid'),
  'ft-10': _toneLight('--pal-denim'),
  'ft-11': _toneDark('--pal-fern'),
  'ft-ink': { bg:'var(--liquorice)', fg:'var(--cream)', dim:'rgba(245,241,232,0.7)', track:'rgba(245,241,232,0.2)', fill:'var(--cream)' },
};
function cardToneFor(color) { return CARD_TONES[color] || CARD_TONES['ft-ink']; }

function CampaignPage({ campaignId, onBack }) {
  const c = CAMPAIGNS.find(x => x.id === campaignId) || CAMPAIGNS[0];
  // BrandX campaigns (paid-social performance) get a totally different page
  // treatment — different KPIs, different table columns, no episode rollup.
  if (c.type === 'brandx') return <BrandXCampaignPage c={c} onBack={onBack}/>;
  // Flight-TBD campaigns: goals haven't been set yet, so impPct / budPct
  // would divide by zero. Guard against it so they render as "TBD" later
  // without breaking downstream math.
  const flightTbd = c.flight === 'TBD' || (c.impressions.goal === 0 && c.budget.goal === 0);
  const impPct = c.impressions.goal > 0 ? (c.impressions.delivered / c.impressions.goal) * 100 : 0;
  const budPct = c.budget.goal > 0 ? (c.budget.delivered / c.budget.goal) * 100 : 0;
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

  // Per-campaign channels (with YouTube split into In-feed + Pre-roll).
  // Falls back to scaled cross-campaign data if the per-campaign rollup isn't populated.
  const channels = (c.channels && c.channels.length > 0)
    ? c.channels
    : CHANNELS.map(ch => ({
        ...ch,
        impressions: Math.round(ch.impressions * (c.impressions.delivered / 13_780_000)),
        eng: Math.round(ch.eng * (c.impressions.delivered / 13_780_000))
      }));

  const totalPosts = c.episodes * 6 + 4;

  // Episode breakdown by channel
  // distKind: 'organic' | 'organic+boosted' | 'paid'
  const EPISODES = (window.EPISODES_BY_CAMPAIGN || {})[campaignId] || [];

  const cardTone = cardToneFor(c.color);

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
        actions={<>
          <div className="card" style={{
            padding:'14px 18px', minWidth:240, background:'var(--surface)',
            border:'1px solid var(--line)', borderRadius:'var(--r-md)',
            display:'flex', flexDirection:'column', gap:6
          }}>
            <div style={{display:'flex', justifyContent:'space-between', fontSize:11, gap:16}}>
              <span style={{color:'var(--ink-3)', fontWeight:500}}>Flight</span>
              <span style={{color:'var(--ink)', fontWeight:600, textAlign:'right'}}>{c.flight}</span>
            </div>
            <div style={{display:'flex', justifyContent:'space-between', fontSize:11, gap:16}}>
              <span style={{color:'var(--ink-3)', fontWeight:500}}>Last Updated</span>
              <span style={{color:'var(--ink)', fontWeight:600, textAlign:'right'}}>{fmtLastUpdated(c.lastUpdated)}</span>
            </div>
          </div>
          <div style={{display:'flex', flexDirection:'column', gap:8, marginLeft:12}}>
            <button className="btn btn-acc"><Ic.download/> Export</button>
            <WrapCampaignButton campaign={c}/>
          </div>
        </>}
      />

      {/* HERO PACING BANNER */}
      <div style={{
        background: cardTone.bg, color: cardTone.fg,
        borderRadius: 'var(--r-lg)', padding: 22,
        marginBottom: 24, display: 'grid',
        gridTemplateColumns: '1.1fr 1fr 1fr', gap: 24,
        alignItems: 'center', position: 'relative', overflow: 'hidden'
      }}>
        <div>
          <div style={{display:'flex', alignItems:'center', gap:8, marginBottom:10}}>
            <span style={{fontSize:10, letterSpacing:'0.14em', textTransform:'uppercase', fontWeight:600, opacity:0.7}}>Status</span>
            <span style={{
              display:'inline-flex', alignItems:'center', gap:6,
              padding:'3px 10px', borderRadius:999,
              background: 'rgba(255,255,255,0.92)',
              color: c.statusKind === 'on' ? '#2f7a3f' : c.statusKind === 'danger' ? '#b8392b' : '#a06b14',
              fontFamily:'var(--mono)', fontSize:10, letterSpacing:'0.06em', fontWeight:600
            }}>
              <span style={{width:6, height:6, borderRadius:'50%', background: c.statusKind === 'on' ? '#2f7a3f' : (c.statusKind === 'danger' ? '#b8392b' : '#a06b14')}}/>
              {c.status}
            </span>
          </div>
          <div style={{fontSize:13, lineHeight:1.5, opacity:0.88}}>{c.blurb}</div>
        </div>
        <div>
          <div style={{fontSize:11, letterSpacing:'0.12em', textTransform:'uppercase', fontWeight:600, opacity:0.7, marginBottom:10}}>Impression delivery</div>
          <div style={{display:'flex', alignItems:'baseline', gap:8, marginBottom:8}}>
            <span style={{fontFamily:'var(--serif)', fontSize:48, lineHeight:1, letterSpacing:'-0.02em', fontWeight:300}}>{fmt.num(c.impressions.delivered)}</span>
            <span style={{fontSize:14, opacity:0.7}}>{c.impressions.goal > 0 ? `of ${fmt.num(c.impressions.goal)}` : 'goal TBD'}</span>
          </div>
          <div style={{height:6, background: cardTone.track, borderRadius:999, overflow:'hidden', marginBottom:6}}>
            <div style={{height:'100%', width: Math.min(100,impPct)+'%', background: cardTone.fill, borderRadius:999}}/>
          </div>
          <div style={{fontSize:12, opacity:0.7}}>
            {c.impressions.goal > 0
              ? `${impPct.toFixed(1)}% delivered · ${elapsedPct.toFixed(0)}% time elapsed`
              : flightTbd ? 'Pacing pending — flight & goal TBD' : 'No impression goal set'}
          </div>
        </div>
        <div>
          <div style={{fontSize:11, letterSpacing:'0.12em', textTransform:'uppercase', fontWeight:600, opacity:0.7, marginBottom:10}}>Budget</div>
          <div style={{display:'flex', alignItems:'baseline', gap:8, marginBottom:8}}>
            <span style={{fontFamily:'var(--serif)', fontSize:48, lineHeight:1, letterSpacing:'-0.02em', fontWeight:300}}>{fmt.money(c.budget.delivered)}</span>
            <span style={{fontSize:14, opacity:0.7}}>{c.budget.goal > 0 ? `of ${fmt.money(c.budget.goal)}` : 'budget TBD'}</span>
          </div>
          <div style={{height:6, background: cardTone.track, borderRadius:999, overflow:'hidden', marginBottom:6}}>
            <div style={{height:'100%', width: Math.min(100,budPct)+'%', background: cardTone.fill, borderRadius:999}}/>
          </div>
          <div style={{fontSize:12, opacity:0.7}}>
            {c.budget.goal > 0
              ? `${budPct.toFixed(1)}% spent · ${fmt.money(c.budget.goal - c.budget.delivered)} remaining`
              : c.budget.delivered > 0
                ? `${fmt.money(c.budget.delivered)} delivered · budget cap pending`
                : flightTbd ? 'Awaiting budget confirmation' : 'No budget set'}
          </div>
        </div>
      </div>

      {/* FLIGHT TRACKER — three-bar pacing alignment */}
      <div className="card" style={{marginBottom: 24}}>
        <div className="card-h">
          <div>
            <div className="card-title-serif">Flight <em>tracker</em></div>
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

      {/* KPI ROW — 5 tiles on one row.
          Avg CPM was dropped (it's still surfaced per-channel in the By Channel
          section). Number sizing scales with viewport but caps lower so long
          full-integer values like "15,279,181" stay readable. */}
      <div className="kpi-row" style={{gridTemplateColumns:'repeat(5, minmax(0, 1fr))'}}>
        <div className="kpi">
          <div className="kpi-lbl">Total Impressions</div>
          <div className="kpi-val" style={{fontSize:'clamp(22px, 2.1vw, 30px)', lineHeight:1.1}}>{fmt.numFull(c.impressions.delivered)}</div>
          <div className="kpi-foot"><span className="muted">{impPct.toFixed(1)}% to goal</span></div>
        </div>
        <div className="kpi">
          <div className="kpi-lbl">Total Views</div>
          <div className="kpi-val" style={{fontSize:'clamp(22px, 2.1vw, 30px)', lineHeight:1.1}}>{fmt.numFull(c.views || 0)}</div>
        </div>
        <div className="kpi">
          <div className="kpi-lbl">Engagements</div>
          <div className="kpi-val" style={{fontSize:'clamp(22px, 2.1vw, 30px)', lineHeight:1.1}}>{fmt.numFull(Math.round(c.impressions.delivered * c.er / 100))}</div>
        </div>
        <div className="kpi">
          <div className="kpi-lbl">Engagement Rate</div>
          <div className="kpi-val" style={{fontSize:'clamp(22px, 2.1vw, 30px)', lineHeight:1.1}}>{c.er}<span className="unit">%</span></div>
        </div>
        <div className="kpi">
          <div className="kpi-lbl">{c.type === 'social' ? 'Posts' : 'Episodes / Posts'}</div>
          <div className="kpi-val" style={{fontSize:'clamp(22px, 2.1vw, 30px)', lineHeight:1.1}}>
            {c.type === 'social'
              ? c.posts
              : <>{c.episodes}<span className="unit" style={{margin:'0 6px', color:'var(--ink-3)'}}>/</span>{c.posts}</>}
          </div>
          <div className="kpi-foot"><span className="muted">{c.topChannel} leading</span></div>
        </div>
      </div>

      {/* PULSE CHECK — was "What we're seeing", moved up per request.
          Always renders on active campaigns so the section has a stable home
          even when no callouts have fired yet. */}
      {(c.lifecycle || 'active') === 'active' && (
      <div className="sec">
        <div className="sec-h">
          <div>
            <div className="sec-title">Pulse <em>check</em></div>
            <div className="sec-sub" style={{marginTop:6}}>Auto-flagged based on this campaign's recent activity.</div>
          </div>
        </div>
        {(c.callouts && c.callouts.length > 0) ? (
          <div style={{display:'grid', gridTemplateColumns:`repeat(${Math.min(c.callouts.length, 3)}, minmax(0, 1fr))`, gap:14}}>
            {c.callouts.map((co, i) => {
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
        ) : (
          <div className="card" style={{padding:'22px', textAlign:'center', fontSize:13, color:'var(--ink-3)'}}>
            No flags yet — this campaign is performing in line with benchmarks.
          </div>
        )}
      </div>
      )}

      {/* PACING BY COMPONENT — per-bucket delivery vs each component's own
          impression goal (Spectrum: Day in the Life / SB Highlights / SB
          Cutdowns). Renders when the campaign defines pacing_components. */}
      {c.pacingComponents && c.pacingComponents.length > 0 && (
        <div className="sec">
          <div className="sec-h">
            <div>
              <div className="sec-title">Pacing by <em>component</em></div>
              <div className="sec-sub" style={{marginTop:6}}>Each component tracked against its own impression goal.</div>
            </div>
          </div>
          <div style={{display:'grid', gridTemplateColumns:`repeat(${Math.min(c.pacingComponents.length, 3)}, minmax(0, 1fr))`, gap:14}}>
            {c.pacingComponents.map((b) => {
              const pct = b.impressions.goal ? (b.impressions.delivered / b.impressions.goal) * 100 : 0;
              const done = pct >= 100;
              const barCol = cardTone.bg === 'var(--liquorice)' ? 'var(--ink)' : cardTone.bg;
              const tag = pct >= 105 ? 'Goal exceeded' : pct >= 100 ? 'Goal hit' : 'In progress';
              const tagColor = done ? '#2f7a3f' : 'var(--ink-3)';
              const tagBg = done ? 'rgba(143,199,102,0.18)' : 'var(--bg-soft)';
              return (
                <div key={b.label} className="card" style={{padding:22, display:'flex', flexDirection:'column', gap:10}}>
                  <div style={{fontSize:12, fontWeight:600, color:'var(--ink)', lineHeight:1.35, minHeight:34}}>{b.label}</div>
                  <div style={{display:'flex', alignItems:'baseline', gap:8}}>
                    <span style={{fontFamily:'var(--serif)', fontSize:30, fontWeight:300, letterSpacing:'-0.01em'}}>{fmt.numFull(b.impressions.delivered)}</span>
                    <span style={{fontSize:12, color:'var(--ink-3)'}}>of {fmt.numFull(b.impressions.goal)}</span>
                  </div>
                  <div style={{height:6, background:'var(--bg-soft)', borderRadius:999, overflow:'hidden'}}>
                    <div style={{height:'100%', width: Math.min(100, pct) + '%', background: barCol, borderRadius:999}}/>
                  </div>
                  <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
                    <span style={{fontSize:13, fontWeight:600, color:'var(--ink)'}}>{pct.toFixed(0)}%<span style={{fontSize:11, color:'var(--ink-3)', fontWeight:400}}> to goal</span></span>
                    <span style={{fontFamily:'var(--mono)', fontSize:10, letterSpacing:'0.08em', fontWeight:600, color:tagColor, background:tagBg, padding:'3px 8px', borderRadius:4, textTransform:'uppercase'}}>{done ? '✓ ' : ''}{tag}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* FULL EPISODES vs CUTDOWNS — only renders when YAML defines
          goal_split_full_ep + goal_split_cutdowns for the campaign. Two
          side-by-side cards with separate impression + budget goals so
          partners can see how each tier is tracking. */}
      {c.goalSplit && c.goalSplit.length === 2 && (
        <div className="sec">
          <div className="sec-h">
            <div>
              <div className="sec-title">Full episodes <em>vs</em> cutdowns</div>
              <div className="sec-sub" style={{marginTop:6}}>Separate impression and budget targets for the long-form content and the cutdown rollout.</div>
            </div>
          </div>
          <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:14}}>
            {c.goalSplit.map((tier) => {
              const impPct = tier.impressions.goal ? (tier.impressions.delivered / tier.impressions.goal) * 100 : 0;
              const budPct = tier.budget.goal ? (tier.budget.delivered / tier.budget.goal) * 100 : 0;
              return (
                <div key={tier.label} className="card" style={{padding:22}}>
                  <div style={{fontSize:11, letterSpacing:'0.12em', textTransform:'uppercase', color:'var(--ink-3)', fontWeight:600, marginBottom:8}}>
                    {tier.label} · <span style={{color:'var(--ink-2)'}}>{tier.posts} {tier.posts === 1 ? 'post' : 'posts'}</span>
                  </div>
                  <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:18}}>
                    <div>
                      <div style={{fontSize:10, color:'var(--ink-3)', letterSpacing:'0.08em', textTransform:'uppercase', fontWeight:600, marginBottom:6}}>Impressions</div>
                      <div style={{display:'flex', alignItems:'baseline', gap:6, marginBottom:8}}>
                        <span style={{fontFamily:'var(--serif)', fontSize:26, fontWeight:300}}>{fmt.numFull(tier.impressions.delivered)}</span>
                      </div>
                      <div style={{height:5, background:'var(--bg-soft)', borderRadius:999, overflow:'hidden', marginBottom:5}}>
                        <div style={{height:'100%', width: Math.min(100, impPct) + '%', background: cardTone.bg === 'var(--liquorice)' ? 'var(--ink)' : cardTone.bg}}/>
                      </div>
                      <div style={{fontSize:11, color:'var(--ink-3)'}}>{impPct.toFixed(1)}% of {fmt.numFull(tier.impressions.goal)} goal</div>
                    </div>
                    <div>
                      <div style={{fontSize:10, color:'var(--ink-3)', letterSpacing:'0.08em', textTransform:'uppercase', fontWeight:600, marginBottom:6}}>Spend</div>
                      <div style={{display:'flex', alignItems:'baseline', gap:6, marginBottom:8}}>
                        <span style={{fontFamily:'var(--serif)', fontSize:26, fontWeight:300}}>{fmt.moneyFull(tier.budget.delivered)}</span>
                      </div>
                      {tier.budget.goal > 0 ? (
                        <>
                          <div style={{height:5, background:'var(--bg-soft)', borderRadius:999, overflow:'hidden', marginBottom:5}}>
                            <div style={{height:'100%', width: Math.min(100, budPct) + '%', background:'var(--pear)'}}/>
                          </div>
                          <div style={{fontSize:11, color:'var(--ink-3)'}}>{budPct.toFixed(1)}% of {fmt.moneyFull(tier.budget.goal)} budget</div>
                        </>
                      ) : (
                        // No per-tier budget split configured (only impression
                        // goals differ) — show delivered spend without a goal bar.
                        <div style={{fontSize:11, color:'var(--ink-3)'}}>spend delivered · no per-tier budget</div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* PER-EPISODE PERFORMANCE — content campaigns only. Each episode row is
          clickable and expands to show every individual POST in that episode
          (not aggregated per platform — the By Channel section already does that). */}
      {c.type !== 'social' && EPISODES.length > 0 && (
      <div className="sec">
        <div className="sec-h">
          <div>
            <div className="sec-title">Per-episode <em>performance</em></div>
            <div className="sec-sub" style={{marginTop:6}}>Click any episode row to expand the post-by-post breakdown — every individual post on every platform, with distribution, paid vs organic split, spend, and ER.</div>
          </div>
        </div>
        <EpisodePerformanceTable episodes={EPISODES} channels={channels}/>
      </div>
      )}

      {/* POST-LEVEL PERFORMANCE — flat table of every post in the campaign
          (no episode wrapper). Always shown for social; also shown for content
          campaigns that have no episode breakdown (e.g. Microsoft, State Farm),
          where it's the only post-by-post view. Content campaigns WITH episodes
          use the per-episode table above instead. */}
      {(c.type === 'social' || EPISODES.length === 0) && (() => {
        const rows = (window.POSTS_BY_CAMPAIGN || {})[campaignId] || [];
        if (!rows.length) return null;
        const distLabel = (k) =>
          k === 'organic' ? { txt: 'Organic only', bg: 'rgba(143,199,102,0.18)', fg: '#2f7a3f' } :
          k === 'paid'    ? { txt: 'Paid only',    bg: 'rgba(36,28,23,0.10)',    fg: 'var(--liquorice)' } :
                            { txt: 'Organic + Boosted', bg: 'rgba(92,181,242,0.20)', fg: '#0a4f7a' };
        const chColor = (name) => (channels.find(c => c.name === name) || {}).color || '#666';
        return (
          <div className="sec">
            <div className="sec-h">
              <div>
                <div className="sec-title">Post-level <em>performance</em></div>
                <div className="sec-sub" style={{marginTop:6}}>Every post in this campaign, broken out individually. Distribution, paid vs organic split, spend, and ER per row.</div>
              </div>
            </div>
            <PerPostTable rows={rows} distLabel={distLabel} chColor={chColor}/>
          </div>
        );
      })()}

      {/* EPISODE / COMPONENT COMPARISON CARDS — hidden for single-component
          campaigns since the side-by-side cards collapse to just one and
          duplicate what the per-episode performance section already shows.
          For social campaigns these are framed as "components" (e.g. RBC's
          Heather/DITL/Panel buckets, Heineken's Editorial/Red Card pieces,
          Spectrum's NASCAR/World Cup/Branded Article parts) rather than
          episodes — they're parallel pieces of one campaign, not a series. */}
      {EPISODES.length > 1 && (
      <div className="sec">
        <div className="sec-h">
          <div>
            <div className="sec-title">
              {c.type === 'social' ? <>Component <em>comparison</em></> : <>Episode <em>comparison</em></>}
            </div>
            <div className="sec-sub" style={{marginTop:6}}>
              {c.type === 'social'
                ? `Side-by-side across the ${EPISODES.length} components of this campaign.`
                : "What worked, what didn't — episode by episode."}
            </div>
          </div>
        </div>
        <div style={{
          display:'grid',
          gridTemplateColumns: c.type === 'social'
            // Social campaigns can have up to 3 components shown side-by-side
            // (RBC TST = 3 buckets, Heineken = 2 videos, Spectrum = 3 parts).
            // Anything beyond 3 wraps to a second row at 3 cols wide.
            ? `repeat(${Math.min(EPISODES.length, 3)}, minmax(0, 1fr))`
            : 'repeat(3, minmax(0, 1fr))',
          gap:14
        }}>
          {EPISODES.map((e, idx) => {
            const tones = ['ft-3', 'ft-4', 'ft-2'];
            const bgs = { 'ft-3': 'var(--sky)', 'ft-4': 'var(--pear)', 'ft-2': 'var(--blossom)' };
            return (
              <div key={e.n} style={{
                background: 'var(--surface)', border: '1px solid var(--line)',
                borderRadius: 'var(--r-lg)', padding: 18, display:'flex', flexDirection:'column', gap: 12,
                minWidth: 0, overflow: 'hidden'
              }}>
                <div>
                  <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom: 10}}>
                    <span style={{fontSize:11, letterSpacing:'0.12em', textTransform:'uppercase', fontWeight:600, color:'var(--ink-3)'}}>{e.n}</span>
                    <span style={{
                      background: bgs[tones[idx % tones.length]], padding:'3px 10px', borderRadius: 999,
                      fontSize:11, fontWeight:600, color:'var(--liquorice)'
                    }}>{e.date}</span>
                  </div>
                  <div style={{fontFamily:'var(--serif)', fontSize:20, fontWeight:300, lineHeight:1.2, letterSpacing:'-0.01em', color:'var(--ink)'}}>{e.title}</div>
                </div>
                <div style={{display:'grid', gridTemplateColumns:'1fr 1fr 1fr 1fr', gap:8, paddingTop:12, borderTop:'1px solid var(--line)'}}>
                  <div>
                    <div style={{fontFamily:'var(--serif)', fontSize:22, fontWeight:300, color:'var(--ink)'}}>{fmt.num(e.total.impr)}</div>
                    <div style={{fontSize:10, color:'var(--ink-3)', textTransform:'uppercase', letterSpacing:'0.08em', fontWeight:600, marginTop:2}}>Impr.</div>
                  </div>
                  <div>
                    <div style={{fontFamily:'var(--serif)', fontSize:22, fontWeight:300, color:'var(--ink)'}}>{fmt.num(e.total.views || 0)}</div>
                    <div style={{fontSize:10, color:'var(--ink-3)', textTransform:'uppercase', letterSpacing:'0.08em', fontWeight:600, marginTop:2}}>Views</div>
                  </div>
                  <div>
                    <div style={{fontFamily:'var(--serif)', fontSize:22, fontWeight:300, color:'var(--ink)'}}>{e.total.er}<span style={{fontSize:12, color:'var(--ink-3)'}}>%</span></div>
                    <div style={{fontSize:10, color:'var(--ink-3)', textTransform:'uppercase', letterSpacing:'0.08em', fontWeight:600, marginTop:2}}>ER</div>
                  </div>
                  <div>
                    <div style={{fontFamily:'var(--serif)', fontSize:22, fontWeight:300, color:'var(--ink)'}}>{fmt.num(e.total.eng)}</div>
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

                {/* TOP POSTS for this episode — hidden entirely when no post
                    crosses the ER ≥ 2% threshold (no point showing weak ER as
                    a "top post"). */}
                {e.topPosts && e.topPosts.length > 0 && (
                <div style={{paddingTop:14, borderTop:'1px solid var(--line)'}}>
                  <div style={{fontSize:10, fontFamily:'var(--mono)', letterSpacing:'0.12em', fontWeight:600, color:'var(--ink-3)', marginBottom:10, textTransform:'uppercase'}}>
                    Top posts · this episode
                  </div>
                  <div style={{display:'flex', flexDirection:'column', gap:8}}>
                    {e.topPosts.map((p, i) => (
                      <a key={i}
                        href={p.url || '#'}
                        target={p.url ? '_blank' : undefined}
                        rel={p.url ? 'noreferrer' : undefined}
                        style={{
                        textDecoration:'none', color:'inherit',
                        display:'flex', alignItems:'center', gap:8,
                        padding:'8px 10px', borderRadius:6, minWidth:0,
                        background:'var(--bg-soft)', border:'1px solid var(--line)',
                        cursor: p.url ? 'pointer' : 'default'
                      }}>
                        <span style={{
                          fontFamily:'var(--serif)', fontSize:16, fontWeight:300,
                          color:'var(--ink)', minWidth:42, fontVariantNumeric:'tabular-nums', flexShrink:0
                        }}>{p.er.toFixed(1)}<span style={{fontSize:10, color:'var(--ink-3)'}}>%</span></span>
                        <span style={{flex:'1 1 0', minWidth:0, fontSize:11, color:'var(--ink-2)', lineHeight:1.3, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}}>"{p.quote}"</span>
                        <span style={{flexShrink:0, color:'var(--ink-3)', display:'inline-flex'}}><Ic.ext/></span>
                      </a>
                    ))}
                  </div>
                </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
      )}

      {/* TOP POSTS — per-campaign. Hidden entirely when neither list has a
          qualifier (no posts ≥2% ER OR no posts ≥100K organic reach), since
          showing empty tiles with placeholder copy adds noise. The visible
          column count adapts to whichever side has data. */}
      {((c.topPosts && c.topPosts.length > 0) || (c.topPostsOrganic && c.topPostsOrganic.length > 0)) && (
      <div className="sec">
        <div className="sec-h">
          <div>
            <div className="sec-title">Top <em>posts</em></div>
            <div className="sec-sub" style={{marginTop:6}}>Best-performing assets on this campaign. Click any row to open.</div>
          </div>
        </div>
        {(() => {
          const showEr = c.topPosts && c.topPosts.length > 0;
          const showOrg = c.topPostsOrganic && c.topPostsOrganic.length > 0;
          const cols = (showEr && showOrg) ? '1fr 1fr' : '1fr';
          return (
        <div style={{display:'grid', gridTemplateColumns:cols, gap:14}}>
          {/* By engagement rate — only when at least one qualifier exists */}
          {showEr && (
          <div className="card" style={{padding:0, overflow:'hidden'}}>
            <div style={{padding:'18px 22px 14px', borderBottom:'1px solid var(--line)'}}>
              <div className="card-title-serif" style={{fontSize:20}}>By <em>engagement rate</em></div>
              <div style={{fontSize:11, color:'var(--ink-3)', marginTop:4}}>Min 1K views, ER ≥ 2% — ranked by ER%</div>
            </div>
            {c.topPosts.slice(0, 5).map((p, idx, arr) => (
              <a key={p.id || idx} href={p.url || '#'} target="_blank" rel="noreferrer"
                style={{
                  display:'grid', gridTemplateColumns:'28px 1fr 100px 70px 18px', gap:12,
                  padding:'14px 22px', alignItems:'center',
                  borderBottom: idx < arr.length - 1 ? '1px solid var(--line)' : 'none',
                  textDecoration:'none', color:'inherit', cursor:'pointer',
                  transition:'background 0.15s'
                }}
                onMouseEnter={(ev) => ev.currentTarget.style.background = 'var(--bg-soft)'}
                onMouseLeave={(ev) => ev.currentTarget.style.background = ''}>
                <div style={{fontFamily:'var(--mono)', fontSize:11, fontWeight:600, color:'var(--ink-3)', letterSpacing:'0.04em'}}>{String(p.rank || idx + 1).padStart(2,'0')}</div>
                <div style={{minWidth:0}}>
                  <div style={{fontSize:13, fontWeight:500, marginBottom:3, lineHeight:1.35, overflow:'hidden', textOverflow:'ellipsis', display:'-webkit-box', WebkitLineClamp:2, WebkitBoxOrient:'vertical'}}>{p.quote}</div>
                  <div style={{fontSize:10, color:'var(--ink-3)'}}>{p.format}</div>
                </div>
                <div><PlatformPill name={p.platform}/></div>
                <div style={{textAlign:'right'}}>
                  <div style={{fontVariantNumeric:'tabular-nums', fontWeight:600, fontSize:15}}>{p.er.toFixed(2)}<span style={{fontSize:10, color:'var(--ink-3)'}}>%</span></div>
                  <div style={{fontSize:9, color:'var(--ink-3)', textTransform:'uppercase', letterSpacing:'0.08em', fontWeight:600}}>ER</div>
                </div>
                <div style={{color:'var(--ink-3)', display:'flex', justifyContent:'flex-end'}}><Ic.ext/></div>
              </a>
            ))}
          </div>
          )}

          {/* By organic reach — only when at least one qualifier exists */}
          {showOrg && (
          <div className="card" style={{padding:0, overflow:'hidden'}}>
            <div style={{padding:'18px 22px 14px', borderBottom:'1px solid var(--line)'}}>
              <div className="card-title-serif" style={{fontSize:20}}>By <em>organic reach</em></div>
              <div style={{fontSize:11, color:'var(--ink-3)', marginTop:4}}>Min 100K organic — ranked by organic reach</div>
            </div>
            {c.topPostsOrganic.slice(0, 5).map((p, idx, arr) => (
              <a key={p.id || idx} href={p.url || '#'} target="_blank" rel="noreferrer"
                style={{
                  display:'grid', gridTemplateColumns:'28px 1fr 100px 90px 18px', gap:12,
                  padding:'14px 22px', alignItems:'center',
                  borderBottom: idx < arr.length - 1 ? '1px solid var(--line)' : 'none',
                  textDecoration:'none', color:'inherit', cursor:'pointer',
                  transition:'background 0.15s'
                }}
                onMouseEnter={(ev) => ev.currentTarget.style.background = 'var(--bg-soft)'}
                onMouseLeave={(ev) => ev.currentTarget.style.background = ''}>
                <div style={{fontFamily:'var(--mono)', fontSize:11, fontWeight:600, color:'var(--ink-3)', letterSpacing:'0.04em'}}>{String(p.rank || idx + 1).padStart(2,'0')}</div>
                <div style={{minWidth:0}}>
                  <div style={{fontSize:13, fontWeight:500, marginBottom:3, lineHeight:1.35, overflow:'hidden', textOverflow:'ellipsis', display:'-webkit-box', WebkitLineClamp:2, WebkitBoxOrient:'vertical'}}>{p.quote}</div>
                  <div style={{fontSize:10, color:'var(--ink-3)'}}>{p.format} · {p.organicPct}% organic</div>
                </div>
                <div><PlatformPill name={p.platform}/></div>
                <div style={{textAlign:'right'}}>
                  <div style={{fontVariantNumeric:'tabular-nums', fontWeight:600, fontSize:15, color:'#2f7a3f'}}>{fmt.num(p.organicReach)}</div>
                  <div style={{fontSize:9, color:'var(--ink-3)', textTransform:'uppercase', letterSpacing:'0.08em', fontWeight:600}}>Organic</div>
                </div>
                <div style={{color:'var(--ink-3)', display:'flex', justifyContent:'flex-end'}}><Ic.ext/></div>
              </a>
            ))}
          </div>
          )}
        </div>
          );
        })()}
      </div>
      )}

      {/* CHANNELS — moved to bottom per spec. Layout:
            ≤4 channels  → single row (one per column)
            ≥5 channels  → two rows, YT/IG family on top, others below */}
      <div className="sec">
        <div className="sec-h">
          <div>
            <div className="sec-title">By <em>channel</em></div>
            <div className="sec-sub" style={{marginTop:6}}>Reach, engagement, and CPM with platform benchmarks.</div>
          </div>
        </div>

        {(() => {
          const ROW_1_ORDER = ['YouTube In-feed', 'YouTube Pre-roll', 'YouTube Shorts', 'Instagram', 'Instagram Stories'];
          const ROW_2_ORDER = ['X', 'LinkedIn', 'TikTok', 'Facebook'];
          const orderIndex = (arr, name) => {
            const i = arr.indexOf(name);
            return i === -1 ? 999 : i;
          };

          const renderTile = (ch) => {
            const erDiff = ch.er - ch.bench.er;
            const cpmDiff = ch.bench.cpm > 0 ? ((ch.cpm - ch.bench.cpm) / ch.bench.cpm) * 100 : 0;
            return (
              <div key={ch.name} className="chan">
                <div className="chan-h">
                  <div className="chan-name">
                    <em style={{fontStyle:'italic'}}>{ch.name}</em>
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
                  {ch.bench.cpm > 0 && ch.cpm > 0 && (
                    <div style={{display:'flex', justifyContent:'space-between', fontSize: 11}}>
                      <span style={{color:'var(--ink-3)'}}>CPM bench</span>
                      <span style={{fontWeight:500, color:'var(--ink-2)'}}>
                        ${ch.bench.cpm.toFixed(2)} <span style={{color: cpmDiff > 0 ? 'var(--danger)' : 'var(--positive)', fontWeight:600, marginLeft:4}}>
                          {cpmDiff > 0 ? '+' : ''}{cpmDiff.toFixed(0)}%
                        </span>
                      </span>
                    </div>
                  )}
                </div>
              </div>
            );
          };

          // ≤4 channels: render all on one row, sorted by ROW_1_ORDER then ROW_2_ORDER then impressions
          if (channels.length <= 4) {
            const ordered = [...channels].sort((a, b) => {
              const ai = orderIndex(ROW_1_ORDER, a.name);
              const bi = orderIndex(ROW_1_ORDER, b.name);
              if (ai !== bi) return ai - bi;
              const aj = orderIndex(ROW_2_ORDER, a.name);
              const bj = orderIndex(ROW_2_ORDER, b.name);
              if (aj !== bj) return aj - bj;
              return b.impressions - a.impressions;
            });
            return (
              <div style={{display:'grid', gridTemplateColumns:`repeat(${ordered.length}, minmax(0, 1fr))`, gap:10}}>
                {ordered.map(renderTile)}
              </div>
            );
          }

          // ≥5 channels: split into two rows (YouTube/Instagram family on top, rest below)
          const row1 = channels
            .filter(c => ROW_1_ORDER.includes(c.name))
            .sort((a, b) => orderIndex(ROW_1_ORDER, a.name) - orderIndex(ROW_1_ORDER, b.name));
          const row2Set = new Set(ROW_1_ORDER);
          const row2 = channels
            .filter(c => !row2Set.has(c.name))
            .sort((a, b) => {
              const ai = orderIndex(ROW_2_ORDER, a.name);
              const bi = orderIndex(ROW_2_ORDER, b.name);
              if (ai !== bi) return ai - bi;
              return b.impressions - a.impressions;
            });
          return (
            <>
              {row1.length > 0 && (
                <div style={{display:'grid', gridTemplateColumns:`repeat(${row1.length}, minmax(0, 1fr))`, gap:10, marginBottom:10}}>
                  {row1.map(renderTile)}
                </div>
              )}
              {row2.length > 0 && (
                <div style={{display:'grid', gridTemplateColumns:`repeat(${row2.length}, minmax(0, 1fr))`, gap:10, marginBottom:16}}>
                  {row2.map(renderTile)}
                </div>
              )}
            </>
          );
        })()}
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


// =============================================================================
// BrandXCampaignPage — paid-social performance campaigns
// =============================================================================
// Optimization target is efficiency + clicks, not engagement or organic reach.
// Page layout:
//   1. Hero card with the headline KPIs: impressions, ad spend, clicks
//   2. By-channel breakdown (CPM / CTR / CPC efficiency per platform)
//   3. Per-post performance table — every paid asset, sortable columns
// No episodes, no episode comparison, no organic-reach signals.

function BrandXCampaignPage({ c, onBack }) {
  const posts = (window.POSTS_BY_CAMPAIGN || {})[c.id] || [];
  const channels = c.channels || [];

  // Aggregate KPIs across all posts in the campaign
  const totalImpr = posts.reduce((s, p) => s + (p.impr || 0), 0);
  const totalSpend = posts.reduce((s, p) => s + (p.spend || 0), 0);
  const totalClicks = posts.reduce((s, p) => s + (p.clicks || 0), 0);
  const blendedCPM = totalImpr ? (totalSpend / totalImpr * 1000) : 0;
  const blendedCPC = totalClicks ? (totalSpend / totalClicks) : 0;
  const blendedCTR = totalImpr ? (totalClicks / totalImpr * 100) : 0;

  const impPct = c.impressions.goal ? (totalImpr / c.impressions.goal * 100) : 0;
  const budPct = c.budget.goal ? (totalSpend / c.budget.goal * 100) : 0;
  const elapsedPct = c.elapsedPct || 0;

  // Card tone — same mapping used on the regular CampaignPage so the BrandX
  // banner picks up its campaign's brand color (sky for E*TRADE).
  const cardTone = cardToneFor(c.color);

  // Money / number formatters that handle None gracefully.
  // Money: 2 decimals under $100 (so per-click cost reads as $1.50 not $1.5),
  // no decimals at $100+ (so total spend reads as $4,789 not $4,789.00).
  // BrandX shows full, comma-separated numbers everywhere (no 2.0M / 1.6M
  // abbreviation) so the partner sees exact delivery figures.
  const fmtNum = (n) => (n == null ? '—' : window.fmt.numFull(n));
  const fmtMoney = (n) => {
    if (n == null || isNaN(Number(n))) return '—';
    const num = Number(n);
    if (Math.abs(num) >= 100) return `$${Math.round(num).toLocaleString('en-US')}`;
    return `$${num.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
  };
  const fmtPct = (n) => (n == null ? '—' : `${Number(n).toFixed(2)}%`);

  return (
    <>
      <PageHead
        overline={<>
          <span style={{cursor:'pointer'}} onClick={onBack}><Ic.back/> Overview</span>
          <span style={{margin:'0 8px', opacity:0.4}}>/</span>
          <span>{c.partner}</span>
          <span style={{margin:'0 8px', opacity:0.4}}>·</span>
          <span style={{
            background:'var(--liquorice)', color:'var(--paper)',
            padding:'2px 8px', borderRadius:4, fontSize:10, fontWeight:600,
            letterSpacing:'0.06em', textTransform:'uppercase'
          }}>BrandX</span>
          {c.brandxObjective && (
            <>
              <span style={{margin:'0 8px', opacity:0.4}}>·</span>
              <span style={{fontSize:10, fontFamily:'var(--mono)', color:'var(--ink-3)', letterSpacing:'0.06em', textTransform:'uppercase'}}>
                Primary: <strong style={{color:'var(--ink-2)'}}>{c.brandxObjective.replace('_',' ')}</strong>
                {c.brandxSecondaryObjective && (
                  <> · Secondary: <strong style={{color:'var(--ink-2)'}}>{c.brandxSecondaryObjective.replace('_',' ')}</strong></>
                )}
              </span>
            </>
          )}
        </>}
        title={c.series.replace(c.seriesItalic, '').trim()}
        italic={c.seriesItalic}
        actions={
          <div className="card" style={{
            padding:'14px 18px', minWidth:240, background:'var(--surface)',
            border:'1px solid var(--line)', borderRadius:'var(--r-md)',
            display:'flex', flexDirection:'column', gap:6
          }}>
            <div style={{display:'flex', justifyContent:'space-between', fontSize:11, gap:16}}>
              <span style={{color:'var(--ink-3)', fontWeight:500}}>Flight</span>
              <span style={{color:'var(--ink)', fontWeight:600}}>{c.flight}</span>
            </div>
            <div style={{display:'flex', justifyContent:'space-between', fontSize:11, gap:16}}>
              <span style={{color:'var(--ink-3)', fontWeight:500}}>Last Updated</span>
              <span style={{color:'var(--ink)', fontWeight:600, textAlign:'right'}}>{fmtLastUpdated(c.lastUpdated)}</span>
            </div>
          </div>
        }
      />

      {/* HERO KPI TILES — three primary numbers, three secondary metrics
          shown as a tighter strip below. Layout is one card per row so all
          tiles share the same visual rhythm. */}
      <div className="sec">
        {(() => {
          // Pre-compute everything once so the markup stays clean
          const bx = window.BRANDX_BENCHMARKS || {};
          const obj = c.brandxObjective;
          const ctrBench = (obj && bx.ctrByObjective && bx.ctrByObjective[obj] != null)
            ? bx.ctrByObjective[obj]
            : bx.ctrOverall;
          const ctrDelta = ctrBench ? (blendedCTR - ctrBench) / ctrBench * 100 : null;
          const ctrGood = ctrDelta != null && ctrDelta >= 0;
          const totalReach = posts.reduce((s, p) => s + (p.reach || 0), 0);
          const frequency = totalReach > 0 ? totalImpr / totalReach : null;
          // Video Completion Rate = 100%-watched views / video views started.
          // "Started" = Meta's 3-second video view (paid `three_second_views`),
          // which is the industry-standard VCR denominator. Using impressions
          // would dilute the rate with static creative + scroll-pasts that
          // never started the video. Static IG posts contribute 0 in both
          // numerator AND denominator, so they correctly drop out of the mix.
          const totalP100 = posts.reduce((s, p) => s + (p.videoViews100Pct || 0), 0);
          const totalVideoStarts = posts.reduce((s, p) => s + (p.videoViews3s || 0), 0);
          const vcr = totalVideoStarts > 0 ? (totalP100 / totalVideoStarts * 100) : null;
          // Avg view duration = total watch time across all paid posts
          //   ÷ total video starts (3-sec views / paid plays).
          // FB Reels: watch time comes from MS directly (watch_time_minutes_paid).
          // IG ads: MS doesn't report watch time, so refresh.py estimates it
          // by integrating the p25/p50/p75/p95/p100 retention curve × video
          // duration. Approximate but close enough for blended messaging.
          const totalWatchMin = posts.reduce((s, p) => s + (p.watchTimeMin || 0), 0);
          const avgViewSec = totalVideoStarts > 0 ? (totalWatchMin * 60 / totalVideoStarts) : null;
          // Note: bx.vcrOverall is an impressions-based dark-posts benchmark
          // (~0.36%). Comparing it to a video-starts-based VCR is apples to
          // oranges, so we drop the delta and just surface the absolute rate
          // + total full-views count.
          const vcrBench = null;
          const vcrDelta = null;
          const vcrGood = false;

          // Shared tile styles — defined once so all six tiles match
          const tileBase = {padding:'22px 24px'};
          const tileLbl = {
            fontSize:10, color:'var(--ink-3)', letterSpacing:'0.1em',
            fontWeight:600, textTransform:'uppercase', marginBottom:10,
          };
          const tileNum = {
            fontFamily:'var(--serif)', fontSize:'clamp(28px, 2.6vw, 36px)',
            fontWeight:300, color:'var(--ink)', lineHeight:1,
            letterSpacing:'-0.02em', fontVariantNumeric:'tabular-nums',
          };
          const tileSub = {
            marginTop:10, fontSize:11, color:'var(--ink-3)',
            fontFamily:'var(--mono)', letterSpacing:'0.04em',
            minHeight:16,  // keep all tiles the same height
          };
          const progressBar = (pct, show) => show ? (
            <div style={{height:3, background:'var(--line)', borderRadius:2, marginTop:8, overflow:'hidden'}}>
              <div style={{height:'100%', width:`${Math.min(100, pct)}%`, background:'var(--accent)'}}/>
            </div>
          ) : <div style={{height:3, marginTop:8}}/>;

          return (
            <>
              {/* HERO PACING BANNER — mirrors the status banner on the regular
                  CampaignPage but expanded to three metric columns: impressions
                  (vs goal), spend (vs budget), and clicks (no goal, so the
                  subline shows CTR + CPC instead). Status pill sits in a
                  narrow leftmost column — no longer-form description, per the
                  team's preference for BrandX pages. */}
              <div style={{
                background: cardTone.bg, color: cardTone.fg,
                borderRadius: 'var(--r-lg)', padding: 22, marginBottom: 18,
                display: 'grid',
                gridTemplateColumns: '0.45fr 1fr 1fr 1fr', gap: 24,
                alignItems: 'center', position: 'relative', overflow: 'hidden'
              }}>
                <div>
                  <div style={{fontSize:10, letterSpacing:'0.14em', textTransform:'uppercase', fontWeight:600, opacity:0.7, marginBottom:10}}>Status</div>
                  <span style={{
                    display:'inline-flex', alignItems:'center', gap:6,
                    padding:'4px 12px', borderRadius:999,
                    background: 'rgba(255,255,255,0.92)',
                    color: c.statusKind === 'on' ? '#2f7a3f' : c.statusKind === 'danger' ? '#b8392b' : '#a06b14',
                    fontFamily:'var(--mono)', fontSize:10, letterSpacing:'0.06em', fontWeight:600
                  }}>
                    <span style={{
                      width:6, height:6, borderRadius:'50%',
                      background: c.statusKind === 'on' ? '#2f7a3f' : (c.statusKind === 'danger' ? '#b8392b' : '#a06b14')
                    }}/>
                    {c.status}
                  </span>
                  <div style={{fontSize:11, opacity:0.7, marginTop:10, fontFamily:'var(--mono)', letterSpacing:'0.04em'}}>
                    {c.daysLeft} days left · {elapsedPct.toFixed(0)}% time elapsed
                  </div>
                </div>

                <div>
                  <div style={{fontSize:11, letterSpacing:'0.12em', textTransform:'uppercase', fontWeight:600, opacity:0.7, marginBottom:10}}>Impression delivery</div>
                  <div style={{display:'flex', alignItems:'baseline', gap:8, marginBottom:8}}>
                    <span style={{fontFamily:'var(--serif)', fontSize:'clamp(34px, 3.4vw, 48px)', lineHeight:1, letterSpacing:'-0.02em', fontWeight:300}}>{window.fmt.numFull(totalImpr)}</span>
                    <span style={{fontSize:14, opacity:0.7}}>of {window.fmt.numFull(c.impressions.goal)}</span>
                  </div>
                  <div style={{height:6, background: cardTone.track, borderRadius:999, overflow:'hidden', marginBottom:6}}>
                    <div style={{height:'100%', width: Math.min(100, impPct) + '%', background: cardTone.fill, borderRadius:999}}/>
                  </div>
                  <div style={{fontSize:12, opacity:0.7}}>
                    {impPct.toFixed(1)}% delivered · {elapsedPct.toFixed(0)}% time elapsed
                  </div>
                </div>

                <div>
                  <div style={{fontSize:11, letterSpacing:'0.12em', textTransform:'uppercase', fontWeight:600, opacity:0.7, marginBottom:10}}>Budget</div>
                  <div style={{display:'flex', alignItems:'baseline', gap:8, marginBottom:8}}>
                    <span style={{fontFamily:'var(--serif)', fontSize:'clamp(34px, 3.4vw, 48px)', lineHeight:1, letterSpacing:'-0.02em', fontWeight:300}}>{fmtMoney(totalSpend)}</span>
                    <span style={{fontSize:14, opacity:0.7}}>of {fmtMoney(c.budget.goal)}</span>
                  </div>
                  <div style={{height:6, background: cardTone.track, borderRadius:999, overflow:'hidden', marginBottom:6}}>
                    <div style={{height:'100%', width: Math.min(100, budPct) + '%', background: cardTone.fill, borderRadius:999}}/>
                  </div>
                  <div style={{fontSize:12, opacity:0.7}}>
                    {budPct.toFixed(1)}% spent · {fmtMoney(Math.max(0, c.budget.goal - totalSpend))} remaining
                  </div>
                </div>

                <div>
                  <div style={{fontSize:11, letterSpacing:'0.12em', textTransform:'uppercase', fontWeight:600, opacity:0.7, marginBottom:10}}>Total clicks</div>
                  <div style={{display:'flex', alignItems:'baseline', gap:8, marginBottom:8}}>
                    <span style={{fontFamily:'var(--serif)', fontSize:'clamp(34px, 3.4vw, 48px)', lineHeight:1, letterSpacing:'-0.02em', fontWeight:300}}>{window.fmt.numFull(totalClicks)}</span>
                  </div>
                  {/* No goal for clicks — leave the bar slot empty so the
                      sublines on all three columns line up vertically. */}
                  <div style={{height:6, marginBottom:6}}/>
                  <div style={{fontSize:12, opacity:0.7}}>
                    {fmtPct(blendedCTR)} CTR · {fmtMoney(blendedCPC)} CPC
                  </div>
                </div>
              </div>

              {/* SECONDARY ROW — Blended CPC, Blended CTR, VCR, Avg View
                  Duration, Frequency. Five columns at smaller numeral size
                  than the banner above, so visual hierarchy reads top →
                  bottom. VCR = `video_views_p100` / 3-second video starts
                  across all paid posts (Meta-standard denominator — see
                  comment above the calc). */}
              <div style={{display:'grid', gridTemplateColumns:'repeat(5, 1fr)', gap:14, marginBottom:14}}>
                <div className="card" style={tileBase}>
                  <div style={tileLbl}>Blended CPC</div>
                  <div style={{...tileNum, fontSize:'clamp(22px, 2vw, 28px)'}}>{fmtMoney(blendedCPC)}</div>
                  <div style={tileSub}>across all paid clicks</div>
                </div>

                <div className="card" style={tileBase}>
                  <div style={tileLbl}>Blended CTR</div>
                  <div style={{...tileNum, fontSize:'clamp(22px, 2vw, 28px)'}}>{fmtPct(blendedCTR)}</div>
                  <div style={{...tileSub,
                    color: ctrDelta == null ? 'var(--ink-3)'
                      : ctrGood ? 'var(--positive)' : 'var(--danger)'
                  }}>
                    {ctrDelta == null
                      ? 'no benchmark set'
                      : `${ctrDelta > 0 ? '+' : ''}${ctrDelta.toFixed(0)}% vs ${ctrBench.toFixed(2)}% bench`}
                  </div>
                </div>

                <div className="card" style={tileBase}>
                  <div style={tileLbl}>Video Completion</div>
                  <div style={{...tileNum, fontSize:'clamp(22px, 2vw, 28px)'}}>
                    {vcr != null ? fmtPct(vcr) : '—'}
                  </div>
                  <div style={tileSub}>
                    {vcr == null
                      ? 'no video starts yet'
                      : `${window.fmt.numFull(totalP100)} of ${window.fmt.numFull(totalVideoStarts)} starts`}
                  </div>
                </div>

                <div className="card" style={tileBase}>
                  <div style={tileLbl}>Avg View Duration</div>
                  <div style={{...tileNum, fontSize:'clamp(22px, 2vw, 28px)'}}>
                    {avgViewSec != null ? `${avgViewSec.toFixed(1)}s` : '—'}
                  </div>
                  <div style={tileSub}>
                    {avgViewSec != null
                      ? `${window.fmt.numFull(Math.round(totalWatchMin))} min watched`
                      : '—'}
                  </div>
                </div>

                <div className="card" style={tileBase}>
                  <div style={tileLbl}>Frequency</div>
                  <div style={{...tileNum, fontSize:'clamp(22px, 2vw, 28px)'}}>
                    {frequency != null ? `${frequency.toFixed(2)}×` : '—'}
                  </div>
                  <div style={tileSub}>
                    {frequency != null ? `avg views per reached user` : '—'}
                  </div>
                </div>
              </div>
            </>
          );
        })()}
      </div>

      {/* BY CHANNEL — paid efficiency per platform */}
      {channels.length > 0 && (
        <div className="sec">
          <div className="sec-h" style={{marginBottom:14}}>
            <div>
              <div className="sec-title">By <em>channel</em></div>
              <div className="sec-sub" style={{marginTop:4}}>
                Per-platform efficiency. CTR and CPC are the headline numbers for paid performance.
              </div>
            </div>
          </div>
          <div className="card" style={{padding:0, overflow:'hidden'}}>
            <div style={{
              display:'grid',
              gridTemplateColumns:'1.4fr 100px 90px 90px 130px 90px',
              gap:14, padding:'14px 22px',
              fontSize:10, fontFamily:'var(--mono)', color:'var(--ink-3)',
              letterSpacing:'0.1em', fontWeight:600, textTransform:'uppercase',
              borderBottom:'1px solid var(--line)', background:'var(--bg-soft)'
            }}>
              <div>Channel</div>
              <div style={{textAlign:'right'}}>Impr.</div>
              <div style={{textAlign:'right'}}>Spend</div>
              <div style={{textAlign:'right'}}>CPM</div>
              <div style={{textAlign:'right'}}>vs BrandX bench</div>
              <div style={{textAlign:'right'}}>ER</div>
            </div>
            {channels.map((ch, i) => {
              // Look up the BrandX per-platform CPM benchmark. Match by the
              // lowercased channel name with a couple of normalizations
              // (the channel name is "Facebook" / "Instagram"; benchmark
              // keys are lowercased).
              const bxBench = (window.BRANDX_BENCHMARKS || {}).cpmByPlatform || {};
              // Normalize "YouTube Shorts" → "youtubeShorts", "Facebook" →
              // "facebook" to match the camelCased benchmark keys.
              const lower = ch.name.toLowerCase();
              const snake = lower.replace(/\s+/g, '_');
              const camel = lower.replace(/\s+(.)/g, (_, c) => c.toUpperCase());
              const benchCpm = bxBench[camel] != null ? bxBench[camel] : bxBench[snake];
              const cpmDelta = (benchCpm && ch.cpm > 0) ? (ch.cpm - benchCpm) / benchCpm * 100 : null;
              const good = cpmDelta != null && cpmDelta <= 0;
              return (
              <div key={ch.name} style={{
                display:'grid',
                gridTemplateColumns:'1.4fr 100px 90px 90px 130px 90px',
                gap:14, padding:'14px 22px', alignItems:'center', fontSize:13,
                borderBottom: i < channels.length - 1 ? '1px solid var(--line)' : 'none'
              }}>
                <div style={{display:'flex', alignItems:'center', gap:8}}>
                  <span style={{width:8, height:8, borderRadius:'50%', background:ch.color}}/>
                  <span style={{fontWeight:500}}>{ch.name}</span>
                </div>
                <div style={{textAlign:'right', fontVariantNumeric:'tabular-nums', fontWeight:600}}>{window.fmt.numFull(ch.impressions)}</div>
                <div style={{textAlign:'right', fontVariantNumeric:'tabular-nums'}}>{fmtMoney(((ch.cpm || 0) * ch.impressions / 1000).toFixed(0))}</div>
                <div style={{textAlign:'right', fontVariantNumeric:'tabular-nums'}}>{ch.cpm > 0 ? fmtMoney(ch.cpm.toFixed(2)) : '—'}</div>
                <div style={{textAlign:'right', fontVariantNumeric:'tabular-nums', fontSize:11,
                  color: cpmDelta == null ? 'var(--ink-3)' : (good ? 'var(--positive)' : 'var(--danger)')}}>
                  {benchCpm == null
                    ? '—'
                    : cpmDelta == null
                      ? `$${benchCpm.toFixed(2)} bench`
                      : `${cpmDelta > 0 ? '+' : ''}${cpmDelta.toFixed(0)}% vs $${benchCpm.toFixed(2)}`}
                </div>
                <div style={{textAlign:'right', fontVariantNumeric:'tabular-nums'}}>{fmtPct(ch.er)}</div>
              </div>
              );
            })}
          </div>
        </div>
      )}

      {/* POST-LEVEL PERFORMANCE — every paid asset */}
      {posts.length > 0 && (
        <div className="sec">
          <div className="sec-h" style={{marginBottom:14}}>
            <div>
              <div className="sec-title">Post-level <em>performance</em></div>
              <div className="sec-sub" style={{marginTop:4}}>
                Every paid asset in the campaign. Sortable columns coming next pass — for now sorted by impressions descending.
              </div>
            </div>
          </div>
          <div className="card" style={{padding:0, overflow:'hidden'}}>
            <div style={{overflowX:'auto'}}>
              <div style={{minWidth: 1220}}>
                {/* Header. Watch min was dropped (only FB Reels populate it
                    natively; IG is estimated and the raw min count isn't
                    useful at the per-post grain). 100% Vw was replaced with
                    AVD — the per-post average view duration in seconds,
                    derived from watchTimeMin * 60 / videoViews3s. */}
                <div style={{
                  display:'grid',
                  gridTemplateColumns:'2fr 100px 70px 70px 70px 80px 70px 70px 70px 70px',
                  gap:10, padding:'12px 22px',
                  fontSize:10, fontFamily:'var(--mono)', color:'var(--ink-3)',
                  letterSpacing:'0.08em', fontWeight:600, textTransform:'uppercase',
                  borderBottom:'1px solid var(--line)', background:'var(--bg-soft)'
                }}>
                  <div>Post</div>
                  <div>Platform</div>
                  <div style={{textAlign:'right'}}>Impr.</div>
                  <div style={{textAlign:'right'}}>Views</div>
                  <div style={{textAlign:'right'}}>Reach</div>
                  <div style={{textAlign:'right'}}>Spend</div>
                  <div style={{textAlign:'right'}}>AVD</div>
                  <div style={{textAlign:'right'}}>Clicks</div>
                  <div style={{textAlign:'right'}}>CTR</div>
                  <div style={{textAlign:'right'}}>CPC / CPM</div>
                </div>
                {[...posts]
                  .sort((a, b) => (b.impr || 0) - (a.impr || 0))
                  .map((p, i, arr) => {
                    const title = p.title || '(no text)';
                    const clip = title.length > 95 ? title.slice(0, 95) + '…' : title;
                    const postAvd = (p.watchTimeMin && p.videoViews3s)
                      ? (p.watchTimeMin * 60 / p.videoViews3s)
                      : null;
                    return (
                      <a key={i}
                         href={p.url || '#'}
                         target={p.url ? '_blank' : undefined}
                         rel={p.url ? 'noopener noreferrer' : undefined}
                         style={{
                           display:'grid',
                           gridTemplateColumns:'2fr 100px 70px 70px 70px 80px 70px 70px 70px 70px',
                           gap:10, padding:'14px 22px', alignItems:'center', fontSize:12,
                           textDecoration:'none', color:'inherit',
                           borderBottom: i < arr.length - 1 ? '1px solid var(--line)' : 'none',
                           cursor: p.url ? 'pointer' : 'default'
                         }}>
                        <div style={{minWidth:0, overflow:'hidden', textOverflow:'ellipsis'}}>{clip}</div>
                        <div><PlatformPill name={p.platform}/></div>
                        <div style={{textAlign:'right', fontVariantNumeric:'tabular-nums', fontWeight:600}}>{fmtNum(p.impr)}</div>
                        <div style={{textAlign:'right', fontVariantNumeric:'tabular-nums'}}>{fmtNum(p.views)}</div>
                        <div style={{textAlign:'right', fontVariantNumeric:'tabular-nums'}}>{fmtNum(p.reach)}</div>
                        <div style={{textAlign:'right', fontVariantNumeric:'tabular-nums'}}>{fmtMoney(p.spend && p.spend.toFixed(2))}</div>
                        <div style={{textAlign:'right', fontVariantNumeric:'tabular-nums'}}>{postAvd != null ? `${postAvd.toFixed(1)}s` : '—'}</div>
                        <div style={{textAlign:'right', fontVariantNumeric:'tabular-nums', fontWeight:600}}>{fmtNum(p.clicks)}</div>
                        <div style={{textAlign:'right', fontVariantNumeric:'tabular-nums'}}>{p.ctr != null ? fmtPct(p.ctr) : '—'}</div>
                        <div style={{textAlign:'right', fontVariantNumeric:'tabular-nums', fontSize:11, color:'var(--ink-2)'}}>
                          {p.cpc != null ? `${fmtMoney(p.cpc.toFixed(2))}` : '—'}
                          <span style={{color:'var(--ink-3)'}}> · </span>
                          {p.cpm != null ? `${fmtMoney(p.cpm.toFixed(2))}` : '—'}
                        </div>
                      </a>
                    );
                  })}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

window.CampaignPage = CampaignPage;
