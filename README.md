# Sentence Reader Mac

Sentence Reader 是一个本地优先的 Mac 读书软件，重点不是做一个更漂亮的 Apple Books，而是做一个适合精读的阅读工作台。

它把“句子”当成最小操作单位：你可以对一句话做笔记、整句标红、查词、语音备注、导出，后续也可以把高质量读书笔记同步到 Hermes / Cognitive OS。

## 这个软件能做什么

- 管理 EPUB 书库，首页优先显示 `继续阅读`。
- 导入 EPUB 到软件自己的内部书库，导入后原始文件可以移动或删除。
- 点击书籍封面或书卡，直接进入正文阅读。
- 黑色阅读背景，微软雅黑正文，尽量减少顶部和底部干扰。
- 横向翻页，支持章节边缘继续进入上一章/下一章。
- 双击句子：添加或编辑备注。
- 右键 / 双指点按句子：整句标红。
- 单击英文单词：查词。
- 保存阅读位置、笔记、红标、语音备注、导出记录。
- 提供独立的 `笔记` 和 `红标` 中心。
- 支持 Markdown / JSON 导出。
- 支持同一局域网 iPad 浏览器阅读。
- 支持本地 FunASR 语音转文字作为语音备注能力。
- 预留 Hermes / Cognitive OS 同步入口，但普通阅读不依赖 Hermes。

## 适合谁

适合：

- 想做深度阅读、逐句理解的人。
- 想把书里的好句子沉淀成长期笔记的人。
- 需要“整句标红 + 句子备注 + 查词”的用户。
- 想用 Mac 作为主力阅读和数据中心，同时偶尔用 iPad 访问的人。
- 想把阅读内容后续接入个人知识系统或 AI 工作流的人。

暂时不适合：

- 想要一个 App Store 级别安装包的人。
- 想要云同步、多账号、跨公网访问的人。
- 想要原生 iPad App 的人。
- 想阅读 DRM 加密电子书的人。
- 想要 Calibre 那种完整书库管理系统的人。

## 怎么使用

当前打包后的 App 在：

```bash
build/Sentence Reader.app
```

打开：

```bash
open "build/Sentence Reader.app"
```

正常情况下，软件会直接进入 `书库` 首页。

基本流程：

1. 点击 `导入`，选择 EPUB。
2. 导入完成后，点击封面或书卡进入正文。
3. 阅读时双击句子添加备注。
4. 右键或双指点按句子进行整句标红。
5. 单击英文单词查词。
6. 点击 `书库` 回到主界面。
7. 在 `笔记` / `红标` 中查看沉淀下来的内容。

## iPad 怎么用

Mac 和 iPad 需要在同一个 Wi-Fi 下。

在 iPad 浏览器打开：

```text
http://<你的 Mac 局域网 IP>:18180/library
```

直接进入阅读器：

```text
http://<你的 Mac 局域网 IP>:18180/lan/reader
```

示例：

```text
http://192.168.1.88:18180/library
```

iPad 端是浏览器版本，支持阅读、翻页、字号设置、句子操作栏、笔记、红标、阅读位置保存和语音备注降级路径。

## 数据保存在哪里

Sentence Reader 是本地优先软件，用户数据默认保存在本机。

内部 EPUB 副本：

```text
~/Library/Application Support/SentenceReader/Books
```

语音备注、运行文件等：

```text
~/Library/Application Support/SentenceReader
```

结构化数据：

```text
PostgreSQL 数据库：jiangyu_os
schema：reader
```

主要数据包括：

- 书籍
- 章节
- 句子
- 阅读位置
- 笔记
- 红标
- 语音备注
- 导出记录
- 查词记录

## 本仓库没有放什么

为了避免仓库臃肿和泄露个人数据，GitHub 仓库不包含：

- 打包后的 App
- Python 虚拟环境
- 本地 PostgreSQL 数据
- 你导入的真实书籍
- 生成报告缓存
- 完整 ECDICT CSV 词库
- 本地 Playwright / 构建缓存

这些是本地数据或构建产物，不应该跟源码一起上传。

## 从源码验证

常用验收命令：

```bash
./scripts/v1_acceptance.sh
./scripts/v21_ipad_lan_acceptance.sh
.venv-reader-api/bin/python -m pytest tests/test_reader_api_mock.py
.venv-reader-api/bin/python -m compileall reader_api scripts tests
python3 scripts/package_sentence_reader_app.py
```

数据库迁移：

```bash
PATH="/Applications/Postgres.app/Contents/Versions/latest/bin:$PATH" \
  .venv-reader-api/bin/python scripts/reader_pg_migrate.py
```

可选：导入完整 ECDICT 词库：

```bash
.venv-reader-api/bin/python scripts/sentence_reader_import_ecdict.py \
  data/external/ecdict/ecdict.csv \
  --source ecdict
```

## 主要文档

- [使用说明](docs/user_guide.md)
- [产品验收标准](docs/product_acceptance.md)
- [当前状态](docs/current_status.md)
- [产品路线图](docs/product_roadmap.md)
- [交互规则](docs/interaction_contract.md)
- [运行环境与可迁移性](docs/runtime_portability.md)

## 当前边界

当前版本适合在这台 Mac 上日常使用，也可以给同一局域网下的 iPad 浏览器使用。

它还不是最终的公开发行版。下一步如果要给朋友安装，需要继续做：

- 更清楚的首次启动引导
- 可选词库包下载
- 朋友电脑安装流程
- 签名 App
- release 包和版本说明

核心原则：阅读、标红、笔记、查词这些基础能力必须本地可靠；在线服务和 AI 只能增强体验，不能成为阅读能力的地基。
