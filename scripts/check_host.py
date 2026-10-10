"""Read-only host checks. The board's toolchain is separate from the Mac's."""
import json
from pathlib import Path
import platform
import shutil
import sys

root = Path(__file__).resolve().parents[1]
report = {
    "python": platform.python_version(),
    "platform": platform.platform(),
    "venv": sys.prefix != sys.base_prefix,
    "tools": {tool: shutil.which(tool) for tool in ("git", "ssh", "arduino-cli", "uv")},
    "app_manifest": (root / "apps/crosssense-env/app.yaml").is_file(),
}
print(json.dumps(report, indent=2))
if sys.version_info < (3, 11) or not report["app_manifest"]:
    raise SystemExit(1)
