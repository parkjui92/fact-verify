#!/usr/bin/env python3
"""fact-verify 주장–근거 원장(ledger) 도구.

판정은 사람(또는 검증 에이전트)이 원문을 읽고 내린다. 이 도구는 그 판정이
규칙을 지켰는지를 기계로 확인하는 부분만 맡는다.

  extract  원고를 검증 단위(주장·수치·인용·조문·출처)로 쪼개 원장 뼈대를 만든다
  probe    원장의 URL·DOI·arXiv에 실제로 접속해 접속 상태만 기록한다(판정은 안 함)
  check    채운 원장이 판정 규칙을 지켰는지 점검한다(exit 1 = [필수] 위반)
  report   원장에서 검증 보고서를 만든다(건수는 코드가 센다)
  diff     수정본과 대조해 바뀐 주장만 다시 검증 대상으로 돌린다
  sample   '검증완료' 자기보고 중 일부를 독립 재검증용으로 뽑는다
  selftest 내장 사례로 도구 자체를 점검한다

표준 라이브러리만 쓴다. Python 3.8+.
"""
import argparse
import datetime as _dt
import difflib
import hashlib
import html
import json
import os
import random
import re
import socket
import ssl
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from xml.etree import ElementTree as ET

VERSION = "1.3.0"
SCHEMA = "fact-verify/ledger@1"

VERDICTS = ("PENDING", "VERIFIED", "NEEDS_REVIEW", "REJECT", "NO_SOURCE", "OUT_OF_SCOPE")
ACCESS = ("NOT_CHECKED", "FULL_TEXT", "METADATA_ONLY", "BLOCKED", "NOT_FOUND",
          "EMPTY_BODY", "UNREACHABLE")
EVIDENCE = ("NOT_CHECKED", "SUPPORTS", "CONTRADICTS", "CITATION_MISMATCH",
            "INSUFFICIENT")
ORIGINS = ("literal", "derived", "converted", "paraphrase", "not_in_source")
ABS_EN = {"최초": r"first|earliest|pioneer", "최대": r"largest|biggest|most|maximum|top", "최고": r"highest|best|top|record",
          "최저": r"lowest|least|minimum", "유일": r"only|sole|unique", "전원": r"all|every|entire", "전무": r"none|no |zero",
          "처음": r"first"}
ICON = {"VERIFIED": "✅", "NEEDS_REVIEW": "⚠️", "REJECT": "❌", "NO_SOURCE": "🚫",
        "PENDING": "⏳", "OUT_OF_SCOPE": "·"}
UA = "fact-verify/%s (+https://github.com/parkjui92/fact-verify)" % VERSION


# ---------------------------------------------------------------- 공통

def norm(s):
    """발췌 대조용 정규화: 호환 문자·대소문자·공백·따옴표·대시 차이를 없앤다."""
    s = unicodedata.normalize("NFKC", s or "").lower()
    s = re.sub(r"[“”„‟\"″]", '"', s)
    s = re.sub(r"[‘’‚‛′`']", "'", s)
    s = re.sub(r"[‐‑‒–—―−]", "-", s)
    return re.sub(r"\s+", "", s)


def digits(s):
    return re.sub(r"[^\d.]", "", (s or "").replace(",", "")).strip(".")


def shash(s):
    return hashlib.sha1(norm(s).encode("utf-8")).hexdigest()[:12]


def now():
    return _dt.datetime.now().replace(microsecond=0).isoformat()


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def dump(obj, path):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)


# ---------------------------------------------------------------- 문서 읽기

def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _hwpx_text(zf):
    lines, notes = [], []
    names = sorted(n for n in zf.namelist()
                   if re.match(r"Contents/section\d+\.xml$", n))
    for name in names:
        root = ET.fromstring(zf.read(name))
        for p in root.iter():
            if _local(p.tag) != "p":
                continue
            # 문단 안에 다른 문단(표·각주)이 있으면 그 문단이 따로 처리된다
            buf = []
            for el in p.iter():
                lt = _local(el.tag)
                if lt == "t" and el.text:
                    buf.append(el.text)
                elif lt in ("footNote", "endNote"):
                    txt = "".join(t.text or "" for t in el.iter()
                                  if _local(t.tag) == "t")
                    notes.append(txt)
                    buf.append("[^h%d]" % len(notes))
            # 하위 문단의 글자가 상위 문단에 중복으로 잡히지 않게, 직계 run만 쓴다
            direct = []
            for run in p:
                if _local(run.tag) != "run":
                    continue
                for el in run:
                    lt = _local(el.tag)
                    if lt == "t":
                        direct.append("".join(el.itertext()))
                    elif lt == "ctrl":
                        for c in el:
                            if _local(c.tag) in ("footNote", "endNote"):
                                txt = "".join(t.text or "" for t in c.iter()
                                              if _local(t.tag) == "t")
                                if txt not in notes:
                                    notes.append(txt)
                                direct.append("[^h%d]" % (notes.index(txt) + 1))
            line = "".join(direct).strip()
            if line:
                lines.append(line)
    out = "\n".join(lines)
    if notes:
        out += "\n\n" + "\n".join("[^h%d]: %s" % (i + 1, n)
                                  for i, n in enumerate(notes))
    return out


def _docx_text(zf):
    W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    notes = {}
    if "word/footnotes.xml" in zf.namelist():
        froot = ET.fromstring(zf.read("word/footnotes.xml"))
        for fn in froot.iter(W + "footnote"):
            fid = fn.get(W + "id")
            txt = "".join(t.text or "" for t in fn.iter(W + "t")).strip()
            if txt:
                notes[fid] = txt
    root = ET.fromstring(zf.read("word/document.xml"))
    lines, used = [], []
    for p in root.iter(W + "p"):
        buf = []
        for el in p.iter():
            if el.tag == W + "t" and el.text:
                buf.append(el.text)
            elif el.tag == W + "footnoteReference":
                fid = el.get(W + "id")
                if fid in notes:
                    buf.append("[^d%s]" % fid)
                    used.append(fid)
        line = "".join(buf).strip()
        if line:
            lines.append(line)
    out = "\n".join(lines)
    if used:
        out += "\n\n" + "\n".join("[^d%s]: %s" % (f, notes[f]) for f in used)
    return out


def read_doc(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".hwpx", ".docx"):
        with zipfile.ZipFile(path) as zf:
            return _hwpx_text(zf) if ext == ".hwpx" else _docx_text(zf)
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    if ext in (".html", ".htm"):
        return html_to_text(text)[1]
    return text


# ---------------------------------------------------------------- 쪼개기

ABBR = r"(?:et al|U\.S|U\.K|e\.g|i\.e|vs|No|Vol|pp?|Fig|Dr|Mr|Ms|Inc|Ltd|Co|Jr|St|Art|ed|eds|cf)\."
PROTECT = [
    re.compile(r"\d{4}\.\s?\d{1,2}\.(?:\s?\d{1,2}\.)?"),   # 2026. 10. 9.
    re.compile(r"\b" + ABBR, re.I),
    re.compile(r"(?<!\w)(?:[A-Z]\.){2,}"),                    # U.S.A.
    re.compile(r"“[^”\n]*”|\"[^\"\n]*\""),                    # 따옴표 안의 마침표
]
MASK = "\ue000"
SPLIT = re.compile(r"(?<=[.?!。])\s+(?=\S)")

URL_RE = re.compile(r"https?://[^\s<>\"'「」『』\]\)）]+")
DOI_RE = re.compile(r"\b(10\.\d{4,9}/[^\s\"<>，,;)\]]+)")
ARXIV_RE = re.compile(r"(?:arxiv\.org/(?:abs|pdf)/|arXiv:\s?)(\d{4}\.\d{4,5})(v\d+)?", re.I)
ISBN_RE = re.compile(r"ISBN(?:-1[03])?[:\s]*([\dXx][\d\-\s]{8,16}[\dXx])")
FN_REF = re.compile(r"\[\^([\w-]+)\](?!:)")
FN_DEF = re.compile(r"^\s*\[\^([\w-]+)\]:\s*(.+)$")
AUTHOR_YEAR = re.compile(
    r"\(([^()\n]{1,80}?)[,，]?\s((?:19|20)\d{2}[a-z]?)(?:[:：,]\s?[^()\n]{0,20})?\)")
QUOTE_RE = re.compile(r"“([^”\n]{6,})”|\"([^\"\n]{6,})\"")
TITLE_RE = re.compile(r"「([^」\n]{2,80})」|『([^』\n]{2,80})』")
LAW_RE = re.compile(r"제\s?\d+\s?조(?:의\s?\d+)?(?:\s?제\s?\d+\s?항)?(?:\s?제\s?\d+\s?호)?"
                    r"|\bArt(?:icle)?\.?\s?\d+(?:\(\d+\))?", re.I)
DATE_RE = re.compile(
    r"(?<!\d)(?:\d{4}\.\s?\d{1,2}\.\s?\d{1,2}\.?|\d{4}-\d{2}-\d{2}"
    r"|\d{4}년\s?\d{1,2}월(?:\s?\d{1,2}일)?|\d{4}\.\s?\d{1,2}\.)")
YEAR_RE = re.compile(r"(?<![\d,.])(?:'\d{2}|(?:19|20)\d{2})(?:년도?)?"
                     r"(?:\s?[~∼\-–]\s?(?:'?\d{2}|(?:19|20)\d{2})(?:년도?)?)?(?![\d,])"
                     r"(?!\s?(?:명|건|개|원|억|만|천|%|배))")
UNIT = (r"%p|%|퍼센트|배|개국|개사|개소|개|명|건|원|달러|유로|엔|위안|파운드|USD|EUR|KRW|"
        r"bp|년|개월|주|일|시간|분|km|kg|톤|MW|GW|TWh|GB|TB|위|차|기|호|종|곳|회|편|권|쪽|"
        r"million|billion|trillion|bn")
