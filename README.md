# fact-verify

[![Version](https://img.shields.io/badge/version-1.1.0-blue.svg)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
![Claude Code](https://img.shields.io/badge/Claude_Code-Skill-purple.svg)

**한국어** · [English](README.en.md)

AI가 모아 온 조사 결과·동향 브리핑·보고서 초안의 **출처를 믿기 전에 검증**하는 [Claude Code](https://claude.com/claude-code) 스킬입니다.
일반 "팩트체커"가 아니라 연구·정책 문서의 **출처 규율** 도구입니다 — 출처가 실존하는지, 주장을 실제로 뒷받침하는지, 여러 출처처럼 보이는 것이 실은 한 보도자료의 재인용인지를 가려냅니다.

<!-- 데모 GIF 자리 -->

## 무엇을 잡나

| 실전에서 마주친 실패 | 대응 장치 |
|---|---|
| 존재하지 않는 arXiv ID·DOI를 단 인용 (할루시네이션) | **Step 3 실존 확인** — 식별자를 실제로 resolve |
| 언론 3곳 보도처럼 보이지만 전부 같은 보도자료 (**가짜 교차검증**) | **Step 2 재인용 체인 감지** — 독립 출처 수를 다시 셈 |
| 블로그 글이 정부 통계처럼 인용되는 신뢰도 세탁 | **Step 1 4-Tier 분류** — Tier 4 단독 근거 불가, 원출처로 승격 |
| 국문 논문·국책연 보고서를 국제 DB로 확인 못 해 "출처 불명" 처리 | **Step 3-D 한국 검증원** — KCI·RISS·국회도서관·NKIS |

마지막 줄이 **국제 도구와의 결정적 차별점**입니다. 국문 학술지 논문·국책연구원 보고서·정부 간행물은 DOI가 없는 경우가 많아 CrossRef·arXiv·Semantic Scholar 같은 국제 DB에 거의 잡히지 않습니다. 그래서 국제 검증 도구는 멀쩡히 실재하는 「한국정책학회보」 논문이나 KISTEP 이슈페이퍼를 "확인 불가"로 되돌리고, 그대로 검증을 돌리면 **진짜 출처가 환각으로 오판**됩니다. 실제 문헌을 지우는 오판은 가짜를 통과시키는 것만큼 나쁩니다.

→ [왜 만들었나·상세 사용법](docs/why.md)

## 3단 프로토콜

```
Step 1 4-Tier 분류 → Step 2 재인용 체인 감지 → Step 3 실존 확인 (+ 3-D 한국 검증원)
```

기본 상태는 의심이고, 증거가 있어야 통과합니다. 항목마다 ✅ VERIFIED · ⚠️ NEEDS_REVIEW("틀렸다"가 아니라 "확인하지 못했다") · ❌ REJECT(본문에서 제외) · 🚫 NO_SOURCE(출처 없는 사실 주장) 중 하나와 **사유·조치**가 붙고, 통과하지 못한 항목은 조사 담당에게 그대로 넘길 수 있는 **재조사 요청서**로 함께 나옵니다.
`조사 → fact-verify → 집필`로 배치하면 어떤 리서치 파이프라인에도 게이트가 생깁니다 — 검증자가 조사·집필과 **다른 에이전트**여야 게이트입니다. YAML 연동은 [SKILL.md](SKILL.md).

## 설치

```bash
mkdir -p ~/.claude/skills
cd ~/.claude/skills
git clone https://github.com/parkjui92/fact-verify.git
```

Claude Code를 재시작하면 자동 인식됩니다. [공공데이터포털](https://www.data.go.kr) 인증키(무료)를 `DATA_GO_KR_KEY`에 설정하면 KCI·RISS·국회도서관 API 경로로 승급하지만, **키는 요구사항이 아니라 성능 옵션**입니다 — 없으면 공개 검색 범위에서 확인하고 못 미친 부분은 ⚠️로 정직하게 남깁니다.

## 쓰는 법

```
이번 주 동향 브리핑 초안이야. 근거들 출처 검증해줘                ← standard(기본)
이 원고 참고문헌이 실제로 존재하는지 확인해줘. 국문 논문이 많아   ← 국문 문헌 검증
이 보고서 대외 배포용이야. deep으로 검증해줘                      ← 수치·날짜 원문 대조
지금 오프라인이야. Tier 분류랑 식별자 형식만 훑어줘               ← quick(네트워크 불필요)
```

`quick`은 **실존을 확인하지 않으므로** 발행 전에는 반드시 `standard` 이상으로 다시 돌리십시오. 깊이를 적지 않으면 `standard`로 동작합니다.

## 출력 예시

| # | 주장(요약) | 출처 | Tier | 판정 | 사유·조치 |
|---|---|---|---|---|---|
| 1 | 신규 아키텍처 성능 2배 | arXiv 2404.99999 | 2 | ❌ | 해당 ID 실존하지 않음 — 삭제·재조사 |
| 2 | 업계 투자 급증 | 매경·한경 기사 2건 | 3 | ⚠️ | 둘 다 동일 보도자료 재인용 — 독립 출처 1개 |
| 3 | 혁신클러스터 효과 | 한국정책학회보 32(1) | 2 | ✅ | KCI 조회 확인 (인용 연도 오기 2022→2021 지적) |

표 위에는 총계(대상 N건 / 판정별 건수 / Tier 분포 / 검증 깊이·일시)가 함께 붙습니다. 전체 형태: [examples/verification-report-example.md](examples/verification-report-example.md)

## 한계

- **웹 접근이 필요합니다.** 오프라인에서는 `quick` 깊이만 가능하고, 페이월·유료 원문(DBpia 등)은 확인 불가 시 ⚠️로 보류합니다 — 오류로 단정하지 않습니다
- **출처 규율 도구이지 진위 판정 도구가 아닙니다.** 주장 자체의 학술적 타당성을 최종 보증하지 않습니다. 최종 책임은 사람에게 있습니다
- **검증자도 같은 계열 모델입니다.** 게이트는 오류를 줄이지 없애지 못합니다
- 외부로 나가는 것은 **확인 대상 URL·식별자·검색어(제목·저자)뿐**입니다. 문서 전체를 외부 서비스에 보내지 않습니다
- 기본 Tier 목록은 **과학기술정책(STI) 분야** 기준입니다 — [references/tier-rules.md](references/tier-rules.md)에 자기 분야의 기관·학술지를 추가해 쓰십시오

## 시리즈

**에이전트 팀 킷** — [policy-research-kit](https://github.com/parkjui92/policy-research-kit) (정책연구보고서) · [rnd-proposal-kit](https://github.com/parkjui92/rnd-proposal-kit) (정부 R&D 제안서) · [socsci-paper-kit](https://github.com/parkjui92/socsci-paper-kit) (사회과학 논문)

**제작·편집 킷** — [lecture-deck-kit](https://github.com/parkjui92/lecture-deck-kit) (강의자료 HTML 덱 · 브라우저 라이브 편집)

**단독 스킬** — **fact-verify** (이 저장소, 출처 검증) · [paper-proofread](https://github.com/parkjui92/paper-proofread) (한국어 학술 교정교열) · [form-tailor](https://github.com/parkjui92/form-tailor) (기관 양식 맞춤) · [report-to-brief](https://github.com/parkjui92/report-to-brief) (보고서 압축)

## 라이선스

[MIT](LICENSE)
