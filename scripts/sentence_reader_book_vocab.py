#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import os
import posixpath
import re
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE_URL = "postgresql://localhost/jiangyu_os"
WORD_RE = re.compile(r"[A-Za-z]+(?:[’'][A-Za-z]+)?")

STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "also", "am", "an", "and", "any",
    "are", "as", "at", "be", "because", "been", "before", "being", "between", "both", "but", "by",
    "can", "cannot", "could", "did", "do", "does", "doing", "done", "during", "each", "even", "every",
    "few", "for", "from", "further", "had", "has", "have", "having", "he", "her", "here", "hers",
    "him", "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", "just",
    "many", "may", "me", "more", "most", "must", "my", "no", "nor", "not", "now", "of", "off", "on",
    "once", "one", "only", "or", "other", "our", "ours", "out", "over", "own", "same", "shall",
    "she", "should", "so", "some", "such", "than", "that", "the", "their", "them", "then", "there",
    "these", "they", "this", "those", "through", "to", "too", "under", "up", "us", "very", "was",
    "we", "were", "what", "when", "where", "which", "while", "who", "whom", "why", "will", "with",
    "within", "without", "would", "you", "your", "yours",
    "ch", "cwwl", "day", "days", "et", "etc", "john", "james", "jude", "luke", "mark", "matthew",
    "morning", "nourishment", "page", "pages", "paul", "peter", "pp", "psa", "reading", "rom",
    "scripture", "verses", "vol", "week",
    "andrew", "christ", "elijah", "god", "jesus", "lord", "murray",
}

LEMMA_EXCEPTIONS = {
    "abides": "abide",
    "abiding": "abide",
    "accomplished": "accomplish",
    "accomplishing": "accomplish",
    "constituted": "constitute",
    "constituting": "constitute",
    "dispensed": "dispense",
    "dispenses": "dispense",
    "dispensing": "dispense",
    "expressed": "express",
    "expressing": "express",
    "indwelling": "indwell",
    "mingled": "mingle",
    "mingling": "mingle",
    "prayed": "pray",
    "prayer": "prayer",
    "prayers": "prayer",
    "praying": "pray",
    "transformed": "transform",
    "transforming": "transform",
}

BOOK_GLOSSARY = {
    "body": "身体",
    "constitution": "构成",
    "constitute": "构成",
    "consummation": "终极完成",
    "consummate": "终极完成",
    "dispense": "分赐",
    "dispensing": "分赐",
    "economy": "经纶",
    "expression": "彰显",
    "express": "彰显",
    "fellowship": "交通",
    "church": "召会",
    "divine": "神圣",
    "faith": "信",
    "grace": "恩典",
    "holiness": "圣别",
    "indwell": "内住",
    "indwelling": "内住",
    "life": "生命",
    "mingled": "调和",
    "mingle": "调和",
    "ministry": "职事",
    "organic": "生机的",
    "righteousness": "公义",
    "saint": "圣徒",
    "saints": "圣徒",
    "transformation": "变化",
    "transform": "变化",
}

BOOK_GLOSSARY_VARIANTS = {
    "fellowship": ["交通", "相交"],
    "mingle": ["调和", "调成"],
    "transform": ["变化", "变成", "改变"],
    "transformation": ["变化", "改变"],
}

CONTEXT_PARAPHRASE_RULES = [
    {
        "surface": "constitute",
        "meaning": "构成",
        "english": "do not constitute the ministry",
        "chinese": "还没有话语的职事",
        "reason": "The Chinese renders the negative clause by paraphrase: 'do not constitute' -> '还没有'.",
    },
    {
        "surface": "fellowshipped",
        "meaning": "商量",
        "english": "fellowshipped with God",
        "chinese": "和神商量",
        "reason": "The Chinese sentence translates this verbal use of fellowship as 商量.",
    },
    {
        "surface": "mingle",
        "meaning": "调和",
        "english": "mingle together",
        "chinese": "一起祷告",
        "reason": "The Chinese sentence paraphrases the mingling as praying together in the fellowship of the two spirits.",
    },
]