_NB = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
_MAG = r"(?:천만|백만|천|만|억|조)"
NUM_RE = re.compile(
    r"(?<![\dA-Za-z.\-/])(?:(?:US)?[$€£¥₩]\s?)?" + _NB +
    r"(?:\s?" + _MAG + r"(?:\s?" + _NB + r"\s?" + _MAG + r")*)?"
    r"(?:\s?(?:" + UNIT + r"))?(?![\dA-Za-z])")
LIST_MARK = re.compile(r"^\s*(?:[-*+•·]|\d{1,2}[.)]|\(\d{1,2}\)|[①-⑳]|[가-하][.)]|[□○◦▪■●◆◇※])\s*")
ABSOLUTE_RE = re.compile(
    r"(?:세계|국내|국내외|아시아|업계|국내\s?최초로)?\s?(?:최초|최대|최고|최저|유일)|사상\s?최[고대저]|역대\s?최[고대저]"
    r"|처음으로|전원|전무")
ABSENCE_RE = re.compile(
    r"(?:연구|선행연구|사례|논의|자료|통계|측정\s?방법|방법론|기준|규정|법적\s?근거)(?:가|이|는|은)?\s?"
    r"(?:없|부재|전무|부족)|연구\s?공백|공백(?:으로|이)\s?남")
HEDGE_SRC = re.compile(
    r"\b(?:could|may|might|up to|as (?:much|many|high) as|approximately|about|around|nearly|some|partly|"
    r"partially|plans? to|planned|expected|estimated|projected|proposed|potentially|in some)\b"
    r"|약\s?\d|최대|일부|가능|예정|검토|계획|추진|전망|추정|잠정|부분적|수 있|안\(案\)|초안", re.I)
HEDGE_DRAFT = re.compile(r"약\s?\d|최대|일부|가능|예정|검토|계획|추진|전망|추정|잠정|부분|수 있|안\)|초안|~?까지|이상|이하|내외|정도")
VOLATILE_RE = re.compile(
    r"별(?:은|이|\s?수|\s?개수|\s?\d)|스타|stars?|포크|forks?|다운로드|이용자|사용자|가입자|구독자|팔로워|조회\s?수|게시물\s?수|"
    r"가격|요금|단가|토큰당|/\s?월|per month|버전|모델|파라미터|매개변수|컨텍스트 창|건수|등록\s?건|순위", re.I)
TRACE_RE = re.compile(r"원문\s?대조\s?전|확인\s?필요|검증\s?필요|추후\s?확인|\bTODO\b|\bTBD\b|\[보강 필요\]|\[미확보\]|"
                      r"○○|XX년|\?\?\?")
TIME_RE = re.compile(r"(?<!\d)\d{1,2}:\d{2}(?::\d{2})?(?:\s?[~∼\-–]\s?\d{1,2}:\d{2})?")
SRC_LINE = re.compile(r"^\s*(?:[-*]\s*)?(?:\*\*)?(?:출처|자료|Source|Sources)(?:\*\*)?\s*[:：]", re.I)
REF_HEAD = re.compile(r"^#{1,6}\s*(?:참고\s?문헌|참고자료|References?|Bibliography|출처)\s*$", re.I)


def _mask(s):
    for rx in PROTECT:
        s = rx.sub(lambda m: m.group(0).replace(".", MASK), s)
    return s


def sentences(text):
    return [p.replace(MASK, ".").strip() for p in SPLIT.split(_mask(text)) if p.strip()]


def _strip_cites(s):
    """수치를 찾기 전에 출처 표기(링크·서지·각주 번호)를 지운다."""
    s = URL_RE.sub(" ", s)
    s = DOI_RE.sub(" ", s)
    s = ARXIV_RE.sub(" ", s)
    s = ISBN_RE.sub(" ", s)
    s = AUTHOR_YEAR.sub(" ", s)
    s = FN_REF.sub(" ", s)
    s = re.sub(r"\[\d{1,3}\](?!\()", " ", s)
    s = re.sub(r"\]\([^)]*\)", "] ", s)               # 마크다운 링크 주소
    return s


def atoms_of(sentence):
    s = LIST_MARK.sub("", _strip_cites(sentence))
    s = TIME_RE.sub(lambda m: " " * len(m.group(0)), s)
    s = re.sub(r"\*\*|__|`", "", s)
    found, taken = [], []

    def take(kind, m, text=None):
        a, b = m.span()
        if any(a < y and b > x for x, y in taken):
            return
        taken.append((a, b))
        found.append((a, {"type": kind, "text": (text or m.group(0)).strip()}))

    for m in QUOTE_RE.finditer(s):
        take("quote", m, m.group(1) or m.group(2))
    for m in TITLE_RE.finditer(s):
        take("title", m, m.group(1) or m.group(2))
    for m in LAW_RE.finditer(s):
        take("law", m)
    for m in ABSENCE_RE.finditer(s):
        take("absence", m)
    for m in ABSOLUTE_RE.finditer(s):
        take("absolute", m)
    for m in DATE_RE.finditer(s):
        take("date", m)
    for m in YEAR_RE.finditer(s):
        take("year", m)
    for m in NUM_RE.finditer(s):
        t = m.group(0).strip()
        # 장·절·목록 번호, 모델명 속 숫자, 홀로 선 한 자리 수는 주장으로 세지 않는다
        if re.fullmatch(r"\d", t):
            continue
        a = m.start()
        if a > 0 and re.match(r"[A-Za-z가-힣\-]", s[a - 1]) and not re.match(r"[$€£¥₩]", t):
            if not re.match(r"[가-힣]", s[a - 1]):
                continue
        if re.match(r"\d+(\.\d+){2,}$", t) or s[m.end():m.end() + 1] in ("절", "장") \
                or re.match(r"\d+\s?(?:주차|번째|교시|학년|학기|회차)", s[m.start():]):
            continue                                  # 2.1.3 같은 번호, 3.2절
        take("number", m)
    found.sort(key=lambda x: x[0])
    return [a for _, a in found]


def cites_of(sentence):
    out = []
    for m in URL_RE.finditer(sentence):
        out.append(("url", m.group(0).rstrip(".,;:·")))
    for m in DOI_RE.finditer(sentence):
        if "doi.org/" + m.group(1) in sentence and any(
                k == "url" and m.group(1) in v for k, v in out):
            continue
        out.append(("doi", m.group(1).rstrip(".,;:")))
    for m in ARXIV_RE.finditer(sentence):
        out.append(("arxiv", m.group(1)))
    for m in ISBN_RE.finditer(sentence):
        out.append(("isbn", re.sub(r"[\s-]", "", m.group(1))))
    for m in AUTHOR_YEAR.finditer(sentence):
        who = m.group(1).strip()
        if re.search(r"\d{3,}|[=<>]", who) or len(who) < 2:
            continue
        out.append(("author_year", "%s, %s" % (who, m.group(2))))
    for m in FN_REF.finditer(sentence):
        out.append(("footnote", m.group(1)))
    for m in re.finditer(r"\[(\d{1,3})\](?!\()", sentence):
        out.append(("footnote", m.group(1)))
    return out


def format_issues(kind, value):
    """quick 깊이에서도 할 수 있는 식별자 형식 검사."""
    if kind == "doi" and not re.match(r"10\.\d{4,9}/\S+$", value):
        return "DOI 형식이 아님"
    if kind == "arxiv":
        yymm = value.split(".")[0]
        yy, mm = int(yymm[:2]), int(yymm[2:])
        if not 1 <= mm <= 12:
            return "arXiv 번호의 월(MM)이 01~12가 아님"
        if 2000 + yy > _dt.date.today().year:
            return "arXiv 번호의 연도가 미래"
        if yy >= 15 and len(value.split(".")[1]) != 5:
            return "2015년 이후 arXiv 번호는 소수점 뒤 5자리"
    if kind == "isbn":
        v = value.upper()
        if len(v) == 10 and re.fullmatch(r"\d{9}[\dX]", v):
            tot = sum((10 - i) * (10 if c == "X" else int(c)) for i, c in enumerate(v))
            return None if tot % 11 == 0 else "ISBN-10 체크숫자 불일치"
        if len(v) == 13 and v.isdigit():
            tot = sum((1 if i % 2 == 0 else 3) * int(c) for i, c in enumerate(v))
            return None if tot % 10 == 0 else "ISBN-13 체크숫자 불일치"
        return "ISBN 자릿수 오류"
    return None


def _first_author(who):
    who = re.sub(r"\s*(et al\.?|외|등|&.*|and .*)$", "", who.split(";")[0].split(",")[0]).strip()
    return who.split()[-1] if re.match(r"[A-Za-z]", who) and " " in who else who


