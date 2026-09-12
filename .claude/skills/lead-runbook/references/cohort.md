# 코호트·관찰연구 실행 지침

## 단계와 소집

| 단계 | 소집 | 사용 스킬 | 산출물 |
|------|------|-----------|--------|
| 설계 | methodologist | `design-study`, `find-cohort-gap` | 설계서, 바이어스 점검 |
| 변수 정의 | methodologist (+lit-scout 근거) | `define-variables`, `generate-codebook` | 인용 붙은 변수정의표 |
| 표본수 | methodologist | `calc-sample-size` | 산출근거, IRB용 문단 |
| 데이터 점검 | data-analyst | `clean-data`, `clinical-eda-report`, `deidentify` | 프로파일링, 정제 코드 |
| 잠금 | data-analyst | `version-dataset` | 데이터 매니페스트 |
| 분석 | data-analyst | `clinical-table1`, `clinical-cox-regression`, `clinical-km-survival-analysis`, `analyze-stats` | Table 1, 주분석, 민감도분석 |
| 검증 | adversarial-reviewer | (설치된 검증 도구가 있으면) | 검증 리포트 |
| 원고 | writer → adversarial-reviewer | `write-paper`, `check-reporting`(STROBE) | 원고 |

## 이 유형에서 특히 주의할 것

- **분석 전에 데이터를 잠근다.** `version-dataset`으로 매니페스트를 만들어 두면 "그때 그 데이터"를 증명할 수 있다. 코호트 데이터는 조용히 바뀐다.
- **불멸시간 바이어스**를 설계 단계에서 확인한다 — 노출 정의 시점과 추적 시작 시점이 다르면 발생하고, 분석 후에는 되돌릴 수 없다.
- **경쟁위험**이 있는 결과변수(심혈관 사망 vs 전체 사망)에 Kaplan-Meier를 그대로 쓰면 발생률이 과대추정된다.
- **변수 정의에 임의 컷오프를 쓰지 않는다.** 문헌 근거 없는 컷오프는 리뷰어의 첫 표적이다.
- 결측이 10%를 넘으면 완전사례분석만으로 끝내지 않는다. 결측 기전을 논의하고 민감도분석을 붙인다.
- 인과적 표현은 설계가 허락하는 만큼만 쓴다.

## 검수 포인트
데이터 잠금 여부 / 노출·추적 시점 정합 / 경쟁위험 처리 / 결측 처리와 제외 수 보고 / Table 1의 수치가 스크립트 출력과 일치

## 도구가 없을 때 (경량판)

위에 적힌 스킬 이름(`search-lit`·`verify-refs`·`ma-scout`·`find-cohort-gap`·`write-protocol`·`calc-sample-size`·`define-variables` 등)은 **별도 설치하는 도구 묶음**의 것이다. `/help` 에 없으면 **같은 일을 직접 한다** — 문헌 검색은 PubMed 검색식을 만들어 `python3 _team/scripts/discover.py --days 30 --topic <key>` 또는 사용자에게 검색 실행을 부탁하고, 인용 확인은 PMID 를 하나씩 대조하며, 표본수는 표준 공식으로 계산 과정을 보이고, 프로토콜은 `projects/_template/` 의 서식을 따른다. **도구가 없다고 그 단계를 건너뛰지 않으며, 없었다는 사실을 산출물에 적는다.**
