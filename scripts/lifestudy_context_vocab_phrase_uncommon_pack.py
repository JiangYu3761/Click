#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PIPELINE = ROOT / "reports" / "lifestudy_vocab_pipeline" / "01_Genesis-120-pages-1-1255-pipeline.json"
DEFAULT_WORD_REVIEW = ROOT / "reports" / "lifestudy_vocab_review" / "Genesis-word-review-pack.json"
DEFAULT_OUTPUT_DIR = ROOT / "reports" / "lifestudy_vocab_review"

MAX_REVIEW_PHRASES = 150
MIN_REVIEW_PHRASE_COUNT = 8

WEAK_EDGE_WORDS = {
    "according",
    "appeared",
    "became",
    "called",
    "came",
    "come",
    "gave",
    "give",
    "given",
    "high",
    "made",
    "make",
    "need",
    "needs",
    "never",
    "new",
    "ordained",
    "revealed",
    "said",
    "say",
    "says",
    "seemed",
    "still",
    "told",
    "used",
    "wanted",
    "wants",
}

WEAK_INTERNAL_WORDS = {
    "also",
    "although",
    "another",
    "chapter",
    "first",
    "however",
    "many",
    "much",
    "never",
    "today",
}

TOKEN_MEANINGS = {
    "abraham": "亚伯拉罕",
    "authority": "权柄",
    "blessing": "祝福",
    "body": "身体",
    "building": "建造",
    "calling": "呼召",
    "care": "顾到",
    "christ": "基督",
    "christian": "基督徒",
    "church": "召会",
    "creation": "创造",
    "created": "创造",
    "divine": "神圣",
    "dominion": "管治",
    "dwelling": "居所",
    "economy": "经纶",
    "eternal": "永远",
    "experience": "经历",
    "father": "父",
    "forth": "产生",
    "fulfill": "完成",
    "fulfillment": "完成",
    "glory": "荣耀",
    "god": "神",
    "government": "行政",
    "grace": "恩典",
    "growth": "长大",
    "heavenly": "属天",
    "holy": "圣",
    "house": "家",
    "human": "人的",
    "image": "形像",
    "intention": "心意",
    "jacob": "雅各",
    "jesus": "耶稣",
    "joseph": "约瑟",
    "judgment": "审判",
    "kingdom": "国度",
    "life": "生命",
    "line": "线",
    "live": "活",
    "lord": "主",
    "man": "人",
    "mature": "成熟",
    "maturity": "成熟",
    "married": "婚姻",
    "natural": "天然",
    "presence": "同在",
    "promise": "应许",
    "promised": "应许",
    "proper": "正当的",
    "purpose": "目的",
    "rebellion": "背叛",
    "revelation": "启示",
    "riches": "丰富",
    "salvation": "救恩",
    "see": "看见",
    "selection": "拣选",
    "sovereign": "主宰",
    "sovereignty": "主宰权柄",
    "spirit": "灵",
    "tells": "告诉",
    "type": "预表",
    "waters": "水",
}

TOKEN_MEANINGS.update(
    {
        "appeared": "显现",
        "added": "加到",
        "all-sufficient": "全丰全足",
        "animal": "动物",
        "bible": "圣经",
        "blessed": "赐福",
        "bring": "生出",
        "brought": "生",
        "enjoy": "享受",
        "enjoyment": "享受",
        "full": "满了",
        "genesis": "创世记",
        "nature": "性情",
        "offer": "献给",
        "process": "过程",
        "son": "子",
        "spiritual": "属灵的",
        "supply": "供应",
        "transformation": "变化",
        "word": "话",
        "wrought": "作到",
        "chosen": "拣选",
        "covenant": "约",
        "dealing": "应付",
        "desire": "心愿",
        "eyes": "眼中",
        "expression": "彰显",
        "goal": "目标",
        "habitation": "居所",
        "hand": "手",
        "heart": "心意",
        "heaven": "天",
        "possessor": "主",
        "righteousness": "公义",
        "satisfaction": "满足",
        "called": "呼召",
        "coming": "来临",
        "death": "死",
        "isaac": "以撒",
        "might": "能力",
        "resurrected": "复活的",
        "satan": "撒但",
        "seed": "种子",
        "told": "告诉",
        "transfer": "转移",
        "tree": "树",
    }
)

