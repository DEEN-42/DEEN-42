"""Fetch DEEN-42 GitHub activity and render assets/github-stats.svg.

Data sources (stdlib only, so it runs in a bare GitHub Action):
  * GITHUB_TOKEN set  -> GraphQL API (contributions per year, merged PRs, repos, stars)
  * no token          -> public contribution-calendar HTML + search API (PR count)

Usage:  python scripts/github_stats.py [--user DEEN-42] [--out assets/github-stats.svg]
"""
import argparse, datetime as dt, json, os, random, re, urllib.request

UA = {'User-Agent': 'deen-42-profile-stats'}
BG, PANEL, LINE, TEXT, MUTED, AMBER = '#0D0D0D', '#161616', '#262626', '#EDEDED', '#8A8A8A', '#F5A524'
MONO = "ui-monospace,SFMono-Regular,Consolas,'Liberation Mono',monospace"
SANS = "'Segoe UI',Helvetica,Arial,sans-serif"
LEVEL_FILL = ['#1C1C1C', '#5C3F0E', '#8F6114', '#C4851C', AMBER]


def get(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8')


# ---------------------------------------------------------------- GraphQL path
def via_graphql(user, token):
    h = {'Authorization': f'bearer {token}', 'Content-Type': 'application/json'}
    q = lambda query, **v: json.loads(get('https://api.github.com/graphql',
                                          json.dumps({'query': query, 'variables': v}).encode(), h))['data']
    base = q('''query($u:String!){user(login:$u){createdAt
        contributionsCollection{contributionYears contributionCalendar{totalContributions weeks{contributionDays{date contributionCount contributionLevel}}}}
        merged:pullRequests(states:MERGED){totalCount} prs:pullRequests{totalCount}
        repositories(ownerAffiliations:OWNER,privacy:PUBLIC,first:100){totalCount nodes{stargazerCount}}}}''', u=user)['user']
    total = 0
    for y in base['contributionsCollection']['contributionYears']:
        c = q('''query($u:String!,$f:DateTime!,$t:DateTime!){user(login:$u){contributionsCollection(from:$f,to:$t){
              contributionCalendar{totalContributions}}}}''', u=user, f=f'{y}-01-01T00:00:00Z', t=f'{y}-12-31T23:59:59Z')
        total += c['user']['contributionsCollection']['contributionCalendar']['totalContributions']
    lv = {'NONE': 0, 'FIRST_QUARTILE': 1, 'SECOND_QUARTILE': 2, 'THIRD_QUARTILE': 3, 'FOURTH_QUARTILE': 4}
    days = [(d['date'], d['contributionCount'], lv[d['contributionLevel']])
            for w in base['contributionsCollection']['contributionCalendar']['weeks'] for d in w['contributionDays']]
    return dict(total=total, year=base['contributionsCollection']['contributionCalendar']['totalContributions'],
                merged=base['merged']['totalCount'], prs=base['prs']['totalCount'],
                repos=base['repositories']['totalCount'],
                stars=sum(n['stargazerCount'] for n in base['repositories']['nodes']), days=days)


# ------------------------------------------------------------- public HTML path
def calendar(user, frm=None, to=None):
    url = f'https://github.com/users/{user}/contributions' + (f'?from={frm}&to={to}' if frm else '')
    html = get(url, headers={'User-Agent': 'Mozilla/5.0'})
    tips = {m.group(1): m.group(2) for m in re.finditer(r'for="(contribution-day-component-[\d-]+)"[^>]*>([^<]*)</tool-tip>', html)}
    days = []
    for m in re.finditer(r'data-date="([\d-]+)" id="(contribution-day-component-[\d-]+)" data-level="(\d)"', html):
        t = tips.get(m.group(2), '')
        n = int(re.match(r'(\d+)', t).group(1)) if re.match(r'\d', t) else 0
        days.append((m.group(1), n, int(m.group(3))))
    head = re.search(r'([\d,]+)\s+contributions?\s+in', html)
    return sorted(days), int(head.group(1).replace(',', '')) if head else sum(d[1] for d in days)


def via_public(user):
    days, year_total = calendar(user)
    total = 0
    for y in range(2022, dt.date.today().year + 1):  # calendar years, no overlap
        _, t = calendar(user, f'{y}-01-01', f'{y}-12-31'); total += t
    search = lambda s: json.loads(get(f'https://api.github.com/search/issues?q={s}&per_page=1'))['total_count']
    return dict(total=total, year=year_total, merged=search(f'author:{user}+type:pr+is:merged'),
                prs=search(f'author:{user}+type:pr'), repos=None, stars=None, days=days)


# --------------------------------------------------------------------- SVG card
def render(s, user):
    W, H = 1000, 250
    weeks = 30  # most recent ~7 months on the heatmap
    days = s['days'][-weeks * 7:]
    stats = [('TOTAL CONTRIBUTIONS', s['total'], 'all time'),
             ('LAST 12 MONTHS', s['year'], 'commits · PRs · reviews'),
             ('PULL REQUESTS MERGED', s['merged'], f"of {s['prs']} opened")]
    css = [f'.n{{opacity:0;animation:cf .08s steps(1,end)}}@keyframes cf{{from,to{{opacity:1}}}}',
           '.f{animation:fin .25s ease-out both}@keyframes fin{0%{opacity:0;transform:translateY(5px)}75%,100%{opacity:1;transform:none}}',
           '.c{animation:cell .3s steps(2,end) both}@keyframes cell{0%{opacity:0}70%,100%{opacity:1}}',
           '.live{animation:live 1.6s steps(1) infinite}@keyframes live{50%{opacity:.25}}',
           '@media (prefers-reduced-motion:reduce){.n,.f,.c,.live{animation:none}}']
    upd = 'UPDATED ' + dt.date.today().strftime('%d %b %Y').upper()
    out = [f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14" fill="{BG}" stroke="{LINE}"/>',
           f'<text x="28" y="34" font-family="{MONO}" font-size="12" fill="{MUTED}">$ git log --author=<tspan fill="{AMBER}">{user}</tspan> --stat</text>',
           f'<rect class="live" x="{W - 28 - len(upd) * 8.2 - 16:.0f}" y="25" width="7" height="7" fill="{AMBER}"/>',
           f'<text x="{W - 28}" y="33" text-anchor="end" font-family="{MONO}" font-size="11" letter-spacing="1.5" fill="{MUTED}">'
           f'{upd}</text>',
           f'<path d="M1 50H{W - 1}" stroke="{LINE}"/>']
    # three counters on the left, counting up
    for i, (label, val, sub) in enumerate(stats):
        y = 92 + i * 56
        steps = [int(val * k / 6) for k in range(6)] + [val]
        for k, v in enumerate(steps[:-1]):
            out.append(f'<text class="n" style="animation-delay:{0.4 + i * 0.15 + k * 0.08:.2f}s" x="28" y="{y}" font-family="{SANS}" '
                       f'font-size="30" font-weight="700" fill="{MUTED}">{v:,}</text>')
        out.append(f'<text class="f" style="animation-delay:{0.4 + i * 0.15 + 6 * 0.08:.2f}s" x="28" y="{y}" font-family="{SANS}" '
                   f'font-size="30" font-weight="700" fill="{TEXT}">{val:,}</text>')
        out.append(f'<text x="160" y="{y - 14}" font-family="{MONO}" font-size="11" letter-spacing="1.5" fill="{AMBER}">{label}</text>')
        out.append(f'<text x="160" y="{y + 2}" font-family="{SANS}" font-size="12" fill="{MUTED}">{sub}</text>')
    # heatmap on the right: cells pop in column by column
    x0, y0, c = 410, 72, 17
    rnd = random.Random(3)
    for k, (date, n, lvl) in enumerate(days):
        col, row = k // 7, k % 7
        d = 0.5 + col * 0.035 + rnd.uniform(0, 0.05)
        out.append(f'<rect class="c" style="animation-delay:{d:.2f}s" x="{x0 + col * (c + 2)}" y="{y0 + row * (c + 2)}" '
                   f'width="{c}" height="{c}" rx="2" fill="{LEVEL_FILL[lvl]}"><title>{date}: {n}</title></rect>')
    lx = x0 + weeks * (c + 2) - 150
    out.append(f'<text x="{x0}" y="{y0 + 7 * (c + 2) + 18}" font-family="{MONO}" font-size="11" fill="{MUTED}">last {weeks} weeks</text>')
    out.append(f'<text x="{lx - 8}" y="{y0 + 7 * (c + 2) + 18}" text-anchor="end" font-family="{MONO}" font-size="11" fill="{MUTED}">less</text>')
    for i, f in enumerate(LEVEL_FILL):
        out.append(f'<rect x="{lx + i * 16}" y="{y0 + 7 * (c + 2) + 8}" width="12" height="12" rx="2" fill="{f}"/>')
    out.append(f'<text x="{lx + 5 * 16 + 4}" y="{y0 + 7 * (c + 2) + 18}" font-family="{MONO}" font-size="11" fill="{MUTED}">more</text>')
    label = (f"GitHub activity for {user}: {s['total']:,} contributions all time, {s['year']:,} in the last 12 months, "
             f"{s['merged']} pull requests merged.")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{label}">'
            f'<title>{label}</title><style>{"".join(css)}</style>\n' + '\n'.join(out) + '\n</svg>\n')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--user', default='DEEN-42')
    ap.add_argument('--out', default=os.path.join(os.path.dirname(__file__), '..', 'assets', 'stats', 'github.svg'))
    a = ap.parse_args()
    tok = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
    s = via_graphql(a.user, tok) if tok else via_public(a.user)
    open(a.out, 'w', encoding='utf-8').write(render(s, a.user))
    print({k: v for k, v in s.items() if k != 'days'}, 'days:', len(s['days']))
