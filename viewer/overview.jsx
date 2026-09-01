/* global React, CAMPAIGNS, TOP_POSTS, TOP_POSTS_ORGANIC, HERO_POST, CHANNELS, FORMATS, MONTHLY_DELIVERY, SOURCES, fmt,
   Ic, PlatformPill, PageHead, CampaignCard, WrappedCard, MultiLineChart, Donut, BarChart, PLATFORM_COLORS, PaceBar */
const { useState: useStateO } = React;

// ============================================================
// DATA HEALTH BANNER
// Surfaces silent-failure modes (uploaded-but-unread files, skipped campaigns,
// missing files, Measure errors) so "I uploaded X and nothing happened" can
// never go unnoticed again. Renders nothing when all is well.
// ============================================================
function HealthBanner() {
  const [open, setOpen] = useStateO(false);
  const dh = (typeof window !== 'undefined' && window.DATA_HEALTH) || {};
  const warns = dh.generatedWarnings || [];
  const orphans = dh.orphanFiles || [];
  const msErrors = dh.msErrors || [];
  const duplicates = dh.potentialDuplicates || [];

  // Classify the free-text warnings. "excluded N posts" is normal/expected —
  // don't alarm on it. "SKIPPED" = a campaign fell out of the dashboard.
  const skipped = warns.filter(w => /SKIPPED/i.test(w));
  const missing = warns.filter(w => /missing .*file/i.test(w));

  const critical = skipped.length + msErrors.length + duplicates.length;
  const attention = orphans.length + missing.length;
  const total = critical + attention;
  if (total === 0) return null;

  const tone = critical > 0 ? '#DE6B38' : '#FF9947';
  const Row = ({ label, items, hint }) => items.length === 0 ? null : (
    <div style={{marginTop:12}}>
      <div style={{fontSize:12, fontWeight:600, color:'var(--ink)', marginBottom:4}}>{label}</div>
      {hint && <div style={{fontSize:12, color:'var(--ink-3)', marginBottom:6}}>{hint}</div>}
      <ul style={{margin:0, paddingLeft:18}}>
        {items.map((it, i) => (
          <li key={i} style={{fontSize:12.5, color:'var(--ink-2)', fontFamily:'var(--mono)', lineHeight:1.7, wordBreak:'break-all'}}>{it}</li>
        ))}
      </ul>
    </div>
  );

  return (
    <div className="sec" style={{marginTop:4}}>
      <div className="card" style={{padding:'14px 18px', borderLeft:`3px solid ${tone}`}}>
        <div style={{display:'flex', alignItems:'center', justifyContent:'space-between', gap:12}}>
          <div style={{fontSize:13.5, color:'var(--ink)'}}>
            <strong style={{color:tone}}>Data health</strong> — {total} item{total===1?'':'s'} need{total===1?'s':''} attention
            {critical > 0 && <span style={{color:'#DE6B38'}}> · {critical} critical</span>}
          </div>
          <button onClick={() => setOpen(o => !o)} style={{
            background:'transparent', border:'1px solid var(--line)', borderRadius:6,
            padding:'5px 12px', fontFamily:'var(--mono)', fontSize:11, letterSpacing:'0.04em',
            color:'var(--ink-2)', cursor:'pointer', textTransform:'uppercase', whiteSpace:'nowrap',
          }}>{open ? 'Hide' : 'Details'}</button>
        </div>
        {open && (
          <div style={{marginTop:6, borderTop:'1px solid var(--line)', paddingTop:6}}>
            <Row label="Campaigns dropped (config error)" items={skipped}
                 hint="These campaigns hit a config error and were left off the dashboard. Fix the config to bring them back."/>
            <Row label="Possible double-counts" items={duplicates}
                 hint="An uploaded export looks like it overlaps posts already tracked in Measure — the totals may be inflated. Remove the duplicate upload (or confirm the posts really are distinct)."/>
            <Row label="Measure Studio errors" items={msErrors}
                 hint="Data is incomplete for these — re-run the refresh, or upload a manual CSV."/>
            <Row label="Uploaded files not being used" items={orphans}
                 hint="These files are in the repo but no campaign reads them — usually an export that landed under an off-convention name. Re-upload it via the campaign's own card on Add Campaign Data, or it's a stale/duplicate you can ignore."/>
            <Row label="Expected files missing" items={missing}
                 hint="A campaign is configured to read these, but the file isn't there yet — upload it via that campaign's card."/>
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================
// WRAPPED PAGE — finished campaigns, kept off the main Overview so the live
// dashboard stays light. Final delivery only; no live pacing.
// ============================================================
function WrappedPage({ onOpenCampaign }) {
  const wrapped = CAMPAIGNS.filter(c => c.lifecycle === 'wrapped');
  const totalImpr = wrapped.reduce((s, c) => s + (c.impressions?.delivered || 0), 0);
  const totalBudget = wrapped.reduce((s, c) => s + (c.budget?.delivered || 0), 0);
  // Count how many hit their impression goal, for a one-line scoreboard.
  const hitGoal = wrapped.filter(c => (c.impressions?.delivered || 0) >= (c.impressions?.goal || Infinity)).length;

  return (
    <>
      <PageHead
        overline="Sponsored campaigns · archive"
        title="Wrapped"
        italic="campaigns"
        sub={wrapped.length === 0
          ? <>No wrapped campaigns yet — finished flights will collect here.</>
          : <>{wrapped.length} finished flight{wrapped.length === 1 ? '' : 's'} · {fmt.num(totalImpr)} impressions delivered · {hitGoal} of {wrapped.length} hit goal.</>}
      />

      {wrapped.length > 0 && (
        <div className="sec">
          <div className="sec-h">
            <div>
              <div className="sec-title">Final <em>delivery</em></div>
              <div className="sec-sub" style={{marginTop:6}}>Campaigns that have ended. Numbers are frozen at wrap; click any card for the full breakdown.</div>
            </div>
          </div>
          <div style={{display:'grid', gridTemplateColumns:'repeat(4, 1fr)', gap:14}}>
            {wrapped.map(c => (
              <WrappedCard key={c.id} c={c} onClick={() => onOpenCampaign(c.id)}/>
            ))}
          </div>
        </div>
      )}
    </>
  );
}

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
  // Wrapped campaigns are not part of the "active" cohort — they have their own
  // Recently Wrapped section. Header counts and "needs attention" pulls only
  // from active campaigns.
  const activeOnly = CAMPAIGNS.filter(c => (c.lifecycle || 'active') === 'active');
  const activeCount = activeOnly.length;
  // Campaigns that need attention, worst first (danger before warn). Named
  // explicitly in a strip below so the header count is actionable, not abstract.
  const attnCampaigns = activeOnly
    .filter(c => c.statusKind === 'danger' || c.statusKind === 'warn')
    .sort((a, b) => (a.statusKind === 'danger' ? 0 : 1) - (b.statusKind === 'danger' ? 0 : 1));
  const needsAttn = attnCampaigns.length;

  return (
    <>
      <PageHead
        overline={`Sponsored campaigns · ${new Date().toLocaleString('en-US', { month: 'long', year: 'numeric' })}`}
        title="Good"
        italic={greetItalic}
        sub={<>{activeCount} active campaign{activeCount === 1 ? '' : 's'} · <strong>{needsAttn} need{needsAttn === 1 ? 's' : ''} attention</strong>.</>}
        actions={<>
          <div className="search">
            <Ic.search/><input placeholder="Search campaigns, posts, partners…"/>
          </div>
          <button className="btn btn-acc"><Ic.download/> Export</button>
        </>}
      />

      <HealthBanner/>

      {/* NEEDS ATTENTION — names the campaigns behind the header count so it's
          actionable. Click through to the campaign. Danger (red) first. */}
      {attnCampaigns.length > 0 && (
        <div className="sec" style={{marginTop:4}}>
          <div style={{display:'flex', flexWrap:'wrap', gap:10, alignItems:'center'}}>
            <span style={{fontFamily:'var(--mono)', fontSize:11, letterSpacing:'0.06em', textTransform:'uppercase', color:'var(--ink-3)', marginRight:2}}>Needs attention</span>
            {attnCampaigns.map(c => {
              const danger = c.statusKind === 'danger';
              const dot = danger ? '#DE6B38' : '#FF9947';
              return (
                <button key={c.id} onClick={() => onOpenCampaign(c.id)} style={{
                  display:'inline-flex', alignItems:'center', gap:8,
                  background:'var(--surface)', border:'1px solid var(--line)',
                  borderLeft:`3px solid ${dot}`, borderRadius:'var(--r-md)',
                  padding:'7px 12px', cursor:'pointer', fontFamily:'inherit', fontSize:13,
                }}>
                  <span style={{fontWeight:600, color:'var(--ink)'}}>{c.partner}</span>
                  <span style={{color:'var(--ink-3)'}}>·</span>
                  <span style={{color:dot, fontWeight:600, fontSize:12}}>{c.status}</span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* TOP-OF-DASH CALLOUTS — pulled from per-campaign auto-callouts.
          Capped at the top 4 (already ranked by the pipeline) so the strip
          stays a single clean 4-wide row instead of wrapping a lone tile to a
          second row. Lower-priority callouts still surface on each campaign's
          own page. */}
      {(SIGNALS && SIGNALS.length > 0) && (() => {
      const shownSignals = SIGNALS.slice(0, 4);
      return (
      <div className="sec" style={{marginTop: 4}}>
        <div className="sec-h">
          <div>
            <div className="sec-title">Pulse <em>check</em></div>
            <div className="sec-sub" style={{marginTop:6}}>The most important things to know across your active campaigns — auto-flagged from current performance.</div>
          </div>
        </div>
        <div style={{display:'grid', gridTemplateColumns:`repeat(${Math.min(shownSignals.length, 4)}, minmax(0, 1fr))`, gap:14}}>
          {shownSignals.map((co, i) => {
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
      );
      })()}

      {/* CAMPAIGN GRID — active only. Wrapped campaigns live on their own
          "Wrapped" page (lighter Overview, fewer cards to load here). */}
      {(() => {
        const activeCampaigns = CAMPAIGNS.filter(c => (c.lifecycle || 'active') === 'active');
        const wrappedCount = CAMPAIGNS.filter(c => c.lifecycle === 'wrapped').length;
        return (
          <div className="sec">
            <div className="sec-h">
              <div>
                <div className="sec-title">Active <em>campaigns</em></div>
                <div className="sec-sub" style={{marginTop:6}}>
                  Pacing across impressions and budget for every live flight.
                  {wrappedCount > 0 && <> {wrappedCount} wrapped campaign{wrappedCount === 1 ? '' : 's'} live on the <strong>Wrapped</strong> page.</>}
                </div>
              </div>
            </div>
            <div style={{display:'grid', gridTemplateColumns:'repeat(3, 1fr)', gap:16}}>
              {activeCampaigns.map(c => (
                <CampaignCard key={c.id} c={c} onClick={() => onOpenCampaign(c.id)}/>
              ))}
            </div>
          </div>
        );
      })()}



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
              <a key={p.id} href={p.url || '#'}
                 target={p.url ? '_blank' : undefined}
                 rel={p.url ? 'noopener noreferrer' : undefined}
                 style={{
                display:'grid',
                gridTemplateColumns:'24px 1fr 90px 70px',
                gap:10, padding:'14px 24px', alignItems:'center',
                borderBottom:'1px solid var(--line)',
                textDecoration:'none', color:'inherit', fontSize:13,
                cursor: p.url ? 'pointer' : 'default'
              }}>
                <div style={{fontFamily:'var(--mono)', fontSize:11, color:'var(--ink-3)', fontWeight:600}}>{String(p.rank).padStart(2,'0')}</div>
                <div style={{display:'flex', flexDirection:'column', gap:4, minWidth:0}}>
                  <div style={{display:'flex', alignItems:'center', gap:8}}>
                    <strong style={{fontSize:11, color:'var(--ink)'}}>{p.partner}</strong>
                    <PlatformPill name={p.platform}/>
                  </div>
                  <div style={{fontSize:12, color:'var(--ink-2)', lineHeight:1.35, overflow:'hidden', textOverflow:'ellipsis', display:'-webkit-box', WebkitLineClamp:2, WebkitBoxOrient:'vertical'}}>{p.quote}</div>
                </div>
                <div style={{textAlign:'right', fontVariantNumeric:'tabular-nums', fontWeight:600, fontSize:13}}>{fmt.num(p.reach)}</div>
                <div style={{textAlign:'right', fontVariantNumeric:'tabular-nums', fontWeight:600, fontSize:13}}>{p.er.toFixed(2)}<span style={{fontSize:10, color:'var(--ink-3)', marginLeft:1}}>%</span></div>
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
              <a key={p.id} href={p.url || '#'}
                 target={p.url ? '_blank' : undefined}
                 rel={p.url ? 'noopener noreferrer' : undefined}
                 style={{
                display:'grid',
                gridTemplateColumns:'24px 1fr 100px 70px',
                gap:10, padding:'14px 24px', alignItems:'center',
                borderBottom:'1px solid var(--line)',
                textDecoration:'none', color:'inherit', fontSize:13,
                cursor: p.url ? 'pointer' : 'default'
              }}>
                <div style={{fontFamily:'var(--mono)', fontSize:11, color:'var(--ink-3)', fontWeight:600}}>{String(p.rank).padStart(2,'0')}</div>
                <div style={{display:'flex', flexDirection:'column', gap:4, minWidth:0}}>
                  <div style={{display:'flex', alignItems:'center', gap:8}}>
                    <strong style={{fontSize:11, color:'var(--ink)'}}>{p.partner}</strong>
                    <PlatformPill name={p.platform}/>
                  </div>
                  <div style={{fontSize:12, color:'var(--ink-2)', lineHeight:1.35, overflow:'hidden', textOverflow:'ellipsis', display:'-webkit-box', WebkitLineClamp:2, WebkitBoxOrient:'vertical'}}>{p.quote}</div>
                </div>
                <div style={{textAlign:'right', fontVariantNumeric:'tabular-nums', fontWeight:600, fontSize:13}}>{fmt.num(p.organicReach)}</div>
                <div style={{textAlign:'right', fontVariantNumeric:'tabular-nums', fontWeight:600, fontSize:13, color:'#2f7a3f'}}>{p.organicPct.toFixed(0)}%</div>
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

        {/* CPM BY CHANNEL — bench strip. Data from window.PORTFOLIO_CPM_BY_CHANNEL
            (live, recomputed on every refresh; YouTube subtype-split). */}
        {(() => {
          const cpmRows = (window.PORTFOLIO_CPM_BY_CHANNEL || []).filter(r => r.impressions > 0);
          const blend = window.PORTFOLIO_CPM_BLEND || 0;
          if (!cpmRows.length) return null;
          // Friendlier short names for the YT subtypes
          const shortName = (n) => n
            .replace('YouTube In-feed', 'YT In-feed')
            .replace('YouTube Pre-roll', 'YT In-stream')
            .replace('YouTube Shorts', 'YT Shorts');
          return (
            <div className="card" style={{padding:24, marginBottom:14}}>
              <div className="card-h" style={{marginBottom: 18}}>
                <div>
                  <div className="card-title-serif">Average CPM by channel</div>
                  <div className="card-sub">Blended across all active campaigns vs. Media Valuation Model benchmarks. Green = under MVM (more efficient than projected).</div>
                </div>
                <div style={{fontSize:11, fontFamily:'var(--mono)', color:'var(--ink-3)', letterSpacing:'0.06em'}}>
                  PORTFOLIO BLEND · ${blend.toFixed(2)}
                </div>
              </div>
              <div style={{display:'grid', gridTemplateColumns:`repeat(${cpmRows.length}, 1fr)`, gap:0, borderTop:'1px solid var(--line)'}}>
                {cpmRows.map((r, i, arr) => (
                  <div key={r.name} style={{
                    padding:'18px 14px',
                    borderRight: i < arr.length - 1 ? '1px solid var(--line)' : 'none',
                    display:'flex', flexDirection:'column', gap:6
                  }}>
                    <div style={{display:'flex', alignItems:'center', gap:8}}>
                      <span style={{width:8, height:8, borderRadius:'50%', background:r.color}}/>
                      <span style={{fontSize:11, color:'var(--ink-2)', fontWeight:500}}>{shortName(r.name)}</span>
                    </div>
                    <div style={{fontFamily:'var(--serif)', fontSize:26, fontWeight:300, color:'var(--ink)', letterSpacing:'-0.02em', lineHeight:1}}>
                      {r.cpm > 0 ? `$${r.cpm.toFixed(2)}` : '—'}
                    </div>
                    {/* vs Media Valuation Model benchmark — green = under
                        (more efficient than projected), red = over budget. */}
                    {r.mvmCpm != null && r.mvmDeltaPct != null ? (
                      <div style={{fontSize:10, fontFamily:'var(--mono)', letterSpacing:'0.04em',
                        color: r.mvmDeltaPct <= 0 ? 'var(--positive)' : 'var(--danger)'}}>
                        {r.mvmDeltaPct > 0 ? '+' : ''}{r.mvmDeltaPct.toFixed(0)}% vs MVM (${r.mvmCpm.toFixed(2)})
                      </div>
                    ) : r.mvmCpm != null ? (
                      <div style={{fontSize:10, fontFamily:'var(--mono)', letterSpacing:'0.04em', color:'var(--ink-3)'}}>
                        MVM target ${r.mvmCpm.toFixed(2)}
                      </div>
                    ) : (
                      <div style={{fontSize:10, fontFamily:'var(--mono)', letterSpacing:'0.04em', color:'var(--ink-3)'}}>—</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          );
        })()}

        {/* MVM TUNING SUGGESTIONS — flags platforms where the actual CPM has
            drifted enough from the MVM benchmark that the model should be
            refreshed for the next proposal cycle. Card only renders when at
            least one channel is materially off-target. */}
        {(() => {
          const rows = (window.PORTFOLIO_CPM_BY_CHANNEL || [])
            // Material drift: abs(delta) ≥ 15% AND ≥ 100K paid impressions
            // (volume floor — small samples drift too easily)
            .filter(r => r.mvmCpm != null
              && r.mvmDeltaPct != null
              && Math.abs(r.mvmDeltaPct) >= 15
              && (r.paidImpressions || 0) >= 100_000)
            .sort((a, b) => Math.abs(b.mvmDeltaPct) - Math.abs(a.mvmDeltaPct));
          if (!rows.length) return null;
          const shortName = (n) => n
            .replace('YouTube In-feed', 'YT In-feed')
            .replace('YouTube Pre-roll', 'YT In-stream')
            .replace('YouTube Shorts', 'YT Shorts');
          return (
            <div className="card" style={{padding:24, marginBottom:14, borderLeft:'3px solid var(--accent)'}}>
              <div className="card-h" style={{marginBottom: 14}}>
                <div>
                  <div className="card-title-serif">MVM tuning suggestions</div>
                  <div className="card-sub">
                    Channels where actual delivery has drifted ≥ 15% from the Media Valuation Model benchmark on ≥ 100K paid impressions.
                    Refresh these rates in the MVM so the next proposal projects accurately.
                  </div>
                </div>
              </div>
              <div style={{display:'flex', flexDirection:'column', gap:10}}>
                {rows.map(r => {
                  const direction = r.mvmDeltaPct < 0 ? 'below' : 'above';
                  const directionColor = r.mvmDeltaPct < 0 ? 'var(--positive)' : 'var(--danger)';
                  const absPct = Math.abs(r.mvmDeltaPct).toFixed(0);
                  const imprFmt = (window.fmt && window.fmt.num) ? window.fmt.num(r.paidImpressions) : r.paidImpressions.toLocaleString();
                  return (
                    <div key={r.name} style={{
                      display:'grid',
                      gridTemplateColumns:'140px 1fr',
                      gap:14, padding:'12px 14px',
                      background:'var(--bg-soft)',
                      borderRadius:6
                    }}>
                      <div style={{display:'flex', alignItems:'center', gap:8}}>
                        <span style={{width:8, height:8, borderRadius:'50%', background:r.color}}/>
                        <span style={{fontSize:13, fontWeight:600, color:'var(--ink)'}}>{shortName(r.name)}</span>
                      </div>
                      <div style={{fontSize:13, color:'var(--ink-2)', lineHeight:1.45}}>
                        Update from <strong style={{color:'var(--ink)'}}>${r.mvmCpm.toFixed(2)}</strong>
                        {' → '}
                        <strong style={{color:'var(--ink)'}}>${r.cpm.toFixed(2)}</strong>.
                        Tracking <span style={{color:directionColor, fontWeight:600}}>{absPct}% {direction}</span> projection on {imprFmt} paid impressions.
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })()}

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
