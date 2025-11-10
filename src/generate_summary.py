#!/usr/bin/env python3
"""Generate summary report from quality gate results."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.quality.reporters import SummaryReporter
from src.pipeline import config as pipeline_config


def main():
    """Generate summary report."""
    reports_dir = pipeline_config.OUTPUT_DIR / "reports"
    summary_path = reports_dir / "summary.json"
    
    script_reports_dir = reports_dir / "scripts"
    audio_reports_dir = reports_dir / "audio"
    
    # Collect report files
    script_reports = list(script_reports_dir.glob("*.json")) if script_reports_dir.exists() else []
    audio_reports = list(audio_reports_dir.glob("*.json")) if audio_reports_dir.exists() else []
    
    if not script_reports and not audio_reports:
        print("⚠️  No quality reports found.")
        print(f"   Script reports: {script_reports_dir}")
        print(f"   Audio reports: {audio_reports_dir}")
        return
    
    # Generate summary
    reporter = SummaryReporter(summary_path)
    reporter.generate_summary(script_reports, audio_reports)
    
    print(f"✅ Summary report generated: {summary_path}")
    print(f"   Script reports: {len(script_reports)}")
    print(f"   Audio reports: {len(audio_reports)}")


if __name__ == "__main__":
    main()
