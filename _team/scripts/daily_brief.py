#!/usr/bin/env python3
"""총괄 일일 브리핑 — 팀이 보고해주기를 기다리지 않고 폴더를 직접 본다.

자기보고(`report.py status`)는 사람이 기억해야 하므로 놓친다. 실제로 한 팀의 보고가
그렇게 누락된 적이 있다. 이 도구는 **관찰**이다 — 무엇이 움직였는지는
파일이 알고 있고, 그건 세는 것이지 판단하는 게 아니다.

그래서 LLM을 쓰지 않는다. 공짜이고, 틀리지 않고, 매일 돌아도 부담이 없다.
대신 **왜** 바뀌었는지는 모른다. 그건 자기보고의 몫이고, 둘이 어긋나면 표시한다.

  daily_brief.py              어제부터 지금까지
  daily_brief.py --days 7     기간 지정
  daily_brief.py --quiet      변화가 없으면 아무것도 출력하지 않는다 (자동 실행용)
"""
import os, io, sys, socket, glob, unicodedata, argparse, datetime, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import yaml
except ImportError:
    sys.exit("PyYAML 필요: pip3 install pyyaml")

TEAM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(TEAM)
BRIEF = os.path.join(TEAM, "brief")

SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".ipynb_checkpoints"}
CARD_FILES = {"PROJECT.md", "CLAUDE.md"}          # 팀 관리 파일 — 연구 활동이 아니다


def changed(path, since):
    """폴더 안에서 since 이후에 바뀐 연구 파일을 하위폴더별로 센다."""
    if not os.path.isdir(path):
        return None, {}
    groups, cards = collections.Counter(), []
    for dp, dns, fns in os.walk(path):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        for fn in fns:
            if fn.startswith((".", "~$")):
                continue
            fp = os.path.join(dp, fn)
            try:
                m = os.path.getmtime(fp)
            except OSError:
                continue
            if m < since:
                continue
            rel = os.path.relpath(fp, path)
            if fn in CARD_FILES:
                cards.append(rel)
                continue
            top = rel.split(os.sep)[0] if os.sep in rel else "(루트)"
            groups[top] += 1
    return cards, groups


def inbox_state():
    """제안 큐에서 아직 결정되지 않은 것들.

    머리말이 없는 파일도 **숨기지 않고 드러낸다.** 예전에는 이름 없이 `?` 로만 떠서
    무엇이 잘못됐는지 알 수 없었다 (2026-09-03 Venus 제안이 이틀간 그랬다).
    제안을 만드는 쪽은 사람일 수도 무인 실행일 수도 있으므로, 형식이 틀리는 일은 또 생긴다.
    """
    ib = os.path.join(TEAM, "inbox")
    out = []
    for f in sorted(glob.glob(os.path.join(ib, "*.md"))):
        name = os.path.basename(f)
        if name == "README.md":
            continue
        text = open(f, encoding="utf8").read()
        parts = text.split("---")
        if len(parts) < 3 or parts[0].strip():
            out.append({"id": name[:-3], "_file": name,
                        "_broken": "머리말(--- ... ---)이 없다"})
            continue
        meta = {"id": name[:-3], "_file": name}
        for line in parts[1].splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
        missing = [k for k in ("team", "kind") if not meta.get(k)]
        if missing:
            meta["_broken"] = "머리말에 %s 가 없다" % "·".join(missing)
            out.append(meta)
            continue
        if meta.get("decision", "") in ("", "보류", "추가확인"):
            out.append(meta)
    return out


