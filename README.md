# Huawei Training Camp MCP

把你的**华为运动健康数据**接入 AI——让 Claude、Cherry Studio 等 AI 客户端
直接查询并分析你的训练记录、睡眠、心率、跑力，像和一个懂训练的教练聊天一样。

[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-blue)]()
[![Tests](https://img.shields.io/badge/tests-317%20passed-brightgreen)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **安全边界**：本项目不绕过验证码、二次验证或其他访问控制。用户本人
> 在专用 Edge 配置中打开可用的 Huawei Training Camp 页面；程序只捕获该页面
> 正常发出的成功请求。凭证由 Windows DPAPI 加密保存在本机用户目录，不写入
> 代码、仓库或普通日志。原环境变量认证方式继续可用。

---

## 目录

- [这是什么？能干嘛？](#这是什么能干嘛)
- [开始之前：你需要准备什么](#开始之前你需要准备什么)
- [五步上手教程](#五步上手教程)
  - [第 1 步：安装 Python](#第-1-步安装-python)
  - [第 2 步：下载本项目并安装依赖](#第-2-步下载本项目并安装依赖)
  - [第 3 步：获取华为凭证（关键步骤）](#第-3-步获取华为凭证关键步骤)
  - [第 4 步：连通性自检](#第-4-步连通性自检)
  - [第 5 步：接入你的 AI 客户端](#第-5-步接入你的-ai-客户端)
- [怎么用：可以问 AI 的问题](#怎么用可以问-ai-的问题)
- [功能一览（14 个 MCP 工具）](#功能一览14-个-mcp-工具)
- [排障：401 / 认证过期](#排障401--认证过期)
- [常见问题 FAQ](#常见问题-faq)
- [开发](#开发)
- [已验证的真实 API 契约（摘要）](#已验证的真实-api-契约摘要)
- [许可证与免责声明](#许可证与免责声明)

---

## 这是什么？能干嘛？

你戴着华为手表 / 手环运动，数据都同步在华为运动健康里，但想分析时只能在
App 里一屏屏翻。本项目把这些数据变成 **AI 能直接调用的工具**（MCP，
Model Context Protocol——一个让 AI 安全使用外部数据的标准协议）。

接入后，你可以直接对 AI 说：

- "我最近 4 周跑量 trend 怎么样？和上个月比呢？" → AI 调用周趋势 + 环比工具
- "分析一下我昨天那次间歇跑的心率曲线" → AI 调用训练详情 + 统计摘要
- "我最近睡眠质量如何？静息心率有没有异常？" → AI 调用睡眠 / 静息心率工具
- "我现在跑力多少？预测我半马能跑多少？" → AI 调用运动能力评估工具

本地 MCP 服务直接向华为接口取数。你在 AI 客户端中请求分析时，客户端会把
相关数据提供给你配置的模型服务；使用云端模型时，请留意该服务的隐私设置。

## 开始之前：你需要准备什么

| # | 需要什么 | 说明 |
|---|---|---|
| 1 | 华为设备 + 账号 | 手表 / 手环 + 华为运动健康 App，并能在电脑浏览器打开自己实际使用且可访问训练数据的 Huawei Training Camp 页面 |
| 2 | 一台电脑 + Python 3.12 或更高 | 下文的自动登录与加密存储流程适用于 Windows，并需要安装 Microsoft Edge；Mac / Linux 可使用环境变量兼容模式 |
| 3 | 一个支持 MCP 的 AI 客户端 | 如 **Cherry Studio**（免费、对中文用户友好）、Claude Desktop 等 |

> 不需要会编程——下面每一步都是复制粘贴级别的内容。
> 需要的只是按顺序做完五步。

## 五步上手教程

### 第 1 步：安装 Python

1. 打开 [python.org/downloads](https://www.python.org/downloads/)，下载
   **Python 3.12 或更高版本**的安装包（Windows 点黄色大按钮即可）；
2. 运行安装包，**务必勾选最底部的 `Add Python to PATH`**（不勾后面会报
   "'python' 不是内部或外部命令"），然后点 Install Now；
3. 验证：按 `Win + R`，输入 `powershell` 回车，在蓝底窗口输入：

   ```powershell
   python --version
   ```

   显示 `Python 3.12.x`（或更高）即成功。

### 第 2 步：下载本项目并安装依赖

1. 在本仓库页面点绿色的 **Code → Download ZIP**，解压到任意目录
   （本文以 `C:\huawei-health-mcp` 为例；会 Git 的同学直接 `git clone` 更好，
   方便以后更新）；
2. 打开 PowerShell（`Win + R` → 输入 `powershell` 回车），逐行粘贴执行：

   ```powershell
   cd C:\huawei-health-mcp                 # 进入项目目录（按你的实际解压路径改）
   python -m venv .venv                    # 创建独立的运行环境（约 30 秒）
   .\.venv\Scripts\pip install -r requirements.txt   # 安装依赖（约 1~2 分钟）
   ```

3. 装完先跑一遍自带测试（不需要任何凭证，验证环境没问题）：

   ```powershell
   .\.venv\Scripts\python.exe -m pytest -q
   ```

   最后显示测试通过即环境就绪。

### 第 3 步：获取华为凭证（关键步骤）

首次配置或需要重新授权时，在项目目录运行：

```powershell
.\.venv\Scripts\python.exe -m scripts.auth_login
```

程序会打开独立 Edge 配置。请在该窗口中手动打开你已确认可访问数据的
Huawei Training Camp 页面，并查看训练记录。不要把密码、验证码或请求头发给
程序或聊天。观察到成功的训练接口请求后，程序只把必要请求头写入 DPAPI
加密文件 `%LOCALAPPDATA%\HuaweiTrainingCampMCP\credentials.dpapi`，不会显示值。

查看本机凭证状态（不发起网络请求）：

```powershell
.\.venv\Scripts\python.exe -m scripts.auth_status
```

原来的 `HTC_AUTHORIZATION` / `HTC_CLIENT_ID` 环境变量仍作为兼容回退方式，
可在无法使用 DPAPI 的系统上继续使用。

### 第 4 步：连通性自检

完成第 3 步的 Windows 授权后，在项目目录执行：

```powershell
.\.venv\Scripts\python.exe -m scripts.test_dpapi_mcp
```

看到 `DPAPI_MCP_CHECK=SUCCESS`，表示服务列出了 14 个工具，且用当前
Windows 用户加密保存的凭证完成了一次真实训练查询。此脚本不会打印训练数据。

如果你使用的是环境变量兼容模式，可改用
`.\.venv\Scripts\python.exe scripts\test_real_htc.py` 验证。该旧脚本只读取
`HTC_*` 环境变量，不读取 DPAPI 凭证，并可能在本地 `data_temp/` 保存真实响应。

使用环境变量兼容模式时，还可用旧脚本运行以下自检（可选）：

```powershell
.\.venv\Scripts\python.exe scripts\test_real_htc.py sleep 7         # 最近 7 晚睡眠
.\.venv\Scripts\python.exe scripts\test_real_htc.py resting-hr 28   # 28 天静息心率
.\.venv\Scripts\python.exe scripts\test_real_htc.py hrv 28          # 28 天 HRV
.\.venv\Scripts\python.exe scripts\test_real_htc.py performance     # 跑力与预测成绩
.\.venv\Scripts\python.exe scripts\test_real_htc.py pb              # 个人纪录
.\.venv\Scripts\python.exe scripts\test_real_htc.py trend 8         # 8 周训练趋势
```

### 第 5 步：接入你的 AI 客户端

以 **Cherry Studio** 为例（Claude Desktop 等同理，都在 MCP / 工具设置里）：

1. 打开 设置 → MCP 服务 → 添加（或"+"新建）；
2. 类型选 **stdio**，按下表填写：

| 配置项 | 填什么 |
|---|---|
| 名称 | `huawei-training-camp`（随意） |
| 命令 | `C:\huawei-health-mcp\.venv\Scripts\python.exe`（你项目里的实际路径） |
| 参数 | `-m src.huawei_health_mcp.server` |
| 工作目录 | `C:\huawei-health-mcp` |

JSON 配置（部分客户端直接编辑配置文件；适用于完成第 3 步的 Windows 用户）：

```json
{
  "mcpServers": {
    "huawei-training-camp": {
      "command": "C:\\huawei-health-mcp\\.venv\\Scripts\\python.exe",
      "args": ["-m", "src.huawei_health_mcp.server"],
      "cwd": "C:\\huawei-health-mcp"
    }
  }
}
```

使用环境变量兼容模式时，须由用户本人在本机设置 `HTC_AUTHORIZATION` 与
`HTC_CLIENT_ID`，并让 MCP 子进程继承它们。不要把真实请求头写入分享的配置
文件或提交到 GitHub。

3. 保存并启用该服务，客户端里应该能看到 14 个工具（`health_check`、
   `get_recent_activities` 等）；
4. 开个对话直接问："帮我看看最近两周的训练情况"——AI 会自己调用工具。

## 怎么用：可以问 AI 的问题

- **训练回顾**："我最近 7 天练了多少？和上一个 7 天比呢？"
- **单次分析**："分析我昨天那次跑步的心率和配速。"
- **长期趋势**："最近 8 周跑量趋势如何？哪周练得最猛？"
- **恢复状态**："我最近睡眠怎么样？静息心率正常吗？HRV 呢？"
- **能力评估**："我现在的跑力是多少？预测全马成绩？我的 5 公里 PB 是什么时候跑的？"

> 提示：不需要记工具名——直接用自然语言说需求，AI 自己选工具。

## 功能一览（14 个 MCP 工具）

| 工具 | 说明 |
|---|---|
| `health_check` | 服务连通性检查 |
| `get_recent_activities(limit=5, lookback_days=30)` | 最近训练列表（活动 id / 时间 / 类型 / 距离 / 心率 / 配速 / VO2max / 训练负荷等摘要） |
| `get_activity_detail(activity_id, lookback_days=30)` | 单次训练高频采样详情（心率 / 速度 / 步频 / 海拔 / 位置 / 跑姿，通用 field-value 结构） |
| `get_training_summary(activity_id, lookback_days=30)` | 单次训练确定性统计摘要（每采集器样本数 / 时间范围 / 各字段 min-max-avg-first-last），无 AI 推断 |
| `get_session_metrics(activity_id, lookback_days=30)` | 单次训练核心指标（时长 / 心率 / 速度 / 配速 / 距离，带 device_summary/samples 来源标记） |
| `get_training_period_summary(lookback_days=7, limit=100)` | 一段周期内多次训练聚合（次数 / 总距离 / 总历时 / 平均与最大单次 / 心率 / 卡路里 / 累计爬升下降 / 步数 / 按 activityType 分组），类型值原样保留不命名语义；另含总纯运动时长与周期平均配速 |
| `get_training_period_comparison(window_days=7, limit=100)` | 两个连续周期对比：最近 N 天 vs 之前 N 天（每指标 baseline / current / delta / percentage_change；缺失≠0，不除零） |
| `get_training_weekly_trend(weeks=4, limit=100)` | 最近 N 个连续周窗口的训练量趋势（滚动 7 天窗口、不重叠；每周完整周期聚合） |
| `get_training_weekly_trend_delta(weeks=4, limit=100)` | 相邻周环比（older → newer，最多 weeks-1 对；weeks=1 返回空数组） |
| `get_sleep_records(days=14)` | 最近 N 天睡眠记录（每晚：上床/入睡/醒来时刻，浅睡/深睡/快速眼动/清醒分钟，总睡眠、得分、效率、入睡用时、夜醒次数；服务端解析口径） |
| `get_resting_heart_rate(days=28)` | 最近 N 天静息心率统计（服务端聚合：全窗口 avg/max/min/count + 按天明细；fieldName=restBpm，bpm） |
| `get_hrv_stats(days=28)` | 最近 N 天 HRV 统计（服务端聚合：全窗口 + 按天明细；fieldName=avgHrv，数值原样返回——华为未声明单位与算法口径，不擅自换算） |
| `get_athletic_performance()` | 最新运动能力评估（跑力指数 / 状态 / 健康 / 疲劳 / 排名 + 1/3/5/10 公里·半马·全马预测成绩秒数；服务端口径） |
| `get_personal_bests(activity_type='running')` | 单运动类型个人纪录（name/value/达成起止时间；value 单位由华为定义——时间为秒、距离为米，原样返回） |

参数说明：

- `get_recent_activities` 的心率是设备汇总值；列表接口可能不返回逐点心率，
  因而 `heart_rate_samples` 为空不代表华为没有心率曲线。先取活动 id，再调用
  `get_training_summary` 查看采样覆盖，或用 `get_activity_detail` 获取逐点数据。
  某些设备可能返回 `0 bpm` 等无效瞬时值；解读时应检查并排除。
- `lookback_days`：查询窗口天数，默认 30，范围 1~730；查更早的训练时调大。
- `days`：恢复状态类窗口天数（睡眠默认 14，心率 / HRV 默认 28）。
- `weeks`（周趋势）：周窗口数，默认 4，范围 1~104；滚动 7 天连续窗口
  （非自然周），单次列表请求整个跨度后本地归窗。
- `window_days`（周期对比）：单窗口天数，默认 7，范围 1~365。
- `activity_id` 来自 `get_recent_activities` 返回；HTC API 不支持按 id
  直查详情，详情查询内部先在列表中定位该活动再拉取高频数据。

## 排障：401 / 认证过期

**症状**：任一 tool 报 `HTC HTTP 请求失败：status=401`（或脚本输出
`HTC API request: FAILED` + 401）。通常**昨天还能用、今天全体 tool 一起失败**——
这是会话凭证过期的典型形态，不是本项目代码问题。

**原因**：`HTC_AUTHORIZATION` / `HTC_COOKIE` 来自浏览器会话，有效期由华为
服务端控制（数小时到数天不等），过期后所有请求统一 401。

**修复步骤**：先运行 `\.venv\Scripts\python.exe -m scripts.auth_status`。
若没有可解密凭证，运行 `\.venv\Scripts\python.exe -m scripts.auth_login`，
在专用浏览器中手动打开可访问的 Training Camp 页面并查看训练记录。若 MCP
自动恢复后仍返回 401，按此步骤重新认证，然后重启 MCP 服务。

**相邻情况区分**：

| 现象 | 含义 | 处理 |
|---|---|---|
| 全部 tool 401 | 凭证过期（最常见） | 按上述步骤换新 |
| 单一 tool 400 | 该请求参数问题 | 提 issue 附现象（不含凭证） |
| 403 / 405 | 权限或入口不匹配 | 确认复制的是 `things.dbankcloud.cn` 域下成功请求的请求头 |
| 脚本 WARNING 提示未设 `HTC_VERSION` / `HTC_COOKIE` | 可选头缺失，不致命 | 通常仍可成功；被拒时按第 3 步同样方法补全 |

> 安全提醒：DPAPI 文件仅供创建它的 Windows 用户在本机解密；不要复制到仓库、
> issue 或其他设备。

## 常见问题 FAQ

**Q1：报错 "'python' 不是内部或外部命令"**
安装 Python 时没勾 `Add Python to PATH`。最简单的解决：重新运行安装包，
勾上后再 Install；或改用 `py` 命令（`py -m venv .venv`）。

**Q2：PowerShell 提示"在此系统上禁止运行脚本"（执行策略）**
本教程的命令不涉及运行 .ps1 脚本，一般不会遇到。若确需放开，以管理员
开 PowerShell 执行 `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
（输入 Y 确认）。

**Q3：`.\.venv\Scripts\pip` 提示找不到路径**
你不在项目目录里。先 `cd` 到项目根目录（有 `requirements.txt` 的那层）。

**Q4：探测器没捕获到成功请求**
确认专用 Edge 中打开的是你已验证可访问训练数据的 Huawei Training Camp 页面，
并等训练列表或详情加载完毕。程序只监听该服务的 `activityRecord:query` 成功请求。

**Q5：Mac / Linux 能用吗？**
核心 MCP 服务有环境变量认证兼容路径，但本项目的浏览器授权捕获、DPAPI
加密存储与自动恢复只在 Windows + Edge 验证过。Mac / Linux 用户需自行提供
有效的 `HTC_AUTHORIZATION` 与 `HTC_CLIENT_ID`；这条安装路径尚未做真实账号验收。

**Q6：我的数据会不会上传到第三方？**
不会。本服务只在你本机运行，请求只发往华为官方服务器。AI 客户端从本地
服务读数——你问 AI 时，AI 客户端会把要分析的数据发给**你自己配置的模型
服务方**（和你平时用它聊天是同一回事，介意的话选本地模型）。

**Q7：程序会自动输入密码或验证码吗？**
不会。你本人在专用 Edge 配置中登录和操作页面；程序只读取该页面正常请求的
必要请求头。凭证使用当前 Windows 用户的 DPAPI 加密保存；环境变量方式仍兼容。

**Q8：测试全通过但我一条数据都没有？**
单元测试用合成数据，不需要凭证和网络。真实数据要看第 4 步的
`test_real_htc.py` 输出。

## 开发

```powershell
# 运行全部测试（全部 Mock，不联网、不需要凭证）
.\.venv\Scripts\python.exe -m pytest -q      # 当前 318 passed（9 skipped）
```

> **测试不会随日历日期漂移（issue #2）**：`tests/test_detail_tool.py` 的定位窗口用合成数据，
> 依赖一个固定的"现在"锚点——常量 `NOW_MS` 配合 `_FixedDatetime` 类，测试内
> `patch("src.huawei_health_mcp.server.datetime", _FixedDatetime)` 让服务端始终以该锚点算窗口，
> 而非真实系统时间。如此即便真实日期越过锚点（原本会把 60 天前的合成活动滤出窗口、用例必失败），
> 结果依然确定。`_FixedDatetime.now(tz=None)` 返回本地时区 naive 时间，与真实 `datetime.now()` 语义一致；
> 回归测试 `test_fixed_now_anchor_and_window_independent_of_real_clock` 把"窗口与真实墙钟无关"这条契约锁死。


```
src/huawei_health_mcp/
├─ client.py             # HTCClient：HTTP 取数，返回原始 JSON（不解析）
├─ parser.py             # 训练原始 JSON → 标准模型（时间戳契约：记录 ms / 采样 ns）
├─ health_parser.py      # 恢复状态解析（睡眠记录 / 静息心率 / HRV 统计）
├─ performance_parser.py # 训练能力解析（运动能力评估 / PB 个人纪录）
├─ models.py             # Pydantic 模型（ActivityRecord / TrainingSummary / SleepRecord / AthleticPerformance 族）
├─ analysis.py           # 确定性统计分析（ActivityDetail → TrainingSummary）
├─ period_analysis.py    # 周期聚合（多 ActivityRecord → TrainingPeriodSummary）
├─ period_comparison.py  # 周期对比（两个 TrainingPeriodSummary → TrainingPeriodComparison）
├─ trend_analysis.py     # 滚动周趋势与相邻周环比（复用聚合层与对比层）
└─ server.py             # FastMCP 服务与工具接线
scripts/auth_login.py      # 用户手动操作专用 Edge，并安全保存成功请求凭证
scripts/auth_status.py     # 检查本地 DPAPI 凭证是否可解密
scripts/test_dpapi_mcp.py  # 清除子进程 HTC_* 后验证 DPAPI-backed MCP 数据调用
scripts/test_auto_recovery.py # 用临时无效凭证验证真实 API 的单次 401 恢复
scripts/test_real_htc.py   # 人工真实请求脚本（十一模式，环境变量兼容）
scripts/test_mcp_client.py # 真实 MCP 客户端验收（14 个 tool 全调用）
tests/                     # 单元测试（synthetic fixture，无真实用户数据）
PROJECT_STATE.md           # 项目长期状态账本（新贡献者/Agent 从这里恢复上下文）
```

开发约定：认证只经 DPAPI 本地存储或兼容环境变量；真实响应只存 `data_temp/`（git-ignored）；
测试全部使用 Mock / synthetic 数据；每个 Phase 完成后更新 `PROJECT_STATE.md`。

## 已验证的真实 API 契约（摘要）

- 列表 / 详情响应顶层均为 `list`
- 记录级与详情顶层时间为毫秒；采集器 / 采样点时间为纳秒
- 采样值 `floatValue` → float、`integerValue` → int
- 请求的数据类型不保证全部返回（`details` / `samplePoints` 可为空，属正常）
- 恢复状态端点：`GET /healthRecords` 时间戳为纳秒；`healthRecords` 统计的
  startDay/endDay 为字符串、`sampleSet` 统计为数字（两端口径不混用）；
  睡眠分段为分钟（light+deep+dream=all 自洽）
- 训练能力端点：`GET /athleticPerformance/latest` 直接收五项指数与
  predictedTimes（秒）；`GET /sportReports` PB 的 startTime/endTime 为毫秒，
  value 单位由华为定义（时间为秒、距离为米）

## 许可证与免责声明

本项目以 [MIT License](LICENSE) 开源。

**免责声明**：本项目仅用于分析用户**自己账号、自己授权**的运动数据。
不实现任何绕过华为权限、破解认证、窃取 Cookie、绕过访问控制的功能。
使用本项目产生的任何后果（如账号因异常访问被服务方限制）由使用者自行承担。
