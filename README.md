# Sentence Reader Mac

Sentence Reader 是一个本地优先的 Mac 精读软件。

它不是普通电子书阅读器。它的核心交互不是“选中文字再点一堆按钮”，而是围绕一句话快速完成阅读动作：

- 单击：聚焦 / 查词
- 双击：备注
- 右键或双指点按：整句标红
- 点击已有备注的句子：查看备注
- 横向滑动：翻页

一句话就是一个可操作对象。

## 你为什么需要它

Apple Books 可以阅读，但它不适合高频精读：

- 不能快速给整句话加备注
- 不能用双指点按整句标红
- 不能围绕一句话沉淀笔记
- 不能把阅读数据稳定保存在你自己的数据库里
- 很难把笔记继续接入 AI / Hermes / 个人知识系统

Sentence Reader 解决的是这个问题：让你在读书时用最少动作，把有价值的句子沉淀下来。

## 最常用的阅读动作

### Mac 端

| 你想做什么 | 怎么操作 | 结果 |
| --- | --- | --- |
| 聚焦一句话 | 单击句子 | 当前句子高亮聚焦 |
| 查英文词 | 单击英文单词 | 弹出词义 |
| 写备注 | 快速双击句子 | 打开备注窗口 |
| 看已有备注 | 单击有备注的句子 | 显示这句话的备注 |
| 整句标红 | 右键句子 | 整句话变红 / 取消标红 |
| 整句标红 | 双指点按句子 | 整句话变红 / 取消标红 |
| 复制文字 | 拖选文字后按 `Command+C` | 复制选中文本 |
| 关闭弹窗 | `Esc` | 关闭备注 / 查词 / 抽屉 |
| 退出软件 | `Command+Q` | 退出 App |

注意：**双击不是慢慢点两次。**

双击必须是快速连续两下。慢慢点两次会被当成两次单击，不会打开备注。

### iPad / 浏览器端

| 你想做什么 | 怎么操作 | 结果 |
| --- | --- | --- |
| 操作一句话 | 点击句子 | 底部出现句子操作栏 |
| 查英文词 | 点击英文单词 | 弹出词义 |
| 写备注 | 快速双击句子 | 打开备注 |
| 整句标红 | 长按句子 | 整句话变红 / 取消标红 |
| 翻页 | 左右滑动 | 上一页 / 下一页 |
| 调整字体 | 点 `Aa` | 调整字号、行高、边距 |
| 回书库 | 点 `书库` | 回到主界面 |

iPad 没有右键，所以用“长按句子”代替 Mac 上的右键 / 双指点按。

## 交互优先级

Sentence Reader 有一个重要规则：

**在正文句子上，Sentence Reader 的句子操作优先于系统默认菜单。**

也就是说：

- 你在句子上双指点按，优先是“整句标红”
- 不是优先弹出系统复制菜单
- 如果你要复制文字，请拖选文字后按 `Command+C`
- 如果你点的是输入框、按钮、备注框，系统默认复制 / 粘贴 / 编辑行为仍然保留

这个设计不是 bug。

这是这个软件的核心：让“整句标红”和“句子备注”足够快。

## 查词和备注会不会冲突

不会。

逻辑是：

- 单击英文词：查词
- 如果这一下其实是双击的第一下，系统会等一下
- 如果你马上第二下形成双击，就取消查词，打开备注
- 如果没有第二下，就执行查词

所以：

- 想查词：单击英文词
- 想备注：快速双击句子
- 想标红：右键 / 双指点按 / iPad 长按

## 书库怎么用

打开 App 后会进入 `书库`。

你可以：

- 导入 EPUB
- 继续阅读上次的书
- 点击封面进入正文
- 查看阅读进度
- 查看笔记数和红标数
- 进入 `笔记` 中心
- 进入 `红标` 中心
- 搜索书名、作者、笔记和红标内容

导入 EPUB 后，软件会复制一份到内部书库。

导入完成后，原来的 EPUB 文件可以移动或删除。

## 怎么打开

当前开发机上，App 位于：

```bash
build/Sentence Reader.app
```

打开：

```bash
open "build/Sentence Reader.app"
```

正常情况下，软件会直接进入 `书库` 首页。

## 数据保存在哪里

Sentence Reader 是本地优先软件。

你的数据主要保存在：

```text
~/Library/Application Support/SentenceReader
```

结构化数据保存在 PostgreSQL：

```text
database: jiangyu_os
schema: reader
```

保存内容包括：

- 书籍
- 阅读位置
- 句子备注
- 红标
- 语音备注
- 导出记录
- 查词记录

## iPad 怎么用

Mac 和 iPad 需要在同一个 Wi-Fi。

打开书库：

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

这是局域网功能，不是公网服务。

## 当前版本边界

当前版本适合在这台 Mac 上日常使用。

还不是最终公开发行版：

- 还没有签名安装包
- 还不是原生 iPad App
- 还没有云同步
- 还不适合公网访问
- 朋友电脑安装还需要继续整理
- PDF 不是当前重点

## 不上传到 GitHub 的内容

为了避免仓库臃肿和泄露私人数据，GitHub 不包含：

- 你的真实书籍
- 本地数据库
- 完整词库 CSV
- 打包后的 App
- Python 虚拟环境
- 构建缓存
- 运行报告

GitHub 只保存源码、文档、迁移脚本和小型测试样本。

## 从源码验证

常用验收命令：

```bash
./scripts/v1_acceptance.sh
./scripts/v21_ipad_lan_acceptance.sh
.venv-reader-api/bin/python -m pytest tests/test_reader_api_mock.py
.venv-reader-api/bin/python -m compileall reader_api scripts tests
python3 scripts/package_sentence_reader_app.py
```

## 主要文档

- [使用说明](docs/user_guide.md)
- [产品验收标准](docs/product_acceptance.md)
- [当前状态](docs/current_status.md)
- [产品路线图](docs/product_roadmap.md)
- [交互规则](docs/interaction_contract.md)
- [运行环境与可迁移性](docs/runtime_portability.md)

## 产品原则

Sentence Reader 的原则是：

```text
读书动作要短
句子操作要快
数据要本地可靠
AI 和在线服务只能增强，不能成为地基
```
