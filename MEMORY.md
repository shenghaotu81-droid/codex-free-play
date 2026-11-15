# 仓库长期记忆

最后整理：2026-11-15。本文是新窗口的接续材料，不是已确认的产品规格。先读 AGENTS.md，再用 Git 和文件检查核实现场。

## 当前最重要的结论

**现在讨论选题，不启动新产品实现。** 用户明确说“不要着急开始做”，希望负责人持续思考、查重、判断和讨论。Ferry 是已经可运行的第一阶段成果，尚未成为双方认可的长期主方向。

最新转向：用户觉得前述视觉方案可能太复杂，希望结合正在参加的 PnX 校内赛，依据规则场景讨论比赛仿真。已授权只读查看指定外部代码分支和 Windows 资料。当前已完成初步只读核对，尚未开始模拟器实现，用户尚未确认具体范围。更早的偏好仍是视觉优先；“视频变可编辑物理世界”候选已降级。

## 用户背景与合作方式

用户主动提供的背景：

- 香港科技大学（广州）大一学生。
- 方向：机器人 + AI，做视觉和导航，接触 ROS 2、SLAM、Nav2。
- 正在学习 C++、线性代数、Python。

用户给本仓库负责人的授权和期待：

- 最初为空仓库、仅 README；项目由负责人自行选择，做出可运行、可展示的成果。
- 自行组织分支、提交和 push，不必反复等待批准；工具权限限制仍需如实处理。
- 有独立判断和想象力，不能总把用户放在产品经理的位置。
- 背景提供能力和需求线索，**不要把选题锁死在机器人、导航、调试工具里**。
- 对话使用中文，讨论可以深入，不要一收到认同就立即开始写代码。

## 选题标准

用户明确要求：

1. 创新、有趣、有价值，要有实际用途。
2. 避免重做 GitHub 上已有的同类项目，可以从网络、论文和其他领域寻找灵感。
3. 技术应足够硬核；前面几次教学、轻量模拟和游戏化包装未满足期待。
4. 成品应像给人用的产品，而非只是一组命令、接口或技术能力。
5. 希望仓库能获得较多 GitHub Stars，重视宣传、演示 Demo 视频及传播。
6. 创意不能被当前代码、已有投入或之前提出的方案局限。
7. 最新偏好：更倾向视觉（“看”）而非音频（“听”）；希望都调研，未选定具体视觉产品。

讨论中获得用户大致认同的判断（负责人提出的工作假设，非额外硬性要求）：

- 看完演示会让人自然想到“我能不能拿它试试另一个东西”。
- 硬核技术能转化为用户可直接使用的创作或实验能力。
- 用户使用过程中产生可分享的作品、案例或实验结果，有利于持续传播。
- 第一眼的演示、第一次运行的回报、长期用途、社区贡献入口应一起考虑。
- 宣传需要演示证据；短视频呈现效果，长内容解释方法、对照实验及边界。

尚未确定：目标人群、产品形态、核心技术、最终项目名、宣传渠道与具体路线。没有确定增长目标数值，也没有承诺 Stars 结果。

## 操作与环境约束

- 仓库路径：`/home/tushenghao/projects/codex-free-play`。
- 用户明确要求不要越界超出仓库。文件、构建物、测试临时目录均放在仓库内。
- 后续明确例外：允许只读访问 `/home/tushenghao/projects/campus-marker-opencv-assignment` 的 `refactor/vision-lean-fixed` 分支，以及 `/mnt/d/Personal/Study/26-27Fall/PNX/校内赛`（Windows `D:\Personal\Study\26-27Fall\PNX\校内赛`）。不得修改这些项目/资料、切换外部仓库分支或执行会写源目录的构建/脚本。
- 用户明确说“网页版不要”。当前不能默认选择网页产品。
- 不在 WSL 中启动浏览器或运行 WebGL 测试，只做 CPU 验证。终端伪终端测试、本地 HTTP 测试已经使用过。
- 联网研究已获用户明确邀请。讨论、公开资料阅读与实际编码应区分。
- 沙箱可能禁止写 `.git` 或绑定回环端口；之前通过工具原生提权完成操作，不要规避权限。

