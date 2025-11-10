"""Hash index to detect duplicate artifacts (e.g., scripts)."""

import hashlib
import json
import logging
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
import threading
import fcntl
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class HashIndex:
    """Persistent index mapping content hash -> list of artifact IDs."""

    def __init__(self, index_path: Path):
        self.index_path = index_path
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self._data: Dict[str, List[str]] = self._load()
        self._lock = threading.Lock()

    @property
    def _lockfile_path(self) -> Path:
        return Path(str(self.index_path) + ".lock")

    @contextmanager
    def _file_lock(self):
        self._lockfile_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._lockfile_path, 'w') as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lf, fcntl.LOCK_UN)

    def _load(self) -> Dict[str, List[str]]:
        if self.index_path.exists():
            try:
                with open(self.index_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load hash index {self.index_path}: {e}")
        return {}

    @staticmethod
    def compute_hash(content: str) -> str:
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def find(self, content_hash: str) -> List[str]:
        with self._lock, self._file_lock():
            # reload to ensure latest across processes
            self._data = self._load()
            return list(self._data.get(content_hash, []))

    def add(self, content_hash: str, artifact_id: str):
        with self._lock, self._file_lock():
            latest = self._load()
            self._data = latest
            ids = self._data.setdefault(content_hash, [])
            if artifact_id not in ids:
                ids.append(artifact_id)
                self._save()

    def _save(self):
        try:
            with tempfile.NamedTemporaryFile(
                mode='w', encoding='utf-8', dir=self.index_path.parent, delete=False, suffix='.tmp'
            ) as tf:
                json.dump(self._data, tf, indent=2, ensure_ascii=False)
                tmp = tf.name
            Path(tmp).replace(self.index_path)
        except Exception as e:
            logger.error(f"Failed to save hash index: {e}")
