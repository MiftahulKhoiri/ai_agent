# AI Agent — Coding Assistant Lokal (Ollama)

Coding agent otonom yang jalan lokal via Ollama, bisa cari file, baca source,
edit, simpan, compile, dan otomatis memperbaiki error compile — semua lewat
chat interaktif di terminal.

**Model:** `hf.co/yuxinlu1/gemma-4-12B-agentic-fable5-composer2.5-v2-3.5x-tau2-GGUF:Q4_K_M`

---

## Struktur Folder

```
ai_agent/
├── main.py              # entrypoint chatbot interaktif
├── data/
│   ├── __init__.py
│   ├── config.py         # konfigurasi (model, system prompt, dll)
│   └── from.json         # skema tool untuk model (function calling)
└── src/
    ├── __init__.py
    ├── tools.py           # logika murni semua tools (search, read, write, compile, dll)
    ├── agent.py           # penghubung: model call + loop tahapan + UI
    └── ui.py              # tampilan tahapan proses (berpikir/kode/compile/dll)
```

---

## 1. Setup Awal (sekali saja)

### Install Ollama & pull model
```bash
# install Ollama (kalau belum ada)
curl -fsSL https://ollama.com/install.sh | sh

# jalankan server Ollama di background
ollama serve &

# cek model sudah ada atau belum
ollama list

# kalau belum ada, pull dulu
ollama pull hf.co/yuxinlu1/gemma-4-12B-agentic-fable5-composer2.5-v2-3.5x-tau2-GGUF:Q4_K_M
```

### Install dependency Python
```bash
pip install requests --break-system-packages
```

### (Opsional) Toolchain bahasa lain
Agent bisa compile/syntax-check C++, C, Python, JS, Java, Go, Rust — pasang
sesuai kebutuhan:
```bash
sudo apt update
sudo apt install build-essential python3 -y     # g++, gcc, make, python3 (wajib minimal)
sudo apt install default-jdk golang-go nodejs -y # opsional: Java, Go, Node
curl https://sh.rustup.rs -sSf | sh              # opsional: Rust/cargo
```

---

## 2. Cek Struktur Sudah Lengkap

```bash
cd ai_agent
ls -R
```
Pastikan ada: `main.py`, `data/__init__.py`, `data/config.py`, `data/from.json`,
`src/__init__.py`, `src/tools.py`, `src/agent.py`, `src/ui.py`.

---

## 3. Menjalankan Agent

Siapkan folder project (bisa folder baru kosong atau project yang sudah ada):
```bash
mkdir -p ~/code
```

Jalankan:
```bash
python3 main.py --root ~/code
```

Kalau berhasil, akan muncul:
```
AI Agent siap. Root: /home/xxx/code
Ketik /help untuk daftar perintah, /exit untuk keluar.

kamu>
```

**Argumen CLI:**
| Argumen | Default | Keterangan |
|---|---|---|
| `--root` | `.` | Folder project aktif tempat agent bekerja |
| `--max-iter` | `8` | Batas iterasi loop berpikir→tool→berpikir per satu perintah |

---

## 4. Perintah di Dalam Chat

| Perintah | Fungsi |
|---|---|
| `/help` | Tampilkan daftar perintah |
| `/root <path>` | Ganti folder project aktif |
| `/ls [path]` | Tampilkan struktur folder langsung (tanpa lewat model) |
| `/allow-outside on` | Izinkan agent menulis/hapus file di luar root aktif |
| `/allow-outside off` | Kembali batasi ke root aktif (default) |
| `/reset` | Hapus histori percakapan, mulai sesi baru |
| `/exit` | Keluar dari program |

Selain perintah di atas, ketik pesan biasa untuk memberi tugas ke agent.

---

## 5. Contoh Pemakaian

```
kamu> buatkan aku script kalkulator.py sederhana dengan operasi tambah kurang kali bagi
```

Proses yang akan terlihat:
```
🤔 Berpikir
✍️  Menulis kode — kalkulator.py
🤔 Berpikir
⚙️  Compile & testing...
   Compile sukses.
🤔 Berpikir
✅ Hasil

agent> Ringkasan: membuat kalkulator.py dengan operasi dasar...
Deskripsi: fungsi calculate(a, op, b) menangani +,-,*,/ dan pembagian nol...
Cara pakai: jalankan `python3 kalkulator.py` lalu ikuti prompt input...

📁 File yang diubah/dibuat:
   - kalkulator.py
```

Kalau compile gagal, otomatis lanjut ke tahap `🐛 Debugging` → perbaiki →
compile ulang, sampai sukses atau `--max-iter` habis.

Contoh lain:
```
kamu> perbaiki bug null pointer di layers.cpp
kamu> /root ~/MiniGPT/src
kamu> tambahkan fungsi save_checkpoint di checkpoint.cpp
kamu> hapus file debug_temp.py yang sudah tidak dipakai
kamu> /ls
kamu> /reset
kamu> /exit
```

---

## 6. Tools yang Dimiliki Agent

| Tool | Fungsi |
|---|---|
| `search_files` | Cari file berdasarkan nama pattern dan/atau isi teks |
| `list_directory` | Tampilkan struktur folder (seperti `tree`) |
| `read_file` | Baca isi file (seluruh atau rentang baris) |
| `write_file` | Buat file baru / timpa / append |
| `replace_in_file` | Edit presisi: ganti satu blok teks unik |
| `delete_file` | Hapus file (wajib konfirmasi, dilindungi guard folder) |
| `compile` | Auto-deteksi bahasa & compile/syntax-check (C++, C, Python, JS, Java, Go, Rust) |
| `run_shell` | Jalankan perintah shell arbitrer |

---

## 7. Keamanan (Path Safety Guard)

`write_file`, `replace_in_file`, dan `delete_file` otomatis diblokir kalau
targetnya di luar folder `--root` aktif — mencegah agent mengubah/menghapus
file di luar project yang sedang dikerjakan. Untuk override sementara:
```
kamu> /allow-outside on
```
Ingat kembalikan ke `off` setelah selesai kalau tidak dibutuhkan terus-menerus.

**Catatan:** `run_shell` **tidak** dibatasi guard ini — perintah shell bisa
menyentuh apa pun sesuai permission user yang menjalankan `main.py`. Hati-hati
kalau menjalankan dengan `sudo`.

---

## 8. Troubleshooting

| Masalah | Solusi |
|---|---|
| `[ERROR] Ollama server belum jalan` | Jalankan `ollama serve &` dulu |
| `ModuleNotFoundError: requests` | `pip install requests --break-system-packages` |
| Model tidak pernah memanggil tool (cuma jawab teks) | Cek manual `ollama run <model>` apakah model ini dukung tool-calling |
| `replace_in_file` gagal "muncul lebih dari 1x" | Wajar — model perlu perluas konteks `old_str`, biasanya retry otomatis |
| Compile gagal "perintah tidak ditemukan" | Pasang toolchain terkait (lihat bagian Setup Awal) |
| `[BLOKIR] Path di luar root` | Gunakan `/root <path>` untuk pindah, atau `/allow-outside on` |