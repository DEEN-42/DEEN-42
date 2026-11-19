"""Build every asset of the DEEN-42 profile README.

    python scripts/build_profile.py                         # SVGs + icons
    python scripts/build_profile.py --gif-source art.gif    # also rebuild the header GIF (needs Pillow)

Design: graphite + one amber accent, system fonts only, pure-CSS animation inside each SVG
(GitHub renders SVGs through <img>, so no JS, no external fonts). Every keyframe finishes its
visible change by ~80 % so the last painted frame is always the final state, and every
animation is skipped under prefers-reduced-motion. Icons: Lucide (ISC), vendored in scripts/lucide.
"""
import argparse, html, os, random, re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ASSETS = os.path.join(ROOT, 'assets')
LUCIDE = os.path.join(os.path.dirname(__file__), 'lucide')

BG, PANEL, LINE, TEXT, MUTED, GREY, AMBER = '#0D0D0D', '#161616', '#262626', '#EDEDED', '#8A8A8A', '#B5B5B5', '#F5A524'
MONO = "ui-monospace,SFMono-Regular,Consolas,'Liberation Mono',monospace"
SANS = "'Segoe UI',Helvetica,Arial,sans-serif"


def esc(s): return html.escape(str(s), quote=True)


def write(rel, s):
    p = os.path.join(ASSETS, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'w', encoding='utf-8').write(s)


def svg_doc(w, h, label, body, css=(), overlay=''):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" '
            f'aria-label="{esc(label)}">\n<title>{esc(label)}</title>\n<style>{"".join(css)}</style>\n{body}\n{overlay}\n</svg>\n')


# ------------------------------------------------------------------ icons
LINKEDIN = ('<path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"/>'
            '<rect width="4" height="12" x="2" y="9"/><circle cx="4" cy="4" r="2"/>')  # Lucide's last brand glyph


def icon_body(name):
    if name == 'linkedin': return LINKEDIN
    src = open(os.path.join(LUCIDE, name + '.svg'), encoding='utf-8').read()
    return re.sub(r'\s+', ' ', re.search(r'<svg[^>]*>(.*)</svg>', src, re.S).group(1)).strip()


def icon_at(name, x, y, size=22, color=AMBER):
    return (f'<g transform="translate({x} {y}) scale({size / 24:.4f})" fill="none" stroke="{color}" stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round">{icon_body(name)}</g>')


# ------------------------------------------------------------------ animation kit
CSS = [
    f'.cv{{opacity:0;fill:{BG};animation:cv .5s steps(3,end) both}}.cv.h{{animation-name:cvh}}',
    f'@keyframes cv{{0%{{opacity:1;fill:{BG}}}50%{{opacity:1;fill:{PANEL}}}80%,100%{{opacity:0}}}}',
    f'@keyframes cvh{{0%{{opacity:1;fill:{BG}}}45%{{opacity:1;fill:{AMBER}}}80%,100%{{opacity:0}}}}',
    '.up{animation:up .4s ease-out both}@keyframes up{0%{opacity:0;transform:translateY(6px)}75%,100%{opacity:1;transform:none}}',
    '.ln{animation:ln .35s ease-out both}@keyframes ln{0%{opacity:0;transform:translateX(-6px)}75%,100%{opacity:1;transform:none}}',
    '.live{animation:live 1.6s steps(1) infinite}@keyframes live{50%{opacity:.25}}',
    '.bk{animation:bk 1.1s steps(1) infinite}@keyframes bk{50%{opacity:0}}',
    '.cn{opacity:0;animation:cn .08s steps(1,end)}@keyframes cn{from,to{opacity:1}}',
    '@media (prefers-reduced-motion:reduce){.cv,.up,.ln,.live,.bk,.cn,.tw,.ty{animation:none}}',
]


def pixels(x, y, w, h, start, span, seed, cell=14, hot=0.05):
    """Background-coloured squares over a region that fade out in a seeded random order.
    They default to opacity 0, so a static render simply shows the content."""
    rnd = random.Random(seed)
    cells = [(cx, cy) for cy in range(y, y + h, cell) for cx in range(x, x + w, cell)]
    rnd.shuffle(cells)
    return ''.join(f'<rect class="{"cv h" if rnd.random() < hot else "cv"}" style="animation-delay:{start + span * i / len(cells):.2f}s" '
                   f'x="{cx}" y="{cy}" width="{min(cell, x + w - cx)}" height="{min(cell, y + h - cy)}"/>'
                   for i, (cx, cy) in enumerate(cells))


