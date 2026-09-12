# AI 모델·벤치마크 연구 실행 지침

## 단계와 소집

| 단계 | 소집 | 사용 스킬 | 산출물 |
|------|------|-----------|--------|
| 평가 설계 | methodologist | `design-ai-benchmarking`, `design-study` | 평가질문, 비교군(arm) 정의, 루브릭 |
| 루브릭·평가자 | methodologist | `design-ai-benchmarking` | 차원별 앵커, 평가자 패널, IRR 목표 |
| 데이터 준비 | data-analyst | `clean-data`, `deidentify`, `version-dataset` | 평가셋, 분할 기록 |
| 실행 | data-analyst | `analyze-stats`, `batch-cohort` | 모델별 출력, 평가 결과 |
| 분석 | data-analyst → adversarial-reviewer | (설치된 통계 도구가 있으면) | 정확도·일치도·보정, 신뢰구간 |
| 원고 | writer → adversarial-reviewer | `write-paper`, `check-reporting`(TRIPOD+AI/TRIPOD-LLM/CLAIM) | 원고 |

## 이 유형에서 특히 주의할 것

- **누출(leakage)이 최대 위험이다.** 같은 환자의 다른 검사가 학습·평가에 나뉘어 들어가면 성능이 부풀려진다. 분할은 환자 단위로 하고 그 사실을 명시한다.
- **평가 시점을 고정한다.** 모델과 프롬프트는 버전·날짜와 함께 기록한다. 상용 LLM은 조용히 바뀌므로, 기록 없는 결과는 재현 불가능하다.
- **AUC만으로 임상적 유용성을 주장하지 않는다.** 유병률에 따른 PPV, 보정(calibration), 결정곡선을 함께 본다.
- **인간 전문가와 비교할 때** 전문가 패널 구성·경력·정보 제공 조건을 모델과 대칭으로 맞춘다. 비대칭이면 비교 자체가 무효다.
- LLM-as-judge를 쓸 때는 인간 평가와의 일치도를 먼저 보이고, 판정자 편향(자기 모델 선호)을 점검한다.
- 다중 비교(모델 × 지표 × 하위군)를 통제하거나 탐색적임을 명시한다.

## 검수 포인트
분할 단위 / 모델·프롬프트 버전 기록 / PPV·보정 제시 / 비교군 대칭성 / 평가자 신뢰도(IRR) / 다중비교 처리