# 저절로 도는 일들. (표시이름, 기록폴더, 파일머리, 언제 도는가)
#
# '언제 도는가'가 있어야 아직 시각이 안 된 일을 '기록 없음'으로 잘못 알리지 않는다.
#   ("매일", 시, 분)        매일 그 시각
#   ("요일", 요일, 시, 분)  파이썬 요일(월=0). 랩미팅은 화요일=1
#   ("수시",)               30분마다처럼 늘 도는 것
def _unattended():
    """저절로 도는 일의 목록과 일정 — _team/lab.yaml 에서. 프로젝트 전용 무인 실행은 아래에 한 줄씩 더한다."""
    import labconfig
    cfg = labconfig.load()
    b = labconfig.hm(cfg["schedule"]["brief"], (6, 15))
    out = []
    if cfg["ideation"].get("enabled", True):
        i = labconfig.hm(cfg["ideation"].get("time"), (5, 45))
        out.append(("발굴 문헌 수집", "{LOGS}", "{d}_ideate", ("매일",) + i))
    m = cfg["schedule"]["lab_meeting"]
    if m.get("enabled", True):
        p = labconfig.hm(m.get("prep"), (6, 0))
        out.append(("랩미팅 준비", "{MEET}", "{d}", ("요일", int(m.get("weekday", 1))) + p))
    out.append(("연구실 현황판", "{BRIEF}", "lab-dashboard-{d}", ("매일",) + b))
    return out


UNATTENDED = []   # 경량판: 정해진 시각에 도는 일이 없다


def due_state(spec, now):
    """지금 시점에서 이 일이 이미 돌았어야 하는가."""
    kind = spec[0]
    if kind == "수시":
        return "지났음"
    if kind == "요일":
        wd, hh, mm = spec[1], spec[2], spec[3]
        if now.weekday() != wd:
            return "오늘 없음"
        try:
            import labconfig
            if not labconfig.meeting_day(labconfig.load(), now.date()):
                return "오늘 없음"          # 격주 이상 간격에서 회의 주가 아닌 주
        except Exception:
            pass
    else:
        hh, mm = spec[1], spec[2]
    return "지났음" if (now.hour, now.minute) >= (hh, mm) else "아직"


def classify(text):
    """기록을 읽고 어떻게 끝났는지 가른다. 마지막 줄만 보면 오해한다 —
    자막 수집처럼 진행 상황을 계속 찍는 일은 마지막 줄이 결과가 아니다."""
    if not text.strip():
        return "빈 기록", ""
    lines = [l for l in text.strip().splitlines() if l.strip()]
    last = lines[-1][:80]
    joined = "\n".join(lines)
    if "건너뜀" in joined and len(lines) <= 2:
        return "건너뜀", ""                      # 담당이 아닌 컴퓨터
    for l in reversed(lines):
        if "exit=" in l:
            import re as _re
            m = _re.findall(r"exit=(-?\d+)", l)
            if m and any(x != "0" for x in m):
                return "실패", l[:80]
            return "완료", l[:80]
        if "수집 실패" in l or "받아오지 못한" in l:
            return "실패", l[:80]
        if "신규 문헌 없음" in l:
            return "신규 없음", l[:80]
        if "종료" in l or "완료" in l:
            return "완료", l[:80]
        if "찾지 못했다" in l or "실패" in l:
            return "실패", l[:80]
    return "진행 중", last


def unattended_today(today):
    """오늘 저절로 돈 일들의 결과. 컴퓨터 이름이 붙은 파일을 전부 본다.

    기록 파일 이름에 컴퓨터 이름을 붙였는데(`..._<일이름>__<컴퓨터이름>.log`)
    여기를 같이 고치지 않아, 실제로 돈 일을 '오늘 기록 없음'으로 보고했다.
    그래서 이제 파일 이름을 정확히 맞히려 하지 않고, 머리글자로 찾아 전부 읽는다.
    """
    base = {
        "LOGS":  os.path.join(TEAM, "inbox", "_logs"),
        "MEET":  os.path.join(TEAM, "lab_meetings", "_logs"),
        "BRIEF": os.path.join(TEAM, "brief", "logs"),
    }
    now = datetime.datetime.now()
    out = []
    for name, where, head, when in UNATTENDED:
        d_state = due_state(when, now)
        d = os.path.normpath(where.format(**base))
        prefix = head.format(d=today)
        hits = sorted(glob.glob(os.path.join(d, prefix + "*.log")))
        if not hits:
            if d_state == "오늘 없음":
                out.append((name, None, "오늘 해당 없음", ""))
            elif d_state == "아직":
                out.append((name, None, "아직 시각 전", ""))
            else:
                out.append((name, None, "기록 없음", ""))
            continue
        best = None
        for p in hits:
            host = os.path.basename(p).replace(".log", "").split("__")[-1]
            try:
                st, detail = classify(open(p, encoding="utf8", errors="replace").read())
            except OSError:
                st, detail = "읽지 못함", ""
            # 실제로 일한 컴퓨터를 고른다. 건너뛴 기록은 일한 기록이 없을 때만 쓴다.
            if st != "건너뜀":
                best = (name, host, st, detail)
                break
            if best is None:
                best = (name, host, st, detail)
        out.append(best)
    return out


