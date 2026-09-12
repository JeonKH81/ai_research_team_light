#!/usr/bin/env python3
"""현황판 숫자 갱신 — 매일 아침. LLM을 쓰지 않는다.

`source.html`의 `<!--AUTO:이름-->…<!--/AUTO:이름-->` 구역만 다시 만든다.
표시 밖의 문장과 해석은 건드리지 않는다 — 그건 판단이고, 랩미팅에서 사람이 손본다.

갱신하는 구역:
  stamp     기준 날짜
  stats     통계 5칸 (플랜 한도 카드는 수동값이라 그대로 옮긴다)
  teams     10개 팀 줄 — 단계·배지·색
  aging     마지막 활동으로부터 경과일 (파일 수정시각 기준)
그리고 `const TEAMS` 안의 stage·badge·path.

파이프라인 흐름도(SVG)와 대기 카드는 갱신하지 않는다 — 좌표와 분류가 판단이라
기계가 건드리면 조용히 어긋난다. 랩미팅에서 손본다.

  refresh.py          갱신 후 build.py 로 구조 검사
  refresh.py --dry    무엇이 바뀌는지만 출력
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace"); _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import os, re, sys, json, glob, argparse, datetime, subprocess, collections

try:
    import yaml
except ImportError:
    sys.exit("PyYAML 필요")

HERE = os.path.dirname(os.path.abspath(__file__))
TEAM = os.path.dirname(HERE)
ROOT = os.path.dirname(TEAM)
SRC = os.path.join(HERE, "source.html")

SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".ipynb_checkpoints", "_workspace"}
CARDS = {"PROJECT.md", "CLAUDE.md"}
GLYPH = {  # 행성 마크 — 팀마다 고정
 "Mercury": '<circle cx="30" cy="30" r="11" fill="var(--surface-2)" stroke="%s" stroke-width="4"/>',
 "Venus": '<circle cx="30" cy="30" r="15" fill="%s" fill-opacity=".18" stroke="%s" stroke-width="4"/>',
 "Terra": '<circle cx="30" cy="30" r="15" fill="var(--surface-2)" stroke="%s" stroke-width="4"/><path d="M30 15a15 15 0 0 1 0 30" fill="%s" fill-opacity=".25"/>',
 "Mars": '<circle cx="30" cy="30" r="10" fill="%s" fill-opacity=".18" stroke="%s" stroke-width="4"/>',
 "Jupiter": '<circle cx="30" cy="30" r="22" fill="var(--surface-2)" stroke="%s" stroke-width="4"/><path d="M11 23h38M13 37h34" stroke="%s" stroke-width="3.4" stroke-opacity=".5"/>',
 "Saturn": '<ellipse cx="30" cy="30" rx="27" ry="8" fill="none" stroke="%s" stroke-width="3.4" transform="rotate(-18 30 30)"/><circle cx="30" cy="30" r="13" fill="var(--surface-2)" stroke="%s" stroke-width="4"/>',
 "Uranus": '<ellipse cx="30" cy="30" rx="8" ry="26" fill="none" stroke="%s" stroke-width="3.4"/><circle cx="30" cy="30" r="12" fill="var(--surface-2)" stroke="%s" stroke-width="4"/>',
 "Neptune": '<circle cx="30" cy="30" r="15" fill="%s" fill-opacity=".18" stroke="%s" stroke-width="4"/>',
 "Ceres": '<circle cx="30" cy="30" r="9" fill="var(--surface-2)" stroke="%s" stroke-width="3.4" stroke-dasharray="5 5"/>',
 "Pluto": '<circle cx="30" cy="30" r="7" fill="var(--surface-2)" stroke="%s" stroke-width="3.4" stroke-dasharray="5 5"/>',
}
GLYPH_ANY = '<circle cx="30" cy="30" r="14" fill="var(--surface-2)" stroke="%s" stroke-width="4"/>'


def newest(path):
    """연구 파일의 최신 수정일. 카드·작업폴더는 활동으로 세지 않는다."""
    if not os.path.isdir(path):
        return None
    best = 0
    for dp, dns, fns in os.walk(path):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        for fn in fns:
            if fn in CARDS or fn.startswith((".", "~$")):
                continue
            try:
                best = max(best, os.path.getmtime(os.path.join(dp, fn)))
            except OSError:
                pass
    return datetime.date.fromtimestamp(best) if best else None


def state():
    reg = yaml.safe_load(open(os.path.join(TEAM, "registry.yaml"), encoding="utf8"))
    tms = yaml.safe_load(open(os.path.join(TEAM, "teams.yaml"), encoding="utf8"))
    today = datetime.date.today()
    by = {p.get("team"): p for p in reg["projects"]}
    rows = []
    for t in tms["teams"]:
        p = by.get(t["name"])
        age = None
        if p:
            d = p["path"] if os.path.isabs(p["path"]) else os.path.join(ROOT, p["path"])
            m = newest(d)
            age = (today - m).days if m else None
        rows.append({"name": t["name"], "ko": t["ko"], "code": t.get("code"),
                     "label": t.get("label"), "project": t.get("project"),
                     "stage": (p or {}).get("stage", "idle"),
                     "blockers": len((p or {}).get("blockers") or []),
                     "age": age, "key": t["name"].lower()})
    return reg, rows


def badge(r):
    """상태 배지 — 배지 문구는 기계가 정할 수 있는 만큼만 정한다."""
    st = r["stage"]
    if st == "idle" or not r["project"]:
        return "idle", "프로젝트 미배정", "a-idle"
    if st == "onhold":
        return "idle", "PI 보류", "a-idle"
    if st in ("submitted", "published"):
        return "ok", ("투고 완료" if st == "submitted" else "게재"), "a-ok"
    if r["age"] is not None and r["age"] >= 60:
        return "crit", "정체 %d일" % r["age"], "a-crit"
    if r["blockers"] == 0:
        return "ok", "진행 중", "a-ok"
    return "warn", "대기 %d건" % r["blockers"], "a-warn"  # 연구가 기다리는 것


def lab_name():
    """연구실 이름 — `_team/lab.yaml` 의 lab_name, 없으면 `_team/LAB_NAME` 한 줄, 없으면 일반 문구."""
    try:
        sys.path.insert(0, os.path.join(TEAM, "scripts"))
        import labconfig
        v = labconfig.load().get("lab_name")
        if v and v != "AI Research Team":
            return v
    except Exception:
        pass
    p = os.path.join(TEAM, "LAB_NAME")
    try:
        v = open(p, encoding="utf8").readline().strip()
        if v:
            return v
    except OSError:
        pass
    return "1인 AI 연구실"


def block_stamp(reg, rows, now):
    return ("      %s 기준<br>\n      %s<br>\n"
            "      1인 연구실 · 팀 10 · 연구원 11" % (now.strftime("%Y-%m-%d %H:%M"), lab_name()))


def _card_sections(path):
    """PROJECT.md 를 '## 제목' 단위로 나눈다. 없으면 빈 표."""
    try:
        txt = open(path, encoding="utf8").read()
    except OSError:
        return {}
    out, cur = {}, None
    for line in txt.split("\n"):
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            cur = m.group(1).strip(); out[cur] = []
        elif cur is not None:
            out[cur].append(line)
    return {k: "\n".join(v).strip() for k, v in out.items()}


def _bullets(text, n=5):
    """절 본문에서 글머리 줄만 n개. 표·코드는 건너뛴다."""
    got = []
    for line in (text or "").split("\n"):
        t = line.strip()
        if t.startswith(("- ", "* ")) or re.match(r"^\d+\.\s", t):
            t = re.sub(r"^(- |\* |\d+\.\s)", "", t)
            t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
            t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
            got.append(t)
        if len(got) >= n:
            break
    return got


def _first_para(text):
    for para in re.split(r"\n\s*\n", text or ""):
        p = para.strip()
        if p and not p.startswith(("|", ">", "#", "```")):
            return re.sub(r"\s+", " ", p)
    return ""


def teams_js(reg, rows):
    """화면의 팀 상세 패널과 연구원 대화가 쓰는 팀 자료. 등록부와 카드에서 만든다 — 손으로 쓰지 않는다."""
    by = {p.get("team"): p for p in reg["projects"]}
    out = []
    for r in rows:
        p = by.get(r["name"]) or {}
        cls, text, _ = badge(r)
        sec = {}
        if p.get("path"):
            d = p["path"] if os.path.isabs(p["path"]) else os.path.join(ROOT, p["path"])
            sec = _card_sections(os.path.join(d, "PROJECT.md"))
        def pick(*names):
            for n in names:
                for k in sec:
                    if k.startswith(n):
                        return sec[k]
            return ""
        out.append({
            "k": r["key"], "name": r["name"], "code": r["code"] or "미배정", "ko": r["ko"],
            "acc": cls, "badge": [cls, text], "stage": r["stage"] if r["project"] else "idle",
            "title": p.get("title") or ("미배정 — 다음 프로젝트 대기"),
            "path": p.get("path") or "",
            "q": _first_para(pick("연구 질문", "연구질문")),
            "design": _bullets(pick("설계")),
            "status": _bullets(pick("현재 상태", "현재 진행")),
            "todo": _bullets(pick("다음 마일스톤", "다음 할 일", "다음")),
            "blockers": list(p.get("blockers") or []),
            "facts": [], "warn": "", "blocknote": "",
        })
    return out


def block_stats(reg, rows, now):
    act = sum(1 for r in rows if r["project"] and r["stage"] not in ("idle", "onhold"))
    hold = sum(1 for r in rows if r["stage"] == "onhold")
    wait = sum(1 for r in rows if not r["project"])
    stall = [r for r in rows if r["age"] is not None and r["age"] >= 60 and r["stage"] not in ("onhold", "idle")]
    blk = sum(r["blockers"] for r in rows)
    sub = [r for r in rows if r["stage"] in ("submitted", "published")]
    L = []
    L.append('    <div class="stat s-acc"><div class="k">가동 중인 팀</div><div class="v num">%d</div>' % act)
    L.append('      <div class="d">보류 %d · 미배정 %d · 고정 10</div></div>' % (hold, wait))
    L.append('    <div class="stat s-crit"><div class="k">정체</div><div class="v num">%d</div>' % len(stall))
    L.append('      <div class="d">%s</div></div>' % (" · ".join("%s %d일" % (r["name"], r["age"]) for r in stall) or "없음"))
    L.append('    <div class="stat s-warn"><div class="k">대기</div><div class="v num">%d</div>' % blk)
    L.append('      <div class="d">팀별 상세는 registry.yaml</div></div>')
    L.append('    <div class="stat s-ok"><div class="k">투고</div><div class="v num">%d</div>' % len(sub))
    L.append('      <div class="d">%s</div></div>' % (" · ".join(r["label"] for r in sub) or "없음"))
    # 플랜 한도는 손으로 넣는 값이라 있던 것을 그대로 옮긴다
    L.append(PLAN_CARD)
    return "\n".join(L)


def block_teams(reg, rows, now):
    order = {"ok": 0, "warn": 1, "crit": 2, "idle": 3}
    rs = sorted(rows, key=lambda r: (order[badge(r)[0]], -(r["age"] or 0)))
    out = []
    for r in rs:
        cls, text, acc = badge(r)
        col = {"ok": "var(--ok)", "warn": "var(--warn)", "crit": "var(--crit)", "idle": "var(--ink-3)"}[cls]
        g = GLYPH.get(r["name"], GLYPH_ANY)   # 태양계가 아닌 팀 이름이면 공통 그림
        g = g % ((col,) * g.count("%s"))
        idle = " idle" if cls == "idle" else ""
        pj = r["project"] or "— 다음 프로젝트 대기"
        code = r["code"] or "미배정"
        out.append(
            '      <a class="trow %s" href="#" data-team="%s" role="button">\n'
            '        <svg class="g" viewBox="0 0 60 60" aria-hidden="true">%s</svg>\n'
            '        <i class="b b-%s%s"></i>\n'
            '        <div class="id"><span class="pl">%s</span><span class="cd">_%s</span>\n'
            '          <span class="ko">%s</span></div>\n'
            '        <div class="pj">%s</div>\n'
            '        <div class="stg">%s</div>\n'
            '        <div class="st"><span class="pill %s">%s</span></div>\n'
            '      </a>' % (acc, r["key"], g, r["key"], idle, r["name"], code,
                            r["ko"], pj, "" if not r["project"] else r["stage"], cls, text))
    return "\n".join(out)


def block_aging(reg, rows, now):
    rs = [r for r in rows if r["age"] is not None and r["project"]]
    rs.sort(key=lambda r: r["age"])
    mx = max([r["age"] for r in rs] + [1])
    L = ['      <div class="bars">']
    for r in rs:
        pct = r["age"] / mx * 100
        cls = "crit" if r["age"] >= 60 else "ok"
        d = (now.date() - datetime.timedelta(days=r["age"])).strftime("%m-%d")
        lab = "%d일 · %s" % (r["age"], d)
        pos = ('right:calc(%.1f%% + 12px);color:var(--on-mark)' % (100 - pct)) if pct >= 55 \
              else ('left:calc(%.1f%% + 12px);color:var(--%s-text)' % (pct, cls))
        L.append('        <div class="bar-row"><div class="bar-id">%s</div>' % r["label"])
        L.append('          <div class="bar-track"><div class="bar-fill %s" style="width:%.1f%%"></div>' % (cls, max(pct, 0.6)))
        L.append('            <div class="bar-lab" style="%s">%s</div></div></div>' % (pos, lab))
    L.append("      </div>")
    return "\n".join(L)


def usage_data(days=14):
    """사용량은 대화 기록에서 센다. usage.py 가 두 컴퓨터 몫을 합쳐 준다."""
    try:
        import importlib.util
        sp = importlib.util.spec_from_file_location("ug", os.path.join(TEAM, "scripts", "usage.py"))
        m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
        return m.collect(days), m.human
    except Exception:
        return None, None


def josa(word, pair=("이", "가")):
    """받침이 있으면 앞것, 없으면 뒷것. 팀 이름이 바뀌어도 문장이 어색해지지 않게."""
    ch = word.strip()[-1:] if word else ""
    if not ch:
        return pair[1]
    if "가" <= ch <= "힣":
        return pair[0] if (ord(ch) - 0xAC00) % 28 else pair[1]
    if ch.isdigit():
        return pair[0] if ch in "0136780" else pair[1]
    return pair[0] if ch.lower() in "lmnr" else pair[1]


def block_usage(reg, rows, now):
    r, human = usage_data(14)
    if not r:
        return '      <p class="note">사용량을 읽지 못했다 — <code>_team/scripts/usage.py</code> 를 확인하라.</p>'

    def big(v):
        t = human(v)
        if t and t[-1] in "KMB":
            return '%s<span style="font-size:24px">%s</span>' % (t[:-1], t[-1])
        return t

    t = r["totals"]
    models = " · ".join("%s %d" % (k, v) for k, v in r["models"]
                        if not k.startswith("<"))[:80] or "—"
    L = ['      <div class="stats" style="margin-bottom:16px">']
    L.append('        <div class="stat s-acc"><div class="k">신규 입력</div><div class="v num">%s</div>' % big(t["fresh"]))
    L.append('          <div class="d">새로 읽은 토큰</div></div>')
    L.append('        <div class="stat"><div class="k">캐시 읽기</div><div class="v num">%s</div>' % big(t["cache"]))
    L.append('          <div class="d">재사용 — 훨씬 싸다</div></div>')
    L.append('        <div class="stat s-ok"><div class="k">출력</div><div class="v num">%s</div>' % big(t["out"]))
    L.append('          <div class="d">생성된 토큰</div></div>')
    L.append('        <div class="stat s-warn"><div class="k">응답 수</div><div class="v num">%s</div>' % "{:,}".format(t["n"]))
    L.append('          <div class="d">%s</div></div>' % models)
    L.append('      </div>')

    # 세로축은 실제 최대값에 맞춰 잡는다. 고정하면 하루 튀는 날에 그래프가 잘린다.
    peak = max([x["total"] for x in r["series"]] + [1])
    step = 50_000_000
    axis = max(step, ((peak + step - 1) // step) * step)
    L.append('      <div class="panel" style="padding:22px 24px 18px">')
    L.append('        <div class="uhd">일별 총 토큰 <span>세로축 최대 %s</span></div>' % human(axis))
    cells = []
    for x in r["series"]:
        d = x["date"][5:]
        if x["total"] == 0:
            cells.append('<span class="c" title="%s · 0"></span>' % d)
        else:
            h = 100.0 * x["total"] / axis
            cells.append('<span class="c" title="%s · %s"><span class="b" style="height:%.1f%%"></span></span>'
                         % (d, human(x["total"]), h))
    L.append('        <div class="uplot">%s</div>' % "".join(cells))
    dates = [x["date"][5:] for x in r["series"]]
    marks = [dates[i] for i in (0, len(dates)//4, len(dates)//2, 3*len(dates)//4, len(dates)-1)] if dates else []
    L.append('        <div class="uaxis">%s</div>' % "".join("<span>%s</span>" % d for d in marks))

    L.append('        <div class="uhd" style="margin-top:28px">팀별 누적 <span>최근 14일</span></div>')
    tot = sum(v for _, v in r["by_team"]) or 1
    rowsx = []
    for team, v in r["by_team"][:6]:
        rowsx.append('<div class="ur"><div class="un">%s</div><div class="ut"><div class="uf" style="width:%.1f%%"></div></div><div class="uv">%s</div></div>'
                     % (team, 100.0 * v / tot, human(v)))
    L.append('        <div class="ulist">%s</div>' % "".join(rowsx))
    L.append('      </div>')

    ratio = (t["cache"] / t["fresh"]) if t["fresh"] else 0
    top = r["by_team"][0] if r["by_team"] else ("—", 0)
    alltop = r["alltime_by_team"][0] if r["alltime_by_team"] else ("—", 0)
    L.append('      <p class="note">')
    L.append('        캐시 읽기가 신규 입력의 <b>%.0f배</b>다 — 같은 맥락을 반복해서 다시 읽지 않고 재사용했다는 뜻이고, 그만큼 값이 싸다.' % ratio)
    L.append('        최근 14일에는 <b>%s</b>%s <b>%s</b>로 가장 많고, 전체 기간 누계는 <b>%s</b>%s <b>%s</b>다.'
             % (top[0], josa(top[0]), human(top[1]), alltop[0], josa(alltop[0]), human(alltop[1])))
    L.append('      </p>')
    return "\n".join(L)


def block_nextmeeting(reg, rows, now):
    """다음 랩미팅. 요일·시각·간격은 _team/lab.yaml 이 정한다.

    2026-09-06 확인: 이 칸이 '2026-09-01 첫 랩미팅'에 멈춰 있었다. 손으로 쓴 문장이었다.
    날짜는 계산하면 되는 것이므로 계산한다.
    """
    d = now.date()
    sys.path.insert(0, os.path.join(TEAM, "scripts"))
    import labconfig
    _cfg = labconfig.load()
    nxt = labconfig.next_meeting(_cfg, now)
    if nxt is None:
        return ('        <div class="ck">다음 랩미팅</div>\n'
                '        <p>정기 랩미팅을 <b>하지 않기로</b> 설정돼 있다(<span class="code">_team/lab.yaml</span>).'
                ' 필요할 때 <span class="code">/lab-meeting</span> 으로 연다.</p>')
    _m = _cfg["schedule"]["lab_meeting"]
    _hh, _mm = labconfig.hm(_m.get("time"), (7, 0))
    _ph, _pm = labconfig.hm(_m.get("prep"), (6, 0))
    agenda = os.path.join(TEAM, "lab_meetings", "%s_agenda.md" % nxt.isoformat())
    minutes = os.path.join(TEAM, "lab_meetings", "%s.md" % nxt.isoformat())
    prepared = "준비됨" if os.path.exists(agenda) or os.path.exists(minutes) else "준비 전"
    days = (nxt - d).days
    when = "오늘" if days == 0 else ("내일" if days == 1 else "%d일 뒤" % days)

    # 지난 회의
    import glob as _g
    past = sorted(x for x in _g.glob(os.path.join(TEAM, "lab_meetings", "20*.md"))
                  if "_agenda" not in x)
    last = os.path.basename(past[-1])[:-3] if past else None

    # 판정을 기다리는 것
    pend = 0
    ib = os.path.join(TEAM, "inbox")
    if os.path.isdir(ib):
        for p in _g.glob(os.path.join(ib, "*.md")):
            if os.path.basename(p) == "README.md":
                continue
            t = open(p, encoding="utf8", errors="replace").read().split("---")
            if len(t) > 2 and "decision:" in t[1]:
                dec = [l for l in t[1].splitlines() if l.strip().startswith("decision:")]
                if dec and not dec[0].split(":", 1)[1].strip():
                    pend += 1

    L = ['        <div class="ck">다음 랩미팅</div>']
    _every = max(1, int(_m.get("interval_weeks", 1) or 1))
    L.append('        <p><b>%s(%s) %02d:%02d</b> — %s. 그날 총괄팀장 창에서 <span class="code">/lab-meeting</span> 으로 연다(%s).%s'
             % (nxt.isoformat(), "월화수목금토일"[nxt.weekday()], _hh, _mm, when, prepared,
                "" if _every == 1 else " %d주마다." % _every))
    if last:
        L.append('        지난 회의는 <span class="code">_team/lab_meetings/%s.md</span>.' % last)
    if pend:
        L.append('        <b>제안 큐에 판정 대기 %d건</b>이 올라와 있다.' % pend)
    L.append('        순서는 액션아이템 점검 → 진행 팀 리뷰 → 신규 주제 심의 → 우선순위.</p>')
    return "\n".join(L)


def block_blockers(reg, rows, now):
    """무엇이 기다리고 있는가 — registry 의 대기와 오래 남은 미해결에서 뽑는다.

    2026-09-06 확인: 이 절이 손으로 쓴 8/31 목록에 멈춰 있었다. 그사이 Venus 의 대기 3건이
    사라졌는데도 그대로 남아 있었다. 정본에서 뽑으면 어긋나지 않는다.
    """
    today = now.date()
    items = []
    for p in reg["projects"]:
        label = p.get("label") or p.get("team")
        for b in (p.get("blockers") or []):
            items.append({"label": label, "what": str(b), "days": None, "who": None})
        for it in (p.get("open_items") or []):
            if str(it.get("status", "open")) != "open":
                continue
            try:
                d = (today - datetime.date.fromisoformat(str(it.get("since")))).days
            except Exception:
                d = None
            items.append({"label": label, "what": str(it.get("what")),
                          "days": d, "who": it.get("who"),
                          "done": it.get("done_when")})
    if not items:
        return '      <p class="note">기다리는 것이 없다.</p>'

    items.sort(key=lambda x: -(x["days"] or 0))
    L = ['      <div class="stats" style="margin-bottom:18px">']
    L.append('        <div class="stat s-warn"><div class="k">대기</div><div class="v num">%d</div>'
             '<div class="d">누군가의 결정이나 작업을 기다린다</div></div>' % len(items))
    old = [i for i in items if (i["days"] or 0) >= 90]
    if old:
        L.append('        <div class="stat s-crit"><div class="k">90일 넘음</div>'
                 '<div class="v num">%d</div><div class="d">굳고 있다</div></div>' % len(old))
    byteam = {}
    for i in items:
        byteam.setdefault(i["label"], 0)
        byteam[i["label"]] += 1
    worst = sorted(byteam.items(), key=lambda kv: -kv[1])[0]
    L.append('        <div class="stat"><div class="k">가장 많은 팀</div><div class="v num">%d</div>'
             '<div class="d">%s</div></div>' % (worst[1], worst[0]))
    L.append('      </div>')

    L.append('      <div class="panel" style="padding:18px 22px">')
    cur = None
    for i in items:
        if i["label"] != cur:
            cur = i["label"]
            L.append('        <div class="bkteam">%s</div>' % cur)
        age = ""
        if i["days"] is not None:
            age = ' <span class="bkage%s">%d일째</span>' % (
                " bkold" if i["days"] >= 90 else "", i["days"])
        who = ' <span class="bkwho">%s</span>' % i["who"] if i.get("who") else ""
        L.append('        <div class="bkrow">%s%s%s</div>' % (i["what"][:150], age, who))
        if i.get("done"):
            L.append('        <div class="bkdone">끝나는 조건 — %s</div>' % i["done"][:150])
    L.append('      </div>')
    L.append('      <p class="note">`registry.yaml` 의 <code>blockers</code> 와 <code>open_items</code> 에서 '
             '뽑아 쓴다. 손으로 고치지 마라 — 상태를 바꾸려면 <code>report.py status</code> 로 정본을 고쳐라.</p>')
    return "\n".join(L)


def worklog_hours(days=14):
    try:
        sys.path.insert(0, os.path.join(TEAM, "scripts"))
        import importlib.util
        sp = importlib.util.spec_from_file_location("wt", os.path.join(TEAM, "scripts", "worktime.py"))
        m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
        return m.daily_hours(m.load_events())
    except Exception:
        return {}


def block_worktime(reg, rows, now):
    tbl = worklog_hours()
    days = [(now.date() - datetime.timedelta(days=i)) for i in range(13, -1, -1)]
    keys = [d.isoformat() for d in days]
    MX = 2.5
    label = {r["name"]: r["label"] for r in rows}
    label["연구실 운영"] = "연구실 운영"
    ent = sorted(tbl.items(), key=lambda kv: -sum(kv[1].get(k, 0) for k in keys))
    L = ['      <div class="spark">']
    seen = set()
    for team, per in ent:
        vals = [per.get(k, 0) for k in keys]
        if sum(vals) == 0:
            continue
        seen.add(team)
        cols = "".join(
            ('<span class="c" title="%s %.1fh"><span class="b" style="height:%.1f%%"></span></span>'
             % (keys[i][5:], v, min(v / MX * 100, 100))) if v > 0
            else '<span class="c" title="%s 0"></span>' % keys[i][5:]
            for i, v in enumerate(vals))
        cls = " ops" if team == "연구실 운영" else ""
        L.append('      <div class="sp-row%s">\n        <div class="sp-name">%s</div>\n'
                 '        <div class="sp-plot">%s</div>\n        <div class="sp-tot">%.1fh</div>\n      </div>'
                 % (cls, label.get(team, team), cols, sum(vals)))
    for r in rows:
        if r["name"] in seen:
            continue
        note = "미배정" if not r["project"] else ("보류" if r["stage"] == "onhold" else "이 기간 0")
        L.append('      <div class="sp-row">\n        <div class="sp-name mute">%s</div>\n'
                 '        <div class="sp-plot empty"><span>%s</span></div>\n'
                 '        <div class="sp-tot zero">—</div>\n      </div>' % (r["label"], note))
    L.append("      </div>")
    # 날짜 눈금도 여기서 만든다. 2026-09-06 이전에는 이 눈금이 자동 구역 **밖**에 있어
    # 08-18~08-31 에 멈춰 있었다 — 막대는 오늘까지인데 축만 옛날이었다.
    marks = [0, len(days)//4, len(days)//2, 3*len(days)//4, len(days)-1]
    L.append('      <div class="sp-axis">')
    L.append('        <div></div>')
    L.append('        <div class="d">%s</div>'
             % "".join("<span>%s</span>" % days[k].strftime("%m-%d") for k in marks))
    L.append('        <div></div>')
    L.append('      </div>')
    L.append('      <div class="sp-legend">세로축 최대 %.1f시간 · 15분 이상 끊긴 구간은 제외 · '
             '최근 14일 (%s ~ %s)</div>' % (MX, days[0].strftime("%m-%d"), days[-1].strftime("%m-%d")))
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    html = open(SRC, encoding="utf8").read()
    global PLAN_CARD
    m = re.search(r'(    <div class="stat s-acc plan5">.*?\n    </div>)', html, re.S)
    PLAN_CARD = m.group(1) if m else ""

    reg, rows = state()
    now = datetime.datetime.now()
    changed = []
    for name, fn in (("stamp", block_stamp), ("stats", block_stats), ("teams", block_teams),
                     ("aging", block_aging), ("blockers", block_blockers),
                     ("nextmeeting", block_nextmeeting)):
        # 표시 사이가 비어 있어도 찾도록 줄바꿈을 느슨하게 본다.
        # 이걸 엄격하게 두면 새 구역을 넣을 때마다 걸린다.
        pat = re.compile(r"(<!--AUTO:%s-->)\n?(.*?)\n?(<!--/AUTO:%s-->)" % (name, name), re.S)
        mm = pat.search(html)
        if not mm:
            sys.exit("표시 없음: AUTO:%s — source.html 이 손상됐다" % name)
        new = fn(reg, rows, now)
        if new.strip() != mm.group(2).strip():
            changed.append(name)
        html = pat.sub(lambda x: x.group(1) + "\n" + new + "\n" + x.group(3), html, count=1)

    # const TEAMS — 팀 상세 자료를 등록부와 카드에서 통째로 다시 만든다
    tm = re.search(r"const TEAMS = (\[.*?\]);\n", html, re.S)
    if tm:
        new_js = json.dumps(teams_js(reg, rows), ensure_ascii=False)
        if new_js != tm.group(1):
            changed.append("TEAMS")
        html = html[:tm.start(1)] + new_js + html[tm.end(1):]

    if a.dry:
        print("바뀔 구역:", ", ".join(changed) or "없음")
        return
    open(SRC, "w", encoding="utf8").write(html)
    print("갱신:", ", ".join(changed) or "변화 없음")
    r = subprocess.run([sys.executable, os.path.join(HERE, "build.py")],
                       capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr.strip())
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