def frame(w, h, rx=14, fill=BG, stroke=LINE, dash=False):
    d = ' stroke-dasharray="5 5"' if dash else ''
    return f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="{rx}" fill="{fill}" stroke="{stroke}"{d}/>'


def spans(segs):
    """segs: [(text, kind)], kind 0 = normal, 1 = number (amber bold), 2 = tech (white)."""
    st = {0: f'fill="{GREY}"', 1: f'fill="{AMBER}" font-weight="700"', 2: f'fill="{TEXT}" font-weight="600"'}
    return ''.join(f'<tspan {st[k]}>{esc(t)}</tspan>' for t, k in segs)


def chip(xr, y, text, color, filled=False, dashed=False):
    w = len(text) * 7.4 + 18
    d = ' stroke-dasharray="3 3"' if dashed else ''
    return (f'<rect x="{xr - w:.0f}" y="{y}" width="{w:.0f}" height="20" rx="4" fill="{color if filled else PANEL}" stroke="{color}"{d}/>'
            f'<text x="{xr - w / 2:.0f}" y="{y + 14}" text-anchor="middle" font-family="{MONO}" font-size="10.5" font-weight="700" '
            f'letter-spacing="1.2" fill="{BG if filled else color}">{esc(text)}</text>'), w


def tags(x, y, items):
    out = []
    for t in items:
        w = len(t) * 7 + 18
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="22" rx="4" fill="{PANEL}" stroke="{LINE}"/>'
                   f'<text x="{x + w / 2}" y="{y + 15}" text-anchor="middle" font-family="{MONO}" font-size="11" fill="{GREY}">{esc(t)}</text>')
        x += w + 8
    return ''.join(out)


# ------------------------------------------------------------------ header
CAT = ["..A.........A..",
       "..AA.......AA..",
       "..ADA.....ADA..",
       "..AAAAAAAAAAA..",
       ".AAAAAAAAAAAAA.",
       ".AAEEAAAAAEEAA.",
       ".AAEEAAAAAEEAA.",
       "WAAAAAANAAAAAAW",
       ".AAAAAMAMAAAAA.",
       "W.AAAAAAAAAAA.W",
       "...AAAAAAAAA...",
       "....AAAAAAA...."]


def pixel_cat(x0, y0, cell, seed=9):
    """Pixel-art cat face: amber fur with a little texture, dim inner ears and whiskers,
    dark nose/mouth, and eyes that blink every few seconds."""
    rnd = random.Random(seed); out = []
    for r, row in enumerate(CAT):
        for c, ch in enumerate(row):
            if ch == '.': continue
            x, y = x0 + c * cell, y0 + r * cell
            if ch == 'A':
                out.append(f'<rect x="{x}" y="{y}" width="{cell - 1}" height="{cell - 1}" fill="{AMBER}" opacity="{1 if rnd.random() > .15 else .82}"/>')
            elif ch == 'D':
                out.append(f'<rect x="{x}" y="{y}" width="{cell - 1}" height="{cell - 1}" fill="#8F6114"/>')
            elif ch == 'W':
                out.append(f'<rect x="{x}" y="{y + cell // 2 - 1}" width="{cell - 1}" height="3" fill="#8F6114"/>')
            elif ch in 'NM':
                out.append(f'<rect x="{x}" y="{y}" width="{cell - 1}" height="{cell - 1}" fill="{"#5C3F0E" if ch == "N" else BG}"/>')
            elif ch == 'E':
                out.append(f'<rect x="{x}" y="{y}" width="{cell - 1}" height="{cell - 1}" fill="{BG}"/>')
    # slit pupils + eyelids (the lids blink shut every few seconds)
    for c in (3, 10):  # left column of each 2x2 eye
        ex, ey = x0 + c * cell, y0 + 5 * cell
        out.append(f'<rect x="{ex + cell - 3}" y="{ey + 2}" width="4" height="{2 * cell - 5}" rx="2" fill="{AMBER}"/>')
        out.append(f'<rect class="eye" x="{ex}" y="{ey}" width="{2 * cell - 1}" height="{2 * cell - 1}" fill="{AMBER}"/>')
    return ''.join(out)


