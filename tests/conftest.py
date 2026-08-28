import sys, os
from pathlib import Path
# tests import the pipeline modules from src/; they use only toy data
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
