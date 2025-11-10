#!/usr/bin/env python3
"""List failed artifacts from quality gate checks."""

import json
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.quality.manifest import RunManifest
from src.pipeline import config as pipeline_config
from src.utils.json_logger import configure_json_logging


def list_failures():
    """List all failed artifacts from the manifest."""
    configure_json_logging()
    manifest_path = pipeline_config.OUTPUT_DIR / "quality_gates" / "run_manifest.json"

    if not manifest_path.exists():
        print(f"❌ No manifest found at {manifest_path}")
        print("   Run the pipeline first to generate artifacts.")
        return

    manifest = RunManifest(manifest_path)

    failed_scripts = manifest.get_failed_scripts()
    failed_audio = manifest.get_failed_audio()

    print("=" * 60)
    print("QUALITY GATE FAILURES REPORT")
    print("=" * 60)
    print()

    # Failed scripts
    print(f"📝 FAILED SCRIPTS: {len(failed_scripts)}")
    print("-" * 60)
    if failed_scripts:
        for script in failed_scripts:
            print(f"  • {script['script_id']}")
            print(f"    Topic: {script.get('topic', 'Unknown')}")
            print(f"    Status: {script['quality_status']}")
            print(f"    Path: {script['path']}")
            details = script.get('quality_details', {})
            if details.get('error'):
                print(f"    Error: {details['error']}")
            print()
    else:
        print("  ✅ No failed scripts")
    print()

    # Failed audio
    print(f"🔊 FAILED AUDIO: {len(failed_audio)}")
    print("-" * 60)
    if failed_audio:
        for audio in failed_audio:
            print(f"  • {audio['audio_id']}")
            print(f"    Script ID: {audio.get('script_id', 'Unknown')}")
            print(f"    Status: {audio['quality_status']}")
            print(f"    Path: {audio['path']}")
            details = audio.get('quality_details', {})
            if details.get('error'):
                print(f"    Error: {details['error']}")
            print()
    else:
        print("  ✅ No failed audio")
    print()

    # Summary
    total_failures = len(failed_scripts) + len(failed_audio)
    print("=" * 60)
    print(f"TOTAL FAILURES: {total_failures}")
    print("=" * 60)

    # Show report locations
    if total_failures > 0:
        print()
        print("📊 Detailed reports available at:")
        print(f"  Scripts: {pipeline_config.OUTPUT_DIR / 'quality_gates' / 'reports' / 'scripts'}")
        print(f"  Audio:   {pipeline_config.OUTPUT_DIR / 'quality_gates' / 'reports' / 'audio'}")
        print()
        print("🚫 Quarantined artifacts at:")
        print(f"  Scripts: {pipeline_config.OUTPUT_DIR / 'quality_gates' / 'quarantine' / 'scripts'}")
        print(f"  Audio:   {pipeline_config.OUTPUT_DIR / 'quality_gates' / 'quarantine' / 'audio'}")


if __name__ == "__main__":
    list_failures()