# 동기화 폴더는 두 컴퓨터가 같은 파일을 동시에 고치면 원본을 살려두고 사본을 따로 만든다.
# 그 사본은 조용히 생기므로 늦게 발견된다 — 2026-08-28에 87개가 갈라진 뒤에야 알았다.
# 이름에 '충돌' 표시가 들어가므로 그것으로 찾는다. 언어 설정에 따라 표기가 다르다.
CONFLICT_MARKS = ("conflicted copy", "충돌된 사본", "충돌 사본", "의 충돌")
# _archive 는 이미 사람이 확인해 치워둔 곳이다. 다시 세면 매일 같은 경고가 뜬다.
SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__", ".DS_Store", "dist", "_archive"}


def conflicted_copies(limit=40):
    hits = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in list(dirnames) + filenames:
            # macOS는 한글 이름을 자모로 쪼개 저장한다. 합쳐놓지 않으면 글자 비교가 빗나간다.
            low = unicodedata.normalize("NFC", name).lower()
            if any(m in low for m in CONFLICT_MARKS):
                rel = os.path.relpath(os.path.join(dirpath, name), ROOT)
                try:
                    when = datetime.datetime.fromtimestamp(
                        os.path.getmtime(os.path.join(dirpath, name))).strftime("%m-%d %H:%M")
                except OSError:
                    when = "-"
                hits.append((rel, when))
                if len(hits) >= limit:
                    return hits, True
    return hits, False


def unattended_changes(today):
    """무인 실행이 오늘 정본을 바꾼 것들.

    2026-09-05 부터 무인도 단계·다음행동·대기추가를 바꿀 수 있다(PI 결정).
    막지 않는 대신 **보이게 한다** — 틀린 판정이 조용히 굳지 않도록.
    status_log.tsv 의 source 칸이 'PI' 가 아니면 무인이 쓴 것이다.
    """
    p = os.path.join(TEAM, "status_log.tsv")
    out = []
    if not os.path.exists(p):
        return out
    for line in open(p, encoding="utf8"):
        c = line.rstrip("\n").split("\t")
        if len(c) < 7 or c[0] != today or c[2] == "PI" or c[2] == "source":
            continue
        moved = "%s → %s" % (c[3], c[4]) if c[3] != c[4] else None
        out.append((c[1], c[2], moved, c[5], c[6][:70]))
    return out


def open_items(reg, today):
    """오래 남은 미해결. 담당과 '무엇을 보면 끝난 것인가'가 붙어 있다.

    경고만 반복하면 굳는다 — 2026-09-05 확인 시점에 Jupiter 의 네 건은 203일,
    Uranus 의 두 건은 169일째였다. 그래서 끝나는 조건을 registry 에 적고 매일 보여준다.
    """
    out = []
    for p in reg["projects"]:
        for it in (p.get("open_items") or []):
            if str(it.get("status", "open")) != "open":
                continue
            try:
                d = (today - datetime.date.fromisoformat(str(it.get("since")))).days
            except Exception:
                d = None
            out.append((d if d is not None else -1, p.get("label") or p.get("team"), it))
    out.sort(key=lambda x: -x[0])
    return out


LEDGER = os.path.join(BRIEF, "blocker_first_seen.tsv")
STALE_DAYS = 30


