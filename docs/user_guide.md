# Sentence Reader 使用说明

更新日期：2026-06-29

## 一句话说明

Sentence Reader 是一个本地优先的 Mac 精读软件。

它的核心不是“打开一本书”，而是围绕一句话完成阅读动作：标红、备注、语音备注、查词、导出和后续知识沉淀。

## 核心功能

### 书库

- 首页优先显示 `继续阅读`。
- 支持 EPUB 导入。
- 导入后会复制到软件内部书库。
- 支持封面墙、最近阅读、阅读进度、笔记数、红标数。
- 点击封面或书卡直接进入正文。
- 支持查看内部 EPUB 副本。
- 支持非破坏性移出书库。

非破坏性移出书库的意思是：只从书库列表隐藏，不删除书籍副本、不删除笔记、不删除红标、不删除数据库记录。

### 阅读

- 黑色阅读背景。
- 微软雅黑正文。
- 顶部和底部工具栏默认尽量少打扰。
- 横向翻页。
- 到章节边缘可以继续进入上一章或下一章。
- 支持图片约束，避免图片撑破页面。
- 自动保存阅读位置。

### 句子操作

Mac 端：

| 你想做什么 | 怎么操作 | 结果 |
| --- | --- | --- |
| 聚焦一句话 | 单击句子 | 当前句子高亮聚焦；如果已有备注，会显示备注预览 |
| 查英文词 | 单击英文单词 | 弹出词义 |
| 写备注 | 快速双击句子 | 打开备注窗口 |
| 看已有备注 | 单击有备注的句子 | 显示这句话的备注 |
| 整句标红 | 右键句子 | 整句话变红 / 取消标红 |
| 整句标红 | 双指点按句子 | 整句话变红 / 取消标红 |
| 备用查词 | `Option` + 双击英文词 | 走备用查词路径 |
| 复制文字 | 拖选文字后按 `Command+C` | 复制选中的文字 |
| 关闭弹窗 | `Esc` | 关闭备注、查词、抽屉等临时浮层 |
| 退出软件 | `Command+Q` | 退出 App |

iPad / 局域网页面：

| 你想做什么 | 怎么操作 | 结果 |
| --- | --- | --- |
| 操作一句话 | 点击句子 | 底部出现句子操作栏 |
| 查英文词 | 点击英文单词 | 弹出词义 |
| 写备注 | 快速双击句子 | 打开备注 |
| 整句标红 | 长按句子 | 整句话变红 / 取消标红 |
| 翻页 | 左右滑动 | 上一页 / 下一页 |
| 调整字体 | 点 `Aa` | 调整字号、行高、边距 |
| 回书库 | 点 `书库` | 回到主界面 |

注意：在正文句子上，Sentence Reader 的句子级交互优先于系统默认手势。这是这个软件存在的原因。

这里的“双击”指快速连续点两下。双击不是慢慢点两次；慢慢点两次不会触发备注，只会执行两次单击/点击逻辑。

### 交互优先级

在正文句子上，Sentence Reader 的句子操作优先于系统默认菜单。

也就是说：

- 双指点按句子，优先执行整句标红。
- 不会优先弹出系统复制菜单。
- 如果要复制文字，请拖选文字后按 `Command+C`。
- 输入框、按钮、备注框仍然保留系统默认复制、粘贴和编辑行为。

这个设计不是 bug。它是为了让整句标红和句子备注足够快。

### 查词和备注会不会冲突

不会。

逻辑是：

- 单击英文词：查词。
- 如果这一下其实是双击的第一下，系统会短暂等待。
- 如果马上第二下形成双击，就取消查词，打开备注。
- 如果没有第二下，就执行查词。

### 笔记和红标

- 文本备注会保存到 Reader API 和 PostgreSQL。
- 语音备注会保存到本地，并和对应句子关联。
- 有备注的句子可以点击查看备注。
- 书库里有独立的 `笔记` 中心。
- 书库里有独立的 `红标` 中心。
- 支持搜索书名、作者、笔记和红标内容。

