#!/usr/bin/env python3
"""발굴 현황판 — 후보의 흐름과 수집이 살아 있는지를 한 화면에 놓는다.

**왜 따로 두는가.** 연구실 현황판은 '지금 돌고 있는 열 팀'을 본다.
발굴은 축이 다르다 — '다음에 무엇을 시작할 것인가'다. 섞으면 둘 다 흐려진다.

**무엇을 보여주는가.** 순위표를 그림으로 옮기는 것은 값이 적다(`_pool.md` 를 열면 된다).
정작 필요한 것은 2026-09-05 에 드러난 두 가지다:

  · **수집이 살아 있는가** — 9/1~9/4 나흘간 아무것도 받아오지 못했는데
    매일 '신규 문헌 없음'으로 보고돼 아무도 몰랐다.
  · **후보가 어디서 막혀 있는가** — I03 은 8/29 에 만들어져 1위인데 아직 채택되지 않았다.
    순위표만 보면 늙고 있다는 것이 보이지 않는다.

    python3 ideation_dashboard.py            # 만들고 경로를 찍는다
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace"); _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import os, io, re, sys, glob, html, datetime, collections

TEAM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IDEAS = os.path.join(TEAM, "ideas")
LOGS = os.path.join(TEAM, "brief", "logs")
OUT = os.path.join(IDEAS, "dashboard.html")

# 단계는 카드마다 꼬리말이 붙는다. 앞부분으로 하나로 모은다.
STAGE_ORDER = ["generated", "screened", "gap-verified", "adopted", "dropped"]
STAGE_KO = {
    "generated": "떠올림", "screened": "1차 거름", "gap-verified": "공백 확인",
    "adopted": "채택", "dropped": "폐기",
}


def norm_stage(v):
    v = re.sub(r"<[^>]+>|\*\*", "", v or "").strip().lower()
    for s in STAGE_ORDER:
        if v.startswith(s):
            return s
    return "generated"


def read_cards():
    out = []
    for f in sorted(glob.glob(os.path.join(IDEAS, "I*.md"))):
        s = io.open(f, encoding="utf8").read()
        m = re.search(r"^#\s+(I\d+)\s+(.*)$", s, re.M)
        if not m:
            continue
        card = {"id": m.group(1), "title": m.group(2).strip(), "file": os.path.basename(f)}
        for mm in re.finditer(r"^\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|$", s, re.M):
            k, v = mm.group(1).strip(), mm.group(2).strip()
            if k in ("항목",) or set(k) <= set("- "):
                continue
            card.setdefault(k, v)
        card["stage"] = norm_stage(card.get("단계"))
        card["q"] = section(s, "연구 질문", 400)
        card["why"] = (section(s, "왜 이 질문인가", 460) or section(s, "가설", 380)
                       or section(s, "발상", 380))
        card["gap"] = gap_line(s) or gap_bullet(s)
        card["feas"] = section(s, "실현 가능성", 300)
        card["refs"] = refs_in(s)
        out.append(card)
    return out


def section(text, name, limit=400):
    """카드의 한 절에서 첫 문단을 꺼낸다. 표·목록은 건너뛴다."""
    m = re.search(r"^##\s*%s.*?$(.*?)(?=^##\s|\Z)" % re.escape(name), text, re.M | re.S)
    if not m:
        return ""
    for para in m.group(1).strip().split("\n\n"):
        p = para.strip()
        if not p or p.startswith(("|", "-", "*", ">")):
            continue
        p = re.sub(r"\*\*|`", "", p)
        p = re.sub(r"\s+", " ", p).strip()
        return p[:limit] + ("…" if len(p) > limit else "")
    return ""


def gap_line(text):
    """'선행연구 지형' 표에서 **아직 답이 없는 것** 줄을 꺼낸다.

    발굴팀이 논문을 쌓는 팀이 아니라는 것이 여기서 드러난다 — 무엇이 이미 답해졌고
    무엇이 비어 있는지를 가려내는 것이 이 팀의 일이다."""
    m = re.search(r"^##\s*선행연구 지형.*?$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    if not m:
        return ""
    for row in re.finditer(r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|$", m.group(1), re.M):
        a, b = row.group(1), row.group(2)
        if "없음" in b or (a.startswith("**") and a.endswith("**")):
            return re.sub(r"\*\*|`", "", a).strip()
    return ""


def gap_bullet(text):
    """오래된 카드는 '갭 검증' 절에 판정을 글머리로 적었다. 거기서 꺼낸다."""
    m = re.search(r"^##\s*갭 검증.*?$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    if not m:
        return ""
    body = m.group(1)
    verdict = re.search(r"^-\s*판정:\s*(.+)$", body, re.M)
    kind = re.search(r"^-\s*공백 유형:\s*(.+)$", body, re.M)
    bits = []
    for x in (verdict, kind):
        if x:
            t = re.sub(r"\*\*|`", "", x.group(1)).strip()
            bits.append(re.sub(r"\s+", " ", t))
    return " · ".join(bits)[:220]


REF_RE = re.compile(r"(arXiv:\d{4}\.\d{4,5}|pmid:\d+|PMID\s*\d+|doi\s*10\.\S+?)(?=[\s,)\]。」]|$)")


def refs_in(text):
    """카드가 근거로 든 문헌. 어느 논문에서 이 생각이 나왔는지 보이게 한다."""
    seen, out = set(), []
    for m in REF_RE.finditer(text):
        r = m.group(1).strip().rstrip(".,)")
        k = r.lower().replace(" ", "")
        if k in seen:
            continue
        seen.add(k)
        if r.lower().startswith("arxiv:"):
            url = "https://arxiv.org/abs/" + r.split(":", 1)[1]
        elif r.lower().startswith("pmid"):
            url = "https://pubmed.ncbi.nlm.nih.gov/" + re.sub(r"\D", "", r) + "/"
        else:
            url = "https://doi.org/" + re.sub(r"^doi\s*", "", r, flags=re.I)
        out.append({"label": r, "url": url})
        if len(out) >= 6:
            break
    return out


def age_of(card, today):
    for k in ("생성일", "최종 갱신"):
        v = re.sub(r"[^\d-]", "", str(card.get(k, "")))[:10]
        try:
            return (today - datetime.date.fromisoformat(v)).days
        except Exception:
            continue
    return None


def pool_rank():
    """순위표에서 순위만 가져온다. 없으면 빈 dict."""
    p = os.path.join(IDEAS, "_pool.md")
    rank = {}
    if not os.path.exists(p):
        return rank
    for m in re.finditer(r"^\|\s*(\d+)\s*\|\s*\*{0,2}(I\d+)\*{0,2}\s*\|", io.open(p, encoding="utf8").read(), re.M):
        rank[m.group(2)] = int(m.group(1))
    return rank


# 이 날부터 '못 받아옴'과 '새 문헌 없음'을 구별할 수 있다. 그전 기록으로는 알 수 없다.
FAIL_DETECTION_SINCE = datetime.date(2000, 1, 1)   # 수집 실패를 "신규 없음"과 구별해 기록하기 시작한 날. 서식은 처음부터 구별한다


def collection(today, days=10):
    """최근 며칠간 몇 건을 모았고, 못 받아온 날이 있었는지."""
    rows = []
    for i in range(days - 1, -1, -1):
        d = (today - datetime.timedelta(days=i)).isoformat()
        n = 0
        for suffix in ("", "_watch"):
            p = os.path.join(IDEAS, "_incoming", f"{d}{suffix}.md")
            if os.path.exists(p):
                s = io.open(p, encoding="utf8").read()
                n += sum(int(x) for x in re.findall(r"^총 \*\*(\d+)건\*\*", s, re.M))
                n += sum(int(x) for x in re.findall(r"^\*\*(\d+)건\*\* 더 모았다", s, re.M))
        state = "ok" if n else (
            "none" if datetime.date.fromisoformat(d) >= FAIL_DETECTION_SINCE else "unknown")
        for p in glob.glob(os.path.join(LOGS, f"{d}_ideate*.log")):
            t = io.open(p, encoding="utf8", errors="replace").read()
            if "받아오지 못한" in t or "수집 실패" in t:
                state = "fail"
            elif "건너뜀" in t and n == 0 and state == "none":
                state = "skip"
        rows.append({"date": d, "n": n, "state": state})
    return rows


def esc(t):
    return html.escape(str(t or ""))


def read_incoming(days=7):
    """모아 둔 문헌을 날짜별·영역별로 읽는다.

    수집분은 지금까지 파일로만 있었다. 건수는 보이는데 무엇을 모았는지는 볼 수 없었다 —
    폴더를 열어야 했다. 발굴은 결국 '무엇이 나왔나'를 보는 일이므로 화면에 올린다.
    """
    out = []
    today = datetime.date.today()
    for i in range(days):
        d = (today - datetime.timedelta(days=i)).isoformat()
        for suffix, kind in (("", "발굴"), ("_watch", "감시")):
            p = os.path.join(IDEAS, "_incoming", f"{d}{suffix}.md")
            if not os.path.exists(p):
                continue
            txt = io.open(p, encoding="utf8").read()
            groups = []
            for gm in re.finditer(r"^##\s+(.+?)\s+—\s+(\d+)건\s*$(.*?)(?=^##\s|\Z)",
                                  txt, re.M | re.S):
                items = []
                for im in re.finditer(
                        r"^- \*\*(.+?)\*\*\s*\n\s+(.*?) · \[([^\]]+)\]\(([^)]+)\)\s*$",
                        gm.group(3), re.M | re.S):
                    items.append({"title": re.sub(r"\s+", " ", im.group(1)).strip(),
                                  "meta": re.sub(r"\s+", " ", im.group(2)).strip(),
                                  "id": im.group(3), "url": im.group(4)})
                if items:
                    groups.append({"label": re.sub(r"^\[감시\]\s*", "", gm.group(1)).strip(),
                                   "watch": gm.group(1).startswith("[감시]"), "items": items})
            if groups:
                out.append({"date": d, "kind": kind, "groups": groups,
                            "n": sum(len(g["items"]) for g in groups)})
    return out


def read_shelved():
    """카드가 되지 못한 착상. 폐기가 아니라 자리에서 밀린 것들이다.

    발굴팀은 한 번에 다섯 개까지만 카드로 만든다. 나머지는 `_generated_<날짜>.md` 에
    한 줄씩 남는데, 화면에 없으면 없는 것이나 같다 — 2026-09-05 에 '아이디어가 여섯 개가
    전부인가'라는 물음을 받고 넣었다. 자원이 풀리면 되살릴 수 있는 것들이다.
    """
    out = []
    for p in sorted(glob.glob(os.path.join(IDEAS, "_generated_*.md")), reverse=True):
        txt = io.open(p, encoding="utf8").read()
        date = re.sub(r"[^\d]", "", os.path.basename(p))[:8]
        date = "%s-%s-%s" % (date[:4], date[4:6], date[6:8]) if len(date) == 8 else date
        # '한 줄 | 발상 근거 | 밀린 이유' 표만 읽는다. 같은 파일에 통계 요약표도 있어서
        # 아무 표나 읽으면 '발상 축 3건' 같은 것이 착상으로 둔갑한다 (2026-09-05 실제로 그랬다).
        head = re.search(r"^\|\s*한 줄\s*\|.*$", txt, re.M)
        if not head:
            continue
        rows = []
        for line in txt[head.end():].splitlines():
            if not line.startswith("|"):
                if rows:
                    break
                continue
            cells = [re.sub(r"\*\*|`", "", c).strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 3 or set(cells[0]) <= set("- :"):
                continue
            rows.append({"one": cells[0], "src": cells[1], "why": cells[2]})
        if rows:
            out.append({"date": date, "rows": rows, "file": os.path.basename(p)})
    return out


def build():
    today = datetime.date.today()
    cards = read_cards()
    rank = pool_rank()
    coll = collection(today)
    incoming = read_incoming()
    shelved = read_shelved()

    by_stage = collections.Counter(c["stage"] for c in cards)
    alive = [c for c in cards if c["stage"] not in ("dropped",)]
    dropped = [c for c in cards if c["stage"] == "dropped"]
    waiting = [c for c in cards if c["stage"] == "gap-verified"]
    for c in cards:
        c["age"] = age_of(c, today)
        c["rank"] = rank.get(c["id"], 99)
    alive.sort(key=lambda c: (c["rank"], -(c["age"] or 0)))

    fails = [r for r in coll if r["state"] == "fail"]
    silent = [r for r in coll if r["state"] in ("none", "skip")]
    unknown = [r for r in coll if r["state"] == "unknown"]
    oldest = max((c["age"] or 0) for c in waiting) if waiting else 0

    L = []
    A = L.append
    A('<!doctype html>\n<html lang="ko">\n<head>\n<meta charset="utf-8">')
    A('<meta name="viewport" content="width=device-width,initial-scale=1">')
    A("<title>발굴 현황</title>")
    A('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Gowun+Dodum&display=swap">')
    A("""<style>
  /* 색과 서체는 문 페이지(_team/dashboard/door.html)와 맞춘다. 화면마다 다르면 남의 집 같다. */
  @font-face{font-family:"Pretendard";font-weight:45 920;font-display:swap;
    /* 서버로 열 때와 파일로 열 때 경로가 다르다. 둘 다 대면 브라우저가 되는 쪽을 쓴다. */
    src:url("Pretendard.woff2") format("woff2"),
        url("../dashboard/assets/Pretendard.woff2") format("woff2")}
  :root{--bg:#f4f3ed;--paper:#fffef9;--ink:#233d35;--muted:#626f65;--line:#d9dfd5;
        --soft:#e9ede3;--accent:#315e49;--hero:#183e30;--hero-text:#f1f5e9;
        --hero-muted:#b9cdbd;--gold:#dbeaaf;--bad:#8f3a2f;--warn:#9a6320;
        --shadow:0 2px 3px #192f2203,0 12px 32px #192f2206;color-scheme:light}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);padding:0 0 64px;
       font:15px/1.65 "Pretendard","Apple SD Gothic Neo",-apple-system,sans-serif;
       -webkit-font-smoothing:antialiased}
  .shell{max-width:1060px;margin:auto;padding:0 48px}
  .top{display:flex;justify-content:space-between;align-items:baseline;gap:20px;
       padding-block:27px;border-bottom:1px solid var(--line)}
  .brand{font-weight:650;letter-spacing:-.3px;font-size:17px}
  .brand small{display:block;font-size:10px;letter-spacing:1.8px;font-weight:500;color:var(--muted)}
  .date{font-size:12px;color:var(--muted)}
  .intro{padding-block:40px 26px}
  .eyebrow{font-size:11px;letter-spacing:2.1px;font-weight:600;color:var(--accent);margin:0 0 12px}
  .intro h1{font-size:clamp(27px,3.4vw,37px);font-weight:600;letter-spacing:-1.4px;margin:0}
  .lead{margin:12px 0 0;color:var(--muted);font-size:14px;word-break:keep-all;max-width:640px}
  section{margin-top:34px}
  h2{font-size:14px;font-weight:650;margin:0 0 14px;display:flex;align-items:baseline;gap:10px;
     letter-spacing:-.2px}
  h2 .n{font-size:11px;color:var(--muted);font-weight:400;font-variant-numeric:tabular-nums}
  .stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px}
  .stat{background:var(--paper);border:1px solid var(--line);border-radius:16px;
        padding:17px 19px;box-shadow:var(--shadow)}
  .stat .k{font-size:11px;letter-spacing:.4px;color:var(--muted)}
  .stat .v{font:31px/1.15 Georgia,serif;letter-spacing:-1px;margin-top:3px;
           font-variant-numeric:tabular-nums}
  .stat .d{font-size:11px;color:var(--muted);margin-top:4px}
  .stat.warn .v{color:var(--warn)} .stat.bad .v{color:var(--bad)} .stat.ok .v{color:var(--accent)}
  .funnel{display:flex;gap:10px;flex-wrap:wrap}
  .fstep{flex:1 1 120px;background:var(--paper);border:1px solid var(--line);
         border-radius:16px;padding:15px 17px;box-shadow:var(--shadow)}
  .fstep .k{font-size:11px;color:var(--muted)}
  .fstep .v{font:26px/1.2 Georgia,serif;letter-spacing:-.8px}
  .fstep.hot{border-color:var(--accent);background:var(--soft)}
  .item{background:var(--paper);border:1px solid var(--line);border-radius:16px;
        padding:19px 21px;box-shadow:var(--shadow);margin-bottom:12px}
  .ihead{display:flex;gap:12px;align-items:baseline;flex-wrap:wrap}
  .rank{font:italic 15px Georgia,serif;color:var(--muted);min-width:20px}
  .ititle{font-size:17px;font-weight:600;letter-spacing:-.4px}
  .q{color:var(--muted);font-size:13px;margin:8px 0 0;word-break:keep-all}
  .pill{display:inline-block;font-size:11px;padding:2px 9px;border-radius:99px;
        border:1px solid var(--line);color:var(--muted);white-space:nowrap}
  .pill.gap{border-color:var(--accent);color:var(--accent);background:var(--soft)}
  .pill.old{border-color:var(--warn);color:var(--warn)}
  .acts{display:flex;gap:8px;margin-top:14px;padding-top:13px;border-top:1px solid var(--line);
        align-items:center;flex-wrap:wrap}
  .acts button{font:inherit;font-size:12px;font-weight:600;padding:8px 15px;min-height:38px;
        border-radius:9px;border:1px solid var(--line);background:var(--paper);
        color:var(--ink);cursor:pointer}
  .acts button:hover{background:var(--soft)}
  .acts button:active{scale:.97}
  .acts button.adopt{background:var(--hero);color:var(--hero-text);border-color:var(--hero)}
  .acts button.adopt:hover{background:#12312576}
  .acts button.reject{color:var(--bad)}
  .acts button:disabled{opacity:.4;cursor:not-allowed}
  .acts .msg{font-size:12px;color:var(--muted)}
  .acts .msg.ok{color:var(--accent)} .acts .msg.err{color:var(--bad)}
  .bars{display:flex;gap:5px;align-items:flex-end;height:72px}
  .bar{flex:1;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;gap:5px}
  .bar i{display:block;width:100%;border-radius:4px 4px 0 0;background:var(--accent);min-height:3px}
  .bar.none i{background:var(--line)} .bar.fail i{background:var(--bad);min-height:12px}
  .bar b{font-size:10px;color:var(--muted);font-weight:400}
  .note{color:var(--muted);font-size:13px;background:var(--paper);border:1px solid var(--line);
        border-left:3px solid var(--warn);border-radius:12px;padding:14px 17px;margin:14px 0 0;
        word-break:keep-all}
  .note.ok{border-left-color:var(--accent)}
  table{width:100%;border-collapse:collapse;font-size:13px}
  td{padding:8px 10px;border-bottom:1px solid var(--line);color:var(--muted)}
  td b{color:var(--ink)}
  footer{border-top:1px solid var(--line);margin-top:40px;padding-top:20px;
         color:var(--muted);font-size:11px;letter-spacing:.4px}
  code{font:11px/1.6 ui-monospace,monospace;overflow-wrap:anywhere}
  .fld{margin-top:11px;padding-top:10px;border-top:1px solid var(--soft)}
  .fld .flabel{font-size:11px;font-weight:650;letter-spacing:.3px;color:var(--muted);
        margin-bottom:3px}
  .fld p{margin:0;font-size:13px;color:var(--ink);word-break:keep-all;line-height:1.6}
  .fld.gap{background:var(--soft);border-radius:10px;padding:11px 13px;border-top:none}
  .fld.gap .flabel{color:var(--accent)}
  .fld.gap p b{font-weight:650}
  .refs a{font-size:12px;color:var(--accent);text-decoration:none;
        border-bottom:1px solid transparent}
  .refs a:hover{border-bottom-color:var(--accent)}
  details.day{background:var(--paper);border:1px solid var(--line);border-radius:16px;
        padding:4px 20px;box-shadow:var(--shadow);margin-bottom:10px}
  details.day summary{cursor:pointer;padding:14px 0;font-size:14px;list-style:none;
        display:flex;align-items:center;gap:10px;min-height:44px}
  details.day summary::-webkit-details-marker{display:none}
  details.day summary::before{content:"▸";color:var(--muted);font-size:11px}
  details.day[open] summary::before{content:"▾"}
  table.shelf{margin:4px 0 14px}
  table.shelf th{font-size:11px;color:var(--muted);font-weight:650;text-align:left;
        padding:8px 10px;border-bottom:1px solid var(--line)}
  table.shelf td{vertical-align:top;font-size:13px;color:var(--muted);
        padding:9px 10px;border-bottom:1px solid var(--soft)}
  table.shelf td b{color:var(--ink);font-weight:600;display:block}
  table.shelf .meta{display:block;font-size:11px;color:var(--muted);margin-top:3px}
  .grp{padding:6px 0 14px}
  .glabel{font-size:12px;font-weight:650;color:var(--accent);padding:8px 0 6px;
        border-top:1px solid var(--line)}
  .glabel .n{font-weight:400;color:var(--muted)}
  ul.lit{list-style:none;margin:0;padding:0}
  ul.lit li{padding:7px 0;border-bottom:1px solid var(--soft)}
  ul.lit a{color:var(--ink);font-size:13px;line-height:1.5;text-decoration:none;
        word-break:keep-all}
  ul.lit a:hover{color:var(--accent);text-decoration:underline;text-underline-offset:3px}
  ul.lit .meta{display:block;font-size:11px;color:var(--muted);margin-top:2px}
  @media(max-width:760px){.shell{padding-inline:24px}}
</style>""")
    A("</head>\n<body>")
    A('<div class="shell">')

    A('<div class="top"><div class="brand">발굴<small>WHAT&rsquo;S NEXT</small></div>'
      '<div class="date">%s</div></div>' % today.isoformat())

    A('<div class="intro">')
    A('<p class="eyebrow">IDEATION</p>')
    A("<h1>다음에 무엇을 시작할 것인가</h1>")
    A('<p class="lead">발굴팀은 문헌을 쌓는 팀이 아니다. <b>무엇이 이미 답해졌고 무엇이 비어 있는지</b>를 '
      '가려 연구 질문으로 만든다. 문헌은 그 재료다. 판정은 여기서 내린다 — 누르는 순간 카드에 기록된다.</p>')
    A("</div>")

    # ---- 한눈에 ----
    A("<section>")
    A('<div class="stats">')
    A('<div class="stat"><div class="k">후보</div><div class="v">%d</div>'
      '<div class="d">살아 있는 것 %d · 기각 %d</div></div>' % (len(cards), len(alive), len(dropped)))
    cls = "warn" if oldest >= 7 else "ok"
    A('<div class="stat %s"><div class="k">판정 대기</div><div class="v">%d</div>'
      '<div class="d">%s</div></div>' % (cls, len(waiting),
      ("가장 오래된 것 %d일째" % oldest) if waiting else "없음"))
    tot = sum(r["n"] for r in coll)
    A('<div class="stat"><div class="k">최근 10일 수집</div><div class="v">%s</div>'
      '<div class="d">건</div></div>' % f"{tot:,}")
    if fails:
        A('<div class="stat bad"><div class="k">수집 실패</div><div class="v">%d</div>'
          '<div class="d">일 — 원천을 못 읽었다</div></div>' % len(fails))
    else:
        A('<div class="stat ok"><div class="k">수집</div><div class="v">정상</div>'
          '<div class="d">최근 10일 실패 없음</div></div>')
    A("</div></section>")

    # ---- 수집 ----
    A("<section>")
    A('<h2>수집이 살아 있는가 <span class="n">최근 10일</span></h2>')
    mx = max([r["n"] for r in coll] + [1])
    A('<div class="bars">')
    for r in coll:
        h = max(3, int(62 * r["n"] / mx)) if r["n"] else 4
        cls = {"fail": "fail", "none": "none", "skip": "none", "unknown": "none"}.get(r["state"], "")
        tip = "%s · %d건%s" % (r["date"][5:], r["n"],
                               " · 못 받아옴" if r["state"] == "fail" else "")
        A('<span class="bar %s" title="%s"><i style="height:%dpx"></i><b>%s</b></span>'
          % (cls, esc(tip), h, r["date"][8:]))
    A("</div>")
    if fails:
        A('<p class="note"><b>%d일은 자료를 받아오지 못했다.</b> 새 문헌이 없었던 것이 아니다 — '
          '수집을 손으로 돌리면(<code>python3 _team/scripts/discover.py --days 7</code>) 막힌 원천이 화면에 찍힌다.</p>' % len(fails))
    elif unknown:
        A('<p class="note"><b>%d일은 알 수 없다.</b> 2026-09-05 이전에는 &lsquo;못 받아옴&rsquo;과 '
          '&lsquo;새 문헌 없음&rsquo;을 구별하지 못했다 — 실패해도 &lsquo;신규 문헌 없음&rsquo;으로만 기록됐다.</p>'
          % len(unknown))
    else:
        A('<p class="note ok">최근 10일 동안 모든 원천을 정상적으로 읽었다.</p>')
    A("</section>")

    # ---- 흐름 ----
    A("<section>")
    A('<h2>후보는 어디까지 왔나 <span class="n">%d건</span></h2>' % len(cards))
    A('<div class="funnel">')
    for st in STAGE_ORDER:
        hot = "hot" if st == "gap-verified" and by_stage[st] else ""
        A('<div class="fstep %s"><div class="k">%s</div><div class="v">%d</div></div>'
          % (hot, STAGE_KO[st], by_stage[st]))
    A("</div>")
    if waiting:
        A('<p class="note"><b>공백 확인까지 끝난 %d건이 판정을 기다린다.</b> 여기가 병목이다 — '
          '다음 관문은 사람의 판정이다.</p>' % len(waiting))
    A("</section>")

    # ---- 후보 + 판정 ----
    A("<section>")
    A('<h2>발굴한 연구 질문 <span class="n">%d건 · 순위표 기준 · 누르면 카드에 기록된다</span></h2>' % len(alive))
    A('<p class="note" id="offline" hidden>이 화면을 <b>파일로 열면 판정할 수 없다</b> — 저장할 곳이 없기 때문이다. '
      '터미널에서 <code>python3 _team/scripts/ideas_server.py</code> 를 실행하고 '
      '<code>http://localhost:8790</code> 으로 여시라.</p>')
    for c in alive:
        rk = "—" if c["rank"] == 99 else str(c["rank"])
        age = c["age"]
        agecls = "old" if (age or 0) >= 7 and c["stage"] == "gap-verified" else ""
        stcls = "gap" if c["stage"] == "gap-verified" else ""
        A('<div class="item" data-id="%s">' % esc(c["id"]))
        A('<div class="ihead"><span class="rank">%s</span>'
          '<span class="ititle">%s %s</span>'
          '<span class="pill %s">%s</span><span class="pill %s">%s</span></div>'
          % (esc(rk), esc(c["id"]), esc(c["title"]), stcls, STAGE_KO[c["stage"]],
             agecls, ("%d일째" % age) if age is not None else "—"))
        if c["q"]:
            A('<p class="q">%s</p>' % esc(c["q"]))
        if c.get("why"):
            A('<div class="fld"><div class="flabel">왜 이 질문인가</div><p>%s</p></div>' % esc(c["why"]))
        if c.get("gap"):
            A('<div class="fld gap"><div class="flabel">아직 아무도 답하지 않은 것</div>'
              '<p><b>%s</b></p></div>' % esc(c["gap"]))
        if c.get("feas"):
            A('<div class="fld"><div class="flabel">이 연구실이 할 수 있는가</div><p>%s</p></div>'
              % esc(c["feas"]))
        if c.get("refs"):
            A('<div class="fld"><div class="flabel">이 생각이 나온 문헌</div><p class="refs">%s</p></div>'
              % " · ".join('<a href="%s" target="_blank" rel="noopener">%s</a>'
                           % (esc(r["url"]), esc(r["label"])) for r in c["refs"]))
        A('<div class="acts">'
          '<button class="adopt" data-d="채택">채택</button>'
          '<button data-d="보류">보류</button>'
          '<button class="reject" data-d="기각">기각</button>'
          '<span class="msg"></span></div>')
        A("</div>")
    A("</section>")

    # ---- 밀린 착상 ----
    if shelved:
        tot_s = sum(len(b["rows"]) for b in shelved)
        A("<section>")
        A('<h2>카드가 되지 못한 착상 <span class="n">%d건 · 폐기가 아니라 자리에서 밀린 것</span></h2>' % tot_s)
        A('<p class="note">발굴팀은 한 번에 다섯 개까지만 카드로 만든다. 아래는 그 자리에 들지 못한 것들이다. '
          '<b>밀린 이유가 풀리면 되살릴 수 있다</b> — 대개 자료를 갖고 있는지가 갈랐다.</p>')
        for b in shelved:
            A('<details class="day"%s>' % (" open" if b is shelved[0] else ""))
            A('<summary><b>%s</b> 착상 <span class="pill">%d건</span></summary>'
              % (esc(b["date"]), len(b["rows"])))
            A("<table class=\"shelf\">")
            A("<tr><th>한 줄</th><th>밀린 이유</th></tr>")
            for r in b["rows"]:
                A("<tr><td><b>%s</b><span class=\"meta\">근거 %s</span></td><td>%s</td></tr>"
                  % (esc(r["one"]), esc(r["src"][:80]), esc(r["why"][:130])))
            A("</table>")
            A("</details>")
        A("</section>")

    # ---- 모아 둔 문헌 ----
    if incoming:
        A("<section>")
        tot_in = sum(b["n"] for b in incoming)
        A('<h2>재료 — 모아 둔 문헌 <span class="n">최근 7일 · %d건 · 위 질문들이 여기서 나왔다</span></h2>' % tot_in)
        for b in incoming:
            A('<details class="day">')
            A('<summary><b>%s</b> %s <span class="pill">%d건</span></summary>'
              % (esc(b["date"]), esc(b["kind"]), b["n"]))
            for g in b["groups"]:
                A('<div class="grp"><div class="glabel">%s <span class="n">%d건</span></div>'
                  % (esc(g["label"][:80]), len(g["items"])))
                A("<ul class=\"lit\">")
                for it in g["items"]:
                    A('<li><a href="%s" target="_blank" rel="noopener">%s</a>'
                      '<span class="meta">%s · %s</span></li>'
                      % (esc(it["url"]), esc(it["title"]), esc(it["meta"]), esc(it["id"])))
                A("</ul></div>")
            A("</details>")
        A('<p class="note">원본은 <code>_team/ideas/_incoming/</code> 에 날짜별로 있다. '
          '이미 본 것은 <code>_seen.tsv</code> 로 걸러지므로 같은 논문이 두 번 오지 않는다.</p>')
        A("</section>")

    # ---- 기각 ----
    if dropped:
        A("<section>")
        A('<h2>기각·폐기 <span class="n">%d건 — 지우지 않고 모아 둔다</span></h2>' % len(dropped))
        A("<table>")
        for c in dropped:
            A("<tr><td><b>%s</b> %s</td><td>%s</td></tr>"
              % (esc(c["id"]), esc(c["title"]), esc(c.get("최종 갱신") or c.get("생성일") or "")))
        A("</table>")
        A('<p class="note">기각된 카드는 <code>_team/ideas/_dropped/</code> 로 옮겨진다. '
          '판정 기록은 <code>_decisions.tsv</code> 에 남으므로 되돌릴 수 있다.</p>')
        A("</section>")

    A("<footer>")
    A("<p>카드와 수집분에서 뽑아 쓴다 · 순위 근거 <code>_team/ideas/_pool.md</code> · "
      "전체 색인 <code>_backlog.md</code> · 우리가 낸 것은 <code>_ours.yaml</code> 로 수집에서 뺀다</p>")
    A("</footer>")

    A("""<script>
(function(){
  // 파일로 열면 저장할 곳이 없다. 그때는 단추를 잠그고 이유를 알린다.
  var live = location.protocol === "http:" || location.protocol === "https:";
  if (!live) {
    var n = document.getElementById("offline");
    if (n) n.hidden = false;
    document.querySelectorAll(".acts button").forEach(function(b){ b.disabled = true; });
    return;
  }
  document.querySelectorAll(".item").forEach(function(item){
    var id = item.dataset.id, msg = item.querySelector(".msg");
    item.querySelectorAll(".acts button").forEach(function(btn){
      btn.addEventListener("click", function(){
        var d = btn.dataset.d;
        var note = prompt(d + " 사유를 적어 주십시오. (그대로 카드에 남습니다)", "");
        if (note === null) return;
        item.querySelectorAll("button").forEach(function(b){ b.disabled = true; });
        msg.className = "msg"; msg.textContent = "기록하는 중…";
        fetch("/decide", {method:"POST", headers:{"Content-Type":"application/json"},
                          body: JSON.stringify({id:id, decision:d, note:note})})
          .then(function(r){ return r.json(); })
          .then(function(r){
            if (r.ok) { msg.className = "msg ok"; msg.textContent = d + " — 기록됨. 새로 고치면 반영됩니다."; }
            else { msg.className = "msg err"; msg.textContent = r.error || "실패";
                   item.querySelectorAll("button").forEach(function(b){ b.disabled = false; }); }
          })
          .catch(function(e){
            msg.className = "msg err"; msg.textContent = "서버에 닿지 못했습니다: " + e;
            item.querySelectorAll("button").forEach(function(b){ b.disabled = false; });
          });
      });
    });
  });
})();
</script>""")
    A("</div>\n</body>\n</html>")
    return "\n".join(L)


def main():
    doc = build()
    tmp = OUT + ".tmp.%d" % os.getpid()
    io.open(tmp, "w", encoding="utf8").write(doc)
    os.replace(tmp, OUT)
    print("발굴 현황판 → %s (%.0f KB)" % (os.path.relpath(OUT, TEAM), len(doc.encode()) / 1024))


if __name__ == "__main__":
    main()
