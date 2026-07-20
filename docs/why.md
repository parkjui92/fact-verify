# 왜 만들었나 · 상세 사용법

**한국어** · [English](#english)

README에서 덜어낸 배경과 상세 사용법을 여기 둡니다.

---

## 왜 만들었나

AI에게 리서치를 맡겨 본 사람은 대개 같은 경험을 합니다. **결과물은 매끄럽습니다.** 문장이 좋고, 구성도 그럴듯하고, 말미에는 실제로 열리는 URL이 열 개쯤 달려 있습니다. 그래서 이미 검증을 거친 문서처럼 보입니다.

문제는 그다음입니다. 그 URL을 하나씩 실제로 열어보면 이런 것들이 나옵니다.

- **지표 혼동** — "AI 서비스 경험률 67.8%". 67.8%라는 숫자 자체는 실재합니다. 다만 전혀 다른 지표(65세 이상 디지털정보화 수준, 2023)의 값입니다. 없는 숫자를 지어낸 것이 아니라 **있는 숫자를 엉뚱한 지표에 붙인 것**이라, 오히려 검산이 어렵습니다.
- **문서 귀속 오류** — 근거로 달린 연구보고서를 237쪽 전문까지 파싱해도 그 수치는 없습니다. 실제 출처는 다른 기관의 다른 조사였습니다.
- 그리고 두 오류 모두 **확정 어조**로 서술돼 있었습니다. 말미에는 진짜 URL 10개가 달려 있어, 읽는 사람 입장에서는 **문서 전체가 검증된 것처럼** 보였습니다.

> 위 두 사례는 자매 저장소 policy-research-kit이 순정 Claude Code 산출물을 대상으로 수행한 실측 감사 기록에서 인용했습니다. 제3의 중립 세션이 양쪽 산출물의 인용 URL 14건을 전수 열람해 원문과 대조한, 단일 주제·단일 실행 기록입니다 — 통계적 주장이 아니라 재현 가능한 사례로 읽어 주십시오. 전문: [policy-research-kit/docs/vanilla-vs-kit.md](https://github.com/parkjui92/policy-research-kit/blob/main/docs/vanilla-vs-kit.md)

이것은 모델이 부족해서 생기는 문제가 아닙니다. **인용을 10건 달면서 원문은 0회 열어보는 공정**이 만드는 문제입니다. 검색 결과 요약만으로 인용이 완성되기 때문에, 틀려도 틀린 자리에 아무 표시가 남지 않습니다. 그리고 리서치 산출물에서 이건 유난히 비쌉니다 — 브리핑에 실린 수치는 다시 인용되고, 보고서 근거가 되고, 몇 달 뒤 "이 숫자 어디서 나왔냐"는 질문으로 돌아옵니다.

그래서 필요했던 것은 더 나은 요약이 아니라 **믿기 전에 한 번 걸러내는 칸**이었습니다.

이 스킬은 원래 **R&D 동향 조사 에이전트 팀**(2026-04 구축)의 내장 검증자(`fact-verifier`)였습니다. 조사 에이전트가 모아 온 주간 브리핑 재료를 집필자에게 넘기기 전에 걸러내는 관문으로 실전에서 돌리던 것을, 어느 리서치 파이프라인에나 붙일 수 있도록 일반화해 독립 스킬로 승격한 것이 이 저장소입니다. 그래서 이 스킬은 "문서를 잘 읽어주는 도구"가 아니라 **공정의 한 칸**으로 설계돼 있습니다 — 통과 여부를 판정하고, 통과하지 못한 항목에 대해서는 조사 담당에게 그대로 넘길 수 있는 **재조사 요청서**를 함께 냅니다.

---

## 실패 유형 → 대응 장치 (전체)

실전에서 마주친 실패는 종류가 달랐고, 종류마다 다른 장치를 요구했습니다. 3단 프로토콜은 그렇게 하나씩 붙여 만든 것입니다.

| 실전에서 마주친 실패 | 대응 장치 |
|---|---|
| 존재하지 않는 arXiv ID·DOI를 단 인용 (할루시네이션) | **Step 3 실존 확인** — 식별자를 실제로 resolve |
| URL은 열리는데 그 페이지에 없는 내용의 인용 (출처-주장 불일치) | **Step 3 실존 확인** — 페이지를 fetch해 주장과 대조 |
| 언론 3곳 보도처럼 보이지만 전부 같은 보도자료 (**가짜 교차검증**) | **Step 2 재인용 체인 감지** — 독립 출처 수를 다시 셈 |
| 블로그 글이 정부 통계처럼 인용되는 신뢰도 세탁 | **Step 1 4-Tier 분류** — Tier 4 단독 근거 불가, 원출처로 승격 |
| 국문 논문·국책연 보고서를 국제 DB로 확인 못 해 "출처 불명" 처리 | **Step 3-D 한국 검증원** (v1.1) — KCI·RISS·국회도서관·NKIS |

마지막 줄이 한국에서 일할 때만 생기는 문제입니다. **국문 학술지 논문·국책연구원 보고서·정부 간행물은 DOI가 없는 경우가 많아 CrossRef·arXiv·Semantic Scholar 같은 국제 DB에 거의 잡히지 않습니다.** 그래서 국제 검증 도구는 멀쩡히 실재하는 「한국정책학회보」 논문이나 KISTEP 이슈페이퍼를 "확인 불가"로 되돌리고, 그대로 검증을 돌리면 **진짜 출처가 환각으로 오판**됩니다. 실제 문헌을 지우는 오판은 가짜를 통과시키는 것만큼 나쁩니다. v1.1에서 KCI·RISS·국회도서관·NKIS·PRISM을 별도 검증원으로 붙인 이유입니다.

---

## 3단 프로토콜 상세

**설계 전제는 회의론자 자세입니다.** 기본 상태는 의심이고, 증거가 있어야 통과합니다. "AI가 작성했을 가능성"을 상수로 가정하고, 그럴듯한 주장일수록 더 엄격히 봅니다. 불확실하면 포함하지 않는 쪽을 택합니다.

**Step 1 — 출처 Tier 분류.** 모든 출처를 네 단계로 나눕니다. **Tier 1** 정부·기관 공식(`.go.kr`·`.gov`·`europa.eu` 등) · **Tier 2** 학술·국책연구(peer-reviewed 학술지, KCI 등재지, KISTEP·STEPI 등) · **Tier 3** 주요 언론 · **Tier 4** 블로그·SNS·커뮤니티·익명. Tier 1·2는 단독 근거가 되지만 **Tier 4는 단독 근거가 절대 불가**하며, 유용해 보이면 그 글이 인용한 원 논문·공식 발표를 찾아 **원출처의 Tier로 승격**해 인용합니다. 목록에 없는 도메인은 보수적으로(낮은 쪽으로) 분류하고 판정 근거를 남깁니다.

**Step 2 — 교차 일관성.** 이 스킬의 핵심 기능인 **재인용 체인 감지**가 여기서 돕니다.

```
❌ 가짜 교차 검증
   주장 X가 매경·한경·서울경제 3곳에서 보도됨
   → 세 기사 모두 "과기부 보도자료"를 받아쓴 것이면 실은 출처 1개입니다.

✅ 진짜 교차 검증
   주장 X가 ① 정부 공식 발표 ② 독립 취재 기사 ③ 학술지 논평에서
   일관되게 나타남 → 독립 출처 3개.
```

각 기사에서 "○○가 밝혔다/발표했다/보도자료에 따르면" 같은 **공통 원천 표지**를 찾아 인용 체인을 거슬러 올라가고, 재인용은 1개로 합산해 독립 출처 수를 다시 셉니다. 여러 출처가 같은 수치를 다르게 보고하면 원출처를 확인해 판정하거나 보류합니다.

**Step 3 — 실존 확인.** URL을 실제로 fetch하고(404면 할루시네이션 의심, 200이지만 그 페이지에 주장 내용이 없으면 출처-주장 불일치), DOI는 `doi.org` 리다이렉트로 메타데이터를 대조하고, arXiv ID는 `arxiv.org/abs/`에서 실존·제목을 확인합니다. NTIS 과제번호(10자리)·ISBN은 형식과 서지를 검사합니다. 발표일이 원문 날짜와 맞는지, 인용 수치가 **단위·기준연도까지 포함해** 원문과 일치하는지도 여기서 봅니다.

**Step 3-D — 한국 학술·정책 검증 (v1.1).** 국문 문헌은 위 국제 경로로 확인되지 않는 것이 정상이므로 별도 검증원을 씁니다.

| 출처 유형 | 검증원 |
|---|---|
| 국내 학술지 논문(KCI 등재) | **KCI** (한국연구재단) — 학술지·논문·인용 정보 |
| 대학 학위논문·학술자원 | **RISS** (KERIS) |
| 단행본·논문·의안 등 폭넓은 서지 | **국회도서관** 국가학술정보 |
| 국책연구원 보고서 | **NKIS** (국가정책연구포털) · 기관 사이트 |
| 정부 정책연구용역 | **PRISM** (정책연구관리시스템) |
| 단행본·보고서 ISBN | 국립중앙도서관 서지정보 |

저자·제목·연도·게재지로 조회한 뒤 서지정보를 인용과 대조해 **연도·권호 오기와 학회지명 오기**까지 짚습니다. 국내외 어디에서도 확인되지 않을 때에만 환각 의심으로 판정합니다. 자세한 목록과 접근 방법은 [references/korea-sources.md](../references/korea-sources.md)에 있습니다.

### (선택) 한국 학술 API 정밀 검증 켜기

키 없이도 각 포털의 **공개 검색으로 동작합니다.** [공공데이터포털](https://www.data.go.kr) 인증키(무료, 대부분 자동승인)를 설정하면 KCI·RISS·국회도서관 API 경로로 자동 승급해 **대량·정밀** 검증이 됩니다.

```bash
# ~/.zshrc 등
export DATA_GO_KR_KEY="발급받은_Decoding_인증키"
```

키는 요구사항이 아니라 성능 옵션입니다. 없으면 공개 검색 범위 안에서 확인하고 못 미친 부분은 ⚠️로 정직하게 남깁니다 — **없는 능력을 있는 척하지 않습니다.** 데이터셋 목록·발급 절차는 [references/korea-sources.md](../references/korea-sources.md)를 참조하십시오.

---

## 상세 사용법

입력은 두 형태를 받습니다. **구조화 입력**(`주장 — 출처` 쌍 목록, 다른 에이전트·스킬의 조사 산출물)과 **자유 텍스트**(브리핑·보고서 초안·기사 초고)입니다. 자유 텍스트일 때는 먼저 본문에서 "사실 주장 + 붙어 있는 출처"를 추출해 검증 대상 목록을 만드는데, 이 과정에서 **출처가 아예 없는 사실 주장**은 그 자체로 🚫 `NO_SOURCE` 플래그가 붙습니다. 문서에 URL이 몇 개 달렸는지가 아니라 **어느 문장이 무엇에 근거하는지**를 보기 때문입니다.

### 시나리오 1 — 브리핑을 발행하기 전에 (standard)

```
이번 주 동향 브리핑 초안이야. 실으려는 근거들 출처 검증해줘.
```

가장 흔한 사용법이자 기본값입니다. 주장–출처 쌍을 뽑아 Tier로 분류하고, URL을 실제로 열고, DOI·arXiv를 resolve하고, 국문 문헌은 KCI·NKIS로 조회합니다. 결과는 항목별 판정표와 재조사 요청으로 돌아옵니다.

### 시나리오 2 — 참고문헌이 실재하는 문헌인지 (국문 포함)

```
이 원고 참고문헌이 실제로 존재하는 문헌인지 확인해줘. 국문 논문이 많아.
```

AI가 관여한 원고에서 가장 위험한 지점입니다. 국제 DB에서 "확인 불가"가 뜬 국문 문헌을 **곧바로 환각으로 처리하지 않는 것**이 이 스킬의 요점입니다. 실존이 확인되면 거기서 멈추지 않고 게재지명·권호·연도를 인용과 대조하므로, "논문은 진짜인데 인용 권호가 틀린" 항목까지 잡힙니다. 이런 항목은 본문을 뺄 일이 아니라 참고문헌만 고치면 됩니다.

### 시나리오 3 — 대외로 나가는 문서 (deep)

```
이 보고서 대외 배포용이야. deep으로 검증해줘.
```

standard에 더해 **핵심 주장에는 독립 출처 2개**를 요구하고, 인용 수치·날짜를 원문과 한 건씩 대조합니다. 재인용 체인 감지가 본격적으로 도는 것도 이 깊이입니다 — "언론 3곳 보도"가 실은 독립 출처 1개였다는 판정이 여기서 나옵니다. 투고 원고, 기사, 대외 보고서처럼 나간 뒤 회수가 안 되는 문서에 씁니다.

### 시나리오 4 — 네트워크가 없거나, 아직 초안일 때 (quick)

```
지금 오프라인이야. 일단 Tier 분류랑 식별자 형식만 훑어줘.
```

네트워크 없이 Tier 분류와 식별자 형식 검사만 수행합니다. arXiv ID가 `YYMM.NNNNN` 형식을 벗어났다거나, 핵심 주장이 전부 Tier 4에 걸려 있다거나 하는 문제는 이 단계에서 이미 드러납니다. 다만 quick은 **실존을 확인하지 않으므로** 발행 전에는 반드시 standard 이상으로 다시 돌리십시오.

### 검증 깊이 3단 — 언제 무엇을 쓰나

| 깊이 | 수행 범위 | 언제 |
|---|---|---|
| `quick` | Step 1(Tier 분류) + 식별자 **형식** 검사. 네트워크 불필요 | 초안 단계 빠른 점검, 오프라인 |
| `standard` **(기본)** | + Step 3 실존 확인(URL fetch, DOI·arXiv resolve, 한국 검증원 공개 검색) | 브리핑·내부 보고서 발행 전 |
| `deep` | + Step 2 교차 독립성(핵심 주장 독립 출처 2개), 수치·날짜 원문 대조 | 대외 보고서·기사·투고 |

깊이가 깊어질수록 외부 조회가 늘어 시간이 더 걸립니다. 초안 단계에서 `deep`을 도는 것은 대개 낭비이고, 대외 문서를 `quick`으로 넘기는 것은 대개 사고입니다. 요청에 깊이를 적지 않으면 `standard`로 동작합니다.

전체 보고서 형태는 [examples/verification-report-example.md](../examples/verification-report-example.md)에서 볼 수 있습니다(가상의 브리핑 초안 8개 항목을 검증한 예시입니다).

---

## 판정 4종을 받았을 때 — 어떻게 대응하나

판정은 사람의 판단을 돕는 **신호**이지 최종 결재가 아닙니다. 그래서 모든 판정에는 사유와 조치가 함께 붙습니다.

### ✅ VERIFIED — 통과. 단, Tier를 함께 읽으십시오

3단계를 통과했다는 뜻이지 "무조건 안전"이라는 뜻은 아닙니다. Tier 3(언론) 단독 근거라면 가능한 한 Tier 1·2 원출처로 올려 인용하는 편이 낫습니다. 또 VERIFIED에 **서지 오기 지적이 함께 붙는 경우**가 있습니다 — 문헌은 실재하지만 인용 권호·연도가 틀린 경우입니다. 본문을 뺄 일이 아니라 참고문헌만 고치면 되는 항목이니 놓치지 마십시오.

### ⚠️ NEEDS_REVIEW — "틀렸다"가 아니라 "확인하지 못했다"

가장 자주 나오고 가장 자주 오해받는 판정입니다. **원인에 따라 조치가 다릅니다.**

- **페이월·로그인 뒤 원문**(DBpia 유료 원문 등) → 접근 권한이 있는 사람이 직접 열어 확인하십시오. 확인 전까지는 문장에 강등 표기를 남기고 쓰거나, 빼십시오.
- **재인용 체인** → 원 보도자료·원 발표로 **교체 인용**하십시오. 같은 계통의 기사를 더 붙이는 것은 해결이 아닙니다.
- **수치 불일치** → 원출처를 열어 어느 쪽이 맞는지 판정하십시오.
- **제목 부분일치 후보만 확인됨** → 제시된 후보 중 맞는 것을 고르거나, 정확한 서지를 조사 담당에게 요청하십시오.

핵심은 ⚠️를 조용히 ✅로 바꾸지 않는 것입니다. **확인하지 못한 것은 확인하지 못했다고 문서에 남기는 편**이 훨씬 안전합니다.

### ❌ REJECT — 본문에서 빼십시오

URL 404, 식별자 실존 실패, 출처-주장 불일치, Tier 4 단독 근거가 여기 해당합니다. 주의할 것은 "다른 출처를 찾아 붙이면 된다"고 넘기지 않는 것입니다. **arXiv ID가 통째로 존재하지 않는다면 인용 형식이 틀린 게 아니라 그 주장 자체가 어디서 왔는지 의심해야 하는 상황**입니다. 재조사를 요청하고, 재조사 후에도 확인되지 않으면 확정 REJECT로 기록에 남깁니다.

### 🚫 NO_SOURCE — 출처를 붙이든지, 어조를 낮추든지, 빼든지

"업계 관계자에 따르면 규제 완화가 임박했다" 같은 문장입니다. 길은 셋입니다. ① 출처를 찾아 붙인다 ② 사실 서술에서 관측·추정 어조로 강등한다 ③ 문장을 뺀다. 확정 어조 그대로 두는 것만 아니면 됩니다 — 앞서 본 실패 사례에서 가장 위험했던 것도 오류 자체가 아니라 **오류가 확정 어조로 적혀 있었다**는 점이었습니다.

### 조사 담당에게 돌려주는 재조사 요청

검증만 하고 끝내면 다음 사람이 같은 자리에서 막힙니다. 그래서 판정표와 함께 **무엇이 왜 문제이고 무엇을 확인하면 되는지**를 항목별로 적은 재조사 요청을 냅니다. 사람 조사자에게도, 조사 에이전트에게도 그대로 넘길 수 있는 형식입니다.

```
#3: arXiv 2404.99999가 존재하지 않습니다. 실제 논문이라면 정확한 ID나
    DOI를 확인해 주세요. 확인 불가 시 제외합니다.
#7: KISTEP 이슈페이퍼는 국제 DB에 없는 것이 정상입니다. NKIS(nkis.re.kr)
    또는 KISTEP 발간자료에서 정확한 발간번호·제목을 확인해 주세요.
```

같은 항목이 재조사 후에도 확인되지 않으면 `REJECT`로 확정하고 기록을 남깁니다.

---

## 에이전트 파이프라인의 게이트로

이 스킬의 원래 자리입니다. `조사 → fact-verify → 집필` 순서로 배치하면 어떤 리서치 파이프라인에도 검증 게이트가 생깁니다. 게이트가 의미를 가지려면 **검증자가 조사·집필과 다른 에이전트**여야 합니다 — 자기가 모은 근거를 자기가 통과시키는 구조는 게이트가 아닙니다.

```markdown
---
name: fact-verifier
description: 조사 결과를 독립 검증하는 전문 에이전트. 조사 완료 후, 집필 시작 전에 호출.
tools: [WebFetch, WebSearch, Read, Write]
---
fact-verify 스킬의 3단 프로토콜을 따라 조사 산출물을 검증하고
verification_report를 반환한다. REJECT 항목은 집필에 사용 금지.
```

다른 에이전트가 결과를 프로그램적으로 소비해야 할 때는 마크다운 대신 **YAML**(`verification_report:` — 총계, `by_tier`, `rejected_items`[사유·조치], `review_needed`, `verified_items`)로 반환하도록 요청할 수 있습니다. 집필 에이전트가 `rejected_items`를 읽고 해당 근거를 배제하도록 배선하면 게이트가 자동으로 작동합니다. 상세는 [SKILL.md](../SKILL.md)를 참조하십시오.

---

## 커스터마이즈

기본 Tier 목록은 **과학기술정책(STI) 분야** 기준으로 작성돼 있습니다. [references/tier-rules.md](../references/tier-rules.md)에 자기 분야의 기관·학술지·전문지를 추가해 쓰십시오 — 예를 들어 보건 분야라면 Tier 1에 질병관리청·식약처·WHO를, Tier 2에 해당 분야 국책연·대표 학술지를, Tier 3에 분야 전문지를 보강하면 됩니다. 목록은 예시이지 완결이 아니며, 판정의 원칙(공식성·심사 여부·독립성)이 목록보다 우선합니다.

---
---

<a name="english"></a>

# Why I built this · Detailed usage

[한국어](#왜-만들었나--상세-사용법) · **English**

Background and detailed usage trimmed out of the README.

---

## Why I built this

Anyone who has handed research to an LLM has had the same experience. **The output is smooth.** The prose is good, the structure is plausible, and there are ten working URLs at the bottom. So it looks like a document that has already been checked.

The trouble starts when you open those URLs one by one:

- **Indicator confusion** — "AI service usage rate: 67.8%." The figure 67.8% is real. It just belongs to an entirely different indicator (digital literacy level among those aged 65+, 2023). This is not a fabricated number; it is a **real number attached to the wrong indicator**, which makes it *harder* to catch than an invented one.
- **Misattribution** — the research report cited as evidence does not contain the figure at all. The full 237-page PDF was parsed to confirm. The real source was a different survey by a different institution.
- And both errors were written in a **tone of certainty**. With ten genuine URLs listed at the end, the document read as though **the whole thing had been verified.**

> Both examples are quoted from a measured audit published by the sister repository policy-research-kit, run against vanilla Claude Code output. A neutral third-party session opened all 14 cited URLs from both sides and checked them against the primary sources. It is a single run on a single topic — read it as a reproducible case, not a statistical claim. Full record: [policy-research-kit/docs/vanilla-vs-kit.md](https://github.com/parkjui92/policy-research-kit/blob/main/docs/vanilla-vs-kit.md)

This is not a model-quality problem. It is what happens when a process **attaches 10 citations while opening zero source documents**. Citations get completed from search-result snippets, so when one is wrong, nothing marks the spot. And in research output that is unusually expensive: a figure published in a briefing gets re-cited, becomes the basis for a report, and comes back months later as "where did this number come from?"

So what was needed was not a better summary. It was **a step that filters before you believe**.

This skill began as the built-in verifier (`fact-verifier`) inside an **R&D trends research agent team** (built April 2026). It ran in production as the gate that screened the weekly briefing material an investigator agent had gathered, before any of it reached the writer. This repository is that gate, generalized so it can be dropped into any research pipeline. Which is why it is designed as **a step in a process**, not as a document reader: it issues a verdict, and for anything that does not pass, it produces a **re-investigation request** you can hand straight back to whoever did the research.

---

## Failure modes and devices — full table

The failures encountered in practice were of different kinds, and each kind demanded a different device. The three-step protocol was assembled one piece at a time.

| Failure seen in practice | Device |
|---|---|
| Citations with nonexistent arXiv IDs or DOIs (hallucination) | **Step 3 — existence check**: resolve the identifier for real |
| A URL that loads but does not contain the cited content (source–claim mismatch) | **Step 3 — existence check**: fetch the page and compare it to the claim |
| Three news outlets that look like corroboration but all ran the same press release (**fake cross-validation**) | **Step 2 — re-quotation chain detection**: recount independent sources |
| A blog post cited as though it were a government statistic (credibility laundering) | **Step 1 — 4-tier classification**: Tier 4 can never stand alone; trace to the original |
| Korean-language papers and institute reports marked "unverifiable" because international databases don't index them | **Step 3-D — Korean verification sources** (v1.1): KCI, RISS, National Assembly Library, NKIS |

### Why Korean sources need their own verifier

That last row is the problem you only hit when you work in Korea, and it is the reason this skill exists in the form it does.

Korean-language scholarship and policy literature largely lives outside the international citation infrastructure. **Korean journal articles, government-funded institute reports, and official publications frequently have no DOI at all**, and CrossRef, OpenAlex, Semantic Scholar, and arXiv index almost none of them. So a verification tool built on those databases will report a perfectly real article in *Korean Policy Studies Review* — a KCI-indexed journal — or a genuine KISTEP issue paper as "not found." Run verification in that state and **real sources get flagged as hallucinations.** Deleting a real citation is as damaging as letting a fake one through.

The fix is to query the Korean registries directly. For readers unfamiliar with them:

| Source | What it is |
|---|---|
| **KCI** (Korea Citation Index) | The national index of Korean scholarly journals, operated by the National Research Foundation of Korea. Coverage of accredited domestic journals and their citation data — roughly the Korean analogue of Web of Science for domestic publications |
| **RISS** | Research Information Sharing Service, operated by KERIS (the national education/research IT agency). University theses and dissertations, plus academic resources |
| **National Assembly Library** | Broad bibliographic coverage — books, articles, and legislative bills — from the library of Korea's legislature |
| **NKIS** | National Knowledge Information System, the portal aggregating reports from Korea's government-funded research institutes (KDI, KIEP, STEPI, KISTEP and peers). These reports carry real policy weight and are cited constantly, but they are not journal articles and carry no DOI |
| **PRISM** | The government's registry of commissioned policy research projects |
| **NTIS** | Korea's national R&D project database. Project numbers are 10 digits and are routinely cited in proposals and reports |
| **National Library of Korea** | ISBN and bibliographic records for books and monograph-form reports |

Two more names that appear below: **DBpia** is a major Korean academic database whose full texts sit behind a paywall, and **data.go.kr** is Korea's national open-data portal, which issues free API keys for several of the registries above.

---

## The three-step protocol in detail

**The design stance is skepticism.** The default state is doubt; something has to earn a pass. The skill assumes as a constant that an AI may have written the material, and scrutinizes plausible-sounding claims *more* rather than less. When in doubt, it excludes.

**Step 1 — Source tier classification.** Every source is sorted into four tiers. **Tier 1**, official government and institutional sources (`.go.kr`, `.gov`, `europa.eu`, and equivalents); **Tier 2**, scholarly and government-funded research (peer-reviewed journals, KCI-indexed Korean journals, institutes such as KISTEP and STEPI); **Tier 3**, major news media; **Tier 4**, blogs, social media, forums, anonymous material. Tiers 1 and 2 can stand as sole evidence. **Tier 4 never can** — if a Tier 4 item looks useful, the skill traces the paper or official announcement it cites and, on confirmation, **promotes the citation to that original source's tier** rather than citing the blog. Domains not on the list are classified conservatively (downward), with the reasoning recorded.

**Step 2 — Cross-consistency.** This is where the skill's signature feature, **re-quotation chain detection**, runs.

```
❌ Fake cross-validation
   Claim X is reported by three business dailies.
   → If all three ran the same ministry press release, that is one source.

✅ Real cross-validation
   Claim X appears consistently in ① an official government release,
   ② independently reported journalism, ③ a journal commentary
   → three independent sources.
```

The skill looks for shared-origin markers in each article — "according to a statement by," "the ministry announced," "per the press release" — walks the citation chain back, collapses re-quotations into a single count, and reports how many genuinely independent sources remain. Where sources report the same figure differently, it checks the original or holds the item.

**Step 3 — Existence check.** URLs are actually fetched: a 404 raises hallucination suspicion, and a page that loads but does not contain the claim is a source–claim mismatch. DOIs are resolved through `doi.org` and their metadata compared against the citation; arXiv IDs are checked at `arxiv.org/abs/` for existence and title. NTIS project numbers (10 digits) and ISBNs are checked for format and record. Publication dates are compared against the source, and cited figures are compared to the original **including units and base year**.

**Step 3-D — Korean scholarship and policy verification (v1.1).** Because Korean-language material is expected *not* to appear in the international path above, it gets its own route through KCI, RISS, the National Assembly Library, NKIS, PRISM, and the National Library of Korea (see the table above for what each covers).

The skill queries by author, title, year, and publication venue, then compares the returned bibliographic record against the citation — which catches **wrong year, wrong volume/issue, and wrong journal name** on sources that do exist. Only when an item cannot be found in *either* the Korean or the international registries is it treated as a suspected hallucination. Details and access notes are in [references/korea-sources.md](../references/korea-sources.md).

### Optional — enable precise Korean API verification

The skill **works with no key at all**, using each portal's public search. Setting a free [data.go.kr](https://www.data.go.kr) API key (most datasets are auto-approved) upgrades it automatically to the KCI / RISS / National Assembly Library REST APIs, which allow **bulk and field-level** verification.

```bash
# in ~/.zshrc or equivalent
export DATA_GO_KR_KEY="your_decoded_key"
```

The key is a performance option, not a requirement. Without it the skill verifies what public search can reach and honestly leaves the rest at ⚠️ — **it does not pretend to capabilities it does not have.** Dataset list and signup steps: [references/korea-sources.md](../references/korea-sources.md).

---

## Detailed usage

Two input shapes are accepted: **structured input** (a list of `claim — source` pairs, typically the output of another research agent or skill) and **free text** (a briefing, report draft, or article draft). With free text, the skill first extracts "factual claim + attached source" pairs to build the verification list — and in doing so, any **factual claim with no source at all** is flagged 🚫 `NO_SOURCE` on its own. The question is never how many URLs the document carries; it is **which sentence rests on what**.

### Scenario 1 — Before publishing a briefing (standard)

```
Here's this week's trends briefing draft. Verify the sources I'm about to publish.
```

The most common use, and the default. Claim–source pairs are extracted, tiered, URLs opened, DOIs and arXiv IDs resolved, Korean-language items checked against KCI and NKIS. You get back a per-item verdict table plus a re-investigation request.

### Scenario 2 — Do these references actually exist? (including Korean)

```
Check whether the references in this manuscript are real publications.
A lot of them are Korean-language.
```

The most dangerous spot in any AI-assisted manuscript. The point here is that a Korean-language work returning "not found" from an international database is **not** treated as a hallucination on that basis alone. And verification does not stop at existence: the journal name, volume/issue, and year in the record are compared against the citation, so items where "the paper is real but the volume number is wrong" surface too. Those don't need the passage removed — just the reference corrected.

### Scenario 3 — Documents that leave the building (deep)

```
This report is going out externally. Verify it at deep.
```

On top of standard, this requires **two independent sources for key claims** and compares each cited figure and date against the original. Re-quotation chain detection runs in earnest at this depth — this is where "reported by three outlets" comes back as one independent source. Use it for submissions, articles, and external reports: anything you cannot recall after it ships.

### Scenario 4 — No network, or still drafting (quick)

```
I'm offline. Just run the tier classification and identifier format checks.
```

Tier classification and identifier *format* checks only, no network needed. Problems like an arXiv ID that violates the `YYMM.NNNNN` pattern, or a document whose key claims all rest on Tier 4, are already visible at this stage. But quick **does not check existence**, so re-run at standard or deeper before publishing.

### Choosing a depth

| Depth | Scope | When |
|---|---|---|
| `quick` | Step 1 (tier classification) + identifier **format** check. No network required | Fast pass on an early draft; offline |
| `standard` **(default)** | + Step 3 existence check (URL fetch, DOI/arXiv resolve, Korean registries via public search) | Before publishing a briefing or internal report |
| `deep` | + Step 2 cross-independence (two independent sources for key claims), figure and date comparison against originals | External reports, articles, submissions |

Deeper settings mean more external lookups and more time. Running `deep` on an early draft is usually waste; pushing an external document out on `quick` is usually an incident. If you don't specify a depth, it runs `standard`.

A complete report is at [examples/verification-report-example.md](../examples/verification-report-example.md) (a worked example over eight items from a hypothetical briefing draft).

---

## What to do with each of the four verdicts

A verdict is a **signal to support your judgment**, not a sign-off. That is why every verdict carries a reason and an action.

### ✅ VERIFIED — passed, but read the tier with it

It means the item cleared all three steps, not that it is unconditionally safe. If a claim rests on a Tier 3 (news) source alone, prefer promoting the citation to the Tier 1 or 2 original where one exists. Also note that VERIFIED sometimes arrives **with a bibliographic correction attached** — the work is real, but the cited volume or year is wrong. That is not a reason to cut the passage; it is a reference-list fix. Don't skip past it.

### ⚠️ NEEDS_REVIEW — not "wrong," but "could not be confirmed"

The most frequent verdict and the most frequently misread. **The action depends on the cause:**

- **Paywalled or login-gated originals** (DBpia full texts and similar) → have someone with access open them. Until then, either carry the sentence with an explicit downgrade marker or drop it.
- **Re-quotation chain** → **replace the citation** with the original press release or announcement. Adding more articles from the same lineage is not a fix.
- **Figure mismatch** → open the original and determine which value is correct.
- **Only a partial title match found** → pick the right candidate from those offered, or ask the researcher for the exact bibliographic record.

The one thing that matters is not quietly promoting ⚠️ to ✅. **Recording that something could not be confirmed is far safer than implying it was.**

### ❌ REJECT — take it out of the document

This covers 404s, identifiers that don't resolve, source–claim mismatches, and Tier 4 standing alone. The trap is treating it as "just find another source." **If an arXiv ID does not exist at all, the citation format isn't what's broken — you should be asking where the claim itself came from.** Send it back for re-investigation, and if it still cannot be confirmed, record it as a confirmed REJECT.

### 🚫 NO_SOURCE — attach a source, soften the claim, or cut it

Sentences like "industry sources say deregulation is imminent." Three options: ① find and attach a source, ② downgrade it from assertion to observation or estimate, ③ remove it. Anything but leaving it standing in a tone of certainty — in the failure cases above, the most dangerous property was not the error itself but the fact that **the error was written as settled fact**.

### The re-investigation request

Verifying and stopping there just leaves the next person stuck in the same place. So alongside the verdict table, the skill writes a per-item request stating **what is wrong, why, and what would resolve it** — in a form you can hand to a human researcher or to an investigator agent unchanged.

```
#3: arXiv 2404.99999 does not exist. If this is a real paper, please confirm
    the correct ID or DOI. If it can't be confirmed, we drop it.
#7: A KISTEP issue paper is expected to be absent from international
    databases. Please confirm the exact publication number and title via
    NKIS (nkis.re.kr) or KISTEP's publications page.
```

If an item still cannot be confirmed after re-investigation, it is finalized as `REJECT` and recorded.

---

## As a gate in an agent pipeline

This is where the skill came from. Place it as `research → fact-verify → writing` and any research pipeline gains a verification gate. For the gate to mean anything, **the verifier must be a different agent from the researcher and the writer** — a structure where you clear your own evidence is not a gate.

```markdown
---
name: fact-verifier
description: Independent verifier for research output. Invoked after research completes, before writing begins.
tools: [WebFetch, WebSearch, Read, Write]
---
Follow the fact-verify three-step protocol, verify the research output,
and return a verification_report. REJECT items may not be used in writing.
```

When another agent needs to consume the result programmatically, ask for **YAML** instead of Markdown (`verification_report:` — totals, `by_tier`, `rejected_items` with reason and action, `review_needed`, `verified_items`). Wire the writing agent to read `rejected_items` and exclude that evidence, and the gate enforces itself. Details in [SKILL.md](../SKILL.md).

---

## Customizing

The default tier lists are written for **science and technology policy (STI)**. Add your own field's agencies, journals, and trade press to [references/tier-rules.md](../references/tier-rules.md) — for public health, for example, add the disease control agency, the drug regulator and WHO to Tier 1; your field's national institutes and flagship journals to Tier 2; its trade press to Tier 3. The lists are examples, not a closed set: the classification principles (official standing, peer review, independence) take precedence over the list.