def build_header():
    W, H = 1000, 230
    body = f'''{frame(W, H)}<path d="M1 44H{W - 1}" stroke="{LINE}"/>
<text x="28" y="28" font-family="{MONO}" font-size="12" fill="{MUTED}">~/deen-42 <tspan fill="{LINE}">/</tspan> profile.md</text>
<text x="{W - 28}" y="28" text-anchor="end" font-family="{MONO}" font-size="12" fill="{MUTED}">IIT KHARAGPUR · 2023–28</text>
<text x="28" y="88" font-family="{MONO}" font-size="12" letter-spacing="3" fill="{AMBER}">HELLO, I&#39;M</text>
<text x="25" y="140" font-family="{SANS}" font-size="54" font-weight="700" letter-spacing="-1.5" fill="{TEXT}">Debanshu Ghosh</text>
<text x="28" y="174" font-family="{SANS}" font-size="18" fill="{MUTED}">Backend systems · Real-time products · Agentic AI</text>
<text x="28" y="208" font-family="{MONO}" font-size="14" fill="{TEXT}"><tspan fill="{AMBER}">$</tspan> next_stop --company eBay --term &quot;Summer 2027&quot;</text>
<rect class="bk" x="414" y="196" width="8" height="15" fill="{AMBER}"/>{pixel_cat(772, 62, 13)}'''
    eye = (f'.eye{{opacity:0;animation:eye 4.5s steps(1) 1.8s infinite}}@keyframes eye{{0%,90%{{opacity:0}}91%,95%{{opacity:1}}96%,100%{{opacity:0}}}}'
           '@media (prefers-reduced-motion:reduce){.eye{animation:none}}')
    write('header/hero.svg', svg_doc(W, H, 'Debanshu Ghosh: backend systems, real-time products, agentic AI. Next stop: eBay, Summer 2027. '
                                     'A pixel-art cat face blinks on the right.', body, CSS + [eye], pixels(0, 0, W, H, 0, 1.1, 11, cell=20)))

    W, H = 1000, 128
    cells = [(['0', '3,100', '9,600', '17,400', '24,200'], '28,000 RPS', 'C++ IN-MEMORY DATABASE', 'project benchmark'),
             (['0', '640', '1,410', '1,980', '2,270'], '2353', 'LEETCODE PEAK RATING', 'Guardian · top 0.41% at peak'),
             (['TOP 500', 'TOP 120', 'TOP 40', 'TOP 12', 'TOP 7'], 'TOP 5', "SMART INDIA HACKATHON '25", '500+ teams nationwide')]
    b = [frame(W, H), f'<path d="M333 24V104M666 24V104" stroke="{LINE}"/>']
    for i, (seq, v, lab, sub) in enumerate(cells):
        cx = 166 + i * 334
        for k, iv in enumerate(seq):
            b.append(f'<text class="cn" style="animation-delay:{1 + k * .09:.2f}s" x="{cx}" y="56" text-anchor="middle" '
                     f'font-family="{SANS}" font-size="34" font-weight="700" fill="{MUTED}">{esc(iv)}</text>')
        b.append(f'<text class="up" style="animation-delay:{1 + len(seq) * .09:.2f}s" x="{cx}" y="56" text-anchor="middle" '
                 f'font-family="{SANS}" font-size="34" font-weight="700" fill="{TEXT}">{esc(v)}</text>'
                 f'<text x="{cx}" y="82" text-anchor="middle" font-family="{MONO}" font-size="11" letter-spacing="1.5" fill="{AMBER}">{esc(lab)}</text>'
                 f'<text x="{cx}" y="102" text-anchor="middle" font-family="{SANS}" font-size="12" fill="{MUTED}">{esc(sub)}</text>')
    write('header/highlights.svg', svg_doc(W, H, '28,000 requests per second in a C++ benchmark; LeetCode peak rating 2353 (Guardian); '
                                           'Smart India Hackathon 2025 top 5 of 500+ teams.', '\n'.join(b), CSS,
                                           pixels(0, 0, W, H, .25, 1.1, 23, cell=16)))


