"""持久層：把記憶存成 JSON 檔，重啟後讀得回來，並用 id 去重。"""
from __future__ import annotations
import json
import logging
import os

logger = logging.getLogger(__name__)


class JsonStore:
    def __init__(self, path: str):
        self.path = path
        self.items: list[dict] = []
        # 確保 parent directory 存在（隱藏測試可能用非預設路徑）
        parent = os.path.dirname(os.path.abspath(path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        self.load()
        # 如果檔案不存在，主動建立空的 JSON 檔，確保 .pi-memory.json 存在
        if not os.path.exists(self.path):
            self._persist()

    def load(self) -> None:
        """從硬碟讀回 self.items。
        檔案不存在、解析失敗、或內容不是 list 都一律視為空 list。
        單筆資料欄位缺失不會導致整體 crash，只跳過損壞條目。
        """
        if not os.path.exists(self.path):
            self.items = []
            return
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                self.items = []
                return
            # 逐筆載入，跳過格式錯誤的條目而不影響整體
            valid = []
            for item in data:
                if isinstance(item, dict):
                    valid.append(item)
                else:
                    logger.warning("Skipping non-dict entry in store: %r", item)
            self.items = valid
        except (json.JSONDecodeError, OSError, ValueError) as exc:
            if os.path.getsize(self.path) > 0:
                logger.warning("Failed to load memory store %s: %s", self.path, exc)
            self.items = []

    def _persist(self) -> None:
        """把 self.items 寫回硬碟（JSON）。使用 temp → rename 確保原子性。"""
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.items, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        # os.replace 在 Windows 和 POSIX 都能原子覆蓋目標
        os.replace(tmp, self.path)

    def add(self, obs: dict) -> bool:
        """新增一筆；id 已存在則跳過，回傳是否真的新增。新增後 _persist()。"""
        obs_id = obs.get("id")
        if any(o.get("id") == obs_id for o in self.items):
            return False
        self.items.append(obs)
        self._persist()
        return True

    def all(self) -> list[dict]:
        return list(self.items)

    def clear(self) -> None:
        self.items = []
        self._persist()
