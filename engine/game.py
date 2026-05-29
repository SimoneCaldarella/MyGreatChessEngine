from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

import chess
import chess.pgn


class GameMode(StrEnum):
    FRIEND = "friend"
    STOCKFISH = "stockfish"


@dataclass
class MoveSelection:
    selected_square: chess.Square | None = None
    legal_targets: set[chess.Square] = field(default_factory=set)

    def clear(self) -> None:
        self.selected_square = None
        self.legal_targets.clear()


class ChessSession:
    def __init__(self, mode: GameMode = GameMode.FRIEND):
        self.mode = mode
        self.board = chess.Board()
        self.selection = MoveSelection()
        self.last_move_was_capture = False

    def reset(self, mode: GameMode) -> None:
        self.mode = mode
        self.board = chess.Board()
        self.selection.clear()
        self.last_move_was_capture = False

    def can_human_move(self) -> bool:
        if self.board.is_game_over():
            return False
        return not (self.mode == GameMode.STOCKFISH and self.board.turn == chess.BLACK)

    def select(self, square: chess.Square) -> bool:
        piece = self.board.piece_at(square)
        if not piece or piece.color != self.board.turn:
            self.selection.clear()
            return False

        self.selection.selected_square = square
        self.selection.legal_targets = {
            move.to_square for move in self.board.legal_moves if move.from_square == square
        }
        return True

    def move_selected_piece_to(self, square: chess.Square) -> chess.Move | None:
        if self.selection.selected_square is None:
            return None
        return self.push_move(self.selection.selected_square, square)

    def push_move(self, from_square: chess.Square, to_square: chess.Square) -> chess.Move | None:
        move = self._candidate_move(from_square, to_square)
        if move not in self.board.legal_moves:
            return None
        self.last_move_was_capture = self.board.is_capture(move)
        self.board.push(move)
        self.selection.clear()
        return move

    def push_engine_move(self, move: chess.Move | None) -> bool:
        if move is None or move not in self.board.legal_moves:
            self.last_move_was_capture = False
            return False
        self.last_move_was_capture = self.board.is_capture(move)
        self.board.push(move)
        return True

    def status_text(self) -> str:
        if self.board.is_game_over():
            return f"Game over: {self.board.result()}. Save the PGN or start a new setup."

        side = "White" if self.board.turn == chess.WHITE else "Black"
        if self.mode == GameMode.STOCKFISH:
            detail = "Your move." if self.board.turn == chess.WHITE else "Stockfish to move."
            return f"{side} to move. {detail}"
        return f"{side} to move."

    def _candidate_move(self, from_square: chess.Square, to_square: chess.Square) -> chess.Move:
        move = chess.Move(from_square, to_square)
        piece = self.board.piece_at(from_square)
        if (
            piece
            and piece.piece_type == chess.PAWN
            and chess.square_rank(to_square) in {0, 7}
            and move not in self.board.legal_moves
        ):
            return chess.Move(from_square, to_square, promotion=chess.QUEEN)
        return move


class PgnReplay:
    def __init__(self, game: chess.pgn.Game):
        self.board = game.board()
        self.moves = list(game.mainline_moves())
        self.index = 0
        self.last_move_was_capture = False

    def next(self) -> bool:
        if self.index >= len(self.moves):
            self.last_move_was_capture = False
            return False
        move = self.moves[self.index]
        self.last_move_was_capture = self.board.is_capture(move)
        self.board.push(move)
        self.index += 1
        return True

    def status_text(self) -> str:
        if self.index >= len(self.moves):
            return "End of match."
        return f"Move {self.index} of {len(self.moves)}."