# ------------------------------------------------------------------ buttons
BUTTONS = [('portfolio', 'globe', 'PORTFOLIO'), ('linkedin', 'linkedin', 'LINKEDIN'), ('email', 'mail', 'EMAIL'),
           ('repositories', 'folder-git-2', 'REPOSITORIES'), ('view-code', 'code-xml', 'VIEW CODE')]


def build_buttons():
    for name, ico, label in BUTTONS:
        body = (frame(158, 34, 7, PANEL) + icon_at(ico, 14, 9, 16) +
                f'<text x="94" y="21.5" text-anchor="middle" font-family="{MONO}" font-size="11" font-weight="600" '
                f'letter-spacing="1.5" fill="{TEXT}">{label}</text>')
        write(f'buttons/{name}.svg', svg_doc(158, 34, label.title(), body))


# ------------------------------------------------------------------ list rows (experience + projects)
def row(path, label, *, tile, title, sub, desc, right, chip_spec=None, live=False, timeline=None, delay=0.0, seed=1):
    """One-line LinkedIn-style row (it sits inside <details><summary>).
    tile: ('letter', 'E') or ('icon', 'zap'); timeline: None or (is_first, is_last, filled)."""
    W, H = 1000, 84
    b = [frame(W, H, 12)]
    x = 22
    if timeline:
        first, last, filled = timeline
        b.append(f'<path d="M34 {0 if not first else 42}V{H if not last else 42}" stroke="{LINE}" stroke-width="2"/>')
        b.append(f'<rect x="28" y="36" width="12" height="12" fill="{AMBER if filled else BG}" stroke="{AMBER if filled else MUTED}" stroke-width="2"/>')
        x = 58
    b.append(f'<rect x="{x}" y="18" width="48" height="48" rx="10" fill="{PANEL}" stroke="{LINE}"/>')
    if tile[0] == 'letter':
        b.append(f'<text x="{x + 24}" y="51" text-anchor="middle" font-family="{SANS}" font-size="24" font-weight="700" fill="{AMBER}">{esc(tile[1])}</text>')
    else:
        b.append(icon_at(tile[1], x + 12, 30, 24))
    tx = x + 66
    b.append(f'<g class="ln" style="animation-delay:{delay + .35:.2f}s"><text x="{tx}" y="38" font-family="{SANS}" font-size="18" font-weight="700" '
             f'fill="{TEXT}">{esc(title)}<tspan font-weight="400" fill="{MUTED}">  ·  {esc(sub)}</tspan></text>'
             f'<text x="{tx}" y="60" font-family="{SANS}" font-size="13.5" fill="{GREY}">{esc(desc)}</text></g>')
    xr = W - 24
    if chip_spec:
        c, cw = chip(xr, 18, *chip_spec)
        b.append(c)
        if live:
            b.append(f'<rect class="live" x="{xr - cw - 14:.0f}" y="25" width="7" height="7" fill="{AMBER}"/>')
    b.append(f'<text x="{xr}" y="{60 if chip_spec else 46}" text-anchor="end" font-family="{MONO}" font-size="11" '
             f'letter-spacing="1.3" fill="{AMBER if chip_spec else MUTED}">{esc(right)}</text>')
    write(path, svg_doc(W, H, label, '\n'.join(b), CSS, pixels(0, 0, W, H, delay, .6, seed, cell=12)))


def detail_card(path, label, lines, tag_list, footer=None, delay=0.1, seed=1):
    """Expanded content: one-liners with amber numbers, wiped in line by line."""
    W = 1000
    H = 40 + len(lines) * 30 + (50 if tag_list else 0) + (30 if footer else 0)
    b = [frame(W, H, 12, PANEL)]
    covers = []
    y = 44
    rnd = random.Random(seed)
    for k, segs in enumerate(lines):
        t = delay + k * .14
        b.append(f'<rect x="28" y="{y - 10}" width="6" height="6" fill="{AMBER}"/>')
        b.append(f'<text class="ln" style="animation-delay:{t:.2f}s" x="46" y="{y - 2}" font-family="{SANS}" font-size="15">{spans(segs)}</text>')
        width = int(sum(len(s) for s, _ in segs) * 7.8) + 24
        for c in range(0, width, 24):
            for r in (0, 12):
                covers.append(f'<rect class="cv h" style="animation-delay:{t + c / width * .35 + rnd.uniform(0, .05):.2f}s" '
                              f'x="{40 + c}" y="{y - 22 + r}" width="24" height="12"/>')
        y += 30
    if tag_list:
        b.append(f'<path d="M28 {y - 6}H{W - 28}" stroke="{LINE}"/>')
        b.append(f'<g class="up" style="animation-delay:{delay + len(lines) * .14 + .2:.2f}s">{tags(28, y + 8, tag_list)}</g>')
        y += 50
    if footer:
        b.append(f'<text x="28" y="{y + 2}" font-family="{MONO}" font-size="12" fill="{AMBER}">&gt; {esc(footer)}</text>'
                 f'<rect class="bk" x="{28 + (len(footer) + 2) * 7.2:.0f}" y="{y - 10}" width="7" height="14" fill="{AMBER}"/>')
    write(path, svg_doc(W, H, label, '\n'.join(b), CSS, ''.join(covers)))


