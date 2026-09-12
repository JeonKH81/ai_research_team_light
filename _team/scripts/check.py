#!/usr/bin/env python3
"""설치 확인 — 30초. 전부 ✓ 이면 핸즈온을 시작해도 된다.

    python3 _team/scripts/check.py
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace"); _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import os, sys, shutil, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ok = True


def line(good, what, fix=""):
    global ok
    ok = ok and good
    print(("  ✓ " if good else "  ✗ ") + what + ("" if good or not fix else "\n      → " + fix))


print("연구실 폴더: " + ROOT)
v = sys.version_info
line(v >= (3, 9), "Python %d.%d" % (v.major, v.minor), "Python 3.9 이상을 설치하세요 (python.org)")
try:
    import yaml  # noqa
    line(True, "pyyaml")
except ImportError:
    line(False, "pyyaml 없음", "python3 -m pip install --user -r requirements.txt")
line(bool(shutil.which("claude")), "Claude Code (claude 명령)", "Claude Code 를 설치하고 로그인하세요")
line(not os.environ.get("ANTHROPIC_API_KEY"), "ANTHROPIC_API_KEY 없음 (있으면 claude.ai 로그인이 꺼진다)", "터미널에서 unset ANTHROPIC_API_KEY")
for rel in ("_team/lab.yaml", "_team/registry.yaml", "_team/teams.yaml", "projects/P01_demo-ecg-sr/PROJECT.md", "_team/dashboard/source.html"):
    line(os.path.exists(os.path.join(ROOT, rel)), rel, "저장소를 다시 내려받으세요")
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import labconfig
    cfg = labconfig.load()
    line(bool(cfg["pi"].get("field")), "설정 문답 완료 (전공: %s)" % (cfg["pi"].get("field") or "비어 있음"), "Claude Code 에서 /setup")
except Exception as e:
    line(False, "설정을 읽지 못함: %s" % e)
r = subprocess.run([sys.executable, os.path.join(ROOT, "_team", "dashboard", "build.py"), "--check"], capture_output=True, text=True)
line(r.returncode == 0, "현황판 구조", (r.stdout + r.stderr).strip()[-120:])
dist = os.path.join(ROOT, "_team", "dashboard", "dist", "lab-dashboard.html")
line(os.path.exists(dist), "현황판 파일 있음", "python3 _team/dashboard/refresh.py")
print("\n" + ("전부 정상 — 핸즈온을 시작합니다. Claude Code 에서 /hands-on" if ok else "✗ 항목을 먼저 고치세요."))
sys.exit(0 if ok else 1)
