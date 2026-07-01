from __future__ import annotations

import base64
import hashlib
import html
import json
import mimetypes
import os
import re
import shutil
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.request import Request as UrlRequest, urlopen
from uuid import uuid4

from fastapi import APIRouter, Body, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field


router = APIRouter()

RECORDING_SCHEMA = "local.recordings.audio_asset.v1"
LEGACY_RECORDING_SCHEMA = "click.knowledge_inbox.recording.v1"
HERMES_CHAT_SCHEMA = "click.hermes_mobile.voice_message.v1"
MOBILE_ACCESS_SCHEMA = "click.mobile_access.v1"
EDGE_TTS_VOICE = "zh-CN-YunjianNeural"
HERMES_RUNTIME_BASE_URL = os.getenv("CLICK_HERMES_RUNTIME_BASE_URL", "http://127.0.0.1:8765")
FUNASR_BASE_URL = os.getenv("CLICK_FUNASR_BASE_URL", "http://127.0.0.1:18081")


class RecordingCreate(BaseModel):
    audio_base64: str
    mime_type: str = "audio/m4a"
    duration_seconds: Optional[float] = None
    device_id: Optional[str] = None
    source: str = "mobile_app"
    source_app: Optional[str] = None
    source_feature: Optional[str] = None
    contexts: list[dict[str, Any]] = Field(default_factory=list)
    durability: str = "durable"
    access_token: Optional[str] = None
    device_name: Optional[str] = None


class HermesChatCreate(BaseModel):
    message: str
    session_id: Optional[str] = None
    device_id: Optional[str] = None
    access_token: Optional[str] = None


class HermesVoiceCreate(BaseModel):
    audio_base64: str
    mime_type: str = "audio/m4a"
    duration_seconds: Optional[float] = None
    session_id: Optional[str] = None
    device_id: Optional[str] = None
    tts: bool = True
    access_token: Optional[str] = None


class MobileAccessRequest(BaseModel):
    device_id: str
    device_name: Optional[str] = None
    platform: Optional[str] = None


class MobileAccessApprove(BaseModel):
    device_id: str
    device_name: Optional[str] = None


class MobileAccessRevoke(BaseModel):
    device_id: str