def extract(text, path=None):
    lines = text.splitlines()
    fdefs, refs, units = {}, [], []
    in_code = in_refs = False
    header_next = False
    for i, raw in enumerate(lines, 1):
        line = raw.rstrip()
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code or not line.strip() or line.strip().startswith("<!--"):
            continue
        m = FN_DEF.match(line)
        if m:
            fdefs[m.group(1)] = (i, m.group(2).strip())
            continue
        if line.lstrip().startswith("#"):
            in_refs = bool(REF_HEAD.match(line.strip()))
            units.append((i, "", "heading"))
            continue
        if in_refs:
            refs.append((i, LIST_MARK.sub("", line).strip()))
            continue
        if re.match(r"^\s*\|?\s*:?-{3,}", line):
            if units and units[-1][2] == "row":
                units.pop()                           # 바로 위 줄은 표 머리
            continue
        if line.lstrip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            units.append((i, " | ".join(c for c in cells if c), "row"))
            continue
        if line.lstrip().startswith(">"):
            line = line.lstrip("> ")
        if SRC_LINE.match(line):
            units.append((i, line.strip(), "source_line"))
            continue
        for s in sentences(line):
            units.append((i, s, "text"))

    ledger = {"schema": SCHEMA, "tool": "fv.py " + VERSION,
              "document": {"path": path, "sha256": hashlib.sha256(
                  text.encode("utf-8")).hexdigest(), "extracted_at": now()},
              "depth": "standard", "sources": {}, "claims": [],
              "orphans": {"cites_without_reference": [], "references_never_cited": []}}
    src_index = {}

    def add_source(kind, value):
        key = (kind, value)
        if key not in src_index:
            sid = "S%02d" % (len(src_index) + 1)
            src_index[key] = sid
            ledger["sources"][sid] = {
                "kind": kind, "ref": value, "tier": None, "chain": None,
                "access_status": "NOT_CHECKED", "http_status": None,
                "final_url": None, "title": None, "text_file": None,
                "text_chars": None, "meta": {}, "note": "",
                "format_issue": format_issues(kind, value), "alt_for": None}
        return src_index[key]

    ref_text = [r for _, r in refs]
    cited_refs = set()
    section_start = 0
    for line_no, s, kind in units:
        if kind == "heading":
            section_start = len(ledger["claims"])
            continue
        if kind == "source_line":
            got = [add_source(k, v) for k, v in cites_of(s) if k in ("url", "doi", "arxiv", "isbn")]
            if not got:
                got = [add_source("note", re.sub(r"^\s*[-*]?\s*\S+\s*[:：]\s*", "", s)[:200])]
            for c in ledger["claims"][section_start:]:
                if not c["sources"]:
                    c["sources"] = list(got)
                    c["no_source_candidate"] = False
                    c["source_line"] = line_no
            continue
        atoms = atoms_of(s)
        raw_cites = cites_of(s)
        if not atoms and not raw_cites:
            continue
        cites = []
        for k, v in raw_cites:
            if k == "footnote":
                if v in fdefs:
                    ftxt = fdefs[v][1]
                    sub = [c for c in cites_of(ftxt) if c[0] != "footnote"]
                    for k2, v2 in sub:
                        cites.append(add_source(k2, v2))
                    if not sub:
                        cites.append(add_source("note", ftxt))
                else:
                    cites.append(add_source("note", "각주 [%s] 본문 없음" % v))
            elif k == "author_year":
                who, yr = v.rsplit(", ", 1)
                fa = _first_author(who)
                hit = next((r for r in ref_text
                            if norm(fa) in norm(r) and yr[:4] in r), None)
                if hit:
                    cited_refs.add(hit)
                    sub = [c for c in cites_of(hit) if c[0] in ("url", "doi", "arxiv", "isbn")]
                    for k2, v2 in sub:
                        cites.append(add_source(k2, v2))
                    cites.append(add_source("bib", hit))
                else:
                    cites.append(add_source("bib", v))
                    if refs:
                        ledger["orphans"]["cites_without_reference"].append(
                            {"line": line_no, "cite": v})
            else:
                cites.append(add_source(k, v))
        cid = "C%03d" % (len(ledger["claims"]) + 1)
        has_when = any(a["type"] in ("date", "year") for a in atoms)
        needs_as_of = bool(VOLATILE_RE.search(s)) and any(a["type"] == "number" for a in atoms) and not has_when
        ledger["claims"].append({
            "id": cid, "line": line_no, "unit": kind, "sentence": s,
            "sentence_hash": shash(s),
            "atoms": [dict(a, id="%s.a%d" % (cid, j + 1)) for j, a in enumerate(atoms)],
            "sources": list(dict.fromkeys(cites)),
            "checks": [], "verdict": "PENDING", "reason": "", "action": "",
            "no_source_candidate": bool(atoms) and not cites, "needs_as_of": needs_as_of})
    ledger["traces"] = [{"line": i, "text": m.group(0)} for i, raw in enumerate(lines, 1)
                        for m in TRACE_RE.finditer(raw)]
    if refs:
        for r in ref_text:
            if r not in cited_refs and AUTHOR_YEAR.search("(" + r + ")") is None:
                pass
            if r not in cited_refs and re.search(r"(19|20)\d{2}", r):
                ledger["orphans"]["references_never_cited"].append(r[:160])
    return ledger


# ---------------------------------------------------------------- 접속

BLOCK_MARKS = ("just a moment", "attention required", "access denied", "captcha",
               "cf-browser-verification", "are you a robot", "request blocked",
               "unusual traffic", "bot detection", "pardon our interruption")
JS_MARKS = ("enable javascript", "requires javascript", "javascript is disabled",
            "you need to enable javascript", "자바스크립트를 활성화")


def html_to_text(raw):
    t = re.search(r"<title[^>]*>(.*?)</title>", raw, re.S | re.I)
    title = html.unescape(re.sub(r"\s+", " ", t.group(1))).strip() if t else None
    body = re.sub(r"(?is)<(script|style|noscript|svg|nav|header|footer|aside|form)\b.*?</\1>", " ", raw)
    body = re.sub(r"(?is)<!--.*?-->", " ", body)
    body = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|h\d)>", "\n", body)
    body = html.unescape(re.sub(r"<[^>]+>", " ", body))
    body = re.sub(r"[ \t\r\f\v]+", " ", body)
    body = re.sub(r"\n\s*\n+", "\n", body).strip()
    return title, body


def _ctx():
    try:
        import certifi  # noqa
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def fetch(url, timeout=15, accept=None, limit=6_000_000):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": accept or "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko,en;q=0.8"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r:
            data = r.read(limit)
            return {"status": r.status, "final_url": r.geturl(), "url": url,
                    "ctype": r.headers.get("Content-Type", ""), "data": data}
    except urllib.error.HTTPError as e:
        try:
            data = e.read(200_000)
        except Exception:
            data = b""
        return {"status": e.code, "final_url": url, "url": url,
                "ctype": e.headers.get("Content-Type", "") if e.headers else "", "data": data}
    except (urllib.error.URLError, socket.timeout, ssl.SSLError, ConnectionError, OSError) as e:
        reason = getattr(e, "reason", e)
        return {"status": None, "final_url": url, "ctype": "", "data": b"",
                "error": "%s: %s" % (type(reason).__name__, reason)}


def classify(resp, min_chars=300):
    """HTTP 응답 → (access_status, title, text, note). 판정(근거)은 하지 않는다."""
    st, data, ctype = resp.get("status"), resp.get("data") or b"", (resp.get("ctype") or "").lower()
    if st is None:
        return "UNREACHABLE", None, None, resp.get("error", "")
    if st in (404, 410):
        return "NOT_FOUND", None, None, "HTTP %d — 이 주소에는 문서가 없음(원문이 없다는 뜻은 아님)" % st
    if st in (401, 402, 403, 407, 429, 451, 999) or st >= 500:
        return "BLOCKED", None, None, "HTTP %d — 접속 차단·제한" % st
    req_path = urllib.parse.urlparse(resp.get("url") or "").path.strip("/")
    fin_path = urllib.parse.urlparse(resp.get("final_url") or "").path.strip("/")
    if req_path.count("/") >= 1 and fin_path in ("", "index.html", "index.do", "main", "main.do", "ko", "en", "kor"):
        return "NOT_FOUND", None, None, "HTTP %d이지만 첫 화면으로 이동 — 소프트 404 의심(문서가 옮겨졌을 수 있음)" % st
    if data[:5] == b"%PDF-" or "application/pdf" in ctype:
        return "FULL_TEXT", None, None, "PDF — 텍스트 미추출, 원문을 직접 읽어 대조"
    raw = data.decode("utf-8", errors="replace")
    title, text = html_to_text(raw) if "<" in raw[:2000] else (None, raw)
    low = (text or "").lower()[:4000] + " " + (title or "").lower()
    if any(k in low for k in BLOCK_MARKS) and len(text) < 3000:
        return "BLOCKED", title, None, "HTTP %d이지만 봇 확인 화면" % st
    if len(text) < min_chars or (any(k in low for k in JS_MARKS) and len(text) < 1500):
        return "EMPTY_BODY", title, text, "HTTP %d이지만 본문 %d자 — 스크립트로 그리는 화면일 수 있음" % (st, len(text))
    return "FULL_TEXT", title, text, "HTTP %d" % st


def wayback(url, timeout=15):
    """웨이백 머신의 가장 가까운 보관본 주소. 내용을 가져오지는 않는다(판본·시점은 검증자가 본다)."""
    r = fetch("https://archive.org/wayback/available?url=" + urllib.parse.quote(url, safe=""),
              timeout=timeout, accept="application/json")
    try:
        snap = json.loads(r["data"].decode("utf-8"))["archived_snapshots"]["closest"]
        if snap.get("available"):
            return {"url": snap["url"], "timestamp": snap.get("timestamp")}
    except Exception:
        pass
    return None


def probe_doi(doi, timeout=15):
    r = fetch("https://doi.org/api/handles/" + urllib.parse.quote(doi, safe="/"),
              timeout=timeout, accept="application/json")
    if r.get("status") is None:
        return "UNREACHABLE", {}, r.get("error", "")
    try:
        code = json.loads(r["data"].decode("utf-8")).get("responseCode")
    except Exception:
        code = None
    if r["status"] == 404 or code == 100:
        return "NOT_FOUND", {}, "doi.org에 등록되지 않은 DOI"
    meta = {}
    m = fetch("https://doi.org/" + urllib.parse.quote(doi, safe="/"), timeout=timeout,
              accept="application/vnd.citationstyles.csl+json")
    try:
        j = json.loads(m["data"].decode("utf-8"))
        meta = {"title": j.get("title"), "container": j.get("container-title"),
                "year": ((j.get("issued") or {}).get("date-parts") or [[None]])[0][0],
                "authors": [" ".join(x for x in (a.get("given"), a.get("family")) if x)
                            for a in (j.get("author") or [])][:6]}
    except Exception:
        pass
    return "METADATA_ONLY", meta, "DOI 등록 확인 — 본문은 아님"


