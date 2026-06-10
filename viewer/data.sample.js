// ============================================================
// DATA — Front Office Sports content campaigns
// ============================================================
window.CAMPAIGNS = [
  {
    id: 'adp',
    partner: 'ADP',
    series: 'Future of Sports',
    seriesItalic: 'Sports',
    flight: 'Oct 1, 2025 — May 31, 2026',
    elapsedPct: 89.3,
    daysLeft: 26,
    status: 'On Track',
    statusKind: 'on',
    impressions: { delivered: 5_910_000, goal: 6_600_000 },
    budget: { delivered: 7240, goal: 10916 },
    color: 'ft-1',
    leadFormat: 'Longform Video',
    topChannel: 'YouTube',
    er: 4.6,
    cpm: 0.51,
    episodes: 3,
    posts: 24,
    blurb: 'Three-episode interview series with HR & sports execs. Strong organic resonance on LinkedIn.'
  },
  {
    id: 'etrade',
    partner: 'E*TRADE',
    series: 'Portfolio Players',
    seriesItalic: 'Players',
    flight: 'Jan 1 — Jun 30, 2026',
    elapsedPct: 70.1,
    daysLeft: 56,
    status: 'Behind Pace',
    statusKind: 'danger',
    impressions: { delivered: 13_780_000, goal: 45_000_000 },
    budget: { delivered: 22798, goal: 50000 },
    color: 'ft-3',
    leadFormat: 'Longform Video',
    topChannel: 'YouTube',
    er: 4.2,
    cpm: 0.53,
    episodes: 7,
    posts: 32,
    blurb: 'Sports ownership & investing series. Mark Cuban teaser is generating organic buzz ahead of launch.'
  },
  {
    id: 'tastytrade',
    partner: 'TastyTrade',
    series: 'The Come Up',
    seriesItalic: 'Come Up',
    flight: 'Mar 1 — Apr 20, 2026',
    elapsedPct: 100,
    daysLeft: 0,
    status: 'Goal Exceeded',
    statusKind: 'on',
    impressions: { delivered: 2_756_799, goal: 2_280_000 },
    budget: { delivered: 8054, goal: 8500 },
    color: 'ft-2',
    leadFormat: 'Episodic Video',
    topChannel: 'YouTube Shorts',
    er: 15.1,
    cpm: 4.32,
    episodes: 4,
    posts: 18,
    blurb: 'March Madness episodic series across 5 platforms. Delivered 121% of goal on 95% of budget. Ep 4 (Fudd) added post-contract.'
  },
  {
    id: 'usbank',
    partner: 'US Bank',
    series: 'NFL Draft',
    seriesItalic: 'Draft',
    flight: 'Apr 21 — May 15, 2026',
    elapsedPct: 100,
    daysLeft: 0,
    status: 'Goal Exceeded',
    statusKind: 'on',
    impressions: { delivered: 15_000_000, goal: 14_000_000 },
    budget: { delivered: 30986, goal: 31375 },
    color: 'ft-4',
    leadFormat: 'Made for Social',
    topChannel: 'Instagram',
    er: 8.5,
    cpm: 5.07,
    episodes: 3,
    posts: 38,
    blurb: '3 social components, 38 posts live across IG, FB, X, LinkedIn & YouTube Shorts. Delivered 103.6% of impression goal on 98.8% of budget.'
  },
];

