import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
HEADPHONES_PATH = DATA_DIR / "headphones_databasev2.json"

def load_headphones():
    with open(HEADPHONES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

ALL_HEADPHONES = load_headphones()