EXPERIENCE = [  # newest first, like LinkedIn
    dict(slug='ebay', letter='e', title='Summer Intern', company='eBay', desc='Incoming software engineering internship',
         when='SUMMER 2027', chip=('INCOMING', AMBER, False, True), live=False, filled=False,
         lines=[[('Joining ', 0), ('eBay', 2), (' as a summer intern in ', 0), ('2027', 1)]], tags=[], footer='loading next chapter'),
    dict(slug='edumorph', letter='E', title='SDE Intern', company='Edumorph · Remote', desc='Payments, queues and real-time pipelines for an edtech app',
         when='AUG 2026 – PRESENT', chip=('CURRENT', AMBER, True, False), live=True, filled=True,
         lines=[[('Video-progress pipeline on ', 0), ('Redis Cluster', 2), (' + ', 0), ('BullMQ', 2), (' workers', 0)],
                [('Razorpay QR & payment links: ', 0), ('250+', 1), (' transactions', 0)],
                [('Push notifications via FCM to ', 0), ('2,000+', 1), (' users', 0)],
                [('Install-to-signup conversion ', 0), ('55% → 78%', 1)]],
         tags=['Flutter', 'Node.js', 'Redis', 'BullMQ', 'Razorpay', 'FCM', 'PostHog'], footer=None),
    dict(slug='webyalaya', letter='W', title='Full Stack Intern', company='Webyalaya', desc='Async pipelines, observability and payments',
         when='NOV 2025 – FEB 2026', chip=('DONE', MUTED, False, False), live=False, filled=False,
         lines=[[('Core API latency ', 0), ('1,200 ms → 700 ms', 1), (' on AWS ECS', 0)],
                [('Observability with ', 0), ('Prometheus', 2), (', ', 0), ('Grafana', 2), (', ', 0), ('Sentry', 2)],
                [('Idempotent Razorpay gateway + Google Calendar sync', 0)],
                [('Transcription network calls cut by ', 0), ('60%', 1)]],
         tags=['NestJS', 'AWS ECS', 'Redis', 'BullMQ', 'Prometheus', 'Grafana', 'Sentry'], footer=None),
]

