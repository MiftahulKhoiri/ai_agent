"""main.py — entrypoint chatbot interaktif"""

import os
import sys
import argparse
import requests

from data import config
from src.agent import Agent


def check_ollama():
    try:
        requests.get("http://localhost:11434", timeout=3)
        return True
    except requests.exceptions.ConnectionError:
        return False


HELP_TEXT = """Perintah tersedia:
  /root <path>   ganti root project aktif
  /reset         hapus histori percakapan (mulai sesi baru)
  /help          tampilkan pesan ini
  /exit          keluar
Ketik pesan biasa untuk memberi tugas ke agent."""


def main():
    parser = argparse.ArgumentParser(description="AI coding agent lokal via Ollama — mode chat")
    parser.add_argument("--root", default=".", help="Root direktori project awal")
    parser.add_argument("--max-iter", type=int, default=config.MAX_ITER_DEFAULT)
    args = parser.parse_args()

    if not check_ollama():
        print("[ERROR] Ollama server belum jalan. Jalankan: ollama serve &")
        sys.exit(1)

    if not os.path.isfile(config.TOOL_SCHEMA_PATH):
        print(f"[ERROR] {config.TOOL_SCHEMA_PATH} tidak ditemukan.")
        sys.exit(1)

    agent = Agent(root=args.root)

    print(f"AI Agent siap. Root: {agent.root}")
    print("Ketik /help untuk daftar perintah, /exit untuk keluar.\n")

    while True:
        try:
            user_input = input("kamu> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nKeluar.")
            break

        if not user_input:
            continue

        if user_input == "/exit":
            print("Keluar.")
            break
        elif user_input == "/help":
            print(HELP_TEXT)
            continue
        elif user_input == "/reset":
            agent.reset()
            print("[OK] Histori percakapan direset.")
            continue
        elif user_input.startswith("/root "):
            new_root = user_input[len("/root "):].strip()
            agent.set_root(new_root)
            print(f"[OK] Root diganti ke: {agent.root}")
            continue

        reply = agent.send(user_input, max_iter=args.max_iter)
        print(f"\nagent> {reply}\n")


if __name__ == "__main__":
    main()