// Top performing assets — by Engagement Rate
window.TOP_POSTS = [
  {
    id: 1, rank: 1, partner: 'TastyTrade', platform: 'TikTok', format: 'Short video',
    quote: 'Ben McCollum turned down a bank job to start coaching…',
    er: 10.36, eng: 7558, reach: 72_969, organic: 100,
    metric: 'er',
    insight: 'Highest ER across all posts — pure organic TikTok resonance.'
  },
  {
    id: 2, rank: 2, partner: 'TastyTrade', platform: 'Instagram', format: 'Reel',
    quote: 'Braylon Mullins went from a single D1 offer to leading UCONN to the Final Four',
    er: 9.95, eng: 26_135, reach: 262_761, organic: 18,
    metric: 'er',
    insight: 'Highest ER of any IG post across both campaigns — UCONN storyline resonated.'
  },
  {
    id: 3, rank: 3, partner: 'ADP', platform: 'LinkedIn', format: 'Image post',
    quote: '"You have to be overly prepared, overly thorough, incredibly competent."',
    er: 6.85, eng: 591, reach: 8_627, organic: 100,
    metric: 'er',
    insight: 'Kim Ng quote — highest ER of any LinkedIn post on ADP.'
  },
  {
    id: 4, rank: 4, partner: 'E*TRADE', platform: 'LinkedIn', format: 'Image post',
    quote: '"There is so much capital that wants to come into sports…"',
    er: 5.38, eng: 746, reach: 13_861, organic: 100,
    metric: 'er',
    insight: '100% organic LinkedIn — zero spend.'
  },
  {
    id: 5, rank: 5, partner: 'ADP', platform: 'LinkedIn', format: 'Image post',
    quote: 'Kim Ng made history as the first woman to serve as General Manager…',
    er: 6.14, eng: 947, reach: 15_428, organic: 100,
    metric: 'er',
    insight: 'Sustained 6%+ ER on Future of Sports series.'
  },
  {
    id: 6, rank: 6, partner: 'TastyTrade', platform: 'LinkedIn', format: 'Image post',
    quote: 'Ben McCollum turned down a bank job to start coaching…',
    er: 4.72, eng: 1847, reach: 39_126, organic: 100,
    metric: 'er',
    insight: 'Ep 2 LinkedIn — consistent 4–5% ER on zero spend.'
  },
  {
    id: 7, rank: 7, partner: 'E*TRADE', platform: 'LinkedIn', format: 'Image post',
    quote: '50–100x returns in sports ownership. AI-proof assets…',
    er: 5.00, eng: 781, reach: 15_619, organic: 100,
    metric: 'er',
    insight: 'Mark Cuban teaser driving organic LinkedIn buzz.'
  },
  {
    id: 8, rank: 8, partner: 'US Bank', platform: 'Instagram', format: 'Reel',
    quote: 'NFL Draft Day — behind the scenes with the rookies',
    er: 4.20, eng: 4_180, reach: 99_500, organic: 12,
    metric: 'er',
    insight: 'Strong Meta paid amplification on NFL Draft content.'
  }
];

window.HERO_POST = {
  partner: 'TastyTrade', platform: 'TikTok', format: '100% organic short video',
  quote: 'Ben McCollum turned down a bank job to start coaching.',
  attribution: 'Ep 2: Iowa → Sweet 16 — The Come Up',
  er: '10.36%',
  eng: '7,558',
  reach: '72,969',
  organic: '100%'
};

// Top performing assets — by Organic Reach (highest organic views/impressions)
window.TOP_POSTS_ORGANIC = [
  {
    id: 'o1', rank: 1, partner: 'TastyTrade', platform: 'Instagram', format: 'Reel',
    quote: 'After taking over a 4–28 Siena program and leading them to March Madness…',
    organicReach: 79_268, totalReach: 555_506, organicPct: 14.3, er: 3.50,
    insight: 'Ep 1 Instagram organic blowout — highest raw organic volume.'
  },
  {
    id: 'o2', rank: 2, partner: 'TastyTrade', platform: 'TikTok', format: 'Short video',
    quote: 'Ben McCollum turned down a bank job to start coaching…',
    organicReach: 72_969, totalReach: 72_969, organicPct: 100, er: 10.36,
    insight: '100% organic — pure algorithmic distribution on TikTok.'
  },
  {
    id: 'o3', rank: 3, partner: 'TastyTrade', platform: 'Instagram', format: 'Reel',
    quote: 'Ben McCollum turned down a bank job to start coaching…',
    organicReach: 31_932, totalReach: 287_631, organicPct: 11.1, er: 4.32,
    insight: 'Ep 2 IG — 31K organic on paid-amplified content.'
  },
  {
    id: 'o4', rank: 4, partner: 'TastyTrade', platform: 'YouTube', format: 'Shorts',
    quote: 'Ben McCollum — Iowa to the Sweet 16',
    organicReach: 30_064, totalReach: 190_341, organicPct: 15.8, er: 4.10,
    insight: 'Ep 2 YouTube Shorts — strongest organic Shorts performance.'
  },
  {
    id: 'o5', rank: 5, partner: 'TastyTrade', platform: 'TikTok', format: 'Short video',
    quote: 'After taking over a 4–28 Siena program…',
    organicReach: 29_786, totalReach: 87_950, organicPct: 33.9, er: 0.48,
    insight: 'Ep 1 TikTok — 33% organic lift alongside paid amplification.'
  },
  {
    id: 'o6', rank: 6, partner: 'ADP', platform: 'LinkedIn', format: 'Image post',
    quote: '"You have to be overly prepared, overly thorough, incredibly competent."',
    organicReach: 8_627, totalReach: 8_627, organicPct: 100, er: 6.85,
    insight: 'Kim Ng quote — 100% organic LinkedIn.'
  }
];

