import os
import json
import contextvars
from pathlib import Path
from typing import Optional, List, Any
from dotenv import load_dotenv

load_dotenv()

WORKSPACE_DIR = Path(os.getenv("SCHAGENT_WORKSPACE", str(Path(__file__).parent / "workspace")))
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

BACKEND_API_BASE = os.getenv("SCHAGENT_BACKEND_URL")

DAY_NAMES = ["", "周一", "周二", "周三", "周四", "周五", "周六", "周日"]

_current_user_id: contextvars.ContextVar[str] = contextvars.ContextVar('current_user_id', default='')
_current_username: contextvars.ContextVar[str] = contextvars.ContextVar('current_username', default='')


class UserMemoryStore:
    def __init__(self, storage_dir: Path):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, username: str) -> Path:
        safe_name = "".join(c for c in username if c.isalnum() or c in "_-")
        return self.storage_dir / f"{safe_name}.json"

    def get_all(self, username: str) -> dict:
        path = self._get_path(username)
        if not path.exists():
            return {}
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get(self, username: str, key: str) -> Optional[Any]:
        return self.get_all(username).get(key)

    def set(self, username: str, key: str, value: Any) -> None:
        path = self._get_path(username)
        data = self.get_all(username)
        data[key] = value
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def delete(self, username: str, key: Optional[str] = None) -> None:
        path = self._get_path(username)
        if key is None:
            path.unlink(missing_ok=True)
        elif path.exists():
            data = self.get_all(username)
            data.pop(key, None)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    def list_keys(self, username: str) -> List[str]:
        return list(self.get_all(username).keys())


memory_store = UserMemoryStore(WORKSPACE_DIR / "user_data")


def _get_user_workspace() -> Path:
    uid = _current_user_id.get()
    if uid:
        user_dir = WORKSPACE_DIR / uid
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir
    return WORKSPACE_DIR


def _resolve_user_path(file_name: str) -> Path:
    base = _get_user_workspace()
    resolved = (base / file_name).resolve()
    if not str(resolved).startswith(str(WORKSPACE_DIR.resolve())):
        raise ValueError(f"非法文件路径：{file_name}")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def _format_size(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
