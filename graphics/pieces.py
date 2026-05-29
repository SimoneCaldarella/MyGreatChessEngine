from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import chess
from PIL import Image, ImageTk

from config import PIECE_ROOT


PIECE_TYPES = {
    chess.PAWN: "pawn",
    chess.KNIGHT: "knight",
    chess.BISHOP: "bishop",
    chess.ROOK: "rook",
    chess.QUEEN: "queen",
    chess.KING: "king",
}


@dataclass(frozen=True)
class PieceSet:
    name: str
    folder: Path
    files: dict[tuple[bool, int], Path]

    @property
    def display_name(self) -> str:
        return self.name.title()


class PieceSetLibrary:
    def __init__(self, root: Path = PIECE_ROOT):
        self.root = root

    def discover(self) -> list[PieceSet]:
        if not self.root.exists():
            return []

        piece_sets = []
        for folder in sorted(path for path in self.root.iterdir() if path.is_dir()):
            files = self._discover_files(folder)
            if len(files) == 12:
                piece_sets.append(PieceSet(folder.name, folder, files))
        return piece_sets

    def _discover_files(self, folder: Path) -> dict[tuple[bool, int], Path]:
        files: dict[tuple[bool, int], Path] = {}
        pngs = sorted(folder.glob("*.png"))
        for color, prefix in ((chess.WHITE, "w-"), (chess.BLACK, "b-")):
            for piece_type, label in PIECE_TYPES.items():
                match = self._first_matching_sprite(pngs, prefix, label)
                if match:
                    files[(color, piece_type)] = match
        return files

    @staticmethod
    def _first_matching_sprite(pngs: list[Path], prefix: str, label: str) -> Path | None:
        for path in pngs:
            if path.name.startswith(prefix) and label in path.stem.lower():
                return path
        return None


class SpriteCache:
    def __init__(self, piece_set: PieceSet):
        self.piece_set = piece_set
        self._cache: dict[tuple[bool, int, int], ImageTk.PhotoImage] = {}

    def get(self, color: bool, piece_type: int, size: int) -> ImageTk.PhotoImage:
        key = (color, piece_type, size)
        if key not in self._cache:
            self._cache[key] = self._load_sprite(color, piece_type, size)
        return self._cache[key]

    def _load_sprite(self, color: bool, piece_type: int, size: int) -> ImageTk.PhotoImage:
        path = self.piece_set.files[(color, piece_type)]
        image = Image.open(path).convert("RGBA")
        image.thumbnail((size, size), Image.LANCZOS)
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        x = (size - image.width) // 2
        y = (size - image.height) // 2
        canvas.alpha_composite(image, (x, y))
        return ImageTk.PhotoImage(canvas)
