# Click Hermes Mobile Gateway Construction Plan

更新日期：2026-07-01

## 一句话结论

Click 移动端下一阶段要从“只进读书”升级成“本地入口工作台”：

```text
打开 Click App
  -> 阅读
  -> 录音
  -> Hermes
```

阅读继续复用现有 Reader API。录音进入独立的 `~/Documents/Recordings` 总仓库。Hermes 继续跑在 Mac 上，但只作为理解、命名和对话能力，不拥有录音数据本身。手机只负责录音、显示和播放，不在手机本地跑模型。当前本地可验收范围覆盖 P1.1-P6：录音总仓库、移动设备审核、录音管理、Hermes 语音消息、edge-tts 回复和 Android debug APK。

## 归属判断

录音资产不能放进 Hermes 内部。原因是 Hermes 会持续升级，而且 Hermes、Marketplace OS、Reader 等系统应该是平行消费者，不应该互相吞并数据所有权。

```text
Owner project: Local Recordings asset store, with Click / Reader as current product client
Asset type: product_code + runtime_user_data
Canonical product doc: docs/hermes_mobile_gateway_construction.md
Canonical runtime data: ~/Documents/Recordings
Promotion rule: promote_to_project
Stop condition: do not write recordings into Hermes internal memory, Hermes repo, or Marketplace OS database by default
```

正确关系：

```text
Recordings total store
  -> 保存录音资产原件
  -> 保存 transcript / title / summary / tags
  -> Click / Reader 只记录来源和上下文
  -> Hermes 可读取、命名、总结
  -> Marketplace OS 可在授权后读取相关资产
  -> Reader 可在后续关联读书笔记
```

Hermes 是处理器，不是录音仓库。

`~/Documents/Recordings` 是独立的本地录音资产层，不是 Reader API 的书籍数据，也不是 Hermes Gateway 的内部状态，更不是 Marketplace OS 的经营数据库。Click、Hermes、Marketplace OS、Reader 后续都只能通过 manifest / API 读取授权资产；Hermes 升级或替换时，不迁移、不接管、不重写录音仓库。旧的 `~/Library/Application Support/Click/KnowledgeInbox/Recordings` 只作为 legacy read-only 兼容路径，不再作为新录音主写入路径。

## 当前是否在做正确的事

是，但只能按这个边界做：

- Click App 是入口，不是第二套阅读器。
- Click Local Hub 可以复用现有 `18180` 服务承载移动页面和同源转发，但 Reader 的书籍/PostgreSQL 数据层、Recordings 总仓库、Hermes Runtime 仍然分开。
- 录音是独立知识资产，不混进 Hermes 临时聊天消息。
- 录音资产属于独立 Recordings 总仓库，不属于 Click 或 Hermes 内部状态。
- Hermes 可以在移动端使用，但必须经过局域网安全网关和设备授权。
- 语音 P1 只做语音消息，不先做实时电话。

错误方向是：

- 把 Hermes 记忆、工具、录音资产或会话状态塞进 Reader 书籍/PostgreSQL 数据层。
- 把长期录音资产和临时聊天语音混成一类。
- 把录音资产写进 Hermes 内部 memory / session / repo。
- 让手机直接调用 Hermes CLI。
- 手机本地跑大模型或本地 TTS 模型。
- 只靠 IP 白名单保护 Hermes。
- 一上来做全双工实时电话。

## P2 设备审核边界

手机访问不能只靠 IP 白名单。Click Local Hub 在本机保存移动设备授权文件：

```text
~/Library/Application Support/Click/MobileAccess/allowed_devices.json
~/Library/Application Support/Click/MobileAccess/pending_devices.json
```

接口：

```text
GET  /v1/mobile/access/status
POST /v1/mobile/access/request
GET  /v1/mobile/access/pending
POST /v1/mobile/access/approve
POST /v1/mobile/access/revoke
```

Android / iPad 壳会生成稳定 `device_id`。未审核设备可以请求连接和查看基础状态，但带 `device_id` 的 durable recording upload、Hermes text chat、Hermes voice message 需要本地 approve 后的 token。Mac 上没有 `device_id` 的 localhost 浏览器调试仍然保留。

