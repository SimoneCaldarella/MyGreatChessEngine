from __future__ import annotations

import chess
import tkinter as tk

from config import BOARD_SIZE, SQUARE_SIZE
from graphics.pieces import SpriteCache


class BoardView:
    LIGHT = "#f0d9b5"
    DARK = "#b58863"
    SELECTED = "#f5d76e"
    TARGET = "#c9d97e"
    TARGET_DOT = "#607d3b"

    def __init__(self, parent: tk.Widget, sprites: SpriteCache):
        self.canvas = tk.Canvas(parent, width=BOARD_SIZE, height=BOARD_SIZE, highlightthickness=0)
        self.sprites = sprites

    def grid(self, **kwargs: object) -> None:
        self.canvas.grid(**kwargs)

    def bind_click(self, callback: object) -> None:
        self.canvas.bind("<Button-1>", callback)

    def draw(
        self,
        board: chess.Board,
        selected_square: chess.Square | None = None,
        legal_targets: set[chess.Square] | None = None,
    ) -> None:
        self.canvas.delete("all")
        legal_targets = legal_targets or set()
        self._draw_squares(selected_square, legal_targets)
        self._draw_pieces(board)

    @staticmethod
    def event_to_square(event: tk.Event) -> chess.Square | None:
        file = event.x // SQUARE_SIZE
        rank = 7 - (event.y // SQUARE_SIZE)
        if not 0 <= file <= 7 or not 0 <= rank <= 7:
            return None
        return chess.square(file, rank)

    def _draw_squares(
        self,
        selected_square: chess.Square | None,
        legal_targets: set[chess.Square],
    ) -> None:
        for rank in range(8):
            for file in range(8):
                square = chess.square(file, rank)
                x1 = file * SQUARE_SIZE
                y1 = (7 - rank) * SQUARE_SIZE
                fill = self._square_color(rank, file, square, selected_square, legal_targets)
                self.canvas.create_rectangle(
                    x1, y1, x1 + SQUARE_SIZE, y1 + SQUARE_SIZE, fill=fill, outline=fill
                )
                if square in legal_targets:
                    self.canvas.create_oval(
                        x1 + 27,
                        y1 + 27,
                        x1 + 43,
                        y1 + 43,
                        fill=self.TARGET_DOT,
                        outline="",
                    )

    def _square_color(
        self,
        rank: int,
        file: int,
        square: chess.Square,
        selected_square: chess.Square | None,
        legal_targets: set[chess.Square],
    ) -> str:
        if square == selected_square:
            return self.SELECTED
        if square in legal_targets:
            return self.TARGET
        return self.LIGHT if (rank + file) % 2 == 0 else self.DARK

    def _draw_pieces(self, board: chess.Board) -> None:
        for square, piece in board.piece_map().items():
            file = chess.square_file(square)
            rank = chess.square_rank(square)
            x = file * SQUARE_SIZE + SQUARE_SIZE // 2
            y = (7 - rank) * SQUARE_SIZE + SQUARE_SIZE // 2
            image = self.sprites.get(piece.color, piece.piece_type, 58)
            self.canvas.create_image(x, y, image=image)
