from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

APP_VERSION = "0.8.0-alpha.1"
HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = Path(r"C:\mycode\Kristal") if os.name == "nt" else Path.home() / "Kristal"
DEFAULT_FRAMEWORK = next((p for p in (DEFAULT_ROOT / "Kristal-Framework", DEFAULT_ROOT / "KristalV10") if p.is_dir()), DEFAULT_ROOT / "Kristal-Framework")


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"Kompiler {APP_VERSION} — optional Kristal context compiler")
        self.geometry("1180x760")
        self.minsize(980, 620)
        self.api_proc: subprocess.Popen[str] | None = None

        self.workspace = tk.StringVar(value=str(DEFAULT_ROOT))
        self.catalog = tk.StringVar(value=str(DEFAULT_ROOT / "kristal-manager.json"))
        self.framework = tk.StringVar(value=str(DEFAULT_FRAMEWORK))
        self.framework_pin = tk.StringVar(value=os.getenv("KOMPILER_KRISTAL_CONTRACT_SET_SHA256", ""))
        self.github_source = tk.StringVar(value="https://github.com/Rejean-McCormick/kristal-public")
        self.github_slug = tk.StringVar(value="")
        self.github_file = tk.StringVar(value="AI_START_HERE.md")
        self.output_path = tk.StringVar(value=str(DEFAULT_ROOT / "context-pack.json"))

        self._build()
        self.after(150, self.refresh_locals)

    def _build(self) -> None:
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")
        ttk.Label(top, text="Kompiler", font=("Segoe UI", 16, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(top, text="Read-only / optional. Manager synchronizes GitHub; Setup publishes/activates.").grid(row=0, column=1, columnspan=4, sticky="w", padx=12)

        for row, (label, var) in enumerate((("Workspace", self.workspace), ("Manager catalog", self.catalog), ("Framework", self.framework)), start=1):
            ttk.Label(top, text=label).grid(row=row, column=0, sticky="w", pady=3)
            ttk.Entry(top, textvariable=var).grid(row=row, column=1, columnspan=3, sticky="ew", padx=6)
            ttk.Button(top, text="Browse", command=lambda v=var: self._browse(v)).grid(row=row, column=4, sticky="e")
        ttk.Label(top, text="Contract-set SHA-256").grid(row=4, column=0, sticky="w", pady=3)
        ttk.Entry(top, textvariable=self.framework_pin).grid(row=4, column=1, columnspan=3, sticky="ew", padx=6)
        ttk.Button(top, text="Inspect / pin local Framework", command=self.pin_framework).grid(row=4, column=4, sticky="e")
        top.columnconfigure(1, weight=1)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        locals_tab = ttk.Frame(nb, padding=8)
        query_tab = ttk.Frame(nb, padding=8)
        runtime_tab = ttk.Frame(nb, padding=8)
        github_tab = ttk.Frame(nb, padding=8)
        nb.add(locals_tab, text="Local Kristals")
        nb.add(github_tab, text="GitHub Collections")
        nb.add(query_tab, text="Context Query")
        nb.add(runtime_tab, text="Runtime")
        self._build_github(github_tab)

        cols = ("title", "kind", "validation", "sync", "publish", "path")
        self.tree = ttk.Treeview(locals_tab, columns=cols, show="headings")
        for c, title, width in (
            ("title", "Kristal", 160), ("kind", "Kind", 80), ("validation", "Validation", 90),
            ("sync", "GitHub Sync", 100), ("publish", "Publication", 90), ("path", "Local path", 520),
        ):
            self.tree.heading(c, text=title)
            self.tree.column(c, width=width, anchor="w")
        self.tree.pack(fill="both", expand=True)
        bar = ttk.Frame(locals_tab)
        bar.pack(fill="x", pady=(8, 0))
        ttk.Button(bar, text="Refresh Manager catalog", command=self.refresh_locals).pack(side="left")
        ttk.Button(bar, text="Discover readable targets", command=self.discover).pack(side="left", padx=6)
        ttk.Label(bar, text="This catalog is discovery only; it is not semantic authority.").pack(side="left", padx=10)

        qbar = ttk.Frame(query_tab)
        qbar.pack(fill="x")
        ttk.Label(qbar, text="Output").pack(side="left")
        ttk.Entry(qbar, textvariable=self.output_path).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(qbar, text="Browse", command=lambda: self._save_browse(self.output_path)).pack(side="left")
        ttk.Button(qbar, text="Run locally", command=self.run_query).pack(side="right", padx=(8, 0))
        self.query = tk.Text(query_tab, wrap="none", font=("Consolas", 10))
        self.query.pack(fill="both", expand=True, pady=(8, 0))
        self.query.insert("1.0", json.dumps({
            "protocol": "kompiler.query",
            "version": "1.1",
            "request_id": "local-session-001",
            "operations": []
        }, indent=2))

        controls = ttk.Frame(runtime_tab)
        controls.pack(fill="x")
        ttk.Button(controls, text="Self-test", command=self.self_test).pack(side="left")
        ttk.Button(controls, text="Start local API", command=self.start_api).pack(side="left", padx=6)
        ttk.Button(controls, text="Stop API", command=self.stop_api).pack(side="left")
        self.log = tk.Text(runtime_tab, wrap="word", font=("Consolas", 9))
        self.log.pack(fill="both", expand=True, pady=(8, 0))

    def _build_github(self, parent: ttk.Frame) -> None:
        for i, (name, var) in enumerate((("Collection URL / local checkout", self.github_source), ("Kristal slug", self.github_slug), ("File", self.github_file))):
            ttk.Label(parent, text=name).grid(row=i, column=0, sticky="w", pady=4)
            ttk.Entry(parent, textvariable=var).grid(row=i, column=1, sticky="ew", padx=8)
        parent.columnconfigure(1, weight=1)
        bar = ttk.Frame(parent)
        bar.grid(row=3, column=0, columnspan=2, sticky="ew", pady=8)
        ttk.Button(bar, text="Browse index", command=lambda: self.github_action("catalog")).pack(side="left")
        ttk.Button(bar, text="Read AI entrypoint", command=lambda: self.github_action("read", entry=True)).pack(side="left", padx=5)
        ttk.Button(bar, text="Read selected file", command=lambda: self.github_action("read")).pack(side="left")
        ttk.Label(parent, text="Read-only. Remote access requires gh auth; no clone or GitHub mutation.").grid(row=4, column=0, columnspan=2, sticky="w")
        self.github_output = tk.Text(parent, wrap="word", font=("Consolas", 9))
        self.github_output.grid(row=5, column=0, columnspan=2, sticky="nsew", pady=(8,0))
        parent.rowconfigure(5, weight=1)

    def github_action(self, command: str, *, entry: bool = False) -> None:
        src = self.github_source.get().strip()
        slug = self.github_slug.get().strip()
        if not src or (command == "read" and not slug):
            messagebox.showerror("GitHub Collection", "Provide a collection URL and, for reading, a Kristal slug.")
            return
        args = ["github", command, src]
        if command == "read":
            args += [slug, "AI_START_HERE.md" if entry else self.github_file.get().strip()]
        self.github_output.delete("1.0", "end")
        self.github_output.insert("end", f"Reading {src} ...\n")
        def worker():
            try:
                result = self._cmd(args)
                assert isinstance(result, subprocess.CompletedProcess)
                txt = (result.stdout or result.stderr or "").strip()
                if result.returncode:
                    txt = "ERROR\n" + txt
            except Exception as exc:
                txt = f"ERROR: {exc}"
            self.after(0, lambda: (self.github_output.delete("1.0", "end"), self.github_output.insert("end", txt)))
        threading.Thread(target=worker, daemon=True).start()

    def _browse(self, var: tk.StringVar) -> None:
        current = Path(var.get())
        if current.suffix.lower() == ".json":
            p = filedialog.askopenfilename(initialdir=str(current.parent), filetypes=[("JSON", "*.json"), ("All", "*.*")])
        else:
            p = filedialog.askdirectory(initialdir=str(current if current.exists() else current.parent))
        if p:
            var.set(p)

    def _save_browse(self, var: tk.StringVar) -> None:
        p = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if p:
            var.set(p)

    def pin_framework(self) -> None:
        import hashlib
        root = Path(self.framework.get())
        path = root / "contracts" / "contract-set.json"
        if not path.is_file():
            messagebox.showerror("Framework", "contracts/contract-set.json not found")
            return
        version = root / "VERSION"
        if not version.is_file():
            messagebox.showerror("Framework", "Framework VERSION not found")
            return
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if messagebox.askyesno("Trust local Framework", f"Version: {version.read_text().strip()}\nSHA-256: {digest}\n\nPin this exact local contract set for this Kompiler session?"):
            self.framework_pin.set(digest)
            self._append("Pinned the selected local Framework contract set (this session only).")

    def _env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(HERE / "src") + os.pathsep + env.get("PYTHONPATH", "")
        env["KOMPILER_KRISTAL_STANDARD_ROOT"] = self.framework.get()
        if self.framework_pin.get().strip():
            env["KOMPILER_KRISTAL_CONTRACT_SET_SHA256"] = self.framework_pin.get().strip()
        env["KOMPILER_KRISTAL_MANAGER_CATALOG"] = self.catalog.get()
        return env

    def _cmd(self, args: list[str], *, wait: bool = True) -> subprocess.CompletedProcess[str] | subprocess.Popen[str]:
        cmd = [sys.executable, "-m", "kompiler", *args]
        kwargs = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW") else {}
        if not wait:
            return subprocess.Popen(cmd, cwd=str(HERE), env=self._env(), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs)
        return subprocess.run(cmd, cwd=str(HERE), env=self._env(), text=True, capture_output=True, **kwargs)

    def _append(self, text: str) -> None:
        self.log.insert("end", text.rstrip() + "\n")
        self.log.see("end")

    def refresh_locals(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        p = Path(self.catalog.get())
        if not p.is_file():
            return
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            for e in data.get("entries", []):
                if not isinstance(e, dict):
                    continue
                self.tree.insert("", "end", values=(
                    e.get("title") or Path(str(e.get("path") or "")).name,
                    e.get("kind") or "",
                    e.get("last_validation_result") or "",
                    "SYNCED" if e.get("last_sync_surface_digest") else ("LEGACY" if e.get("last_sync_repository") else "PENDING"),
                    str(e.get("publication_target") or "").upper(),
                    e.get("path") or "",
                ))
        except Exception as exc:
            messagebox.showerror("Kompiler", f"Cannot read Manager catalog:\n{exc}")

    def _run_async(self, title: str, fn) -> None:
        def work():
            try:
                result = fn()
                self.after(0, lambda: self._append(f"\n== {title} ==\n{result}"))
            except Exception as exc:
                self.after(0, lambda: self._append(f"\nERROR: {exc}"))
        threading.Thread(target=work, daemon=True).start()

    def discover(self) -> None:
        def action():
            p = self._cmd(["locals", "--catalog", self.catalog.get(), "--discover-adapters"])
            assert isinstance(p, subprocess.CompletedProcess)
            return (p.stdout or p.stderr or "").strip()
        self._run_async("Local discovery", action)

    def self_test(self) -> None:
        def action():
            p = self._cmd(["self-test"])
            assert isinstance(p, subprocess.CompletedProcess)
            return (p.stdout or p.stderr or "").strip()
        self._run_async("Self-test", action)

    def run_query(self) -> None:
        try:
            json.loads(self.query.get("1.0", "end"))
        except Exception as exc:
            messagebox.showerror("Kompiler", f"Query JSON is invalid:\n{exc}")
            return
        def action():
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
                f.write(self.query.get("1.0", "end"))
                tmp = f.name
            try:
                p = self._cmd(["run", tmp, "-o", self.output_path.get()])
                assert isinstance(p, subprocess.CompletedProcess)
                if p.returncode:
                    return (p.stdout or p.stderr or "").strip()
                return f"PASS\nContext Pack: {self.output_path.get()}\n" + (p.stdout or "").strip()
            finally:
                try: os.unlink(tmp)
                except OSError: pass
        self._run_async("Context query", action)

    def start_api(self) -> None:
        if self.api_proc and self.api_proc.poll() is None:
            self._append("API already running.")
            return
        proc = self._cmd(["serve"], wait=False)
        assert isinstance(proc, subprocess.Popen)
        self.api_proc = proc
        self._append(f"Started local API (PID {proc.pid}) on 127.0.0.1:7788")
        def drain():
            if proc.stdout:
                for line in proc.stdout:
                    self.after(0, lambda l=line: self._append(l))
        threading.Thread(target=drain, daemon=True).start()

    def stop_api(self) -> None:
        if self.api_proc and self.api_proc.poll() is None:
            self.api_proc.terminate()
            self._append("API stop requested.")
        self.api_proc = None

    def destroy(self) -> None:
        self.stop_api()
        super().destroy()


if __name__ == "__main__":
    App().mainloop()
