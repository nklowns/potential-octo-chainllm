from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from src.quality.manifest import RunManifest, ScriptEntry, AudioEntry


def test_manifest_thread_safety(tmp_path):
    """Stress concurrent writes to manifest using ThreadPoolExecutor."""
    manifest_path = tmp_path / 'quality_gates' / 'run_manifest.json'
    manifest_path.parent.mkdir(parents=True)
    m = RunManifest(manifest_path)

    def add_script(i):
        entry = ScriptEntry(
            topic=f"t{i}", script_id=f"s{i:03d}", path=f"/tmp/s{i:03d}.txt", quality_status="pass", ready_for_audio=True
        )
        m.add_script(entry)

    def add_audio(i):
        entry = AudioEntry(
            script_id=f"s{i:03d}", audio_id=f"a{i:03d}", path=f"/tmp/a{i:03d}.wav", quality_status="pass", duration=1.23
        )
        m.add_audio(entry)

    N = 50
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = []
        for i in range(N):
            futs.append(ex.submit(add_script, i))
            futs.append(ex.submit(add_audio, i))
        for f in as_completed(futs):
            f.result()

    # Reload
    m2 = RunManifest(manifest_path)
    data = m2.to_dict()
    assert len(data['scripts']) == N
    assert len(data['audio']) == N
    # Ensure unique ids persisted
    assert len({s['script_id'] for s in data['scripts']}) == N
    assert len({a['audio_id'] for a in data['audio']}) == N