def probe_arxiv(aid, timeout=15):
    r = fetch("https://export.arxiv.org/api/query?id_list=" + aid, timeout=timeout,
              accept="application/atom+xml")
    if r.get("status") is None:
        return "UNREACHABLE", {}, r.get("error", "")
    xml = r["data"].decode("utf-8", errors="replace")
    entries = re.findall(r"<entry>(.*?)</entry>", xml, re.S)
    if not entries or "<title>Error</title>" in entries[0]:
        return "NOT_FOUND", {}, "arXiv에 없는 번호"
    e = entries[0]
    title = re.search(r"<title>(.*?)</title>", e, re.S)
    year = re.search(r"<published>(\d{4})", e)
    names = re.findall(r"<name>(.*?)</name>", e)
    return "METADATA_ONLY", {"title": re.sub(r"\s+", " ", title.group(1)).strip() if title else None,
                             "year": int(year.group(1)) if year else None,
                             "authors": names[:6]}, "arXiv 등록 확인 — 본문은 아님"


def cmd_probe(a):
    led = load(a.ledger)
    save_dir = a.save_dir or os.path.join(os.path.dirname(os.path.abspath(a.ledger)), "fv_sources")
    os.makedirs(save_dir, exist_ok=True)
    todo = [(sid, s) for sid, s in led["sources"].items()
            if s["kind"] in ("url", "doi", "arxiv") and (a.force or s["access_status"] == "NOT_CHECKED")]
    if a.only:
        todo = [t for t in todo if t[0] in set(a.only.split(","))]
    counts = {}
    for sid, s in todo:
        if s["kind"] == "url":
            r = fetch(s["ref"], timeout=a.timeout)
            st, title, text, note = classify(r)
            s.update(http_status=r.get("status"), final_url=r.get("final_url"), title=title)
            if st == "FULL_TEXT":
                if text is None:
                    fn = os.path.join(save_dir, sid + ".pdf")
                    with open(fn, "wb") as f:
                        f.write(r["data"])
                    s.update(text_file=os.path.relpath(fn, os.path.dirname(os.path.abspath(a.ledger))),
                             text_chars=None)
                else:
                    fn = os.path.join(save_dir, sid + ".txt")
                    with open(fn, "w", encoding="utf-8") as f:
                        f.write("# %s\n# %s\n# fetched %s\n\n%s\n" % (s["ref"], title or "", now(), text))
                    s.update(text_file=os.path.relpath(fn, os.path.dirname(os.path.abspath(a.ledger))),
                             text_chars=len(text))
        elif s["kind"] == "doi":
            st, meta, note = probe_doi(s["ref"], a.timeout)
            s["meta"] = meta
            s["title"] = meta.get("title") if isinstance(meta.get("title"), str) else s["title"]
        else:
            st, meta, note = probe_arxiv(s["ref"], a.timeout)
            s["meta"] = meta
            s["title"] = meta.get("title")
        if s["kind"] == "url" and st in ("NOT_FOUND", "BLOCKED", "EMPTY_BODY") and not a.no_wayback:
            wb = wayback(s["ref"], a.timeout)
            if wb:
                s.setdefault("meta", {})["wayback"] = wb
                note += " · 보관본 %s (%s)" % (wb["url"], (wb.get("timestamp") or "")[:8])
        s.update(access_status=st, note=note, probed_at=now())
        counts[st] = counts.get(st, 0) + 1
        print("%s  %-13s %s  %s" % (sid, st, s["ref"][:70], note[:60]))
    dump(led, a.ledger)
    print("\n접속 확인 %d건: %s" % (len(todo), ", ".join("%s %d" % kv for kv in sorted(counts.items())) or "없음"))
    print("※ 접속 상태는 판정이 아닙니다. NOT_FOUND·BLOCKED·EMPTY_BODY는 대체 원문·색인을 찾은 뒤 판정하세요.")
    return 0


# ---------------------------------------------------------------- 점검

def _source_text(led, sid, base):
    s = led["sources"].get(sid) or {}
    fn = s.get("text_file")
    if not fn or fn.endswith(".pdf"):
        return None
    p = fn if os.path.isabs(fn) else os.path.join(base, fn)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8", errors="replace") as f:
        return f.read()


