import sys
from pathlib import Path

# Ensure the project root is on sys.path so tests can import utils.py
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
    