## 已讨论方案及反馈

以下用于避免重复绕圈，不表示整个领域永久禁止：

| 方案 | 反馈或结论 |
| --- | --- |
| 像素生态瓶（网页 + 终端） | 用户说不要网页版，要求更有想象力 |
| 深海终端打捞游戏《深渊来信》 | 用户补充创意需要实用性与独特思考；未实施 |
| 中断后找回 Git 工作上下文的 Backmark | 用户明确觉得对自己用处不大；未实施 |
| 目录备份内容验收 Ferry | 做了一部分，用户转向网站采集；旧验收核心已被替换 |
| 网站采集与本地资料库《拾页 / Ferry》 | 按用户指定方向完成；用户认可基本功能已实现，继续寻找更好的方向 |
| 变化收件箱、采集配方、验收单、结构化提取 | 用户觉得仍不像给人用，要求跳出已有产品限制 |
| 数字修理铺、空间摆放、群体决策、小实验室、私人出版 | 发散候选，未获具体选中；不要把泛泛列举当成选题完成 |
| 机器人迷路博物馆、给机器人装修 | 用户认为不够硬核 |
| 导航反事实实验台 | 负责人提出技术路线；用户认为具体路线仍受局限，并强调宣传与演示。未接受为主方向 |
| 自动找导航失败场景、缩减反例、生成回归案例 | 负责人用于讨论产品结构的例子，未获具体路线认可；相关 fuzzing、故障缩减工作已存在 |
| 视频变可修改的物理世界 | 最新候选，用户认为“有点无聊”；不要继续替它辩护或直接实现 |
| 录音/口技→可编辑、可嵌入游戏的 DSP 发声程序 | 用户反馈更偏视觉，声音保留对照、降低优先级。逆合成与程序式音频已有强相关工作，尚未完成直接同类排除 |
| 可 fork 的 Demo：从演示的某个检查点接手运行、改变输入 | 新提出的候选，用户尚未反馈。VHS、Scrimba 等已覆盖部分核心体验；仅录屏或互动教学不构成差异 |
| 视觉发散：视觉奇观、直接操纵生成规律、新的视觉感知能力 | 本轮调研分类，尚不是产品方案；原始 Demo 与边界见 docs/IDEAS.md |
| 以对象为中心的跨视角接力播放器 | 本轮新机会假设，用户尚未反馈；跨视角实例对应与常规多机位剪辑都已有工作，未完成直接同类排除 |
| 基于自己校内赛规则的比赛模拟器 | 用户主动提出的新方向，希望降低复杂度并直接服务自己的比赛；已只读核对资料，未开始产品实现，具体范围未定 |

经常出现的对话失误：负责人反复缩窄到机器人诊断/仿真；堆技术词替代产品吸引力；过早提出一个新名字并承诺实现；反复让用户从列表中选。后续应给出更有判断的讨论，也允许承认并淘汰候选。

## 现有实现：拾页 / Ferry

已提交实现的基线：`241d5f7`，`Build Ferry website collector with searchable offline archives`。已通过 `feat/ferry` 开发并快进到 `main`，两者均曾推送 origin。这份记忆的提交会更新 HEAD，接续时查看当前状态。

远程：`git@github.com:shenghaotu81-droid/codex-free-play.git`。

功能：

- Python 3.10+ 标准库，CLI 和 curses 终端资料馆。
- 同源 BFS 采集；深度、请求数、队列数、单页大小、间隔和超时限制。
- include/exclude 网址正则，contains 内容保留筛选；未保留页面仍发现链接。
- 读取 robots，重定向每跳检查范围和策略；不执行 JavaScript。
- SQLite 持久队列和元数据；SHA-256 内容寻址原始页面对象、去重、完整性校验。
- 中文网址、常见编码；离线标题/正文关键词、状态及网址筛选。
- Markdown / JSON / CSV 导出，原始页面读取，交互选择和阅读。
- 不抓图片/CSS 等页面依赖，不处理 PDF、登录、验证码或 JS 渲染网页；不是完整网站镜像。

