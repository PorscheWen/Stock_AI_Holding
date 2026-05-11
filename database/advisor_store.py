"""
使用者 Agent 建議報告持久化（JSON，與 portfolios 相同目錄）。
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

DB_DIR = Path("database/data")
STORE_FILE = DB_DIR / "advisor_reports.json"
MAX_REPORTS_PER_USER = 40


def _ensure() -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    if not STORE_FILE.exists():
        STORE_FILE.write_text("{}", encoding="utf-8")


def _load() -> dict[str, Any]:
    _ensure()
    try:
        return json.loads(STORE_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error("advisor_store 讀取失敗: %s", e)
        return {}


def _save(data: dict[str, Any]) -> None:
    _ensure()
    STORE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def append_report(user_id: str, report: dict[str, Any]) -> dict[str, Any]:
    """
    寫入一筆新報告（含 id），置於該使用者列表最前。
    report 應已含 stocks、summary、generated_at 等欄位。
    """
    data = _load()
    uid = str(user_id)
    entry = dict(report)
    entry["id"] = str(uuid.uuid4())
    if not entry.get("generated_at"):
        entry["generated_at"] = datetime.now().isoformat(timespec="seconds")
    bucket = data.setdefault(uid, {"reports": []})
    reports: list = bucket.setdefault("reports", [])
    reports.insert(0, entry)
    del reports[MAX_REPORTS_PER_USER:]
    _save(data)
    return entry


def get_latest(user_id: str) -> Optional[dict[str, Any]]:
    data = _load()
    uid = str(user_id)
    reps = (data.get(uid) or {}).get("reports") or []
    return reps[0] if reps else None


def get_history(user_id: str, limit: int = 10) -> list[dict[str, Any]]:
    data = _load()
    uid = str(user_id)
    reps = (data.get(uid) or {}).get("reports") or []
    return reps[: max(1, min(limit, 50))]
