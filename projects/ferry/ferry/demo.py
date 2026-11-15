"""An actual HTTP miniature site, including redirects, failures, robots and duplicates."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading


def page(title, body):
    return f'<!doctype html><html lang="zh"><meta charset="utf-8"><title>{title}</title><main>{body}</main></html>'.encode()


OFFLINE = page("把知识留在本地", "<h1>离线阅读指南</h1><p>离线资料库保存原始网页与正文，断网后也能检索。内容指纹让重复页面共用一份存储。</p><p>先采集，再筛选，最后把有用的内容导出成 Markdown。</p><script>秘密脚本内容，不应出现在正文</script>")

PAGES = {
    "/": page("潮汐资料站", """<h1>潮汐资料站</h1><p>一个用于检验采集工具的小网站。</p>
      <a href='/notes/'>进入笔记</a> <a href='/about'>关于我们</a>
      <a href='/mirror'>另一份离线指南</a> <a href='/jump'>重定向入口</a>
      <a href='/private/secret'>私人区域</a> <a href='/private/public'>允许的公开页</a>
      <a href='/broken'>失效链接</a> <a href='/download.bin'>二进制附件</a>
      <a href='https://example.invalid/outside'>外站</a><a href='/#top'>回到顶部</a>"""),
    "/notes/": page("笔记目录", """<h1>笔记目录</h1><a href='offline'>离线阅读</a>
      <a href='gardening'>阳台种菜</a><a href='python'>Python 工具</a>
      <a href='编码'>中文路径</a><a href='/legacy'>旧编码网页</a>"""),
    "/about": page("关于潮汐", "<h1>每一页都值得被好好保存</h1><p>网址会失效，内容需要出处。让收藏从一串链接变成自己的资料。</p>"),
    "/notes/offline": OFFLINE,
    "/mirror": OFFLINE,
    "/notes/gardening": page("阳台种菜日记", "<h1>薄荷与番茄</h1><p>记录浇水、光照与土壤湿度。夏季早晨浇水，避免中午暴晒。</p>"),
    "/notes/python": page("Python 离线工具箱", "<h1>用标准库构建离线工具</h1><p>Python 的 SQLite 和 HTMLParser 可以实现轻量资料库。这个网页提到离线与 Python。</p>"),
    "/notes/%E7%BC%96%E7%A0%81": page("中文网址测试", "<h1>中文内容不会丢</h1><p>中文网址、UTF-8 编码和标点，都应该能完整保存。</p>"),
    "/private/public": page("公开的例外", "<p>robots.txt 中更具体的 Allow 可以开放这个页面。</p>"),
}


@contextmanager
def demo_site(extra=None):
    hits = []
    routes = dict(PAGES)
    routes.update(extra or {})

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            hits.append(self.path)
            status, mime, body, headers = 200, "text/html; charset=utf-8", b"", {}
            if extra and self.path in extra:
                item = extra[self.path]
                if isinstance(item, tuple):
                    status, mime, body, headers = item
                else:
                    body = item
            elif self.path == "/robots.txt":
                mime, body = "text/plain", b"User-agent: *\nDisallow: /private/\nAllow: /private/public\n"
            elif self.path == "/jump":
                status, headers = 302, {"Location": "/notes/offline"}
            elif self.path == "/download.bin":
                mime, body = "application/octet-stream", b"not a document"
            elif self.path == "/legacy":
                mime = "text/html; charset=gb18030"
                body = '<title>旧编码也能读</title><p>这是一份 GB18030 编码的离线文档。</p>'.encode("gb18030")
            elif self.path in routes:
                item = routes[self.path]
                if isinstance(item, tuple):
                    status, mime, body, headers = item
                else:
                    body = item
            else:
                status, body = 404, b"not found"
            self.send_response(status)
            self.send_header("Content-Type", mime)
            if "Content-Length" not in headers:
                self.send_header("Content-Length", str(len(body)))
            for key, value in headers.items():
                if value is not None:
                    self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/", hits
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
