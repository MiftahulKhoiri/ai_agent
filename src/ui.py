"""src/ui.py — tampilan tahapan proses agent di terminal (mirip chatbot)"""

import sys
import time
import threading
import itertools

STAGE_ICONS = {
    "think": "🤔",
    "code": "✍️ ",
    "search": "🔍",
    "compile": "⚙️ ",
    "shell": "🖥️ ",
    "debug": "🐛",
    "result": "✅",
    "error": "❌",
}

STAGE_LABELS = {
    "think": "Berpikir",
    "code": "Menulis kode",
    "search": "Mencari & membaca file",
    "compile": "Compile & testing",
    "shell": "Menjalankan perintah",
    "debug": "Debugging: memperbaiki error",
    "result": "Hasil",
    "error": "Error",
}


def stage(key, detail=""):
    icon = STAGE_ICONS.get(key, "•")
    label = STAGE_LABELS.get(key, key)
    line = f"{icon} {label}"
    if detail:
        line += f" — {detail}"
    print(line)


class Spinner:
    """Spinner untuk proses blocking (compile/run_shell) supaya tidak terlihat diam."""
    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, label="Memproses"):
        self.label = label
        self._stop = threading.Event()
        self._thread = None

    def _spin(self):
        for frame in itertools.cycle(self.FRAMES):
            if self._stop.is_set():
                break
            sys.stdout.write(f"\r{frame} {self.label}...   ")
            sys.stdout.flush()
            time.sleep(0.08)
        sys.stdout.write("\r" + " " * (len(self.label) + 15) + "\r")
        sys.stdout.flush()

    def __enter__(self):
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._stop.set()
        if self._thread:
            self._thread.join()