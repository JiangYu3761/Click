#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    import pdfplumber
except ImportError as exc:  # pragma: no cover - surfaced by CLI
    raise SystemExit("pdfplumber is required. Use the bundled Codex Python runtime or install pdfplumber.") from exc


ROOT = Path(__file__).resolve().parents[1]
WORD_RE = re.compile(r"[A-Za-z]+(?:[-'][A-Za-z]+)?")
CJK_RE = re.compile(r"[\u3400-\u9fff]")
ASCII_ALPHA_RE = re.compile(r"[A-Za-z]")

STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "also", "am", "an", "and", "any", "are",
    "as", "at", "be", "because", "been", "before", "being", "between", "both", "but", "by", "can",
    "cannot", "could", "did", "do", "does", "doing", "done", "during", "each", "even", "every", "few",
    "for", "from", "further", "had", "has", "have", "having", "he", "her", "here", "hers", "him",
    "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", "just", "many",
    "may", "me", "more", "most", "must", "my", "no", "nor", "not", "now", "of", "off", "on",
    "once", "one", "only", "or", "other", "our", "ours", "out", "over", "own", "same", "shall",
    "she", "should", "so", "some", "such", "than", "that", "the", "their", "them", "then", "there",
    "these", "they", "this", "those", "through", "to", "too", "under", "up", "us", "very", "was",
    "we", "were", "what", "when", "where", "which", "while", "who", "whom", "why", "will", "with",
    "within", "without", "would", "you", "your", "yours",
}

GENERIC_WORDS = {
    "book", "chapter", "message", "page", "pages", "first", "second", "third", "fourth", "last", "many",
    "much", "things", "something", "anything", "everything", "people", "time", "way", "matter", "items",
}

DOMAIN_SINGLE_WORDS = {
    "life", "spirit", "divine", "eternal", "bible", "word", "creation", "created", "restoration", "light",
    "darkness", "death", "satan", "serpent", "jehovah", "christ", "god", "heavens", "earth", "calling",
    "dispensing", "economy", "mingled", "organic", "fellowship", "body", "church", "transformation",
}

DOMAIN_PHRASES = {
    "life-study": ["生命读经", "生命讀經"],
    "life study": ["生命读经", "生命讀經"],
    "divine life": ["神圣的生命", "神聖的生命"],
    "eternal life": ["永远的生命", "永遠的生命"],
    "divine word": ["神圣的话语", "神聖的話語", "神圣的话", "神聖的話"],
    "god-breathed": ["神的呼出"],
    "god breathed": ["神的呼出"],
    "breath of god": ["神的呼出"],
    "spirit and life": ["灵与生命", "靈與生命"],
    "living word": ["活的话", "活的話"],
    "open heart": ["敞开的心", "敞開的心"],
    "open spirit": ["敞开的灵", "敞開的靈"],
    "exercise our spirit": ["运用我们的灵", "運用我們的靈"],
    "old testament": ["旧约", "舊約"],
    "new testament": ["新约", "新約"],
    "god created": ["神创造", "神創造"],
    "jehovah called": ["耶和华呼召", "耶和華呼召"],
    "serpent corrupted": ["蛇败坏", "蛇敗壞"],
    "tree of life": ["生命树", "生命樹"],
    "tree of knowledge": ["知识树", "知識樹"],
    "dry land": ["旱地"],
    "third day": ["第三天"],
    "light darkness": ["光暗"],
}