def check_ledger(led, base=".", final=False):
    """[필수]/[권고]/[참고] 목록을 돌려준다. 판정 내용이 아니라 판정의 규칙 준수만 본다."""
    out = []

    def add(level, cid, msg):
        out.append((level, cid, msg))

    if led.get("schema") != SCHEMA:
        add("필수", "-", "원장 형식(schema)이 %s가 아님" % SCHEMA)
    srcs = led.get("sources", {})
    for sid, s in srcs.items():
        if s.get("access_status") not in ACCESS:
            add("필수", sid, "access_status 값이 허용 목록에 없음: %r" % s.get("access_status"))
        if s.get("format_issue"):
            add("권고", sid, "식별자 형식 문제 — %s (%s)" % (s["format_issue"], s.get("ref")))
        if s.get("tier") not in (None, 1, 2, 3, 4):
            add("필수", sid, "tier는 1~4")
    for c in led.get("claims", []):
        cid, v = c["id"], c.get("verdict", "PENDING")
        if v not in VERDICTS:
            add("필수", cid, "판정 값이 허용 목록에 없음: %r" % v)
            continue
        if v == "PENDING":
            add("필수" if final else "참고", cid, "아직 판정하지 않음")
            continue
        if v == "OUT_OF_SCOPE":
            if not c.get("reason"):
                add("필수", cid, "검증 대상이 아니라고 본 사유(reason)가 필요")
            continue
        checks = c.get("checks", [])
        atom_ids = {a["id"] for a in c.get("atoms", [])}
        checked = {k.get("atom") for k in checks}
        for k in checks:
            if k.get("evidence_status") not in EVIDENCE:
                add("필수", cid, "evidence_status 값이 허용 목록에 없음: %r" % k.get("evidence_status"))
            if k.get("origin") is not None and k.get("origin") not in ORIGINS:
                add("필수", cid, "origin 값이 허용 목록에 없음: %r" % k.get("origin"))
            if k.get("source") and k["source"] not in srcs:
                add("필수", cid, "checks가 원장에 없는 출처 %s를 가리킴" % k["source"])
        if v in ("NEEDS_REVIEW", "REJECT", "NO_SOURCE") and not (c.get("reason") and c.get("action")):
            add("필수", cid, "%s에는 사유(reason)와 다음 조치(action)가 모두 있어야 함" % v)
        if v == "NO_SOURCE":
            continue
        if v == "VERIFIED":
            missing = atom_ids - checked
            if missing:
                add("필수", cid, "검증 항목 %d개 중 %d개를 대조하지 않고 VERIFIED (R2: 수치 N개 = 검증 항목 N개) — %s"
                    % (len(atom_ids), len(missing), ", ".join(sorted(missing))))
            if not c.get("sources") and not any(k.get("source") for k in checks):
                add("필수", cid, "출처가 하나도 없는데 VERIFIED")
            elif not c.get("sources"):
                add("권고", cid, "검증자가 찾은 출처를 본문에도 달아야 함")
            tiers = [srcs[k["source"]].get("tier") for k in checks
                     if k.get("source") in srcs and k.get("evidence_status") == "SUPPORTS"]
            sup = [srcs[k["source"]] for k in checks
                   if k.get("source") in srcs and k.get("evidence_status") == "SUPPORTS"]
            speech_only = all(at["type"] in ("quote", "date", "year") for at in c.get("atoms", []))
            if tiers and all(t == 4 for t in tiers) and not (
                    speech_only and sup and all(x.get("speaker_own") for x in sup)):
                add("필수", cid, "Tier 4 출처만으로 VERIFIED — 원출처를 찾아 대체 (발언 귀속 주장이면 발언자 본인 채널에 speaker_own 표시)")
        for k in checks:
            ev, src = k.get("evidence_status"), srcs.get(k.get("source")) or {}
            acc = src.get("access_status", "NOT_CHECKED")
            scope = k.get("scope", "content")
            atom = next((x for x in c.get("atoms", []) if x["id"] == k.get("atom")), None)
            if ev == "SUPPORTS" and k.get("via") == "summary":
                add("필수", cid, "%s: 요약 도구(WebFetch 요약·검색 AI 요약)를 거친 문장으로 대조 — 원문 텍스트(fv_sources)로 다시 대조" % k.get("atom"))
            if ev == "SUPPORTS":
                need = ("FULL_TEXT", "METADATA_ONLY") if scope == "bibliographic" else ("FULL_TEXT",)
                if acc not in need:
                    add("필수", cid, "%s: 출처 %s의 접속 상태가 %s인데 SUPPORTS — 본문을 확보한 출처로만 뒷받침 가능"
                        % (k.get("atom"), k.get("source"), acc))
                if k.get("scope_match") is False:
                    add("필수", cid, "%s: 집계 범위·모수가 다르다고 기록했는데 SUPPORTS (⑭)" % k.get("atom"))
                if scope != "bibliographic":
                    if not (k.get("excerpt") and k.get("locator")):
                        add("필수", cid, "%s: SUPPORTS에는 원문 발췌(excerpt)와 위치(locator)가 필요" % k.get("atom"))
                    else:
                        txt = _source_text(led, k.get("source"), base)
                        if txt is not None and norm(k["excerpt"]) not in norm(txt):
                            add("필수", cid, "%s: 발췌문이 저장된 원문(%s)에 없음 — 자기보고를 믿지 않는다"
                                % (k.get("atom"), src.get("text_file")))
                        elif txt is None:
                            add("참고", cid, "%s: 저장된 원문 텍스트가 없어 발췌를 기계로 대조하지 못함" % k.get("atom"))
                origin = k.get("origin") or "literal"
                if atom and origin == "literal" and k.get("excerpt"):
                    if atom["type"] in ("number", "year", "date"):
                        d = digits(atom["text"])
                        if d and d not in digits(k["excerpt"]).replace(".", "") and \
                                d.replace(".", "") not in re.sub(r"\D", "", k["excerpt"]):
                            add("권고", cid, "%s: '%s'를 원문 그대로라고 했는데 발췌에 그 숫자가 없음 — 환산·계산이면 origin과 formula를 적을 것"
                                % (k.get("atom"), atom["text"]))
                    if atom["type"] == "quote" and norm(atom["text"]) not in norm(k["excerpt"]):
                        add("필수", cid, "%s: 직접인용이 발췌문에 글자 그대로 없음 (⑥ 직접인용 날조 의심)" % k.get("atom"))
                ex = k.get("excerpt") or ""
                if atom and atom["type"] == "absolute" and ex:
                    word = re.sub(r"\s", "", atom["text"])
                    key = next((w for w in ABS_EN if w in word), None)
                    if word not in re.sub(r"\s", "", ex) and not (key and re.search(ABS_EN[key], ex, re.I)):
                        add("필수", cid, "%s: 최상급·전칭 '%s'이 발췌에 없음 — 원문 문자 그대로일 때만 쓴다 (⑰)" % (k.get("atom"), atom["text"]))
                if atom and atom["type"] == "absence" and not k.get("search_scope"):
                    add("필수", cid, "%s: '없다·공백' 주장에는 무엇을 어디까지 찾았는지(search_scope)가 필요 (⑳)" % k.get("atom"))
                if ex and HEDGE_SRC.search(ex) and not HEDGE_DRAFT.search(c["sentence"]):
                    add("권고", cid, "%s: 원문의 유보·한정어('%s')가 본문에서 빠졌을 수 있음 — 단언 강도 확인 (⑯)"
                        % (k.get("atom"), HEDGE_SRC.search(ex).group(0)))
                if atom and atom["type"] == "number" and ex:
                    pp = re.search(r"%p|percentage point|퍼센트\s?포인트|%\s?포인트", ex, re.I)
                    if "%p" in atom["text"] and not pp and "%" in ex:
                        add("권고", cid, "%s: 본문은 %%p, 발췌는 %% — 단위 확인 (⑲)" % k.get("atom"))
                    elif atom["text"].endswith("%") and pp:
                        add("권고", cid, "%s: 본문은 %%, 발췌는 %%p(퍼센트포인트) — 단위 확인 (⑲)" % k.get("atom"))
                if k.get("source") and k["source"] not in c.get("sources", []) and \
                        (srcs.get(k["source"]) or {}).get("alt_for") not in c.get("sources", []) and c.get("sources"):
                    add("권고", cid, "%s: 본문 각주에 없는 출처(%s)로만 확인됨 — 출처줄 불일치, 각주 보강 (㉑)" % (k.get("atom"), k["source"]))
                if origin in ("derived", "converted") and not k.get("formula"):
                    add("필수", cid, "%s: 계산·환산한 수치에는 산식(formula)이 필요 (⑧)" % k.get("atom"))
                if origin == "derived" and not re.search(r"산출|추정|계산|환산|역산|합산|기준", c["sentence"]):
                    add("권고", cid, "%s: 계산한 수치가 본문에서 원문 수치처럼 보임 — '산출'·'추정' 등으로 표시" % k.get("atom"))
                if origin == "paraphrase" and atom and atom["type"] == "quote":
                    add("권고", cid, "%s: 취지만 같은 인용 — 따옴표를 벗겨 의역으로" % k.get("atom"))
                if origin == "not_in_source":
                    add("필수", cid, "%s: 원문에 없다고 기록했는데 SUPPORTS" % k.get("atom"))
            if ev == "CONTRADICTS" and k.get("scope_match") is False:
                add("필수", cid, "%s: 모수·범위가 다르면 반박이 아니라 범위 차이 (⑭)" % k.get("atom"))
        if v == "REJECT":
            ok = [k for k in checks if k.get("evidence_status") in ("CONTRADICTS", "CITATION_MISMATCH")
                  and (srcs.get(k.get("source")) or {}).get("access_status") in ("FULL_TEXT", "METADATA_ONLY")
                  and k.get("scope_match") is not False]
            if not ok:
                add("필수", cid, "REJECT는 확보한 원문이 반박하거나 인용이 어긋난다는 근거가 있어야 함 — 접속 실패(404·403·빈 본문)만으로는 REJECT 불가")
        if v == "VERIFIED" and any(k.get("evidence_status") in ("CONTRADICTS", "CITATION_MISMATCH") for k in checks):
            add("필수", cid, "반박·인용 불일치 기록이 있는데 VERIFIED")
        if v == "VERIFIED" and any(k.get("evidence_status") in ("INSUFFICIENT", "NOT_CHECKED") for k in checks):
            add("필수", cid, "근거 부족(INSUFFICIENT)·미대조 항목이 있는데 VERIFIED")
        if v == "VERIFIED" and c.get("needs_as_of") and not any(k.get("as_of") for k in checks):
            add("권고", cid, "시점에 따라 바뀌는 값(가격·사용자 수·모델 사양·저장소 지표 등) — 조회일(as_of)을 적고 본문에 기준일 표기 (⑱)")
        if c.get("reintroduced"):
            add("필수", cid, "이전 판에서 반박된 값 %s이 다시 나타남 — 정정 회귀" % ", ".join(c["reintroduced"]))
        if any(k.get("source_inconsistent") for k in checks):
            add("참고", cid, "원문 자체가 내부적으로 어긋남 — 본문이 어느 값을 썼는지 밝힐 것 (㉒)")
        if v == "NEEDS_REVIEW" and c.get("carried", 0) >= 2:
            add("권고", cid, "확인 보류가 %d차째 넘어옴 — 확인 경로를 정해 끝내거나, 본문 단정을 낮춰 미확인임을 드러낼 것" % (c["carried"] + 1))
        if c.get("no_source_candidate") and v == "VERIFIED" and not c.get("sources"):
            add("권고", cid, "본문에 출처 표기가 없는 문장 — 확인한 출처를 각주로")
    for o in led.get("orphans", {}).get("cites_without_reference", []):
        add("권고", "L%d" % o["line"], "본문 인용 '%s'가 참고문헌 목록에 없음" % o["cite"])
    for r in led.get("orphans", {}).get("references_never_cited", []):
        add("참고", "-", "본문에서 부르지 않는 참고문헌: %s" % r[:80])
    for t in led.get("traces", []):
        add("참고", "L%d" % t["line"], "작업 흔적 '%s' — 배포 전 정리" % t["text"])
    return out


def cmd_check(a):
    led = load(a.ledger)
    res = check_ledger(led, os.path.dirname(os.path.abspath(a.ledger)), a.final)
    order = {"필수": 0, "권고": 1, "참고": 2}
    res.sort(key=lambda x: (order[x[0]], x[1]))
    shown = [r for r in res if a.verbose or r[0] != "참고"]
    for lv, cid, msg in shown:
        print("[%s] %s  %s" % (lv, cid, msg))
    n = {k: sum(1 for r in res if r[0] == k) for k in order}
    print("\n점검 결과: [필수] %d · [권고] %d · [참고] %d%s" % (
        n["필수"], n["권고"], n["참고"], "" if a.verbose else " (참고는 -v로 표시)"))
    if n["필수"]:
        print("→ [필수]가 남아 있으면 보고서를 내보내지 않습니다.")
    return 1 if n["필수"] else 0


# ---------------------------------------------------------------- 보고서

def summarize(led):
    cl = led.get("claims", [])
    by_v = {v: sum(1 for c in cl if c.get("verdict") == v) for v in VERDICTS}
    srcs = led.get("sources", {})
    used = {sid for c in cl for sid in c.get("sources", [])} | \
           {k.get("source") for c in cl for k in c.get("checks", []) if k.get("source")}
    by_t = {t: sum(1 for sid in used if (srcs.get(sid) or {}).get("tier") == t) for t in (1, 2, 3, 4)}
    by_t["미분류"] = sum(1 for sid in used if (srcs.get(sid) or {}).get("tier") is None)
    by_a = {}
    for sid in used:
        st = (srcs.get(sid) or {}).get("access_status", "NOT_CHECKED")
        by_a[st] = by_a.get(st, 0) + 1
    atoms = sum(len(c.get("atoms", [])) for c in cl)
    checked = sum(len({k.get("atom") for k in c.get("checks", [])}) for c in cl)
    return {"claims": len(cl), "by_verdict": by_v, "by_tier": by_t, "by_access": by_a,
            "atoms": atoms, "atoms_checked": checked, "sources": len(used)}


def _independent(led, c):
    srcs = led.get("sources", {})
    ids = [k["source"] for k in c.get("checks", [])
           if k.get("evidence_status") == "SUPPORTS" and k.get("source") in srcs]
    return len({srcs[s].get("chain") or s for s in ids})


def _clean(s):
    s = FN_REF.sub("", LIST_MARK.sub("", s or ""))
    return re.sub(r"\[\d{1,3}\](?!\()", "", s).strip()


def _cell(s, n=60):
    s = re.sub(r"\s+", " ", s or "").replace("|", "／")
    return s if len(s) <= n else s[:n - 1] + "…"


def _src_label(s):
    if not s:
        return "-"
    ref = s.get("ref", "")
    if s["kind"] == "url":
        host = urllib.parse.urlparse(ref).netloc.replace("www.", "")
        return host or ref[:30]
    if s["kind"] in ("doi", "arxiv", "isbn"):
        return "%s %s" % (s["kind"].upper() if s["kind"] != "arxiv" else "arXiv", ref)
    return _cell(ref, 30)


