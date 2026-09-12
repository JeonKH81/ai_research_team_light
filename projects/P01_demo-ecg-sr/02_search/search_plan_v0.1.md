# 검색계획 v0.1 (본보기)

**판본:** v0.1 (2026-09-03 초안) · **상태:** 동료검토(PRESS) 회신 대기
**본보기 문서다.** 실제로 돌린 검색이 아니다.

## 정보원 (6개)
서지 데이터베이스 4개 + 전문 검색 1개 + 임상시험 등록부 1개. 합집합으로 쓴다.

## 개념 블록
1. 대상 — 당뇨병 · 당뇨망막병증
2. 검사 — 안저사진 · 안저촬영
3. 도구 — 인공지능 · 딥러닝 · 자동판독
4. 결과 — 진단정확도 · 민감도 · 특이도 · 검진

## 주 검색식 (본보기)
```
(diabet*[tiab] AND (retinopath*[tiab] OR "fundus"[tiab]))
AND ("artificial intelligence"[tiab] OR "deep learning"[tiab] OR automat*[tiab])
AND (sensitivit*[tiab] OR specificit*[tiab] OR "diagnostic accuracy"[tiab] OR screening[tiab])
```

## 제한
언어 제한 없음. 날짜 제한 없음 — 제한을 걸려면 실측 근거(오래된 구간 표본 감사)를 먼저 만든다.

## 검증
1. 시드 논문 회수 — 미리 정해 둔 시드가 전부 걸리는지 확인
2. 상대재현율 — 기존 고찰의 포함 문헌을 골드셋으로 삼아 회수율 확인
3. **둘 다 통과해야 정식 검색을 연다**

## 남은 것
- PRESS 회신 반영 (**대기 중**)
- 정보원별 구문 변환과 시험 검색
