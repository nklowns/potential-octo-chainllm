"""Structured JSON logging setup with correlation IDs."""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base: Dict[str, Any] = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Optional extras
        for attr in ("run_id", "artifact_id", "artifact_type", "gate", "duration_ms"):
            if hasattr(record, attr):
                base[attr] = getattr(record, attr)
        return json.dumps(base, ensure_ascii=False)


_configured = False


def configure_json_logging():
    global _configured
    if _configured:
        return
    root = logging.getLogger()
    root.setLevel(os.getenv("LOG_LEVEL", "INFO"))
    # Remove existing handlers (avoid duplicates)
    for h in list(root.handlers):
        root.removeHandler(h)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    root.addHandler(handler)
    _configured = True