// Cross-campaign blended channel performance
window.CHANNELS = [
  { name: 'YouTube', italic: 'Tube', impressions: 9_098_000, eng: 768_000, er: 8.4, cpm: 1.21, color: '#E00922', delta: 12, bench: { er: 4.2, cpm: 4.50 } },
  { name: 'Instagram', italic: 'gram', impressions: 2_982_000, eng: 88_534, er: 2.97, cpm: 5.03, color: '#E4405F', delta: 4, bench: { er: 1.8, cpm: 5.10 } },
  { name: 'TikTok', italic: 'Tok', impressions: 2_002_000, eng: 78_478, er: 3.92, cpm: 1.94, color: '#000000', delta: 18, bench: { er: 2.0, cpm: 2.40 } },
  { name: 'LinkedIn', italic: 'LinkedIn', impressions: 561_319, eng: 24_111, er: 4.30, cpm: 0, color: '#0A66C2', delta: 6, bench: { er: 3.5, cpm: 0 } },
  { name: 'X', italic: 'X', impressions: 1_230_000, eng: 14_500, er: 1.20, cpm: 0.93, color: '#1d1d1f', delta: -3, bench: { er: 1.1, cpm: 1.10 } }
];

window.FORMATS = [
  { name: 'Longform video', share: 56, impressions: 7_700_000, color: 'var(--flame)' },
  { name: 'Cutdowns', share: 22, impressions: 3_030_000, color: 'var(--orange)' },
  { name: 'Made for social', share: 14, impressions: 1_930_000, color: 'var(--sunshine)' },
  { name: 'Image / static', share: 6, impressions: 826_000, color: 'var(--blossom)' },
  { name: 'Editorial', share: 2, impressions: 275_000, color: 'var(--lilac)' }
];

window.MONTHLY_DELIVERY = [
  { m: 'Jan', adp: 510_000, etrade: 980_000, fid: 0, cisco: 0 },
  { m: 'Feb', adp: 760_000, etrade: 1_840_000, fid: 0, cisco: 1_120_000 },
  { m: 'Mar', adp: 920_000, etrade: 2_310_000, fid: 1_200_000, cisco: 1_840_000 },
  { m: 'Apr', adp: 1_440_000, etrade: 2_870_000, fid: 1_410_000, cisco: 1_960_000 },
  { m: 'May', adp: 1_680_000, etrade: 2_980_000, fid: 1_510_000, cisco: 1_880_000 }
];

window.SOURCES = [
  { name: 'Measure Studio', date: 'May 5, 2026', stale: false },
  { name: 'Google Ads', date: 'May 5, 2026', stale: false },
  { name: 'X Ads Manager', date: 'May 5, 2026', stale: false },
  { name: 'Meta Business', date: 'May 4, 2026', stale: false },
  { name: 'TikTok Ads', date: 'May 1, 2026', stale: true },
  { name: 'YouTube Studio', date: 'May 5, 2026', stale: false }
];


// Cross-campaign signals shown on the overview "Pulse check" strip
window.SIGNALS = [
  {
    kind: 'win',
    title: 'TikTok is your zero-cost reach engine',
    body: 'TastyTrade TikTok delivered 592K views on $267 in spend — 228% of contracted impressions at $1.94 CPM. 77% organic. Should be a default channel for every package.'
  },
  {
    kind: 'watch',
    title: 'E*TRADE pacing watch',
    body: '70% of flight elapsed but only 31% of impressions delivered. Mark Cuban episode launching this week should close the gap.'
  },
  {
    kind: 'opportunity',
    title: 'LinkedIn = free engagement',
    body: 'TastyTrade, ADP, and E*TRADE all hit 4%+ ER on LinkedIn at $0 spend. Default-include in every content package.'
  }
];

