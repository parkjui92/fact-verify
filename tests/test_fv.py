"""fv.py 시험 — 네트워크 없이 돈다(접속 분류는 내 컴퓨터 안의 임시 서버로)."""
import http.server
import io
import json
import os
import sys
import tempfile
import threading
import unittest
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import fv  # noqa: E402

LONG = "<p>" + "연구개발 예산은 5,000억 원으로 확정되었다. " * 40 + "</p>"
PAGES = {
    "/ok": (200, "text/html; charset=utf-8", "<html><title>공식 보도자료</title><body><nav>메뉴</nav>%s</body></html>" % LONG),
    "/gone": (404, "text/html", "<html>not found</html>"),
    "/forbidden": (403, "text/html", "<html>Access denied</html>"),
    "/js": (200, "text/html", "<html><title>App</title><body><div id=root></div>"
                              "<noscript>You need to enable JavaScript to run this app.</noscript></body></html>"),
    "/challenge": (200, "text/html", "<html><title>Just a moment...</title><body>Checking your browser</body></html>"),
    "/pdf": (200, "application/pdf", "%PDF-1.7\n1 0 obj\n"),
}


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        st, ct, body = PAGES.get(self.path, (404, "text/plain", "x"))
        data = body.encode("utf-8")
        self.send_response(st)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


class TestSelf(unittest.TestCase):
    def test_selftest(self):
        self.assertEqual(fv.selftest(), 0)


class TestExtract(unittest.TestCase):
    def test_r2_two_numbers_two_items(self):
        led = fv.extract("배출 인력은 200명이고 그중 정년직은 60명이다[^1].\n\n[^1]: https://example.go.kr/a\n")
        c = led["claims"][0]
        self.assertEqual([a["text"] for a in c["atoms"] if a["type"] == "number"], ["200명", "60명"])
        self.assertFalse(c["no_source_candidate"])

    def test_korean_particles(self):
        at = fv.atoms_of("총200명이 참여했고 예산은 5,000억 원이며 성장률은 3%다.")
        self.assertEqual([a["text"] for a in at], ["200명", "5,000억 원", "3%"])

    def test_year_vs_count(self):
        at = fv.atoms_of("2030명이 2030년까지 참여한다.")
        self.assertEqual([(a["type"], a["text"]) for a in at], [("number", "2030명"), ("year", "2030년")])

    def test_table_rows_and_header(self):
        led = fv.extract("| 국가 | 예산 |\n|---|---|\n| 한국 | 30조 원 |\n| 미국 | 2,000억 달러 |\n")
        self.assertEqual(len(led["claims"]), 2)

    def test_code_and_headings_skipped(self):
        led = fv.extract("# 2025년 계획\n\n```\nx = 300\n```\n")
        self.assertEqual(led["claims"], [])

    def test_hwpx_footnote(self):
        sec = ('<?xml version="1.0" encoding="UTF-8"?>'
               '<hs:sec xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" '
               'xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">'
               '<hp:p><hp:run><hp:t>예산은 5,000억 원이다.</hp:t>'
               '<hp:ctrl><hp:footNote><hp:subList><hp:p><hp:run><hp:t>https://example.go.kr/b</hp:t>'
               '</hp:run></hp:p></hp:subList></hp:footNote></hp:ctrl></hp:run></hp:p></hs:sec>')
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "a.hwpx")
            with zipfile.ZipFile(p, "w") as z:
                z.writestr("Contents/section0.xml", sec)
            text = fv.read_doc(p)
        led = fv.extract(text)
        self.assertEqual(led["claims"][0]["atoms"][0]["text"], "5,000억 원")
        self.assertEqual(led["sources"][led["claims"][0]["sources"][0]]["ref"], "https://example.go.kr/b")

    def test_docx_footnote(self):
        W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        doc = ('<w:document xmlns:w="%s"><w:body><w:p><w:r><w:t>인력은 200명이다.</w:t></w:r>'
               '<w:r><w:footnoteReference w:id="2"/></w:r></w:p></w:body></w:document>' % W)
        fn = ('<w:footnotes xmlns:w="%s"><w:footnote w:id="2"><w:p><w:r><w:t>Kim (2021), '
              'https://doi.org/10.1000/xyz123</w:t></w:r></w:p></w:footnote></w:footnotes>' % W)
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "a.docx")
            with zipfile.ZipFile(p, "w") as z:
                z.writestr("word/document.xml", doc)
                z.writestr("word/footnotes.xml", fn)
            led = fv.extract(fv.read_doc(p))
        kinds = {led["sources"][s]["kind"] for s in led["claims"][0]["sources"]}
        self.assertIn("url", kinds)


