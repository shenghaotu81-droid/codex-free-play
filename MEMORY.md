# 仓库长期记忆

最后整理：2026-11-15。本文是新窗口的接续材料，不是已确认的产品规格。先读 AGENTS.md，再用 Git 和文件检查核实现场。

## 当前最重要的结论

**一分钟视觉自动兑换仿真的可运行第一版已完成并通过 CPU 验证。** 最新授权：“这些你说的不确定的都设计为可调的……如果你确定没啥问题就可以开始做了”。此前等待可行性批准的记录已过时。Ferry 保留为独立的已有项目。

最新明确范围：只模拟自动兑换一分钟；车辆周围若干存放框中已有矿石，机械臂沿写死的路径自动夹取、举升，视觉/算法判断合适时机令夹爪松开放入运动兑换框。环境应检验**整条算法闭环**，支持更换具体实现和公平对照，帮助用户反复调试、挑选算法。负责人主要负责依据具体场景建仿真环境；不明参数可调；原生桌面、无界面入口、真实 C++ 视觉桥接、算法插件与配对评测均已实现。不要重新索要开工许可。

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
| 一分钟视觉自动兑换的可替换算法验证环境 | 用户已明确范围和负责人职责：固定取料路径的机械臂＋存放框＋运动兑换框；整条算法可替换迭代。先确认可行性，用户确认后再实现 |

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

Ferry 接续命令（先 `cd projects/ferry`）：

```bash
python3 -m ferry --help
python3 -m ferry demo
python3 -m ferry demo --interactive
python3 -m unittest discover -s tests -v
python3 tests/terminal_smoke.py
python3 scripts/build_zipapp.py
python3 .local/dist/ferry.pyz --help
```

最后一次验证事实：

- 31 项单元/本地 HTTP 集成测试通过。
- 真实 curses 伪终端测试通过：选择、阅读、滚动、筛选、窗口缩放、状态切换和退出。
- 内置本地网站演示保存 11 个网址、9 个内容对象；包含故意的 404 和二进制跳过记录。
- 实际采集 `https://books.toscrape.com/` 的首页及两个详情页，3 页保存并通过校验。
- `projects/ferry/.local/captures/books`、`projects/ferry/.local/demos/demo-*` 和 `projects/ferry/.local/dist/ferry.pyz` 是本地忽略文件，不随 clone 出现；接续时检查是否仍存在，不要在 README 中承诺新 clone 自带这些数据。
- GitHub Actions 配置了 Python 3.10/3.12/3.13 的 CPU 测试。没有在本次对话中核实远端 CI 结果，不能声称全部版本已在本机跑过。

实现入口（相对于 `projects/ferry/`）：`ferry/core.py`（URL、文本提取、robots）、`crawler.py`（采集）、`archive.py`（存储与校验）、`cli.py`、`view.py`、`demo.py`。完整使用说明在 `projects/ferry/README.md`。

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

1. 优先接续已实现的一分钟视觉自动兑换仿真，围绕用户实拍、参数标定与新算法迭代。不要扩展全场比赛；先检查实际文件和测试状态。
2. 已进入实现阶段；用户提出新想法时保持开放，不把用户背景当成题材边界。
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
- 上一条为先前建议，已被用户最新范围收窄：**当前只做一分钟自动兑换，不扩展全场采集/运输**。只测试松爪判据也不足，目标是让检测、位姿、追踪、状态机、外环控制、投放决策及协议联调组成的整条算法可替换和迭代比较。
- 模型不明的行程、机构、延迟与运动分布需显式配置，仿真结果不替代实车验证；不要从场地示意图捏造精确全场尺寸。

资料提取与详细内部笔记放在本仓库被忽略的 `projects/exchange-sim/.local/research/`，不把外部规则原文、图纸或代码副本发布到本仓库。PDF读取库也只安装在 `projects/exchange-sim/.local/research/python`，运行时按需使用 `PYTHONPATH`；未改变全局依赖。新clone不带这些本地资料，应重新从授权源读取。

