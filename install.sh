#!/bin/zsh
# 설치 — 한 번만. 필요한 것을 확인하고, 없는 것은 넣고, 첫 현황판을 만든다.
#   zsh install.sh
HERE=${0:A:h}
cd "$HERE" || exit 1
echo "연구실 폴더: $HERE"
if ! command -v python3 >/dev/null; then echo "✗ python3 가 없습니다. https://www.python.org/downloads/macos/ 에서 설치하세요."; exit 1; fi
if ! python3 -c "import yaml" 2>/dev/null; then
  echo "pyyaml 을 넣습니다…"
  python3 -m pip install --user -r requirements.txt 2>/dev/null || {
    echo "  사용자 설치가 막혀 있어 연구실 전용 공간(.venv)에 넣습니다"
    python3 -m venv .venv && .venv/bin/python3 -m pip install -q -r requirements.txt && echo "  앞으로 이 폴더에서는  source .venv/bin/activate  를 먼저 하세요"; }
fi
python3 _team/dashboard/refresh.py >/dev/null 2>&1 && echo "첫 현황판을 만들었습니다."
python3 _team/scripts/check.py
echo
echo "다음:  claude   ← 이 폴더에서 열면 그 창이 총괄팀장입니다. 첫 대화에서  /setup  이라고 치세요."
