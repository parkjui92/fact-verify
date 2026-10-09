"""가상 예제: 검증자가 원장을 채우는 과정을 재현한다.
실제 검증에서는 이 부분을 검증자(사람·AI)가 원문을 읽고 직접 채운다.
    python3 fill_demo.py && python3 ../../scripts/fv.py check draft.fv.json --final
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(HERE, "fv_sources"), exist_ok=True)

TEXTS = {
    "S01": "# https://www.example.go.kr/press/2026-ai-chip (가상)\n\n"
           "정부는 2026년도 AI 반도체 예산을 1조 2,000억 원으로 확정했다. "
           "이 가운데 3,000억 원은 인력 양성에 배정하고, 나머지는 인프라 구축과 기술개발에 나누어 투입한다. "
           "현재 국내 AI 기업은 1,250개로 집계된다.\n",
    "S07": "# https://www.example.re.kr/press/2026-0312 (가상 — 기관 보도자료, S02의 대체 원문)\n\n"
           "연구소장은 \"실패 여부는 사전에 정한 중단 기준에 따라 판단한다\"고 밝혔다.\n",
    "S03": "# https://news-a.example.com/2026/invest (가상)\n\n"
           "협회가 발표한 자료에 따르면 업계 투자는 전년 대비 40% 늘었다.\n",
    "S04": "# https://news-b.example.com/2026/invest (가상)\n\n"
           "협회 발표에 따르면 올해 업계 투자는 전년 대비 40% 증가했다.\n",
    "S08": "# 김민수(2021) 초록 — KCI 원문 보기에서 옮김 (가상)\n\n"
           "분석 결과 클러스터 참여 기업의 특허 출원이 비참여 기업보다 1.4배 많았다.\n",
}
for sid, t in TEXTS.items():
    with open(os.path.join(HERE, "fv_sources", sid + ".txt"), "w", encoding="utf-8") as f:
        f.write(t)

p = os.path.join(HERE, "draft.fv.json")
with open(p, encoding="utf-8") as f:
    led = json.load(f)
S = led["sources"]


def src(sid, **kw):
    S[sid].update(kw)


src("S01", tier=1, access_status="FULL_TEXT", http_status=200, text_file="fv_sources/S01.txt")
src("S02", tier=2, access_status="NOT_FOUND", http_status=404,
    note="HTTP 404 — 기사 주소가 옮겨짐")
S["S07"] = {"kind": "url", "ref": "https://www.example.re.kr/press/2026-0312", "tier": 2, "chain": None,
            "access_status": "FULL_TEXT", "http_status": 200, "final_url": None, "title": "기관 보도자료",
            "text_file": "fv_sources/S07.txt", "text_chars": None, "meta": {}, "note": "S02의 대체 원문",
            "format_issue": None, "alt_for": "S02"}
src("S03", tier=3, chain="협회 보도자료 2026-03", access_status="FULL_TEXT", text_file="fv_sources/S03.txt")
src("S04", tier=3, chain="협회 보도자료 2026-03", access_status="FULL_TEXT", text_file="fv_sources/S04.txt")
src("S05", tier=1, access_status="BLOCKED", http_status=403, note="HTTP 403 — 자동 접속 차단")
src("S06", tier=2, access_status="METADATA_ONLY", note="KCI 서지 확인 — 30(3), 2021")
S["S08"] = {"kind": "note", "ref": "김민수(2021) 초록", "tier": 2, "chain": None, "access_status": "FULL_TEXT",
            "http_status": None, "final_url": None, "title": None, "text_file": "fv_sources/S08.txt",
            "text_chars": None, "meta": {}, "note": "S06의 본문(초록)", "format_issue": None, "alt_for": "S06"}

C = {c["id"]: c for c in led["claims"]}


def chk(atom, sid, ev, excerpt="", locator="", origin="literal", **kw):
    d = {"atom": atom, "source": sid, "evidence_status": ev, "origin": origin,
         "excerpt": excerpt, "locator": locator}
    d.update(kw)
    return d


def verdict(cid, v, checks, reason="", action=""):
    C[cid].update(verdict=v, checks=checks, reason=reason, action=action)


verdict("C001", "VERIFIED", [
    chk("C001.a1", "S01", "SUPPORTS", "2026년도 AI 반도체 예산", "보도자료 1문단"),
    chk("C001.a2", "S01", "SUPPORTS", "1조 2,000억 원으로 확정", "보도자료 1문단")])
verdict("C002", "NEEDS_REVIEW", [
    chk("C002.a1", "S01", "SUPPORTS", "3,000억 원은 인력 양성에 배정", "보도자료 2문장"),
    chk("C002.a2", "S01", "INSUFFICIENT", "나머지는 인프라 구축과 기술개발에 나누어 투입", "보도자료 2문장",
        origin="derived", formula="1조 2,000억 − 3,000억")],
    "9,000억 원은 원문에 없는 역산치이고, 원문은 나머지를 인프라와 기술개발에 나눈다고만 함(⑧·①)",
    "'나머지 9,000억 원은 인프라 구축과 기술개발에 투입'으로 고치거나 수치 삭제")
verdict("C003", "REJECT", [
    chk("C003.a1", "S01", "CONTRADICTS", "현재 국내 AI 기업은 1,250개로 집계된다", "보도자료 3문장")],
    "원문은 1,250개 — 본문 2,500개와 다름", "1,250개로 정정")
verdict("C004", "NEEDS_REVIEW", [
    chk("C004.a1", "S07", "INSUFFICIENT", "실패 여부는 사전에 정한 중단 기준에 따라 판단한다", "기관 보도자료",
        origin="paraphrase")],
    "원래 기사 링크는 404. 대체 원문(기관 보도자료)에서 취지는 같으나 문구가 다름(⑥)",
    "따옴표를 벗겨 간접 인용으로 바꾸고 출처를 기관 보도자료로 교체")
verdict("C005", "NEEDS_REVIEW", [
    chk("C005.a1", "S03", "SUPPORTS", "업계 투자는 전년 대비 40% 늘었다", "기사 1문단"),
    chk("C005.a1", "S04", "SUPPORTS", "전년 대비 40% 증가했다", "기사 1문단")],
    "두 기사 모두 같은 협회 보도자료를 받아씀 — 독립 출처 1개",
    "협회 보도자료 원문으로 출처를 교체")
verdict("C006", "NEEDS_REVIEW", [
    chk("C006.a1", "S05", "NOT_CHECKED"), chk("C006.a2", "S05", "NOT_CHECKED")],
    "법령 사이트가 자동 접속을 막음(403) — 틀렸다는 뜻이 아님",
    "국가법령정보센터 원문에서 조문 번호와 시행일을 직접 확인")
verdict("C007", "VERIFIED", [
    chk("C007.a1", "S08", "SUPPORTS", "특허 출원이 비참여 기업보다 1.4배 많았다", "초록")])
C["C007"]["sources"] = ["S06", "S08"]
verdict("C008", "NO_SOURCE", [], "출처 없는 전망", "출처를 찾지 못하면 문장 삭제")

with open(p, "w", encoding="utf-8") as f:
    json.dump(led, f, ensure_ascii=False, indent=1)
    f.write("\n")
print("원장을 채웠습니다: draft.fv.json")