接续命令（仓库根目录）：

```bash
python3 -m ferry --help
python3 -m ferry demo
python3 -m ferry demo --interactive
python3 -m unittest discover -s tests -v
python3 tests/terminal_smoke.py
python3 scripts/build_zipapp.py
python3 dist/ferry.pyz --help
```

最后一次验证事实：

- 31 项单元/本地 HTTP 集成测试通过。
- 真实 curses 伪终端测试通过：选择、阅读、滚动、筛选、窗口缩放、状态切换和退出。
- 内置本地网站演示保存 11 个网址、9 个内容对象；包含故意的 404 和二进制跳过记录。
- 实际采集 `https://books.toscrape.com/` 的首页及两个详情页，3 页保存并通过校验。
- `captures/books`、`.ferry-demo-*` 和 `dist/ferry.pyz` 是本地忽略文件，不随 clone 出现；接续时检查是否仍存在，不要在 README 中承诺新 clone 自带这些数据。
- GitHub Actions 配置了 Python 3.10/3.12/3.13 的 CPU 测试。没有在本次对话中核实远端 CI 结果，不能声称全部版本已在本机跑过。

实现入口：`ferry/core.py`（URL、文本提取、robots）、`crawler.py`（采集）、`archive.py`（存储与校验）、`cli.py`、`view.py`、`demo.py`。完整使用说明在 README.md。

## 已查到的相关工作

这些链接是已有工作的线索，不是对功能、维护状态、Star 数或项目差异的永久保证。需要使用时重新核实。相关思想已有，不应包装成我们的独创。

- Czkawka：https://github.com/qarmin/czkawka
- rclone check：https://rclone.org/commands/rclone_check/
- SLAMLab：https://github.com/Kanishk-Rungta/SLAMLab
- NavigationAnalyzer：https://github.com/rsasaki0109/NavigationAnalyzer
- Hardware Troubleshooting Detective：https://dmccreary.github.io/stem-robots/sims/hardware-troubleshooting-detective/
- RoboFuzz：https://github.com/sslab-gatech/RoboFuzz
- ROCF 生命周期并发测试/复现论文：https://ieeexplore.ieee.org/document/11095749/
- 环境修改解释规划失败：https://kclpure.kcl.ac.uk/ws/files/248844611/icra2024_motion_planning_env_explanations.pdf
- MetaLiDAR：https://doi.org/10.1002/smr.2644
- MultiTest：https://arxiv.org/abs/2401.14314
- 视觉定位标记布局：https://www.josephdegol.com/docs/MarkerPlacement_RAL23_Paper.pdf
- 自动环境缩减：https://merielvonstein.com/files/publications/ICRA2021-DDEnv.pdf
- PythonRobotics：https://github.com/AtsushiSakai/PythonRobotics
- LeRobot：https://github.com/huggingface/lerobot
- Genesis：https://github.com/Genesis-Embodied-AI/genesis-world
- 自主空仓库孵化：Autonomous-Forge，https://github.com/OmarH-creator/Autonomous-Forge 。与本仓库起点、代理长期记忆和自主维护叙事非常近，故不将该叙事直接当新产品原创点。
- 程序化终端演示：VHS，https://github.com/charmbracelet/vhs
- 可交互编程录屏：Scrimba，https://docs.scrimba.com/explain/scrims
- 固定合成器参数逆推：INSTRUMENTAL，https://github.com/philippbogdan/instrumental
- 可微模态声音/逆设计：DiffSound，https://github.com/TechnetiumMan/DiffSound
- DSP Programming by Example 原论文：https://www.cs.yale.edu/homes/piskac/papers/2018SantolucitoETALdsp-pbe.pdf
- DDSP-SFX：https://arxiv.org/abs/2309.08060
- Visual Anagrams：https://dangeng.github.io/visual_anagrams/
- pEt 参数化纹样直接操纵：https://marzia-riso.github.io/pet.html
- Meschers 不可能物体几何：https://anadodik.github.io/publication/meschers/
- ObjectRelator 跨视角对象对应：https://yuqianfu.com/ObjectRelator/
- CornerCameras 墙角间接光成像：https://people.csail.mit.edu/klbouman/cornercameras.html
- Motion Vectorization 动效转 SVG 程序：https://arxiv.org/abs/2309.14642

