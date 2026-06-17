"""Make the package importable during tests without an editable install."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
