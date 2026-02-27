from __future__ import annotations

import json
import os
from pathlib import Path


class UserRepo:
    def __init__(self, data_dir: str):
        self.base = Path(data_dir)
        self.base.mkdir(parents=True, exist_ok=True)
        self.file = self.base / "users.json"
        if not self.file.exists():
            self.file.write_text("{}", encoding="utf-8")

    def _load(self) -> dict:
        return json.loads(self.file.read_text(encoding="utf-8"))

    def _save(self, data: dict) -> None:
        tmp = self.file.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self.file)

    def set_subscription(self, user_id: int, url: str) -> None:
        data = self._load()
        data[str(user_id)] = {"subscription_url": url}
        self._save(data)

    def get_subscription(self, user_id: int) -> str | None:
        data = self._load()
        rec = data.get(str(user_id), {})
        return rec.get("subscription_url")
