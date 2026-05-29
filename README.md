# My Great Chess Engine

A small Python chess GUI using the sprites in `assets/sprites/pieces`.

## Run

```bash
.venv/bin/python main.py
```

## Play

1. Choose a sprite set.
2. Choose a mode:
   - `Play With A Friend`: local two-player chess.
   - `Play With Stockfish`: play as White against Stockfish. If Stockfish is missing, the app can download the correct engine for your OS.
   - `Load Existing Match`: select a PGN from `assets/matches` or `saved_matches` and press `Next Step` to replay it.
3. During a game, press `Save PGN` to save the current match.

Saved games default to `saved_matches`.

## Code Layout

- `main.py`: app entry point.
- `app.py`: Tkinter screens and user interaction flow.
- `engine/`: chess state, PGN handling, and Stockfish integration.
- `graphics/`: sprite loading and board rendering.
- `config.py`: shared paths and UI constants.

## Requirements

- Python 3
- `python-chess`
- `Pillow`
- Tkinter, usually included with Python

Install Python packages with:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

In your IDE, select `.venv/bin/python` as the project interpreter so `import chess`
and `import chess.pgn` resolve correctly.
