from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

import chess
import tkinter as tk
from PIL import Image, ImageSequence, ImageTk

from config import ANIMATION_ROOT, BOARD_SIZE, SQUARE_SIZE
from graphics.pieces import SpriteCache


@dataclass(frozen=True)
class Animation:
    frames: tuple[ImageTk.PhotoImage, ...]
    durations: tuple[int, ...]


class BoardView:
    LIGHT = "#f0d9b5"
    DARK = "#b58863"
    SELECTED = "#f5d76e"
    TARGET = "#c9d97e"
    TARGET_DOT = "#607d3b"
    CAPTURE_ANIMATION_SECONDS = 2
    FALLBACK_FRAME_DURATION_MS = 80

    def __init__(self, parent: tk.Widget, sprites: SpriteCache):
        self.canvas = tk.Canvas(parent, width=BOARD_SIZE, height=BOARD_SIZE, highlightthickness=0)
        self.sprites = sprites
        self._animation_cache: dict[Path, Animation] = {}
        self._animation_frame_index = 0
        self._animation_item: int | None = None
        self._animation_job: str | None = None
        self._animation_stop_job: str | None = None
        self._active_animation: Animation | None = None

    def grid(self, **kwargs: object) -> None:
        self.canvas.grid(**kwargs)

    def bind_click(self, callback: object) -> None:
        self.canvas.bind("<Button-1>", callback)

    def cancel_animation(self) -> None:
        self._cancel_animation_jobs()
        self._active_animation = None
        self._animation_item = None

    def draw(
        self,
        board: chess.Board,
        selected_square: chess.Square | None = None,
        legal_targets: set[chess.Square] | None = None,
    ) -> None:
        self.canvas.delete("all")
        self._animation_item = None
        legal_targets = legal_targets or set()
        self._draw_squares(selected_square, legal_targets)
        self._draw_pieces(board)
        self._redraw_active_animation_frame()

    def show_random_capture_animation(self) -> None:
        paths = [ANIMATION_ROOT / f"kill_{number}.gif" for number in range(1, 6)]
        available_paths = [path for path in paths if path.exists()]
        if not available_paths:
            return
        self.show_capture_animation(random.choice(available_paths))

    def show_capture_animation(self, path: Path) -> None:
        animation = self._load_animation(path)
        if animation is None:
            return
        self._cancel_animation_jobs()
        self._active_animation = animation
        self._animation_frame_index = 0
        self._draw_animation_frame()
        self._animation_stop_job = self.canvas.after(
            self.CAPTURE_ANIMATION_SECONDS * 1000,
            self._stop_animation,
        )

    @staticmethod
    def event_to_square(event: tk.Event) -> chess.Square | None:
        file = event.x // SQUARE_SIZE
        rank = 7 - (event.y // SQUARE_SIZE)
        if not 0 <= file <= 7 or not 0 <= rank <= 7:
            return None
        return chess.square(file, rank)

    def _cancel_animation_jobs(self) -> None:
        if self._animation_job is not None:
            self.canvas.after_cancel(self._animation_job)
            self._animation_job = None
        if self._animation_stop_job is not None:
            self.canvas.after_cancel(self._animation_stop_job)
            self._animation_stop_job = None

    def _load_animation(self, path: Path) -> Animation | None:
        if path in self._animation_cache:
            return self._animation_cache[path]

        frames: list[ImageTk.PhotoImage] = []
        durations: list[int] = []
        with Image.open(path) as source:
            for frame in ImageSequence.Iterator(source):
                image = frame.convert("RGBA")
                frames.append(ImageTk.PhotoImage(image))
                durations.append(frame.info.get("duration", self.FALLBACK_FRAME_DURATION_MS))

        if not frames:
            return None

        animation = Animation(tuple(frames), tuple(durations))
        self._animation_cache[path] = animation
        return animation

    def _draw_animation_frame(self) -> None:
        if self._active_animation is None:
            return

        self._redraw_active_animation_frame()
        duration = self._active_animation.durations[self._animation_frame_index]
        self._animation_frame_index = (self._animation_frame_index + 1) % len(self._active_animation.frames)
        self._animation_job = self.canvas.after(max(1, duration), self._draw_animation_frame)

    def _redraw_active_animation_frame(self) -> None:
        if self._active_animation is None:
            return

        if self._animation_item is not None:
            self.canvas.delete(self._animation_item)
        image = self._active_animation.frames[self._animation_frame_index]
        self._animation_item = self.canvas.create_image(
            BOARD_SIZE // 2,
            BOARD_SIZE // 2,
            image=image,
        )
        self.canvas.tag_raise(self._animation_item)

    def _stop_animation(self) -> None:
        if self._animation_job is not None:
            self.canvas.after_cancel(self._animation_job)
            self._animation_job = None
        self._animation_stop_job = None
        self._active_animation = None
        if self._animation_item is not None:
            self.canvas.delete(self._animation_item)
            self._animation_item = None

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
