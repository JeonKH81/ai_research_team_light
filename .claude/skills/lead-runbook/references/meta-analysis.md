# 체계적문헌고찰·메타분석 실행 지침

## 단계와 소집

| 단계 | 소집 | 사용 스킬 | 산출물 |
|------|------|-----------|--------|
| 주제·공백 | lit-scout, methodologist | `ma-scout`, `search-lit` | 주제 타당성, 기존 SR 중복 확인 |
| 프로토콜 | methodologist | `write-protocol`, `check-reporting`(PRISMA-P) | 프로토콜, PROSPERO 등록안 |
| 검색 | lit-scout | `search-lit`, `fulltext-retrieval` | DB별 검색식·히트수·검색일 |
| 스크리닝 | lit-scout (2인 독립 시뮬레이션) | `meta-analysis` | 포함·제외 목록, 제외사유 |
| 추출 | data-analyst | `meta-analysis` | 추출표, 특성표 |
| 비뚤림 평가 | methodologist | `check-reporting`(QUADAS-2/ROBINS-I) | 항목별 판정 |
| 합성 | data-analyst | `meta-analysis`, `analyze-stats` | 통합추정치, 이질성, forest/SROC |
| 원고 | writer → adversarial-reviewer | `write-paper`, `check-reporting`(PRISMA) | 원고, PRISMA 흐름도 |

## 이 유형에서 특히 주의할 것

- **PROSPERO 등록 전에 검색을 끝내지 않는다.** 등록 시점 이후 검색이 표준이며, 순서가 뒤바뀌면 저널에서 지적받는다.
- **검색식은 그 자체가 결과물이다.** DB별 전체 문자열, 필터, 검색일, 히트 수를 원문 그대로 보존한다. 재현이 안 되면 SR이 아니다.
- **제외 사유 없는 제외는 없다.** PRISMA 흐름도의 모든 숫자는 기록에서 나온다. 사후에 복원할 수 없다.
- **진단정확도 메타분석은 단순 pooling을 쓰지 않는다.** 민감도·특이도의 상관 때문에 bivariate/HSROC가 표준이다.
- 이질성이 크면 통합값을 제시하기 전에 원인을 다룬다. I²만 보고하고 넘어가지 않는다.

## 검수 포인트
검색일·히트수 기록 / 제외사유 완전성 / 흐름도 숫자 정합 / 비뚤림 평가의 판단 근거 / 이질성 처리
