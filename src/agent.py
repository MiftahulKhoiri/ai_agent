"""src/agent.py — penghubung: model call + loop tahapan + UI.
Logika tool ada di tools.py, tampilan proses ada di ui.py.
"""

import json
import os
import requests

from data import config
from . import tools
from . import ui


class Agent:
    def __init__(self, root, allow_outside_root=False):
        self.root = os.path.abspath(root)
        self.allow_outside_root = allow_outside_root
        self.tool_schema = tools.load_tool_schema()
        self.messages = [
            {"role": "system", "content": config.SYSTEM_PROMPT},
            {"role": "user", "content": f"Root project aktif: {self.root}"},
        ]

    def set_root(self, root):
        self.root = os.path.abspath(root)
        self.messages.append({"role": "user", "content": f"Root project diganti ke: {self.root}"})

    def toggle_outside_root(self, allow):
        self.allow_outside_root = allow

    def reset(self):
        self.messages = [
            {"role": "system", "content": config.SYSTEM_PROMPT},
            {"role": "user", "content": f"Root project aktif: {self.root}"},
        ]

    def _call_model(self):
        """
        Panggil model dengan stream=True supaya token muncul langsung
        (seperti `ollama run` biasa) — tidak terlihat macet saat menunggu.
        Mengembalikan message dict yang sama formatnya seperti mode non-stream,
        supaya sisa kode (send/_dispatch) tidak perlu berubah.
        """
        resp = requests.post(config.OLLAMA_URL, json={
            "model": config.MODEL,
            "messages": self.messages,
            "tools": self.tool_schema,
            "stream": True,
            "options": {
                "temperature": config.TEMPERATURE,
                "num_thread": getattr(config, "NUM_THREAD", 4),
            },
        }, timeout=config.REQUEST_TIMEOUT, stream=True)
        resp.raise_for_status()

        ui.stage("think")
        print("   ", end="", flush=True)

        full_content = ""
        tool_calls = None
        printed_anything = False

        for line in resp.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            piece = chunk.get("message", {})

            piece_content = piece.get("content", "")
            if piece_content:
                print(piece_content, end="", flush=True)
                full_content += piece_content
                printed_anything = True

            if piece.get("tool_calls"):
                tool_calls = piece["tool_calls"]

            if chunk.get("done"):
                break

        if printed_anything:
            print()  # newline setelah streaming selesai

        message = {"role": "assistant", "content": full_content}
        if tool_calls:
            message["tool_calls"] = tool_calls
        return message

    def _dispatch(self, tool_call):
        """Pilih tampilan tahap yang sesuai berdasarkan nama tool, lalu eksekusi."""
        fname = tool_call["function"]["name"]
        args = tool_call["function"]["arguments"]
        if isinstance(args, str):
            args = json.loads(args)

        if fname in ("write_file", "replace_in_file"):
            ui.stage("code", args.get("path", ""))
            result = tools.execute_tool_call(tool_call, root=self.root,
                                              allow_outside_root=self.allow_outside_root)
            if result.startswith("[BLOKIR]"):
                ui.stage("error", "path di luar root")
            return result, args.get("path")

        if fname == "list_directory":
            ui.stage("search", f"struktur folder {args.get('root', '')}")
            result = tools.execute_tool_call(tool_call, root=self.root)
            return result, None

        if fname == "search_files":
            ui.stage("search", args.get("root", ""))
            result = tools.execute_tool_call(tool_call, root=self.root)
            return result, None

        if fname == "read_file":
            ui.stage("search", args.get("path", ""))
            result = tools.execute_tool_call(tool_call, root=self.root)
            return result, None

        if fname == "delete_file":
            ui.stage("delete", args.get("path", ""))
            result = tools.execute_tool_call(tool_call, root=self.root,
                                              allow_outside_root=self.allow_outside_root)
            if result.startswith("[BLOKIR]"):
                ui.stage("error", "hapus diblokir")
            return result, None

        if fname == "compile":
            with ui.Spinner("Compile & testing"):
                result = tools.execute_tool_call(tool_call, root=self.root)
            if "GAGAL" in result:
                print(result[:600])
                ui.stage("debug")
            else:
                print("   Compile sukses.")
            return result, None

        if fname == "run_shell":
            ui.stage("shell", args.get("cmd", "")[:60])
            with ui.Spinner("Menjalankan"):
                result = tools.execute_tool_call(tool_call, root=self.root)
            return result, None

        ui.stage("shell", fname)
        result = tools.execute_tool_call(tool_call, root=self.root)
        return result, None

    def send(self, user_text, max_iter=None):
        """
        Kirim satu pesan user, jalankan loop tool dengan tahapan terlihat
        (termasuk streaming teks berpikir model secara live) sampai model
        memberi jawaban teks akhir.
        Return: (reply_text, set_file_yang_diubah)
        """
        max_iter = max_iter or config.MAX_ITER_DEFAULT
        self.messages.append({"role": "user", "content": user_text})
        touched_files = set()

        for step in range(1, max_iter + 1):
            msg = self._call_model()  # sudah print stage("think") + stream isi di dalamnya
            self.messages.append(msg)

            tool_calls = msg.get("tool_calls")
            if not tool_calls:
                ui.stage("result")
                return msg.get("content", ""), touched_files

            for tc in tool_calls:
                result, touched_path = self._dispatch(tc)
                if touched_path:
                    touched_files.add(touched_path)
                self.messages.append({"role": "tool", "content": result})

        ui.stage("error", "batas iterasi tercapai")
        return "[STOP] Batas iterasi tercapai tanpa jawaban akhir dari model.", touched_files