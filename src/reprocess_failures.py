#!/usr/bin/env python3
"""Reprocess only failed artifacts from the manifest.

Usage:
  python -m src.reprocess_failures [--scripts] [--audio]
If no flags provided, reprocess both scripts and audio failures.
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline import config as pipeline_config
from src.quality.manifest import RunManifest
from src.check_script_quality import ScriptQualityChecker
from src.check_audio_quality import AudioQualityChecker

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Reprocess failed artifacts from manifest")
    parser.add_argument('--scripts', action='store_true', help='Reprocess failed scripts only')
    parser.add_argument('--audio', action='store_true', help='Reprocess failed audio only')
    parser.add_argument('--strict', action='store_true', help='Exit non-zero if any reprocessed item still fails')
    args = parser.parse_args()

    manifest_path = pipeline_config.OUTPUT_DIR / 'quality_gates' / 'run_manifest.json'
    if not manifest_path.exists():
        logger.error(f"Manifest not found at {manifest_path}. Nothing to reprocess.")
        sys.exit(1)

    manifest = RunManifest(manifest_path)

    do_scripts = args.scripts or not (args.scripts or args.audio)
    do_audio = args.audio or not (args.scripts or args.audio)

    total_failed_after = 0

    if do_scripts:
        failed_scripts = manifest.get_failed_scripts()
        if failed_scripts:
            logger.info(f"Reprocessing {len(failed_scripts)} failed scripts...")
            checker = ScriptQualityChecker()
            # build list of file paths and run sequentially for determinism
            files = [Path(s['path']) for s in failed_scripts if s.get('path')]
            for f in files:
                if not f.exists():
                    logger.warning(f"Script file missing, skipping: {f}")
                    continue
                res = checker.check_artifact(f)
                if not res.get('passed', False):
                    total_failed_after += 1
        else:
            logger.info("No failed scripts to reprocess.")

    if do_audio:
        failed_audio = manifest.get_failed_audio()
        if failed_audio:
            logger.info(f"Reprocessing {len(failed_audio)} failed audio files...")
            checker = AudioQualityChecker()
            files = [Path(a['path']) for a in failed_audio if a.get('path')]
            for f in files:
                if not f.exists():
                    logger.warning(f"Audio file missing, skipping: {f}")
                    continue
                res = checker.check_artifact(f)
                if not res.get('passed', False):
                    total_failed_after += 1
        else:
            logger.info("No failed audio to reprocess.")

    if args.strict and total_failed_after > 0:
        logger.error(f"STRICT: {total_failed_after} artifacts still failing after reprocess.")
        sys.exit(1)

    logger.info("Reprocess completed.")


if __name__ == '__main__':
    main()
