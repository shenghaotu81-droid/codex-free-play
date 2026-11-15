# 拾页 / Ferry

**爬下来，留下来，再慢慢筛。** 一个可以直接跑的网站采集与离线资料工具。

将教程、博客或文档站采集成本地档案，按网址、标题和正文筛选，导出一份带来源的 Markdown、JSON 或 CSV。所有功能都在终端完成；运行只需要 **Python 3.10+ 标准库**，无需安装依赖、浏览器、WebGL 或模型服务。支持 Linux、macOS 和 WSL。

## 一分钟体验

在仓库根目录执行：

```bash
python3 -m ferry demo
```

它会临时启动一个只监听 `127.0.0.1` 的小网站，真实执行采集 → 暂停 → 重开档案续爬 → 筛选 → 导出 → 校验，随后自动关闭网站。文件留在仓库的 `.ferry-demo-*/` 中，命令会打印具体位置。

想直接体验交互界面：

```bash
python3 -m ferry demo --interactive
```

`↑↓` 或 `j/k` 选择，`Enter` 阅读，`/` 输入关键词，`a` 切换全部/已保存状态，`q` 返回或退出。阅读时空格翻页。终端建议至少 80 × 24；支持中文宽度处理和窗口缩放。

演示预期结果：**11 个已保存网址，9 个内容对象**；另有一个故意失效的链接和一个跳过的二进制附件。搜索“离线”得到 7 条记录。三个不同网址的离线指南只保存一份原始内容，仍分别保留来源。演示命令成功返回 0，故意制造的 404 会在结果中如实列出。

## 采集真实网站

```bash
# 新档案目录必须不存在。默认同源站内爬取，深度 2，本次最多请求 30 页。
python3 -m ferry crawl https://example.com/ -o captures/example

# 可实际体验的公开爬虫练习站：只跟随书籍详情页，本次请求 3 页。
python3 -m ferry crawl https://books.toscrape.com/ -o captures/books \
  --include '/catalogue/[^/]+_[0-9]+/index.html$' --max-pages 3 --depth 1

# 只跟随 /docs/ 中的链接，排除搜索页；起始页不受 include 限制。
python3 -m ferry crawl https://example.com/ -o captures/docs \
  --include '/docs/' --exclude '/search|[?]' --depth 3 --max-pages 100

# 只保存同时包含两个关键词的页面，其余页面仍提取链接。
python3 -m ferry crawl https://example.com/ -o captures/offline \
  --contains 'Python 离线' --delay 1

# 达到数量限制或 Ctrl+C 后，队列留在档案中。
python3 -m ferry resume captures/example --max-pages 50
python3 -m ferry resume captures/example --retry-errors
```

起始页深度为 0；数量限制是**本次页面任务数**，robots 请求与重定向跟随请求另计。队列容量默认累计 5,000 个网址，每页至多提取 2,000 条链接。可用 `--max-queue`、`--max-bytes`、`--timeout` 调整限制。默认单页解压后最大 2 MiB，单次网络阻塞超时 10 秒；超时并非整个任务的总时限。串行请求默认间隔 0.5 秒。

同源严格要求协议、域名和端口相同；站外链接仅登记，不访问。重定向的**每一跳**都要通过同源、网址规则和 robots 检查。HTTP 跳转到 HTTPS 或另一个域名时，请直接以最终网址为起点。

## 离线筛选与阅读

```bash
python3 -m ferry stats captures/example
python3 -m ferry search captures/example 'Python 离线'
python3 -m ferry search captures/example --url '/docs/' --title '教程|指南' --min-chars 200
python3 -m ferry search captures/example --state error,skipped --limit 0
python3 -m ferry search captures/example --state all --json
python3 -m ferry read captures/example 3
python3 -m ferry browse captures/example
```

关键词忽略大小写，空格分隔时采用 AND 匹配，范围是标题与正文。它是可解释的子串筛选，不依赖语义模型；网址、标题规则使用 Python 正则。默认只搜 `saved`，至多 20 条；`--limit 0` 显示全部。筛选条件可以组合，整个过程无需联网。

页面状态：

| 状态 | 含义 |
| --- | --- |
| `saved` | 原始内容和正文均已保存 |
| `pending` | 尚未执行，下次续爬继续 |
| `filtered` | 已访问并提取链接，但关键词不匹配，未保留正文或原始内容 |
| `blocked` | robots 或重定向范围限制拦截 |
| `skipped` | 非支持的内容类型、响应超大或不支持的压缩格式 |
| `error` | HTTP 错误、超时或网络故障，可明确选择重试 |

