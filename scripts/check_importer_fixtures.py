import json
from pathlib import Path
from urllib.request import urlopen

root = Path(__file__).resolve().parents[1]
source = json.loads((root / "tests/fixtures/importer-fidelity-source.json").read_text())
local_fixture = json.loads((root / "tests/fixtures/importer-fidelity.json").read_text())
raw = f"https://raw.githubusercontent.com/markup-carve/carve/{source['coreCommit']}/"
with urlopen(raw + "tests/importer-fidelity/manifest.json", timeout=15) as response:
    manifest = json.load(response)
if manifest.get("schemaVersion") != 2:
    raise SystemExit("pinned core importer manifest is not schema version 2")
owned = [item for item in manifest["cases"] if item.get("repository") == source["repository"]]
if not owned:
    raise SystemExit("pinned core importer manifest has no PDF-owned cases")
if owned != [local_fixture]:
    raise SystemExit("PDF importer fixture differs from its pinned core manifest subset")
with urlopen(raw + "resources/migration-report-schema.json", timeout=15) as response:
    upstream_schema = json.load(response)
local_schema = json.loads((root / "tests/fixtures/migration-report-schema.json").read_text())
if upstream_schema != local_schema:
    raise SystemExit("migration report schema differs from the pinned core copy")
