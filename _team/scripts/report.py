#!/usr/bin/env python3
"""팀 상태 보고 — 팀장(또는 연구책임자)이 상태 변화를 팀에 알린다.

이 도구가 없어서 생긴 일: 2026-08-31 Neptune이 npj에 투고했는데 현황판은 여전히
'투고 직전'이었다. 세션 밖에서 일어난 변화가 팀에 전달될 길이 없었다.

  report.py status <팀> --stage submitted --note "npj 투고 완료"
  report.py status <팀> --blocker "IRB 승인번호 확인" --clear-blockers
  report.py check          카드와 실제 파일 수정일이 어긋난 팀을 찾는다
  report.py log            최근 보고 내역

`registry.yaml`·`teams.yaml`을 직접 고친다.

보고는 사람(팀장 창)이 한다.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace"); _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import os, sys, hashlib, argparse, datetime, glob

try:
    import yaml
except ImportError:
    sys.exit("PyYAML이 필요하다: pip3 install pyyaml")

TEAM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(TEAM)
REG = os.path.join(TEAM, "registry.yaml")
TEAMS = os.path.join(TEAM, "teams.yaml")
LOG = os.path.join(TEAM, "status_log.tsv")

STAGES = ["idea", "protocol", "design", "data", "analysis",
          "writing", "review", "submitted", "published", "onhold"]

REG_HEADER = (
    "# 원본 보존 규칙: 같은 연구 폴더가 다른 곳에도 있으면 그것은 스냅샷이다. 작업은 여기서만 한다.\n"
    "# stage: idea|protocol|design|data|analysis|writing|review|submitted|published|onhold\n"
    "# team: 10개 고정 팀 (_team/teams.yaml). 호칭은 label(행성_약어)을 쓴다.\n"
    "# 상태 변경은 report.py 로 한다 — 손으로 고치면 status_log.tsv와 어긋난다.\n")


# 읽을 때의 파일 내용을 기억해 둔다. 쓸 때 그사이 남이 바꿨는지 확인하려고.
_READ_AT = {}


def load(p):
    raw = open(p, encoding="utf8").read()
    _READ_AT[os.path.abspath(p)] = hashlib.sha256(raw.encode("utf8")).hexdigest()
    return yaml.safe_load(raw)


def save(p, data, header=""):
    """정본을 안전하게 바꾼다.

    두 가지를 막는다.
    **덮어쓰기 사고** — 읽은 뒤 남이 먼저 고쳤으면 멈춘다. 전에는 조용히 밀어냈다.
    이 폴더는 동기화로 두 컴퓨터에 공유되고, 사람이 여는 대화창에는 담당 컴퓨터
    규칙이 적용되지 않으므로 두 곳에서 동시에 보고할 수 있다.

    **반쯤 쓰인 파일** — 옆에 임시 파일로 다 쓴 뒤 한 번에 갈아 끼운다.
    쓰는 도중에 멈춰도 원래 파일은 온전하다.
    """
    ap = os.path.abspath(p)
    was = _READ_AT.get(ap)
    if was and os.path.exists(p):
        now = hashlib.sha256(open(p, encoding="utf8").read().encode("utf8")).hexdigest()
        if now != was:
            sys.exit(
                "[충돌] %s 이(가) 읽은 뒤에 바뀌었다 — 덮어쓰지 않았다.\n"
                "  다른 대화창이나 다른 컴퓨터에서 먼저 보고했을 수 있다.\n"
                "  파일을 다시 확인하고 이 명령을 다시 실행하라." % os.path.basename(p))

    body = header + yaml.dump(data, allow_unicode=True, sort_keys=False, width=200)
    tmp = p + ".tmp.%d" % os.getpid()
    with open(tmp, "w", encoding="utf8") as fh:
        fh.write(body)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, p)
    _READ_AT[ap] = hashlib.sha256(body.encode("utf8")).hexdigest()


def find_project(reg, team):
    for pr in reg["projects"]:
        if (pr.get("team") or "").lower() == team.lower() or pr.get("id", "").lower() == team.lower():
            return pr
    return None


# 팀 관리용 파일은 연구 활동이 아니다 — 카드를 쓴 날짜가 연구가 진전된 날로 잡히면
# check가 전부 오탐이 된다.
NOT_RESEARCH_FILES = {"PROJECT.md", "CLAUDE.md", ".DS_Store"}
NOT_RESEARCH_DIRS = {".git", ".venv", "node_modules", "__pycache__", "_workspace", "digests"}


def newest_mtime(path):
    """폴더에서 가장 최근에 바뀐 **연구 파일**의 날짜. 없으면 None."""
    if not path or not os.path.isdir(path):
        return None
    best = 0
    for dp, dns, fns in os.walk(path):
        dns[:] = [d for d in dns if d not in NOT_RESEARCH_DIRS]
        for fn in fns:
            if fn in NOT_RESEARCH_FILES or fn.startswith(("~$", ".")):
                continue
            try:
                best = max(best, os.path.getmtime(os.path.join(dp, fn)))
            except OSError:
                pass
    return datetime.date.fromtimestamp(best) if best else None


def project_dir(pr):
    p = pr.get("path", "")
    return p if os.path.isabs(p) else os.path.join(ROOT, p)


def cmd_status(a):
    reg = load(REG)
    pr = find_project(reg, a.team)
    if not pr:
        sys.exit("모르는 팀: %s" % a.team)

    source = "PI"
    today0 = datetime.date.today().isoformat()
    if str(pr.get("updated", "")) == today0 and pr.get("last_report"):
        print("⚠ %s 팀이 오늘 이미 보고했다 — 덮어쓰기 전에 확인하라:" % pr.get("team"))
        print("   %s" % str(pr["last_report"])[:160])
    before = dict(stage=pr.get("stage"), blockers=list(pr.get("blockers") or []))

    if a.stage:
        if a.stage not in STAGES:
            sys.exit("stage는 다음 중 하나여야 한다: " + " ".join(STAGES))
        pr["stage"] = a.stage
    if a.clear_blockers:
        pr["blockers"] = []
    for b in (a.blocker or []):
        pr.setdefault("blockers", []).append(b)
    if a.next:
        pr["next"] = a.next
    if a.note:
        pr["last_report"] = a.note
    today = datetime.date.today().isoformat()
    pr["updated"] = today
    save(REG, reg, REG_HEADER)

    if a.stage:
        t = load(TEAMS)
        for tm in t["teams"]:
            if tm["name"].lower() == (pr.get("team") or "").lower():
                tm["stage"] = a.stage
        save(TEAMS, t, "# 10개 고정 연구팀 — 태양계 천체 이름. 순서·우선순위 아님.\n")

    if not os.path.exists(LOG):
        open(LOG, "w", encoding="utf8").write("date\tteam\tsource\tstage_from\tstage_to\tblockers\tnote\n")
    with open(LOG, "a", encoding="utf8") as f:
        f.write("\t".join([today, pr.get("team", a.team), source, str(before["stage"]),
                           str(pr.get("stage")), str(len(pr.get("blockers") or [])),
                           (a.note or "").replace("\t", " ")]) + "\n")

    print("%s 갱신" % (pr.get("label") or pr.get("team")))
    if before["stage"] != pr.get("stage"):
        print("  단계 %s → %s" % (before["stage"], pr.get("stage")))
    if len(before["blockers"]) != len(pr.get("blockers") or []):
        print("  대기 %d → %d건" % (len(before["blockers"]), len(pr.get("blockers") or [])))
    print("  현황판을 다시 뽑아야 반영된다.")


def cmd_check(a):
    reg = load(REG)
    print("%-20s %-10s %-12s %-12s %s" % ("팀", "단계", "카드 갱신", "파일 수정", "판정"))
    print("-" * 78)
    stale = 0
    for pr in reg["projects"]:
        d = project_dir(pr)
        fm = newest_mtime(d)
        up = pr.get("updated", "")
        verdict = "—"
        if fm and up:
            gap = (fm - datetime.date.fromisoformat(str(up))).days
            if gap > 0:
                verdict = "⚠ 파일이 %d일 더 최근 — 보고 누락 의심" % gap
                stale += 1
        elif not fm:
            verdict = "폴더 확인 불가"
        print("%-20s %-10s %-12s %-12s %s" % (
            pr.get("label") or pr.get("team", pr["id"]), pr.get("stage", "-"),
            up, fm.isoformat() if fm else "-", verdict))
    if stale:
        print("\n%d개 팀에서 파일은 움직였는데 카드는 그대로다. "
              "report.py status 로 보고했는지 확인하라." % stale)
    else:
        print("\n어긋난 팀 없음.")


def cmd_log(a):
    if not os.path.exists(LOG):
        print("보고 기록 없음.")
        return
    lines = open(LOG, encoding="utf8").read().strip().splitlines()
    for line in lines[-(a.n + 1):]:
        print("\t".join(line.split("\t")))


def main():
    ap = argparse.ArgumentParser(description="팀 상태 보고")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("status")
    s.add_argument("team")
    s.add_argument("--stage")
    s.add_argument("--note")
    s.add_argument("--next")
    s.add_argument("--blocker", action="append")
    s.add_argument("--clear-blockers", action="store_true")
    s.set_defaults(fn=cmd_status)
    sub.add_parser("check").set_defaults(fn=cmd_check)
    s = sub.add_parser("log")
    s.add_argument("-n", type=int, default=15)
    s.set_defaults(fn=cmd_log)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