发现阶段就被网址规则、robots、深度或队列限制排除的链接，记录在数据库的 `links` 表中，不进入页面队列。`stats --json` 可查看各类链接数量和完整配置。

## 导出与校验

```bash
python3 -m ferry export captures/example '离线' --format md -o collection.md
python3 -m ferry export captures/example --url '/docs/' --format json -o pages.json
python3 -m ferry export captures/example --format csv -o pages.csv

# 将某页恢复成原始 HTML；归档本身不执行其中的脚本。
python3 -m ferry read captures/example 3 --raw > page.html

# SQLite 完整性检查 + 每个原始对象的 SHA-256 与大小校验。
python3 -m ferry verify captures/example
```

导出默认不限制条数，支持与 search 相同的筛选条件；输出文件已存在时拒绝覆盖。省略 `-o` 时写标准输出，可用于管道。CSV 对公式起始字符做保护；终端显示会转义页面中的控制字符。

归档结构：

```text
captures/example/
├── archive.sqlite3        # 网址、标题、正文、状态、出处、链接、配置、持久队列
├── .writer.lock           # 防止同时有两个采集进程写同一档案
└── objects/ab/abcdef.raw  # SHA-256 寻址的原始页面内容（gzip 已解压）
```

整个文件夹可以直接复制、备份和离线使用。相同原始内容只写一个对象；每个网址的元数据与正文独立保留。页面保存和新链接入队在同一数据库事务中提交；未完成的任务仍是 `pending`。极端中断可能留下未引用的对象，不影响已提交档案。`verify` 检验数据库结构和被引用的原始对象，不证明网站内容真实或数据库字段没有被人为篡改。

## 范围与设计取舍

- 处理服务端返回的 HTML、纯文本、JSON 和 XML；提取 HTML 标题、可见文本和链接，支持中文网址、UTF-8、GB18030、BOM 与 HTML charset。脚本、样式及模板不进入正文。
- 不执行 JavaScript，不下载页面依赖的图片/CSS，不处理 PDF、登录、验证码或浏览器渲染页面。HTML 是原始存档，正文用于离线阅读；这不是完整网站镜像。
- 每次采集/续爬重新读取 `robots.txt`，支持最具体的 User-agent 分组、最长路径匹配、Allow 优先、`*`、`$` 和 Crawl-delay；403/401 禁止采集，5xx、429 或网络故障时停止，保留队列。
- include/exclude 控制**遍历**；contains 控制**保留**。这两者独立，目录页不匹配内容关键词时，仍能找到深处的文章。
- 已保存的页面不会在 resume 时重抓；想重新采集更新版本，创建新档案。续爬保留原配置。抓取记录包含失败原因，达到预算不等于全站已采集。

选择这个方向，是希望“收藏网址”能落到一份有出处、能搜索、能带走的资料上。项目从备份验收思路转向采集，保留了其中的内容寻址、去重和完整性校验设计。

实现参考：[Python urllib.request](https://docs.python.org/3/library/urllib.request.html)、[HTMLParser](https://docs.python.org/3/library/html.parser.html)、[Robots Exclusion Protocol / RFC 9309](https://www.rfc-editor.org/rfc/rfc9309.html)。备份校验与内容分组的早期灵感来自 [rclone check](https://rclone.org/commands/rclone_check/) 和 [Czkawka](https://github.com/qarmin/czkawka)。代码为本仓库实现。

## 开发与单文件分发

```bash
python3 -m unittest discover -s tests -v
python3 scripts/build_zipapp.py
python3 dist/ferry.pyz --help
python3 dist/ferry.pyz demo
```

测试全部使用 CPU 和本地回环 HTTP；不启动浏览器，不用 WebGL，不访问外网，临时文件只写在仓库内。交互界面还可通过 `tests/terminal_smoke.py` 在伪终端中验证。构建出的 `.pyz` 包含整个程序，只需 Python 3.10+ 就能运行。

退出码：`0` 命令成功（可能仍有 pending/filtered/skipped/blocked）；`1` 采集档案中有请求错误，或 verify 发现损坏；`2` 参数、配置或运行环境错误；`130` 用户中断。`search` 没结果返回 0。

MIT License。
