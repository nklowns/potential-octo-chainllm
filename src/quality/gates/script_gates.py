"""Script quality gates."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from ..base import QualityGate, QualityStatus, Severity, GateResult

logger = logging.getLogger(__name__)


class SchemaValidationGate(QualityGate):
    """Validates script structure against JSON schema."""
    
    def __init__(self, schema_path: Path, severity: Severity = Severity.ERROR):
        super().__init__("schema_validation", severity)
        self.schema_path = schema_path
        self._schema = None
        self._validator = None
    
    def _load_schema(self):
        """Load and compile JSON schema."""
        if self._schema is None:
            try:
                import jsonschema
                with open(self.schema_path, 'r', encoding='utf-8') as f:
                    self._schema = json.load(f)
                # Use Draft7Validator for format validation
                self._validator = jsonschema.Draft7Validator(self._schema)
            except ImportError:
                logger.error("jsonschema library not installed. Install with: pip install jsonschema")
                raise
            except Exception as e:
                logger.error(f"Error loading schema from {self.schema_path}: {e}")
                raise
    
    def check(self, artifact: Dict[str, Any]) -> GateResult:
        """Check if script matches the schema."""
        self._load_schema()
        
        errors = list(self._validator.iter_errors(artifact))
        
        if not errors:
            return self._create_result(
                QualityStatus.PASS,
                "Script structure is valid",
                {"schema_version": self._schema.get("title", "script_v1")}
            )
        
        # Collect error messages
        error_messages = [f"{e.json_path}: {e.message}" for e in errors]
        
        return self._create_result(
            QualityStatus.FAIL,
            f"Schema validation failed with {len(errors)} error(s)",
            {
                "errors": error_messages,
                "schema_path": str(self.schema_path)
            }
        )


class WordBoundsGate(QualityGate):
    """Validates script word count is within bounds."""
    
    def __init__(self, min_words: int, max_words: int, severity: Severity = Severity.ERROR):
        super().__init__("word_bounds", severity)
        self.min_words = min_words
        self.max_words = max_words
    
    def check(self, artifact: Dict[str, Any]) -> GateResult:
        """Check if word count is within bounds."""
        content = artifact.get('content', '')
        word_count = len(content.split())
        
        # Also check metadata word_count if available
        meta_word_count = artifact.get('metadata', {}).get('word_count')
        
        if word_count < self.min_words:
            return self._create_result(
                QualityStatus.FAIL,
                f"Script too short: {word_count} words (minimum: {self.min_words})",
                {
                    "word_count": word_count,
                    "min_words": self.min_words,
                    "max_words": self.max_words
                }
            )
        
        if word_count > self.max_words:
            return self._create_result(
                QualityStatus.FAIL,
                f"Script too long: {word_count} words (maximum: {self.max_words})",
                {
                    "word_count": word_count,
                    "min_words": self.min_words,
                    "max_words": self.max_words
                }
            )
        
        return self._create_result(
            QualityStatus.PASS,
            f"Word count OK: {word_count} words",
            {
                "word_count": word_count,
                "min_words": self.min_words,
                "max_words": self.max_words,
                "metadata_word_count": meta_word_count
            }
        )


class ForbiddenTermsGate(QualityGate):
    """Checks for forbidden terms in script content."""
    
    def __init__(self, forbidden_terms: List[str], severity: Severity = Severity.ERROR):
        super().__init__("forbidden_terms", severity)
        self.forbidden_terms = [term.lower() for term in forbidden_terms]
    
    def check(self, artifact: Dict[str, Any]) -> GateResult:
        """Check if script contains forbidden terms."""
        content = artifact.get('content', '').lower()
        
        found_terms = [term for term in self.forbidden_terms if term in content]
        
        if found_terms:
            return self._create_result(
                QualityStatus.FAIL,
                f"Found {len(found_terms)} forbidden term(s)",
                {
                    "found_terms": found_terms,
                    "forbidden_terms_count": len(self.forbidden_terms)
                }
            )
        
        return self._create_result(
            QualityStatus.PASS,
            "No forbidden terms found",
            {"checked_terms_count": len(self.forbidden_terms)}
        )


class LanguageGate(QualityGate):
    """Validates script language (basic check)."""
    
    def __init__(self, expected_language: str = "pt-BR", severity: Severity = Severity.WARN):
        super().__init__("language", severity)
        self.expected_language = expected_language
    
    def check(self, artifact: Dict[str, Any]) -> GateResult:
        """
        Check if script appears to be in expected language.
        Basic implementation - checks for common Portuguese characters and words.
        """
        content = artifact.get('content', '')
        
        # Simple heuristic: check for common Portuguese words
        pt_common_words = [
            'o', 'a', 'de', 'que', 'e', 'do', 'da', 'em', 'um', 'para',
            'é', 'com', 'não', 'uma', 'os', 'no', 'se', 'na', 'por', 'mais',
            'como', 'mas', 'foi', 'ao', 'ele', 'das', 'à', 'seu', 'sua', 'ou'
        ]
        
        content_lower = content.lower()
        words = content_lower.split()
        
        if not words:
            return self._create_result(
                QualityStatus.WARN,
                "Script is empty, cannot verify language",
                {"expected_language": self.expected_language}
            )
        
        # Count how many common Portuguese words appear
        pt_word_count = sum(1 for word in words if word in pt_common_words)
        pt_ratio = pt_word_count / len(words) if words else 0
        
        # Also check for Portuguese-specific characters
        has_pt_chars = any(c in content for c in 'áàâãéêíóôõúçÁÀÂÃÉÊÍÓÔÕÚÇ')
        
        # If less than 10% are common PT words and no PT chars, warn
        if pt_ratio < 0.10 and not has_pt_chars:
            return self._create_result(
                QualityStatus.WARN,
                f"Script may not be in {self.expected_language}",
                {
                    "expected_language": self.expected_language,
                    "pt_word_ratio": round(pt_ratio, 3),
                    "has_pt_chars": has_pt_chars,
                    "total_words": len(words)
                }
            )
        
        return self._create_result(
            QualityStatus.PASS,
            f"Script appears to be in {self.expected_language}",
            {
                "expected_language": self.expected_language,
                "pt_word_ratio": round(pt_ratio, 3),
                "has_pt_chars": has_pt_chars,
                "total_words": len(words)
            }
        )