这不是公网账号系统，也不是公开 token 文档。token 只在本地配置和手机壳里使用。

## 已定产品形态

移动端第一屏：

```text
Click

[ 阅读 ]
[ 录音 ]
[ Hermes ]

设置
```

默认行为：

- 点 `阅读`：检查 Mac Reader API `/health`，通过后打开 `/library`。
- 点 `录音`：检查 Click Capture API `/v1/recordings/health`，通过后打开 `/recordings`。
- 点 `Hermes`：检查 Mac Hermes Gateway `/v1/runtime/health`，通过且设备已授权后打开 `/hermes`。
- 点 `设置`：修改 Mac 地址、Reader 端口、Hermes 端口、设备授权状态。

## 读书链路

```text
Android / iPad Click Shell
  -> http://<mac-lan-ip>:18180/library
  -> /lan/reader
  -> Mac Reader API
  -> PostgreSQL / EPUB / 笔记 / 红标 / 查词 / 语音备注入口
```

读书链路不变，不重写阅读器。

## 录音资产链路

录音功能不是 Hermes 聊天里的临时语音消息，而是长期可管理的本地知识资产。

```text
Android / iPad Click Shell
  -> /recordings
  -> 手机录音
  -> POST /v1/recordings
  -> Mac 保存原始音频
  -> Mac FunASR 本地转文字
  -> Capture worker 调用 Hermes Runtime 生成标题、分类、摘要、标签
  -> 更新 recordings index
  -> PC 端和手机端都看到更新后的名称
```

用户体验：

```text
点 录音
  -> 开始录音
  -> 停止
  -> 先显示“处理中”
  -> Hermes 自动命名
  -> 列表里名称自动更新
```

自动命名规则：

- 上传后先用临时名：`录音 2026-06-30 18:30`。
- FunASR 转文字完成后，Hermes 根据大意生成正式标题。
- 标题应该短、可扫读，不超过 18 个中文字符。
- 标题必须来自转写内容的大意，不能凭空扩写。
- 如果转写为空或质量差，保留临时名并标记 `needs_review`。

分类规则：

第一版可以由 Hermes 自动给一个轻量分类：

```text
想法
任务
读书
项目
灵感
待整理
```

分类不需要一开始很复杂。真正重要的是：录音、转写、标题、分类、摘要都能在 PC 和手机端看到同一份状态。

当前录音管理接口：

```text
GET   /v1/recordings
GET   /v1/recordings/<recording_id>
GET   /v1/recordings/<recording_id>/audio
PATCH /v1/recordings/<recording_id>
POST  /v1/recordings/<recording_id>/reprocess
POST  /v1/recordings/<recording_id>/hide
```

管理原则：

- 支持按 `source_app`、`source_feature`、`category`、`tag` 筛选。
- `PATCH` 可以编辑标题、分类、标签和整理状态。
- `reprocess` 支持 dry-run，真实重处理默认不覆盖用户手工修正。
- `hide` 只隐藏索引，不删除原始音频、转写、摘要或 metadata。

## Hermes 文字链路

```text
Android / iPad Click Shell
  -> http://<mac-lan-ip>:18180/hermes
  -> POST /v1/runtime/chat same-origin proxy
  -> Hermes Runtime Adapter
  -> Hermes / Codex / local model fallback
```

当前 Mac 上已知的 Hermes Gateway 形态：

```text
host: 127.0.0.1
port: 8765
default model: gpt-5.3-codex-spark
fallback model: gpt-5.4-mini
```

移动端访问 Hermes 时，P1 不直接暴露 `8765` 给手机，而是由 Click Local Hub 在 `18180` 提供 `/hermes` 和 `/v1/runtime/chat` 同源入口，再转发到本机 Hermes Runtime Adapter。

## Hermes 语音输入链路

这是 Hermes 聊天里的语音消息，不是长期录音资产。手机不做语音识别，只录音并上传。

```text
手机录音
  -> POST /v1/voice/message
  -> Mac 保存音频
  -> Mac FunASR 本地转文字
  -> Hermes 理解
  -> 返回 transcript + reply_text
```

语音识别使用：

```text
FunASR local
```

原因：

