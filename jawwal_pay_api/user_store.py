from __future__ import annotations

import json
import secrets
import uuid
from datetime import datetime
from pathlib import Path


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


class UserStore:
    """Registry of API users; each user gets isolated Jawwal session/data files."""

    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)
        self.users_dir = self.data_dir / "users"
        self.registry_path = self.users_dir / "registry.json"
        self.users_dir.mkdir(parents=True, exist_ok=True)

    def _read_registry(self) -> dict:
        if not self.registry_path.exists():
            return {"users": {}}
        try:
            data = json.loads(self.registry_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"users": {}}
        return data if isinstance(data, dict) else {"users": {}}

    def _write_registry(self, data: dict) -> None:
        self.registry_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _user_dir(self, user_id: str) -> Path:
        path = self.users_dir / user_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def create_user(self, name: str, user_id: str | None = None) -> dict:
        registry = self._read_registry()
        users = registry.setdefault("users", {})
        user_id = (user_id or f"user_{uuid.uuid4().hex[:8]}").strip()
        if user_id in users:
            raise ValueError(f"user_id already exists: {user_id}")

        api_key = secrets.token_urlsafe(32)
        record = {
            "user_id": user_id,
            "name": name.strip() or user_id,
            "api_key": api_key,
            "created_at": _now_iso(),
        }
        users[user_id] = record
        self._write_registry(registry)
        self._user_dir(user_id)
        return record

    def resolve_api_key(self, api_key: str) -> dict | None:
        if not api_key:
            return None
        users = self._read_registry().get("users", {})
        for record in users.values():
            if record.get("api_key") == api_key:
                return record
        return None

    def list_users(self) -> list[dict]:
        users = self._read_registry().get("users", {})
        return [
            {
                "user_id": record["user_id"],
                "name": record.get("name"),
                "created_at": record.get("created_at"),
                "has_session": self.session_path(record["user_id"]).exists(),
            }
            for record in users.values()
        ]

    def get_user(self, user_id: str) -> dict | None:
        return self._read_registry().get("users", {}).get(user_id)

    def session_path(self, user_id: str) -> Path:
        return self._user_dir(user_id) / "jawwal_session.json"

    def pending_path(self, user_id: str) -> Path:
        return self._user_dir(user_id) / "pending_payments.json"

    def history_path(self, user_id: str) -> Path:
        return self._user_dir(user_id) / "payments_history.json"
