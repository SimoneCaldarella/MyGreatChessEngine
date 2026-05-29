from __future__ import annotations

from app import ChessApp


def run_chess_game() -> int:
    app = ChessApp()
    return app.run()


if __name__ == "__main__":
    raise SystemExit(run_chess_game())
