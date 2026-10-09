# 주장–근거 원장 (`scripts/fv.py`)

검증 판정은 원문을 읽은 검증자가 내린다. 원장은 그 판정이 규칙을 지켰는지를 **기계가** 확인하게 해 주는 기록이다. 검증자가 "원문 확인함"이라고 적는 것만으로는 통과하지 못한다. 저장된 원문에서 발췌문이 실제로 발견돼야 한다.

표준 라이브러리만 쓴다(Python 3.8+). 설치할 것이 없다.

## 흐름

```bash
python3 scripts/fv.py extract 원고.md            # 원고.fv.json 생성 (hwpx·docx·html·txt도 됨)
python3 scripts/fv.py probe 원고.fv.json          # 링크·DOI·arXiv 접속 상태 기록, 본문은 fv_sources/에 저장
#   … 검증자가 원장의 sources(tier·chain)와 claims(checks·verdict)를 채운다 …
python3 scripts/fv.py check 원고.fv.json --final  # exit 1 = [필수] 위반
python3 scripts/fv.py report 원고.fv.json -o 원고_검증보고서.md
python3 scripts/fv.py diff 원고.fv.json 원고_v2.md -o 원고_v2.fv.json   # 수정본: 바뀐 주장만 PENDING
python3 scripts/fv.py sample 원고.fv.json --rate 0.25 --seed 1          # R3 자기보고 표본
python3 scripts/fv.py selftest
```

| 단계 | 도구가 하는 것 | 검증자가 하는 것 |
|---|---|---|
| extract | 문장을 검증 단위로 쪼갬. 수치·날짜·연도·직접인용·「문서명」·조문을 **항목(atom)** 으로, 링크·DOI·arXiv·ISBN·(저자, 연도)·각주를 **출처**로 등록. 출처 없는 수치 문장, 참고문헌에 없는 인용, 본문에서 부르지 않는 문헌을 표시 | 숫자·인용이 없는 사실 주장("○○ 제도는 폐지됐다")은 기계가 고르지 못한다. 필요하면 `claims`에 직접 추가 |
| probe | 실제로 접속해 `access_status`만 기록. 본문은 `fv_sources/Sxx.txt`에 저장. **판정은 하지 않는다** | 접속 실패(BLOCKED·NOT_FOUND·EMPTY_BODY)면 대체 원문·색인을 찾고(R1), 찾은 출처를 `sources`에 추가하고 `alt_for`로 잇는다 |
| (판정) | — | 항목마다 원문을 읽고 `checks`를 채운 뒤 주장별 `verdict`를 정한다 |
| check | 판정이 아래 규칙을 지켰는지 점검 | [필수]를 0으로 만든다 |
| report | 건수를 **코드가 세어** 보고서 작성. [필수]가 남아 있으면 만들지 않음 | 정정 내역을 덧붙여 사용자에게 보고 |
| diff | 수정본과 문장 단위로 대조해 그대로인 주장은 판정을 이어받고, 바뀐 주장·새 주장만 PENDING | 바뀐 주장만 다시 검증 |

## 원장 필드

### sources (출처)

| 필드 | 뜻 |
|---|---|
| `kind` | url · doi · arxiv · isbn · bib(서지 문자열) · note(각주·출처 줄 문구) |
| `ref` | 원래 표기 |
| `tier` | 1~4 (references/tier-rules.md) — 검증자가 채움 |
| `chain` | 재인용 계통 이름. 같은 보도자료를 받아쓴 기사들은 같은 값 → 보고서가 독립 출처를 1개로 셈 |
| `access_status` | `NOT_CHECKED` · `FULL_TEXT` · `METADATA_ONLY` · `BLOCKED` · `NOT_FOUND` · `EMPTY_BODY` · `UNREACHABLE` |
| `text_file` | 저장된 원문(.txt면 발췌 대조에 쓰임, .pdf는 대조 불가 → 검증자가 읽은 쪽을 .txt로 저장하면 대조됨) |
| `alt_for` | 이 출처가 대신하는 원래 출처 번호(원래 링크의 NOT_FOUND는 그대로 남긴다) |
| `speaker_own` | 발언자 본인 계정·본인 발표. 발언 귀속 주장("○○가 '…'라고 썼다")에 한해 1차 원출처로 인정 |

`access_status`의 뜻:

| 값 | 뜻 | 흔한 원인 |
|---|---|---|
| FULL_TEXT | 본문을 확보함 | |
| METADATA_ONLY | 서지(DOI·arXiv 등록)만 확인, 본문은 아님 | |
| BLOCKED | 401·402·403·429·451·5xx, 봇 확인 화면 | 정부·학술 사이트의 자동조회 차단 |
| NOT_FOUND | 404·410, 등록되지 않은 DOI·arXiv | 주소 이동, 오타, 지어낸 식별자 |
| EMPTY_BODY | 200이지만 본문이 거의 없음 | 스크립트로 그리는 화면 |
| UNREACHABLE | 접속 자체 실패(시간 초과·SSL·DNS) | 일시 장애, 지어낸 도메인 |

**접속 상태는 판정이 아니다.** NOT_FOUND도 "그 주소에 문서가 없다"는 뜻일 뿐, 주장이 거짓이라는 뜻이 아니다. probe는 봇 차단을 우회하지 않는다. 자신을 `fact-verify`로 밝히고 접속하며, 막히면 막혔다고 기록한다.

### claims[].checks (항목별 대조)

| 필드 | 뜻 |
|---|---|
| `atom` | 대조한 항목 번호(C012.a2) |
| `source` | 근거로 쓴 출처 번호 |
| `evidence_status` | `SUPPORTS` · `CONTRADICTS` · `CITATION_MISMATCH` · `INSUFFICIENT` · `NOT_CHECKED` |
| `origin` | `literal`(원문에 글자 그대로) · `derived`(계산) · `converted`(단위·통화 환산) · `paraphrase`(취지만 같음) · `not_in_source` |
| `formula` | derived·converted일 때 산식 |
| `excerpt` | 원문 발췌(짧게, 원문 글자 그대로) |
| `locator` | 쪽·표·문단 위치 |
| `scope` | `content`(기본) · `bibliographic`(참고문헌 항목의 실재만 확인할 때 — METADATA_ONLY로 충분) |
| `scope_match` | 집계 범위·모수·기준연도가 본문과 같은가(false면 SUPPORTS도 CONTRADICTS도 불가 — ⑭) |
| `base_year` · `unit` | 기준연도·단위(선택) |

### claims[].verdict

`PENDING` · `VERIFIED` · `NEEDS_REVIEW` · `REJECT` · `NO_SOURCE` · `OUT_OF_SCOPE`(검증 대상 아님 — 강의 운영 시간, 자기 서술 등. 사유 필수)

## check가 막는 것 ([필수])

| 규칙 | 근거 |
|---|---|
| VERIFIED인데 대조하지 않은 항목이 있음 | R2 — 수치 N개 = 검증 항목 N개 |
| 본문을 확보하지 못한 출처(FULL_TEXT 아님)로 SUPPORTS | 판정 규칙 — 공식 사이트·HTTP 200만으로 통과 금지 |
| SUPPORTS에 발췌·위치가 없음, 또는 발췌가 저장된 원문에 없음 | 자기보고 비신뢰 |
| 직접인용이 발췌에 글자 그대로 없음 | ⑥ 직접인용 날조 |
| 계산·환산 수치에 산식 없음 | ⑧ 잔차 역산치 |
| 모수가 다르다고 적고 SUPPORTS·CONTRADICTS | ⑭ 범위 차이 |
| 접속 실패만으로 REJECT | 판정 규칙 — REJECT는 확보한 원문의 반박·인용 불일치가 있어야 함 |
| Tier 4만으로 VERIFIED (발언자 본인 채널의 발언 귀속은 예외) | Step 1 |
| NEEDS_REVIEW·REJECT·NO_SOURCE에 사유·다음 조치 없음 | 재조사 요청서 |
| 반박·근거 부족 기록이 있는데 VERIFIED | 판정 일관성 |

[권고]: 원문 그대로라던 숫자가 발췌에 없음, 계산 수치가 본문에서 원문 수치처럼 보임, 취지만 같은 인용에 따옴표, 식별자 형식 오류(arXiv 월 13, ISBN 체크숫자), 참고문헌에 없는 인용.

## 한계

- 항목 추출은 **놓치지 않는 쪽**으로 짜여 있다. 강의 시간·쪽 번호 같은 비(非)주장도 걸리므로 `OUT_OF_SCOPE`로 사유와 함께 뺀다.
- 숫자·인용·날짜·조문이 없는 사실 주장은 고르지 못한다.
- PDF 본문은 추출하지 않는다(`pdftotext`가 있어도 쓰지 않음). 검증자가 읽은 쪽을 .txt로 저장해야 발췌가 기계로 대조된다.
- 발췌 대조는 글자 일치만 본다. 발췌가 원문에 있어도 **그 발췌가 주장을 뒷받침하는지**는 검증자의 판단이다.