def render_md(led):
    sm = summarize(led)
    v = sm["by_verdict"]
    lines = ["## 출처 검증 보고서", ""]
    lines.append("- 검증 대상: 주장 %d건 · 검증 항목 %d개(대조 %d) | ✅ VERIFIED %d | ⚠️ NEEDS_REVIEW %d | ❌ REJECT %d | 🚫 NO_SOURCE %d%s%s"
                 % (sm["claims"] - v["OUT_OF_SCOPE"], sm["atoms"], sm["atoms_checked"], v["VERIFIED"], v["NEEDS_REVIEW"],
                    v["REJECT"], v["NO_SOURCE"], " | ⏳ 미판정 %d" % v["PENDING"] if v["PENDING"] else "",
                    " (검증 대상 아님 %d건 제외)" % v["OUT_OF_SCOPE"] if v["OUT_OF_SCOPE"] else ""))
    t = sm["by_tier"]
    lines.append("- 출처 %d개 · Tier 분포: T1 %d / T2 %d / T3 %d / T4 %d / 미분류 %d"
                 % (sm["sources"], t[1], t[2], t[3], t[4], t["미분류"]))
    lines.append("- 접속 상태: " + (", ".join("%s %d" % kv for kv in sorted(sm["by_access"].items())) or "-"))
    doc = led.get("document", {})
    lines.append("- 검증 깊이: %s | 원고: %s | 보고서 생성: %s" % (
        led.get("depth", "standard"), os.path.basename(doc.get("path") or "-"), now()[:16].replace("T", " ")))
    lines.append("- 건수는 원장(`fv.py`)이 센 값입니다. 접속 상태는 판정이 아니며, 접속 실패는 거짓의 증거가 아닙니다.")
    lines += ["", "| # | 주장(요약) | 출처 | Tier | 접속 | 대조 | 판정 | 사유·조치 |",
              "|---|---|---|---|---|---|---|---|"]
    srcs = led.get("sources", {})
    for c in led.get("claims", []):
        if c.get("verdict") == "OUT_OF_SCOPE":
            continue
        used = [k.get("source") for k in c.get("checks", []) if k.get("source") in srcs]
        sids = list(dict.fromkeys(used + list(c.get("sources") or [])))
        s0 = srcs.get(sids[0]) if sids else None
        more = " 외 %d" % (len(sids) - 1) if len(sids) > 1 else ""
        if s0 and s0.get("alt_for"):
            more = " (대체)" + more
        n_at = len(c.get("atoms", []))
        n_ok = len({k.get("atom") for k in c.get("checks", []) if k.get("evidence_status") == "SUPPORTS"})
        why = c.get("reason", "")
        if c.get("action"):
            why += (" → " if why else "") + c["action"]
        if c.get("carried"):
            why = ("이월 %d회 · " % c["carried"]) + why
        ind = _independent(led, c)
        if ind > 1:
            why = ("독립 출처 %d · " % ind) + why
        lines.append("| %s | %s | %s%s | %s | %s | %d/%d | %s | %s |" % (
            c["id"], _cell(_clean(c["sentence"])), _src_label(s0), more,
            (s0 or {}).get("tier") or "-", (s0 or {}).get("access_status", "-"),
            n_ok, n_at, ICON.get(c.get("verdict"), "?"), _cell(why, 90)))
    bad = [c for c in led.get("claims", []) if c.get("verdict") == "REJECT"]
    if bad:
        lines += ["", "### 쓰면 안 되는 것 (다음 판에서 다시 나오면 안 됨)", ""]
        for c in bad:
            lines.append("- %s %s → %s" % (c["id"], _cell(_clean(c["sentence"]), 70), c.get("action", "")))
    todo = [c for c in led.get("claims", []) if c.get("verdict") in ("NEEDS_REVIEW", "REJECT", "NO_SOURCE")]
    if todo:
        lines += ["", "### 재조사 요청", ""]
        for c in todo:
            lines.append("- **%s** %s %s — %s / 확인할 것: %s" % (
                c["id"], ICON[c["verdict"]], _cell(_clean(c["sentence"]), 80), c.get("reason", ""), c.get("action", "")))
    if led.get("traces"):
        lines += ["", "### 작업 흔적 (배포 전 정리)", ""]
        for t in led["traces"]:
            lines.append("- %d행: %s" % (t["line"], t["text"]))
    orph = led.get("orphans", {})
    if orph.get("cites_without_reference") or orph.get("references_never_cited"):
        lines += ["", "### 인용–참고문헌 대조", ""]
        for o in orph.get("cites_without_reference", []):
            lines.append("- 목록에 없는 인용: %s (%d행)" % (o["cite"], o["line"]))
        for r in orph.get("references_never_cited", []):
            lines.append("- 본문에서 부르지 않는 문헌: %s" % _cell(r, 100))
    return "\n".join(lines) + "\n"


def _yaml(obj, ind=0):
    pad = "  " * ind
    if isinstance(obj, dict):
        out = []
        for k, v in obj.items():
            if isinstance(v, (dict, list)) and v:
                out.append("%s%s:\n%s" % (pad, k, _yaml(v, ind + 1)))
            else:
                out.append("%s%s: %s" % (pad, k, json.dumps(v, ensure_ascii=False) if not isinstance(v, (dict, list)) else ("{}" if isinstance(v, dict) else "[]")))
        return "\n".join(out)
    if isinstance(obj, list):
        out = []
        for v in obj:
            if isinstance(v, dict):
                body = _yaml(v, ind + 1).lstrip()
                out.append("%s- %s" % (pad, body))
            else:
                out.append("%s- %s" % (pad, json.dumps(v, ensure_ascii=False)))
        return "\n".join(out)
    return pad + json.dumps(obj, ensure_ascii=False)


def render_yaml(led):
    sm = summarize(led)
    srcs = led.get("sources", {})

    def item(c):
        return {"id": c["id"], "claim": c["sentence"], "verdict": c.get("verdict"),
                "reason": c.get("reason", ""), "action": c.get("action", ""),
                "checks": [{"atom": k.get("atom"), "source": (srcs.get(k.get("source")) or {}).get("ref"),
                            "access_status": (srcs.get(k.get("source")) or {}).get("access_status"),
                            "evidence_status": k.get("evidence_status"), "locator": k.get("locator", "")}
                           for k in c.get("checks", [])]}
    cl = led.get("claims", [])
    rep = {"verification_report": {
        "total": sm["claims"], "by_verdict": sm["by_verdict"], "by_tier": {str(k): v for k, v in sm["by_tier"].items()},
        "by_access": sm["by_access"],
        "rejected_items": [item(c) for c in cl if c.get("verdict") == "REJECT"],
        "review_needed": [item(c) for c in cl if c.get("verdict") in ("NEEDS_REVIEW", "NO_SOURCE")],
        "verified_items": [item(c) for c in cl if c.get("verdict") == "VERIFIED"]}}
    return _yaml(rep) + "\n"


def cmd_report(a):
    led = load(a.ledger)
    res = check_ledger(led, os.path.dirname(os.path.abspath(a.ledger)), final=True)
    must = [r for r in res if r[0] == "필수"]
    if must and not a.force:
        print("[필수] %d건이 남아 있어 보고서를 만들지 않습니다. `fv.py check`로 확인하세요 (--force로 무시)." % len(must))
        return 1
    text = render_yaml(led) if a.format == "yaml" else render_md(led)
    if a.output:
        with open(a.output, "w", encoding="utf-8") as f:
            f.write(text)
        print("보고서: %s" % a.output)
    else:
        sys.stdout.write(text)
    return 0


# ---------------------------------------------------------------- 수정본 대조

def diff_ledgers(old, new):
    by_hash = {c["sentence_hash"]: c for c in old.get("claims", [])}
    olds = old.get("claims", [])
    used, stats = set(), {"unchanged": 0, "changed": 0, "new": 0, "removed": 0}
    # 출처 번호를 옛 원장 기준으로 맞춘다
    old_key = {(s["kind"], s["ref"]): sid for sid, s in old.get("sources", {}).items()}
    remap, merged = {}, dict(old.get("sources", {}))
    for sid, s in new.get("sources", {}).items():
        k = (s["kind"], s["ref"])
        if k in old_key:
            remap[sid] = old_key[k]
        else:
            nid = "S%02d" % (len(merged) + 1)
            while nid in merged:
                nid = "S%02d" % (int(nid[1:]) + 1)
            merged[nid] = s
            remap[sid] = nid
    for c in new.get("claims", []):
        c["sources"] = [remap.get(s, s) for s in c.get("sources", [])]
        prev = by_hash.get(c["sentence_hash"])
        if prev and prev["id"] not in used:
            used.add(prev["id"])
            for f in ("checks", "verdict", "reason", "action"):
                c[f] = prev.get(f, c.get(f))
            amap = {a["text"]: a["id"] for a in c["atoms"]}
            for k in c["checks"]:
                old_atom = next((x for x in prev["atoms"] if x["id"] == k.get("atom")), None)
                if old_atom and old_atom["text"] in amap:
                    k["atom"] = amap[old_atom["text"]]
            c["status_change"] = "unchanged"
            if c.get("verdict") == "NEEDS_REVIEW":
                c["carried"] = prev.get("carried", 0) + 1
            stats["unchanged"] += 1
            continue
        best, ratio = None, 0.0
        for o in olds:
            if o["id"] in used:
                continue
            r = difflib.SequenceMatcher(None, norm(o["sentence"]), norm(c["sentence"]), autojunk=False).ratio()
            if r > ratio:
                best, ratio = o, r
        if best and ratio >= 0.6:
            used.add(best["id"])
            c["prev"] = {"id": best["id"], "sentence": best["sentence"], "verdict": best.get("verdict"),
                         "similarity": round(ratio, 2)}
            c["status_change"] = "changed"
            stats["changed"] += 1
        else:
            c["status_change"] = "new"
            stats["new"] += 1
    banned = {}
    for o in olds:
        if o.get("verdict") != "REJECT":
            continue
        for k in o.get("checks", []):
            if k.get("evidence_status") == "CONTRADICTS":
                at = next((x for x in o.get("atoms", []) if x["id"] == k.get("atom")), None)
                if at and at["type"] == "number" and digits(at["text"]):
                    banned[digits(at["text"])] = at["text"]
    for c in new.get("claims", []):
        if c.get("status_change") == "unchanged":
            continue
        hit = [banned[digits(a["text"])] for a in c["atoms"]
               if a["type"] == "number" and digits(a["text"]) in banned]
        if hit:
            c["reintroduced"] = hit
    removed = [{"id": o["id"], "sentence": o["sentence"], "verdict": o.get("verdict")}
               for o in olds if o["id"] not in used]
    stats["removed"] = len(removed)
    new["sources"] = merged
    new["removed_claims"] = removed
    new["diff_from"] = old.get("document", {})
    return new, stats