### 查词

- 单击英文词会查词。
- 优先查当前书的词表。
- 当前书没有词表时，自动查通用词典。
- 通用词典结果会写回当前书的词表，方便之后复用。
- 当前本机已经导入 ECDICT 兼容词库。

词库数据保存在本地 PostgreSQL，不跟 GitHub 源码一起上传。

### 语音备注

- Mac 端优先使用本地 FunASR。
- FunASR 不可用时，会走降级路径。
- iPad 端语音能力以浏览器录音上传和手动备注为主。
- 不调用付费语音服务。

### 导出

支持把读书笔记、红标和相关数据导出为：

- Markdown
- JSON

导出的目标是后续复盘、写作、整理知识资产，或者进入 Hermes / Cognitive OS 工作流。

## 怎么打开

当前开发机上，App 位于：

```bash
build/Sentence Reader.app
```

打开：

```bash
open "build/Sentence Reader.app"
```

正常情况下，打开后会进入 `书库` 主界面。

如果没有进入书库，通常是 Reader API、PostgreSQL 或运行环境没有准备好。此时软件会显示诊断或降级入口。

## 怎么导入书

1. 打开 App。
2. 进入 `书库`。
3. 点击 `导入`。
4. 选择 EPUB 文件。
5. 等待导入完成。
6. 点击封面或书卡开始阅读。

导入完成后，原始 EPUB 文件可以移动或删除。软件使用的是内部副本。

## iPad 怎么访问

Mac 和 iPad 必须在同一个 Wi-Fi 下。

在 iPad 浏览器打开：

```text
http://<Mac 局域网 IP>:18180/library
```

直接进入阅读器：

```text
http://<Mac 局域网 IP>:18180/lan/reader
```

示例：

```text
http://192.168.1.88:18180/library
```

这是局域网访问，不是公网服务。不要直接暴露到互联网。

## 数据在哪里

本地运行数据：

```text
~/Library/Application Support/SentenceReader
```

内部书籍副本：

```text
~/Library/Application Support/SentenceReader/Books
```

数据库：

```text
PostgreSQL database: jiangyu_os
schema: reader
```

主要表：

- `reader.books`
- `reader.book_files`
- `reader.chapters`
- `reader.sentences`
- `reader.annotations`
- `reader.reading_positions`
- `reader.audio_notes`
- `reader.exports`
- `reader.sync_events`
- `reader.dictionary_entries`

## GitHub 仓库里不包含什么

仓库只放源码、文档、迁移和小型测试 fixture。

不上传：

- 打包后的 App
- Python 虚拟环境
- 本地数据库
- 真实书籍文件
- 完整 ECDICT CSV
- 运行报告
- 构建缓存
- Playwright 缓存

这是为了避免仓库变臃肿，也避免上传个人阅读数据。

## 常用验收命令

完整基础验收：

```bash
./scripts/v1_acceptance.sh
```

iPad / LAN 验收：

```bash
./scripts/v21_ipad_lan_acceptance.sh
```

Reader API 测试：

```bash
.venv-reader-api/bin/python -m pytest tests/test_reader_api_mock.py
```

Python 编译检查：

```bash
.venv-reader-api/bin/python -m compileall reader_api scripts tests
```

重新打包 App：

```bash
python3 scripts/package_sentence_reader_app.py
```

## 当前不是最终版的地方

这已经是本机日常可用版本，但还不是适合公开分发的最终版。

还需要继续打磨：

- 朋友电脑首次安装流程。
- 可选词库包下载。
- 更清楚的运行环境检查和修复向导。
- App 签名和正式 release 包。
- 更成熟的主界面视觉设计。
- 更完整的 PDF 能力。
- 原生 iPad App。

## 产品原则

基础阅读能力必须本地可靠：

```text
阅读 -> 句子 -> 笔记/标红/查词 -> 本地持久化 -> 可选导出/同步
```

在线词典、AI 总结、Hermes / Cognitive OS 都只能增强体验，不能成为读书、标红、备注这些核心能力的地基。
