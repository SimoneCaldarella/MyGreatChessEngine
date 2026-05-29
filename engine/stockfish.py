from __future__ import annotations

import os
import platform
import shutil
import stat
import subprocess
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable

import chess

from config import ENGINE_ROOT


class StockfishInstaller:
    VERSION = "sf_18"

    def __init__(self, engine_root: Path = ENGINE_ROOT):
        self.engine_root = engine_root

    def find_binary(self) -> Path | None:
        candidates = list(self.engine_root.rglob("stockfish*")) if self.engine_root.exists() else []
        if platform.system() == "Windows":
            candidates = [path for path in candidates if path.suffix.lower() == ".exe"]
        else:
            candidates = [path for path in candidates if path.is_file() and os.access(path, os.X_OK)]
        if candidates:
            return candidates[0]

        system_binary = shutil.which("stockfish")
        return Path(system_binary) if system_binary else None

    def install(self, status: Callable[[str], None]) -> Path:
        self.engine_root.mkdir(exist_ok=True)
        archive_name = self.archive_name()
        status(f"Downloading {archive_name} ...")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            archive_path = tmp_path / archive_name
            urllib.request.urlretrieve(self.download_url(), archive_path)

            extract_path = tmp_path / "extract"
            extract_path.mkdir()
            self._extract(archive_path, extract_path)

            source = self._find_archive_binary(extract_path)
            destination = self.engine_root / source.name
            shutil.copy2(source, destination)
            if platform.system() != "Windows":
                destination.chmod(destination.stat().st_mode | stat.S_IXUSR)
            status(f"Installed Stockfish at {destination}")
            return destination

    def download_url(self) -> str:
        return (
            "https://sourceforge.net/projects/stockfish.mirror/files/"
            f"{self.VERSION}/{self.archive_name()}/download"
        )

    def archive_name(self) -> str:
        system = platform.system()
        machine = platform.machine().lower()

        if system == "Darwin":
            if "arm" in machine or "aarch64" in machine:
                return "stockfish-macos-m1-apple-silicon.tar"
            return "stockfish-macos-x86-64.tar"
        if system == "Windows":
            if "arm" in machine or "aarch64" in machine:
                return "stockfish-windows-armv8.zip"
            return "stockfish-windows-x86-64.zip"
        if system == "Linux":
            return "stockfish-ubuntu-x86-64.tar"
        raise RuntimeError(f"No Stockfish download is configured for {system}.")

    def _extract(self, archive_path: Path, extract_path: Path) -> None:
        if archive_path.suffix == ".zip":
            with zipfile.ZipFile(archive_path) as zf:
                zf.extractall(extract_path)
        else:
            with tarfile.open(archive_path) as tf:
                tf.extractall(extract_path)

    def _find_archive_binary(self, extract_path: Path) -> Path:
        candidates = []
        for path in extract_path.rglob("*"):
            if path.is_file() and "stockfish" in path.name.lower():
                if platform.system() == "Windows" and path.suffix.lower() != ".exe":
                    continue
                candidates.append(path)
        if not candidates:
            raise RuntimeError("The Stockfish archive did not contain an engine binary.")
        return sorted(candidates, key=lambda p: len(p.name))[0]


class StockfishEngine:
    def __init__(self, installer: StockfishInstaller | None = None):
        self.installer = installer or StockfishInstaller()
        self.process: subprocess.Popen[str] | None = None

    def close(self) -> None:
        if self.process:
            try:
                self._send("quit")
            except OSError:
                pass
            self.process = None

    def best_move(self, board: chess.Board, movetime_ms: int = 500) -> chess.Move | None:
        if self.process is None or self.process.poll() is not None:
            self._start()

        self._send(f"position fen {board.fen()}")
        self._send(f"go movetime {movetime_ms}")
        while True:
            line = self._read()
            if line.startswith("bestmove"):
                parts = line.split()
                if len(parts) >= 2 and parts[1] != "(none)":
                    return chess.Move.from_uci(parts[1])
                return None

    def _start(self) -> None:
        engine_path = self.installer.find_binary()
        if engine_path is None:
            raise RuntimeError("Stockfish is not installed.")

        self.process = subprocess.Popen(
            [str(engine_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        self._uci_handshake()

    def _uci_handshake(self) -> None:
        self._send("uci")
        while self._read() != "uciok":
            pass
        self._send("isready")
        while self._read() != "readyok":
            pass

    def _send(self, command: str) -> None:
        if self.process is None or self.process.stdin is None:
            raise OSError("Stockfish is not running")
        self.process.stdin.write(command + "\n")
        self.process.stdin.flush()

    def _read(self) -> str:
        if self.process is None or self.process.stdout is None:
            raise OSError("Stockfish is not running")
        return self.process.stdout.readline().strip()
