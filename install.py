#!/usr/bin/env python3
"""설치 — 한 번만. 맥·윈도우·리눅스 공통.

    python3 install.py        (맥·리눅스)
    python  install.py        (윈도우 PowerShell)

필요한 것을 확인하고, 없는 것은 넣고(pyyaml · truststore), 첫 현황판을 만들고, 확인 도구를 돌린다.
"""
import os, sys, subprocess, platform

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
PY = sys.executable
WIN = platform.system() == "Windows"
print("연구실 폴더: " + HERE)
print("운영체제   : " + platform.system() + "  ·  Python " + platform.python_version())

if sys.version_info < (3, 9):
    print("✗ Python 3.9 이상이 필요합니다. https://www.python.org/downloads/ 에서 설치한 뒤 다시 실행하세요.")
    sys.exit(1)


def pip(*args):
    return subprocess.run([PY, "-m", "pip", *args], capture_output=True, text=True)


def have(mod):
    return subprocess.run([PY, "-c", "import " + mod], capture_output=True).returncode == 0


if not have("yaml") or (sys.version_info >= (3, 10) and not have("truststore")):
    print("필요한 부품을 넣습니다 (pyyaml · truststore)…")
    r = pip("install", "--user", "-r", "requirements.txt")
    if r.returncode != 0 and "externally-managed" in (r.stdout + r.stderr):
        print("  사용자 설치가 막혀 있어 연구실 전용 공간(.venv)에 넣습니다")
        subprocess.run([PY, "-m", "venv", ".venv"], check=True)
        vpy = os.path.join(".venv", "Scripts" if WIN else "bin", "python.exe" if WIN else "python3")
        subprocess.run([vpy, "-m", "pip", "install", "-q", "-r", "requirements.txt"], check=True)
        PY = vpy
        print("  앞으로 이 폴더에서는 먼저:  " + (r".venv\Scripts\activate" if WIN else "source .venv/bin/activate"))
    elif r.returncode != 0:
        print("  ✗ 설치 실패:\n" + (r.stderr or r.stdout).strip()[-400:])
        sys.exit(1)

r = subprocess.run([PY, os.path.join("_team", "dashboard", "refresh.py")], capture_output=True, text=True)
print("첫 현황판을 만들었습니다." if r.returncode == 0 else "✗ 현황판을 만들지 못했습니다:\n" + (r.stderr or r.stdout).strip()[-300:])
print()
subprocess.run([PY, os.path.join("_team", "scripts", "check.py")])
print()
print("다음:  claude   ← 이 폴더에서 열면 그 창이 총괄팀장입니다. 첫 대화에서  /setup  이라고 치세요.")
print("현황판 열기:  " + ("start _team\\dashboard\\dist\\lab-dashboard.html" if WIN else "open _team/dashboard/dist/lab-dashboard.html"))
