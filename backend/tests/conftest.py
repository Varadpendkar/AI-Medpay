import os, sys
# Ensure project root (one level up from tests) is on sys.path for imports like `from app import app`
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
