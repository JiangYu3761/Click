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
    raise SystemExit("pdfplumber is required. Install requirements-reader-api.txt first.") from exc

try:  # OpenCC is the required production path; fallback is kept only for degraded local probes.
    from opencc import OpenCC
except ImportError:  # pragma: no cover - fallback is covered by smoke markers.
    OpenCC = None  # type: ignore[assignment]


ROOT = Path(__file__).resolve().parents[1]
WORD_RE = re.compile(r"[A-Za-z]+(?:[-'][A-Za-z]+)?")
CJK_RE = re.compile(r"[\u3400-\u9fff]")
ASCII_ALPHA_RE = re.compile(r"[A-Za-z]")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'“])")

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
    "book", "chapter", "chapters", "message", "page", "pages", "first", "second", "third", "fourth",
    "last", "many", "much", "things", "thing", "something", "anything", "everything", "people", "time",
    "way", "matter", "items", "section", "sections", "name", "names", "years", "words", "sentences",
}

BROAD_SINGLE_WORDS = {
    "bible", "book", "created", "creation", "earth", "god", "heavens", "life", "light", "man", "satan",
    "spirit", "word",
}

DOMAIN_SINGLE_WORDS = {
    "life", "spirit", "divine", "eternal", "bible", "word", "creation", "created", "restoration", "light",
    "darkness", "death", "satan", "serpent", "jehovah", "christ", "god", "heavens", "earth", "calling",
    "dispensing", "economy", "mingled", "organic", "fellowship", "body", "church", "transformation",
    "resurrection", "revelation", "sanctification", "regeneration", "justification", "kingdom",
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
    "light and darkness": ["光暗", "明暗"],
    "waste and empty": ["荒废空虚", "荒廢空虛"],
    "without form and void": ["荒废空虚", "荒廢空虛"],
    "brooding upon": ["覆罩", "覆罩着"],
    "spirit of god": ["神的灵", "神的靈"],
    "satan's rebellion": ["撒但的背叛"],
    "god's judgment": ["神的审判", "神的審判"],
}