# Probe-only fallback. Production should use OpenCC; this map only keeps the first sample readable.
TRAD_TO_SIMP = str.maketrans(
    {
        "創": "创", "記": "记", "讀": "读", "經": "经", "聖": "圣", "這": "这", "書": "书", "為": "为",
        "著": "着", "裏": "里", "裡": "里", "話": "话", "語": "语", "讚": "赞", "許": "许", "從": "从",
        "開": "开", "週": "周", "親": "亲", "豐": "丰", "膏": "膏", "靈": "灵", "麼": "么", "麼": "么",
        "牠": "它", "歷": "历", "纔": "才", "認": "认", "鎖": "锁", "義": "义", "復": "复", "點": "点",
        "項": "项", "氣": "气", "萬": "万", "與": "与", "對": "对", "繼": "继", "續": "续", "學": "学",
        "查": "查", "賜": "赐", "們": "们", "見": "见", "過": "过", "後": "后", "餧": "喂", "喫": "吃",
        "體": "体", "豫": "预", "舊": "旧", "約": "约", "這": "这", "啟": "启", "示": "示", "構": "构",
        "華": "华", "壞": "坏", "敗": "败", "亞": "亚", "當": "当", "無": "无", "與": "与", "頭": "头",
        "禱": "祷", "實": "实", "審": "审", "判": "判", "會": "会", "勝": "胜", "裏": "里", "變": "变",
        "聲": "声", "願": "愿", "該": "该", "證": "证", "顯": "显", "穹": "穹", "傳": "传", "揚": "扬",
        "曉": "晓", "諉": "诿", "說": "说", "詞": "词", "組": "组", "國": "国", "號": "号",
        "遠": "远", "樹": "树", "識": "识", "濟": "济", "愛": "爱", "發": "发", "導": "导",
        "靜": "静", "備": "备", "憑": "凭", "應": "应", "雖": "虽", "卻": "却", "個": "个",
        "復": "复", "尋": "寻", "務": "务", "處": "处", "關": "关", "單": "单", "簡": "简",
        "終": "终", "諸": "诸", "墮": "堕", "來": "来", "經": "经", "須": "须", "並": "并",
        "較": "较", "產": "产", "長": "长", "廣": "广", "眾": "众", "數": "数", "產": "产",
        "選": "选", "錄": "录", "觀": "观", "願": "愿", "稱": "称", "區": "区", "壹": "一",
    }
)


@dataclass
class LinePair:
    page: int
    top: float
    en: str
    zh_trad: str
    zh_simp: str


@dataclass
class TextUnit:
    page: int
    unit_no: int
    en: str
    zh_trad: str
    zh_simp: str
    confidence: str


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def to_simplified_probe(text: str) -> str:
    return text.translate(TRAD_TO_SIMP)


def clean_en_line(text: str) -> str:
    value = re.sub(r"\s+", " ", text).strip()
    value = value.replace("Life Study", "Life-Study")
    value = re.sub(r"\bPag(?:e)?\d*\b", "", value)
    return value.strip()


def clean_zh_line(text: str) -> str:
    value = re.sub(r"\s+", "", text).strip()
    value = value.replace("創世記生命讀經第篇第页", "")
    return value


def group_words_by_line(words: list[dict[str, Any]], *, side: str, page_width: float) -> dict[float, str]:
    mid = page_width * 0.5
    grouped: dict[float, list[dict[str, Any]]] = defaultdict(list)
    for word in words:
        text = str(word.get("text") or "")
        x0 = float(word.get("x0") or 0)
        x1 = float(word.get("x1") or 0)
        top = round(float(word.get("top") or 0) / 3.0) * 3.0
        if top < 45:
            continue
        if side == "en" and x0 < mid + 8 and ASCII_ALPHA_RE.search(text):
            grouped[top].append(word)
        elif side == "zh" and x1 > mid - 8 and CJK_RE.search(text):
            grouped[top].append(word)

    lines: dict[float, str] = {}
    for top, items in grouped.items():
        ordered = sorted(items, key=lambda item: float(item.get("x0") or 0))
        if side == "en":
            line = clean_en_line(" ".join(str(item.get("text") or "") for item in ordered))
            if len(line) >= 2:
                lines[top] = line
        else:
            line = clean_zh_line("".join(str(item.get("text") or "") for item in ordered))
            if len(line) >= 2:
                lines[top] = line
    return lines