2026-11-15 后续发散研究：机械轨迹逆设计、影子雕塑、视频恢复声音、触感逆设计等均查到直接相关实现，没有把它们作为已证实原创的候选。详细的新候选与风险见 `docs/IDEAS.md`。本轮未进行新产品实现。

查重原则：检索不到不能证明原创；区分底层库、相关论文与直接同类成品；有相邻工作时说明拟解决的具体差异。此前没有任何新候选完成原创性或可行性验证。

## 下一轮从哪里接

1. 优先接续用户提出的 PnX 比赛仿真讨论；参考下方只读调研记录。不要自动回到泛视觉/音频候选，不把本轮建议当作已经确认的开发任务。
2. 继续开放讨论，避免立即编码，也不要再把用户背景当成题材边界。
3. 优先讨论具体的新体验、实际价值、技术难点和可传播的演示，允许淘汰不够吸引人的想法。
4. 对新获得的反馈更新本文，保留未决事项，勿把负责人的偏好当作双方已经选定。

最近技术讨论：用户问三个视觉方向需要的技术。已把算法、候选桌面栈、CPU/GPU边界和易误判事项追加到 `docs/IDEAS.md` 第4节。没有选定路线、没有安装依赖、没有启动新实现；CPU可行性说明是缩小范围后的工程判断，不是已跑性能测试。

## PnX 比赛仿真：只读调研接续

外部代码读取基线为 `refactor/vision-lean-fixed` 的 `e25d4c98995fff395cf342f20b5fa1ef207a8afb`。工作区当时在该分支且存在大量未提交修改，分析使用 `git show` 的已提交内容；不能将工作区改动当成已提交基线，也不能擅自覆盖。

已读：分支的 `src/tushenghao/README.md`、`docs/flow-guide.md`、公开类型与配置、`tests/app/offline/offline_chain_test.cpp`、测试绘制夹具；Windows 目录的最新 `规则与指南/PnX校内赛规则手册_V1.0.4.pdf`（文字与关键场地图/尺寸图）、225路线图及无硬件阶段终稿。没有逐一打开全部视频和CAD。

关键结论：

- 指定分支已有 C++17/OpenCV 的真实检测→平面IPPE位姿→相机系CV跟踪，以及合成BGR视频贯穿该链路的测试；这是一块可复用起点，但不等于已有比赛闭环控制器。
- 现有离线CLI仅接受视频参数、配置目录固定；不能为仿真随意改外部配置。以后若实现实时桥接，应在本仓库写薄适配器，遵守只读授权。
- 旧225开发路线针对旧规则与旧代码；当前规则及代码需独立核对，不能照搬旧长方案里的接口、数字或已完成状态。
- 仿真应由真实算法消费模拟图像/测量，控制命令改变模拟车辆、进而改变下一帧；评分真值独立保存。视频回放只能测感知，不代表控制闭环。
- 当前建议（未确认）：视觉化比赛沙盘与局部兑换相机联动。第一阶段优先局部兑换任务，之后扩展全场采集、运输与计分；刚体接触、真实夹取和复杂地形动力学留待具体需求验证。
- 模型不明的行程、机构、延迟与运动分布需显式配置，仿真结果不替代实车验证；不要从场地示意图捏造精确全场尺寸。

资料提取与详细内部笔记放在本仓库被忽略的 `.research-local/`，不把外部规则原文、图纸或代码副本发布到本仓库。PDF读取库也只安装在 `.research-local/python`，运行时按需使用 `PYTHONPATH`；未改变全局依赖。新clone不带这些本地资料，应重新从授权源读取。
