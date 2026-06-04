#!/usr/bin/env python3
"""Small macOS-friendly GUI for FCP Shotcut."""

from __future__ import annotations

import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


SCRIPT_DIR = Path(__file__).resolve().parent
CLI = SCRIPT_DIR / "fcp_shotcut.py"


class FcpShotcutApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("FCP Shotcut")
        self.geometry("720x560")
        self.minsize(680, 520)

        self.folder_var = tk.StringVar()
        self.project_var = tk.StringVar()
        self.event_var = tk.StringVar(value="4-16-26")
        self.threshold_var = tk.DoubleVar(value=0.35)
        self.min_len_var = tk.DoubleVar(value=0.35)
        self.previews_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Choose a folder with MP4/MOV/M4V videos.")
        self.output_dir: Path | None = None
        self.log_queue: queue.Queue[str | None] = queue.Queue()
        self.worker: threading.Thread | None = None

        self._build_ui()
        self.after(100, self._pump_logs)

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=18)
        root.pack(fill="both", expand=True)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(8, weight=1)

        ttk.Label(root, text="FCP Shotcut", font=("Helvetica", 22, "bold")).grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(
            root,
            text="Vertical 1080x1920 / 30p / Apple ProRes 422 / Rec.709 / Stereo 48kHz",
            foreground="#555",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(2, 18))

        ttk.Label(root, text="Video folder").grid(row=2, column=0, sticky="w", pady=6)
        ttk.Entry(root, textvariable=self.folder_var).grid(row=2, column=1, sticky="ew", pady=6, padx=(8, 8))
        ttk.Button(root, text="Choose...", command=self.choose_folder).grid(row=2, column=2, pady=6)

        ttk.Label(root, text="Project name").grid(row=3, column=0, sticky="w", pady=6)
        ttk.Entry(root, textvariable=self.project_var).grid(row=3, column=1, columnspan=2, sticky="ew", pady=6, padx=(8, 0))

        ttk.Label(root, text="Event name").grid(row=4, column=0, sticky="w", pady=6)
        ttk.Entry(root, textvariable=self.event_var, width=20).grid(row=4, column=1, sticky="w", pady=6, padx=(8, 0))

        ttk.Label(root, text="Scene sensitivity").grid(row=5, column=0, sticky="w", pady=6)
        scale = ttk.Scale(root, from_=0.15, to=0.65, variable=self.threshold_var, orient="horizontal")
        scale.grid(row=5, column=1, sticky="ew", pady=6, padx=(8, 8))
        ttk.Label(root, textvariable=self.threshold_var, width=5).grid(row=5, column=2, sticky="w", pady=6)

        ttk.Label(root, text="Minimum shot").grid(row=6, column=0, sticky="w", pady=6)
        ttk.Spinbox(root, textvariable=self.min_len_var, from_=0.1, to=2.0, increment=0.05, width=8).grid(
            row=6, column=1, sticky="w", pady=6, padx=(8, 0)
        )
        ttk.Checkbutton(root, text="Generate cut preview images", variable=self.previews_var).grid(
            row=6, column=1, sticky="w", pady=6, padx=(110, 0)
        )

        buttons = ttk.Frame(root)
        buttons.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(14, 8))
        self.generate_button = ttk.Button(buttons, text="Generate Final Cut Pro XML", command=self.generate)
        self.generate_button.pack(side="left")
        self.finder_button = ttk.Button(buttons, text="Show in Finder", command=self.show_in_finder, state="disabled")
        self.finder_button.pack(side="left", padx=(10, 0))
        ttk.Label(buttons, textvariable=self.status_var, foreground="#555").pack(side="left", padx=(14, 0))

        self.log = tk.Text(root, height=12, wrap="word")
        self.log.grid(row=8, column=0, columnspan=3, sticky="nsew")
        self.log.insert("end", "Ready.\n")
        self.log.configure(state="disabled")

    def choose_folder(self) -> None:
        folder = filedialog.askdirectory(title="Choose a folder with videos")
        if folder:
            self.folder_var.set(folder)

    def generate(self) -> None:
        folder = Path(self.folder_var.get()).expanduser()
        if not folder.is_dir():
            messagebox.showerror("FCP Shotcut", "Please choose a valid video folder.")
            return

        self.output_dir = folder / "edit"
        self.finder_button.configure(state="disabled")
        self.generate_button.configure(state="disabled")
        self.status_var.set("Generating...")
        self._clear_log()

        cmd = [
            sys.executable,
            str(CLI),
            str(folder),
            "--event-name",
            self.event_var.get().strip() or "4-16-26",
            "--threshold",
            f"{self.threshold_var.get():.3f}",
            "--min-shot-len",
            f"{self.min_len_var.get():.3f}",
        ]
        project_name = self.project_var.get().strip()
        if project_name:
            cmd.extend(["--project-name", project_name])
        if not self.previews_var.get():
            cmd.append("--no-previews")

        self.worker = threading.Thread(target=self._run_command, args=(cmd,), daemon=True)
        self.worker.start()

    def _run_command(self, cmd: list[str]) -> None:
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            assert proc.stdout is not None
            for line in proc.stdout:
                self.log_queue.put(line)
            rc = proc.wait()
            self.log_queue.put(f"\nFinished with exit code {rc}.\n")
            self.log_queue.put(None if rc == 0 else "__FAILED__")
        except Exception as exc:
            self.log_queue.put(f"\nError: {exc}\n")
            self.log_queue.put("__FAILED__")

    def _pump_logs(self) -> None:
        try:
            while True:
                item = self.log_queue.get_nowait()
                if item is None:
                    self.generate_button.configure(state="normal")
                    self.finder_button.configure(state="normal")
                    self.status_var.set("Done. Import edit/timeline.fcpxml in Final Cut Pro.")
                elif item == "__FAILED__":
                    self.generate_button.configure(state="normal")
                    self.status_var.set("Failed. Check the log.")
                    messagebox.showerror("FCP Shotcut", "Generation failed. Check the log in the window.")
                else:
                    self._append_log(item)
        except queue.Empty:
            pass
        self.after(100, self._pump_logs)

    def _append_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def show_in_finder(self) -> None:
        target = self.output_dir if self.output_dir and self.output_dir.exists() else Path(self.folder_var.get()).expanduser()
        subprocess.run(["open", str(target)], check=False)


def main() -> int:
    app = FcpShotcutApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