def cmd_diff(a):
    old = load(a.ledger)
    new = extract(read_doc(a.document), a.document)
    new["depth"] = old.get("depth", "standard")
    new, st = diff_ledgers(old, new)
    out = a.output or a.ledger
    dump(new, out)
    print("유지 %d · 바뀐 주장 %d(다시 검증) · 새 주장 %d · 빠진 주장 %d → %s"
          % (st["unchanged"], st["changed"], st["new"], st["removed"], out))
    for c in new["claims"]:
        if c.get("reintroduced"):
            print("  ! %s 이전 판에서 반박된 값 %s이 다시 나타남 — %s" % (c["id"], ", ".join(c["reintroduced"]), _cell(_clean(c["sentence"]), 50)))
        if c.get("status_change") == "unchanged" and c.get("verdict") in ("REJECT", "NO_SOURCE"):
            print("  ! %s %s인 문장이 고쳐지지 않은 채 남음 — %s" % (c["id"], c["verdict"], _cell(_clean(c["sentence"]), 60)))
        elif c.get("carried", 0) >= 2:
            print("  ! %s 확인 보류가 %d차째 넘어옴 — %s" % (c["id"], c["carried"] + 1, _cell(_clean(c["sentence"]), 60)))
    for c in new["claims"]:
        if c.get("status_change") == "changed":
            print("  ~ %s (%s였음) %s" % (c["id"], c["prev"]["verdict"], _cell(c["sentence"], 70)))
        elif c.get("status_change") == "new":
            print("  + %s %s" % (c["id"], _cell(c["sentence"], 70)))
    return 0


# ---------------------------------------------------------------- 표본

def cmd_sample(a):
    led = load(a.ledger)
    pool = [c for c in led["claims"] if c.get("verdict") == "VERIFIED"]
    k = max(1, round(len(pool) * a.rate)) if pool else 0
    rng = random.Random(a.seed)
    pick = sorted(rng.sample(pool, k), key=lambda c: c["id"]) if k else []
    print("VERIFIED %d건 중 %d건(%.0f%%)을 독립 재검증 표본으로 뽑았습니다 (seed=%s)."
          % (len(pool), k, a.rate * 100, a.seed))
    for c in pick:
        c["resample"] = True
        print("  %s  %s" % (c["id"], _cell(c["sentence"], 80)))
    if pick:
        dump(led, a.ledger)
    print("표본에서 문제가 나오면 같은 조사자의 다른 VERIFIED도 한 단계 낮춰 다시 봅니다 (R3).")
    return 0


# ---------------------------------------------------------------- extract 명령

def cmd_extract(a):
    text = read_doc(a.document)
    led = extract(text, a.document)
    led["depth"] = a.depth
    out = a.output or os.path.splitext(a.document)[0] + ".fv.json"
    dump(led, out)
    cl = led["claims"]
    types = {}
    for c in cl:
        for at in c["atoms"]:
            types[at["type"]] = types.get(at["type"], 0) + 1
    ns = sum(1 for c in cl if c["no_source_candidate"])
    print("원장: %s" % out)
    print("주장 %d건 · 검증 항목 %d개 (%s)" % (len(cl), sum(types.values()),
          ", ".join("%s %d" % kv for kv in sorted(types.items(), key=lambda x: -x[1]))))
    print("출처 %d개 · 출처 표기 없는 주장 %d건 · 목록에 없는 인용 %d · 부르지 않는 문헌 %d" % (
        len(led["sources"]), ns, len(led["orphans"]["cites_without_reference"]),
        len(led["orphans"]["references_never_cited"])))
    bad = [(sid, s) for sid, s in led["sources"].items() if s["format_issue"]]
    for sid, s in bad:
        print("  형식 문제 %s %s — %s" % (sid, s["ref"], s["format_issue"]))
    return 0


# ---------------------------------------------------------------- 자체 점검

def _case_ledger():
    return {
        "schema": SCHEMA, "depth": "standard", "orphans": {},
        "sources": {
            "S01": {"kind": "url", "ref": "https://old.example.go.kr/a", "tier": 1, "access_status": "NOT_FOUND"},
            "S02": {"kind": "url", "ref": "https://new.example.go.kr/a", "tier": 1, "access_status": "FULL_TEXT",
                    "alt_for": "S01"},
            "S03": {"kind": "url", "ref": "https://spa.example.org", "tier": 2, "access_status": "EMPTY_BODY"},
            "S04": {"kind": "url", "ref": "https://blog.example.com", "tier": 4, "access_status": "FULL_TEXT"},
        },
        "claims": []}


def _claim(cid, verdict, checks, atoms=None, sentence="2025년 예산은 5,000억 원이다.", sources=("S01",), **kw):
    atoms = atoms if atoms is not None else [{"id": cid + ".a1", "type": "number", "text": "5,000억 원"}]
    c = {"id": cid, "sentence": sentence, "sentence_hash": shash(sentence), "atoms": atoms,
         "sources": list(sources), "checks": checks, "verdict": verdict, "reason": "", "action": ""}
    c.update(kw)
    return c