PROJECTS = [
    dict(slug='inmemorydb', icon='zap', title='InMemoryDB', sub='C++17', repo='DEEN-42/MemoryAllocator',
         desc='Key-value store built for concurrency and predictable latency',
         lines=[[('28,000', 1), (' requests/s peak with ', 0), ('0', 1), (' errors over ', 0), ('1M', 1), (' requests', 0)],
                [('Latency ', 0), ('0.4 ms', 1), (' p50 · ', 0), ('1.2 ms', 1), (' p99 at ', 0), ('1,000', 1), (' clients', 0)],
                [('Non-blocking reactor, ', 0), ('64-way', 1), (' sharding, memory arenas', 0)],
                [('AOF persistence + O(1) timing wheel', 0)]],
         tags=['C++17', 'Winsock2', 'Concurrency', 'Sharding', 'AOF']),
    dict(slug='ai-interviewer', icon='brain-circuit', title='AI Interviewer', sub='LangGraph', repo='DEEN-42/AgenticAI_Interviewer',
         desc='Stateful interview agent with adaptive Socratic questioning',
         lines=[[('40%', 1), (' lower LLM cost via a 3-model fallback router', 0)],
                [('Session recovery in under ', 0), ('50 ms', 1), (' over WebSockets', 0)],
                [('90%', 1), (' uptime through API outages', 0)],
                [('RAG context from ', 0), ('FAISS', 2), (' + ', 0), ('Tavily', 2)]],
         tags=['LangGraph', 'FastAPI', 'Redis', 'FAISS', 'Tavily']),
    dict(slug='cv-builder', icon='file-text', title='Collaborative CV Builder', sub='Yjs CRDTs', repo='DEEN-42/resumebuilder',
         desc='Real-time multi-user editing across servers',
         lines=[[('90%', 1), (' smaller payloads with binary state-vector deltas', 0)],
                [('96%', 1), (' fewer synchronous DB writes (BullMQ write-behind)', 0)],
                [('Sub-millisecond', 1), (' in-memory reconciliation', 0)],
                [('Cross-server fan-out with ', 0), ('Redis Pub/Sub', 2)]],
         tags=['Yjs', 'WebSockets', 'Redis', 'BullMQ']),
    dict(slug='fieldsync', icon='wheat', title='FieldSync', sub='SIH 2025', repo='DEEN-42/SIH25-FieldSync',
         desc='Crop-residue logistics platform, Smart India Hackathon finalist',
         lines=[[('Top 5', 1), (' of ', 0), ('500+', 1), (' teams at the SIH 2025 finals', 0)],
                [('6', 1), ('-service platform: Node.js, Prisma, PostgreSQL', 0)],
                [('K-Means + Haversine clustering, ', 0), ('OR-Tools', 2), (' routing', 0)],
                [('Live IoT telemetry with ', 0), ('Socket.IO', 2)]],
         tags=['Node.js', 'PostgreSQL', 'Redis', 'OR-Tools', 'Python']),
]


def plain(lines): return '; '.join(''.join(t for t, _ in seg) for seg in lines)


def build_lists():
    n = len(EXPERIENCE)
    for i, e in enumerate(EXPERIENCE):
        row(f'experience/{e["slug"]}.svg', f'{e["title"]} at {e["company"]}, {e["when"].title()}. {e["desc"]}.',
            tile=('letter', e['letter']), title=e['title'], sub=e['company'], desc=e['desc'], right=e['when'],
            chip_spec=e['chip'], live=e['live'], timeline=(i == 0, i == n - 1, e['filled']), delay=i * .25, seed=40 + i)
        detail_card(f'experience/{e["slug"]}-details.svg', f'{e["company"]}: {plain(e["lines"])}.', e['lines'], e['tags'],
                    e['footer'], seed=60 + i)
    for i, p in enumerate(PROJECTS):
        row(f'projects/{p["slug"]}.svg', f'{p["title"]}: {p["desc"]}.', tile=('icon', p['icon']), title=p['title'],
            sub=p['sub'], desc=p['desc'], right=p['repo'].split('/')[1], delay=i * .2, seed=80 + i)
        detail_card(f'projects/{p["slug"]}-details.svg', f'{p["title"]}: {plain(p["lines"])}.', p['lines'], p['tags'], seed=90 + i)


# ------------------------------------------------------------------ competitive programming
CP = [('leetcode', 'LeetCode', 'deen42', 2353, 'GUARDIAN', 'top 0.41% at peak'),
      ('codeforces', 'Codeforces', 'deen42', 1736, 'EXPERT', 'peak rating'),
      ('codechef', 'CodeChef', 'debanshu_42', 1900, '4-STAR', 'peak rating')]