PHRASE_MEANINGS = {
    "building church": ["召会的建造", "建造召会"],
    "christ church": ["基督、召会", "基督与召会"],
    "christ life": ["基督的生命"],
    "christian life": ["基督徒生活"],
    "church life": ["召会生活"],
    "church life today": ["今天的召会生活"],
    "eternal purpose": ["永远的目的", "永远的定旨"],
    "experience christ": ["经历基督"],
    "experience life": ["经历生命"],
    "fulfill god purpose": ["完成神的目的", "完成神的定旨"],
    "fulfillment god purpose": ["完成神的目的", "完成神的定旨"],
    "god authority": ["神的权柄"],
    "god blessing": ["神的祝福"],
    "god building": ["神的建造"],
    "god calling": ["神的呼召"],
    "god dominion": ["神的管治"],
    "god dwelling": ["神的居所"],
    "god economy": ["神的经纶"],
    "god eternal": ["神永远"],
    "god eternal purpose": ["神永远的目的", "神永远的定旨"],
    "god glory": ["神的荣耀"],
    "god government": ["神的行政", "神的管理"],
    "god grace": ["神的恩典"],
    "god house": ["神在地上的家", "神的家"],
    "god image": ["神的形像"],
    "god intention": ["神的心意"],
    "god judgment": ["神的审判"],
    "god life": ["神的生命"],
    "god man": ["神人", "神与人"],
    "god presence": ["神的同在"],
    "god promise": ["神的应许"],
    "god promised": ["神应许"],
    "god purpose": ["神的目的", "神的定旨"],
    "god revelation": ["神的启示"],
    "god sovereignty": ["神的主宰权柄", "神的主宰"],
    "god spirit": ["神的灵"],
    "growth life": ["生命的长大", "生命长大"],
    "holy spirit": ["圣灵"],
    "human life": ["人的生命"],
    "intimate fellowship": ["亲密的交通"],
    "jesus christ": ["耶稣基督"],
    "joseph life": ["约瑟生平", "约瑟的生平"],
    "line life": ["生命线"],
    "life resurrection": ["在复活里的生活", "复活里的生活"],
    "married life": ["婚姻生活"],
    "mature life": ["生命成熟", "成熟的生命"],
    "maturity life": ["生命成熟", "生命的成熟"],
    "natural life": ["天然的生命"],
    "proper church": ["正当的召会"],
    "proper church life": ["正当的召会生活"],
    "resurrected christ": ["复活的基督"],
    "riches christ": ["基督的丰富"],
    "riches life": ["生命的丰富"],
    "bible see": ["在圣经中看见", "圣经中看见"],
    "bible tells": ["圣经告诉"],
    "death waters": ["死水"],
    "god salvation": ["神的救恩"],
    "satan rebellion": ["撒但的背叛"],
    "tree life": ["生命树"],
    "type christ": ["基督的预表", "预表基督"],
}