- 已在 Mac Q5 Chat 使用过。
- 本地转写，不把用户原始语音上传云端。
- 符合用户要求：语音到 Mac，Mac 解读后返回文字。

语音消息查询接口：

```text
GET /v1/voice/message/<voice_id>
GET /v1/voice/audio/<voice_id>
```

语音消息保存在 Click 的 `HermesMobile/VoiceInbox` 临时聊天输入区。它不是长期录音资产，也不写到 `~/Documents/Recordings`，除非后续用户明确执行“保存为录音资产”的独立动作。

## Hermes 语音回复链路

手机不跑 TTS。Mac 端复用当前 Q5 Chat 实际用得最多的 Edge TTS。

```text
Hermes 回复文字
  -> Mac edge-tts
  -> voice: zh-CN-YunjianNeural
  -> Mac 生成 mp3
  -> 返回 audio_url
  -> 手机播放 audio_url
```

返回数据示例：

```json
{
  "transcript": "用户语音转写文字",
  "reply_text": "Hermes 回复文字",
  "audio_url": "http://<mac-lan-ip>:<hermes-port>/v1/voice/audio/<audio_id>"
}
```

注意：这不是“推送”音频到手机，而是 Mac 生成音频，手机请求播放。

## 语音模型选择

已定主链路：

| 能力 | 采用 | 说明 |
| --- | --- | --- |
| 语音识别 | FunASR local | 用户原始语音留在 Mac |
| Hermes 理解 | gpt-5.3-codex-spark | 当前 Hermes Gateway 默认 |
| 理解 fallback | gpt-5.4-mini | 当前 Hermes Gateway fallback |
| 语音回复 | edge-tts | 当前 Q5 Chat 用得最多 |
| 声音 | zh-CN-YunjianNeural | 过去日志中使用最多 |
| Azure TTS | 不作为主链路 | 仅后续可选 fallback |
| macOS 系统语音 | 最后 fallback | 离线兜底，音质较弱 |

## Mac 本地需要提供的接口规划

Click Local Hub / Capture API 负责：

```text
GET  /home
GET  /recordings
GET  /hermes
GET  /v1/recordings/health
POST /v1/recordings
GET  /v1/recordings
GET  /v1/recordings/<recording_id>
GET  /v1/recordings/<recording_id>/audio
GET  /v1/mobile/diagnostics
GET  /v1/runtime/health
POST /v1/runtime/chat
POST /v1/voice/message
GET  /v1/voice/message/<voice_id>
GET  /v1/voice/audio/<audio_id>
```

Hermes Gateway / Runtime Adapter 继续负责真正模型调用：

```text
GET  /v1/runtime/health
POST /v1/runtime/chat
```

P2 设备审核：

```text
GET  /v1/devices/pending
POST /v1/devices/approve
POST /v1/devices/revoke
GET  /v1/devices/status
```

诊断接口：

```text
GET /v1/mobile/diagnostics
```

诊断至少返回：

- Hermes 是否运行。
- Reader API 是否可达。
- Click Capture API 是否可达。
- Hermes Gateway host / port。
- Mac 当前局域网 IP。
- 录音资产库是否可读写。
- FunASR 是否可用。
- edge-tts 是否可用。
- 已授权设备数量。
- 当前设备授权状态。

## 数据保存

Mac 本地建议目录：

```text
~/Documents/Recordings/
  Inbox/
  Click/
    Reader/
      <recording_id>/
    Standalone/
      <recording_id>/
  Hermes/
    VoiceMessages/
    Saved/
  Shared/
  _index/
    recordings.sqlite
```

每条录音目录至少包含：

```text
<recording_id>/
  original.m4a
  transcript.txt
  summary.txt
  title.txt
  metadata.json
```

日期只写进 `metadata.json` 和 `_index/recordings.sqlite`，不按年月创建主目录。

旧路径只作为只读兼容：

```text
~/Library/Application Support/Click/
  KnowledgeInbox/
    Recordings/
      recordings.sqlite
      <legacy_recording_id>/
        original.m4a
        transcript.txt
        summary.txt
        title.txt
        metadata.json
```

Hermes 临时语音消息仍在 Click 本地移动入口下隔离，不等同于长期录音资产：

