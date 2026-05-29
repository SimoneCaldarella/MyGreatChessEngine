# Roadmap

## Done
- Replaced the placeholder `main.py` with a Tkinter chess application.
- Added sprite-set discovery from `assets/sprites/pieces` and a first screen to choose a complete piece library.
- Added mode selection after sprite selection:
  - play locally with a friend,
  - play against Stockfish,
  - load a PGN from `assets/matches` or `saved_matches`.
- Added graphical board rendering with selected sprites.
- Added legal move handling, turn display, move list, and automatic queen promotion.
- Added PGN save support during and after games.
- Added PGN viewer with a bottom-right "Next Step" button.
- Added Stockfish UCI integration and OS-aware Stockfish 18 downloader.
- Added a minimal player README.
- Added `requirements.txt` for the Python package dependencies.
- Refactored the application into a small MVC-style structure:
  - `app.py` owns Tkinter screen orchestration.
  - `engine/game.py` owns game and replay state.
  - `engine/pgn_service.py` owns PGN loading, saving, and move-list formatting.
  - `engine/stockfish.py` owns Stockfish installation and UCI communication.
  - `graphics/pieces.py` owns sprite discovery and image caching.
  - `graphics/board.py` owns board rendering and board-click coordinate mapping.
  - `config.py` owns project paths and window constants.

## Notes
- Stockfish is downloaded only when the user selects Stockfish mode and no local engine is found.
- Saved games are written to `saved_matches` by default.
- The app uses `python-chess`, Tkinter, and Pillow.

## Possible Next Improvements
- Add promotion choice UI instead of automatically promoting to queen.
- Add board flipping and player color selection for Stockfish games.
- Add previous-step support in the PGN viewer.
- Add clocks and captured-piece trays.