CSV_FIELDS = [
    "surface",
    "lemma",
    "context_meaning_zh",
    "meaning_source",
    "alignment_status",
    "alignment_reason",
    "occurrence_count",
    "chapter_count",
    "score",
    "glossary_candidate_zh",
    "representative_sentence_en",
    "representative_sentence_zh",
    "chapter_title",
    "chapter_locator",
]


@dataclass(frozen=True)
class BilingualPair:
    chapter_title: str
    chapter_locator: str
    sentence_index: int
    english_sentence: str
    chinese_sentence: str


@dataclass(frozen=True)
class WordOccurrence:
    surface: str
    lemma: str
    pair: BilingualPair
    occurrence_index: int


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_id(prefix: str, *parts: Any) -> str:
    raw = "\x1f".join(str(part) for part in parts)
    return f"{prefix}_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24]}"


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def class_names(node: ET.Element) -> set[str]:
    return {part.strip() for part in str(node.attrib.get("class") or "").split() if part.strip()}


def text_content(node: ET.Element | None) -> str:
    if node is None:
        return ""
    text = "".join(node.itertext())
    text = html.unescape(text)
    text = text.replace("\u00a0", " ")
    return re.sub(r"\s+", " ", text).strip()


def safe_member(path: str) -> str:
    normalized = posixpath.normpath(str(path or "").replace("\\", "/")).lstrip("/")
    if not normalized or normalized == "." or normalized.startswith("../") or "/../" in f"/{normalized}/":
        raise ValueError(f"unsafe EPUB member path: {path}")
    return normalized


