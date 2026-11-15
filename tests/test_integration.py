from contextlib import redirect_stdout, redirect_stderr
import gzip
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ferry.archive import Archive, select_pages, writer_lock
from ferry.cli import main, serialize
from ferry.crawler import Crawler
from ferry.demo import demo_site, page
from ferry.view import cell_width, screen_lines

ROOT = Path(__file__).resolve().parents[1]


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix=".ferry-test-", dir=ROOT)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def archive(self, seed, **overrides):
        config = {"seed": seed, "depth": 2, "include": "", "exclude": "", "contains": "",
                  "delay": 0, "timeout": 2, "max_bytes": 2 * 1024 * 1024, "max_queue": 100}
        config.update(overrides)
        return Archive(self.root / "archive", config=config)

    def test_real_crawl_dedup_robots_and_offline_search(self):
        with demo_site() as (seed, hits), self.archive(seed) as archive:
            stats = Crawler(archive).run(30)
            self.assertEqual(stats["counts"]["saved"], 11)
            self.assertEqual(stats["counts"]["error"], 1)
            self.assertEqual(stats["counts"]["skipped"], 1)
            self.assertEqual(stats["objects"], 9)
            self.assertNotIn("/private/secret", hits)
            self.assertIn("/private/public", hits)
            self.assertEqual(archive.verify(), [])
        # The server is gone. Search and verification must still work.
        with Archive(self.root / "archive") as archive:
            matches = select_pages(archive.rows(), query="SQLite 离线")
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]["title"], "Python 离线工具箱")
            self.assertNotIn("秘密脚本", "".join(r["text"] for r in archive.rows()))
            self.assertEqual(archive.verify(), [])

    def test_restart_preserves_frontier_and_does_not_refetch_saved(self):
        with demo_site() as (seed, hits):
            with self.archive(seed) as archive:
                first = Crawler(archive).run(3)
                self.assertEqual(first["counts"]["saved"], 3)
                self.assertGreater(first["counts"]["pending"], 0)
            with Archive(self.root / "archive") as archive:
                Crawler(archive).run(30)
                self.assertEqual(hits.count("/"), 1)
                self.assertEqual(hits.count("/about"), 1)
                self.assertEqual(hits.count("/robots.txt"), 2)
                Crawler(archive).run(1, retry_errors=True)
                broken = [r for r in archive.rows() if r["url"].endswith("/broken")][0]
                self.assertEqual(broken["attempts"], 2)

    def test_content_filter_still_follows_nonmatching_directory(self):
        with demo_site() as (seed, hits), self.archive(seed, contains="SQLite 离线") as archive:
            stats = Crawler(archive).run(30)
            self.assertEqual(stats["counts"]["saved"], 1)
            self.assertIn("/notes/", hits)
            self.assertIn("/notes/python", hits)
            rows = select_pages(archive.rows(), state="filtered")
            self.assertTrue(rows)
            self.assertTrue(all(not r["text"] and r["sha256"] is None for r in rows))

    def test_url_filters(self):
        with demo_site() as (seed, hits), self.archive(seed, include=r"/notes/", exclude="gardening") as archive:
            Crawler(archive).run(30)
            self.assertNotIn("/about", hits)
            self.assertNotIn("/notes/gardening", hits)
            self.assertIn("/notes/offline", hits)

    def test_depth_zero_does_not_follow(self):
        with demo_site() as (seed, hits), self.archive(seed, depth=0) as archive:
            Crawler(archive).run(30)
            self.assertEqual(hits, ["/robots.txt", "/"])
            self.assertGreater(archive.stats()["links"]["depth"], 0)

    def test_queue_budget_and_body_budget(self):
        with demo_site() as (seed, hits), self.archive(seed, max_queue=2) as archive:
            Crawler(archive).run(30)
            self.assertEqual(len(archive.rows()), 2)
            self.assertGreater(archive.stats()["links"]["queue-limit"], 0)

    def test_oversized_body_is_not_saved(self):
        with demo_site() as (seed, hits), self.archive(seed, max_bytes=20) as archive:
            Crawler(archive).run(30)
            self.assertEqual(archive.stats()["counts"]["skipped"], 1)
            self.assertEqual(archive.stats()["objects"], 0)

    def test_cross_origin_and_robots_redirect_are_blocked_before_fetch(self):
        with demo_site() as (other, other_hits):
            extra = {"/": page("root", "<a href='/escape'>out</a><a href='/forbidden'>private</a>"),
                     "/escape": (302, "text/html", b"", {"Location": other + "secret"}),
                     "/forbidden": (302, "text/html", b"", {"Location": "/private/secret"})}
            with demo_site(extra) as (seed, hits), self.archive(seed) as archive:
                Crawler(archive).run(30)
                self.assertEqual(archive.stats()["counts"]["blocked"], 2)
                self.assertNotIn("/private/secret", hits)
                self.assertEqual(other_hits, [])

    def test_robots_unavailable_keeps_frontier(self):
        extra = {"/robots.txt": (503, "text/plain", b"later", {})}
        with demo_site(extra) as (seed, hits), self.archive(seed) as archive:
            with self.assertRaisesRegex(ValueError, "robots.txt"):
                Crawler(archive).run(30)
            self.assertEqual(hits, ["/robots.txt"])
            self.assertEqual(archive.stats()["counts"]["pending"], 1)

    def test_robots_forbidden_blocks_root(self):
        extra = {"/robots.txt": (403, "text/plain", b"no", {})}
        with demo_site(extra) as (seed, hits), self.archive(seed) as archive:
            Crawler(archive).run(30)
            self.assertEqual(archive.stats()["counts"]["blocked"], 1)
            self.assertEqual(hits, ["/robots.txt"])

    def test_gzip_decompression_is_bounded(self):
        extra = {"/": (200, "text/html; charset=utf-8", gzip.compress(b"x" * 5000), {"Content-Encoding": "gzip"})}
        with demo_site(extra) as (seed, hits), self.archive(seed, max_bytes=100) as archive:
            Crawler(archive).run(30)
            self.assertEqual(archive.stats()["counts"]["skipped"], 1)
            self.assertEqual(archive.stats()["objects"], 0)

    def test_unknown_length_response_is_bounded(self):
        extra = {"/": (200, "text/html", b"x" * 5000, {"Content-Length": None})}
        with demo_site(extra) as (seed, hits), self.archive(seed, max_bytes=100) as archive:
            Crawler(archive).run(30)
            self.assertEqual(archive.stats()["counts"]["skipped"], 1)

    def test_truncated_response_is_not_archived(self):
        extra = {"/": (200, "text/html", b"short", {"Content-Length": "1000"})}
        with demo_site(extra) as (seed, hits), self.archive(seed) as archive:
            Crawler(archive).run(30)
            self.assertEqual(archive.stats()["counts"]["error"], 1)
            self.assertEqual(archive.stats()["objects"], 0)

    def test_interrupt_between_page_and_link_commit_is_atomic(self):
        with demo_site() as (seed, hits), self.archive(seed) as archive:
            crawler = Crawler(archive)
            with patch.object(crawler, "discover", side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):
                    crawler.run(30)
            self.assertEqual(archive.stats()["counts"]["pending"], 1)
            self.assertEqual(archive.stats()["counts"]["saved"], 0)
            Crawler(archive).run(30)
            self.assertEqual(archive.stats()["counts"]["saved"], 11)

    def test_verify_detects_corruption_and_missing_objects(self):
        with demo_site() as (seed, hits), self.archive(seed) as archive:
            Crawler(archive).run(3)
            rows = select_pages(archive.rows())
            archive.object_path(rows[0]["sha256"]).write_bytes(b"damaged")
            archive.object_path(rows[1]["sha256"]).unlink()
            self.assertEqual(len(archive.verify()), 2)

    def test_writer_lock_refuses_second_crawler(self):
        with self.archive("http://a/") as archive, writer_lock(archive.root):
            with self.assertRaisesRegex(ValueError, "已有采集进程"):
                with writer_lock(archive.root):
                    pass

    def test_cli_search_export_and_invalid_regex(self):
        with demo_site() as (seed, hits), self.archive(seed) as archive:
            Crawler(archive).run(30)
        dest = str(self.root / "archive")
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(["search", dest, "SQLite 离线", "--json"])
        self.assertEqual(code, 0)
        rows = json.loads(out.getvalue())
        self.assertEqual(len(rows), 1)
        file = self.root / "export.csv"
        with redirect_stderr(io.StringIO()):
            self.assertEqual(main(["export", dest, "离线", "--format", "csv", "-o", str(file)]), 0)
            self.assertEqual(main(["export", dest, "-o", str(file)]), 2)
            self.assertEqual(main(["search", dest, "--url", "["]), 2)
            self.assertEqual(main(["search", dest, "--state", "typo"]), 2)
        self.assertIn("sha256", file.read_text())
        self.assertIn("离线", file.read_text())

    def test_cli_crawl_and_stats_json(self):
        with demo_site() as (seed, hits):
            out = io.StringIO()
            with redirect_stdout(out):
                code = main(["crawl", seed, "-o", str(self.root / "archive"), "--depth", "0", "--delay", "0", "--json"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out.getvalue())["counts"]["saved"], 1)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(["stats", str(self.root / "archive"), "--json"]), 0)

    def test_narrow_and_full_terminal_rendering(self):
        with demo_site() as (seed, hits), self.archive(seed) as archive:
            Crawler(archive).run(3)
            for width, height in ((30, 8), (44, 14), (80, 24), (120, 40)):
                lines = screen_lines(archive.stats(), archive.rows(), 0, "", width, height)
                self.assertLessEqual(len(lines), height)
                self.assertTrue(all(cell_width(line) <= width for line in lines))

    def test_archive_refuses_overwrite_and_bad_digest(self):
        with self.archive("http://a/") as archive:
            with self.assertRaises(ValueError):
                archive.object_path("../../escape")
            with self.assertRaises(FileExistsError):
                self.archive("http://a/")

    def test_csv_prevents_scraped_formula_execution(self):
        row = dict.fromkeys(("id", "url", "final_url", "title", "text", "state", "status", "depth", "fetched_at", "sha256", "reason"), "")
        row["title"] = "=HYPERLINK(1)"
        self.assertIn("'=HYPERLINK(1)", serialize([row], "csv"))


if __name__ == "__main__":
    unittest.main()
