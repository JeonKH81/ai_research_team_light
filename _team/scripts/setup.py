#!/usr/bin/env python3
"""설치 문답 (경량판) — 다섯 가지를 묻고 `_team/lab.yaml` 에 적은 뒤 반영한다. 10분 안에 끝난다.

    python3 _team/scripts/setup.py            # 묻고 → 적고 → 반영
    python3 _team/scripts/setup.py --apply    # lab.yaml 을 손으로 고친 뒤 반영만

묻는 것: ① 연구실 이름 ② 연구책임자 전공 ③ 팀 이름 규칙 ④ 발굴팀 관심 영역과 출처 ⑤ 랩미팅(할지·간격·요일·시각)
반영: _team/LAB_NAME · _team/teams.yaml · _team/roster.md · _team/resources.md → 현황판 다시 만들기 → 문헌 수집 미리보기

Claude Code 안에서 `/setup` 이라고 치면 같은 문답을 대화로 한다 — 검색식을 대신 만들어 준다.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace"); _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import os, sys, re, io, datetime, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
TEAM = os.path.dirname(HERE)
ROOT = os.path.dirname(TEAM)
sys.path.insert(0, HERE)
import labconfig  # noqa: E402

WD = "월화수목금토일"
SOURCES = [("pubmed", "PubMed (학술지 논문)"), ("medrxiv", "medRxiv (의학 프리프린트)"),
           ("arxiv", "arXiv (인공지능·통계 방법론 프리프린트)"), ("trials", "ClinicalTrials.gov (임상시험 등록)")]


def ask(q, default=""):
    d = " [%s]" % default if default != "" else ""
    try:
        v = input("%s%s: " % (q, d)).strip()
    except EOFError:
        v = ""
    return v or default


def yes(q, default=True):
    v = ask(q + " (y/n)", "y" if default else "n").lower()
    return v.startswith("y") or v in ("네", "예", "ㅇ")


def q(s):
    return "'" + str(s).replace("'", "''") + "'"


def query_from(kws):
    return "(%s)" % " OR ".join('"%s"[tiab]' % k if " " in k else "%s[tiab]" % k for k in kws)


def interview(cfg):
    print("\n설치 문답 — 다섯 가지. 엔터를 치면 [ ] 안의 값이 됩니다.\n")
    cfg["lab_name"] = ask("① 연구실 이름", cfg["lab_name"])
    cfg["pi"]["field"] = ask("② 연구책임자 전공 (예: 순환기내과)", cfg["pi"].get("field", ""))
    cfg["pi"]["institution"] = ask("   소속 (선택)", cfg["pi"].get("institution", ""))

    print("\n③ 팀 이름. 팀은 언제나 10개이고 프로젝트가 끝나면 같은 팀이 다음 프로젝트를 받습니다.")
    print("   (1) 태양계 — Mercury·Venus·Terra·Mars·Jupiter·Saturn·Uranus·Neptune·Ceres·Pluto")
    print("   (2) 직접 정한다 — 영문 이름 10개 (별자리·산·원소 …)")
    if ask("   선택", "1" if cfg["teams"]["scheme"] == "planets" else "2") == "2":
        cfg["teams"]["scheme"] = "custom"; names = []
        for i in range(10):
            cur = cfg["teams"]["names"][i] if i < len(cfg["teams"]["names"]) else {"name": "", "ko": ""}
            n = ask("   팀 %d 영문 이름" % (i + 1), cur.get("name", ""))
            if not n:
                n, k = labconfig.PLANETS[i]; print("   비어 있어 행성 이름으로 채웁니다."); names.append({"name": n, "ko": k}); continue
            names.append({"name": re.sub(r"[^A-Za-z0-9]", "", n), "ko": ask("        한글 표기", cur.get("ko") or n)})
        cfg["teams"]["names"] = names
    else:
        cfg["teams"]["scheme"] = "planets"
        cfg["teams"]["names"] = [{"name": n, "ko": k} for n, k in labconfig.PLANETS]

    print("\n④ 발굴팀. 관심 영역의 새 문헌을 모아 연구 질문 후보를 만듭니다. 판정은 랩미팅에서 합니다.")
    cfg["ideation"]["enabled"] = yes("   발굴팀을 둘까요?", cfg["ideation"].get("enabled", True))
    if cfg["ideation"]["enabled"]:
        print("   관심 영역을 1~3개 적습니다. 영역마다 라벨 → 영어 핵심어 → 출처를 묻습니다. 라벨을 비우면 끝.")
        print("   (검색식을 제대로 다듬으려면 Claude Code 에서 /setup 을 쓰세요 — 대신 만들어 줍니다)")
        topics = []
        while len(topics) < 3:
            label = ask("   영역 %d 라벨 (예: 심부전 인공지능)" % (len(topics) + 1), "")
            if not label:
                break
            kws = [k.strip() for k in ask("     영어 핵심어를 쉼표로 (예: heart failure, machine learning)", "").split(",") if k.strip()]
            print("     출처 — 번호를 쉼표로: " + "  ".join("(%d) %s" % (i + 1, n) for i, (_, n) in enumerate(SOURCES)))
            picks = [p.strip() for p in ask("     선택", "1,2").split(",")]
            srcs = [SOURCES[int(p) - 1][0] for p in picks if p.isdigit() and 1 <= int(p) <= len(SOURCES)] or ["pubmed"]
            key = re.sub(r"[^a-z0-9]+", "-", (kws[0] if kws else label).lower()).strip("-") or "topic-%d" % (len(topics) + 1)
            t = {"key": key, "label": label, "sources": srcs}
            if "pubmed" in srcs: t["pubmed"] = query_from(kws) if kws else ""
            if "medrxiv" in srcs: t["medrxiv"] = kws[:2]
            if "arxiv" in srcs: t["arxiv"] = " AND ".join("all:%s" % ('"%s"' % k if " " in k else k) for k in kws[:3])
            if "trials" in srcs: t["trials"] = " ".join(kws[:2])
            topics.append(t)
        if topics:
            cfg["ideation"]["topics"] = topics

    m = cfg["schedule"]["lab_meeting"]
    print("\n⑤ 랩미팅. 진행 중 연구를 검토하고 발굴 후보를 채택·보류·기각하는 정기 회의입니다.")
    m["enabled"] = yes("   정기 랩미팅을 할까요?", m.get("enabled", True))
    if m["enabled"]:
        m["interval_weeks"] = int(ask("   간격 — 1(매주) / 2(격주) / 4(4주)", str(m.get("interval_weeks", 1))) or 1)
        w = ask("   요일 (월/화/수/목/금/토/일)", WD[int(m.get("weekday", 1))])
        m["weekday"] = WD.index(w[0]) if w and w[0] in WD else int(m.get("weekday", 1))
        m["time"] = ask("   시각", m.get("time", "07:00"))
        m["anchor"] = datetime.date.today().isoformat()
    return cfg


def write_yaml(cfg):
    L = ["# 이 연구실의 설정 — `/setup` 문답(또는 `python3 _team/scripts/setup.py`)의 답이 여기 남는다.",
         "# 현황판·브리핑·문헌 수집이 이 파일을 읽는다. 손으로 고쳤으면 `python3 _team/scripts/setup.py --apply`.", "",
         "lab_name: %s" % q(cfg["lab_name"]), "", "pi:",
         "  field: %s          # 연구책임자 전공 — 발굴팀이 후보를 낼 출발점" % q(cfg["pi"].get("field", "")),
         "  institution: %s" % q(cfg["pi"].get("institution", "")),
         "  contact_email: %s  # 문헌 수집기가 PubMed 에 자기를 밝힐 때 (선택)" % q(cfg["pi"].get("contact_email", "")), "",
         "teams:", "  scheme: %s    # planets(태양계) 또는 custom(아래 names). 팀은 언제나 10개" % cfg["teams"]["scheme"], "  names:"]
    for t in cfg["teams"]["names"]:
        L.append("    - {name: %s, ko: %s}" % (t["name"], q(t["ko"])))
    m = cfg["schedule"]["lab_meeting"]
    L += ["", "schedule:", "  lab_meeting:", "    enabled: %s" % ("true" if m.get("enabled", True) else "false"),
          "    weekday: %d         # 0=월 1=화 2=수 3=목 4=금 5=토 6=일" % int(m.get("weekday", 1)),
          "    time: %s" % q(m.get("time", "07:00")),
          "    interval_weeks: %d  # 1=매주 2=격주" % int(m.get("interval_weeks", 1) or 1),
          "    anchor: %s   # 격주 이상일 때 어느 주가 회의 주인지 정하는 기준일" % q(m.get("anchor", datetime.date.today().isoformat())),
          "", "ideation:", "  enabled: %s" % ("true" if cfg["ideation"].get("enabled", True) else "false"),
          "  # 관심 영역 — 수집기가 훑는 곳. sources 는 pubmed / medrxiv / arxiv / trials 중 고른 것.", "  topics:"]
    for t in cfg["ideation"].get("topics") or []:
        L += ["    - key: %s" % t.get("key"), "      label: %s" % q(t.get("label", "")),
              "      sources: [%s]" % ", ".join(t.get("sources") or [k for k in ("pubmed", "medrxiv", "arxiv", "trials") if t.get(k)])]
        for k in ("pubmed", "arxiv", "trials"):
            if t.get(k): L.append("      %s: %s" % (k, q(t[k])))
        if t.get("medrxiv"): L.append("      medrxiv: [%s]" % ", ".join(q(x) for x in t["medrxiv"]))
    io.open(labconfig.PATH, "w", encoding="utf8").write("\n".join(L) + "\n")


def apply(cfg, preview=True):
    import yaml
    done = []
    io.open(os.path.join(TEAM, "LAB_NAME"), "w", encoding="utf8").write(cfg["lab_name"] + "\n"); done.append("LAB_NAME")
    tp = os.path.join(TEAM, "teams.yaml")
    old = yaml.safe_load(io.open(tp, encoding="utf8")) if os.path.exists(tp) else {}
    olds = {t["name"]: t for t in (old.get("teams") or [])}
    teams = []
    for t in cfg["teams"]["names"]:
        keep = olds.get(t["name"])
        if keep:
            keep = dict(keep); keep["ko"] = t["ko"]; keep["slug"] = t["name"].lower(); teams.append(keep)
        else:
            teams.append({"name": t["name"], "ko": t["ko"], "slug": t["name"].lower(), "project": None, "stage": "idle", "code": "미배정", "label": t["name"]})
    # 이름이 바뀐 자리: 옛 i번째 팀에 프로젝트가 있으면 새 i번째 이름으로 옮긴다 (등록부도 함께)
    oldnames = [t["name"] for t in (old.get("teams") or [])]
    renamed = {}
    for i, t in enumerate(teams):
        if i < len(oldnames) and oldnames[i] != t["name"] and olds[oldnames[i]].get("project"):
            src = olds[oldnames[i]]
            t.update(project=src.get("project"), stage=src.get("stage"), code=src.get("code"),
                     label="%s_%s" % (t["name"], src.get("code") or "?"), legacy_id=src.get("legacy_id"))
            renamed[oldnames[i]] = t["name"]
    if renamed:
        rp2 = os.path.join(TEAM, "registry.yaml")
        raw = io.open(rp2, encoding="utf8").read(); hdr2 = "".join(l for l in raw.splitlines(True) if l.startswith("#"))
        reg = yaml.safe_load(raw)
        for p in reg.get("projects") or []:
            if p.get("team") in renamed:
                p["team"] = renamed[p["team"]]; p["label"] = "%s_%s" % (p["team"], p.get("code") or "?")
        io.open(rp2, "w", encoding="utf8").write(hdr2 + yaml.safe_dump(reg, allow_unicode=True, sort_keys=False, width=200))
        print("팀 이름 변경에 따라 배정을 옮겼다: " + " · ".join("%s → %s" % kv for kv in renamed.items()))
    moved = [n for n in olds if olds[n].get("project") and n not in {t["name"] for t in teams} and n not in renamed]
    rules = [r.replace("행성_약어", "팀이름_약어") for r in (old.get("규칙") or [])] or [
        "팀은 10개로 고정한다. 프로젝트가 끝나면 같은 팀이 다음 프로젝트를 받는다.",
        "팀 이름은 순서나 우선순위를 뜻하지 않는다.", "팀 호칭은 `팀이름_약어` 형태로 쓴다 (예: Terra_DEMO-SR)."]
    io.open(tp, "w", encoding="utf8").write("# 10개 고정 연구팀 — 이름 규칙: %s. 바꾸려면 lab.yaml 을 고치고 setup.py --apply\n" % cfg["teams"]["scheme"]
                                            + yaml.safe_dump({"규칙": rules, "teams": teams}, allow_unicode=True, sort_keys=False)); done.append("teams.yaml")
    if moved:
        print("⚠ 프로젝트가 배정돼 있던 팀 이름이 사라졌다: %s — 등록부(registry.yaml)의 team 칸을 손봐야 한다" % ", ".join(moved))
    rp = os.path.join(TEAM, "roster.md")
    if os.path.exists(rp):
        s = io.open(rp, encoding="utf8").read()
        rows = ["| 호칭 | 한글 | 현재 프로젝트 | 단계 | 비고 |", "|---|---|---|---|---|"]
        for t in teams:
            rows.append("| **%s** | %s | %s | %s | |" % (t.get("label") or t["name"], t["ko"], t.get("project") or "— 미배정", t.get("stage") or "idle"))
        s2, k = re.subn(r"\| 호칭 \| 한글 \|.*?(?=\n\n)", "\n".join(rows), s, count=1, flags=re.S)
        if k: io.open(rp, "w", encoding="utf8").write(s2); done.append("roster.md")
    sp = os.path.join(TEAM, "resources.md")
    if os.path.exists(sp) and (cfg["pi"].get("field") or cfg["pi"].get("institution")):
        s = io.open(sp, encoding="utf8").read()
        s2, k = re.subn(r"^- 전공·소속: .*$", "- 전공·소속: %s" % ", ".join(x for x in (cfg["pi"].get("field"), cfg["pi"].get("institution")) if x), s, count=1, flags=re.M)
        if k: io.open(sp, "w", encoding="utf8").write(s2); done.append("resources.md")
    print("\n반영: " + " · ".join(done))
    m = cfg["schedule"]["lab_meeting"]
    print("연구실  : %s" % cfg["lab_name"])
    print("팀 이름 : %s" % " · ".join(t["name"] for t in teams))
    print("랩미팅  : %s" % ("%s요일 %s, %s" % (WD[int(m.get("weekday", 1))], m.get("time"), "매주" if int(m.get("interval_weeks", 1) or 1) == 1 else "%d주마다" % int(m["interval_weeks"])) if m.get("enabled", True) else "정기 회의 없음 (필요할 때 /lab-meeting)"))
    tps = cfg["ideation"].get("topics") or []
    print("발굴팀  : %s" % (("영역 %d개 — " % len(tps) + " · ".join("%s(%s)" % (t.get("label"), ",".join(t.get("sources") or [])) for t in tps)) if cfg["ideation"].get("enabled", True) and tps else ("본보기 영역으로" if cfg["ideation"].get("enabled", True) else "두지 않음")))
    # 현황판 다시 만들기
    r = subprocess.run([sys.executable, os.path.join(TEAM, "dashboard", "refresh.py")], capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("현황판  : %s" % ((r.stdout.strip().splitlines() or ["?"])[-1] if r.returncode == 0 else "실패 — " + r.stderr.strip()[-200:]))
    if preview and cfg["ideation"].get("enabled", True) and tps:
        print("\n문헌 수집 미리보기 (최근 7일, 파일은 만들지 않음) — 인터넷이 막힌 곳이면 여기서 실패가 뜹니다:")
        r = subprocess.run([sys.executable, os.path.join(HERE, "discover.py"), "--days", "7", "--dry"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
        print("  " + "\n  ".join((r.stdout or r.stderr).strip().splitlines()[-8:]))
        if "실패" in (r.stdout + r.stderr) or "CERTIFICATE" in (r.stdout + r.stderr):
            print("  → 병원망이면: python3 install.py 를 다시 돌려 인증서 부품(truststore)을 넣고, 맥에서 그래도 안 되면 zsh _team/scripts/fix_certificates.sh")
    print("\n다음: 현황판을 엽니다 →  open _team/dashboard/dist/lab-dashboard.html")


def main():
    cfg = labconfig.load()
    if "--apply" not in sys.argv:
        cfg = interview(cfg); write_yaml(cfg); cfg = labconfig.load()
        print("\n`_team/lab.yaml` 에 적었습니다.")
    apply(cfg, preview="--no-preview" not in sys.argv)


if __name__ == "__main__":
    main()