### 用户进一步说明与新增只读核对

- 存放框在车周围，拾取后的矿石已在其中；机械臂按固定路径从多个框取料并举到投放位置。视觉/算法判断跟随到位后请求松爪。仿真职责是建立场景/传感器/执行端/评测环境，不提前替用户锁死算法。
- 用户确认现有代码是核心检测逻辑，状态机、外环控制尚待编写；不得把既有视觉链描述成现成完整控制器。
- 已读 `Maixcam/串口通信协议/串口通信协议文档-v0.3.md`、`Maixcam/maixcdk-workflow.md`、2026-11-10框架草稿及规则设备清单。
- 型号来源应区分：上板记录写MaixCAM-Pro；协议v0.3写STM32控制侧与M2006/C610；规则清单和旧文有命名差异。文件出现的参考丝杆车SolidWorks模型不能自动当作用户最新机械臂的最终结构。
- 协议已描述车体速度/使能/机构许可、动作、模式、ACK、夹取事件、速度/状态反馈。新版机械臂循环中的投放位就绪、一次松爪、释放完成、库存等语义仍需明确；不能把ACK等同动作完成，或把机构许可默认为一次释放。
- 最终机械臂尺寸/投放口位置、相机安装关系、库存/动作反馈来源、运动与释放延迟尚未从已读资料得到完整确认。可用显式可替换参数建立模型，但不能宣称已知准确实物。
- 可行性结论应限定为：能在声明的成像、动力学、时序和机构模型下验证软件闭环、比较算法和发现失败域；实车可行性仍需参数辨识和真实测试。算法只看模拟传感器与协议反馈，真值仅供评分，场景固定种子便于公平对照。

## 2026-11-15 用户要求完整整理目录（包括隐藏文件）

- 两个项目已分开：`projects/ferry/`（原有完整爬虫）与 `projects/exchange-sim/`（仿真开发中）。根 README 导航，共用入口 `python3 run.py ferry ...` / `exchange ...` 会切换到项目目录，相对参数路径按项目解析。
- 原根目录的 5 个 `.ferry-demo-*` 已全部保留并迁至 `projects/ferry/.local/demos/demo-*`；`captures/` 与 `dist/` 迁至 Ferry 的 `.local/`。新演示、打包、测试也写入对应 `.local/`，避免再次污染根目录。
- 原 `.research-local/` 全部迁至 `projects/exchange-sim/.local/research/`，含 PDF 依赖、资料提取和内部笔记。不要将这个目录加入运行仿真的 PYTHONPATH，其中 numpy 与系统版本不同。
- `.git` / `.github` / `.gitignore` / `.gitattributes` 是仓库元数据与根配置，留在根；`.agents` / `.codex` / `.aws` 是环境提供的只读空目录，无项目资料，不擅自修改。
- 当前功能分支 `feat/exchange-sim`。仿真已写配置、CPU 成像/车辆/脚本机械臂/弹道评分内核、基线感知/控制、协议速度帧；C++ 适配器、运行入口、桌面界面和端到端验证仍待完成，不能宣称仿真已可交付。
- 外部视觉基线仍固定 `e25d4c98995fff395cf342f20b5fa1ef207a8afb`；外部工作区的未提交修改不参与本次构建。

整理后的验证：31 项 Ferry 单元/本地 HTTP 测试、真实终端交互测试均通过；重新打包并验证 `.local/dist/ferry.pyz --help`；通过根入口完整演示采集 11 网址/9 内容对象。根目录清单审计通过，两个历史 books 档案与研究/PDF 依赖均保留。演示回环服务因沙箱限制经工具原生提权后验证成功。

## 2026-11-15 完成可运行仿真第一版

用户对中途停工明确不满：“怎么就停下了？仿真做完了吗？你怎么搞得”。已承认把目录整理误当终点，并继续完成原仿真目标。以后用户插入整理、询问状态等是对正在进行任务的调整，不得当成取消或完成原目标。

