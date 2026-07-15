# Changelog

## [1.1.0] - 2026-07-13

### Added
- **한국 학술·정책 출처 검증(Step 3-D)**: 국제 DB(CrossRef·arXiv·Semantic Scholar)가 못 잡는 국문 학술지·국책연 보고서·정부 간행물을 KCI(한국연구재단)·RISS(KERIS)·국회도서관·NKIS·PRISM으로 별도 확인. 국문 문헌이 국제 DB에 없다고 환각으로 오판하던 공백을 메움
- **접근 등급(graceful degradation)**: 키 없이도 공개 검색+CrossRef로 동작, 공공데이터포털 인증키(무료)가 있으면 API로 정밀·대량 검증 자동 승급. 없는 능력을 있는 척하지 않음
- `references/korea-sources.md`: 검증원 목록·공공데이터포털 인증키 발급/설정 가이드·응답 처리 원칙
- tier-rules: KCI 등재지·국책연(NKIS)·국내 통계기관·과학기술 전문지 보강, "국문 문헌은 국제 DB에 안 잡혀도 실재할 수 있다" 원칙 명시

### Changed
- description·README에 참고문헌 실재 확인·한국 학술 검증 트리거 추가
- 한계 절: 한국 검증의 무키/유키 범위, DBpia 유료 원문 제한을 정직하게 명시

## [1.0.0] - 2026-07-13

초기 공개.

- R&D 동향 조사 에이전트 팀(2026-04 구축)의 내장 검증자(fact-verifier)를 독립 스킬로 승격·일반화
- 3단 검증 프로토콜: ① 4-Tier 출처 분류 ② 교차 일관성(재인용 체인 감지) ③ 실존 확인(URL/DOI/arXiv/NTIS)
- 판정 4단계(VERIFIED / NEEDS_REVIEW / REJECT / NO_SOURCE) + 사유·조치 병기
- 검증 깊이 3단(quick / standard / deep)
- 출력: 마크다운 검증 보고서(기본) + YAML(에이전트 파이프라인 연동용)
- `references/tier-rules.md`: STI 분야 기본 Tier 목록 + 분야 커스터마이즈 지침