PHRASE_MEANINGS.update(
    {
        "abraham god isaac": ["亚伯拉罕的神、以撒的神"],
        "animal life": ["动物的生命"],
        "bring forth christ": ["生出基督"],
        "building god house": ["神家的建造"],
        "calling lord": ["呼求主名"],
        "christ resurrected": ["基督复活", "复活的基督"],
        "christ brought": ["基督藉我们而生"],
        "christ seed": ["基督作后裔", "基督作为后裔"],
        "christ wrought": ["神在基督里作到人里面", "基督作到人里面"],
        "church kingdom": ["召会里的国度", "召会与国度"],
        "coming church life": ["进入召会生活"],
        "created man": ["创造人"],
        "creation man": ["创造人"],
        "death resurrection": ["死与复活", "在复活里从死里出来"],
        "divine nature": ["神圣的性情"],
        "enjoy christ": ["享受基督"],
        "enjoyment christ": ["对基督的享受"],
        "full life": ["满了生命"],
        "forth christ": ["生出基督"],
        "fulfillment god eternal": ["达成神永远的目的"],
        "fulfillment god eternal purpose": ["达成神永远的目的"],
        "father son spirit": ["父、子、灵"],
        "genesis revelation": ["创世记和启示录"],
        "god abraham": ["亚伯拉罕的神", "神与亚伯拉罕"],
        "god abraham god isaac": ["亚伯拉罕的神、以撒的神"],
        "god added": ["神加到我们的生命中"],
        "god all sufficient": ["全丰全足的神"],
        "god all-sufficient": ["全丰全足的神"],
        "god appeared abraham": ["神向亚伯拉罕显现"],
        "god blessed": ["神赐福给人"],
        "god become": ["神成了人的灵", "神成了"],
        "god called abraham": ["神呼召亚伯拉罕"],
        "god care": ["神的照顾", "神的顾到"],
        "god chosen": ["神所拣选的"],
        "god christ": ["神与基督"],
        "god covenant": ["神的约"],
        "god created man": ["神创造人"],
        "god dealing": ["神的应付", "神的对付"],
        "god desire": ["神的心愿"],
        "god father": ["父神"],
        "god expression": ["神的彰显"],
        "god eyes": ["神眼中", "在神眼中"],
        "god goal": ["神的目标"],
        "god habitation": ["神的居所"],
        "god hand": ["神的手"],
        "god heart": ["神的心意"],
        "god isaac": ["以撒的神", "神与以撒"],
        "god jacob": ["雅各的神", "神与雅各"],
        "god living": ["为着生活信靠神", "凭信而活"],
        "god appearing": ["神的显现"],
        "god possessor": ["至高的神，天地的主", "天地的主"],
        "god possessor heaven": ["至高的神，天地的主", "天地的主"],
        "god righteousness": ["神的公义"],
        "god satisfaction": ["神得着满足", "神的满足"],
        "god told abraham": ["神告诉亚伯拉罕", "神吩咐亚伯拉罕"],
        "high god possessor": ["至高的神，天地的主", "天地的主"],
        "high god possessor heaven": ["至高的神，天地的主", "天地的主"],
        "joseph type christ": ["约瑟是基督的预表"],
        "life christ": ["生命与基督"],
        "life experience": ["生命经历", "对生命的经历"],
        "life jacob": ["雅各天然的生命"],
        "life supply": ["生命供应"],
        "life tree": ["生命树"],
        "living christ": ["活的基督"],
        "offer christ": ["将基督献给神"],
        "process transformation": ["变化的过程"],
        "revelation see": ["在启示录中看见", "从启示中看见"],
        "resurrection life": ["复活生命"],
        "see christ": ["看见基督"],
        "son spirit": ["父、子、灵"],
        "spiritual life": ["属灵的生活"],
        "word lord": ["主的话", "主耶稣的话"],
    }
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, expected_schema: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != expected_schema:
        raise SystemExit(f"unexpected schema for {path}: {payload.get('schema')}")
    return payload


def phrase_tokens(term: str) -> list[str]:
    return [item for item in term.replace("-", " ").split() if item]


def phrase_meaning_from_context(term: str, evidence_zh: str) -> tuple[str, str, str]:
    normalized = " ".join(phrase_tokens(term))
    for candidate in PHRASE_MEANINGS.get(normalized, []):
        if candidate and candidate in evidence_zh:
            return candidate, "exact_phrase_in_chinese_context", "medium"

    for candidate in PHRASE_MEANINGS.get(normalized, []):
        if candidate:
            return candidate, "known_phrase_map_needs_review", "low"

    token_meanings = [TOKEN_MEANINGS.get(token, "") for token in phrase_tokens(normalized)]
    known = [value for value in token_meanings if value]
    if len(known) >= 2 and all(value in evidence_zh for value in known):
        return compose_component_meaning(phrase_tokens(normalized), token_meanings), "component_terms_in_chinese_context", "low"

    if known and len(known) >= 2:
        return compose_component_meaning(phrase_tokens(normalized), token_meanings), "draft_component_translation", "low"
    return "", "aligned_context_only", "none"


def compose_component_meaning(tokens: list[str], meanings: list[str]) -> str:
    pairs = [(token, meaning) for token, meaning in zip(tokens, meanings) if meaning]
    if not pairs:
        return ""
    if len(pairs) == 2:
        (left_token, left), (right_token, right) = pairs
        if left_token in {"proper", "natural", "eternal", "divine", "holy", "human", "mature", "resurrected"}:
            return f"{left}{right}"
        if left_token in {"experience", "fulfill", "fulfillment", "building", "live"}:
            return f"{left}{right}"
        if left_token == "god":
            return f"{left}的{right}"
        if right_token in {
            "authority",
            "blessing",
            "building",
            "calling",
            "care",
            "church",
            "dominion",
            "dwelling",
            "economy",
            "father",
            "glory",
            "government",
            "grace",
            "house",
            "image",
            "intention",
            "life",
            "presence",
            "promise",
            "purpose",
            "revelation",
            "riches",
            "sovereign",
            "sovereignty",
            "spirit",
        }:
            return f"{left}的{right}"
    if len(pairs) == 3 and pairs[0][0] == "god" and pairs[1][0] == "eternal" and pairs[2][0] == "purpose":
        return "神永远的目的"
    return " / ".join(meaning for _, meaning in pairs)


def should_include_review_phrase(item: dict[str, Any]) -> bool:
    if item.get("kind") != "phrase" or item.get("quality_grade") != "C":
        return False
    if int(item.get("occurrence_count") or 0) < MIN_REVIEW_PHRASE_COUNT:
        return False
    tokens = phrase_tokens(str(item.get("term") or ""))
    if len(tokens) < 2 or len(tokens) > 4:
        return False
    if tokens[0] in WEAK_EDGE_WORDS or tokens[-1] in WEAK_EDGE_WORDS:
        return False
    if any(token in WEAK_INTERNAL_WORDS for token in tokens):
        return False
    return True


def normalize_phrase_item(item: dict[str, Any], *, group: str, review_status: str) -> dict[str, Any]:
    meaning = str(item.get("suggested_meaning_zh_simp") or "")
    source = item.get("match_source") or "aligned_context"
    confidence = "high" if meaning else "none"
    if not meaning and review_status != "active_phrase_review":
        meaning, source, confidence = phrase_meaning_from_context(str(item.get("term") or ""), str(item.get("evidence_zh_simp") or ""))
    return {
        "group": group,
        "term": str(item.get("term") or ""),
        "kind": "phrase",
        "quality_grade": item.get("quality_grade"),
        "occurrence_count": int(item.get("occurrence_count") or 0),
        "suggested_meaning_zh_simp": meaning,
        "meaning_source": source,
        "meaning_confidence": confidence,
        "review_status": review_status,
        "import_ready": bool(item.get("import_allowed") is True and item.get("quality_grade") in {"A", "B"}),
        "source_page": item.get("source_page"),
        "evidence_en": item.get("evidence_en") or "",
        "evidence_zh_simp": item.get("evidence_zh_simp") or "",
        "note": (
            "高置信词组，可作为当前正式词条复核。"
            if review_status == "active_phrase_review"
            else "高频词组候选，中文上下文来自原文，但还没有分离出稳定中文词义。"
        ),
    }


def normalize_word_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "group": "uncommon_context_words",
        "term": str(item.get("term") or ""),
        "kind": "word",
        "quality_grade": "C",
        "occurrence_count": int(item.get("occurrence_count") or 0),
        "suggested_meaning_zh_simp": item.get("suggested_meaning_zh_simp") or "",
        "meaning_source": item.get("suggestion_source") or "word_review_pack",
        "meaning_confidence": item.get("suggestion_confidence") or "low",
        "review_status": "pending_word_review",
        "import_ready": False,
        "source_page": item.get("source_page"),
        "evidence_en": item.get("evidence_en") or "",
        "evidence_zh_simp": item.get("evidence_zh_simp") or "",
        "note": "非常用/领域单词，建议中文义来自中文原文证据或生命读经词义规则，需审校后才能入库。",
    }