def build_cp():
    for n, (slug, plat, handle, rating, title, sub) in enumerate(CP):
        W, H = 320, 200
        t0 = .15 + n * .25
        c, _ = chip(W - 16, 22, title, AMBER)
        b = [frame(W, H, 12), c,
             f'<text x="20" y="38" font-family="{SANS}" font-size="18" font-weight="700" fill="{TEXT}">{plat}</text>',
             f'<text x="20" y="57" font-family="{MONO}" font-size="11.5" fill="{MUTED}">@{esc(handle)}</text>']
        for k in range(6):
            b.append(f'<text class="cn" style="animation-delay:{t0 + .6 + k * .08:.2f}s" x="20" y="112" font-family="{SANS}" '
                     f'font-size="42" font-weight="700" fill="{MUTED}">{int(rating * k / 6):,}</text>')
        b.append(f'<text class="up" style="animation-delay:{t0 + 1.08:.2f}s" x="20" y="112" font-family="{SANS}" font-size="42" '
                 f'font-weight="700" fill="{AMBER}">{rating}</text>'
                 f'<text x="20" y="134" font-family="{SANS}" font-size="12" fill="{MUTED}">{esc(sub)}</text>')
        filled = round(rating / 2500 * 20)
        for k in range(20):
            b.append(f'<rect class="up" style="animation-delay:{t0 + .8 + k * .04:.2f}s" x="{20 + k * 14}" y="156" width="11" '
                     f'height="11" fill="{AMBER if k < filled else LINE}"/>')
        b.append(f'<text x="20" y="186" font-family="{MONO}" font-size="10" fill="{MUTED}">0</text>'
                 f'<text x="297" y="186" text-anchor="end" font-family="{MONO}" font-size="10" fill="{MUTED}">2500</text>')
        write(f'stats/{slug}.svg', svg_doc(W, H, f'{plat} @{handle}: peak rating {rating}, {title.lower()}, {sub}.', '\n'.join(b),
                                           CSS, pixels(0, 0, W, H, t0, .6, 300 + n)))


# ------------------------------------------------------------------ layout pieces
PHRASES = ['currently shipping low-latency systems at Edumorph', 'next stop: eBay, Summer 2027',
           'open to: backend · distributed systems · agentic AI', "let's build something fast."]


