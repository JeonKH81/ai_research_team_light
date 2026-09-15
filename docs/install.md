# 설치 — 참석자용

내려받기부터 첫 현황판까지 **20분 안**에 끝납니다. 이어서 `/hands-on` 으로 실습을 시작합니다.

---

## 0. 미리 있어야 하는 것

| 무엇 | 확인하는 법 | 없으면 |
|---|---|---|
| macOS · Windows · Linux | — | 셋 다 됩니다. 윈도우는 PowerShell 로 진행합니다([윈도우에서는](#윈도우에서는)) |
| Git | `git --version` | 맥: 터미널에서 `git` 을 치면 설치를 권합니다. 윈도우: Git for Windows 를 설치합니다 |
| Python 3.9 이상 | `python3 --version` | [python.org](https://www.python.org/downloads/) 에서 설치합니다 |
| Claude Code | `claude --version` | [공식 설치 안내](https://code.claude.com/docs/en/setup)대로 설치하고 `claude` 를 한 번 실행해 **유료 Claude 계정**으로 로그인합니다(무료 계정은 Claude Code 를 쓸 수 없습니다). 별도의 열쇠는 필요 없습니다 |
| 인터넷 | — | Claude Code 대화와 문헌 수집에 필요합니다. 현황판·보고 도구는 인터넷 없이도 돕니다 |

문헌을 받아오는 곳(PubMed·medRxiv·arXiv·ClinicalTrials.gov)은 **등록도 열쇠도 필요 없습니다.**

---

## 1. 내려받습니다

**터미널 없이 하려면 (권장, 핸즈온):** GitHub 페이지의 초록 **Code → Download ZIP** 으로 받아 압축을 풀고, **Claude 앱 → Code 탭 → 폴더 열기**로 그 폴더를 엽니다. 폴더 이름이 `ai_research_team_light-main` 이어도 됩니다. 이후 단계는 앱 안의 대화창에서 그대로 진행합니다 — 명령은 앞에 `!` 를 붙여 치거나, 총괄팀장에게 "설치 확인 돌려 줘"라고 하면 됩니다.

**터미널로 하려면:**

```bash
git clone https://github.com/JeonKH81/ai_research_team_light.git ~/ai_research_team_light
cd ~/ai_research_team_light
```

폴더는 어디에 두어도 됩니다 — 안에서 도는 것들이 **자기가 놓인 자리를 스스로 찾습니다.**
경로를 고쳐 넣는 절차는 없습니다.

---

## 2. 설치합니다

```bash
python3 install.py
```

이 한 줄이 하는 일은 셋입니다: 필요한 것이 있는지 보고 → 없는 것(`pyyaml`)을 넣고 → 첫 현황판을 만듭니다.
끝에 확인 결과가 줄줄이 뜹니다.

```
  ✓ Python 3.12
  ✓ pyyaml
  ✓ Claude Code (claude 명령)
  ✓ ANTHROPIC_API_KEY 없음 (있으면 claude.ai 로그인이 꺼진다)
  ✓ _team/lab.yaml
  ...
  · 설정 문답은 아직 — 설치와는 별개. Claude Code 에서 /setup
      → Claude Code 에서 /setup
```

**읽는 법은 간단합니다.** `✓` 는 됐다는 뜻이고, `✗` 는 그 아래 `→` 가 시키는 대로 하면 됩니다.
설치 직후에는 마지막에 **"설치는 정상. 다음은 Claude Code 에서 /setup"** 이 나오면 됩니다. `✗` 가 있으면 그 줄이 시키는 대로 고칩니다.

확인만 다시 하고 싶으면 언제든:

```bash
python3 _team/scripts/check.py
```

---

## 3. Claude Code 를 엽니다

```bash
claude
```

**이 폴더에서 연 창이 총괄팀장입니다.** 창을 열면 최상위 `CLAUDE.md` 를 먼저 읽고 연구실 규칙을 알게 됩니다.
확인 삼아 한 번 물어보세요 — `연구실 현황 보여줘`. 본보기 연구 한 건(`Terra_DEMO-SR`)이 보이면 제대로 들어온 것입니다.

---

## 4. `/setup` — 다섯 문항 (10분)

총괄팀장 창에서 **`/setup`** 이라고 칩니다. 다섯 가지를 **한 번에 하나씩** 묻습니다.

| 묻는 것 | 무엇을 정하는가 | 기본값 |
|---|---|---|
| ① 연구실 이름 | 현황판 머리에 뜨는 이름입니다 | `AI Research Team` |
| ② 연구책임자 전공 | 발굴팀이 후보를 낼 출발점입니다. 소속은 선택 | 비어 있음 |
| ③ 팀 이름 규칙 | 팀은 언제나 열 개입니다. 태양계 열 개를 쓰거나 직접 정합니다 | 태양계 (Mercury … Pluto) |
| ④ 발굴팀 | 관심 영역 **1~3개**와 영역마다 **어디서 모을지**. 말로 설명하면 검색식을 대신 만들어 줍니다 | 둔다 / PubMed + medRxiv |
| ⑤ 랩미팅 | 할지 · 간격(매주·격주·4주) · 요일 · 시각 | 한다 / 매주 화 07:00 |

④에서 고를 수 있는 곳은 넷입니다 — **PubMed**(학술지) · **medRxiv**(의학 프리프린트) ·
**arXiv**(인공지능·통계 방법론) · **ClinicalTrials.gov**(임상시험 등록).
방법론 영역이면 arXiv 를, 중재 연구 영역이면 임상시험 등록을 함께 고르면 좋습니다.
**검색식은 하루 5~30건이 목표입니다** — 너무 넓으면 못 읽고 너무 좁으면 0건입니다.
총괄팀장이 만든 검색식을 보여 주고 확인을 받은 뒤, 실제로 몇 건이 잡히는지 미리보기로 확인해 줍니다.

답은 **`_team/lab.yaml` 한 파일**에 남습니다 — 연구실 설정이 전부 들어 있는 파일입니다.
현황판·브리핑·문헌 수집이 모두 그것을 읽습니다. 나중에 바꾸고 싶으면 다시 `/setup`, 바꿀 것만 물어봅니다.

터미널에서 직접 하고 싶으면:

```bash
python3 _team/scripts/setup.py            # 묻고 → 적고 → 반영
python3 _team/scripts/setup.py --apply    # lab.yaml 을 손으로 고친 뒤 반영만
```

---

## 5. 현황판을 엽니다

현황판은 열 팀이 지금 어느 단계에 있고 무엇을 기다리는지를 한 화면에 놓은 것입니다.

```bash
python3 _team/dashboard/refresh.py
open _team/dashboard/dist/lab-dashboard.html        # 윈도우: start _team\dashboard\dist\lab-dashboard.html
```

`refresh.py` 는 등록부와 폴더의 수정 시각을 읽어 **숫자와 단계 표시만** 다시 씁니다.
문장과 해석은 판단이 섞이므로 건드리지 않습니다. 무엇이 바뀔지만 미리 보려면 `--dry` 를 붙입니다.

> Linux 에서는 `open` 대신 `xdg-open` 을 쓰거나, 파일을 브라우저로 직접 열면 됩니다.

여기까지 되면 설치는 끝입니다. 총괄팀장 창에서 **`/hands-on`** 이라고 치고 실습을 시작하세요
(순서는 [핸즈온 대본](handson.md)에 그대로 있습니다).

---

## 윈도우에서는

같은 저장소가 그대로 돕니다. **PowerShell 한 가지로만** 진행합니다(Git Bash·WSL 을 섞지 않습니다).

**미리 설치할 것 셋** — 행사 전에: Python 3.9 이상(설치 때 *Add python.exe to PATH* 를 켭니다), Git for Windows, Claude Code(설치 후 `claude` 로 로그인).

| 맥·리눅스 | 윈도우 PowerShell |
|---|---|
| `python3 install.py` | `python install.py` |
| `open _team/dashboard/dist/lab-dashboard.html` | `start _team\dashboard\dist\lab-dashboard.html` |
| `unset ANTHROPIC_API_KEY` | `Remove-Item Env:ANTHROPIC_API_KEY` |
| `source .venv/bin/activate` (전용 공간을 만든 경우) | `.\.venv\Scripts\Activate.ps1` — 실행이 막혀 있으면 활성화 대신 `.\.venv\Scripts\python.exe` 를 `python` 자리에 그대로 씁니다 |

이 문서의 나머지 명령은 앞의 `python3` 를 `python` 으로 바꿔 읽으면 됩니다. 폴더 경로에 공백이나 한글이 있으면 **큰따옴표로 감쌉니다** — `cd "C:\Users\홍길동\ai_research_team_light"`.
전용 공간(`.venv`)을 만들었다면 **새로 여는 창마다**(팀장 창·발굴 화면 창도) 같은 활성화를 먼저 합니다.
정해진 시각에 저절로 도는 기능은 경량판에 없으므로 운영체제 차이가 나는 곳이 더는 없습니다.

## 문제가 생기면

### `externally-managed-environment` 라며 `pyyaml` 이 안 들어갑니다

요즘 파이썬은 시스템 공간에 함부로 넣지 못하게 막아 둡니다. `install.py` 가 이것을 만나면
연구실 전용 공간(`.venv`)에 대신 넣고 그렇게 알려 줍니다. 그 뒤로는 이 폴더에서 일을 시작할 때 먼저:

```bash
source .venv/bin/activate
```

손으로 만들려면 `python3 -m venv .venv` → `source .venv/bin/activate` → `python3 -m pip install -r requirements.txt`.

### 확인 결과에 `ANTHROPIC_API_KEY 없음` 이 `✗` 로 뜹니다

열쇠 값이 환경에 설정돼 있으면 **claude.ai 구독 로그인이 꺼집니다.** 이 연구실은 구독 로그인으로 씁니다.

```bash
unset ANTHROPIC_API_KEY                 # 윈도우 PowerShell: Remove-Item Env:ANTHROPIC_API_KEY
```

창을 새로 열 때마다 되살아난다면 `~/.zshrc` 나 `~/.zshenv` 에 그 줄이 있는 것이니 지우거나 앞에 `#` 을 붙입니다.

### 문헌을 하나도 못 받아옵니다 (병원망·회사망)

`install.py` 가 넣는 인증서 부품(`truststore`)이 운영체제가 믿는 인증서를 파이썬에 그대로 쓰게 합니다. 설치를 다시 돌리면 들어갑니다. 맥에서 그래도 안 되면 `zsh _team/scripts/fix_certificates.sh` 를 한 번 돌립니다.

`CERTIFICATE_VERIFY_FAILED` 라는 말이 보이면 통신이 막힌 것이 아닙니다. 중간에 있는 장비가 통신을 열어 보고
**자기 신분증으로 다시 봉해서** 보내기 때문입니다. 사파리와 Claude 는 잘 되는데 파이썬만 안 되는 이유가 이것입니다.

```bash
python3 install.py
```

이 컴퓨터가 믿는 신분증들을 모아 한 꾸러미로 만들어 두면 문헌 수집이 그것을 찾아 씁니다.
**관리자 권한은 필요 없습니다.** 기관이 신분증을 바꾸면 다시 실행하면 됩니다.

### `claude` 라고 쳤는데 명령이 없다고 합니다

Claude Code 가 아직 설치되지 않았거나, 설치는 됐는데 터미널이 그 자리를 모르는 것입니다.
설치 안내대로 다시 설치한 뒤 **터미널 창을 새로 열어** `claude --version` 으로 확인합니다.
설치가 끝났으면 한 번 `claude` 를 실행해 Claude 계정으로 로그인해 둡니다.

### 현황판이 열리지 않거나 비어 있습니다

먼저 `python3 _team/dashboard/refresh.py` 를 한 번 돌립니다. 그래도 안 되면
`python3 _team/scripts/check.py` 로 어느 줄이 `✗` 인지 봅니다 — 그 줄이 시키는 대로 고치면 됩니다.
