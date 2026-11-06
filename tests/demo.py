"""Reproduce the synthetic technical evidence; never produces publishable content."""
import json
from pathlib import Path
from tests.test_engine import fixture
from nuvem.engine import produce, save

root = Path('work/demo-media').resolve()
root.mkdir(parents=True, exist_ok=True)
manifest = fixture(root)
save(root/'manifest.json', manifest)
report = produce(root, manifest, Path('output/demo').resolve(), Path('work/demo-state.sqlite').resolve(), limit=1)
print(json.dumps(report, ensure_ascii=False, indent=2))
if report['produced'] != 1:
    raise SystemExit('Demo failed or already produced; remove work/demo-state.sqlite to reproduce')
