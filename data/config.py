"""data/config.py — konfigurasi agent"""

import os

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "hf.co/yuxinlu1/gemma-4-12B-agentic-fable5-composer2.5-v2-3.5x-tau2-GGUF:Q4_K_M"

MAX_ITER_DEFAULT = 8
REQUEST_TIMEOUT = 300
TEMPERATURE = 0.2

_DATA_DIR = os.path.dirname(os.path.abspath(__file__))
TOOL_SCHEMA_PATH = os.path.join(_DATA_DIR, "from.json")

SYSTEM_PROMPT = """Kamu adalah coding agent otonom untuk project C++/Python di Termux.
Tugasmu: cari file terkait, baca source, edit dengan presisi (pakai replace_in_file,
bukan menulis ulang seluruh file kecuali file baru), simpan, lalu compile.
Jika compile gagal, baca error dari log, cari baris penyebabnya, perbaiki, lalu compile lagi.
Selalu gunakan tool, jangan hanya menjelaskan saat ada pekerjaan yang bisa dilakukan.

Saat tugas sudah selesai, jawab dengan teks biasa (tanpa tool call) mengikuti format ini:
Ringkasan: <1-2 kalimat apa yang dilakukan>
Deskripsi: <fungsi/isi kode singkat>
Cara pakai: <cara menjalankan/memakai kode singkat>
Lalu tunggu instruksi berikutnya dari user.
"""