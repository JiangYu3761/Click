# Click Mobile App Shell Plan

更新日期：2026-06-30

## 一句话说明

Click 移动端 App 壳是一个全屏沉浸式入口。它连接同一局域网里的 Mac，打开 Mac 上已经运行的 Click 书库和阅读页，让 iPad / Android 不再通过 Safari 或 Chrome 地址栏阅读。

第一版不是新阅读器，不做移动端本地数据库，不复制书到移动端，也不做云同步。

## 为什么要做

当前 iPad / Android 已经可以通过浏览器访问：

```text
http://<mac-lan-ip>:18180/library
http://<mac-lan-ip>:18180/lan/reader
```

这个路线功能可用，但不像一个长期阅读 App：

- 有浏览器地址栏和工具栏。
- 返回、刷新、重连不够自然。
- 断线时不容易知道该检查什么。
- 不适合固定在主屏幕作为日常入口。

移动端 App 壳要解决的是入口体验，不是重新实现阅读系统。

## 产品边界

移动端 App 壳属于 Click 的客户端入口。

```text
iPad / Android App
-> 全屏 WebView
-> Mac Reader API
-> /library
-> /lan/reader
-> PostgreSQL / EPUB / 笔记 / 红标 / 查词
```

数据仍然保存在 Mac：

- EPUB 内部副本：`~/Library/Application Support/SentenceReader/Books`
- PostgreSQL 数据库：Mac 本机 Reader API 使用的 `sentence_reader`
- 笔记、红标、阅读位置、查词记录：继续走现有 Reader API

## 不是什么

第一版明确不做：

- iPad 本地书库
- Android 本地书库
- 移动端导入 EPUB
- 移动端本地 PostgreSQL
- 移动端离线阅读
- 移动端本地 FunASR
- 云同步
- App Store 正式上架
- Google Play 正式上架
- 第二套阅读器

这些不是当前最重要的问题。当前最重要的是把浏览器访问变成沉浸式 App 入口。

## 第一版体验

第一次打开 App，显示连接页：

```text
Click

连接你的 Mac

Mac 地址：
[ <mac-lan-ip> ]

端口：
[ 18180 ]

[ 连接 ]
```

连接成功后，直接进入：

```text
http://<mac-lan-ip>:18180/library
```

点击一本书后，继续进入现有阅读页：

```text
/lan/reader
```

整个过程不出现 Safari / Chrome 的地址栏。

## 移动端壳保留的按钮

不要做复杂工具栏。App 壳只保留少数必要入口：

- 回到书库
- 刷新
- 更换 Mac 地址
- 连接状态提示

阅读、笔记、红标、查词和语音入口继续由现有 `/library` 和 `/lan/reader` 提供。

## iPad P1

iPad 使用：

```text
SwiftUI + WKWebView
```

第一版能力：

- App 名称：`Click`
- 全屏打开
- 输入 Mac IP 和端口
- 保存上次连接地址
- 默认进入 `/library`
- 支持进入 `/lan/reader`
- 支持返回书库
- 支持刷新当前页
- 连接失败时显示人话提示

安装方式：

- 自己用：Xcode 直接装到 iPad
- 少量朋友：Ad Hoc
- 更大范围测试：TestFlight

iPad 不上架安装的难点不是 WebView 开发，而是 Apple 签名、设备授权和测试分发。

## Android P1

Android 使用：

```text
Kotlin WebView
```

第一版能力：

- App 名称：`Click`
- 全屏打开
- 输入 Mac IP 和端口
- 保存上次连接地址
- 默认进入 `/library`
- 支持进入 `/lan/reader`
- 支持返回书库
- 支持刷新当前页
- 连接失败时显示人话提示
- 生成可手动安装的 APK

Android 分发比 iPad 更自由，但仍需要签名 APK，并向用户说明安装来源权限。

## 阶段顺序

| 阶段 | 做什么 | 验收 |
| --- | --- | --- |
| P1 iPad 壳 | SwiftUI + WKWebView、连接页、保存 Mac 地址、全屏打开 `/library` | iPad 打开像 App，不进 Safari，能进入书库和阅读页 |
| P2 Android 壳 | Kotlin WebView、连接页、生成 APK | Android 安装 APK 后能进入同一套书库和阅读页 |
| P3 移动端体验补齐 | 返回、刷新、断线提示、权限、横竖屏、安全区 | 日常阅读不别扭 |
| P4 分发整理 | iPad Ad Hoc/TestFlight、Android APK 签名 | 能发给朋友安装并说明限制 |

## P1 验收标准

iPad P1 通过需要满足：

1. iPad 上看到的是 Click App，不是 Safari。
2. 打开后能输入并保存 Mac 地址。
3. 能连接 Mac Reader API。
4. 成功进入 `/library`。
5. 点书能进入 `/lan/reader`。
6. 没有浏览器地址栏。
7. 可以返回书库。
8. 可以刷新当前页。
9. 可以更换 Mac 地址。
10. 连接失败时提示检查 Mac 是否开机、是否同一 Wi-Fi、18180 是否运行。
11. 不破坏现有 Mac App、iPad 浏览器访问、Reader API、PostgreSQL、笔记、红标、查词和语音入口。

Android P1 通过需要满足：

1. 能生成签名 APK。
2. Android 安装后显示 Click。
3. 输入 Mac 地址后进入 `/library`。
4. 点书进入 `/lan/reader`。
5. 没有浏览器地址栏。
6. 可以返回、刷新、改地址。
7. 不影响 Mac 上的数据保存。

## 风险和约束

- Mac 和移动设备必须在同一局域网。
- Mac Reader API 必须监听 `0.0.0.0:18180`。
- Mac IP 可能变化，后续可考虑二维码或 Bonjour 自动发现。
- iPad WKWebView 的麦克风、文件上传、剪贴板权限需要单独验收。
- Android WebView 在不同系统版本上的权限行为需要单独验收。
- 移动端壳不会解决干净新 Mac 安装问题；它依赖 Mac 端服务已经可用。

## 推荐当前主任务

先做 `Click iPad Shell P1`。

理由：

- 当前最明确的痛点是 iPad 浏览器不沉浸。
- iPad 壳验证成功后，Android 壳可以复用同一套产品逻辑。
- 不会破坏现有阅读器和数据链路。

## 最终形态

```text
Mac App
= 数据中心 + 本地阅读 + Reader API

iPad App
= 沉浸式阅读入口

Android App
= 沉浸式阅读入口
```

三个入口，一套 Click 阅读系统。
