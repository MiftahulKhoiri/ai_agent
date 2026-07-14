"""src/tools.py — logika murni semua tools. Tidak tahu apa-apa soal agent/UI/model.
Tambah tool baru di sini: buat fungsi tool_xxx, daftarkan di TOOL_IMPL,
lalu tambahkan skemanya di data/from.json.
"""

import os
import json
import glob
import fnmatch
import subprocess

from data import config


def tool_search_files(root, pattern="*", grep=None, max_results=50):
    """Cari file berdasarkan nama pattern dan/atau isi (grep sederhana)."""
    results = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "build", "node_modules", "__pycache__")]
        for fname in filenames:
            if fnmatch.fnmatch(fname, pattern):
                full = os.path.join(dirpath, fname)
                if grep:
                    try:
                        with open(full, "r", errors="ignore") as f:
                            content = f.read()
                        if grep not in content:
                            continue
                    except Exception:
                        continue
                results.append(full)
                if len(results) >= max_results:
                    return results
    return results


def tool_list_directory(root, max_depth=3):
    """
    Tampilkan struktur folder (mirip `tree`) sampai max_depth level.
    Berguna supaya model/tahu apa saja isi folder tanpa perlu grep.
    """
    if not os.path.isdir(root):
        return f"[ERROR] Folder tidak ditemukan: {root}"

    lines = [root]
    skip_dirs = {".git", "build", "node_modules", "__pycache__"}

    def walk(dir_path, prefix, depth):
        if depth > max_depth:
            return
        try:
            entries = sorted(os.listdir(dir_path))
        except PermissionError:
            lines.append(f"{prefix}[permission denied]")
            return
        entries = [e for e in entries if e not in skip_dirs]
        for i, entry in enumerate(entries):
            full = os.path.join(dir_path, entry)
            is_last = (i == len(entries) - 1)
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{entry}{'/' if os.path.isdir(full) else ''}")
            if os.path.isdir(full):
                extension = "    " if is_last else "│   "
                walk(full, prefix + extension, depth + 1)

    walk(root, "", 1)
    return "\n".join(lines)


def tool_read_file(path, start=1, end=None):
    """Baca isi file, opsional dengan rentang baris."""
    if not os.path.isfile(path):
        return f"[ERROR] File tidak ditemukan: {path}"
    with open(path, "r", errors="ignore") as f:
        lines = f.readlines()
    end = end or len(lines)
    numbered = [f"{i+1}\t{l}" for i, l in enumerate(lines[start-1:end], start=start-1)]
    return "".join(numbered)