def zip_text(epub: zipfile.ZipFile, name: str) -> str:
    raw = epub.read(name)
    for encoding in ("utf-8", "utf-16", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def opf_path(epub: zipfile.ZipFile) -> str:
    root = ET.fromstring(epub.read("META-INF/container.xml"))
    for node in root.iter():
        if local_name(node.tag) == "rootfile" and node.attrib.get("full-path"):
            return safe_member(node.attrib["full-path"])
    raise ValueError("EPUB rootfile not found")


def spine_html_items(epub: zipfile.ZipFile) -> list[dict[str, str]]:
    opf = opf_path(epub)
    root = ET.fromstring(epub.read(opf))
    opf_dir = posixpath.dirname(opf)
    manifest: dict[str, dict[str, str]] = {}
    spine: list[str] = []
    for node in root.iter():
        name = local_name(node.tag)
        if name == "item" and node.attrib.get("id") and node.attrib.get("href"):
            href = safe_member(posixpath.normpath(posixpath.join(opf_dir, node.attrib["href"])))
            manifest[node.attrib["id"]] = {
                "href": href,
                "media_type": node.attrib.get("media-type", ""),
            }
        elif name == "itemref" and node.attrib.get("idref"):
            spine.append(node.attrib["idref"])
    items = []
    for idref in spine:
        item = manifest.get(idref)
        if not item:
            continue
        href = item["href"]
        media_type = item.get("media_type") or ""
        if media_type in {"application/xhtml+xml", "text/html"} or href.lower().endswith((".xhtml", ".html", ".htm")):
            items.append({"idref": idref, "href": href})
    return items


def first_node(root: ET.Element, tag: str, wanted_class: str | None = None) -> ET.Element | None:
    for node in root.iter():
        if local_name(node.tag) != tag:
            continue
        if wanted_class and wanted_class not in class_names(node):
            continue
        return node
    return None


def find_descendant_by_class(node: ET.Element, tag: str, wanted_class: str) -> ET.Element | None:
    for child in node.iter():
        if local_name(child.tag) == tag and wanted_class in class_names(child):
            return child
    return None


def parse_chapter_pairs(href: str, raw_html: str) -> list[BilingualPair]:
    try:
        root = ET.fromstring(raw_html.encode("utf-8"))
    except ET.ParseError:
        cleaned = re.sub(r"<!DOCTYPE[^>]*>", "", raw_html, flags=re.IGNORECASE)
        root = ET.fromstring(cleaned.encode("utf-8"))
    title = text_content(first_node(root, "h1", "chapter-title")) or text_content(first_node(root, "h1")) or href
    pairs: list[BilingualPair] = []
    for node in root.iter():
        if local_name(node.tag) != "section" or "pair" not in class_names(node):
            continue
        en = text_content(find_descendant_by_class(node, "p", "en"))
        zh = text_content(find_descendant_by_class(node, "p", "zh"))
        if not en:
            continue
        pairs.append(
            BilingualPair(
                chapter_title=title,
                chapter_locator=href,
                sentence_index=len(pairs),
                english_sentence=en,
                chinese_sentence=zh,
            )
        )
    return pairs


def extract_pairs(epub_path: Path) -> list[BilingualPair]:
    pairs: list[BilingualPair] = []
    with zipfile.ZipFile(epub_path) as epub:
        for item in spine_html_items(epub):
            href = item["href"]
            try:
                pairs.extend(parse_chapter_pairs(href, zip_text(epub, href)))
            except KeyError:
                continue
    return pairs


def normalize_surface(token: str) -> str:
    value = token.lower().replace("’", "'").strip("'")
    if value.endswith("'s"):
        value = value[:-2]
    value = re.sub(r"[^a-z']", "", value)
    if "'" in value:
        value = value.replace("'", "")
    return value


def lemma_for(surface: str) -> str:
    if surface in LEMMA_EXCEPTIONS:
        return LEMMA_EXCEPTIONS[surface]
    if len(surface) > 5 and surface.endswith("ies"):
        return surface[:-3] + "y"
    if len(surface) > 5 and surface.endswith("ing"):
        stem = surface[:-3]
        if len(stem) > 3 and stem[-1] == stem[-2] and stem[-1] not in {"s", "l"}:
            stem = stem[:-1]
        return stem
    if len(surface) > 4 and surface.endswith("ed"):
        stem = surface[:-2]
        if len(stem) > 3 and stem[-1] == stem[-2] and stem[-1] not in {"s", "l"}:
            stem = stem[:-1]
        return stem
    if len(surface) > 4 and surface.endswith("es") and not surface.endswith(("ses", "xes")):
        return surface[:-2]
    if len(surface) > 4 and surface.endswith("s") and not surface.endswith("ss"):
        return surface[:-1]
    return surface


def should_keep(surface: str, lemma: str) -> bool:
    if len(surface) < 3 or len(lemma) < 3:
        return False
    if surface in STOPWORDS or lemma in STOPWORDS:
        return False
    if surface.isdigit() or lemma.isdigit():
        return False
    return True


def iter_word_occurrences(pairs: Iterable[BilingualPair]) -> list[WordOccurrence]:
    occurrences: list[WordOccurrence] = []
    for pair in pairs:
        per_sentence_counter: Counter[str] = Counter()
        for match in WORD_RE.finditer(pair.english_sentence):
            surface = normalize_surface(match.group(0))
            lemma = lemma_for(surface)
            if not should_keep(surface, lemma):
                continue
            occurrence_index = per_sentence_counter[surface]
            per_sentence_counter[surface] += 1
            occurrences.append(WordOccurrence(surface=surface, lemma=lemma, pair=pair, occurrence_index=occurrence_index))
    return occurrences


def context_meaning(lemma: str, surface: str) -> tuple[str, str]:
    if lemma in BOOK_GLOSSARY:
        return BOOK_GLOSSARY[lemma], "book_glossary"
    if surface in BOOK_GLOSSARY:
        return BOOK_GLOSSARY[surface], "book_glossary"
    return "", "none"


def meaning_terms(lemma: str, surface: str, meaning: str) -> list[str]:
    terms: list[str] = []
    for value in [meaning, *BOOK_GLOSSARY_VARIANTS.get(lemma, []), *BOOK_GLOSSARY_VARIANTS.get(surface, [])]:
        value = str(value or "").strip()
        if value and value not in terms:
            terms.append(value)
    return terms


def context_paraphrase(lemma: str, surface: str, english_sentence: str, chinese_sentence: str) -> tuple[str, str] | None:
    english = english_sentence.lower()
    for rule in CONTEXT_PARAPHRASE_RULES:
        if rule.get("lemma") and rule["lemma"] != lemma:
            continue
        if rule.get("surface") and rule["surface"] != surface:
            continue
        english_needles = rule.get("english", [])
        if isinstance(english_needles, str):
            english_needles = [english_needles]
        chinese_needles = rule.get("chinese", [])
        if isinstance(chinese_needles, str):
            chinese_needles = [chinese_needles]
        if all(str(needle).lower() in english for needle in english_needles) and all(
            str(needle) in chinese_sentence for needle in chinese_needles
        ):
            return str(rule["meaning"]), str(rule["reason"])
    return None


def current_context_meaning(
    lemma: str,
    surface: str,
    glossary_meaning: str,
    english_sentence: str,
    chinese_sentence: str,
) -> tuple[str, str, str, str]:
    if not chinese_sentence:
        return "", "none", "missing_chinese_sentence", "No aligned Chinese sentence was found in the EPUB pair."
    if not glossary_meaning:
        return "", "none", "context_sentence_available", "The EPUB provides an aligned Chinese sentence, but no exact word-level meaning is confirmed yet."

    for term in meaning_terms(lemma, surface, glossary_meaning):
        if term in chinese_sentence:
            source = "book_glossary" if term == glossary_meaning else "book_glossary_variant"
            reason = "The glossary meaning appears in the representative Chinese sentence."
            if term != glossary_meaning:
                reason = f"A recognized Chinese variant appears in the representative Chinese sentence: {term}."
            return term, source, "confirmed_context_meaning", reason

    paraphrase = context_paraphrase(lemma, surface, english_sentence, chinese_sentence)
    if paraphrase:
        meaning, reason = paraphrase
        return meaning, "book_context_paraphrase", "paraphrased_context_meaning", reason

    return (
        "",
        "unconfirmed_glossary",
        "suspected_alignment_mismatch",
        "The book glossary suggests a meaning, but the representative Chinese sentence does not support a word-level meaning.",
    )


def alignment_status(meaning: str, chinese_sentence: str) -> tuple[str, str]:
    if not chinese_sentence:
        return "missing_chinese_sentence", "No aligned Chinese sentence was found in the EPUB pair."
    if meaning and meaning not in chinese_sentence:
        return "needs_review", "The glossary meaning is not visible in the representative Chinese sentence."
    if meaning:
        return "confirmed_context_meaning", "The glossary meaning appears in the representative Chinese sentence."
    return "context_sentence_available", "The EPUB provides an aligned Chinese sentence, but no exact word-level meaning is confirmed yet."


def representative_score(occurrence: WordOccurrence, meaning: str) -> float:
    pair = occurrence.pair
    score = 0.0
    locator = pair.chapter_locator.lower()
    if pair.chinese_sentence:
        score += 8
    if meaning and any(term in pair.chinese_sentence for term in meaning_terms(occurrence.lemma, occurrence.surface, meaning)):
        score += 20
    if context_paraphrase(occurrence.lemma, occurrence.surface, pair.english_sentence, pair.chinese_sentence):
        score += 16
    if "-day" in locator:
        score += 12
    if "-outline" in locator:
        score -= 8
    if "front-title" in locator or "front-cover" in locator:
        score -= 16
    en_len = len(pair.english_sentence)
    if 60 <= en_len <= 260:
        score += 5
    if en_len > 420:
        score -= 3
    if re.search(r"\b(WEEK|DAY|Reading|Nourishment)\b", pair.english_sentence):
        score -= 2
    return score


def build_vocab(epub_path: Path, *, limit: int, min_count: int) -> dict[str, Any]:
    pairs = extract_pairs(epub_path)
    occurrences = iter_word_occurrences(pairs)
    grouped: dict[tuple[str, str], list[WordOccurrence]] = defaultdict(list)
    for occurrence in occurrences:
        grouped[(occurrence.lemma, occurrence.surface)].append(occurrence)

    items: list[dict[str, Any]] = []
    for (lemma, surface), values in grouped.items():
        if len(values) < min_count:
            continue
        glossary_meaning, _meaning_source = context_meaning(lemma, surface)
        chapters = {item.pair.chapter_locator for item in values}
        representative = max(values, key=lambda item: representative_score(item, glossary_meaning))
        meaning, meaning_source, status, reason = current_context_meaning(
            lemma,
            surface,
            glossary_meaning,
            representative.pair.english_sentence,
            representative.pair.chinese_sentence,
        )
        score = len(values) + min(len(chapters), 12) * 1.5 + (10 if glossary_meaning else 0) + (2 if len(surface) >= 8 else 0)
        items.append(
            {
                "surface": surface,
                "lemma": lemma,
                "context_meaning_zh": meaning,
                "meaning_source": meaning_source,
                "alignment_status": status,
                "alignment_reason": reason,
                "glossary_candidate_zh": glossary_meaning,
                "occurrence_count": len(values),
                "chapter_count": len(chapters),
                "score": round(score, 3),
                "representative_sentence_en": representative.pair.english_sentence,
                "representative_sentence_zh": representative.pair.chinese_sentence,
                "chapter_title": representative.pair.chapter_title,
                "chapter_locator": representative.pair.chapter_locator,
                "sentence_index": representative.pair.sentence_index,
            }
        )

    items.sort(key=lambda item: (-float(item["score"]), -int(item["occurrence_count"]), item["lemma"], item["surface"]))
    if limit > 0:
        glossary_items = [item for item in items if item.get("glossary_candidate_zh")]
        regular_items = [item for item in items if not item.get("glossary_candidate_zh")]
        selected: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for item in glossary_items + regular_items:
            key = (str(item["lemma"]), str(item["surface"]))
            if key in seen:
                continue
            if len(selected) >= limit:
                break
            selected.append(item)
            seen.add(key)
        items = selected

    included_keys = {(item["lemma"], item["surface"]) for item in items}
    included_occurrences = [
        occurrence
        for occurrence in occurrences
        if (occurrence.lemma, occurrence.surface) in included_keys
    ]
    quality = {
        "bilingual_pair_count": len(pairs),
        "raw_word_occurrence_count": len(occurrences),
        "included_occurrence_count": len(included_occurrences),
        "vocab_item_count": len(items),
        "items_with_representative_chinese_sentence": sum(1 for item in items if item.get("representative_sentence_zh")),
        "items_with_context_meaning_zh": sum(1 for item in items if item.get("context_meaning_zh")),
        "items_with_paraphrased_context_meaning": sum(1 for item in items if item.get("alignment_status") == "paraphrased_context_meaning"),
        "items_with_suspected_alignment_mismatch": sum(1 for item in items if item.get("alignment_status") == "suspected_alignment_mismatch"),
        "items_needing_alignment_review": sum(1 for item in items if item.get("alignment_status") == "needs_review"),
        "context_meaning_column": "context_meaning_zh",
        "chinese_sentence_column": "representative_sentence_zh",
        "alignment_status_column": "alignment_status",
    }
    return {
        "schema": "sentence_reader.book_vocabulary.v1",
        "generated_at": now_iso(),
        "source_epub": str(epub_path),
        "limits": {"limit": limit, "min_count": min_count},
        "columns": {
            "context_meaning_zh": "Exact short Chinese meaning when known from the book glossary or user-confirmed rules.",
            "representative_sentence_zh": "The aligned Chinese sentence from the EPUB; this is the evidence column, not a guessed word-level translation.",
        },
        "quality": quality,
        "items": items,
        "occurrences": [
            {
                "surface": occurrence.surface,
                "lemma": occurrence.lemma,
                "english_sentence": occurrence.pair.english_sentence,
                "chinese_sentence": occurrence.pair.chinese_sentence,
                "chapter_title": occurrence.pair.chapter_title,
                "chapter_locator": occurrence.pair.chapter_locator,
                "sentence_index": occurrence.pair.sentence_index,
                "occurrence_index": occurrence.occurrence_index,
            }
            for occurrence in included_occurrences
        ],
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, items: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for item in items:
            writer.writerow({field: item.get(field, "") for field in CSV_FIELDS})


def _load_psycopg():
    try:
        import psycopg
        from psycopg.types.json import Jsonb
    except ImportError as exc:
        raise SystemExit("psycopg is required for --insert-db") from exc
    return psycopg, Jsonb


def insert_db(payload: dict[str, Any], *, book_id: str, database_url: str, replace_occurrences: bool) -> dict[str, int]:
    psycopg, Jsonb = _load_psycopg()
    inserted = {"lexemes": 0, "vocab_items": 0, "occurrences": 0}
    items = payload.get("items", [])
    occurrences = payload.get("occurrences", [])
    with psycopg.connect(database_url) as conn:
        book = conn.execute("SELECT id FROM reader.books WHERE id = %s", (book_id,)).fetchone()
        if not book:
            raise SystemExit(f"book_id not found in reader.books: {book_id}")
        if replace_occurrences:
            conn.execute("DELETE FROM reader.book_word_occurrences WHERE book_id = %s", (book_id,))
        lexeme_ids: dict[tuple[str, str], str] = {}
        for item in items:
            lemma = str(item.get("lemma") or "")
            surface = str(item.get("surface") or "")
            lexeme_id = stable_id("lex", "en", lemma, surface)
            lexeme_ids[(lemma, surface)] = lexeme_id
            conn.execute(
                """
                INSERT INTO reader.lexemes (
                    id, lemma, surface, language, short_definition, source, created_at, updated_at
                )
                VALUES (%s, %s, %s, 'en', %s, %s, now(), now())
                ON CONFLICT (language, lemma, surface) DO UPDATE
                SET short_definition = COALESCE(NULLIF(EXCLUDED.short_definition, ''), reader.lexemes.short_definition),
                    source = COALESCE(NULLIF(EXCLUDED.source, ''), reader.lexemes.source),
                    updated_at = now()
                RETURNING id
                """,
                (lexeme_id, lemma, surface, item.get("context_meaning_zh") or None, item.get("meaning_source") or None),
            )
            vocab_id = stable_id("vocab", book_id, lemma, surface)
            conn.execute(
                """
                INSERT INTO reader.book_vocab_items (
                    id, book_id, lexeme_id, surface, lemma, context_meaning, meaning_source,
                    alignment_status, alignment_reason, representative_sentence_en, representative_sentence_zh, occurrence_count,
                    chapter_count, score, status, metadata, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'candidate', %s, now(), now())
                ON CONFLICT (book_id, lemma, surface) DO UPDATE
                SET lexeme_id = EXCLUDED.lexeme_id,
                    context_meaning = EXCLUDED.context_meaning,
                    meaning_source = EXCLUDED.meaning_source,
                    alignment_status = EXCLUDED.alignment_status,
                    alignment_reason = EXCLUDED.alignment_reason,
                    representative_sentence_en = EXCLUDED.representative_sentence_en,
                    representative_sentence_zh = EXCLUDED.representative_sentence_zh,
                    occurrence_count = EXCLUDED.occurrence_count,
                    chapter_count = EXCLUDED.chapter_count,
                    score = EXCLUDED.score,
                    metadata = reader.book_vocab_items.metadata || EXCLUDED.metadata,
                    updated_at = now()
                """,
                (
                    vocab_id,
                    book_id,
                    lexeme_id,
                    surface,
                    lemma,
                    item.get("context_meaning_zh") or None,
                    item.get("meaning_source") or "none",
                    item.get("alignment_status") or "unknown",
                    item.get("alignment_reason") or None,
                    item.get("representative_sentence_en") or None,
                    item.get("representative_sentence_zh") or None,
                    int(item.get("occurrence_count") or 0),
                    int(item.get("chapter_count") or 0),
                    float(item.get("score") or 0),
                    Jsonb(
                        {
                            "source": "sentence_reader_book_vocab.py",
                            "generated_at": payload.get("generated_at"),
                            "glossary_candidate_zh": item.get("glossary_candidate_zh") or "",
                        }
                    ),
                ),
            )
            inserted["lexemes"] += 1
            inserted["vocab_items"] += 1
        for occurrence in occurrences:
            lemma = str(occurrence.get("lemma") or "")
            surface = str(occurrence.get("surface") or "")
            lexeme_id = lexeme_ids.get((lemma, surface)) or stable_id("lex", "en", lemma, surface)
            occurrence_id = stable_id(
                "occ",
                book_id,
                occurrence.get("chapter_locator"),
                occurrence.get("sentence_index"),
                surface,
                occurrence.get("occurrence_index"),
            )
            conn.execute(
                """
                INSERT INTO reader.book_word_occurrences (
                    id, book_id, sentence_id, lexeme_id, surface, lemma, english_sentence,
                    chinese_sentence, chapter_title, chapter_locator, sentence_index,
                    occurrence_index, position, created_at
                )
                VALUES (%s, %s, NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (book_id, chapter_locator, sentence_index, surface, occurrence_index) DO UPDATE
                SET lexeme_id = EXCLUDED.lexeme_id,
                    lemma = EXCLUDED.lemma,
                    english_sentence = EXCLUDED.english_sentence,
                    chinese_sentence = EXCLUDED.chinese_sentence,
                    chapter_title = EXCLUDED.chapter_title,
                    position = EXCLUDED.position
                """,
                (
                    occurrence_id,
                    book_id,
                    lexeme_id,
                    surface,
                    lemma,
                    occurrence.get("english_sentence") or "",
                    occurrence.get("chinese_sentence") or None,
                    occurrence.get("chapter_title") or None,
                    occurrence.get("chapter_locator") or "",
                    int(occurrence.get("sentence_index") or 0),
                    int(occurrence.get("occurrence_index") or 0),
                    Jsonb({"source": "epub_pair"}),
                ),
            )
            inserted["occurrences"] += 1
        conn.commit()
    return inserted


def default_output_base(epub_path: Path) -> Path:
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "-", epub_path.stem).strip("-") or "book"
    return ROOT / "reports" / f"{stem}-vocab"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a book-local English vocabulary list from bilingual EPUB pairs.")
    parser.add_argument("epub", help="EPUB path")
    parser.add_argument("--output-json", default=None)
    parser.add_argument("--output-csv", default=None)
    parser.add_argument("--limit", type=int, default=500, help="Maximum vocab items; 0 means all.")
    parser.add_argument("--min-count", type=int, default=1)
    parser.add_argument("--book-id", default=None)
    parser.add_argument("--insert-db", action="store_true")
    parser.add_argument("--database-url", default=os.environ.get("SENTENCE_READER_DATABASE_URL") or DEFAULT_DATABASE_URL)
    parser.add_argument("--keep-existing-occurrences", action="store_true")
    args = parser.parse_args()

    epub_path = Path(args.epub).expanduser()
    if not epub_path.exists():
        raise SystemExit(f"EPUB does not exist: {epub_path}")
    payload = build_vocab(epub_path, limit=max(0, args.limit), min_count=max(1, args.min_count))

    output_base = default_output_base(epub_path)
    json_path = Path(args.output_json).expanduser() if args.output_json else output_base.with_suffix(".json")
    csv_path = Path(args.output_csv).expanduser() if args.output_csv else output_base.with_suffix(".csv")
    write_json(json_path, payload)
    write_csv(csv_path, payload["items"])

    db_result: dict[str, int] | None = None
    if args.insert_db:
        if not args.book_id:
            raise SystemExit("--book-id is required with --insert-db")
        db_result = insert_db(
            payload,
            book_id=args.book_id,
            database_url=args.database_url,
            replace_occurrences=not args.keep_existing_occurrences,
        )

    summary = {
        "ok": True,
        "schema": payload["schema"],
        "json_path": str(json_path),
        "csv_path": str(csv_path),
        "quality": payload["quality"],
        "db": db_result,
        "first_items": payload["items"][:8],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