class RecordingPatch(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[list[str]] = None
    organized_status: Optional[str] = None


class RecordingReprocess(BaseModel):
    dry_run: bool = True
    allow_overwrite_user_edits: bool = False


class RecordingHide(BaseModel):
    reason: Optional[str] = None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def click_app_support_dir() -> Path:
    return Path(os.getenv("CLICK_APP_SUPPORT_DIR", str(Path.home() / "Library" / "Application Support" / "Click"))).expanduser()


def knowledge_inbox_dir() -> Path:
    return click_app_support_dir() / "KnowledgeInbox"


def recordings_dir() -> Path:
    return Path(os.getenv("CLICK_RECORDINGS_ROOT", str(Path.home() / "Documents" / "Recordings"))).expanduser()


def legacy_recordings_dir() -> Path:
    return knowledge_inbox_dir() / "Recordings"


def hermes_mobile_dir() -> Path:
    return click_app_support_dir() / "HermesMobile"


def mobile_access_dir() -> Path:
    return click_app_support_dir() / "MobileAccess"


def allowed_devices_path() -> Path:
    return mobile_access_dir() / "allowed_devices.json"


def pending_devices_path() -> Path:
    return mobile_access_dir() / "pending_devices.json"


def voice_inbox_dir() -> Path:
    return hermes_mobile_dir() / "VoiceInbox"


def forbidden_hermes_recordings_dir() -> Path:
    return Path.home() / "Library" / "Application Support" / "HermesGateway" / "Recordings"


def recording_index_path() -> Path:
    return recordings_dir() / "_index" / "recordings.sqlite"


def legacy_recording_index_path() -> Path:
    return legacy_recordings_dir() / "recordings.sqlite"


def ensure_recording_store() -> None:
    for subdir in [
        recordings_dir() / "Inbox",
        recordings_dir() / "Click" / "Reader",
        recordings_dir() / "Click" / "Standalone",
        recordings_dir() / "Hermes" / "VoiceMessages",
        recordings_dir() / "Hermes" / "Saved",
        recordings_dir() / "Shared",
        recordings_dir() / "_index",
    ]:
        subdir.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(recording_index_path()) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS recordings (
                recording_id TEXT PRIMARY KEY,
                schema TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                status TEXT NOT NULL,
                title TEXT NOT NULL,
                provisional_title TEXT NOT NULL,
                category TEXT NOT NULL,
                tags_json TEXT NOT NULL,
                summary TEXT NOT NULL,
                audio_path TEXT NOT NULL,
                transcript_path TEXT NOT NULL,
                summary_path TEXT NOT NULL,
                title_path TEXT NOT NULL,
                metadata_path TEXT NOT NULL,
                mime_type TEXT NOT NULL,
                duration_seconds REAL,
                audio_hash TEXT NOT NULL,
                asr_engine TEXT NOT NULL,
                naming_engine TEXT NOT NULL,
                error_message TEXT NOT NULL,
                source_app TEXT NOT NULL DEFAULT 'Click',
                source_feature TEXT NOT NULL DEFAULT 'Standalone recording',
                contexts_json TEXT NOT NULL DEFAULT '[]',
                durability TEXT NOT NULL DEFAULT 'durable',
                transcript_status TEXT NOT NULL DEFAULT 'pending',
                title_status TEXT NOT NULL DEFAULT 'pending',
                summary_status TEXT NOT NULL DEFAULT 'pending',
                organized_status TEXT NOT NULL DEFAULT '待整理',
                hidden INTEGER NOT NULL DEFAULT 0,
                hidden_at TEXT NOT NULL DEFAULT '',
                hide_reason TEXT NOT NULL DEFAULT '',
                user_title_override INTEGER NOT NULL DEFAULT 0,
                user_category_override INTEGER NOT NULL DEFAULT 0,
                user_tags_override INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        for column, definition in {
            "source_app": "TEXT NOT NULL DEFAULT 'Click'",
            "source_feature": "TEXT NOT NULL DEFAULT 'Standalone recording'",
            "contexts_json": "TEXT NOT NULL DEFAULT '[]'",
            "durability": "TEXT NOT NULL DEFAULT 'durable'",
            "transcript_status": "TEXT NOT NULL DEFAULT 'pending'",
            "title_status": "TEXT NOT NULL DEFAULT 'pending'",
            "summary_status": "TEXT NOT NULL DEFAULT 'pending'",
            "organized_status": "TEXT NOT NULL DEFAULT '待整理'",
            "hidden": "INTEGER NOT NULL DEFAULT 0",
            "hidden_at": "TEXT NOT NULL DEFAULT ''",
            "hide_reason": "TEXT NOT NULL DEFAULT ''",
            "user_title_override": "INTEGER NOT NULL DEFAULT 0",
            "user_category_override": "INTEGER NOT NULL DEFAULT 0",
            "user_tags_override": "INTEGER NOT NULL DEFAULT 0",
        }.items():
            existing = {row[1] for row in conn.execute("PRAGMA table_info(recordings)").fetchall()}
            if column not in existing:
                conn.execute(f"ALTER TABLE recordings ADD COLUMN {column} {definition}")
        conn.commit()


def ensure_voice_store() -> None:
    voice_inbox_dir().mkdir(parents=True, exist_ok=True)


def ensure_mobile_access_store() -> None:
    mobile_access_dir().mkdir(parents=True, exist_ok=True)
    for path in [allowed_devices_path(), pending_devices_path()]:
        if not path.exists():
            path.write_text("{}", encoding="utf-8")


def read_json_object(path: Path) -> dict[str, Any]:
    ensure_mobile_access_store()
    try:
        data = json.loads(path.read_text(encoding="utf-8") or "{}")
    except json.JSONDecodeError:
        data = {}
    return data if isinstance(data, dict) else {}


def write_json_object(path: Path, data: dict[str, Any]) -> None:
    ensure_mobile_access_store()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def normalize_device_id(value: Optional[str]) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.:-]+", "", value or "").strip()
    return cleaned[:96]


def normalize_device_name(value: Optional[str], fallback: str = "移动设备") -> str:
    cleaned = re.sub(r"\s+", " ", value or "").strip()
    return cleaned[:80] if cleaned else fallback


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_access_token() -> str:
    return uuid4().hex + uuid4().hex


def device_access_record(device_id: Optional[str]) -> Optional[dict[str, Any]]:
    normalized = normalize_device_id(device_id)
    if not normalized:
        return None
    return read_json_object(allowed_devices_path()).get(normalized)


def pending_device_record(device_id: Optional[str]) -> Optional[dict[str, Any]]:
    normalized = normalize_device_id(device_id)
    if not normalized:
        return None
    return read_json_object(pending_devices_path()).get(normalized)


def request_device_identity(request: Request, device_id: Optional[str] = None, access_token: Optional[str] = None) -> tuple[str, str]:
    resolved_device_id = normalize_device_id(
        device_id
        or request.query_params.get("device_id")
        or request.cookies.get("click_device_id")
    )
    resolved_access_token = (
        access_token
        or request.query_params.get("access_token")
        or request.cookies.get("click_access_token")
        or ""
    ).strip()
    return resolved_device_id, resolved_access_token


def is_authorized_device(device_id: str, access_token: str = "") -> bool:
    record = device_access_record(device_id)
    if not record or record.get("revoked_at"):
        return False
    expected_hash = str(record.get("token_hash") or "")
    if expected_hash:
        return bool(access_token) and token_hash(access_token) == expected_hash
    return True


def require_mobile_access(request: Request, *, device_id: Optional[str] = None, access_token: Optional[str] = None) -> None:
    resolved_device_id, resolved_access_token = request_device_identity(request, device_id, access_token)
    if not resolved_device_id:
        return
    if is_authorized_device(resolved_device_id, resolved_access_token):
        return
    if not pending_device_record(resolved_device_id):
        pending = read_json_object(pending_devices_path())
        pending[resolved_device_id] = {
            "device_id": resolved_device_id,
            "device_name": "未命名移动设备",
            "platform": "unknown",
            "requested_at": now_iso(),
        }
        write_json_object(pending_devices_path(), pending)
    raise HTTPException(status_code=403, detail="mobile device is not approved")


def access_status_payload(device_id: str, access_token: str = "") -> dict[str, Any]:
    normalized = normalize_device_id(device_id)
    allowed = device_access_record(normalized)
    pending = pending_device_record(normalized)
    authorized = bool(normalized and is_authorized_device(normalized, access_token))
    status = "authorized" if authorized else "pending" if pending else "unknown"
    return {
        "ok": True,
        "schema": MOBILE_ACCESS_SCHEMA,
        "device_id": normalized,
        "status": status,
        "authorized": authorized,
        "pending": bool(pending and not authorized),
        "device_name": (allowed or pending or {}).get("device_name", ""),
        "token_required": bool(allowed and allowed.get("token_hash")),
        "paths": {
            "allowed_devices": str(allowed_devices_path()),
            "pending_devices": str(pending_devices_path()),
        },
    }


def sqlite_row_to_dict(row: sqlite3.Row, *, storage_mode: str = "canonical") -> dict[str, Any]:
    data = dict(row)
    try:
        tags = json.loads(data.pop("tags_json") or "[]")
    except json.JSONDecodeError:
        tags = []
    try:
        contexts = json.loads(data.pop("contexts_json", "[]") or "[]")
    except json.JSONDecodeError:
        contexts = []
    data["tags"] = tags
    data["contexts"] = contexts
    data.setdefault("source_app", "Click")
    data.setdefault("source_feature", "Legacy recording")
    data.setdefault("durability", "durable")
    data.setdefault("transcript_status", "unknown")
    data.setdefault("title_status", "unknown")
    data.setdefault("summary_status", "unknown")
    data.setdefault("organized_status", "待整理")
    data.setdefault("hidden", 0)
    data.setdefault("hidden_at", "")
    data.setdefault("hide_reason", "")
    data.setdefault("user_title_override", 0)
    data.setdefault("user_category_override", 0)
    data.setdefault("user_tags_override", 0)
    data["hidden"] = bool(data["hidden"])
    data["user_title_override"] = bool(data["user_title_override"])
    data["user_category_override"] = bool(data["user_category_override"])
    data["user_tags_override"] = bool(data["user_tags_override"])
    data["audio_url"] = f"/v1/recordings/{data['recording_id']}/audio"
    data["storage_mode"] = storage_mode
    return data


def read_recording_rows(index_path: Path, *, storage_mode: str) -> list[dict[str, Any]]:
    if not index_path.exists():
        return []
    with sqlite3.connect(index_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM recordings ORDER BY created_at DESC").fetchall()
    return [sqlite_row_to_dict(row, storage_mode=storage_mode) for row in rows]


def filter_recording_rows(
    rows: list[dict[str, Any]],
    *,
    include_hidden: bool = False,
    source_app: Optional[str] = None,
    source_feature: Optional[str] = None,
    category: Optional[str] = None,
    tag: Optional[str] = None,
) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for row in rows:
        if row.get("hidden") and not include_hidden:
            continue
        if source_app and row.get("source_app") != source_app:
            continue
        if source_feature and row.get("source_feature") != source_feature:
            continue
        if category and row.get("category") != category:
            continue
        if tag and tag not in set(row.get("tags") or []):
            continue
        filtered.append(row)
    return filtered


def recording_rows(
    *,
    include_hidden: bool = False,
    source_app: Optional[str] = None,
    source_feature: Optional[str] = None,
    category: Optional[str] = None,
    tag: Optional[str] = None,
) -> list[dict[str, Any]]:
    ensure_recording_store()
    canonical = read_recording_rows(recording_index_path(), storage_mode="canonical")
    legacy = read_recording_rows(legacy_recording_index_path(), storage_mode="legacy_read_only")
    seen = {row["recording_id"] for row in canonical}
    return filter_recording_rows(
        canonical + [row for row in legacy if row["recording_id"] not in seen],
        include_hidden=include_hidden,
        source_app=source_app,
        source_feature=source_feature,
        category=category,
        tag=tag,
    )


def read_recording_row(index_path: Path, recording_id: str, *, storage_mode: str) -> Optional[dict[str, Any]]:
    if not index_path.exists():
        return None
    with sqlite3.connect(index_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM recordings WHERE recording_id = ?", (recording_id,)).fetchone()
    return sqlite_row_to_dict(row, storage_mode=storage_mode) if row else None


def recording_row(recording_id: str) -> dict[str, Any]:
    ensure_recording_store()
    row = read_recording_row(recording_index_path(), recording_id, storage_mode="canonical")
    if row:
        return row
    row = read_recording_row(legacy_recording_index_path(), recording_id, storage_mode="legacy_read_only")
    if row:
        return row
    raise HTTPException(status_code=404, detail="recording not found")


def upsert_recording(record: dict[str, Any]) -> None:
    ensure_recording_store()
    for key, value in {
        "organized_status": "待整理",
        "hidden": 0,
        "hidden_at": "",
        "hide_reason": "",
        "user_title_override": 0,
        "user_category_override": 0,
        "user_tags_override": 0,
    }.items():
        record.setdefault(key, value)
    with sqlite3.connect(recording_index_path()) as conn:
        conn.execute(
            """
            INSERT INTO recordings (
                recording_id, schema, created_at, updated_at, status, title,
                provisional_title, category, tags_json, summary, audio_path,
                transcript_path, summary_path, title_path, metadata_path, mime_type,
                duration_seconds, audio_hash, asr_engine, naming_engine, error_message,
                source_app, source_feature, contexts_json, durability,
                transcript_status, title_status, summary_status,
                organized_status, hidden, hidden_at, hide_reason,
                user_title_override, user_category_override, user_tags_override
            )
            VALUES (
                :recording_id, :schema, :created_at, :updated_at, :status, :title,
                :provisional_title, :category, :tags_json, :summary, :audio_path,
                :transcript_path, :summary_path, :title_path, :metadata_path, :mime_type,
                :duration_seconds, :audio_hash, :asr_engine, :naming_engine, :error_message,
                :source_app, :source_feature, :contexts_json, :durability,
                :transcript_status, :title_status, :summary_status,
                :organized_status, :hidden, :hidden_at, :hide_reason,
                :user_title_override, :user_category_override, :user_tags_override
            )
            ON CONFLICT(recording_id) DO UPDATE SET
                updated_at=excluded.updated_at,
                status=excluded.status,
                title=excluded.title,
                category=excluded.category,
                tags_json=excluded.tags_json,
                summary=excluded.summary,
                transcript_path=excluded.transcript_path,
                summary_path=excluded.summary_path,
                title_path=excluded.title_path,
                metadata_path=excluded.metadata_path,
                duration_seconds=excluded.duration_seconds,
                asr_engine=excluded.asr_engine,
                naming_engine=excluded.naming_engine,
                error_message=excluded.error_message,
                source_app=excluded.source_app,
                source_feature=excluded.source_feature,
                contexts_json=excluded.contexts_json,
                durability=excluded.durability,
                transcript_status=excluded.transcript_status,
                title_status=excluded.title_status,
                summary_status=excluded.summary_status,
                organized_status=excluded.organized_status,
                hidden=excluded.hidden,
                hidden_at=excluded.hidden_at,
                hide_reason=excluded.hide_reason,
                user_title_override=excluded.user_title_override,
                user_category_override=excluded.user_category_override,
                user_tags_override=excluded.user_tags_override
            """,
            record,
        )
        conn.commit()


def audio_extension(mime_type: str) -> str:
    normalized = (mime_type or "").split(";", 1)[0].lower().strip()
    return {
        "audio/mp4": ".m4a",
        "audio/m4a": ".m4a",
        "audio/x-m4a": ".m4a",
        "audio/aac": ".aac",
        "audio/wav": ".wav",
        "audio/wave": ".wav",
        "audio/webm": ".webm",
        "audio/ogg": ".ogg",
        "application/octet-stream": ".m4a",
    }.get(normalized, mimetypes.guess_extension(normalized) or ".m4a")


def decode_audio_base64(value: str) -> bytes:
    raw = value.strip()
    if "," in raw and raw.lower().startswith("data:"):
        raw = raw.split(",", 1)[1]
    try:
        data = base64.b64decode(raw, validate=True)
    except Exception as exc:  # noqa: BLE001 - user-facing API error.
        raise HTTPException(status_code=422, detail="invalid audio_base64") from exc
    if not data:
        raise HTTPException(status_code=422, detail="audio_base64 is empty")
    if len(data) > 80 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="audio is too large")
    return data


def call_json(url: str, payload: Optional[dict[str, Any]] = None, timeout: float = 10.0) -> dict[str, Any]:
    if payload is None:
        request = UrlRequest(url, method="GET")
    else:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = UrlRequest(url, data=body, method="POST", headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - local LAN gateway boundary.
        return json.loads(response.read().decode("utf-8"))


def transcribe_audio(audio_path: Path) -> str:
    health = call_json(f"{FUNASR_BASE_URL}/health", timeout=2.0)
    if not health.get("ok"):
        raise RuntimeError("FunASR is not healthy")
    result = call_json(f"{FUNASR_BASE_URL}/transcribe", {"audio": str(audio_path)}, timeout=120.0)
    text = str(result.get("text") or "").strip()
    if not text:
        raise RuntimeError("FunASR did not return text")
    return text


def call_hermes_runtime(prompt: str, *, session_id: Optional[str] = None, timeout_seconds: int = 45) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "prompt": prompt,
        "source": "click_mobile_workspace",
        "timeout_seconds": max(10, min(timeout_seconds, 1800)),
        "concise": True,
    }
    if session_id:
        payload["session_id"] = session_id
    return call_json(f"{HERMES_RUNTIME_BASE_URL}/v1/runtime/chat", payload, timeout=max(timeout_seconds + 5, 15))


def extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
    match = re.search(r"\{.*\}", stripped, flags=re.S)
    raw = match.group(0) if match else stripped
    return json.loads(raw)


def derive_recording_metadata(transcript: str) -> dict[str, Any]:
    prompt = f"""
你是 Click 本地录音资产整理器。请只基于下面转写内容生成 JSON，不要扩写事实。
字段：
- title: 不超过18个中文字符
- category: 只能是 想法 / 任务 / 读书 / 项目 / 灵感 / 待整理 之一
- summary: 1句话
- tags: 2到5个短标签

转写内容：
{transcript}
"""
    response = call_hermes_runtime(prompt, timeout_seconds=60)
    if response.get("status") != "success":
        raise RuntimeError(str(response.get("error") or "Hermes runtime failed"))
    data = extract_json_object(str(response.get("reply") or "{}"))
    title = sanitize_title(str(data.get("title") or ""))
    category = str(data.get("category") or "待整理").strip()
    if category not in {"想法", "任务", "读书", "项目", "灵感", "待整理"}:
        category = "待整理"
    summary = str(data.get("summary") or "").strip()
    tags_raw = data.get("tags") if isinstance(data.get("tags"), list) else []
    tags = [str(tag).strip()[:12] for tag in tags_raw if str(tag).strip()][:5]
    if not title:
        raise RuntimeError("Hermes did not return a usable title")
    return {"title": title, "category": category, "summary": summary, "tags": tags}


def sanitize_title(value: str) -> str:
    cleaned = re.sub(r"[\r\n\t]+", " ", value).strip().strip('"“”')
    return cleaned[:18]


def provisional_title() -> str:
    return "录音 " + datetime.now().strftime("%Y-%m-%d %H:%M")


def normalize_source_app(value: Optional[str], fallback: str = "Click") -> str:
    cleaned = re.sub(r"\s+", " ", value or "").strip()
    return cleaned[:40] if cleaned else fallback


def normalize_source_feature(payload: RecordingCreate) -> str:
    explicit = re.sub(r"\s+", " ", payload.source_feature or "").strip()
    if explicit:
        return explicit[:80]
    source = (payload.source or "").lower()
    if "reader" in source:
        return "Reader voice note"
    if "hermes" in source and "saved" in source:
        return "Hermes saved voice"
    if "hermes" in source:
        return "Hermes voice message"
    if "shared" in source:
        return "Shared recording"
    if "inbox" in source:
        return "Inbox recording"
    return "Standalone recording"


def recording_bucket_for(payload: RecordingCreate) -> Path:
    source = (payload.source or "").lower()
    feature = normalize_source_feature(payload).lower()
    if "reader" in source or "reader" in feature:
        return recordings_dir() / "Click" / "Reader"
    if "hermes" in source and "saved" in source:
        return recordings_dir() / "Hermes" / "Saved"
    if "hermes" in source:
        return recordings_dir() / "Hermes" / "VoiceMessages"
    if "shared" in source or "shared" in feature:
        return recordings_dir() / "Shared"
    if "inbox" in source:
        return recordings_dir() / "Inbox"
    return recordings_dir() / "Click" / "Standalone"


def recording_status_fields(status: str) -> dict[str, str]:
    transcript_status = "ready" if status in {"transcribed", "transcribed_needs_naming", "named"} else "pending"
    title_status = "ready" if status == "named" else "pending"
    summary_status = "ready" if status == "named" else "pending"
    return {
        "transcript_status": transcript_status,
        "title_status": title_status,
        "summary_status": summary_status,
    }


def write_text(path: Path, value: str) -> None:
    path.write_text(value or "", encoding="utf-8")


def write_recording_files(record: dict[str, Any], metadata: dict[str, Any]) -> None:
    write_text(Path(record["transcript_path"]), metadata.get("transcript", ""))
    write_text(Path(record["summary_path"]), record.get("summary", ""))
    write_text(Path(record["title_path"]), record.get("title", ""))
    manifest = {
        "schema": RECORDING_SCHEMA,
        "asset_type": "audio_asset",
        "audio_id": record["recording_id"],
        "recording_id": record["recording_id"],
        "source_app": record.get("source_app", "Click"),
        "source_feature": record.get("source_feature", "Standalone recording"),
        "contexts": json.loads(record.get("contexts_json") or "[]"),
        "durability": record.get("durability", "durable"),
        "created_at": record["created_at"],
        "updated_at": record["updated_at"],
        "status": record["status"],
        "transcript_status": record.get("transcript_status", "pending"),
        "title_status": record.get("title_status", "pending"),
        "summary_status": record.get("summary_status", "pending"),
        "organized_status": record.get("organized_status", "待整理"),
        "hidden": bool(record.get("hidden", 0)),
        "hidden_at": record.get("hidden_at", ""),
        "hide_reason": record.get("hide_reason", ""),
        "user_overrides": {
            "title": bool(record.get("user_title_override", 0)),
            "category": bool(record.get("user_category_override", 0)),
            "tags": bool(record.get("user_tags_override", 0)),
        },
        "title": record["title"],
        "provisional_title": record["provisional_title"],
        "category": record["category"],
        "tags": json.loads(record["tags_json"]),
        "summary": record["summary"],
        "paths": {
            "audio": Path(record["audio_path"]).name,
            "transcript": Path(record["transcript_path"]).name,
            "summary": Path(record["summary_path"]).name,
            "title": Path(record["title_path"]).name,
        },
        "processors": {
            "asr": record["asr_engine"],
            "naming": record["naming_engine"],
        },
        "storage": {
            "canonical_root": str(recordings_dir()),
            "legacy_roots": [str(legacy_recordings_dir())],
            "legacy_read_only": True,
        },
        "error_message": record["error_message"],
    }
    Path(record["metadata_path"]).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def create_recording(payload: RecordingCreate) -> dict[str, Any]:
    ensure_recording_store()
    audio = decode_audio_base64(payload.audio_base64)
    created = now_iso()
    recording_id = f"rec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
    directory = recording_bucket_for(payload) / recording_id
    directory.mkdir(parents=True, exist_ok=False)
    extension = audio_extension(payload.mime_type)
    audio_path = directory / f"original{extension}"
    audio_path.write_bytes(audio)
    title = provisional_title()
    record: dict[str, Any] = {
        "recording_id": recording_id,
        "schema": RECORDING_SCHEMA,
        "created_at": created,
        "updated_at": created,
        "status": "saved",
        "title": title,
        "provisional_title": title,
        "category": "待整理",
        "tags_json": json.dumps([], ensure_ascii=False),
        "summary": "",
        "audio_path": str(audio_path),
        "transcript_path": str(directory / "transcript.txt"),
        "summary_path": str(directory / "summary.txt"),
        "title_path": str(directory / "title.txt"),
        "metadata_path": str(directory / "metadata.json"),
        "mime_type": payload.mime_type,
        "duration_seconds": payload.duration_seconds,
        "audio_hash": hashlib.sha256(audio).hexdigest(),
        "asr_engine": "funasr-local",
        "naming_engine": "hermes-runtime",
        "error_message": "",
        "source": payload.source,
        "source_app": normalize_source_app(payload.source_app, "Click"),
        "source_feature": normalize_source_feature(payload),
        "contexts_json": json.dumps(payload.contexts, ensure_ascii=False),
        "durability": payload.durability if payload.durability in {"durable", "temporary"} else "durable",
        "organized_status": "待整理",
        "hidden": 0,
        "hidden_at": "",
        "hide_reason": "",
        "user_title_override": 0,
        "user_category_override": 0,
        "user_tags_override": 0,
        **recording_status_fields("saved"),
    }
    write_recording_files(record, {"transcript": ""})
    upsert_recording(record)

    transcript = ""
    try:
        transcript = transcribe_audio(audio_path)
        record["status"] = "transcribed"
        record["updated_at"] = now_iso()
        record.update(recording_status_fields(record["status"]))
        write_recording_files(record, {"transcript": transcript})
        upsert_recording(record)
    except Exception as exc:  # noqa: BLE001 - recording must survive ASR failure.
        record["status"] = "needs_processing"
        record["error_message"] = f"ASR pending: {exc}"
        record["updated_at"] = now_iso()
        record.update(recording_status_fields(record["status"]))
        write_recording_files(record, {"transcript": transcript})
        upsert_recording(record)
        return {"ok": True, "recording": sqlite_record_by_id(recording_id), "warning": record["error_message"]}

    try:
        metadata = derive_recording_metadata(transcript)
        record["title"] = metadata["title"]
        record["category"] = metadata["category"]
        record["summary"] = metadata["summary"]
        record["tags_json"] = json.dumps(metadata["tags"], ensure_ascii=False)
        record["status"] = "named"
        record["error_message"] = ""
    except Exception as exc:  # noqa: BLE001 - Hermes naming is a processor, not a storage dependency.
        record["status"] = "transcribed_needs_naming"
        record["error_message"] = f"Hermes naming pending: {exc}"
    record["updated_at"] = now_iso()
    record.update(recording_status_fields(record["status"]))
    write_recording_files(record, {"transcript": transcript})
    upsert_recording(record)
    return {"ok": True, "recording": sqlite_record_by_id(recording_id)}


def record_for_update(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "recording_id": row["recording_id"],
        "schema": row.get("schema", RECORDING_SCHEMA),
        "created_at": row.get("created_at", now_iso()),
        "updated_at": row.get("updated_at", now_iso()),
        "status": row.get("status", "saved"),
        "title": row.get("title", ""),
        "provisional_title": row.get("provisional_title", row.get("title", "")),
        "category": row.get("category", "待整理"),
        "tags_json": json.dumps(row.get("tags", []), ensure_ascii=False),
        "summary": row.get("summary", ""),
        "audio_path": row["audio_path"],
        "transcript_path": row["transcript_path"],
        "summary_path": row["summary_path"],
        "title_path": row["title_path"],
        "metadata_path": row["metadata_path"],
        "mime_type": row.get("mime_type", "audio/m4a"),
        "duration_seconds": row.get("duration_seconds"),
        "audio_hash": row.get("audio_hash", ""),
        "asr_engine": row.get("asr_engine", "funasr-local"),
        "naming_engine": row.get("naming_engine", "hermes-runtime"),
        "error_message": row.get("error_message", ""),
        "source_app": row.get("source_app", "Click"),
        "source_feature": row.get("source_feature", "Standalone recording"),
        "contexts_json": json.dumps(row.get("contexts", []), ensure_ascii=False),
        "durability": row.get("durability", "durable"),
        "transcript_status": row.get("transcript_status", "pending"),
        "title_status": row.get("title_status", "pending"),
        "summary_status": row.get("summary_status", "pending"),
        "organized_status": row.get("organized_status", "待整理"),
        "hidden": 1 if row.get("hidden") else 0,
        "hidden_at": row.get("hidden_at", ""),
        "hide_reason": row.get("hide_reason", ""),
        "user_title_override": 1 if row.get("user_title_override") else 0,
        "user_category_override": 1 if row.get("user_category_override") else 0,
        "user_tags_override": 1 if row.get("user_tags_override") else 0,
    }


def transcript_for_record(row: dict[str, Any]) -> str:
    path = Path(row.get("transcript_path") or "")
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def update_recording_metadata(record: dict[str, Any], transcript: Optional[str] = None) -> dict[str, Any]:
    record["updated_at"] = now_iso()
    write_recording_files(record, {"transcript": transcript if transcript is not None else transcript_for_record(record)})
    upsert_recording(record)
    return sqlite_record_by_id(record["recording_id"])


def sqlite_record_by_id(recording_id: str) -> dict[str, Any]:
    return recording_row(recording_id)


def edge_tts_path() -> Optional[str]:
    configured = os.getenv("CLICK_EDGE_TTS_PATH")
    candidates = [
        configured,
        str(Path.home() / ".hermes" / "tts-venv" / "bin" / "edge-tts"),
        shutil.which("edge-tts"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


def synthesize_edge_tts(text: str, output_path: Path) -> bool:
    command = edge_tts_path()
    if not command:
        return False
    try:
        subprocess.run(
            [command, "--voice", EDGE_TTS_VOICE, "--text", text, "--write-media", str(output_path)],
            check=True,
            capture_output=True,
            text=True,
            timeout=90,
        )
        return output_path.exists() and output_path.stat().st_size > 0
    except Exception:
        return False


def recording_list_html() -> str:
    return """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <title>Click 录音</title>
  <style>
    :root{color-scheme:dark;background:#050505;color:#f6f0e8;font-family:-apple-system,BlinkMacSystemFont,"Microsoft YaHei",sans-serif}
    body{margin:0;background:#050505;min-height:100vh}
    main{max-width:860px;margin:0 auto;padding:calc(env(safe-area-inset-top) + 22px) 18px 32px}
    header{display:flex;gap:10px;align-items:center;justify-content:space-between;margin-bottom:18px}
    h1{font-size:26px;margin:0} p{color:#aaa18f;line-height:1.5}
    .actions{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:18px 0}
    button,a.button{border:0;border-radius:10px;padding:15px 16px;background:#f0d36b;color:#15120a;font-weight:800;font-size:16px;text-decoration:none;text-align:center}
    button.secondary,a.secondary{background:#24231e;color:#f6f0e8}
    button.danger{background:#9b3d32;color:white}
    .card{border:1px solid #292720;background:#11110e;border-radius:12px;padding:14px;margin:12px 0}
    .meta{font-size:13px;color:#8f8878}.status{display:inline-block;padding:3px 8px;border-radius:999px;background:#222015;color:#e4d48a;font-size:12px}
    .row{display:flex;flex-wrap:wrap;gap:8px;align-items:center}.row button{font-size:13px;padding:8px 10px}.row input{min-width:150px}
    input,select{border:1px solid #343024;background:#15140f;color:#f6f0e8;border-radius:8px;padding:8px}
    details{margin-top:10px;color:#cfc5ad}pre{white-space:pre-wrap;overflow:auto;background:#080806;border:1px solid #242116;border-radius:8px;padding:10px}
    audio{width:100%;margin-top:10px}.empty{border:1px dashed #3a362a;border-radius:12px;padding:26px;text-align:center;color:#aaa18f}
  </style>
</head>
<body>
<main>
  <header>
    <h1>录音</h1>
    <a class="button secondary" href="/home">首页</a>
  </header>
  <p>录音会保存到本机 Recordings 总仓库。Click、Reader、Hermes 只是来源或处理器，不拥有录音资产。这里可以编辑标题/分类、查看转写和 metadata，隐藏只从列表移开，不删除文件。</p>
  <section class="actions">
    <button id="start">开始录音</button>
    <button id="stop" class="danger" disabled>停止并保存</button>
  </section>
  <p id="state">准备就绪</p>
  <section id="list"></section>
</main>
<script>
let recorder=null, chunks=[], startedAt=0, mimeType='audio/m4a';
function pickMime(){
  const types=['audio/mp4','audio/webm;codecs=opus','audio/webm','audio/ogg'];
  for (const t of types){ if (window.MediaRecorder && MediaRecorder.isTypeSupported(t)) return t; }
  return '';
}
function asDataUrl(blob){
  return new Promise((resolve,reject)=>{ const r=new FileReader(); r.onload=()=>resolve(r.result); r.onerror=reject; r.readAsDataURL(blob); });
}
async function loadList(){
  const box=document.getElementById('list');
  const res=await fetch('/v1/recordings');
  const data=await res.json();
  if(!data.recordings.length){ box.innerHTML='<div class="empty">还没有录音</div>'; return; }
  box.innerHTML=data.recordings.map(r=>`
    <article class="card" data-id="${escapeHtml(r.recording_id)}">
      <strong>${escapeHtml(r.title)}</strong>
      <span class="status">${escapeHtml(r.organized_status||'待整理')}</span>
      <span class="status">${escapeHtml(r.status)}</span>
      <p class="meta">${escapeHtml(r.category)} · ${escapeHtml(r.source_app)} / ${escapeHtml(r.source_feature)} · ${new Date(r.created_at).toLocaleString()}</p>
      ${r.summary?`<p>${escapeHtml(r.summary)}</p>`:''}
      <p class="meta">标签：${(r.tags||[]).map(escapeHtml).join('、')||'无'}</p>
      <audio controls src="${r.audio_url}"></audio>
      <div class="row">
        <input class="title" value="${escapeAttr(r.title)}" aria-label="标题">
        <select class="category" aria-label="分类">${['待整理','想法','任务','读书','项目','灵感'].map(c=>`<option ${c===r.category?'selected':''}>${c}</option>`).join('')}</select>
        <button onclick="saveEdit('${escapeAttr(r.recording_id)}')">保存</button>
        <button onclick="reprocess('${escapeAttr(r.recording_id)}')">重新整理</button>
        <button class="danger" onclick="hideRecording('${escapeAttr(r.recording_id)}')">隐藏</button>
      </div>
      <details><summary>转写 / metadata</summary><pre class="details">正在加载...</pre></details>
    </article>`).join('');
  document.querySelectorAll('details').forEach(d=>d.addEventListener('toggle',async()=>{
    if(!d.open||d.dataset.loaded)return;
    const id=d.closest('article').dataset.id; const target=d.querySelector('pre');
    const r=await fetch('/v1/recordings/'+encodeURIComponent(id)); const detail=await r.json();
    target.textContent=JSON.stringify(detail.recording,null,2); d.dataset.loaded='1';
  }));
}
function escapeHtml(s){return String(s||'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));}
function escapeAttr(s){return escapeHtml(s).replace(/`/g,'&#96;');}
async function saveEdit(id){const card=document.querySelector(`[data-id="${CSS.escape(id)}"]`); const title=card.querySelector('.title').value; const category=card.querySelector('.category').value; const r=await fetch('/v1/recordings/'+encodeURIComponent(id),{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({title,category,organized_status:'已整理'})}); document.getElementById('state').textContent=r.ok?'已保存编辑':'保存失败'; await loadList();}
async function reprocess(id){const r=await fetch('/v1/recordings/'+encodeURIComponent(id)+'/reprocess',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({dry_run:true})}); const d=await r.json(); document.getElementById('state').textContent=d.ok?'已提交整理检查':'整理失败';}
async function hideRecording(id){const r=await fetch('/v1/recordings/'+encodeURIComponent(id)+'/hide',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({reason:'mobile hidden'})}); document.getElementById('state').textContent=r.ok?'已隐藏':'隐藏失败'; await loadList();}
document.getElementById('start').onclick=async()=>{
  const stream=await navigator.mediaDevices.getUserMedia({audio:true});
  mimeType=pickMime();
  recorder=new MediaRecorder(stream,mimeType?{mimeType}:undefined);
  chunks=[]; startedAt=Date.now();
  recorder.ondataavailable=e=>{if(e.data&&e.data.size)chunks.push(e.data)};
  recorder.onstop=async()=>{
    document.getElementById('state').textContent='正在保存和转写...';
    const blob=new Blob(chunks,{type:mimeType||'audio/m4a'});
    const audio_base64=await asDataUrl(blob);
    const res=await fetch('/v1/recordings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({audio_base64,mime_type:blob.type||'audio/m4a',duration_seconds:(Date.now()-startedAt)/1000})});
    const data=await res.json();
    document.getElementById('state').textContent=data.ok?'已保存':'保存失败';
    await loadList();
    stream.getTracks().forEach(t=>t.stop());
  };
  recorder.start();
  document.getElementById('start').disabled=true; document.getElementById('stop').disabled=false; document.getElementById('state').textContent='正在录音';
};
document.getElementById('stop').onclick=()=>{ if(recorder){ recorder.stop(); } document.getElementById('start').disabled=false; document.getElementById('stop').disabled=true; };
loadList().catch(()=>{document.getElementById('list').innerHTML='<div class="empty">录音列表暂时不可用</div>'});
</script>
</body>
</html>
"""


def home_html() -> str:
    return """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <title>Click</title>
  <style>
    :root{color-scheme:dark;background:#050505;color:#f6f0e8;font-family:-apple-system,BlinkMacSystemFont,"Microsoft YaHei",sans-serif}
    body{margin:0;min-height:100vh;background:#050505}
    main{max-width:760px;margin:0 auto;padding:calc(env(safe-area-inset-top) + 34px) 22px 34px}
    h1{font-size:44px;margin:0 0 8px}p{color:#aaa18f;line-height:1.5}
    .grid{display:grid;gap:14px;margin-top:30px}
    a{display:grid;grid-template-columns:54px 1fr;gap:16px;text-decoration:none;border-radius:16px;padding:20px;background:#14130f;border:1px solid #2f2b21;color:#f8f1dc;align-items:center}
    a strong{display:block;font-size:24px;margin-bottom:8px}a span{color:#aaa18f}
    a.primary{background:#f0d36b;color:#15120a}a.primary span{color:#4d421c}
    .entry-icon{width:54px;height:54px;border-radius:14px;display:grid;place-items:center;background:#24231e}
    .primary .entry-icon{background:#15120a}.entry-icon svg{width:34px;height:34px}
    .status{margin-top:28px;border-top:1px solid #292720;padding-top:18px;font-size:14px;color:#aaa18f}
  </style>
</head>
<body>
<main>
  <h1>Click</h1>
  <p>本地优先阅读工作台。手机只是入口，书、录音、Hermes 处理都在 Mac 本地完成。</p>
  <section class="grid">
    <a class="primary" href="/library"><span class="entry-icon icon-reading" aria-hidden="true"><svg viewBox="0 0 48 48" fill="none"><path d="M8 12h14c5 0 9 4 9 9v19H17c-5 0-9-4-9-9V12Z" fill="#f8f1dc"/><path d="M26 12h14v19c0 5-4 9-9 9h-5V12Z" fill="#d8c7a6"/><path d="M15 22h10M15 29h8M31 22h5M31 29h5" stroke="#15120a" stroke-width="2.6" stroke-linecap="round"/></svg></span><span><strong>阅读</strong><span>打开书库和现有句子级阅读器</span></span></a>
    <a href="/recordings"><span class="entry-icon icon-recordings-local" aria-hidden="true"><svg viewBox="0 0 48 48" fill="none"><rect x="19" y="8" width="10" height="20" rx="5" fill="#f6f0e8"/><path d="M13 23c0 7 4 11 11 11s11-4 11-11M24 34v6M18 40h12" stroke="#f6f0e8" stroke-width="3" stroke-linecap="round"/><path d="M8 19c2-3 2-6 0-9M40 19c-2-3-2-6 0-9" stroke="#d86b5d" stroke-width="2.5" stroke-linecap="round"/></svg></span><span><strong>录音</strong><span>保存到本机 Recordings 总仓库，并由 Hermes 处理标题和摘要</span></span></a>
    <a href="/hermes"><span class="entry-icon icon-hermes" aria-hidden="true"><svg viewBox="0 0 48 48" fill="none"><path d="M24 7l14 8v17L24 41 10 32V15l14-8Z" fill="#e6d28b"/><path d="M17 18h14M17 24h14M21 30h6" stroke="#15120a" stroke-width="3" stroke-linecap="round"/></svg></span><span><strong>Hermes</strong><span>和 Mac 上的 Hermes 对话，支持文字和语音消息</span></span></a>
  </section>
  <section class="status" id="diag">正在检查 Mac 服务...</section>
</main>
<script>
fetch('/v1/mobile/diagnostics').then(r=>r.json()).then(d=>{
  document.getElementById('diag').textContent=`Reader ${d.reader_api.ok?'可用':'异常'} · 录音 ${d.recordings.ok?'可用':'异常'} · Hermes ${d.hermes.ok?'可用':'未连接'} · FunASR ${d.funasr.ok?'可用':'未连接'}`;
}).catch(()=>{document.getElementById('diag').textContent='诊断暂时不可用'});
</script>
</body>
</html>
"""


def hermes_html() -> str:
    return """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <title>Click Hermes</title>
  <style>
    :root{color-scheme:dark;background:#050505;color:#f6f0e8;font-family:-apple-system,BlinkMacSystemFont,"Microsoft YaHei",sans-serif}
    body{margin:0;background:#050505;min-height:100vh}main{max-width:860px;margin:0 auto;padding:calc(env(safe-area-inset-top) + 20px) 14px 24px}
    header{display:flex;justify-content:space-between;align-items:center}h1{font-size:26px;margin:0}
    #log{display:flex;flex-direction:column;gap:10px;margin:18px 0 130px}.msg{border-radius:12px;padding:12px 14px;line-height:1.5;white-space:pre-wrap}.user{background:#24231e}.bot{background:#121a16;border:1px solid #26382c}
    form{position:fixed;left:0;right:0;bottom:0;background:#090908;border-top:1px solid #28251c;padding:12px;display:grid;grid-template-columns:1fr auto auto;gap:8px}
    textarea{min-height:48px;max-height:120px;border-radius:10px;border:1px solid #343024;background:#15140f;color:#f6f0e8;padding:10px;font-size:16px}
    button,a.button{border:0;border-radius:10px;padding:0 14px;background:#f0d36b;color:#15120a;font-weight:800;text-decoration:none;display:flex;align-items:center}
    button.secondary,a.secondary{background:#24231e;color:#f6f0e8}.top{height:38px}
  </style>
</head>
<body>
<main>
  <header><h1>Hermes</h1><a class="button secondary top" href="/home">首页</a></header>
  <section id="log"><div class="msg bot">可以发文字，也可以点语音。语音消息会放到 HermesMobile VoiceInbox，不会混进长期录音资产。状态会显示：录音中、上传中、转写中、Hermes 思考中、错误。语音回复优先使用 Mac 端 edge-tts。</div></section>
</main>
<form id="form">
  <textarea id="text" placeholder="发给 Hermes..."></textarea>
  <button type="button" id="voice">语音</button>
  <button type="submit">发送</button>
</form>
<script>
const log=document.getElementById('log'); let sessionId=null, recorder=null, chunks=[], startedAt=0, voiceStream=null;
function add(kind,text,audio){const el=document.createElement('div');el.className='msg '+kind;el.textContent=text;if(audio){const p=document.createElement('audio');p.controls=true;p.src=audio;el.appendChild(document.createElement('br'));el.appendChild(p)}log.appendChild(el);window.scrollTo(0,document.body.scrollHeight)}
async function chat(message){add('user',message); const r=await fetch('/v1/runtime/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message,session_id:sessionId})}); const d=await r.json(); sessionId=d.session_id||sessionId; add('bot',d.reply||d.error||'Hermes 暂时不可用');}
document.getElementById('form').onsubmit=e=>{e.preventDefault();const t=document.getElementById('text');const v=t.value.trim(); if(v){t.value=''; chat(v).catch(err=>add('bot','发送失败：'+err));}};
function pickMime(){for(const t of ['audio/mp4','audio/webm;codecs=opus','audio/webm','audio/ogg']){if(window.MediaRecorder&&MediaRecorder.isTypeSupported(t))return t}return ''}
function dataUrl(blob){return new Promise((res,rej)=>{const r=new FileReader();r.onload=()=>res(r.result);r.onerror=rej;r.readAsDataURL(blob)})}
document.getElementById('voice').onclick=async()=>{
  const btn=document.getElementById('voice');
  if(recorder&&recorder.state==='recording'){recorder.stop();btn.textContent='语音';return}
  add('bot','状态：录音中');
  voiceStream=await navigator.mediaDevices.getUserMedia({audio:true}); const mt=pickMime(); chunks=[]; startedAt=Date.now();
  recorder=new MediaRecorder(voiceStream,mt?{mimeType:mt}:undefined); recorder.ondataavailable=e=>{if(e.data&&e.data.size)chunks.push(e.data)};
  recorder.onstop=async()=>{const blob=new Blob(chunks,{type:mt||'audio/m4a'}); voiceStream.getTracks().forEach(t=>t.stop()); add('user','[语音消息]'); add('bot','状态：上传中 / 转写中 / Hermes 思考中'); const audio_base64=await dataUrl(blob); const r=await fetch('/v1/voice/message',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({audio_base64,mime_type:blob.type||'audio/m4a',duration_seconds:(Date.now()-startedAt)/1000,session_id:sessionId,tts:true})}); const d=await r.json(); sessionId=d.session_id||sessionId; add('bot',(d.transcript?'转写：'+d.transcript+'\\n\\n':'')+(d.reply_text||d.error||'语音处理失败'),d.audio_url||null);};
  recorder.start();btn.textContent='停止';
};
</script>
</body>
</html>
"""


def html_response_with_access_cookies(content: str, request: Request) -> HTMLResponse:
    response = HTMLResponse(content)
    device_id, access_token = request_device_identity(request)
    if device_id:
        response.set_cookie("click_device_id", device_id, httponly=False, samesite="lax")
    if access_token:
        response.set_cookie("click_access_token", access_token, httponly=False, samesite="lax")
    return response


@router.get("/home", response_class=HTMLResponse)
def mobile_home(request: Request) -> HTMLResponse:
    return html_response_with_access_cookies(home_html(), request)


@router.get("/recordings", response_class=HTMLResponse)
def recordings_page(request: Request) -> HTMLResponse:
    require_mobile_access(request)
    return html_response_with_access_cookies(recording_list_html(), request)


@router.get("/hermes", response_class=HTMLResponse)
def hermes_page(request: Request) -> HTMLResponse:
    require_mobile_access(request)
    return html_response_with_access_cookies(hermes_html(), request)


@router.get("/v1/mobile/access/status")
def mobile_access_status(
    request: Request,
    device_id: Optional[str] = Query(default=None),
    access_token: Optional[str] = Query(default=None),
) -> dict[str, Any]:
    resolved_device_id, resolved_token = request_device_identity(request, device_id, access_token)
    if not resolved_device_id:
        return {
            "ok": True,
            "schema": MOBILE_ACCESS_SCHEMA,
            "status": "local_debug",
            "authorized": True,
            "pending": False,
            "device_id": "",
            "token_required": False,
        }
    return access_status_payload(resolved_device_id, resolved_token)


@router.post("/v1/mobile/access/request")
def mobile_access_request(payload: MobileAccessRequest = Body(...)) -> dict[str, Any]:
    device_id = normalize_device_id(payload.device_id)
    if not device_id:
        raise HTTPException(status_code=422, detail="device_id is required")
    if device_access_record(device_id):
        return {**access_status_payload(device_id), "already_authorized": True}
    pending = read_json_object(pending_devices_path())
    pending[device_id] = {
        "device_id": device_id,
        "device_name": normalize_device_name(payload.device_name),
        "platform": normalize_device_name(payload.platform, "unknown"),
        "requested_at": pending.get(device_id, {}).get("requested_at") or now_iso(),
        "updated_at": now_iso(),
    }
    write_json_object(pending_devices_path(), pending)
    return {**access_status_payload(device_id), "ok": True}


@router.get("/v1/mobile/access/pending")
def mobile_access_pending() -> dict[str, Any]:
    pending = read_json_object(pending_devices_path())
    return {
        "ok": True,
        "schema": MOBILE_ACCESS_SCHEMA,
        "pending": list(pending.values()),
    }


@router.post("/v1/mobile/access/approve")
def mobile_access_approve(payload: MobileAccessApprove = Body(...)) -> dict[str, Any]:
    device_id = normalize_device_id(payload.device_id)
    if not device_id:
        raise HTTPException(status_code=422, detail="device_id is required")
    pending = read_json_object(pending_devices_path())
    allowed = read_json_object(allowed_devices_path())
    token = issue_access_token()
    pending_record = pending.pop(device_id, {})
    allowed[device_id] = {
        "device_id": device_id,
        "device_name": normalize_device_name(payload.device_name or pending_record.get("device_name")),
        "platform": pending_record.get("platform", "unknown"),
        "approved_at": now_iso(),
        "token_hash": token_hash(token),
        "revoked_at": "",
    }
    write_json_object(pending_devices_path(), pending)
    write_json_object(allowed_devices_path(), allowed)
    return {
        **access_status_payload(device_id, token),
        "access_token": token,
        "token_note": "Only shown once; store it on the local mobile app.",
    }


@router.post("/v1/mobile/access/revoke")
def mobile_access_revoke(payload: MobileAccessRevoke = Body(...)) -> dict[str, Any]:
    device_id = normalize_device_id(payload.device_id)
    if not device_id:
        raise HTTPException(status_code=422, detail="device_id is required")
    allowed = read_json_object(allowed_devices_path())
    if device_id in allowed:
        allowed[device_id]["revoked_at"] = now_iso()
        write_json_object(allowed_devices_path(), allowed)
    return {"ok": True, "schema": MOBILE_ACCESS_SCHEMA, "device_id": device_id, "status": "revoked"}


@router.get("/v1/recordings/health")
def recordings_health() -> dict[str, Any]:
    ensure_recording_store()
    probe = recordings_dir() / "_index" / ".write_probe"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        writable = True
    except Exception:
        writable = False
    return {
        "ok": writable,
        "schema": RECORDING_SCHEMA,
        "canonical_root": str(recordings_dir()),
        "storage_root": str(recordings_dir()),
        "index": str(recording_index_path()),
        "legacy_root": str(legacy_recordings_dir()),
        "legacy_read_only": True,
        "legacy_read_paths": [str(legacy_recordings_dir())],
        "uses_legacy_click_path_as_canonical": False,
        "forbidden_hermes_recordings_path": str(forbidden_hermes_recordings_dir()),
        "uses_forbidden_hermes_recordings_path": False,
        "top_level_layout": ["Inbox", "Click/Reader", "Click/Standalone", "Hermes/VoiceMessages", "Hermes/Saved", "Shared", "_index"],
    }


@router.post("/v1/recordings")
def post_recording(request: Request, payload: RecordingCreate = Body(...)) -> dict[str, Any]:
    require_mobile_access(request, device_id=payload.device_id, access_token=payload.access_token)
    return create_recording(payload)


@router.get("/v1/recordings")
def get_recordings(
    request: Request,
    include_hidden: bool = Query(default=False),
    source_app: Optional[str] = Query(default=None),
    source_feature: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    tag: Optional[str] = Query(default=None),
) -> dict[str, Any]:
    require_mobile_access(request)
    return {
        "ok": True,
        "schema": RECORDING_SCHEMA,
        "recordings": recording_rows(
            include_hidden=include_hidden,
            source_app=source_app,
            source_feature=source_feature,
            category=category,
            tag=tag,
        ),
    }


@router.get("/v1/recordings/{recording_id}")
def get_recording(request: Request, recording_id: str) -> dict[str, Any]:
    require_mobile_access(request)
    return {"ok": True, "recording": recording_row(recording_id)}


@router.patch("/v1/recordings/{recording_id}")
def patch_recording(request: Request, recording_id: str, payload: RecordingPatch = Body(...)) -> dict[str, Any]:
    require_mobile_access(request)
    row = recording_row(recording_id)
    if row.get("storage_mode") != "canonical":
        raise HTTPException(status_code=409, detail="legacy recording is read-only")
    record = record_for_update(row)
    if payload.title is not None:
        title = sanitize_title(payload.title)
        if title:
            record["title"] = title
            record["user_title_override"] = 1
    if payload.category is not None:
        category = str(payload.category).strip()[:40] or "待整理"
        record["category"] = category
        record["user_category_override"] = 1
    if payload.tags is not None:
        tags = [str(tag).strip()[:24] for tag in payload.tags if str(tag).strip()][:12]
        record["tags_json"] = json.dumps(tags, ensure_ascii=False)
        record["user_tags_override"] = 1
    if payload.organized_status is not None:
        record["organized_status"] = "已整理" if payload.organized_status == "已整理" else "待整理"
    updated = update_recording_metadata(record)
    return {"ok": True, "schema": RECORDING_SCHEMA, "recording": updated}


@router.post("/v1/recordings/{recording_id}/hide")
def hide_recording(request: Request, recording_id: str, payload: RecordingHide = Body(default=RecordingHide())) -> dict[str, Any]:
    require_mobile_access(request)
    row = recording_row(recording_id)
    if row.get("storage_mode") != "canonical":
        raise HTTPException(status_code=409, detail="legacy recording is read-only")
    record = record_for_update(row)
    record["hidden"] = 1
    record["hidden_at"] = now_iso()
    record["hide_reason"] = str(payload.reason or "")[:120]
    updated = update_recording_metadata(record)
    return {"ok": True, "schema": RECORDING_SCHEMA, "hidden": True, "recording": updated}


@router.post("/v1/recordings/{recording_id}/reprocess")
def reprocess_recording(request: Request, recording_id: str, payload: RecordingReprocess = Body(...)) -> dict[str, Any]:
    require_mobile_access(request)
    row = recording_row(recording_id)
    if row.get("storage_mode") != "canonical":
        raise HTTPException(status_code=409, detail="legacy recording is read-only")
    transcript = transcript_for_record(row)
    if payload.dry_run:
        return {
            "ok": True,
            "schema": RECORDING_SCHEMA,
            "dry_run": True,
            "would_transcribe": not bool(transcript),
            "would_call_hermes": bool(transcript),
            "preserve_user_title": bool(row.get("user_title_override")) and not payload.allow_overwrite_user_edits,
            "preserve_user_category": bool(row.get("user_category_override")) and not payload.allow_overwrite_user_edits,
        }
    record = record_for_update(row)
    try:
        if not transcript:
            transcript = transcribe_audio(Path(row["audio_path"]))
            record["status"] = "transcribed"
            record.update(recording_status_fields(record["status"]))
        metadata = derive_recording_metadata(transcript)
        if not row.get("user_title_override") or payload.allow_overwrite_user_edits:
            record["title"] = metadata["title"]
            record["user_title_override"] = 0
        if not row.get("user_category_override") or payload.allow_overwrite_user_edits:
            record["category"] = metadata["category"]
            record["user_category_override"] = 0
        if not row.get("user_tags_override") or payload.allow_overwrite_user_edits:
            record["tags_json"] = json.dumps(metadata["tags"], ensure_ascii=False)
            record["user_tags_override"] = 0
        record["summary"] = metadata["summary"]
        record["status"] = "named"
        record["organized_status"] = "已整理"
        record["error_message"] = ""
        record.update(recording_status_fields(record["status"]))
    except Exception as exc:  # noqa: BLE001
        record["status"] = "needs_processing"
        record["error_message"] = f"Reprocess pending: {exc}"
    updated = update_recording_metadata(record, transcript)
    return {"ok": True, "schema": RECORDING_SCHEMA, "recording": updated}


@router.get("/v1/recordings/{recording_id}/audio")
def get_recording_audio(request: Request, recording_id: str) -> Response:
    require_mobile_access(request)
    record = recording_row(recording_id)
    audio_path = Path(record["audio_path"])
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="audio file missing")
    media_type = record.get("mime_type") or mimetypes.guess_type(str(audio_path))[0] or "application/octet-stream"
    return Response(content=audio_path.read_bytes(), media_type=media_type)


@router.get("/v1/mobile/diagnostics")
def mobile_diagnostics() -> dict[str, Any]:
    rec_health = recordings_health()
    try:
        hermes_health = call_json(f"{HERMES_RUNTIME_BASE_URL}/v1/runtime/health", timeout=2.0)
        hermes_ok = hermes_health.get("status") == "ok" or hermes_health.get("ok") is True
    except Exception as exc:  # noqa: BLE001 - diagnostics should not fail the page.
        hermes_health = {"error": str(exc)}
        hermes_ok = False
    try:
        funasr_health = call_json(f"{FUNASR_BASE_URL}/health", timeout=2.0)
        funasr_ok = bool(funasr_health.get("ok"))
    except Exception as exc:  # noqa: BLE001
        funasr_health = {"error": str(exc)}
        funasr_ok = False
    return {
        "ok": True,
        "schema": "click.mobile_workspace.diagnostics.v1",
        "reader_api": {"ok": True, "home": "/home", "library": "/library", "lan_reader": "/lan/reader"},
        "recordings": rec_health,
        "hermes": {"ok": hermes_ok, "base_url": HERMES_RUNTIME_BASE_URL, "health": hermes_health},
        "funasr": {"ok": funasr_ok, "base_url": FUNASR_BASE_URL, "health": funasr_health},
        "edge_tts": {"ok": edge_tts_path() is not None, "voice": EDGE_TTS_VOICE},
        "recordings_store": {
            "canonical_root": str(recordings_dir()),
            "legacy_root": str(legacy_recordings_dir()),
            "legacy_read_only": True,
        },
        "mobile_access": {
            "schema": MOBILE_ACCESS_SCHEMA,
            "allowed_devices": str(allowed_devices_path()),
            "pending_devices": str(pending_devices_path()),
            "local_debug_without_device_id": True,
        },
    }


@router.get("/v1/runtime/health")
def mobile_runtime_health() -> dict[str, Any]:
    try:
        payload = call_json(f"{HERMES_RUNTIME_BASE_URL}/v1/runtime/health", timeout=3.0)
        return {"ok": True, "proxied": True, "hermes": payload}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "proxied": True, "error": str(exc)}


@router.post("/v1/runtime/chat")
def mobile_runtime_chat(request: Request, payload: HermesChatCreate = Body(...)) -> dict[str, Any]:
    require_mobile_access(request, device_id=payload.device_id, access_token=payload.access_token)
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="message is empty")
    try:
        result = call_hermes_runtime(message, session_id=payload.session_id, timeout_seconds=120)
        return {
            "ok": result.get("status") == "success",
            "schema": "click.mobile_workspace.hermes_chat.v1",
            "reply": str(result.get("reply") or ""),
            "session_id": result.get("session_id") or payload.session_id,
            "error": result.get("error"),
            "provider_info": result.get("provider_info", {}),
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "schema": "click.mobile_workspace.hermes_chat.v1", "reply": "", "session_id": payload.session_id, "error": str(exc)}


@router.post("/v1/voice/message")
def post_voice_message(request: Request, payload: HermesVoiceCreate = Body(...)) -> dict[str, Any]:
    require_mobile_access(request, device_id=payload.device_id, access_token=payload.access_token)
    ensure_voice_store()
    audio = decode_audio_base64(payload.audio_base64)
    voice_id = f"voice_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
    directory = voice_inbox_dir() / voice_id
    directory.mkdir(parents=True, exist_ok=False)
    audio_path = directory / f"input{audio_extension(payload.mime_type)}"
    transcript_path = directory / "transcript.txt"
    reply_path = directory / "reply.txt"
    metadata_path = directory / "metadata.json"
    audio_path.write_bytes(audio)
    transcript = ""
    reply = ""
    error = ""
    status = "saved"
    try:
        transcript = transcribe_audio(audio_path)
        status = "transcribed"
        chat = call_hermes_runtime(transcript, session_id=payload.session_id, timeout_seconds=120)
        reply = str(chat.get("reply") or "")
        status = "done" if chat.get("status") == "success" else "hermes_error"
        error = str(chat.get("error") or "")
        session_id = chat.get("session_id") or payload.session_id
    except Exception as exc:  # noqa: BLE001
        error = str(exc)
        session_id = payload.session_id
        status = "needs_processing"
    write_text(transcript_path, transcript)
    write_text(reply_path, reply)
    audio_url = None
    if payload.tts and reply:
        tts_path = directory / "reply.mp3"
        if synthesize_edge_tts(reply, tts_path):
            audio_url = f"/v1/voice/audio/{voice_id}"
    metadata = {
        "schema": HERMES_CHAT_SCHEMA,
        "voice_id": voice_id,
        "created_at": now_iso(),
        "status": status,
        "asr_engine": "funasr-local",
        "tts_engine": "edge-tts" if audio_url else "none",
        "tts_voice": EDGE_TTS_VOICE,
        "audio_path": str(audio_path),
        "error": error,
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "ok": status == "done",
        "schema": HERMES_CHAT_SCHEMA,
        "voice_id": voice_id,
        "session_id": session_id,
        "transcript": transcript,
        "reply_text": reply,
        "audio_url": audio_url,
        "status": status,
        "error": error,
    }


@router.get("/v1/voice/message/{voice_id}")
def get_voice_message(request: Request, voice_id: str) -> dict[str, Any]:
    require_mobile_access(request)
    directory = voice_inbox_dir() / voice_id
    metadata_path = directory / "metadata.json"
    if not metadata_path.exists():
        raise HTTPException(status_code=404, detail="voice message not found")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    transcript_path = directory / "transcript.txt"
    reply_path = directory / "reply.txt"
    audio_url = f"/v1/voice/audio/{voice_id}" if (directory / "reply.mp3").exists() else None
    return {
        "ok": True,
        "schema": HERMES_CHAT_SCHEMA,
        "voice_id": voice_id,
        "metadata": metadata,
        "transcript": transcript_path.read_text(encoding="utf-8") if transcript_path.exists() else "",
        "reply_text": reply_path.read_text(encoding="utf-8") if reply_path.exists() else "",
        "audio_url": audio_url,
    }


@router.get("/v1/voice/audio/{voice_id}")
def get_voice_audio(request: Request, voice_id: str) -> Response:
    require_mobile_access(request)
    path = voice_inbox_dir() / voice_id / "reply.mp3"
    if not path.exists():
        raise HTTPException(status_code=404, detail="voice reply audio missing")
    return Response(content=path.read_bytes(), media_type="audio/mpeg")


def escape(value: Any) -> str:
    return html.escape(str(value or ""))
