from __future__ import annotations

import queue
import threading
from pathlib import Path

import chess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from config import SAVE_ROOT, WINDOW_SIZE
from engine.game import ChessSession, GameMode, PgnReplay
from engine.pgn_service import PgnService, format_move_list
from engine.stockfish import StockfishEngine, StockfishInstaller
from graphics.board import BoardView
from graphics.pieces import PieceSet, PieceSetLibrary, SpriteCache


class ChessApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("My Great Chess Engine")
        self.root.geometry(WINDOW_SIZE)
        self.root.resizable(False, False)

        self.status_var = tk.StringVar(value="Choose your pieces.")
        self.piece_sets = PieceSetLibrary().discover()
        self.selected_set: PieceSet | None = None
        self.sprites: SpriteCache | None = None
        self.session = ChessSession()
        self.replay: PgnReplay | None = None
        self.pgn_service = PgnService()
        self.stockfish_installer = StockfishInstaller()
        self.stockfish = StockfishEngine(self.stockfish_installer)
        self.ai_queue: queue.Queue[chess.Move | Exception | None] = queue.Queue()

        self.board_view: BoardView | None = None
        self.moves_box: tk.Listbox | None = None
        self.match_list: tk.Listbox | None = None
        self.current_matches: list[Path] = []

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.show_piece_selection()

    def run(self) -> int:
        self.root.mainloop()
        return 0

    def clear(self) -> None:
        self.board_view = None
        self.moves_box = None
        self.match_list = None
        for child in self.root.winfo_children():
            child.destroy()

    def set_status(self, text: str) -> None:
        self.root.after(0, self.status_var.set, text)

    def show_piece_selection(self) -> None:
        self.clear()
        self.status_var.set("Choose a sprite set before choosing a game mode.")
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Select Pieces", font=("Helvetica", 24, "bold")).pack(anchor="w")
        ttk.Label(frame, textvariable=self.status_var).pack(anchor="w", pady=(4, 16))

        grid = ttk.Frame(frame)
        grid.pack(fill="both", expand=True)

        if not self.piece_sets:
            ttk.Label(grid, text="No complete chess sprite sets found in assets/sprites/pieces.").pack()
            return

        for index, piece_set in enumerate(self.piece_sets):
            self._add_piece_set_card(grid, index, piece_set)

        for col in range(3):
            grid.columnconfigure(col, weight=1)

    def _add_piece_set_card(self, parent: ttk.Frame, index: int, piece_set: PieceSet) -> None:
        card = ttk.Frame(parent, padding=10, relief="ridge")
        card.grid(row=index // 3, column=index % 3, sticky="nsew", padx=8, pady=8)
        ttk.Label(card, text=piece_set.display_name, font=("Helvetica", 13, "bold")).pack()

        preview = tk.Canvas(card, width=180, height=52, highlightthickness=0)
        preview.pack(pady=8)
        self._draw_piece_preview(preview, piece_set)

        ttk.Button(
            card,
            text="Use This Set",
            command=lambda current=piece_set: self.select_piece_set(current),
        ).pack(fill="x")

    def _draw_piece_preview(self, preview: tk.Canvas, piece_set: PieceSet) -> None:
        cache = SpriteCache(piece_set)
        images = []
        for index, piece_type in enumerate(
            [chess.KING, chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT, chess.PAWN]
        ):
            image = cache.get(chess.WHITE, piece_type, 28)
            preview.create_image(12 + index * 28, 26, image=image, anchor="w")
            images.append(image)
        preview.images = images

    def select_piece_set(self, piece_set: PieceSet) -> None:
        self.selected_set = piece_set
        self.sprites = SpriteCache(piece_set)
        self.show_mode_selection()

    def show_mode_selection(self) -> None:
        self.clear()
        frame = ttk.Frame(self.root, padding=36)
        frame.pack(fill="both", expand=True)
        title = f"{self.selected_set.display_name} Pieces" if self.selected_set else "Pieces"
        ttk.Label(frame, text=title, font=("Helvetica", 24, "bold")).pack(anchor="w")
        ttk.Label(frame, text="Choose what to do next.").pack(anchor="w", pady=(4, 24))

        actions = ttk.Frame(frame)
        actions.pack(anchor="center", pady=60)
        ttk.Button(actions, text="Play With A Friend", command=lambda: self.start_game(GameMode.FRIEND)).pack(
            fill="x", pady=8, ipadx=60, ipady=8
        )
        ttk.Button(actions, text="Play With Stockfish", command=self.start_stockfish_game).pack(
            fill="x", pady=8, ipadx=60, ipady=8
        )
        ttk.Button(actions, text="Load Existing Match", command=self.show_match_loader).pack(
            fill="x", pady=8, ipadx=60, ipady=8
        )
        ttk.Button(frame, text="Back To Pieces", command=self.show_piece_selection).pack(anchor="w")

    def start_stockfish_game(self) -> None:
        if self.stockfish_installer.find_binary() is not None:
            self.start_game(GameMode.STOCKFISH)
            return

        answer = messagebox.askyesno(
            "Install Stockfish",
            "Stockfish is not installed locally. Download the matching engine for this OS?",
        )
        if not answer:
            return
        self.status_var.set("Preparing Stockfish download...")

        def worker() -> None:
            try:
                self.stockfish_installer.install(self.set_status)
                self.root.after(0, lambda: self.start_game(GameMode.STOCKFISH))
            except Exception as exc:
                self.root.after(0, lambda: messagebox.showerror("Stockfish", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def start_game(self, mode: GameMode) -> None:
        self.session.reset(mode)
        self.replay = None
        self.show_board_screen()

    def show_board_screen(self) -> None:
        self.clear()
        shell = ttk.Frame(self.root, padding=16)
        shell.pack(fill="both", expand=True)

        self.board_view = BoardView(shell, self._sprites())
        self.board_view.grid(row=0, column=0, rowspan=2)
        self.board_view.bind_click(self.on_board_click)

        side = ttk.Frame(shell, padding=(18, 0, 0, 0), width=270)
        side.grid(row=0, column=1, sticky="nsew")
        side.grid_propagate(False)
        ttk.Label(side, text="Game", font=("Helvetica", 20, "bold")).pack(anchor="w")
        ttk.Label(side, textvariable=self.status_var, wraplength=250).pack(anchor="w", pady=(6, 16))
        ttk.Button(side, text="Save PGN", command=self.save_current_game).pack(fill="x", pady=4)
        ttk.Button(side, text="New Setup", command=self.show_piece_selection).pack(fill="x", pady=4)
        ttk.Button(side, text="Back To Menu", command=self.show_mode_selection).pack(fill="x", pady=4)

        self.moves_box = tk.Listbox(side, height=22)
        self.moves_box.pack(fill="both", expand=True, pady=(18, 0))
        self.update_game_status()
        self.draw_current_board()

    def on_board_click(self, event: tk.Event) -> None:
        if self.board_view is None or not self.session.can_human_move():
            return

        square = self.board_view.event_to_square(event)
        if square is None:
            return

        if self.session.selection.selected_square is None:
            self.select_square(square)
            return

        move = self.session.move_selected_piece_to(square)
        if move:
            self.after_human_move()
        else:
            self.select_square(square)
        self.draw_current_board()

    def select_square(self, square: chess.Square) -> None:
        if self.session.select(square):
            self.status_var.set(f"Selected {chess.square_name(square)}.")
        self.draw_current_board()

    def after_human_move(self) -> None:
        self.update_game_status()
        if self.session.mode == GameMode.STOCKFISH and not self.session.board.is_game_over():
            self.status_var.set("Stockfish is thinking...")
            snapshot = self.session.board.copy()

            def worker() -> None:
                try:
                    self.ai_queue.put(self.stockfish.best_move(snapshot))
                except Exception as exc:
                    self.ai_queue.put(exc)

            threading.Thread(target=worker, daemon=True).start()
            self.root.after(100, self.poll_ai_move)

    def poll_ai_move(self) -> None:
        try:
            result = self.ai_queue.get_nowait()
        except queue.Empty:
            self.root.after(100, self.poll_ai_move)
            return

        if isinstance(result, Exception):
            messagebox.showerror("Stockfish", str(result))
        else:
            self.session.push_engine_move(result)
        self.update_game_status()
        self.draw_current_board()

    def save_current_game(self) -> None:
        SAVE_ROOT.mkdir(exist_ok=True)
        path = filedialog.asksaveasfilename(
            title="Save PGN",
            initialdir=SAVE_ROOT,
            initialfile=self.pgn_service.default_save_name(),
            defaultextension=".pgn",
            filetypes=[("PGN files", "*.pgn"), ("All files", "*.*")],
        )
        if not path:
            return
        self.pgn_service.save_game(self.session.board, Path(path), self.session.mode)
        self.status_var.set(f"Saved {Path(path).name}.")

    def show_match_loader(self) -> None:
        self.clear()
        frame = ttk.Frame(self.root, padding=24)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Load PGN Match", font=("Helvetica", 24, "bold")).pack(anchor="w")
        ttk.Label(frame, text="Choose a match and step through it.").pack(anchor="w", pady=(4, 16))

        self.match_list = tk.Listbox(frame, height=18)
        self.match_list.pack(fill="both", expand=True)
        self.current_matches = self.pgn_service.available_matches()
        for path in self.current_matches:
            self.match_list.insert(tk.END, self.pgn_service.display_path(path))
        if self.current_matches:
            self.match_list.selection_set(0)

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=16)
        ttk.Button(buttons, text="Load Selected", command=self.load_selected_match).pack(side="left")
        ttk.Button(buttons, text="Back", command=self.show_mode_selection).pack(side="left", padx=8)

    def load_selected_match(self) -> None:
        if self.match_list is None:
            return
        selection = self.match_list.curselection()
        if not selection:
            return

        path = self.current_matches[selection[0]]
        game = self.pgn_service.read_game(path)
        if game is None:
            messagebox.showerror("PGN", "Could not read this PGN file.")
            return

        self.replay = PgnReplay(game)
        self.show_viewer(path.name)

    def show_viewer(self, title: str) -> None:
        self.clear()
        shell = ttk.Frame(self.root, padding=16)
        shell.pack(fill="both", expand=True)

        self.board_view = BoardView(shell, self._sprites())
        self.board_view.grid(row=0, column=0, rowspan=2)

        side = ttk.Frame(shell, padding=(18, 0, 0, 0), width=270)
        side.grid(row=0, column=1, sticky="nsew")
        side.grid_propagate(False)
        ttk.Label(side, text=title, font=("Helvetica", 16, "bold"), wraplength=250).pack(anchor="w")
        ttk.Label(side, textvariable=self.status_var, wraplength=250).pack(anchor="w", pady=(6, 16))
        ttk.Button(side, text="Back To Matches", command=self.show_match_loader).pack(fill="x", pady=4)
        ttk.Button(side, text="New Setup", command=self.show_piece_selection).pack(fill="x", pady=4)

        bottom = ttk.Frame(side)
        bottom.pack(side="bottom", fill="x")
        ttk.Button(bottom, text="Next Step", command=self.next_viewer_step).pack(fill="x", ipady=8)

        self.moves_box = tk.Listbox(side, height=22)
        self.moves_box.pack(fill="both", expand=True, pady=(18, 12))
        self.status_var.set(self.replay.status_text() if self.replay else "No match loaded.")
        self.draw_current_board()

    def next_viewer_step(self) -> None:
        if self.replay is None:
            return
        self.replay.next()
        self.refresh_moves(self.replay.board)
        self.status_var.set(self.replay.status_text())
        self.draw_current_board()

    def update_game_status(self) -> None:
        self.status_var.set(self.session.status_text())
        self.refresh_moves(self.session.board)

    def refresh_moves(self, board: chess.Board) -> None:
        if self.moves_box is None:
            return
        self.moves_box.delete(0, tk.END)
        for item in format_move_list(board):
            self.moves_box.insert(tk.END, item)
        self.moves_box.yview_moveto(1)

    def draw_current_board(self) -> None:
        if self.board_view is None:
            return
        if self.replay is not None:
            self.board_view.draw(self.replay.board)
            return
        self.board_view.draw(
            self.session.board,
            self.session.selection.selected_square,
            self.session.selection.legal_targets,
        )

    def _sprites(self) -> SpriteCache:
        if self.sprites is None:
            raise RuntimeError("No piece set has been selected.")
        return self.sprites

    def on_close(self) -> None:
        self.stockfish.close()
        self.root.destroy()
