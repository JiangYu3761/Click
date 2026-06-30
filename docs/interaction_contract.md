# Sentence Reader Interaction Contract

Updated: 2026-06-29

## Decision

Sentence Reader uses a sentence-first interaction contract inside the reading surface.

This does not change macOS or iPadOS globally. It only decides which events the Sentence Reader reading surface claims before WebKit or the operating system default menu handles them.

## Priority Rules

### 中文快捷命令说明

| 场景 | 操作 | 结果 |
| --- | --- | --- |
| Mac 正文句子 | 单击句子 | 聚焦句子；已有备注时显示备注预览 |
| Mac 英文单词 | 单击英文词 | 查词 |
| Mac 正文句子 | 快速双击句子 | 打开备注流程 |
| Mac 正文句子 | 慢慢点两次 | 两次单击，不等于双击 |
| Mac 正文句子 | 双指点按 | 整句标红 / 取消标红 |
| Mac 英文单词 | `Option` + 双击 | 备用查词路径 |
| Mac 选中文字 | `Command+C` | 复制选中文字 |
| Mac 应用 | `Command+Q` | 退出 Sentence Reader |
| iPad 正文句子 | 点击句子 | 显示句子操作栏 |
| iPad 英文单词 | 点击英文词 | 查词 |
| iPad 正文句子 | 快速双击句子 | 打开备注流程 |
| iPad 正文句子 | 慢慢点两次 | 两次点击，不等于双击 |
| iPad 句子操作栏 | 点 `红标` | 整句标红 / 取消标红 |
| iPad 阅读页 | 左右滑动 | 翻页 |
| 桌面 Web / Windows 路线 | 聚焦句子后 `N` | 添加备注 |
| 桌面 Web / Windows 路线 | 聚焦句子后 `R` | 整句标红 / 取消标红 |
| 桌面 Web / Windows 路线 | 聚焦句子后 `V` | 添加语音备注 |
| 桌面 Web / Windows 路线 | `Esc` | 关闭弹窗、抽屉或取消聚焦 |

`双击` means two quick clicks/taps inside the system double-click interval. Two slow clicks/taps are intentionally treated as two separate single-click actions.

| Area | Gesture / Key | Owner | Result |
| --- | --- | --- | --- |
| Sentence text | Single click / tap | Sentence Reader | Focus the sentence and show note preview if it already has a note |
| English word in sentence text | Single click / tap | Sentence Reader | Look up the clicked word after a short delay, cancelled by double click / double tap |
| Sentence text | Double click / double tap | Sentence Reader | Open sentence note flow |
| Sentence text | Option + double click | Sentence Reader, then dictionary/vocab flow | Backup lookup path for pointer devices |
| Mac sentence text | Two-finger tap | Sentence Reader | Toggle whole-sentence red highlight |
| iPad sentence action bar | Red button | Sentence Reader | Toggle whole-sentence red highlight |
| Active text selection | Command+C | System/WebKit | Copy selected text |
| Mac app | Command+Q | System-style app command | Quit Sentence Reader |
| Active text selection outside sentence text | Context menu | System/WebKit | Show copy/search/share actions |
| Inputs, textareas, buttons, controls | Click, context menu, keyboard | System/WebKit | Preserve editing, copy, paste, focus, button activation |
| Page surface | Horizontal wheel/swipe or page keys | Sentence Reader | Turn page once with cooldown |
| Desktop Web / Windows route focused sentence | N / R / V | Sentence Reader | Note, red highlight, or voice note |
| Overlays/sheets | Esc | Sentence Reader first | Close sheet/toast/focus before falling through |

## Hard Rule

If a two-finger tap lands on `.sr-sentence`, Sentence Reader owns it and toggles red highlight, even when text selection exists.

The copy path is `Command+C` or a context menu outside sentence text. This is intentional: whole-sentence red highlight is the app's core shortcut and must not be silently replaced by a menu flow.

English lookup is intentionally attached to the clicked word, not the whole sentence. If the click is actually the first click of a double-click, the pending lookup is cancelled and the double-click note flow wins.

## Why This Is Reasonable

Sentence Reader exists because Apple Books and default WebKit reading do not provide the desired whole-sentence annotation workflow. Therefore, sentence-level gestures must win on sentence text.

At the same time, Sentence Reader should not fight the operating system in editing or control areas. Text fields, buttons, settings, file inputs, note editors, and non-sentence selection zones keep normal system behavior.

## Implementation Points

- Mac native reader: `Probe/NativeSentenceReader/SentenceReaderNative.swift`
- iPad/LAN reader: `reader_api/app.py`
- Contract marker: `sentence-reader-interaction-v1`
- English lookup marker: `english-click-lookup` / `english-tap-lookup`
- Static guard: `scripts/sentence_reader_interaction_contract_smoke.py`

## Non-Goals

- Do not change global macOS or iPadOS gestures.
- Do not make the system context menu the primary sentence annotation path.
- Do not use long press as the Mac primary red-highlight gesture.
- Do not route Mac reading through `/lan/reader`.
