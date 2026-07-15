# Tier 분류 상세 규칙

fact-verify 스킬 Step 1에서 참조하는 출처 신뢰도 Tier 판정 기준.
기본 목록은 과학기술정책(STI) 분야 기준 — 말미의 커스터마이즈 지침에 따라 자기 분야로 보강해 쓴다.
한국 학술·정책 출처의 실재 확인 방법은 `korea-sources.md` 참조.

## Tier 1 — 정부·기관 공식

### 자동 판정 도메인
```
.go.kr        (한국 정부 기관)
.gov          (미국 정부)
.gov.uk       (영국 정부)
.europa.eu    (EU 기관)
.go.jp        (일본 정부)
.mil          (미군 — darpa.mil 등)
```

### 명시적 Tier 1 기관 (예시)
- 과학기술정보통신부 (msit.go.kr) · 기획재정부 (moef.go.kr)
- 한국연구재단 (nrf.re.kr) · 정책브리핑 (korea.kr)
- 국회 (assembly.go.kr) · 국회예산정책처 (nabo.go.kr) · 국회입법조사처
- 통계청 (kostat.go.kr) · e-나라지표 · KOSIS
- NSF (nsf.gov) · NIH (nih.gov) · DARPA (darpa.mil)
- UKRI (ukri.org) · JSPS (jsps.go.jp) · DFG (dfg.de)
- OECD (oecd.org) · UN 계열 공식 기구

### 규칙
- 단독 근거로 사용 가능
- **공식 발표·공고·보도자료·통계 원문만** 해당 (기관 포털에 걸린 외부 링크·보도 스크랩은 아님)

---

## Tier 2 — 학술·국책연구

### 국책연구기관 (예시)
- KISTEP (kistep.re.kr) · KISTI (kisti.re.kr) · STEPI (stepi.re.kr)
- 경제·인문사회연구회 소관 연구기관 간행물 (KDI·KIEP·KIPF 등)
- 국책연 보고서는 **NKIS**(nkis.re.kr)·기관 사이트에서 실재 확인 (korea-sources.md)

### Peer-reviewed 학술지
- Nature, Science, Cell 등 종합 top-tier
- Research Policy, Technovation, Scientometrics 등 분야 전문지
- **KCI 등재/등재후보 국내 학회지** — 실재·서지 확인은 KCI로 (korea-sources.md)

### 싱크탱크
- Brookings (brookings.edu) · RAND (rand.org) · CSIS (csis.org)

### 규칙
- 단독 근거로 사용 가능 (전문 판단 영역)
- peer-review 여부 확인 권장. 프리프린트(arXiv 등)는 "미심사" 표기를 병기
- 워킹페이퍼·이슈페이퍼는 기관 공식 간행물인지 확인
- **국문 문헌은 국제 DB에 안 잡혀도 실재할 수 있다** — KCI·RISS·국회도서관으로 교차 확인 후 판정

---

## Tier 3 — 주요 언론

### 국내
- 종합일간지: 조선 (chosun.com) · 중앙 (joongang.co.kr) · 동아 (donga.com) · 한겨레 (hani.co.kr) · 경향 (khan.co.kr)
- 경제지: 매일경제 (mk.co.kr) · 한국경제 (hankyung.com) · 서울경제 (sedaily.com)
- 과학·기술 전문: 동아사이언스 (dongascience.com) · 전자신문 (etnews.com) · HelloDD (hellodd.com)
- 통신사: 연합뉴스 (yna.co.kr)

### 해외
- NYT · WSJ · FT · The Guardian · Reuters · AP
- Economist · MIT Technology Review · Wired

### 규칙
- 핵심 주장은 **가능하면 2개 이상 독립 언론** 확인
- **동일 보도자료 재인용은 교차 확인이 아니다** (독립 출처 1개로 합산)
- 사설·칼럼·인터뷰는 "필자/화자의 입장"임을 명시

---

## Tier 4 — 비공식·개인

### 해당
- 개인 블로그, Medium, 브런치
- SNS (X/트위터, 페이스북, 링크드인, 스레드)
- 커뮤니티 (Reddit, 네이버카페, 디시인사이드 등)
- 개인 유튜브 채널, 뉴스레터
- 익명·출처 불명 자료
- 위키백과 (출처 추적의 시작점일 뿐, 그 자체로 근거 불가)

### 규칙
- **단독 근거 절대 불가**
- 유용해 보이면 **원출처를 추적**한다: 블로그가 인용한 원 논문·공식 발표를 찾아 확인되면 **그 원출처의 Tier로 승격**해 원출처를 인용한다 (블로그 자체를 인용하지 않는다)
- 전문가 개인 SNS(예: 저명 연구자의 자기 논문 소개)는 원문(논문·보고서)으로 승격해 인용

---

## 공통 판정 규칙

1. **목록에 없는 도메인**: 성격을 판단해 보수적으로(낮은 Tier로) 분류하고, 보고서에 "판정 근거"를 남긴다.
2. **기관 사칭·유사 도메인 주의**: 공식 도메인 여부를 확인한다 (예: 기관명.org 가 공식인지).
3. **애그리게이터**(포털 뉴스, 큐레이션 서비스)는 원 기사·원 발표로 거슬러 올라가 그 원출처 기준으로 판정한다.
4. **날짜 확인**: 오래된 자료가 최신 사실처럼 인용되지 않았는지 발행일을 함께 기록한다.

---

## 커스터마이즈 지침

자기 분야에 맞게 이 파일을 보강하라:

- **Tier 1**: 소관 부처·규제기관·공식 통계 생산기관 추가 (예: 보건 분야 → 질병관리청, 식약처, WHO)
- **Tier 2**: 분야 국책연·대표 학술지·주요 싱크탱크 추가
- **Tier 3**: 분야 전문지 추가 (예: 의학신문, 환경일보 등)
- 목록은 "예시"이지 완결이 아니다 — 판정의 원칙(공식성·심사 여부·독립성)이 우선한다.
