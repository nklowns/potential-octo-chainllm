"""Manifest management for pipeline execution tracking."""

import json
import logging
import hashlib
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class ScriptEntry:
    """Entry for a script in the manifest."""
    topic: str
    script_id: str
    path: str
    quality_status: str = "pending"  # pending, pass, fail, warn
    ready_for_audio: bool = False
    word_count: Optional[int] = None
    timestamp: Optional[str] = None
    quality_details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AudioEntry:
    """Entry for audio in the manifest."""
    script_id: str
    audio_id: str
    path: str
    quality_status: str = "pending"
    duration: Optional[float] = None
    timestamp: Optional[str] = None
    quality_details: Dict[str, Any] = field(default_factory=dict)


class RunManifest:
    """Manages the execution manifest for tracking pipeline state."""
    
    def __init__(self, manifest_path: Path):
        """
        Initialize manifest manager.
        
        Args:
            manifest_path: Path to the manifest JSON file.
        """
        self.manifest_path = manifest_path
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load_or_create()
    
    def _load_or_create(self) -> Dict[str, Any]:
        """Load existing manifest or create new one."""
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.info(f"Loaded existing manifest from {self.manifest_path}")
                return data
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load manifest, creating new: {e}")
        
        # Create new manifest
        data = {
            "run_id": self._generate_run_id(),
            "config_hash": "",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "scripts": [],
            "audio": []
        }
        logger.info(f"Created new manifest with run_id: {data['run_id']}")
        return data
    
    def _generate_run_id(self) -> str:
        """Generate a unique run ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return f"run_{timestamp}"
    
    def set_config_hash(self, config_hash: str):
        """Set the configuration hash for this run."""
        self._data["config_hash"] = config_hash
        self._save()
    
    def add_script(self, entry: ScriptEntry):
        """Add a script entry to the manifest."""
        # Check if script already exists
        for i, s in enumerate(self._data["scripts"]):
            if s["script_id"] == entry.script_id:
                # Update existing entry
                self._data["scripts"][i] = asdict(entry)
                self._save()
                return
        
        # Add new entry
        self._data["scripts"].append(asdict(entry))
        self._save()
    
    def add_audio(self, entry: AudioEntry):
        """Add an audio entry to the manifest."""
        # Check if audio already exists
        for i, a in enumerate(self._data["audio"]):
            if a["audio_id"] == entry.audio_id:
                # Update existing entry
                self._data["audio"][i] = asdict(entry)
                self._save()
                return
        
        # Add new entry
        self._data["audio"].append(asdict(entry))
        self._save()
    
    def get_scripts_ready_for_audio(self) -> List[Dict[str, Any]]:
        """Get all scripts that are ready for audio generation."""
        return [s for s in self._data["scripts"] if s.get("ready_for_audio", False)]
    
    def get_script(self, script_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific script entry."""
        for s in self._data["scripts"]:
            if s["script_id"] == script_id:
                return s
        return None
    
    def get_audio(self, audio_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific audio entry."""
        for a in self._data["audio"]:
            if a["audio_id"] == audio_id:
                return a
        return None
    
    def get_failed_scripts(self) -> List[Dict[str, Any]]:
        """Get all scripts that failed quality checks."""
        return [s for s in self._data["scripts"] if s.get("quality_status") == "fail"]
    
    def get_failed_audio(self) -> List[Dict[str, Any]]:
        """Get all audio that failed quality checks."""
        return [a for a in self._data["audio"] if a.get("quality_status") == "fail"]
    
    def _save(self):
        """Save manifest to file atomically."""
        self._data["updated_at"] = datetime.utcnow().isoformat() + "Z"
        
        # Atomic write using temp file + rename
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                encoding='utf-8',
                dir=self.manifest_path.parent,
                delete=False,
                suffix='.tmp'
            ) as tf:
                json.dump(self._data, tf, indent=2, ensure_ascii=False)
                temp_path = tf.name
            
            # Rename is atomic on POSIX systems
            Path(temp_path).replace(self.manifest_path)
            logger.debug(f"Manifest saved to {self.manifest_path}")
            
        except Exception as e:
            logger.error(f"Failed to save manifest: {e}")
            # Clean up temp file if it exists
            try:
                Path(temp_path).unlink(missing_ok=True)
            except:
                pass
            raise
    
    def to_dict(self) -> Dict[str, Any]:
        """Return manifest data as dictionary."""
        return self._data.copy()


def compute_config_hash(config_dict: Dict[str, Any]) -> str:
    """
    Compute SHA256 hash of configuration for reproducibility tracking.
    
    Args:
        config_dict: Configuration dictionary to hash.
        
    Returns:
        Hex string of SHA256 hash.
    """
    config_str = json.dumps(config_dict, sort_keys=True)
    return hashlib.sha256(config_str.encode('utf-8')).hexdigest()[:16]