```text
~/Library/Application Support/Click/
  HermesMobile/
    allowed_devices.json
    VoiceInbox/
      <voice_id>/
        input.m4a
        transcript.txt
        reply.txt
        reply.mp3
        metadata.json
```

不要使用：

```text
~/Library/Application Support/HermesGateway/Recordings
```

这个路径会误导成 Hermes 拥有录音资产。Hermes 只能通过 manifest / API 读取 Recordings 总仓库。

## 资产 manifest

录音资产应该有稳定 schema，方便 Hermes、Marketplace OS、Reader 后续读取：

```text
local.recordings.audio_asset.v1
```

manifest 示例：

```json
{
  "schema": "local.recordings.audio_asset.v1",
  "asset_type": "audio_asset",
  "audio_id": "random-id",
  "recording_id": "random-id",
  "source_app": "Click",
  "source_feature": "Standalone recording",
  "contexts": [],
  "durability": "durable",
  "created_at": "2026-06-30T00:00:00Z",
  "updated_at": "2026-06-30T00:00:00Z",
  "status": "named",
  "transcript_status": "ready",
  "title_status": "ready",
  "summary_status": "ready",
  "title": "产品录音入口想法",
  "category": "项目",
  "tags": ["Click", "Hermes", "录音"],
  "summary": "讨论 Click App 中新增录音入口，并由 Hermes 自动转写和命名。",
  "paths": {
    "audio": "original.m4a",
    "transcript": "transcript.txt",
    "summary": "summary.txt"
  },
  "processors": {
    "asr": "funasr-local",
    "naming": "hermes-runtime"
  }
}
```

旧的目录草案：

```text
~/Library/Application Support/HermesGateway/
  allowed_devices.json
  Recordings/
    recordings.sqlite
    <recording_id>/
      original.m4a
      transcript.txt
      summary.txt
      title.txt
      metadata.json
  VoiceInbox/
    <voice_id>/
      input.m4a
      transcript.txt
      reply.txt
      reply.mp3
      metadata.json
```

上面这个旧草案废弃，不作为实施路径。

录音资产 `metadata.json` 示例：

```json
{
  "recording_id": "random-id",
  "device_id": "approved-device-id",
  "created_at": "2026-06-30T00:00:00Z",
  "updated_at": "2026-06-30T00:00:00Z",
  "status": "named",
  "provisional_title": "录音 2026-06-30 18:30",
  "title": "产品录音入口想法",
  "category": "项目",
  "tags": ["Click", "Hermes", "录音"],
  "summary": "讨论 Click App 中新增录音入口，并由 Hermes 自动转写和命名。",
  "asr_engine": "funasr-local",
  "naming_engine": "hermes-runtime",
  "audio_deleted": false
}
```

Hermes 聊天语音 `metadata.json` 示例：

```json
{
  "voice_id": "random-id",
  "device_id": "approved-device-id",
  "created_at": "2026-06-30T00:00:00Z",
  "status": "done",
  "asr_engine": "funasr-local",
  "tts_engine": "edge-tts",
  "tts_voice": "zh-CN-YunjianNeural",
  "audio_deleted": false
}
```

后续设置项：

- 转写完成后删除原始音频。
- 只保留最近 N 条语音。
- 清空 VoiceInbox。
- 录音资产永久保存或手动删除。
- 录音资产导出为 Markdown / JSON。
- 录音资产可被 Hermes / Marketplace OS / Reader 在授权后读取。

## 安全设计

Hermes 比 Reader API 更敏感，所以不能裸露在局域网里。

P1 安全底线：

```text
同一局域网
+ 设备审核
+ token
+ token hash 本地保存
+ 默认 chat_only
+ 不默认开放工具调用
```

设备审核流程：

```text
新手机点 Hermes
  -> Hermes Gateway 创建 pending device
  -> Mac 端显示待审核
  -> 用户允许
  -> Gateway 发放 token
  -> 手机保存 token
  -> 后续自动进入
```

权限等级：

```text
chat_only
read_context
limited_tools
full_agent_mode
```

P1 默认只允许：

```text
chat_only
```

明确禁止：

- 未授权设备进入 Hermes。
- 未授权设备上传录音。
- 手机端直接触发 Mac 命令。
- 默认读取 Mac 文件。
- 默认调用自动化工具。
- 暴露公网访问。

