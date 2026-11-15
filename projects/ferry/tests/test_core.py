import unittest

from ferry.core import MAX_LINKS, Robots, extract, normalize_url
from ferry.view import cell_width, clip, safe, wrap


class URLTests(unittest.TestCase):
    def test_normalization_preserves_query_semantics(self):
        self.assertEqual(normalize_url("HTTPS://EXAMPLE.COM:443/a?q=2&q=1#top"),
                         "https://example.com/a?q=2&q=1")
        self.assertEqual(normalize_url("../中文", "https://example.com/docs/index"),
                         "https://example.com/%E4%B8%AD%E6%96%87")

    def test_invalid_and_non_http_links(self):
        for value in ("javascript:alert(1)", "file:///etc/passwd", "mailto:a@b.com",
                      "http://u:p@host/", "http://bad:99999/", "http://a/\nx", ""):
            with self.subTest(value=value):
                self.assertIsNone(normalize_url(value))

    def test_ipv6_and_port_zero(self):
        self.assertEqual(normalize_url("http://[::1]:8000"), "http://[::1]:8000/")
        self.assertEqual(normalize_url("http://a:0/"), "http://a:0/")


class ExtractionTests(unittest.TestCase):
    def test_extracts_prose_base_and_links_without_executing_scripts(self):
        doc = extract(b"<title>A &amp; B</title><base href='/docs/'><h1>Hello</h1>"
                      b"<script>bad</script><style>hidden</style><p>world</p>"
                      b"<a href='next#one'>Next</a><a href='next#two'>Again</a>"
                      b"<a href='mailto:a@b'>Mail</a>", "https://site.test/", "text/html", None)
        self.assertEqual(doc.title, "A & B")
        self.assertNotIn("bad", doc.text)
        self.assertNotIn("hidden", doc.text)
        self.assertIn("Hello\nworld", doc.text)
        self.assertEqual(doc.links, ["https://site.test/docs/next"])

    def test_chinese_meta_encoding_and_plain_text(self):
        raw = '<meta charset="gb18030"><title>中文</title><p>离线资料</p>'.encode("gb18030")
        doc = extract(raw, "https://site.test/", "text/html", None)
        self.assertEqual(doc.title, "中文")
        self.assertEqual(doc.text, "离线资料")
        self.assertEqual(extract(b"some <text>", "http://a/note.txt", "text/plain", "utf-8").text, "some <text>")

    def test_link_limit(self):
        doc = extract("".join(f'<a href="/{i}">x</a>' for i in range(MAX_LINKS + 5)).encode(),
                      "https://site.test/", "text/html", None)
        self.assertEqual(len(doc.links), MAX_LINKS)
        self.assertTrue(doc.links_truncated)


class RobotsTests(unittest.TestCase):
    def test_longest_match_allow_tie_and_wildcards(self):
        robot = Robots("User-agent: *\nDisallow: /private\nAllow: /private/open\n"
                       "Disallow: /*.pdf$\nDisallow: /equal\nAllow: /equal\nCrawl-delay: 1.5")
        self.assertFalse(robot.allows("http://a/private/a"))
        self.assertTrue(robot.allows("http://a/private/open/a"))
        self.assertFalse(robot.allows("http://a/a/b.pdf"))
        self.assertTrue(robot.allows("http://a/a.pdf?download=1"))
        self.assertTrue(robot.allows("http://a/equal"))
        self.assertEqual(robot.delay, 1.5)

    def test_specific_agent_and_merged_groups(self):
        robot = Robots("User-agent: *\nDisallow: /\nUser-agent: Ferry\nDisallow: /a\n"
                       "User-agent: Ferry\nDisallow: /b\n")
        self.assertTrue(robot.allows("http://a/c"))
        self.assertFalse(robot.allows("http://a/a"))
        self.assertFalse(robot.allows("http://a/b"))

    def test_percent_encoded_and_unicode_paths(self):
        self.assertFalse(Robots("User-agent: *\nDisallow: /private").allows("http://a/p%72ivate"))
        self.assertFalse(Robots("User-agent: *\nDisallow: /中文").allows("http://a/%E4%B8%AD%E6%96%87"))
        self.assertTrue(Robots("User-agent: *\nDisallow:").allows("http://a/"))


class DisplayTests(unittest.TestCase):
    def test_untrusted_controls_and_cjk_width(self):
        self.assertNotIn("\x1b", safe("x\x1b[31m\u202ey"))
        self.assertNotIn("\u202e", safe("x\u202ey"))
        self.assertLessEqual(cell_width(clip("这是中文和 English", 10)), 10)
        self.assertTrue(all(cell_width(line) <= 8 for line in wrap("这是一段很长的中文 English", 8)))


if __name__ == "__main__":
    unittest.main()