window.fmt = {
  num(n) {
    if (n >= 1_000_000) return (n / 1_000_000).toFixed(n >= 10_000_000 ? 0 : 1) + 'M';
    if (n >= 1_000) return (n / 1_000).toFixed(n >= 10_000 ? 0 : 1) + 'K';
    return n.toString();
  },
  numFull(n) { return Math.round(Number(n) || 0).toLocaleString('en-US'); },
  pct(n, d = 1) { return n.toFixed(d) + '%'; },
  money(n) {
    if (n >= 1_000) return '$' + (n / 1_000).toFixed(1) + 'K';
    return '$' + n.toLocaleString();
  },
  moneyFull(n) {
    const v = Number(n) || 0;
    return '$' + v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
};

// ============================================================
// US BANK — three social components (bespoke layout)
// ============================================================
window.UB_COMPONENTS = [
  {
    id: 'comeup',
    n: '01',
    title: 'The Come Up',
    italic: 'Up',
    sub: '4 Athlete Stories × 5 Platforms · 20 Posts Live',
    status: 'Goal Exceeded',
    statusKind: 'on',
    color: 'var(--orange)',
    fg: 'var(--liquorice)',
    accent: 'ft-1',
    impressions: { delivered: 8_410_825, goal: 8_000_000 },
    budget: { delivered: 22_743, goal: 16_875 },
    engagements: 306_409,
    er: 3.6,
    posts: 20,
    blurb: 'X paid drove 4.65M impressions at $1.54 CPM — the dominant reach driver. Meta delivered 2.65M IG+FB. YT Shorts 25.0% blended ER.',
    budgetNote: 'Budget reallocated from Native Social to support paid amplification after CPMs ran elevated during the busy draft window.',
    platforms: [
      { name: 'Instagram',     posts: 4, organic: 50_803,  paid: 1_717_115, total: 1_767_918, eng: 139_158, er: 7.9,  spend: 8_664.43, est: 7_102, pct: 122.0 },
      { name: 'Facebook',      posts: 4, organic: 35_023,  paid: 936_646,   total: 971_669,   eng: 16_177,  er: 1.7,  spend: 4_512.05, est: 3_721, pct: 121.3 },
      { name: 'X',             posts: 4, organic: 253_827, paid: 4_653_038, total: 4_906_865, eng: 4_938,   er: 0.10, spend: 7_180.00, est: 2_500, pct: 287.2 },
      { name: 'LinkedIn',      posts: 4, organic: 187_787, paid: null,      total: 187_787,   eng: 2_046,   er: 1.1,  spend: 0,        est: 0,     pct: null },
      { name: 'YouTube Shorts',posts: 4, organic: 179_914, paid: 396_672,   total: 576_586,   eng: 144_090, er: 25.0, spend: 2_386.88, est: 3_592, pct: 66.5  },
    ],
    stories: [
      {
        name: 'Mauigoa', kind: 'Non-Collab', published: '4/22',
        sub: 'OL · American Samoa → 5-Star IMG Prospect',
        reach: 2_747_650, eng: 76_932, spend: 6_235,
        rows: [
          { plat:'Instagram',     dist:'organic+paid', impr: 484_628,   eng: 39_924, er: 8.2,  spend: 2_163.30 },
          { plat:'Facebook',      dist:'organic+paid', impr: 271_956,   eng: 5_417,  er: 2.0,  spend: 1_129.95 },
          { plat:'X',             dist:'organic+paid', impr: 1_775_698, eng: 2_244,  er: 0.13, spend: 2_345.00 },
          { plat:'LinkedIn',      dist:'organic',      impr: 84_358,    eng: 733,    er: 0.9,  spend: 0 },
          { plat:'YouTube Shorts',dist:'organic+paid', impr: 131_010,   eng: 28_614, er: 21.8, spend: 596.82 },
        ],
        highlight: 'Highest reach story (2.75M). X paid delivered 1.64M at $1.43 CPM. IG at 8.2% ER. Non-collab leader.'
      },
      {
        name: 'Tate', kind: 'Non-Collab', published: '4/23',
        sub: 'WR · Tragedy → NFL Draft',
        reach: 1_974_102, eng: 92_016, spend: 5_537,
        rows: [
          { plat:'Instagram',     dist:'organic+paid', impr: 446_436,   eng: 35_221, er: 7.9,  spend: 2_165.46 },
          { plat:'Facebook',      dist:'organic+paid', impr: 229_036,   eng: 5_251,  er: 2.3,  spend: 1_129.98 },
          { plat:'X',             dist:'organic+paid', impr: 1_087_225, eng: 770,    er: 0.07, spend: 1_645.00 },
          { plat:'LinkedIn',      dist:'organic',      impr: 17_061,    eng: 85,     er: 0.5,  spend: 0 },
          { plat:'YouTube Shorts',dist:'organic+paid', impr: 194_344,   eng: 50_689, er: 26.1, spend: 596.17 },
        ],
        highlight: 'Highest engagement story (92K). YT Shorts 26.1% ER. IG 7.9%. Strongest emotional resonance.'
      },
      {
        name: 'Downs', kind: 'Collab', published: '4/23',
        sub: 'DB · Family of Pros → Carving His Own Name',
        reach: 1_919_294, eng: 52_634, spend: 5_542,
        rows: [
          { plat:'Instagram',     dist:'organic+paid', impr: 401_309,   eng: 11_778, er: 2.9,  spend: 2_167.70 },
          { plat:'Facebook',      dist:'organic+paid', impr: 232_187,   eng: 2_300,  er: 1.0,  spend: 1_129.98 },
          { plat:'X',             dist:'organic+paid', impr: 1_106_334, eng: 725,    er: 0.07, spend: 1_645.00 },
          { plat:'LinkedIn',      dist:'organic',      impr: 13_948,    eng: 44,     er: 0.3,  spend: 0 },
          { plat:'YouTube Shorts',dist:'organic+paid', impr: 165_516,   eng: 37_787, er: 22.8, spend: 599.51 },
        ],
        highlight: 'X paid at 1.1M impr. YT Shorts 22.8% ER. IG ER lower at 2.9% — collab format underperforming here.'
      },
      {
        name: 'Mendoza', kind: 'Collab', published: '4/21',
        sub: 'QB · Overlooked → Probable No. 1 Pick',
        reach: 1_769_779, eng: 84_827, spend: 5_429,
        rows: [
          { plat:'Instagram',     dist:'organic+paid', impr: 435_545,   eng: 52_235, er: 12.0, spend: 2_167.97 },
          { plat:'Facebook',      dist:'organic+paid', impr: 238_490,   eng: 3_209,  er: 1.3,  spend: 1_122.14 },
          { plat:'X',             dist:'organic+paid', impr: 937_608,   eng: 1_199,  er: 0.13, spend: 1_545.00 },
          { plat:'LinkedIn',      dist:'organic',      impr: 72_420,    eng: 1_184,  er: 1.6,  spend: 0 },
          { plat:'YouTube Shorts',dist:'organic+paid', impr: 85_716,    eng: 27_000, er: 31.5, spend: 594.38 },
        ],
        highlight: 'Highest IG ER (12.0% — 52K eng). YT Shorts 31.5% ER. Strongest collab story by engagement quality.'
      },
    ],
    callouts: [
      { kind:'pos', tag:'GOAL EXCEEDED', headline:'8.41M impressions delivered against 8M target (105.1%).', body:'All 4 stories above 1.7M. X paid drove 4.65M (55%); Meta delivered 2.65M IG+FB. 3.6% blended ER, 306K total engagements.' },
      { kind:'warn', tag:'BUDGET OVERSPEND', headline:'$22,743 spent of $16,875 contracted (134.8%). X at 287% of allocation.', body:'X spent $7,180 vs $2,500 allocated. IG at 122%, FB 121%. YT Shorts only platform under at 66.5%. Flag X overspend & 0.10% ER for future learnings.' },
      { kind:'pos', tag:'ENGAGEMENT LEADER', headline:'Tate is the engagement leader (92K) despite being last to publish.', body:'Driven by YT Shorts (51K eng, 26.1% ER) and IG (35K eng, 7.9% ER). Mauigoa leads reach at 2.75M via X paid. Both formats — collab and non-collab — worked for different reasons.' },
    ]
  },
  {
    id: 'native',
    n: '02',
    title: 'Native Social Coverage',
    italic: 'Coverage',
    sub: 'Draft Day editorial · 10 Posts Live · 4 Platforms',
    status: 'In Flight',
    statusKind: 'watch',
    color: 'var(--pear)',
    fg: 'var(--liquorice)',
    accent: 'ft-4',
    impressions: { delivered: 1_964_772, goal: 2_500_000 },
    budget: { delivered: 0, goal: 6_000 },
    engagements: 72_579,
    er: 3.7,
    posts: 10,
    blurb: 'Organic momentum strong — 78.6% of goal reached with $0 paid spend. IG is the powerhouse at 1.41M (72%, 4.0% ER). LinkedIn at 3.95% ER on 382K impr.',
    platforms: [
      { name: 'Instagram', posts: 3, organic: 1_412_517, paid: 0, total: 1_412_517, eng: 56_796, er: 4.02, spend: 0, est: null, pct: null },
      { name: 'Facebook',  posts: 1, organic: 135_356,   paid: 0, total: 135_356,   eng: 254,    er: 0.19, spend: 0, est: null, pct: null },
      { name: 'LinkedIn',  posts: 3, organic: 382_247,   paid: 0, total: 382_247,   eng: 15_087, er: 3.95, spend: 0, est: null, pct: null },
      { name: 'X',         posts: 3, organic: 34_652,    paid: 0, total: 34_652,    eng: 442,    er: 1.28, spend: 0, est: null, pct: null },
    ],
    callouts: [
      { kind:'pos', tag:'ORGANIC MOMENTUM', headline:'1.96M impressions from 10 posts on $0 spend (78.6% of 2.5M goal).', body:'Instagram is the powerhouse — 1.41M impr, 72% of total, 4.0% ER. LinkedIn delivering strong engagement at 3.95% ER. Continued organic posting through May 15 should close the 536K gap without deploying paid.' },
    ]
  },
  {
    id: 'redcarpet',
    n: '03',
    title: 'Red Carpet with Baker Machado',
    italic: 'Machado',
    sub: 'NFL Draft Red Carpet interviews · 2 Videos · 8 Posts Live',
    status: 'Goal Exceeded',
    statusKind: 'on',
    color: 'var(--flame)',
    fg: 'var(--paper)',
    accent: 'ft-6',
    impressions: { delivered: 4_130_182, goal: 3_500_000 },
    budget: { delivered: 8_242, goal: 8_500 },
    engagements: 195_662,
    er: 4.7,
    posts: 8,
    blurb: 'Red Carpet smashed its 3.5M goal with 4.13M delivered at 97% budget. X top reach (1.78M). YT Shorts strongest engagement (167K eng, 19.1% ER).',
    budgetNote: 'Budget reallocated from Native Social Coverage to support paid amplification after organic came in lower than expected.',
    videos: [
      {
        name: 'Video 1', dist: 'Organic + Paid',
        quote: '"Cars, homes, watches…"',
        rows: [
          { plat:'Instagram',     dist:'organic+paid', impr: 774_249, eng: 25_546,  er: 3.3,  spend: 1_887.11 },
          { plat:'Facebook',      dist:'organic',      impr: 6_327,   eng: 51,      er: 0.8,  spend: 0 },
          { plat:'X',             dist:'organic+paid', impr: 864_430, eng: 1_454,   er: 0.17, spend: 861.24 },
          { plat:'LinkedIn',      dist:'organic',      impr: 59_423,  eng: 294,     er: 0.5,  spend: 0 },
          { plat:'YouTube Shorts',dist:'organic+paid', impr: 327_627, eng: 114_309, er: 34.9, spend: 1_300.28 },
        ],
        subtotal: { impr: 2_032_056, eng: 141_654, er: 7.0, spend: 4_048.63 }
      },
      {
        name: 'Video 2', dist: 'Paid Only (Dark)',
        quote: '"Best financial advice…"',
        rows: [
          { plat:'Instagram',     dist:'paid', impr: 636_674, eng: 497,    er: 0.08, spend: 1_999.96 },
          { plat:'X',             dist:'paid', impr: 916_140, eng: 712,    er: 0.08, spend: 900.00 },
          { plat:'YouTube Shorts',dist:'paid', impr: 545_312, eng: 52_799, er: 9.7,  spend: 1_293.86 },
        ],
        subtotal: { impr: 2_098_126, eng: 54_008, er: 2.6, spend: 4_193.82 }
      }
    ],
    callouts: [
      { kind:'pos', tag:'GOAL EXCEEDED', headline:'4.13M impressions on $8,242 (118% of 3.5M target, 97% budget).', body:'X top reach driver (1.78M, 43%). YT Shorts strongest engagement at 167K / 19.1% ER. IG organic drove 336K views with 25.5K engagements. Blended CPM $2.00.' },
    ]
  },
];
window.UB_PLATFORM_CPMS = [
  { plat:'Instagram',      tasty: 4.99, ub: 5.07 },
  { plat:'Facebook',       tasty: 3.21, ub: 4.65 },
  { plat:'X',              tasty: null, ub: 1.54 },
  { plat:'LinkedIn',       tasty: 0,    ub: 0 },
  { plat:'YouTube Shorts', tasty: 4.10, ub: 7.79 },
];

// ============================================================
// EPISODES — keyed by campaign ID
// ============================================================
window.EPISODES_BY_CAMPAIGN = {
  etrade: [
    {
      n: 'Ep. 01', title: 'Kim Ng on building competence', date: 'Mar 14',
      total: { impr: 2_140_000, er: 5.4, eng: 115_560, spend: 8_400 },
      perChannel: [
        { name: 'YouTube',   distKind:'paid',            impr: 1_420_000, paidImpr: 1_420_000, orgImpr: 0,       eng: 81_000, paidEng: 81_000, orgEng: 0,    er: 5.7, cpm: 0.49, spend: 6_958, posts: 2 },
        { name: 'LinkedIn',  distKind:'organic',         impr: 86_400,    paidImpr: 0,         orgImpr: 86_400,  eng: 4_400,  paidEng: 0,      orgEng: 4_400, er: 5.1, cpm: 0,    spend: 0,     posts: 3 },
        { name: 'Instagram', distKind:'organic+boosted', impr: 412_000,   paidImpr: 380_000,   orgImpr: 32_000,  eng: 6_590,  paidEng: 5_900,  orgEng: 690,  er: 1.6, cpm: 4.80, spend: 1_824, posts: 4 },
        { name: 'TikTok',    distKind:'organic+boosted', impr: 158_000,   paidImpr: 116_000,   orgImpr: 42_000,  eng: 3_790,  paidEng: 2_400,  orgEng: 1_390, er: 2.4, cpm: 1.90, spend: 220,   posts: 3 },
        { name: 'X',         distKind:'paid',            impr: 63_000,    paidImpr: 63_000,    orgImpr: 0,       eng: 820,    paidEng: 820,    orgEng: 0,    er: 1.3, cpm: 0.88, spend: 55,    posts: 2 },
      ],
      topPosts: [
        { quote: 'The way Kim Ng describes her hiring philosophy as "overly thorough"…', platform:'LinkedIn', er: 5.12, reach: 8_640 },
        { quote: '"Competence compounds." — Kim Ng cutdown', platform:'TikTok', er: 4.18, reach: 42_300 },
      ],
      callouts: [
        { kind: 'pos', text: 'YouTube CPM beat benchmark by 25%.' },
        { kind: 'pos', text: 'LinkedIn organic ER hit 5.1% — strongest of the campaign.' },
      ]
    },
    {
      n: 'Ep. 02', title: 'The data layer behind clutch performance', date: 'Mar 28',
      total: { impr: 1_980_000, er: 4.7, eng: 93_060, spend: 8_100 },
      perChannel: [
        { name: 'YouTube',   distKind:'paid',            impr: 1_310_000, paidImpr: 1_310_000, orgImpr: 0,       eng: 64_200, paidEng: 64_200, orgEng: 0,     er: 4.9, cpm: 0.51, spend: 6_681, posts: 2 },
        { name: 'LinkedIn',  distKind:'organic',         impr: 78_200,    paidImpr: 0,         orgImpr: 78_200,  eng: 3_440,  paidEng: 0,      orgEng: 3_440, er: 4.4, cpm: 0,    spend: 0,     posts: 3 },
        { name: 'Instagram', distKind:'organic+boosted', impr: 384_000,   paidImpr: 351_000,   orgImpr: 33_000,  eng: 5_760,  paidEng: 5_120,  orgEng: 640,   er: 1.5, cpm: 5.10, spend: 1_790, posts: 4 },
        { name: 'TikTok',    distKind:'organic+boosted', impr: 142_000,   paidImpr: 100_000,   orgImpr: 42_000,  eng: 2_840,  paidEng: 1_700,  orgEng: 1_140, er: 2.0, cpm: 2.05, spend: 205,   posts: 3 },
        { name: 'X',         distKind:'paid',            impr: 65_800,    paidImpr: 65_800,    orgImpr: 0,       eng: 720,    paidEng: 720,    orgEng: 0,     er: 1.1, cpm: 0.95, spend: 62,    posts: 2 },
      ],
      topPosts: [
        { quote: 'Cutdown: "Clutch is the data layer most teams ignore."', platform:'Instagram', er: 4.92, reach: 51_200 },
        { quote: '"What separates teams in the playoffs?" — full clip', platform:'YouTube', er: 4.31, reach: 384_000 },
      ],
      callouts: [
        { kind: 'pos', text: 'IG cutdown drove 384K impressions — best of campaign.' },
        { kind: 'warn', text: 'LinkedIn ER softened from Ep. 01 (5.1% → 4.4%).' },
      ]
    },
    {
      n: 'Ep. 03', title: 'Leslie Osborne on culture as compounding', date: 'Apr 11',
      total: { impr: 1_790_000, er: 4.2, eng: 75_180, spend: 7_300 },
      perChannel: [
        { name: 'YouTube',   distKind:'paid',            impr: 1_180_000, paidImpr: 1_180_000, orgImpr: 0,       eng: 51_900, paidEng: 51_900, orgEng: 0,     er: 4.4, cpm: 0.46, spend: 5_428, posts: 2 },
        { name: 'LinkedIn',  distKind:'organic',         impr: 72_600,    paidImpr: 0,         orgImpr: 72_600,  eng: 3_480,  paidEng: 0,      orgEng: 3_480, er: 4.8, cpm: 0,    spend: 0,     posts: 3 },
        { name: 'Instagram', distKind:'organic+boosted', impr: 358_000,   paidImpr: 320_000,   orgImpr: 38_000,  eng: 4_650,  paidEng: 4_100,  orgEng: 550,   er: 1.3, cpm: 5.40, spend: 1_728, posts: 4 },
        { name: 'TikTok',    distKind:'organic+boosted', impr: 127_000,   paidImpr: 89_000,    orgImpr: 38_000,  eng: 2_670,  paidEng: 1_500,  orgEng: 1_170, er: 2.1, cpm: 2.18, spend: 194,   posts: 3 },
        { name: 'X',         distKind:'paid',            impr: 52_400,    paidImpr: 52_400,    orgImpr: 0,       eng: 524,    paidEng: 524,    orgEng: 0,     er: 1.0, cpm: 0.99, spend: 52,    posts: 2 },
      ],
      topPosts: [
        { quote: '"Culture isn\'t a poster — it\'s the compound interest of every hire."', platform:'LinkedIn', er: 5.34, reach: 14_200 },
        { quote: 'Leslie Osborne on raising standards (full ep.)', platform:'YouTube', er: 4.88, reach: 412_000 },
      ],
      callouts: [
        { kind: 'pos', text: 'Best YouTube CPM of campaign at $0.46.' },
        { kind: 'warn', text: 'IG ER trending down — refresh creative for Ep. 04.' },
      ]
    },
  ],
  tastytrade: [],
  adp: [],
  usbank: []
};
