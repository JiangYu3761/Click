#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET


CONTAINER_NS = {"c": "urn:oasis:names:tc:opendocument:xmlns:container"}
OPF_NS = {
    "opf": "http://www.idpf.org/2007/opf",
    "dc": "http://purl.org/dc/elements/1.1/",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect EPUB metadata without extracting book content.")
    parser.add_argument("epubs", nargs="+", help="EPUB file paths")
    parser.add_argument("--output", help="Write JSON report to this path")
    args = parser.parse_args()

    report = {
        "schema_version": "sentence_reader.epub_fixture_report.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items": [inspect_epub(Path(path)) for path in args.epubs],
    }

    data = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(data, encoding="utf-8")
        print(f"epub inspect report={output}")
    else:
        print(data)
    return 0 if all(item["ok"] for item in report["items"]) else 1


def inspect_epub(path: Path) -> dict:
    item = {
        "path": str(path),
        "ok": False,
        "exists": path.exists(),
    }
    if not path.exists():
        item["error"] = "file does not exist"
        return item

    item["size_bytes"] = path.stat().st_size
    item["sha256"] = sha256(path)

    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            item["zip_entries"] = len(names)
            item["has_mimetype"] = "mimetype" in names
            item["has_container"] = "META-INF/container.xml" in names
            item["has_encryption_xml"] = "META-INF/encryption.xml" in names
            opf_path = find_opf_path(archive)
            item["opf_path"] = opf_path
            metadata = read_opf_metadata(archive, opf_path) if opf_path else {}
            item.update(metadata)
            item["ok"] = bool(opf_path and item["has_mimetype"] and item["has_container"])
    except Exception as exc:  # noqa: BLE001 - report probe failures
        item["error"] = str(exc)

    return item


def find_opf_path(archive: zipfile.ZipFile) -> str | None:
    try:
        raw = archive.read("META-INF/container.xml")
    except KeyError:
        return None
    root = ET.fromstring(raw)
    rootfile = root.find(".//c:rootfile", CONTAINER_NS)
    if rootfile is None:
        return None
    return rootfile.attrib.get("full-path")


def read_opf_metadata(archive: zipfile.ZipFile, opf_path: str) -> dict:
    root = ET.fromstring(archive.read(opf_path))
    title = text(root.find(".//dc:title", OPF_NS))
    creators = [text(node) for node in root.findall(".//dc:creator", OPF_NS)]
    creators = [creator for creator in creators if creator]
    language = text(root.find(".//dc:language", OPF_NS))

    manifest = {}
    for node in root.findall(".//opf:manifest/opf:item", OPF_NS):
        item_id = node.attrib.get("id")
        href = node.attrib.get("href")
        media_type = node.attrib.get("media-type")
        if item_id and href:
            manifest[item_id] = {
                "href": normalize_href(opf_path, href),
                "media_type": media_type,
            }

    spine_ids = [
        node.attrib.get("idref")
        for node in root.findall(".//opf:spine/opf:itemref", OPF_NS)
        if node.attrib.get("idref")
    ]
    spine_items = [manifest[item_id] for item_id in spine_ids if item_id in manifest]
    nav_items = [
        item for item in manifest.values()
        if item.get("media_type") in {"application/xhtml+xml", "text/html"}
        and ("nav" in item.get("href", "").lower() or "toc" in item.get("href", "").lower())
    ]

    return {
        "title": title,
        "creators": creators,
        "language": language,
        "manifest_count": len(manifest),
        "spine_count": len(spine_items),
        "first_spine_items": spine_items[:8],
        "nav_candidates": nav_items[:5],
    }


def normalize_href(opf_path: str, href: str) -> str:
    base = posixpath.dirname(opf_path)
    return posixpath.normpath(posixpath.join(base, href))


def text(node: ET.Element | None) -> str | None:
    if node is None or node.text is None:
        return None
    value = node.text.strip()
    return value or None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())

