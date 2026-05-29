from __future__ import annotations

import datetime as dt
from pathlib import Path

import chess
import chess.pgn

from config import MATCH_ROOT, ROOT, SAVE_ROOT
from engine.game import GameMode


class PgnService:
    def __init__(self, match_root: Path = MATCH_ROOT, save_root: Path = SAVE_ROOT):
        self.match_root = match_root
        self.save_root = save_root

    def available_matches(self) -> list[Path]:
        matches = sorted(self.match_root.glob("*.pgn")) if self.match_root.exists() else []
        saved = sorted(self.save_root.glob("*.pgn")) if self.save_root.exists() else []
        return matches + saved

    def display_path(self, path: Path) -> str:
        try:
            return str(path.relative_to(ROOT))
        except ValueError:
            return str(path)

    def read_game(self, path: Path) -> chess.pgn.Game | None:
        with open(path, "r", encoding="utf-8") as handle:
            return chess.pgn.read_game(handle)

    def default_save_name(self) -> str:
        return f"match_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.pgn"

    def save_game(self, board: chess.Board, path: Path, mode: GameMode) -> None:
        self.save_root.mkdir(exist_ok=True)
        game = chess.pgn.Game.from_board(board)
        game.headers["Event"] = "My Great Chess Engine"
        game.headers["Date"] = dt.date.today().strftime("%Y.%m.%d")
        game.headers["White"] = "White"
        game.headers["Black"] = "Stockfish" if mode == GameMode.STOCKFISH else "Black"
        game.headers["Result"] = board.result() if board.is_game_over() else "*"

        with open(path, "w", encoding="utf-8") as handle:
            exporter = chess.pgn.FileExporter(handle)
            game.accept(exporter)


def format_move_list(board: chess.Board) -> list[str]:
    temp = chess.Board()
    lines: list[str] = []
    for index, move in enumerate(board.move_stack, start=1):
        san = temp.san(move)
        temp.push(move)
        if index % 2 == 1:
            lines.append(f"{(index + 1) // 2}. {san}")
        else:
            lines[-1] += f"  {san}"
    return lines
