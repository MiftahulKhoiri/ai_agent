"""agent.py — implementasi tools + loop agent"""

import os
import json
import glob
import fnmatch
import subprocess
import requests

from data config import config

# ---------------------------------------------------------------------------
# TOOLS — implementasi aktual (dijalankan lokal, bukan oleh model)
# ---------------------------------------------------------------------------

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


TOOL_IMPL = {
    "search_files": tool_search_files,
    "read_file": tool_read_file,
    "write_file": tool_write_file,
    "replace_in_file": tool_replace_in_file,
    "compile": tool_compile,
    "run_shell": tool_run_shell,
}


def load_tool_schema():
    with open(config.TOOL_SCHEMA_PATH, "r") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# MODEL CALL + AGENT LOOP
# ---------------------------------------------------------------------------

def call_model(messages, tool_schema):
    resp = requests.post(config.OLLAMA_URL, json={
        "model": config.MODEL,
        "messages": messages,
        "tools": tool_schema,
        "stream": False,
        "options": {"temperature": config.TEMPERATURE},
    }, timeout=config.REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()["message"]


def execute_tool_call(tool_call):
    name = tool_call["function"]["name"]
    args = tool_call["function"]["arguments"]
    if isinstance(args, str):
        args = json.loads(args)
    if name not in TOOL_IMPL:
        return f"[ERROR] Tool tidak dikenal: {name}"
    try:
        result = TOOL_IMPL[name](**args)
        if name == "compile":
            ok, log = result
            return f"[compile {'SUKSES' if ok else 'GAGAL'}]\n{log[-4000:]}"
        return str(result)[:6000]
    except Exception as e:
        return f"[ERROR] {name} gagal: {e}"


def run_agent(task, root, max_iter=None):
    max_iter = max_iter or config.MAX_ITER_DEFAULT
    tool_schema = load_tool_schema()

    messages = [
        {"role": "system", "content": config.SYSTEM_PROMPT},
        {"role": "user", "content": f"Root project: {root}\nTugas: {task}"},
    ]

    for step in range(1, max_iter + 1):
        print(f"\n=== Iterasi {step} ===")
        msg = call_model(messages, tool_schema)
        messages.append(msg)

        tool_calls = msg.get("tool_calls")
        if not tool_calls:
            print("[AGENT]", msg.get("content", ""))
            return

        for tc in tool_calls:
            fname = tc["function"]["name"]
            print(f"-> memanggil tool: {fname}({tc['function']['arguments']})")
            result = execute_tool_call(tc)
            print(result[:800])
            messages.append({"role": "tool", "content": result})

    print("\n[STOP] Batas iterasi tercapai tanpa penyelesaian eksplisit dari model.")