def pair_lines_for_page(page: Any, page_no: int) -> list[LinePair]:
    words = page.extract_words(x_tolerance=1, y_tolerance=3, keep_blank_chars=False, use_text_flow=False)
    en_lines = group_words_by_line(words, side="en", page_width=page.width)
    zh_lines = group_words_by_line(words, side="zh", page_width=page.width)
    pairs: list[LinePair] = []
    for top, en in sorted(en_lines.items()):
        zh_top = min(zh_lines, key=lambda value: abs(value - top), default=None)
        if zh_top is None or abs(zh_top - top) > 5:
            continue
        zh_trad = zh_lines[zh_top]
        pairs.append(LinePair(page=page_no, top=top, en=en, zh_trad=zh_trad, zh_simp=to_simplified_probe(zh_trad)))
    return pairs


def looks_like_sentence_end(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if stripped.endswith((".", "!", "?", ".”", "!”", "?”")):
        return True
    if len(stripped) > 260:
        return True
    return False


def build_units(line_pairs: list[LinePair]) -> list[TextUnit]:
    units: list[TextUnit] = []
    en_buffer: list[str] = []
    zh_trad_buffer: list[str] = []
    zh_simp_buffer: list[str] = []
    start_page = 0
    unit_no = 0

    def flush(confidence: str = "medium") -> None:
        nonlocal unit_no, start_page
        en = re.sub(r"\s+", " ", " ".join(en_buffer)).strip()
        zh_trad = "".join(zh_trad_buffer).strip()
        zh_simp = "".join(zh_simp_buffer).strip()
        if len(en) >= 20 and len(zh_simp) >= 8:
            unit_no += 1
            units.append(
                TextUnit(
                    page=start_page,
                    unit_no=unit_no,
                    en=en,
                    zh_trad=zh_trad,
                    zh_simp=zh_simp,
                    confidence=confidence,
                )
            )
        en_buffer.clear()
        zh_trad_buffer.clear()
        zh_simp_buffer.clear()
        start_page = 0

    for pair in line_pairs:
        if not start_page:
            start_page = pair.page
        en_buffer.append(pair.en)
        zh_trad_buffer.append(pair.zh_trad)
        zh_simp_buffer.append(pair.zh_simp)
        if looks_like_sentence_end(pair.en):
            ratio = len("".join(zh_simp_buffer)) / max(len(" ".join(en_buffer)), 1)
            confidence = "high" if 0.25 <= ratio <= 2.3 else "medium"
            flush(confidence)
    if en_buffer:
        flush("medium")
    return units


def normalize_token(value: str) -> str:
    return value.lower().strip("-'").replace("’", "'")


def words_for(text: str) -> list[str]:
    result = []
    for match in WORD_RE.finditer(text):
        word = normalize_token(match.group(0))
        if len(word) < 3 or word in STOPWORDS:
            continue
        result.append(word)
    return result


def phrase_candidates(tokens: list[str], max_n: int) -> Iterable[str]:
    for n in range(2, max_n + 1):
        for idx in range(0, len(tokens) - n + 1):
            values = tokens[idx : idx + n]
            if any(value in STOPWORDS for value in values):
                continue
            if all(value not in DOMAIN_SINGLE_WORDS for value in values):
                continue
            yield " ".join(values)


def candidate_meaning(term: str, zh_trad: str, zh_simp: str) -> tuple[str, str, str]:
    variants = DOMAIN_PHRASES.get(term, [])
    for variant in variants:
        if variant in zh_trad or variant in zh_simp:
            return to_simplified_probe(variant), "confirmed", "known domain phrase appears in aligned Chinese text"
    compact = term.replace("-", " ")
    variants = DOMAIN_PHRASES.get(compact, [])
    for variant in variants:
        if variant in zh_trad or variant in zh_simp:
            return to_simplified_probe(variant), "confirmed", "known domain phrase appears in aligned Chinese text"
    return "", "needs_review", "aligned Chinese context is available, but no exact phrase match was confirmed"


def build_vocab_candidates(units: list[TextUnit], *, min_count: int, limit: int) -> list[dict[str, Any]]:
    occurrences: dict[str, list[TextUnit]] = defaultdict(list)
    word_counts: Counter[str] = Counter()
    phrase_counts: Counter[str] = Counter()

    for unit in units:
        tokens = words_for(unit.en)
        word_counts.update(tokens)
        phrase_counts.update(phrase_candidates(tokens, max_n=4))
        lowered = unit.en.lower().replace("god’s", "god's")
        for phrase in DOMAIN_PHRASES:
            if phrase in lowered:
                phrase_counts[phrase] += 2
                occurrences[phrase].append(unit)
        for word in set(tokens):
            if word in DOMAIN_SINGLE_WORDS:
                occurrences[word].append(unit)
        for phrase in set(phrase_candidates(tokens, max_n=4)):
            occurrences[phrase].append(unit)

    candidates: list[dict[str, Any]] = []
    for term, units_for_term in occurrences.items():
        count = len(units_for_term)
        if count < min_count:
            continue
        sample = units_for_term[0]
        meaning, status, reason = candidate_meaning(term, sample.zh_trad, sample.zh_simp)
        kind = "phrase" if " " in term or "-" in term else "word"
        score = count * (4 if kind == "phrase" else 1)
        if status == "confirmed":
            score += 25
        if term in DOMAIN_PHRASES:
            score += 15
        if term in DOMAIN_SINGLE_WORDS:
            score += 5
        candidates.append(
            {
                "term": term,
                "kind": kind,
                "occurrence_count": count,
                "suggested_meaning_zh_simp": meaning,
                "status": status,
                "score": score,
                "source_page": sample.page,
                "evidence_en": sample.en,
                "evidence_zh_simp": sample.zh_simp,
                "alignment_confidence": sample.confidence,
                "reason": reason,
            }
        )

    candidates.sort(key=lambda item: (-int(item["score"]), item["status"], item["term"]))
    return candidates[:limit] if limit else candidates


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "term",
        "kind",
        "occurrence_count",
        "suggested_meaning_zh_simp",
        "status",
        "score",
        "source_page",
        "alignment_confidence",
        "reason",
        "evidence_en",
        "evidence_zh_simp",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe Life-study bilingual PDF sentence alignment and vocab candidates.")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--pages", type=int, default=20)
    parser.add_argument("--min-count", type=int, default=1)
    parser.add_argument("--limit", type=int, default=120)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports" / "lifestudy_vocab_probe")
    args = parser.parse_args()

    if not args.pdf.exists():
        raise SystemExit(f"PDF not found: {args.pdf}")

    line_pairs: list[LinePair] = []
    with pdfplumber.open(str(args.pdf)) as pdf:
        page_count = min(max(args.pages, 1), len(pdf.pages))
        for idx in range(page_count):
            line_pairs.extend(pair_lines_for_page(pdf.pages[idx], idx + 1))

    units = build_units(line_pairs)
    candidates = build_vocab_candidates(units, min_count=max(1, args.min_count), limit=max(0, args.limit))

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "-", args.pdf.stem).strip("-") or "lifestudy"
    json_path = output_dir / f"{stem}-pages-1-{args.pages}-probe.json"
    csv_path = output_dir / f"{stem}-pages-1-{args.pages}-vocab.csv"

    payload = {
        "schema": "sentence_reader.lifestudy_vocab_probe.v1",
        "generated_at": now_iso(),
        "source_pdf": str(args.pdf),
        "page_limit": args.pages,
        "simplified_converter": "probe_fallback_map",
        "quality": {
            "line_pair_count": len(line_pairs),
            "text_unit_count": len(units),
            "candidate_count": len(candidates),
            "confirmed_candidate_count": sum(1 for item in candidates if item.get("status") == "confirmed"),
            "needs_review_count": sum(1 for item in candidates if item.get("status") == "needs_review"),
            "high_confidence_unit_count": sum(1 for item in units if item.confidence == "high"),
        },
        "sample_units": [unit.__dict__ for unit in units[:20]],
        "candidates": candidates,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(csv_path, candidates)

    print(
        json.dumps(
            {
                "ok": True,
                "json_path": str(json_path),
                "csv_path": str(csv_path),
                "quality": payload["quality"],
                "top_candidates": candidates[:12],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
