#!/usr/bin/env python3
"""포트폴리오 요약을 정본에서 뽑아 쓴다.

**왜 필요한가.** `portfolio.md` 는 손으로 쓰는 문서였고 2026-09-01 에 멈춰 있었다.
2026-09-05 대조 결과: Neptune 이 표에 아예 없었고(8건 중 7건만), Venus·Saturn·Mars 는
단계가 registry 와 달랐다. Saturn 은 registry 가 '보류'인데 표는 '분석·원고 착수'였다.

같은 사실을 두 곳에 손으로 적으면 반드시 갈라진다. 그래서 **표는 registry.yaml 에서
뽑아 쓰고**, 사람이 판단해 적는 부분(결정 필요·위험 기록 같은 것)은 그대로 둔다.

`<!--AUTO:projects-->` 와 `<!--/AUTO:projects-->` 사이만 다시 쓴다. 나머지는 건드리지 않는다.

    python3 portfolio.py          # 무엇이 바뀌는지 보여주기만
    python3 portfolio.py --write  # 실제로 쓴다
"""
import os, io, re, sys, argparse, datetime

try:
    import yaml
except ImportError:
    sys.exit("PyYAML 이 필요하다: python3 -m pip install pyyaml")

TEAM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = os.path.join(TEAM, "registry.yaml")
OUT = os.path.join(TEAM, "portfolio.md")

STAGE_KO = {
    "idea": "착상", "protocol": "프로토콜", "design": "설계", "data": "자료수집",
    "analysis": "분석", "writing": "집필", "review": "심사", "submitted": "투고",
    "published": "게재", "onhold": "보류",
}


def aging(updated, today):
    """카드가 마지막으로 갱신된 뒤 며칠 지났는가."""
    try:
        d = datetime.date.fromisoformat(str(updated))
    except Exception:
        return None
    return (today - d).days


def state_of(p, days):
    """한눈에 읽히는 상태 한 마디. registry 의 사실만 쓴다 — 새로 판단하지 않는다."""
    st = p.get("stage")
    nb = len(p.get("blockers") or [])
    if st == "onhold":
        return "**보류** (PI 결정)"
    if st in ("submitted", "published"):
        return "**투고 완료**" if st == "submitted" else "**게재**"
    if days is not None and days >= 60:
        return "**정체 %d일**" % days
    if nb:
        return "대기 %d건" % nb
    return "진행 중"


def build(reg, today):
    L = []
    L.append("| 팀 | 제목 | 단계 | 상태 | 다음 할 일 | 카드 갱신 |")
    L.append("|----|------|------|------|-----------|----------|")
    # 손댈 순서로 정렬한다: 보류·대기는 뒤로, 오래 멈춘 것과 차단 많은 것이 앞으로.
    def key(p):
        st = p.get("stage")
        d = aging(p.get("updated"), today) or 0
        return (0 if st not in ("onhold",) else 1, -d)
    for p in sorted(reg["projects"], key=key):
        d = aging(p.get("updated"), today)
        label = p.get("label") or p.get("team") or p.get("id")
        title = (p.get("title") or "").strip()
        nxt = str(p.get("next") or "—").strip().replace("|", "·")
        if len(nxt) > 70:
            nxt = nxt[:68] + "…"
        L.append("| **%s** | %s | %s | %s | %s | %s%s |" % (
            label, title[:34], STAGE_KO.get(p.get("stage"), p.get("stage")),
            state_of(p, d), nxt, p.get("updated", "—"),
            (" (%d일 전)" % d) if d and d >= 14 else ""))
    L.append("")
    blocked = sum(len(p.get("blockers") or []) for p in reg["projects"])
    active = sum(1 for p in reg["projects"] if p.get("stage") not in ("onhold", "published"))
    L.append("프로젝트 **%d건** · 진행 **%d건** · 대기 합계 **%d건**." % (
        len(reg["projects"]), active, blocked))
    closed = reg.get("closed") or []
    if closed:
        L.append("")
        L.append("### 끝난 연구 %d건" % len(closed))
        L.append("")
        L.append("| 팀 | 제목 | 끝난 날 | 왜 | 다시 열 조건 |")
        L.append("|----|------|--------|----|------------|")
        for p in closed:
            L.append("| %s | %s | %s | %s | %s |" % (
                p.get("label") or p.get("id"), (p.get("title") or "")[:28],
                p.get("closed_on") or "—",
                str(p.get("closed_why") or "—").replace("|", "·")[:70],
                str(p.get("reopen_when") or "—").replace("|", "·")[:70]))
        L.append("")
        L.append("폴더는 `projects/_closed/` 에 그대로 있다. 되살리려면 "
                 "등록부의 `closed` 절에서 `projects` 절로 옮기고 폴더를 되돌린다.")

    L.append("")
    L.append("*이 표는 `_team/registry.yaml` 에서 뽑아 쓴다. 손으로 고치면 다음 갱신 때 사라진다 —"
             " 내용을 바꾸려면 `report.py status` 로 정본을 고쳐라.*")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()

    reg = yaml.safe_load(io.open(REG, encoding="utf8"))
    today = datetime.date.today()
    block = build(reg, today)

    text = io.open(OUT, encoding="utf8").read()
    # 표시 사이가 비어 있어도 찾도록 줄바꿈을 느슨하게 본다.
    pat = re.compile(r"(<!--AUTO:projects-->)\n?(.*?)\n?(<!--/AUTO:projects-->)", re.S)
    if not pat.search(text):
        sys.exit("표시가 없다: portfolio.md 에 <!--AUTO:projects--> … <!--/AUTO:projects--> 를 넣어라.")

    new = pat.sub(lambda m: m.group(1) + "\n" + block + "\n" + m.group(3), text, count=1)
    if new == text:
        print("바뀐 것 없음.")
        return
    if not a.write:
        print(block)
        print("\n(보여주기만 했다. 실제로 쓰려면 --write)")
        return
    tmp = OUT + ".tmp.%d" % os.getpid()
    io.open(tmp, "w", encoding="utf8").write(new)
    os.replace(tmp, OUT)
    print("portfolio.md 갱신 — 프로젝트 %d건" % len(reg["projects"]))


if __name__ == "__main__":
    main()
