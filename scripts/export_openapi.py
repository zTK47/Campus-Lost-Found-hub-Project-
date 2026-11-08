import json
import sys
from pathlib import Path

repository_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repository_root))

from app.main import app  # noqa: E402

output_path = repository_root / "docs" / "openapi.json"
output_path.write_text(
    json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