def build_pack(pipeline_report: Path, word_review: Path, output_dir: Path) -> dict[str, Any]:
    pipeline = load_json(pipeline_report, "sentence_reader.lifestudy_vocab_pipeline.v1")
    word_payload = load_json(word_review, "sentence_reader.lifestudy_single_word_review_pack.v1")
    candidates = list(pipeline.get("candidates") or [])

    active_phrases = [
        normalize_phrase_item(item, group="active_high_confidence_phrases", review_status="active_phrase_review")
        for item in candidates
        if item.get("kind") == "phrase" and item.get("quality_grade") in {"A", "B"} and item.get("import_allowed") is True
    ]
    active_phrases.sort(key=lambda row: (str(row["quality_grade"]), -int(row["occurrence_count"]), str(row["term"])))

    review_candidates = [
        item for item in candidates if should_include_review_phrase(item)
    ]
    review_candidates.sort(key=lambda item: (int(item.get("score") or 0), int(item.get("occurrence_count") or 0)), reverse=True)
    review_phrases = [
        normalize_phrase_item(item, group="high_frequency_phrase_candidates", review_status="pending_phrase_review")
        for item in review_candidates[:MAX_REVIEW_PHRASES]
    ]

    word_items = [normalize_word_item(item) for item in word_payload.get("items") or []]
    word_items.sort(key=lambda row: (-int(row["occurrence_count"]), str(row["term"])))

    items = active_phrases + review_phrases + word_items
    counts = Counter(item["group"] for item in items)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "Genesis-phrase-uncommon-pack.json"
    csv_path = output_dir / "Genesis-phrase-uncommon-pack.csv"
    md_path = output_dir / "Genesis-phrase-uncommon-pack.md"
    payload = {
        "schema": "sentence_reader.lifestudy_phrase_uncommon_pack.v1",
        "generated_at": now_iso(),
        "source_pipeline": str(pipeline_report),
        "source_word_review": str(word_review),
        "database_write_performed": False,
        "policy": "phrase_and_uncommon_word_review_document_no_db_write",
        "quality": {
            "active_high_confidence_phrase_count": counts.get("active_high_confidence_phrases", 0),
            "high_frequency_phrase_candidate_count": counts.get("high_frequency_phrase_candidates", 0),
            "uncommon_context_word_count": counts.get("uncommon_context_words", 0),
            "total_item_count": len(items),
            "import_ready_count": sum(1 for item in items if item["import_ready"]),
            "pending_review_count": sum(1 for item in items if not item["import_ready"]),
            "meaning_filled_count": sum(1 for item in items if item["suggested_meaning_zh_simp"]),
            "review_phrase_meaning_filled_count": sum(
                1
                for item in items
                if item["group"] == "high_frequency_phrase_candidates" and item["suggested_meaning_zh_simp"]
            ),
            "exact_phrase_in_chinese_context_count": sum(
                1 for item in items if item["meaning_source"] == "exact_phrase_in_chinese_context"
            ),
            "component_terms_in_chinese_context_count": sum(
                1 for item in items if item["meaning_source"] == "component_terms_in_chinese_context"
            ),
            "review_phrase_min_count": MIN_REVIEW_PHRASE_COUNT,
            "review_phrase_limit": MAX_REVIEW_PHRASES,
        },
        "outputs": {
            "json": str(json_path),
            "csv": str(csv_path),
            "markdown": str(md_path),
        },
        "items": items,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(csv_path, items)
    write_markdown(md_path, payload)
    return payload


def write_csv(path: Path, items: list[dict[str, Any]]) -> None:
    fields = [
        "group",
        "term",
        "kind",
        "quality_grade",
        "occurrence_count",
        "suggested_meaning_zh_simp",
        "meaning_source",
        "meaning_confidence",
        "review_status",
        "import_ready",
        "source_page",
        "evidence_en",
        "evidence_zh_simp",
        "note",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in items:
            writer.writerow({field: item.get(field, "") for field in fields})


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    labels = {
        "active_high_confidence_phrases": "已入库高置信词组",
        "high_frequency_phrase_candidates": "高频待审词组候选",
        "uncommon_context_words": "非常用/领域单词",
    }
    lines = [
        "# Genesis 词组与非常用词组合包",
        "",
        "- Policy: `phrase_and_uncommon_word_review_document_no_db_write`",
        f"- Total: `{payload['quality']['total_item_count']}`",
        f"- Active high-confidence phrases: `{payload['quality']['active_high_confidence_phrase_count']}`",
        f"- High-frequency phrase candidates: `{payload['quality']['high_frequency_phrase_candidate_count']}`",
        f"- Uncommon/context words: `{payload['quality']['uncommon_context_word_count']}`",
        f"- Meaning filled: `{payload['quality']['meaning_filled_count']}`",
        f"- Review phrase meanings filled: `{payload['quality']['review_phrase_meaning_filled_count']}`",
        "",
        "这份文档只用于审校和沉淀，不会写入 PostgreSQL。中文义来源分为完整中文原文命中、词素在中文原文中命中、已知词组规则待审、草案组合、仅上下文。",
        "",
    ]
    items = payload["items"]
    for group, label in labels.items():
        lines.extend([f"## {label}", ""])
        group_items = [item for item in items if item["group"] == group]
        for item in group_items:
            meaning = item["suggested_meaning_zh_simp"] or "待从中文上下文确认"
            lines.extend(
                [
                    f"### {item['term']}",
                    "",
                    f"- Type: `{item['kind']}`",
                    f"- Grade: `{item['quality_grade']}`",
                    f"- Frequency: `{item['occurrence_count']}`",
                    f"- Chinese: `{meaning}`",
                    f"- Meaning source: `{item['meaning_source']}`",
                    f"- Review: `{item['review_status']}`",
                    f"- Page: `{item['source_page']}`",
                    f"- EN: {item['evidence_en']}",
                    f"- ZH: {item['evidence_zh_simp']}",
                    "",
                ]
            )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    payload = build_pack(DEFAULT_PIPELINE, DEFAULT_WORD_REVIEW, DEFAULT_OUTPUT_DIR)
    print(json.dumps({k: payload[k] for k in ("schema", "policy", "quality", "outputs")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
