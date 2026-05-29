from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent
PIECE_ROOT = ROOT / "assets" / "sprites" / "pieces"
ANIMATION_ROOT = ROOT / "assets" / "sprites" / "animations"
MATCH_ROOT = ROOT / "assets" / "matches"
SAVE_ROOT = ROOT / "saved_matches"
ENGINE_ROOT = ROOT / "engines"

BOARD_SIZE = 560
SQUARE_SIZE = BOARD_SIZE // 8
WINDOW_SIZE = "900x640"