交付目录 `projects/exchange-sim/`：

- 根入口 `python3 run.py exchange` 打开原生 Tk；默认 auto 检测已构建校园赛桥接，当前本机用真实 C++ 链，新 clone 无桥接用明确标注的 baseline。无显示可 `python3 run.py exchange --headless --video`。
- 场景 JSON 支持完整/部分覆盖；原有四类运动；相机 960x720、默认焦距900px/高度0.18m均为可调假设，MARK80mm几何。车辆平面运动、默认1ms执行器步长、脚本机械臂、继承投放点速度的弹道、真实落点开口评分。相机/算法默认30Hz。
- `scripts/build_campus_bridge.py` 通过 git show 提取指定提交，只在本项目 `.local/sources/`、`.local/build/` 构建；编译真实 Detector/PoseEstimator/TargetTracker。当前固定 e25d4c98995fff395cf342f20b5fa1ef207a8afb；60个源/配置文件只在忽略目录，未发布源码副本。
- `SensorPacket` 包含延迟原始BGR、可选感知输出、理想轮速里程计/IMU、机构阶段/库存及0x0015字节；`Command` 包含速度/单次释放，可传已有0x0001速度帧。插件 `make_policy(settings)` 能替换整条算法，`examples/image_policy.py` 已验证。真值/未来轨迹/seed不给算法；非恶意代码隔离，不是安全沙箱。
- 速度包实际走CRC、下行延迟/丢包、坏帧丢弃和100ms看门狗。尚未实现完整UART字节流、状态/模式/ACK重传等；新机械臂语义仍为显式仿真API。协议flags算例0x16与低两位01的描述矛盾，按位定义使用0x15，已记录在README。
- 示例控制器同步图像与自身里程计再估目标速度，含前馈/释放预测；不宣称这是用户已完成的真实控制器。`scripts/compare.py` 可比较自定义policy A/B，固定场景哈希，保留每次证据。
- `.local/runs/delivery/` 为最终完整60秒真实视觉链演示：seed7、噪声sigma1、6入框/6误投、实测1106/1800帧、库存耗尽；`demo.avi` 1360x900/15fps/900帧，另生成约1.5MB H264 `demo.mp4`。这些本地数据不随clone；README预览assets/preview.png从该视频取帧。
- `.local/runs/paired-final/` 为8次完整60秒真实C++链配对：关闭像素噪声，fixed两seed、两算法均12/12；random seed7 A预测6入6误、B响应0入12误；seed11 A7入4误仍夹1，B1入11误。仅两个种子的模型内对照，不是普遍优劣证明。验证记录已提交到项目docs/VALIDATION.md。
- `make test` 全部通过：Ferry31项+真实终端；仿真18项（含真实C++固定闭环/黑屏）；原生Tk桌面冒烟测试也通过。未启动浏览器或WebGL/GPU测试。完整测试中的本地HTTP需工具原生提权，沙箱拒绝后已成功重跑。GitHub Actions新增Python3.12仿真CPU测试；未声称远端CI已完成。
- 未实现CAD/关节接触碰撞、真实曝光纹理、机械臂自遮挡、Tag/RFID退出、完整比赛裁判和板端性能。默认几何/时延需实测标定；PC耗时不等于MaixCAM时延，显式注入camera.latency_s。

后续先读项目 README 与验证记录，用已存在入口实际运行；重点让用户换算法、用真实资料校准，不应重新从讨论/可行性阶段开始。所有临时资料/生成物继续写各项目.local，外部仓库和Windows资料始终只读。

Git 交付：实现提交 `6a284bd` 已推送 `feat/exchange-sim`，并快进合并、推送到 `main`；当前工作分支是 `main`。根目录随后出现编辑器自动生成的 `.vscode/settings.json`（CMake 源路径、含本机绝对路径），内容保留未修改，按个人编辑器配置加入忽略规则，不作为项目产物移动或发布。
