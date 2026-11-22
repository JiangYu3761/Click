#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NATIVE_READER = ROOT / "Probe" / "NativeSentenceReader" / "SentenceReaderNative.swift"


def fail(message: str) -> None:
    raise SystemExit(f"native lookup card UI static smoke FAIL: {message}")


def require(text: str, needle: str) -> None:
    if needle not in text:
        fail(f"missing `{needle}`")


def extract_function(text: str, name: str) -> str:
    marker = f"private func {name}"
    start = text.find(marker)
    if start < 0:
        fail(f"missing function `{name}`")

    brace_start = text.find("{", start)
    if brace_start < 0:
        fail(f"function `{name}` has no body")

    depth = 0
    for index in range(brace_start, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]

    fail(f"function `{name}` body is not closed")
    return ""


def main() -> int:
    text = NATIVE_READER.read_text(encoding="utf-8")
    show_lookup = extract_function(text, "showLookupAlert")
    show_correction = extract_function(text, "showLookupCorrectionPanel")
    show_evidence = extract_function(text, "showLookupEvidenceAlert")

    for marker in [
        "func correctLookupMeaning(bookID: String, word: String, meaning: String, sentenceIndex: String?, sentence: String?) -> [String: Any]?",
        "path: \"/books/\\(bookID)/lookup-corrections\"",
        "private final class LocalReaderSpeech",
        "private final class LookupWordButton",
        "acceptsFirstMouse",
        "LookupPronunciation.label",
        "AVAudioPlayer(data: data)",
        "self.synthesis === finished",
        "private func decorateLookupActionButtons",
        "private static func lookupPartOfSpeechTitle",
        "private static func lookupPartOfSpeechShortTitle",
        "读释义",
        "speaker.wave.2.fill",
        ".sr-word-focused",
        "function focusWordHit",
        "function lookupWordHitFromEvent",
    ]:
        require(text, marker)

    for marker in [
        "alert.informativeText = \"\"",
        "makeLookupActionButton(",
        "title: displayWord",
        "size: 34",
        "LookupWordButton(title: displayWord",
        "clickableWordButton.toolTip = \"点击朗读单词\"",
        "clickableWordButton.alignment = .center",
        "已点击单词，准备朗读",
        "LookupActionTarget { [weak self] in",
        "withExtendedLifetime(lookupActionTargets)",
        "title: \"读释义\"",
        "title: \"证据\"",
        "title: \"纠错\"",
        "symbolName: \"pencil\"",
        "showLookupCorrectionPanel(",
        "textView.alignment = .center",
        "textView.textContainerInset = NSSize(width: 0, height: 17)",
        "speakReaderText(speakMeaning, chinese: true)",
        "speakReaderText(displayWord, chinese: false)",
        "alert.addButton(withTitle: \"关闭\")",
    ]:
        require(show_lookup, marker)

    for marker in [
        "alert.messageText = \"修正释义\"",
        "alert.addButton(withTitle: \"保存\")",
        "alert.addButton(withTitle: \"取消\")",
        "correctLookupMeaning(",
        "已保存纠错",
        "纠错保存失败",
        "payload: [\"item\": updated]",
    ]:
        require(show_correction, marker)

    for forbidden in [
        "(\"读句\", \"speak_sentence\")",
        "(\"读词\", \"speak_word\")",
        "(\"读释义\", \"speak_meaning\")",
        "title: \"读词\"",
        "英文例句：",
        "对应中文：",
    ]:
        if forbidden in show_lookup:
            fail(f"default lookup card still contains primary evidence/noise marker `{forbidden}`")

    ordinary_click = text.split("claimSentenceEvent(event);\n            focusWordHit(hit);", 1)
    if len(ordinary_click) != 2 or not re.search(r"post\(\{\s*type: 'lookup',\s*word: hit.word", ordinary_click[1].split("return;", 1)[0]):
        fail("ordinary click must focus the word and post the lookup")

    for marker in [
        "这些信息用于复核，不作为默认查词内容。",
        "英文上下文：",
        "中文证据：",
        "来源：",
        "对齐：",
        "本书出现：",
        "(\"复习\", \"reviewing\")",
        "(\"掌握\", \"known\")",
    ]:
        require(show_evidence, marker)

    print("native lookup card UI static smoke PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
