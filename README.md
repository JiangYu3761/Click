<h1 align="center">Click</h1>

<p align="center">
  <strong>一句话就是一个操作对象。</strong>
</p>

Click 是一个本地优先的精读系统。它不是普通电子书阅读器，重点不是把书翻过去，而是在阅读时用最短动作沉淀句子、笔记、红标、单词和复习材料。

当前产品以 macOS 为主，局域网网页端可以在 iPad 或手机浏览器里使用。Windows 不是不能做，但应该按层拆开适配，不能把 macOS 原生壳硬搬过去。

## 它解决什么

Apple Books 适合读书，但不适合高频精读。Click 解决的是另一件事：

| 阅读动作 | Click 的设计 |
| --- | --- |
| 聚焦一句话 | 单击句子，当前句子成为操作对象 |
| 查英文词 | 点击英文词，优先给出和上下文相关的释义 |
| 写备注 | 快速双击句子，直接记录判断 |
| 整句标红 | 右键、双指点按或长按，整句进入红标系统 |
| 复习沉淀 | 笔记、红标、单词、原句能回到同一个工作台 |
| 书库管理 | 收藏、作者、分类、自定义标签和批量整理集中处理 |

## 第一屏能力

Click 的首页不是装饰页，而是工作台：

| 区域 | 作用 |
| --- | --- |
| 继续阅读 | 直接回到上次阅读位置 |
| 最近阅读 | 用封面、进度、笔记数、红标数快速判断书的状态 |
| 最近沉淀 | 把刚写下的笔记和红标拉回视野 |
| 书库导航 | 按收藏、作者、分类、单词、笔记、红标进入不同工作流 |
| 批量整理 | 对多本书统一收藏、分类、隐藏或恢复 |

## 核心交互

### Mac

| 你想做什么 | 怎么操作 | 结果 |
| --- | --- | --- |
| 聚焦一句话 | 单击句子 | 当前句子高亮聚焦 |
| 查英文词 | 单击英文单词 | 弹出词义 |
| 写备注 | 快速双击句子 | 打开备注窗口 |
| 看已有备注 | 单击有备注的句子 | 显示这句话的备注 |
| 整句标红 | 右键句子 | 整句话变红或取消红标 |
| 整句标红 | 双指点按句子 | 整句话变红或取消红标 |
| 复制文字 | 拖选文字后按 `Command+C` | 复制选中文本 |
| 关闭弹窗 | `Esc` | 关闭备注、查词或抽屉 |

双击必须是快速连续两下。慢慢点两次会被当成两次单击。

### iPad / 浏览器

| 你想做什么 | 怎么操作 | 结果 |
| --- | --- | --- |
| 操作一句话 | 点击句子 | 底部出现句子操作栏 |
| 查英文词 | 点击英文单词 | 弹出词义 |
| 写备注 | 快速双击句子 | 打开备注 |
| 整句标红 | 长按句子 | 整句话变红或取消红标 |
| 翻页 | 左右滑动 | 上一页或下一页 |
| 调整字体 | 点 `Aa` | 调整字号、行高、边距 |

## 书库组织

Click 的书库整理不是“把书堆起来”，而是为后续学习服务。

| 组织方式 | 当前状态 |
| --- | --- |
| 收藏 | 支持单本收藏和批量收藏 |
| 作者 | 首页统计和作者分组 |
| 自定义分类 | 支持单本分类和批量分类 |
| 标签 | 书籍详情里维护标签 |
| 隐藏 / 恢复 | 非破坏式移除，避免误删书籍数据 |
| 笔记 / 红标 | 可以按书回到原文 |
| 单词本 | 书内词汇可以进入主动复习 |

## 系统形态

```mermaid
flowchart LR
    EPUB["EPUB 文件"] --> Importer["导入与解析"]
    Importer --> API["Reader API"]
    API --> DB[("PostgreSQL 本地数据库")]
    API --> Web["Click Web 工作台"]
    Web --> Mac["macOS App 壳"]
    Web --> LAN["局域网 iPad / 手机"]
    Web -. P1 .-> WinBrowser["Windows 浏览器版"]
    Web -. P2 .-> WinShell["Tauri / Electron 桌面壳"]
```

核心判断：阅读数据、解析逻辑和 Web 工作台应该跨平台；macOS 外壳、系统菜单、权限、打包签名不应该跨平台硬搬。

## Windows 适配

现在没有 Windows 原生版。可行，但要分阶段。

| 阶段 | 判断 | 做法 |
| --- | --- | --- |
| P1 | 最值得先做 | Windows 运行本地 Reader API，用浏览器打开 Click 工作台 |
| P2 | 可产品化 | 用 Tauri 或 Electron 包一层桌面壳，复用 Web UI |
| P3 | 最重 | 做 WinUI / .NET 原生阅读壳，只在交互已经稳定后考虑 |

可复用部分：

- `reader_api` 的 FastAPI 服务
- EPUB 导入、句子、笔记、红标、单词数据模型
- PostgreSQL schema 和迁移脚本
- 书库 Web UI 和局域网阅读页

需要重做或改造的部分：

- Swift / macOS App 壳
- WebKit 与 macOS 菜单交互
- macOS 权限、文件导入、打开方式绑定
- Apple 语音能力
- macOS 打包、签名和 LaunchServices 行为

结论很直接：Windows 不要先承诺“原生完整复刻”。第一步应该做 Windows Web Companion，把阅读工作台跑起来；第二步再考虑 Tauri / Electron。

## 当前边界

当前版本适合在开发机和同一局域网内使用，还不是最终公开发行版。

- 还没有正式签名安装包
- 还不是原生 iPad App
- 还没有云同步
- 还不适合公网访问
- PDF 不是当前重点
- 部分本地目录仍沿用历史兼容路径，这是为了不破坏已有数据

## 本地数据

Click 是本地优先软件。你的真实书籍、阅读位置、笔记、红标、查词记录和导出记录保存在本机数据库与本地应用目录里。

结构化数据使用 PostgreSQL：

```text
database: sentence_reader
schema: reader
```

局域网入口：

```text
http://<Mac 局域网 IP>:18180/library
http://<Mac 局域网 IP>:18180/lan/reader
```

## 从源码验证

常用验收命令：

```bash
./scripts/v1_acceptance.sh
./scripts/v21_ipad_lan_acceptance.sh
.venv-reader-api/bin/python -m pytest tests/test_reader_api_mock.py
.venv-reader-api/bin/python -m compileall reader_api scripts tests
python3 scripts/package_sentence_reader_app.py
python3 scripts/public_repo_privacy_smoke.py
```

前端静态冒烟：

```bash
.venv-reader-api/bin/python scripts/sentence_reader_library_ui_static_smoke.py
.venv-reader-api/bin/python scripts/reader_api_static_smoke.py
```

## 不进入 GitHub 的内容

为了避免仓库臃肿和泄露私人数据，GitHub 不包含：

- 真实书籍
- 本地数据库
- 完整词库 CSV
- 打包后的 App
- Python 虚拟环境
- 构建缓存
- 运行报告
- 真实界面截图
- 书籍封面或阅读内容图片

GitHub 只保存源码、文档、迁移脚本和小型测试样本。

## 文档入口

- [使用说明](docs/user_guide.md)
- [产品验收标准](docs/product_acceptance.md)
- [当前状态](docs/current_status.md)
- [产品路线图](docs/product_roadmap.md)
- [交互规则](docs/interaction_contract.md)
- [运行环境与可迁移性](docs/runtime_portability.md)

## 产品原则

```text
读书动作要短
句子操作要快
数据要本地可靠
AI 和在线服务只能增强，不能成为地基
```