def selftest():
    fails = []

    def ok(cond, name):
        if not cond:
            fails.append(name)

    def must(led):
        return [r for r in check_ledger(led) if r[0] == "필수"]

    # 쪼개기
    s = sentences("2026. 10. 9. 발표에 따르면 예산은 5,000억 원이다. 인력은 200명이다.")
    ok(len(s) == 2, "날짜 안의 마침표에서 문장을 자르지 않음")
    ok(len(sentences("“Step 1 build the thing. Step 2 build the ramp.” — 2024. 2. 22.")) == 1, "따옴표 안에서 자르지 않음")
    at = atoms_of("배출 인력은 200명이고 그중 정년직은 60명이다(Kim, 2021).")
    ok(sum(1 for x in at if x["type"] == "number") == 2, "한 문장의 수치 2개 = 항목 2개")
    ok([x["text"] for x in atoms_of("예산은 1조 2,000억 원, 사업비는 3억 5천만 원이다.")] == ["1조 2,000억 원", "3억 5천만 원"],
       "조·억·만이 이어지는 수는 하나로")
    ok(not any(x["text"] == "2021" for x in at), "서지 연도는 수치로 세지 않음")
    at = atoms_of("GPT-4와 COVID-19 관련 3.2절에서 “혁신은 실패를 전제로 한다”고 했다.")
    ok([x["type"] for x in at] == ["quote"], "모델명·절 번호는 제외, 직접인용은 항목")
    at = atoms_of("「과학기술기본법」 제7조 제2항에 따라 2024년 12월 3일 시행")
    ok({x["type"] for x in at} == {"title", "law", "date"}, "법령명·조문·날짜 항목")
    ok(format_issues("arxiv", "2413.12345") is not None, "arXiv 월 13 형식 오류")
    ok(format_issues("isbn", "9788936433598") is None, "ISBN-13 정상")
    led = extract("예산은 5,000억 원이다[^1].\n\n성장률 3.1%를 기록했다.\n\n[^1]: https://example.go.kr/x\n")
    ok(len(led["claims"]) == 2 and led["claims"][1]["no_source_candidate"], "출처 없는 수치 문장 표시")
    ok(led["sources"]["S01"]["ref"] == "https://example.go.kr/x", "각주 속 링크를 출처로")
    led = extract("효과가 컸다(Lee, 2020).\n\n## 참고문헌\n- Kim, J. (2019). Title. Journal.\n")
    ok(led["orphans"]["cites_without_reference"] and led["orphans"]["references_never_cited"], "고아 인용·고아 문헌")

    # 판정 규칙 회귀 사례 (정비 계획의 통과 기준)
    good = {"atom": "C1.a1", "source": "S02", "evidence_status": "SUPPORTS", "origin": "literal",
            "excerpt": "예산 5,000억 원", "locator": "보도자료 2쪽"}
    led = _case_ledger()
    led["claims"] = [_claim("C1", "VERIFIED", [good])]
    ok(not must(led), "① 원래 링크 404 + 공식 대체 원문 대조 → VERIFIED 가능")
    led["claims"] = [_claim("C1", "VERIFIED", [dict(good, source="S03")], sources=("S03",))]
    ok(must(led), "② 200이지만 빈 본문으로 VERIFIED 불가")
    led["claims"] = [_claim("C1", "NEEDS_REVIEW", [dict(good, source="S03", evidence_status="INSUFFICIENT")],
                            sources=("S03",), reason="빈 본문", action="PDF 원문 확보")]
    ok(not must(led), "② 빈 본문 → NEEDS_REVIEW + 사유·조치는 통과")
    led["claims"] = [_claim("C1", "VERIFIED", [dict(good, scope_match=False)])]
    ok(must(led), "③ 모수가 다른 수치로 SUPPORTS 불가")
    led["claims"] = [_claim("C1", "REJECT", [dict(good, evidence_status="CONTRADICTS", scope_match=False)],
                            reason="수치 다름", action="범위 확인")]
    ok(must(led), "③ 모수가 다른데 REJECT 불가")
    led["claims"] = [_claim("C1", "REJECT", [dict(good, evidence_status="CONTRADICTS", excerpt="예산 3,000억 원")],
                            reason="원문은 3,000억", action="수정")]
    ok(not must(led), "④ 확보한 원문이 반박 → REJECT 통과")
    led["claims"] = [_claim("C1", "REJECT", [], reason="404", action="삭제")]
    ok(must(led), "④ 접속 실패만으로 REJECT 불가")
    led["claims"] = [_claim("C1", "VERIFIED", [dict(good, origin="derived")])]
    ok(must(led), "⑤ 계산한 수치에 산식 없음")
    q = [{"id": "C1.a1", "type": "quote", "text": "실패를 미리 합의한다"}]
    led["claims"] = [_claim("C1", "VERIFIED", [dict(good, excerpt="kill criteria agreed in advance")], atoms=q)]
    ok(must(led), "⑥ 직접인용이 발췌에 없음")
    led["claims"] = [_claim("C1", "VERIFIED", [dict(good, source="S04")], sources=("S04",))]
    ok(must(led), "⑦ Tier 4만으로 VERIFIED 불가")
    two = [{"id": "C1.a1", "type": "number", "text": "200명"}, {"id": "C1.a2", "type": "number", "text": "60명"}]
    led["claims"] = [_claim("C1", "VERIFIED", [dict(good, excerpt="200명")], atoms=two)]
    ok(must(led), "⑧ 항목 2개 중 1개만 대조하고 VERIFIED 불가")

    # 수정본 대조
    old = extract("예산은 5,000억 원이다.\n\n인력은 200명이다.\n")
    old["claims"][0]["verdict"] = "VERIFIED"
    new = extract("예산은 5,000억 원이다.\n\n인력은 250명이다.\n\n성장률은 3%다.\n")
    new, st = diff_ledgers(old, new)
    ok(st == {"unchanged": 1, "changed": 1, "new": 1, "removed": 0}, "수정본: 유지·바뀜·새 주장 구분")
    ok(new["claims"][0]["verdict"] == "VERIFIED" and new["claims"][1]["verdict"] == "PENDING",
       "바뀐 주장만 다시 미판정으로")

    old2 = extract("예산은 5,000억 원이다.\n")
    old2["claims"][0].update(verdict="NEEDS_REVIEW", reason="차단", action="원문 확보", carried=1)
    new2, _ = diff_ledgers(old2, extract("예산은 5,000억 원이다.\n"))
    ok(new2["claims"][0].get("carried") == 2, "확인 보류 이월 횟수 누적")
    ok(any("넘어옴" in r[2] for r in check_ledger(new2)), "두 번 넘어온 보류는 [권고]")

    # 실전 채굴(보고서 65건)에서 나온 규칙
    ok(any(x["type"] == "absolute" for x in atoms_of("국내 최초로 도입한 제도다.")), "최상급 항목")
    ok(any(x["type"] == "absence" for x in atoms_of("이 주제의 선행연구가 없다.")), "부재 주장 항목")
    led = _case_ledger()
    ab = [{"id": "C1.a1", "type": "absolute", "text": "세계 최초"}]
    led["claims"] = [_claim("C1", "VERIFIED", [dict(good, excerpt="could be among the first")], atoms=ab,
                            sentence="세계 최초로 개발했다.")]
    ok(not must(led) and any("유보" in r[2] for r in check_ledger(led)), "원문 could → 본문 단정은 [권고]")
    led["claims"][0]["checks"][0]["excerpt"] = "a new system was developed"
    ok(must(led), "발췌에 없는 최상급은 [필수]")
    gap = [{"id": "C1.a1", "type": "absence", "text": "선행연구가 없"}]
    led["claims"] = [_claim("C1", "VERIFIED", [dict(good, excerpt="선행연구가 없")], atoms=gap)]
    ok(must(led), "'없다' 주장에 검색 범위 없음")
    led["claims"] = [_claim("C1", "VERIFIED", [dict(good, via="summary")])]
    ok(must(led), "요약 도구를 거친 대조는 [필수]")
    pp = [{"id": "C1.a1", "type": "number", "text": "17%p"}]
    led["claims"] = [_claim("C1", "VERIFIED", [dict(good, excerpt="17% lower")], atoms=pp)]
    ok(any("%p" in r[2] for r in check_ledger(led)), "%p와 % 혼동")
    led["claims"] = [_claim("C1", "VERIFIED", [dict(good)], sources=("S03",))]
    ok(any("출처줄 불일치" in r[2] for r in check_ledger(led)), "각주에 없는 출처로만 확인")
    led = extract("이 저장소의 별은 1,200개다(https://github.com/x/y).\n")
    ok(led["claims"][0]["needs_as_of"], "시점 의존 값에 기준일 없음 표시")
    old3 = extract("기업 수는 2,500개다.\n")
    old3["claims"][0].update(verdict="REJECT", reason="원문 1,250", action="정정", checks=[
        {"atom": "C001.a1", "source": "S01", "evidence_status": "CONTRADICTS"}])
    new3, _ = diff_ledgers(old3, extract("기업 수는 1,250개다.\n\n요약하면 기업은 2,500개다.\n"))
    ok(any(c.get("reintroduced") for c in new3["claims"]), "반박된 값이 다른 문장에 되살아남")
    ok(extract("TODO 원문 대조 전 수치 30%\n")["traces"], "작업 흔적 검출")
    ok(classify({"status": 200, "url": "https://a.go.kr/board/view/123", "final_url": "https://a.go.kr/",
                 "data": b"<html>" + b"x" * 900 + b"</html>"})[0] == "NOT_FOUND", "홈으로 넘어가는 소프트 404")

    # 접속 분류
    ok(classify({"status": 404})[0] == "NOT_FOUND", "404 분류")
    ok(classify({"status": 403})[0] == "BLOCKED", "403 분류")
    ok(classify({"status": 200, "data": b"<html><title>x</title><body>Please enable JavaScript</body></html>"})[0]
       == "EMPTY_BODY", "빈 본문 분류")
    ok(classify({"status": 200, "data": b"%PDF-1.7 ..."})[0] == "FULL_TEXT", "PDF 분류")
    ok(classify({"status": None, "error": "timeout"})[0] == "UNREACHABLE", "접속 불가 분류")

    at = atoms_of("휴식은 09:50–10:00, 6주차 3번째 장에서 30분 진행")
    ok([x["text"] for x in at] == ["30분"], "시각·서수는 수치로 세지 않음")
    led = extract("## 사례\n\n2분 만에 키가 쓰였다.\n\n출처: [Orca](https://orca.example/r)\n")
    ok(len(led["claims"]) == 1 and led["claims"][0]["sources"], "출처 줄을 같은 절의 앞 주장에 붙임")
    led = _case_ledger()
    led["claims"] = [_claim("C1", "OUT_OF_SCOPE", [])]
    ok(must(led), "검증 대상 아님에도 사유 필요")

    led = _case_ledger()
    led["sources"]["S04"]["speaker_own"] = True
    led["claims"] = [_claim("C1", "VERIFIED", [dict(good, source="S04", excerpt="실패를 미리 합의한다")],
                            atoms=[{"id": "C1.a1", "type": "quote", "text": "실패를 미리 합의한다"}], sources=("S04",))]
    ok(not must(led), "발언 귀속 주장은 발언자 본인 채널(speaker_own)로 VERIFIED 가능")
    led["claims"][0]["atoms"].append({"id": "C1.a2", "type": "number", "text": "30%"})
    led["claims"][0]["checks"].append(dict(good, atom="C1.a2", source="S04", excerpt="30%"))
    ok(must(led), "발언자 본인 채널이어도 수치 사실은 원출처 필요")

    total = 52
    print("자체 점검 %d/%d 통과" % (total - len(fails), total))
    for f in fails:
        print("  실패: " + f)
    return 1 if fails else 0


# ---------------------------------------------------------------- 진입점

def main(argv=None):
    p = argparse.ArgumentParser(prog="fv.py", description="fact-verify 주장–근거 원장 도구 " + VERSION)
    sub = p.add_subparsers(dest="cmd")
    e = sub.add_parser("extract", help="원고 → 원장 뼈대")
    e.add_argument("document")
    e.add_argument("-o", "--output")
    e.add_argument("--depth", default="standard", choices=("quick", "standard", "deep"))
    pr = sub.add_parser("probe", help="URL·DOI·arXiv 접속 상태 기록")
    pr.add_argument("ledger")
    pr.add_argument("--save-dir")
    pr.add_argument("--timeout", type=int, default=15)
    pr.add_argument("--only", help="S01,S03처럼 일부만")
    pr.add_argument("--force", action="store_true", help="이미 확인한 것도 다시")
    pr.add_argument("--no-wayback", action="store_true", help="막힌 링크의 웨이백 보관본 조회를 끔")
    c = sub.add_parser("check", help="판정 규칙 준수 점검 (exit 1 = [필수])")
    c.add_argument("ledger")
    c.add_argument("--final", action="store_true", help="미판정도 [필수]로")
    c.add_argument("-v", "--verbose", action="store_true")
    r = sub.add_parser("report", help="원장 → 검증 보고서")
    r.add_argument("ledger")
    r.add_argument("-o", "--output")
    r.add_argument("--format", default="md", choices=("md", "yaml"))
    r.add_argument("--force", action="store_true")
    d = sub.add_parser("diff", help="수정본과 대조해 바뀐 주장만 재검증 대상으로")
    d.add_argument("ledger")
    d.add_argument("document")
    d.add_argument("-o", "--output")
    s = sub.add_parser("sample", help="VERIFIED 자기보고 표본 추출 (R3)")
    s.add_argument("ledger")
    s.add_argument("--rate", type=float, default=0.25)
    s.add_argument("--seed", default="0")
    sub.add_parser("selftest", help="도구 자체 점검")
    p.add_argument("--version", action="version", version=VERSION)
    a = p.parse_args(argv)
    if not a.cmd:
        p.print_help()
        return 2
    try:
        return {"extract": cmd_extract, "probe": cmd_probe, "check": cmd_check, "report": cmd_report,
                "diff": cmd_diff, "sample": cmd_sample, "selftest": lambda _: selftest()}[a.cmd](a)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, ET.ParseError) as ex:
        print("입력 오류: %s: %s" % (type(ex).__name__, ex), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
