"""Fail the CI build if Radon reports any C-or-worse complexity blocks."""
import json
import sys
from pathlib import Path

path = Path(sys.argv[1] if len(sys.argv) > 1 else "reports/radon.json")
data = json.loads(path.read_text(encoding="utf-8"))
violations = []
for filename, blocks in data.items():
    for block in blocks:
        if block.get("rank") in {"C", "D", "E", "F"}:
            violations.append(
                f"{filename}:{block.get('lineno')} {block.get('name')} complexity={block.get('complexity')} rank={block.get('rank')}"
            )
if violations:
    print("Complexity quality gate failed:")
    print("\n".join(violations))
    sys.exit(1)
print("Complexity quality gate passed: no C-or-worse blocks.")