def build_layout():
    W, H = 1000, 24
    dots = ''.join(f'<rect class="up" style="animation-delay:{i * .012:.3f}s" x="{i * 12 + 4}" y="10" width="4" height="4" '
                   f'fill="{AMBER if i % 12 == 0 else LINE}"/>' for i in range(W // 12))
    write('layout/divider.svg', svg_doc(W, H, 'Divider', dots, CSS))

    W, H = 1000, 96
    body = (frame(W, H) + f'<text x="500" y="44" text-anchor="middle" font-family="{SANS}" font-size="18" font-weight="600" fill="{TEXT}">'
            f'Build with intent. Measure the impact. Keep shipping.</text><text x="500" y="70" text-anchor="middle" font-family="{MONO}" '
            f'font-size="12" letter-spacing="2" fill="{AMBER}">DEEN-42 / IIT KHARAGPUR</text>')
    write('layout/footer.svg', svg_doc(W, H, 'Build with intent. Measure the impact. Keep shipping.', body, CSS,
                                       pixels(0, 0, W, H, 0, 1, 31, cell=16)))

    # typewriter: four phrases on a 16 s loop, each typed by a stepping cover + cursor
    W, H, CYC, SLOT, CH, X0, Y = 1000, 120, 16, 4, 9.6, 52, 80
    css = CSS + [f'.tw{{animation:tw {CYC}s linear infinite both}}@keyframes tw{{0%,23%{{opacity:1}}23.5%,100%{{opacity:0}}}}']
    b = [frame(W, H), f'<text x="28" y="32" font-family="{MONO}" font-size="12" fill="{MUTED}">~/deen-42 <tspan fill="{LINE}">—</tspan> zsh</text>',
         f'<path d="M1 46H{W - 1}" stroke="{LINE}"/>', f'<text x="28" y="{Y}" font-family="{MONO}" font-size="16" font-weight="700" fill="{AMBER}">$</text>']
    for i, ph in enumerate(PHRASES):
        n, wpx, dly = len(ph), len(ph) * CH, (CYC - i * SLOT) % CYC
        css.append(f'.ty{i}{{animation:ty{i} {CYC}s infinite both}}@keyframes ty{i}{{0%{{transform:translateX(0);'
                   f'animation-timing-function:steps({n},end)}}{1.8 / CYC * 100:.2f}%,100%{{transform:translateX({wpx:.1f}px)}}}}')
        b.append(f'<g class="tw" style="animation-delay:-{dly}s"><text x="{X0}" y="{Y}" font-family="{MONO}" font-size="16" fill="{TEXT}" '
                 f'textLength="{wpx:.1f}" lengthAdjust="spacingAndGlyphs">{esc(ph)}</text><g class="ty{i}" style="animation-delay:-{dly}s">'
                 f'<rect x="{X0}" y="{Y - 18}" width="{wpx + 30:.0f}" height="26" fill="{BG}"/>'
                 f'<rect class="bk" x="{X0 + 1}" y="{Y - 15}" width="9" height="19" fill="{AMBER}"/></g></g>')
    b.append(f'<text x="{W - 28}" y="{H - 20}" text-anchor="end" font-family="{MONO}" font-size="11" letter-spacing="1.5" fill="{MUTED}">DEEN-42 · IIT KHARAGPUR</text>')
    write('layout/terminal.svg', svg_doc(W, H, 'Terminal: ' + ' / '.join(PHRASES), '\n'.join(b), css))


# ------------------------------------------------------------------ section icons for the README
SECTION_ICONS = ['hand', 'rocket', 'briefcase', 'graduation-cap', 'boxes', 'trophy', 'git-pull-request']


def build_icons():
    for n in SECTION_ICONS:
        write(f'icons/{n}.svg', f'<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" '
                                f'stroke="{AMBER}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                                f'<!-- Lucide "{n}" (ISC) -->{icon_body(n)}</svg>\n')


# ------------------------------------------------------------------ header GIF (optional)
def build_gif(src_path, out_rel='header/developer.gif', blk=7, steps=10):
    from PIL import Image, ImageSequence
    frames = [f.convert('RGB') for f in ImageSequence.Iterator(Image.open(src_path))]
    fw, fh = frames[0].size
    dark, amber, line = (13, 13, 13), (245, 165, 36), (38, 38, 38)

    def mosaic(img, b):
        return img if b <= 1 else img.resize((max(1, fw // b), max(1, fh // b)), Image.BOX).resize((fw, fh), Image.NEAREST)

    def blocks(img, shown, fresh=()):
        out = Image.new('RGB', (fw, fh), dark)
        for bx, by in shown:
            box = (bx * blk, by * blk, min(fw, (bx + 1) * blk), min(fh, (by + 1) * blk)); out.paste(img.crop(box), box[:2])
        for bx, by in fresh:
            out.paste(amber, (bx * blk, by * blk, min(fw, (bx + 1) * blk), min(fh, (by + 1) * blk)))
        return out

    rnd = random.Random(42)
    grid = [(x, y) for y in range(-(-fh // blk)) for x in range(-(-fw // blk))]; rnd.shuffle(grid)
    seq, dur = [Image.new('RGB', (fw, fh), dark)], [260]
    base = mosaic(frames[0], 14)
    for s in range(1, steps + 1):
        shown = grid[:len(grid) * s // steps]
        fresh = rnd.sample(shown[len(grid) * (s - 1) // steps:], k=14) if s < steps else []
        seq.append(blocks(base, shown, fresh)); dur.append(55)
    for b in (7, 4, 2): seq.append(mosaic(frames[0], b)); dur.append(80)
    seq += frames; dur += [70] * len(frames)
    for b in (2, 4, 7, 14): seq.append(mosaic(frames[-1], b)); dur.append(70)
    base = mosaic(frames[-1], 14)
    for s in range(steps - 1, -1, -1): seq.append(blocks(base, grid[:len(grid) * s // steps])); dur.append(45)
    seq = [Image.new('RGB', (fw + 2, fh + 2), line) for _ in seq] and [_border(f, line) for f in seq]
    sample = Image.new('RGB', ((fw + 2) * 4, fh + 2))
    for i, k in enumerate([0, 30, 60, len(seq) // 2]): sample.paste(seq[k], (i * (fw + 2), 0))
    sample.paste(Image.new('RGB', (8, 8), amber), (0, 0))
    pal = sample.quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    p = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in seq]
    out = os.path.join(ASSETS, out_rel); os.makedirs(os.path.dirname(out), exist_ok=True)
    p[0].save(out, save_all=True, append_images=p[1:], duration=dur, loop=0, optimize=True)
    print('gif', len(p), 'frames', os.path.getsize(out), 'bytes')


def _border(img, color):
    from PIL import Image
    out = Image.new('RGB', (img.width + 2, img.height + 2), color); out.paste(img, (1, 1)); return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--gif-source')
    a = ap.parse_args()
    build_icons(); build_header(); build_buttons(); build_lists(); build_cp(); build_layout()
    if a.gif_source: build_gif(a.gif_source)
    print('built assets in', ASSETS)