class TestCheckAndReport(unittest.TestCase):
    def _ledger(self, d):
        src = os.path.join(d, "fv_sources")
        os.makedirs(src)
        with open(os.path.join(src, "S02.txt"), "w", encoding="utf-8") as f:
            f.write("# 보도자료\n\n2025년 연구개발 예산은 5,000억 원으로 확정되었다.\n")
        led = fv._case_ledger()
        led["sources"]["S02"]["text_file"] = "fv_sources/S02.txt"
        led["claims"] = [fv._claim("C1", "VERIFIED", [
            {"atom": "C1.a1", "source": "S02", "evidence_status": "SUPPORTS", "origin": "literal",
             "excerpt": "연구개발 예산은 5,000억 원으로 확정", "locator": "보도자료 1문단"}])]
        return led

    def test_excerpt_found_in_saved_text(self):
        with tempfile.TemporaryDirectory() as d:
            led = self._ledger(d)
            self.assertFalse([r for r in fv.check_ledger(led, d) if r[0] == "필수"])

    def test_excerpt_not_in_saved_text_is_blocking(self):
        with tempfile.TemporaryDirectory() as d:
            led = self._ledger(d)
            led["claims"][0]["checks"][0]["excerpt"] = "예산은 6,000억 원"
            msgs = [r[2] for r in fv.check_ledger(led, d) if r[0] == "필수"]
            self.assertTrue(any("발췌문이 저장된 원문" in m for m in msgs))

    def test_report_counts_are_computed(self):
        with tempfile.TemporaryDirectory() as d:
            led = self._ledger(d)
            led["claims"].append(fv._claim("C2", "NEEDS_REVIEW", [], reason="빈 본문", action="PDF 확보",
                                           sentence="성장률은 3%다.", sources=("S03",)))
            md = fv.render_md(led)
            self.assertIn("✅ VERIFIED 1 | ⚠️ NEEDS_REVIEW 1", md)
            self.assertIn("### 재조사 요청", md)
            y = fv.render_yaml(led)
            self.assertIn("verification_report:", y)

    def test_report_refuses_with_blocking_issues(self):
        with tempfile.TemporaryDirectory() as d:
            led = self._ledger(d)
            led["claims"][0]["checks"][0]["source"] = "S03"
            p = os.path.join(d, "l.json")
            fv.dump(led, p)
            self.assertEqual(fv.main(["report", p, "-o", os.path.join(d, "r.md")]), 1)


class TestDemo(unittest.TestCase):
    """examples/ledger-demo — 채운 원장이 규칙을 지키고, 수정본에서 바뀐 두 문장만 다시 검증 대상이 되는가."""

    def test_demo_passes_gate_and_diff(self):
        import shutil
        demo = os.path.join(HERE, "..", "examples", "ledger-demo")
        with tempfile.TemporaryDirectory() as d:
            for name in ("draft.md", "draft_v2.md", "draft.fv.json"):
                shutil.copy(os.path.join(demo, name), d)
            shutil.copytree(os.path.join(demo, "fv_sources"), os.path.join(d, "fv_sources"))
            led_p = os.path.join(d, "draft.fv.json")
            self.assertEqual(fv.main(["check", led_p, "--final"]), 0)
            with open(led_p, encoding="utf-8") as f:
                old = json.load(f)
            new, st = fv.diff_ledgers(old, fv.extract(fv.read_doc(os.path.join(d, "draft_v2.md"))))
            self.assertEqual(st, {"unchanged": 6, "changed": 2, "new": 0, "removed": 0})
            changed = [c["prev"]["verdict"] for c in new["claims"] if c.get("status_change") == "changed"]
            self.assertEqual(sorted(changed), ["NEEDS_REVIEW", "REJECT"])


class TestProbeClassify(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.base = "http://127.0.0.1:%d" % cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def status(self, path):
        return fv.classify(fv.fetch(self.base + path, timeout=5))[0]

    def test_statuses(self):
        self.assertEqual(self.status("/ok"), "FULL_TEXT")
        self.assertEqual(self.status("/gone"), "NOT_FOUND")
        self.assertEqual(self.status("/forbidden"), "BLOCKED")
        self.assertEqual(self.status("/js"), "EMPTY_BODY")
        self.assertEqual(self.status("/challenge"), "BLOCKED")
        self.assertEqual(self.status("/pdf"), "FULL_TEXT")

    def test_unreachable(self):
        self.assertEqual(fv.classify(fv.fetch("http://127.0.0.1:9/", timeout=2))[0], "UNREACHABLE")

    def test_probe_command_saves_text_and_never_judges(self):
        with tempfile.TemporaryDirectory() as d:
            doc = os.path.join(d, "a.md")
            with open(doc, "w", encoding="utf-8") as f:
                f.write("예산은 5,000억 원이다(%s/ok).\n\n성장률은 3%%다(%s/gone).\n" % (self.base, self.base))
            led_p = os.path.join(d, "a.fv.json")
            self.assertEqual(fv.main(["extract", doc, "-o", led_p]), 0)
            self.assertEqual(fv.main(["probe", led_p, "--timeout", "5", "--no-wayback"]), 0)
            with open(led_p, encoding="utf-8") as f:
                led = json.load(f)
            st = {s["ref"].rsplit("/", 1)[-1]: s for s in led["sources"].values()}
            self.assertEqual(st["ok"]["access_status"], "FULL_TEXT")
            self.assertTrue(os.path.exists(os.path.join(d, st["ok"]["text_file"])))
            self.assertEqual(st["gone"]["access_status"], "NOT_FOUND")
            self.assertTrue(all(c["verdict"] == "PENDING" for c in led["claims"]))


if __name__ == "__main__":
    unittest.main(verbosity=1)