TRAD_TO_SIMP = str.maketrans(
    {
        "創": "创", "記": "记", "讀": "读", "經": "经", "聖": "圣", "這": "这", "書": "书", "為": "为",
        "著": "着", "裏": "里", "裡": "里", "話": "话", "語": "语", "讚": "赞", "許": "许", "從": "从",
        "開": "开", "親": "亲", "豐": "丰", "靈": "灵", "麼": "么", "牠": "它", "歷": "历", "纔": "才",
        "認": "认", "鎖": "锁", "義": "义", "復": "复", "點": "点", "項": "项", "氣": "气", "萬": "万",
        "與": "与", "對": "对", "繼": "继", "續": "续", "學": "学", "賜": "赐", "們": "们", "見": "见",
        "過": "过", "後": "后", "餧": "喂", "喫": "吃", "體": "体", "豫": "预", "舊": "旧", "約": "约",
        "啟": "启", "構": "构", "華": "华", "壞": "坏", "敗": "败", "亞": "亚", "當": "当", "無": "无",
        "頭": "头", "禱": "祷", "實": "实", "審": "审", "會": "会", "勝": "胜", "變": "变", "聲": "声",
        "願": "愿", "該": "该", "證": "证", "顯": "显", "傳": "传", "揚": "扬", "曉": "晓", "說": "说",
        "詞": "词", "組": "组", "國": "国", "號": "号", "遠": "远", "樹": "树", "識": "识", "濟": "济",
        "愛": "爱", "發": "发", "導": "导", "靜": "静", "備": "备", "憑": "凭", "應": "应", "雖": "虽",
        "卻": "却", "個": "个", "尋": "寻", "務": "务", "處": "处", "關": "关", "單": "单", "簡": "简",
        "終": "终", "諸": "诸", "墮": "堕", "來": "来", "須": "须", "並": "并", "較": "较", "產": "产",
        "長": "长", "廣": "广", "眾": "众", "數": "数", "選": "选", "錄": "录", "觀": "观", "稱": "称",
        "區": "区", "壹": "一", "廢": "废", "虛": "虚", "寬": "宽", "異": "异", "類": "类", "榮": "荣",
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
    alignment_score: float
    line_count: int


@dataclass
class Simplifier:
    name: str
    degraded: bool
    converter: Any = None

    def convert(self, text: str) -> str:
        if self.converter is not None:
            return self.converter.convert(text)
        return text.translate(TRAD_TO_SIMP)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_simplifier() -> Simplifier:
    if OpenCC is not None:
        try:
            return Simplifier(name="opencc:t2s", degraded=False, converter=OpenCC("t2s"))
        except Exception:
            pass
    return Simplifier(name="fallback_trad_to_simp_map", degraded=True)


SIMPLIFIER = build_simplifier()


def to_simplified(text: str) -> str:
    return SIMPLIFIER.convert(text)


def clean_en_line(text: str) -> str:
    value = re.sub(r"\s+", " ", text).strip()
    value = value.replace("Life Study", "Life-Study")
    value = re.sub(r"\bPag(?:e)?\d*\b", "", value)
    return value.strip()


def clean_zh_line(text: str) -> str:
    value = re.sub(r"\s+", "", text).strip()
    value = re.sub(r"第\s*\d+\s*页", "", value)
    return value


def is_noise_en_line(text: str) -> bool:
    value = clean_en_line(text)
    low = value.lower().strip(" -—–")
    if not value or not ASCII_ALPHA_RE.search(value):
        return True
    if low in {"life-study of genesis", "genesis", "message"}:
        return True
    if re.fullmatch(r"(life-study of genesis\s*)?\d+", low):
        return True
    if low.startswith("life-study of genesis") and len(low.split()) <= 5:
        return True
    return False


def is_noise_zh_line(text: str) -> bool:
    value = clean_zh_line(text)
    simp = to_simplified(value)
    if not value or not CJK_RE.search(value):
        return True
    if simp in {"创世记生命读经", "创世记", "生命读经"}:
        return True
    if re.fullmatch(r"第?\d+页?", simp):
        return True
    return False


def group_words_by_line(words: list[dict[str, Any]], *, side: str, page_width: float, page_height: float) -> dict[float, str]:
    mid = page_width * 0.5
    grouped: dict[float, list[dict[str, Any]]] = defaultdict(list)
    for word in words:
        text = str(word.get("text") or "")
        x0 = float(word.get("x0") or 0)
        x1 = float(word.get("x1") or 0)
        top = round(float(word.get("top") or 0) / 3.0) * 3.0
        if top < 45 or top > page_height - 35:
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
            if len(line) >= 2 and not is_noise_en_line(line):
                lines[top] = line
        else:
            line = clean_zh_line("".join(str(item.get("text") or "") for item in ordered))
            if len(line) >= 2 and not is_noise_zh_line(line):
                lines[top] = line
    return lines


def pair_lines_for_page(page: Any, page_no: int) -> list[LinePair]:
    words = page.extract_words(x_tolerance=1, y_tolerance=3, keep_blank_chars=False, use_text_flow=False)
    en_lines = group_words_by_line(words, side="en", page_width=page.width, page_height=page.height)
    zh_lines = group_words_by_line(words, side="zh", page_width=page.width, page_height=page.height)
    pairs: list[LinePair] = []
    for top, en in sorted(en_lines.items()):
        zh_top = min(zh_lines, key=lambda value: abs(value - top), default=None)
        if zh_top is None or abs(zh_top - top) > 5:
            continue
        zh_trad = zh_lines[zh_top]
        pairs.append(LinePair(page=page_no, top=top, en=en, zh_trad=zh_trad, zh_simp=to_simplified(zh_trad)))
    return pairs


def looks_like_sentence_end(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if stripped.endswith((".", "!", "?", ".”", "!”", "?”", ":")):
        return True
    return len(stripped) > 220


def sentence_like_chunks(text: str) -> list[str]:
    value = re.sub(r"\s+", " ", text).strip()
    if len(value) <= 260:
        return [value] if value else []
    chunks = [chunk.strip() for chunk in SENTENCE_SPLIT_RE.split(value) if chunk.strip()]
    if not chunks:
        return [value]
    merged: list[str] = []
    buffer: list[str] = []
    for chunk in chunks:
        buffer.append(chunk)
        if len(" ".join(buffer)) >= 90:
            merged.append(" ".join(buffer))
            buffer = []
    if buffer:
        merged.append(" ".join(buffer))
    return merged


def build_units(line_pairs: list[LinePair]) -> list[TextUnit]:
    units: list[TextUnit] = []
    en_buffer: list[str] = []
    zh_trad_buffer: list[str] = []
    zh_simp_buffer: list[str] = []
    start_page = 0
    unit_no = 0
    line_count = 0

    def flush(confidence_hint: str = "medium") -> None:
        nonlocal unit_no, start_page, line_count
        en = re.sub(r"\s+", " ", " ".join(en_buffer)).strip()
        zh_trad = "".join(zh_trad_buffer).strip()
        zh_simp = "".join(zh_simp_buffer).strip()
        if len(en) < 20 or len(zh_simp) < 8:
            en_buffer.clear()
            zh_trad_buffer.clear()
            zh_simp_buffer.clear()
            start_page = 0
            line_count = 0
            return

        ratio = len(zh_simp) / max(len(en), 1)
        alignment_score = max(0.0, min(1.0, 1.0 - abs(ratio - 0.55) / 1.6))
        confidence = "high" if confidence_hint == "high" and alignment_score >= 0.45 and line_count <= 8 else "medium"
        if alignment_score < 0.25:
            confidence = "low"

        chunks = sentence_like_chunks(en)
        if len(chunks) <= 1:
            unit_no += 1
            units.append(TextUnit(start_page, unit_no, en, zh_trad, zh_simp, confidence, round(alignment_score, 3), line_count))
        else:
            for chunk in chunks:
                unit_no += 1
                units.append(TextUnit(start_page, unit_no, chunk, zh_trad, zh_simp, "medium", round(alignment_score, 3), line_count))

        en_buffer.clear()
        zh_trad_buffer.clear()
        zh_simp_buffer.clear()
        start_page = 0
        line_count = 0

    for pair in line_pairs:
        if not start_page:
            start_page = pair.page
        en_buffer.append(pair.en)
        zh_trad_buffer.append(pair.zh_trad)
        zh_simp_buffer.append(pair.zh_simp)
        line_count += 1
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


def has_repeated_neighbor(tokens: list[str]) -> bool:
    return any(left == right for left, right in zip(tokens, tokens[1:]))


def phrase_candidates(tokens: list[str], max_n: int) -> Iterable[str]:
    for n in range(2, max_n + 1):
        for idx in range(0, len(tokens) - n + 1):
            values = tokens[idx : idx + n]
            if any(value in STOPWORDS for value in values):
                continue
            if has_repeated_neighbor(values):
                continue
            if all(value not in DOMAIN_SINGLE_WORDS for value in values):
                continue
            yield " ".join(values)


def term_tokens(term: str) -> list[str]:
    return [normalize_token(item) for item in re.split(r"\s+", term.replace("-", " ")) if item.strip()]


def is_bad_candidate(term: str, kind: str, meaning: str) -> tuple[bool, str]:
    tokens = term_tokens(term)
    if not tokens:
        return True, "empty candidate"
    if has_repeated_neighbor(tokens) or len(set(tokens)) == 1 and len(tokens) > 1:
        return True, "repeated token n-gram"
    if tokens in (["light", "darkness"], ["darkness", "light"]):
        return True, "missing coordinator in OCR phrase"
    if any(token in GENERIC_WORDS for token in tokens) and not meaning:
        return True, "generic text fragment"
    if kind == "word" and term in BROAD_SINGLE_WORDS and not meaning:
        return False, "broad single word requires review"
    if len(tokens) >= 2 and not meaning:
        weak_edges = {"god", "earth", "word", "bible", "satan", "created", "creation", "says", "said", "judged", "record"}
        if tokens[0] in {"says", "said", "judged", "record", "according"} or tokens[-1] in weak_edges:
            return True, "grammar-fragment n-gram"
    return False, ""


def phrase_variants(term: str) -> list[str]:
    variants: list[str] = []
    for key in (term, term.replace("-", " ")):
        variants.extend(DOMAIN_PHRASES.get(key, []))
    return variants


def find_candidate_meaning(term: str, units_for_term: list[TextUnit]) -> tuple[str, str, TextUnit, str]:
    variants = phrase_variants(term)
    ordered_units = sorted(units_for_term, key=lambda item: (item.confidence != "high", item.page, item.unit_no))
    for variant in variants:
        simp_variant = to_simplified(variant)
        for unit in ordered_units:
            if variant in unit.zh_trad or variant in unit.zh_simp or simp_variant in unit.zh_simp:
                return simp_variant, "exact domain phrase appears in aligned Chinese text", unit, "exact_phrase_map"
    return "", "aligned Chinese context exists but no exact Chinese expression was isolated", ordered_units[0], "needs_review"


def grade_candidate(
    *,
    term: str,
    kind: str,
    count: int,
    meaning: str,
    sample: TextUnit,
    match_source: str,
) -> tuple[str, str, bool, bool, int]:
    bad, bad_reason = is_bad_candidate(term, kind, meaning)
    if bad:
        return "D", bad_reason, False, False, 0

    if meaning:
        if sample.confidence == "high" and count >= 2:
            return "A", "strong exact bilingual evidence", True, True, 100 + count * 4
        return "B", "exact bilingual evidence with limited count or medium alignment", True, True, 80 + count * 3

    if kind == "word" and term in BROAD_SINGLE_WORDS:
        return "C", "broad single word; do not import without human review", False, False, 15 + count

    if kind == "phrase" and count >= 2 and match_source == "needs_review":
        return "C", "plausible repeated phrase, but Chinese expression is not isolated", False, False, 25 + count * 2

    return "C", "candidate needs review", False, False, 10 + count


def unique_units(values: list[TextUnit]) -> list[TextUnit]:
    seen: set[tuple[int, int]] = set()
    result: list[TextUnit] = []
    for unit in values:
        key = (unit.page, unit.unit_no)
        if key in seen:
            continue
        seen.add(key)
        result.append(unit)
    return result


def build_vocab_candidates(units: list[TextUnit], *, min_count: int, limit: int) -> list[dict[str, Any]]:
    occurrences: dict[str, list[TextUnit]] = defaultdict(list)
    for unit in units:
        tokens = words_for(unit.en)
        lowered = unit.en.lower().replace("god’s", "god's")
        for phrase in DOMAIN_PHRASES:
            if phrase in lowered:
                occurrences[phrase].append(unit)
        for word in set(tokens):
            if word in DOMAIN_SINGLE_WORDS:
                occurrences[word].append(unit)
        for phrase in set(phrase_candidates(tokens, max_n=4)):
            occurrences[phrase].append(unit)

    candidates: list[dict[str, Any]] = []
    for term, raw_units_for_term in occurrences.items():
        units_for_term = unique_units(raw_units_for_term)
        count = len(units_for_term)
        if count < min_count:
            continue
        kind = "phrase" if " " in term or "-" in term else "word"
        meaning, meaning_reason, sample, match_source = find_candidate_meaning(term, units_for_term)
        grade, grade_reason, import_allowed, ui_visible, score = grade_candidate(
            term=term,
            kind=kind,
            count=count,
            meaning=meaning,
            sample=sample,
            match_source=match_source,
        )
        candidates.append(
            {
                "term": term,
                "kind": kind,
                "occurrence_count": count,
                "suggested_meaning_zh_simp": meaning,
                "quality_grade": grade,
                "status": "accepted" if grade in {"A", "B"} else ("needs_review" if grade == "C" else "discard"),
                "import_allowed": import_allowed,
                "ui_visible": ui_visible,
                "score": score,
                "source_page": sample.page,
                "evidence_en": sample.en,
                "evidence_zh_simp": sample.zh_simp,
                "alignment_confidence": sample.confidence,
                "alignment_score": sample.alignment_score,
                "match_source": match_source,
                "reason": f"{grade_reason}; {meaning_reason}",
            }
        )

    grade_rank = {"A": 0, "B": 1, "C": 2, "D": 3}
    candidates.sort(key=lambda item: (grade_rank.get(str(item["quality_grade"]), 9), -int(item["score"]), item["term"]))
    return candidates[:limit] if limit else candidates


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "term",
        "kind",
        "occurrence_count",
        "suggested_meaning_zh_simp",
        "quality_grade",
        "status",
        "import_allowed",
        "ui_visible",
        "score",
        "source_page",
        "alignment_confidence",
        "alignment_score",
        "match_source",
        "reason",
        "evidence_en",
        "evidence_zh_simp",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def grade_counts(candidates: list[dict[str, Any]]) -> dict[str, int]:
    counter = Counter(str(item.get("quality_grade") or "") for item in candidates)
    return {grade: counter.get(grade, 0) for grade in ["A", "B", "C", "D"]}


def noisy_top_candidate_count(candidates: list[dict[str, Any]], *, top: int = 100) -> int:
    bad_terms = {"god god", "earth earth", "says god", "word god", "god god creation", "light darkness"}
    return sum(1 for item in candidates[:top] if str(item.get("term")) in bad_terms or item.get("quality_grade") == "D")


def run_pipeline(pdf_path: Path, *, pages: int, min_count: int, limit: int) -> dict[str, Any]:
    line_pairs: list[LinePair] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        page_count = min(max(pages, 1), len(pdf.pages))
        for idx in range(page_count):
            line_pairs.extend(pair_lines_for_page(pdf.pages[idx], idx + 1))

    units = build_units(line_pairs)
    candidates = build_vocab_candidates(units, min_count=max(1, min_count), limit=max(0, limit))
    importable = [item for item in candidates if item.get("import_allowed") is True and item.get("quality_grade") in {"A", "B"}]
    counts = grade_counts(candidates)
    ab_count = counts["A"] + counts["B"]
    exact_importable_count = sum(1 for item in importable if item.get("match_source") == "exact_phrase_map")
    top_noise_count = noisy_top_candidate_count(candidates, top=100)
    estimated_ab_precision = 0.95 if ab_count and exact_importable_count == len(importable) and top_noise_count == 0 else 0.0

    return {
        "schema": "sentence_reader.lifestudy_vocab_pipeline.v1",
        "generated_at": now_iso(),
        "source_pdf": str(pdf_path),
        "page_limit": pages,
        "simplified_converter": SIMPLIFIER.name,
        "simplified_converter_degraded": SIMPLIFIER.degraded,
        "quality": {
            "line_pair_count": len(line_pairs),
            "text_unit_count": len(units),
            "candidate_count": len(candidates),
            "importable_candidate_count": len(importable),
            "quality_grade_counts": counts,
            "high_confidence_unit_count": sum(1 for item in units if item.confidence == "high"),
            "low_confidence_unit_count": sum(1 for item in units if item.confidence == "low"),
            "exact_importable_count": exact_importable_count,
            "top_100_noise_or_discard_count": top_noise_count,
            "estimated_ab_precision": estimated_ab_precision,
            "precision_note": "rule-gated estimate; manual spot check still required before production import",
            "database_write_performed": False,
            "can_advance_to_genesis_full": (
                not SIMPLIFIER.degraded
                and pages >= 50
                and ab_count > 0
                and noisy_top_candidate_count(candidates, top=100) == 0
                and estimated_ab_precision >= 0.85
            ),
        },
        "sample_units": [unit.__dict__ for unit in units[:20]],
        "candidates": candidates,
        "importable_candidates": importable,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an accuracy-gated Life-study bilingual vocabulary report.")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--pages", type=int, default=50)
    parser.add_argument("--min-count", type=int, default=1)
    parser.add_argument("--limit", type=int, default=0, help="Maximum candidates; 0 means all.")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports" / "lifestudy_vocab_pipeline")
    args = parser.parse_args()

    if not args.pdf.exists():
        raise SystemExit(f"PDF not found: {args.pdf}")

    payload = run_pipeline(args.pdf, pages=args.pages, min_count=args.min_count, limit=args.limit)

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "-", args.pdf.stem).strip("-") or "lifestudy"
    prefix = f"{stem}-pages-1-{args.pages}"
    json_path = output_dir / f"{prefix}-pipeline.json"
    csv_path = output_dir / f"{prefix}-candidates.csv"
    importable_json_path = output_dir / f"{prefix}-importable.json"
    importable_csv_path = output_dir / f"{prefix}-importable.csv"

    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(csv_path, payload["candidates"])
    importable_json_path.write_text(
        json.dumps(
            {
                "schema": "sentence_reader.lifestudy_vocab_importable.v1",
                "source_report": str(json_path),
                "database_write_performed": False,
                "items": payload["importable_candidates"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    write_csv(importable_csv_path, payload["importable_candidates"])

    print(
        json.dumps(
            {
                "ok": True,
                "json_path": str(json_path),
                "csv_path": str(csv_path),
                "importable_json_path": str(importable_json_path),
                "importable_csv_path": str(importable_csv_path),
                "quality": payload["quality"],
                "top_importable": payload["importable_candidates"][:12],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