## 阶段施工

| 阶段 | 主任务 | 输出 | 验收 |
| --- | --- | --- | --- |
| P0 | 查清现有 Hermes Gateway | Hermes 当前端口、host、接口、启动方式清单 | 明确 `8765` 当前只监听本机，确认已有 `/v1/runtime/chat` 和 `/v1/runtime/health` |
| P1 | 做移动工作台网页 | `/home`、`/hermes`、`/recordings` 页面 | Mac 浏览器能打开，手机同 Wi-Fi 能打开 |
| P2 | 做设备审核 | pending / approve / token / revoke | 未授权不能聊，授权后能聊 |
| P3 | 做独立录音资产 | `/v1/recordings` + `~/Documents/Recordings` | 手机上传录音，Mac 保存到 Recordings 总仓库，转写、自动命名，PC/手机列表同步更新 |
| P4 | 做 Hermes 语音消息 | `/v1/voice/message` | 手机上传音频，Mac FunASR 转文字，Hermes 回文字 |
| P5 | 做语音回复 | `/v1/voice/audio/<id>` | Mac edge-tts 生成 mp3，手机能播放 |
| P6 | 打包和真机验收 | Android APK / iPad shell 构建说明 | 安卓真机可用；iPad 继续受签名和 Xcode 环境约束 |
| P7 | 半双工通话 | 通话页、轮次状态、语音回复播放 | 你说完停顿，Hermes 回答 |
| P8 | 打断机制 | `turn_id`、interrupt、取消旧回复 | Hermes 正在说话时可以被打断 |
| P9 | 实时通话研究 | 流式 ASR / LLM / TTS 方案 | 只研究，不作为当前交付 |

## 每阶段施工标准

### P0 标准

必须输出：

- Hermes Gateway 项目路径。
- 当前 launchd 配置。
- 当前 host / port。
- 当前 runtime health 是否可达。
- 当前 runtime chat 是否可达。
- FunASR 是否可启动。
- edge-tts 是否存在。

不得做：

- 不改移动端。
- 不改 Reader API。

### P1 标准

必须输出：

- `/home` 工作台页面。
- `/hermes` 页面。
- `/recordings` 页面。
- 基础聊天输入框。
- 调用 `/v1/runtime/chat`。
- 录音列表空状态。
- 移动端页面适配。

验收：

- Mac 浏览器可打开工作台。
- 手机浏览器可打开工作台。
- 首页显示 `阅读`、`录音`、`Hermes`。
- 未授权设备只能看到授权提示。

### P2 标准

必须输出：

- `allowed_devices.json`。
- token 生成、校验、撤销。
- pending device 列表。

验收：

- 新设备第一次进入需要审核。
- 审核后不用重复授权。
- revoke 后无法继续访问。

### P3 标准

录音资产是独立入口，不是 Hermes 聊天临时语音。

必须输出：

- `/recordings` 页面。
- `POST /v1/recordings`。
- `GET /v1/recordings`。
- `GET /v1/recordings/<recording_id>`。
- `GET /v1/recordings/<recording_id>/audio`。
- `~/Documents/Recordings`。
- `_index/recordings.sqlite` 或等价索引。
- `local.recordings.audio_asset.v1` manifest。
- 每条录音独立目录。
- Hermes 自动命名和分类。

验收：

- 手机能录音并上传。
- Mac 本地能看到原始音频文件。
- FunASR 生成 transcript。
- Hermes 生成标题、分类、摘要、标签。
- 手机端列表从临时名更新为 Hermes 生成标题。
- PC 端打开 `/recordings` 能看到同一个更新后标题。
- 转写为空时不硬命名，标记 `needs_review`。
- Hermes 内部 memory / session / repo 没有被写入录音原始数据。

### P4 标准

必须输出：

- `/v1/voice/message`。
- 手机上传音频。
- Mac 保存音频。
- FunASR 转文字。
- Hermes 回文字。

验收：

- 一条中文语音能得到中文 transcript。
- Hermes 能基于 transcript 回复。
- 原始音频保存在 VoiceInbox。

### P5 标准

必须输出：

