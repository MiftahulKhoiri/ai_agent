"""config.py — konfigurasi agent"""

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "hf.co/yuxinlu1/gemma-4-12B-agentic-fable5-composer2.5-v2-3.5x-tau2-GGUF:Q4_K_M"

MAX_ITER_DEFAULT = 8
REQUEST_TIMEOUT = 300
TEMPERATURE = 0.2

TOOL_SCHEMA_PATH = "from.json"

SYSTEM_PROMPT = """Kamu adalah coding agent otonom untuk project C++/Python di Termux.
Tugasmu: cari file terkait, baca source, edit dengan presisi (pakai replace_in_file,
bukan menulis ulang seluruh file kecuali file baru), simpan, lalu compile.
Jika compile gagal, baca error dari log, cari baris penyebabnya, perbaiki, lalu compile lagi.
Selalu gunakan tool, jangan hanya menjelaskan. Setelah compile sukses atau tugas selesai,
akhiri dengan pesan teks biasa (tanpa tool call) berisi ringkasan singkat.
"""