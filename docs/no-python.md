# Python 이 없을 때 — 총괄팀장이 대신 하는 법

> 이 문서는 **총괄팀장(Claude)이 읽는 지침**입니다. 사람이 따라 할 절차가 아닙니다.

이 연구실의 도구 몇 가지는 Python 으로 돕니다. **윈도우에는 Python 이 기본으로 없어서**
핸즈온에서 참석자 다수가 여기서 멈추는 일이 실제로 있었습니다(2026-09-17).

**Python 이 없다고 실습을 멈추지 않는다.** 아래대로 총괄팀장이 파일을 직접 다뤄 같은 일을 한다.
실습의 뼈대 — 설정, 연구 등록, 연구원 정의, 팀장 창, 연구원 소환, 검토 — 는 **전부 파일 작업이라
Python 이 필요 없다.** Python 이 꼭 필요한 것은 **문헌 수집** 하나뿐이다.

## 언제 이 판으로 가는가

시작할 때 `python3 --version` 과 `python --version` 을 한 번씩 본다. 둘 다 없으면 이 판이다.
참석자에게는 이렇게만 말한다:

> "이 컴퓨터에는 Python 이 없네요. 오늘 실습은 그대로 갑니다 — 제가 대신 처리하겠습니다.
> 문헌 자동 수집 한 가지만 오늘은 빼고, 나머지는 똑같이 돕니다."

**설치를 시키지 않는다.** 현장에서 Python 을 깔면 한 사람당 10분이 날아가고, 한 명이 막히면 전체가 선다.
설치는 실습이 끝난 뒤 [준비 문서](prepare.md)로 안내한다.

## 무엇을 무엇으로 대신하는가

| 원래 도구 | 하는 일 | Python 없이 |
|---|---|---|
| `_team/scripts/check.py` | 설치 확인 | 아래 파일들이 있는지 직접 보고 같은 형식으로 보고한다 |
| `_team/scripts/setup.py --apply` | 설정 반영 | `_team/lab.yaml` 을 직접 고친다 |
| `_team/dashboard/refresh.py` + `build.py` | 현황판 | 등록부를 읽어 **간단한 현황판 HTML 을 직접 쓴다**(아래) |
| `_team/scripts/report.py status` | 보고 기록 | `_team/registry.yaml` 과 `_team/status_log.tsv` 를 직접 고친다 |
| `_team/scripts/discover.py` | 문헌 수집 | **대신할 수 없다.** 오늘은 건너뛴다고 말한다 |

### 설치 확인 대신

다음이 있는지 보고, 있으면 `✓`, 없으면 `✗` 로 같은 모양의 목록을 만든다:
`_team/lab.yaml` · `_team/registry.yaml` · `_team/teams.yaml` · `projects/_template/PROJECT.md` ·
`_team/dashboard/source.html` · `.claude/agents/` 안 연구원 정의 9개 · `.claude/skills/` 안 스킬들.
맨 끝에 한 줄: **"Python 은 없지만 실습에는 지장 없습니다. 문헌 자동 수집만 오늘 빼겠습니다."**

### 설정 문답(`/setup`) 대신

문답은 그대로 진행한다. 답을 `_team/lab.yaml` 에 **직접 적는다** — 형식과 주석은 그대로 두고 값만 바꾼다.
`lab_name` · `pi.field` · `lab_meeting` · `ideation.topics` 가 채워지면 된다.
팀 이름을 태양계에서 바꿨으면 `_team/teams.yaml` 과 `_team/roster.md` 의 이름도 같이 고친다.
검색식은 만들어 보여 주되 **미리보기 수집은 돌릴 수 없으므로 "오늘은 확인하지 못합니다"라고 밝힌다.**

### 연구 등록(`/project-intake`) 대신

폴더와 문서를 직접 만든다: `projects/P0X_<slug>/PROJECT.md` 와 `projects/P0X_<slug>/CLAUDE.md`
(둘 다 `projects/_template/` 의 것을 본보기로). 그리고 `_team/registry.yaml` 의 `projects:` 아래에
한 건을 **같은 형식으로** 덧붙인다 — `id` `slug` `title` `stage` `path` `team` `team_ko` `code` `label`
`next` `updated` 는 반드시 채우고, 모르는 것은 `[확인 필요]` 로 둔다.

### 보고(`report.py status`) 대신

`_team/registry.yaml` 의 그 프로젝트에서 `stage` · `next` · `blockers` · `updated` 를 고치고,
`_team/status_log.tsv` 맨 끝에 **탭으로 나눈 한 줄**을 덧붙인다:
`날짜 ⇥ 팀 ⇥ 출처 ⇥ 이전단계 ⇥ 이후단계 ⇥ 대기수 ⇥ 메모`

### 현황판 대신

`_team/dashboard/dist/` 폴더에 **`lab-dashboard-simple.html`** 을 직접 쓴다.
정식 현황판 파일(`lab-dashboard.html`)을 덮어쓰지 않는다 — 나중에 Python 을 깔면 정식판이 다시 만들어져야 한다.

한 장짜리로 충분하다. 등록부에서 읽어 이만큼만 담는다:
- 머리: 연구실 이름, 만든 시각, "간단판 — Python 을 설치하면 정식 현황판이 만들어집니다" 한 줄
- 팀 10줄: `label`(행성_약어) · `stage` · `next` · 대기 건수. 프로젝트 없는 팀은 **미배정**
- 각 줄을 눌러 펼치면 `blockers` 와 `open_items`

바깥에서 받아오는 것 없이 **한 파일로** 쓴다(글꼴·그림·스크립트를 밖에서 불러오지 않는다).
다 쓰면 파일 경로를 알려 주고, 참석자가 직접 두 번 눌러 열게 한다.
설명 한 줄은 정식판과 같다: *이 화면은 손으로 그리지 않습니다. 등록부와 프로젝트 문서에서 매번 다시 만들어집니다.*

## 실습이 끝난 뒤

마무리에서 한 줄 덧붙인다:

> "오늘 문헌 자동 수집만 빼고 다 해 보셨습니다. 집에서 Python 을 한 번 깔면 그것까지 돕니다 —
> 준비 문서에 한 줄짜리 방법이 있습니다."