- edge-tts 调用。
- `reply.mp3`。
- `/v1/voice/audio/<audio_id>`。
- 返回 `audio_url`。

验收：

- 手机收到 `audio_url`。
- 手机能播放 Hermes 语音回复。
- edge-tts 失败时仍显示文字回复。

### P6 标准

必须输出：

- Android / iPad shell 首页三入口。
- Reader port 默认 `18180`。
- Hermes port 可配置。
- 使用同一个 Mac IP。

验收：

- 点 `阅读` 进入 `/library`。
- 点 `录音` 进入 `/recordings`。
- 点 `Hermes` 进入 `/hermes`。
- 设置里能改 Mac 地址和端口。

### P7 标准

半双工通话不是实时电话，第一版按“你说完，Hermes 回答”的模式做。

必须输出：

- 通话页。
- `正在听` / `正在转文字` / `Hermes 正在想` / `Hermes 正在说` 状态。
- 通话模式仍然复用 FunASR local 和 edge-tts。
- 每一轮对话都有 `turn_id`。

验收：

- 点击通话后可以开始录音。
- 停顿后自动提交本轮语音。
- Hermes 返回文字和语音。
- 手机播放 Hermes 语音回复。
- 结束通话后回到 Hermes 聊天页。

### P8 标准

打断是通话体验的核心，不做会很难长期使用。

必须输出：

- `POST /v1/voice/interrupt`。
- 当前播放音频立刻停止。
- 当前 `turn_id` 标记为 `interrupted`。
- 旧回复即使稍后完成，也不能覆盖新一轮对话。
- 手机开始新录音时可以自动触发打断。

打断流程：

```text
Hermes 正在说 turn_001
  -> 用户点打断或开始说话
  -> 手机停止播放
  -> POST /v1/voice/interrupt turn_001
  -> Mac 标记 turn_001 interrupted
  -> 如果 TTS 正在生成，结果丢弃
  -> 如果 LLM 旧回复稍后返回，结果丢弃
  -> turn_002 开始听用户新语音
```

验收：

- Hermes 正在说话时，点打断立即静音。
- 被打断的旧回复不会继续播放。
- 被打断的旧回复不会插入当前对话底部。
- 新一轮语音可以立刻开始。

## 不做的事

当前阶段不做：

- 不做全双工实时电话。
- 不做后台常开监听。
- 不做公网访问。
- 不做云端 ASR。
- 不默认 Azure TTS。
- 不做移动端本地模型。
- 不把录音资产塞进 Reader API。
- 不把录音资产塞进 Hermes 内部。
- 不把录音资产当成临时 Hermes 语音消息。
- 不把 Hermes 对话状态、工具权限或录音资产写进 Reader 书籍/PostgreSQL 数据层。P1 可以使用同源 `/v1/runtime/chat` 转发，降低手机连接复杂度。
- 不让未审核设备访问 Hermes。

## 后续升级方向

当前 P1-P6 做完后，再考虑：

- 半双工通话：你说完，Hermes 回答。
- 打断：Hermes 正在说话时可以停止。
- 流式转写。
- 流式 TTS。
- 多设备授权管理。
- 按设备区分权限等级。
- 语音历史搜索。
- 录音资产全文搜索。
- 录音资产和读书笔记关联。

真正的“像打电话一样”放在后面，不抢 P1。

## 三个主入口设计边界

当前主入口先定三个：

```text
阅读
录音
Hermes
```

| 入口 | 解决什么 | 保存在哪里 | 是否需要 Hermes 理解 |
| --- | --- | --- | --- |
| 阅读 | 看书、标红、笔记、查词 | Reader API / PostgreSQL / Books | 可选同步，不强依赖 |
| 录音 | 保存独立语音资产，自动转写和命名 | `~/Documents/Recordings` | 需要，但只作为命名、摘要、分类处理器 |
| Hermes | 直接对话、语音消息、后续通话 | HermesGateway / VoiceInbox / 会话状态 | 需要 |

录音和 Hermes 聊天的差别：

- 录音是资产，应该能在列表里长期查看、搜索、改名、分类。
- Hermes 聊天语音是一次对话输入，默认属于聊天流。
- 录音可以后来发送给 Hermes 继续分析，但上传时不自动变成聊天消息。
- Hermes、Marketplace OS、Reader 都只能通过授权读取录音资产，不直接拥有录音资产。