def tool_write_file(path, content, mode="overwrite"):
    """Simpan/edit file. mode: overwrite | append."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    flag = "w" if mode == "overwrite" else "a"
    with open(path, flag) as f:
        f.write(content)
    return f"[OK] Tersimpan: {path} ({mode}, {len(content)} bytes)"


def tool_replace_in_file(path, old_str, new_str):
    """Edit presisi: replace satu blok teks unik dalam file."""
    if not os.path.isfile(path):
        return f"[ERROR] File tidak ditemukan: {path}"
    with open(path, "r", errors="ignore") as f:
        content = f.read()
    count = content.count(old_str)
    if count == 0:
        return f"[ERROR] old_str tidak ditemukan di {path}"
    if count > 1:
        return f"[ERROR] old_str muncul {count}x di {path}, harus unik. Perluas konteksnya."
    content = content.replace(old_str, new_str, 1)
    with open(path, "w") as f:
        f.write(content)
    return f"[OK] {path} diedit."


def tool_compile(root):
    """
    Otomatis deteksi cara build:
    - CMakeLists.txt -> cmake + make
    - Makefile -> make
    - fallback -> compile semua .cpp langsung dengan g++
    Return (success: bool, log: str)
    """
    cmake_file = os.path.join(root, "CMakeLists.txt")
    makefile = os.path.join(root, "Makefile")

    if os.path.isfile(cmake_file):
        build_dir = os.path.join(root, "build")
        os.makedirs(build_dir, exist_ok=True)
        cfg = subprocess.run(["cmake", ".."], cwd=build_dir, capture_output=True, text=True)
        if cfg.returncode != 0:
            return False, cfg.stdout + cfg.stderr
        build = subprocess.run(["make", "-j2"], cwd=build_dir, capture_output=True, text=True)
        return build.returncode == 0, build.stdout + build.stderr

    if os.path.isfile(makefile):
        build = subprocess.run(["make"], cwd=root, capture_output=True, text=True)
        return build.returncode == 0, build.stdout + build.stderr

    cpp_files = glob.glob(os.path.join(root, "**", "*.cpp"), recursive=True)
    if not cpp_files:
        return False, "[ERROR] Tidak ada CMakeLists.txt, Makefile, atau file .cpp untuk dicompile."
    out_bin = os.path.join(root, "a.out")
    cmd = ["g++", "-std=c++17", "-O2", "-o", out_bin] + cpp_files
    build = subprocess.run(cmd, capture_output=True, text=True)
    return build.returncode == 0, build.stdout + build.stderr


def tool_run_shell(cmd):
    """Jalankan perintah shell umum (mis. mkdir, ls, python script.py)."""
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
    return f"[exit={r.returncode}]\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"


# ---------------------------------------------------------------------------
# PATH SAFETY GUARD — cegah write_file/replace_in_file menulis di luar root aktif
# ---------------------------------------------------------------------------

def is_within_root(root, target_path):
    """True kalau target_path berada di dalam root (atau sama dengan root)."""
    root_abs = os.path.abspath(root)
    target_abs = os.path.abspath(target_path)
    try:
        return os.path.commonpath([root_abs, target_abs]) == root_abs
    except ValueError:
        # beda drive di Windows, dsb — anggap tidak aman
        return False

def tool_delete_file(path, confirm=False):
    """Hapus file. Wajib confirm=True dari model supaya tidak terjadi tidak sengaja."""
    if not confirm:
        return f"[BLOKIR] Hapus file butuh confirm=true. Path: {path}"
    if not os.path.isfile(path):
        return f"[ERROR] File tidak ditemukan: {path}"
    os.remove(path)
    return f"[OK] File dihapus: {path}"


# ---------------------------------------------------------------------------
# REGISTRY — daftar semua tool. Tambah tool baru cukup daftarkan di sini.
# ---------------------------------------------------------------------------

TOOL_IMPL = {
    "search_files": tool_search_files,
    "list_directory": tool_list_directory,
    "read_file": tool_read_file,
    "write_file": tool_write_file,
    "replace_in_file": tool_replace_in_file,
    "delete_file": tool_delete_file,
    "compile": tool_compile,
    "run_shell": tool_run_shell,
}

# tool yang menulis ke disk — wajib lolos path safety guard
WRITE_TOOLS = {"write_file", "replace_in_file","delete_file"}


def load_tool_schema():
    with open(config.TOOL_SCHEMA_PATH, "r") as f:
        return json.load(f)


def execute_tool_call(tool_call, root=None, allow_outside_root=False):
    """
    Jalankan satu tool_call dari model, return hasil sebagai string.
    root: folder aktif, dipakai untuk guard WRITE_TOOLS.
    allow_outside_root: kalau True, guard dilewati (dipakai user secara sadar).
    """
    name = tool_call["function"]["name"]
    args = tool_call["function"]["arguments"]
    if isinstance(args, str):
        args = json.loads(args)

    if name not in TOOL_IMPL:
        return f"[ERROR] Tool tidak dikenal: {name}"

    if name in WRITE_TOOLS and root and not allow_outside_root:
        target = args.get("path", "")
        if target and not is_within_root(root, target):
            return (f"[BLOKIR] Path '{target}' berada di luar root aktif ({root}). "
                     f"Ganti root dengan /root <path>, atau minta user izinkan akses di luar root.")

    try:
        result = TOOL_IMPL[name](**args)
        if name == "compile":
            ok, log = result
            return f"[compile {'SUKSES' if ok else 'GAGAL'}]\n{log[-4000:]}"
        return str(result)[:6000]
    except Exception as e:
        return f"[ERROR] {name} gagal: {e}"