"""main.py — entrypoint CLI"""

import os
import sys
import argparse
import requests

from data import config
from src import agent


def check_ollama():
    try:
        requests.get("http://localhost:11434", timeout=3)
        return True
    except requests.exceptions.ConnectionError:
        return False


def main():
    parser = argparse.ArgumentParser(description="AI coding agent lokal via Ollama")
    parser.add_argument("task", help="Deskripsi tugas, mis. 'perbaiki bug di layers.cpp'")
    parser.add_argument("--root", default=".", help="Root direktori project")
    parser.add_argument("--max-iter", type=int, default=config.MAX_ITER_DEFAULT)
    args = parser.parse_args()

    if not check_ollama():
        print("[ERROR] Ollama server belum jalan. Jalankan: ollama serve &")
        sys.exit(1)

    if not os.path.isfile(config.TOOL_SCHEMA_PATH):
        print(f"[ERROR] {config.TOOL_SCHEMA_PATH} tidak ditemukan di direktori kerja.")
        sys.exit(1)

    agent.run_agent(args.task, os.path.abspath(args.root), args.max_iter)


if __name__ == "__main__":
    main()