## 通话模式设计边界

用户未来有两个高频场景：

```text
场景 A：发语音，Hermes 回文字
场景 B：像打电话一样，你说话，Hermes 也说话，并且你能打断它
```

这两个场景必须分开做。

场景 A 是 P3/P4：

```text
录完整段音频
  -> 上传
  -> 转写
  -> 回复文字
  -> 可选播放语音
```

场景 B 是 P7/P8：

```text
通话模式
  -> 一轮一轮听
  -> 一轮一轮回答
  -> 支持打断
```

当前不做真正全双工电话。真正全双工需要：

- 流式 ASR。
- 流式 LLM。
- 流式 TTS。
- 回声消除。
- 抢话判断。
- 网络抖动处理。

这些不是当前最小可验收范围。

## 和前面讨论的一致性自检

| 前面讨论结论 | 当前方案是否一致 | 说明 |
| --- | --- | --- |
| 移动端打开先有读书 / Hermes | 已更新 | 根据新需求升级为 `阅读` / `录音` / `Hermes` 三入口 |
| 读书继续用现有 `/library` 和 `/lan/reader` | 一致 | 不重写阅读器 |
| 新增独立录音功能 | 一致 | 录音作为资产存入 Recordings，不混入临时聊天语音 |
| 录音由 Hermes 自动命名 | 一致 | FunASR 转写后，Hermes 生成标题、分类、摘要、标签 |
| PC 和手机都能看到更新后的名称 | 一致 | `/recordings` 和 `GET /v1/recordings` 共用同一索引 |
| 录音不要集成进 Hermes 本身 | 一致 | 录音归属独立 Recordings 总仓库，Hermes 只作为处理器读取 |
| Hermes / Marketplace OS 等系统平行读取资产 | 一致 | manifest 采用 `local.recordings.audio_asset.v1`，后续授权读取 |
| Hermes 不塞进 Reader API | 一致 | 独立 Hermes Gateway |
| Mac Hermes 负责计算，手机只做入口 | 一致 | 手机只录音、显示、播放 |
| 安全不能只靠 IP | 一致 | IP + 设备审核 + token |
| P1 默认 chat_only | 一致 | 不开放文件、命令、工具 |
| 语音先做语音消息，不先做真电话 | 一致 | P3/P4 是语音消息和语音回复 |
| 用户原始语音不上传云端 | 一致 | ASR 用 FunASR local |
| TTS 用现在 Q5 Chat 用得最多的 | 一致 | edge-tts + zh-CN-YunjianNeural |
| Azure TTS 不作为主链路 | 一致 | 只作为后续可选 fallback |
| Edge TTS 用 Mac 端同一个 | 一致 | Mac 生成 mp3，手机播放 URL |
| 手机端不跑 Edge TTS | 一致 | 手机只请求 `audio_url` |
| Mac 要可诊断 | 一致 | P3 诊断接口列出 Reader、Hermes、FunASR、edge-tts、授权状态 |
| 用户未来可能像打电话一样使用 | 一致 | P7 设计半双工通话 |
| 用户需要能打断 Hermes | 一致 | P8 设计 `turn_id` 和 interrupt |
| 不一上来做真正实时电话 | 一致 | P9 只做研究，不作为当前交付 |

当前方案和讨论没有核心出入；已根据新需求从双入口升级为三入口。唯一需要在开工前实测确认的是：现有 Hermes Gateway 如何最小改造成局域网安全网关，以及是否直接在现有 `8765` 上扩展，还是另开一个 LAN-facing wrapper。

## 推荐下一步

下一轮不要先改手机 APK。先做 P0：

1. 扫描 Hermes Gateway 当前项目。
2. 读取 launchd 配置。
3. 验证 `/v1/runtime/health` 和 `/v1/runtime/chat`。
4. 检查 FunASR 和 edge-tts 可用性。
5. 输出 P0 报告。
6. 决定是在现有 `8765` 上扩展，还是新建 LAN wrapper。

只有 P0 明确后，再开始 P1 `/home`、`/recordings`、`/hermes` 页面。
