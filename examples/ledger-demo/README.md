# 원장 예제 — 가상 주간 동향 브리핑

모든 기관·주소·수치는 가상입니다(`example.go.kr` 등). 네트워크 없이 따라 할 수 있습니다.

```bash
cd examples/ledger-demo
python3 ../../scripts/fv.py extract draft.md          # draft.fv.json (주장 8건 · 검증 항목 11개)
python3 fill_demo.py                                   # 검증자가 원장을 채우는 과정을 재현
python3 ../../scripts/fv.py check draft.fv.json --final
python3 ../../scripts/fv.py report draft.fv.json -o 검증보고서.md
python3 ../../scripts/fv.py diff draft.fv.json draft_v2.md -o draft_v2.fv.json
```

| 주장 | 판정 | 무엇을 보여 주나 |
|---|---|---|
| C001 예산 1조 2,000억 원 | ✅ | 원문 발췌가 저장된 원문(`fv_sources/S01.txt`)에 실제로 있어야 통과 |
| C002 나머지 9,000억 원이 기술개발에 | ⚠️ | 원문에 없는 역산치(⑧) — 산식을 적고, 원문은 '인프라와 기술개발'이라 범위도 다름 |
| C003 AI 기업 2,500개 | ❌ | 확보한 원문이 1,250개라고 반박 — REJECT는 이럴 때만 |
| C004 연구소장의 직접인용 | ⚠️ | 원래 링크 404 → 대체 원문(`alt_for`)에서 취지는 같으나 문구가 다름(⑥) |
| C005 투자 40% 증가 | ⚠️ | 기사 두 곳이 같은 협회 보도자료를 받아씀(`chain`) — 독립 출처 1개 |
| C006 제12조·시행일 | ⚠️ | 법령 사이트가 자동 접속을 막음(403) — 틀렸다는 뜻이 아님 |
| C007 특허 출원 1.4배 | ✅ | 서지 확인(METADATA_ONLY)만으로는 부족 — 초록 본문으로 확인 |
| C008 규제 3건 완화 | 🚫 | 출처 없음 |

`draft_v2.md`는 C002·C003을 고친 판입니다. `diff`는 이 두 문장만 다시 검증 대상으로 돌리고, 고치지 않은 C008을 알려 줍니다.