def stale_waits(reg, today):
    """30일 넘은 대기 — 원문 확인 대상.

    한 팀이 76일간 기다린 결정이 이미 접힌 시도의 것으로 드러난 일이 있었다.
    대기 문구는 날짜가 없어 언제부터 기다렸는지 아무도 몰랐다. 그래서 대기 문구가 처음 보인 날을
    여기 장부에 적어 두고, 30일이 넘으면 '이 대기의 근거 문서가 아직 유효한가'를 매일 묻는다.
    (총괄 결정 2026-09-09. 근거: Critic — "대기마다 무엇을·누구에게·언제 물었는지가 붙지 않으면 반복된다")
    """
    seen = {}
    if os.path.exists(LEDGER):
        for line in io.open(LEDGER, encoding="utf8"):
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 3 and parts[0] != "team":
                seen[(parts[0], parts[1])] = parts[2]
    current = {}
    for p in reg["projects"]:
        label = p.get("label") or p.get("team")
        for b in (p.get("blockers") or []):
            key = (label, str(b).replace("\t", " ").replace("\n", " "))
            current[key] = seen.get(key) or today.isoformat()
    # 지금 있는 대기만 남긴다 — 사라진 대기는 장부에서도 빠진다
    tmp = LEDGER + ".tmp"
    with io.open(tmp, "w", encoding="utf8") as f:
        f.write("team\tblocker\tfirst_seen\n")
        for (label, b), d in sorted(current.items(), key=lambda kv: kv[1]):
            f.write("%s\t%s\t%s\n" % (label, b, d))
    os.replace(tmp, LEDGER)
    out = []
    for (label, b), d in current.items():
        try:
            age = (today - datetime.date.fromisoformat(d)).days
        except Exception:
            continue
        if age >= STALE_DAYS:
            out.append((age, label, b, d))
    out.sort(key=lambda x: -x[0])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=1)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    now = datetime.datetime.now()
    since = (now - datetime.timedelta(days=a.days)).timestamp()
    today = now.date().isoformat()
    reg = yaml.safe_load(open(os.path.join(TEAM, "registry.yaml"), encoding="utf8"))

    moved, quiet_teams, mismatch = [], [], []
    for p in reg["projects"]:
        path = p["path"] if os.path.isabs(p["path"]) else os.path.join(ROOT, p["path"])
        cards, groups = changed(path, since)
        label = p.get("label", p["id"])
        if groups is None or (not groups and not cards):
            quiet_teams.append((label, p.get("stage", "-"), p.get("updated", "")))
            continue
        if groups:
            moved.append((label, p.get("stage", "-"), groups, cards))
            upd = str(p.get("updated", ""))
            if upd and upd < today:
                mismatch.append((label, upd))
        elif cards:
            quiet_teams.append((label, p.get("stage", "-"), p.get("updated", "")))

    pend = []                       # 경량판: 제안 큐 없음
    runs = []                       # 경량판: 저절로 도는 일 없음
    conflicts, truncated = [], False   # 경량판: 한 컴퓨터
    uchanges = []
    oitems = open_items(reg, now.date())
    stale = stale_waits(reg, now.date())

    if a.quiet and not moved and not pend and not mismatch and not conflicts and not uchanges:
        return

    L = []
    W = L.append
    W(f"# 총괄 브리핑 — {today} ({'월화수목금토일'[now.weekday()]}) {now:%H:%M}")
    W("")
    W(f"관찰 구간: 최근 {a.days}일. 파일 수정 시각 기준이며 **왜** 바뀌었는지는 알지 못한다.")
    W("")
    W(f"작성한 컴퓨터: {socket.gethostname().split('.')[0]}")
    W("")

    if conflicts:
        W("## \u26a0 갈라진 파일 %d건%s" % (len(conflicts), " 이상" if truncated else ""))
        W("")
        W("두 컴퓨터가 같은 파일을 동시에 고쳤다. 동기화 도구가 원본을 살리고 사본을 따로 만든 것이다.")
        W("**어느 쪽이 맞는지 확인해 합치고, 사본은 지운다.** 오래 두면 어느 것이 진짜인지 알 수 없게 된다.")
        W("")
        for rel, when in conflicts:
            W(f"- `{rel}` — {when}")
        W("")

    W("## 움직인 팀")
    W("")
    if not moved:
        W("없음.")
    else:
        for label, stage, groups, cards in moved:
            detail = " · ".join(f"`{k}` {v}" for k, v in groups.most_common(5))
            W(f"- **{label}** ({stage}) — {sum(groups.values())}개 파일: {detail}")
            if cards:
                W(f"  - 카드도 갱신됨: {', '.join(cards)}")
    W("")

    if mismatch:
        W("## ⚠ 보고 누락 의심")
        W("")
        W("파일은 움직였는데 카드의 `updated`가 그대로다. 세션이 `report.py status`를 안 했을 수 있다.")
        W("")
        for label, upd in mismatch:
            W(f"- **{label}** — 카드 갱신일 {upd}")
        W("")

    W("## 기다리는 것")
    W("")
    if pend:
        for m in pend:
            urg = m.get("urgency", "none")
            if m.get("_broken"):
                W(f"- **✗ 읽지 못한 제안** — {m['_broken']}."
                  f" 파일: `_team/inbox/{m.get('_file', m.get('id','?') + '.md')}`")
                continue
            W(f"- `{m.get('id','?')}` · {m.get('team','-')} · **{m.get('kind','-')}**"
              + (f" · 마감 {urg}" if urg not in ("none", "") else ""))
    blocked = sum(len(p.get("blockers") or []) for p in reg["projects"])
    W(f"- 대기 **{blocked}건** — 누군가의 결정이나 작업을 기다리는 것 (팀별 상세는 `registry.yaml`)")
    W("")

    if oitems:
        W("## 오래 남은 미해결")
        W("")
        W("경고만 반복하면 굳는다. **무엇을 보면 끝난 것인지**를 함께 적어 둔다.")
        W("")
        for d, label, it in oitems[:8]:
            age = "**%d일**" % d if d >= 90 else "%d일" % d
            W("- %s · **%s** — %s (%s)" % (label, it.get("what"), age, it.get("who", "?")))
            W("  - 끝나는 조건: %s" % it.get("done_when", "—"))
            if it.get("checked"):
                W("  - 확인: %s" % it["checked"])
        if len(oitems) > 8:
            W("")
            W("그 밖 %d건은 `registry.yaml` 의 `open_items` 에 있다." % (len(oitems) - 8))
        W("")

    if stale:
        W("## 원문 확인 대상 — %d일 넘은 대기 %d건" % (STALE_DAYS, len(stale)))
        W("")
        W("오래 기다린 대기는 **근거 문서가 아직 유효한지**를 먼저 본다. 한 팀이 76일간 기다린 결정이")
        W("이미 접힌 시도의 것이었음이 드러났다 — 대기 문구만 보고 원문을 아무도 열지 않았기 때문이다.")
        W("")
        for age, label, b, d in stale:
            W("- **%s** · %d일째 (%s부터) — %s" % (label, age, d, b))
            W("  - 확인할 것: 이 대기가 가리키는 문서·결정이 지금도 살아 있는가. 접혔거나 대체됐으면 대기 문구를 바꾼다")
        W("")
    W("## 조용한 팀")
    W("")
    W(" · ".join(f"{l}({s})" for l, s, _ in quiet_teams) or "없음")
    W("")

    if uchanges:
        W("## 무인이 바꾼 것")
        W("")
        W("사람이 아니라 저절로 도는 작업이 정본을 고쳤다. **틀렸으면 여기서 잡아야 한다.**")
        W("")
        for team, who, moved, nblock, note in uchanges:
            bits = []
            if moved:
                bits.append("단계 **%s**" % moved)
            bits.append("대기 %s건" % nblock)
            W("- **%s** (%s) — %s%s" % (team, who, " · ".join(bits), (" — " + note) if note else ""))
        W("")

    text = "\n".join(L)
    os.makedirs(BRIEF, exist_ok=True)
    open(os.path.join(BRIEF, f"{today}.md"), "w", encoding="utf8").write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
