import sys
from pathlib import Path

# The package modules use flat imports (e.g. `from data_config import ...`),
# so the package directory itself needs to be importable.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "table_plan"))
