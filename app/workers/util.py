from __future__ import annotations

import subprocess
from pathlib import Path
import json
import subprocess
from datetime import datetime
from typing import List, Set, Iterable, Dict, Any
from platformdirs import user_config_dir, user_log_dir


def human_readable_size(num_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(num_bytes)
    for unit in units:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def reveal_in_finder(path: Path) -> None:
    try:
        subprocess.run(["open", "-R", str(path)], check=False)
    except Exception:
        pass


# Persistence for excluded folders
APP_NAME = "clean-mac"
CONFIG_FILE = Path(user_config_dir(APP_NAME)) / "settings.json"
LOG_DIR = Path(user_log_dir(APP_NAME))
LOG_FILE = LOG_DIR / "actions.jsonl"


def load_excluded_paths() -> List[Path]:
    try:
        if CONFIG_FILE.exists():
            data = json.loads(CONFIG_FILE.read_text())
            paths = [Path(p) for p in data.get("exclude_paths", [])]
            return [p for p in paths if p.exists()]
    except Exception:
        pass
    return []


def save_excluded_paths(paths: List[Path]) -> None:
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        # Merge with existing config to preserve other fields
        data = {}
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text())
            except Exception:
                data = {}
        data["exclude_paths"] = [str(p) for p in paths]
        CONFIG_FILE.write_text(json.dumps(data, indent=2))
    except Exception:
        pass


def default_dev_ignore_names() -> Set[str]:
    return {
        # JS/TS
        "node_modules", "bower_components", "dist", "build", "coverage", 
        ".next", ".nuxt", ".svelte-kit", ".vite", ".angular", ".storybook", "storybook-static",
        ".turbo", ".nx", ".expo", ".vercel", ".output",
        # Python
        "venv", ".venv", "env", ".env", "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".ipynb_checkpoints",
        # Java/Kotlin/Android
        "target", "out", ".gradle", ".mvn",
        # Swift/iOS
        "DerivedData", ".build", ".swiftpm", "Pods", "Carthage",
        # Go
        "vendor", "bin", "pkg",
        # Rust
        "target",
        # Ruby
        "vendor", ".bundle", "tmp", "log", "coverage", ".yardoc",
        # PHP/Laravel/Symfony
        "vendor", "var", "bootstrap", "storage",
        # .NET
        "bin", "obj", "packages", "TestResults",
        # C/C++/CMake
        "CMakeFiles", ".deps",
        # Haskell
        "dist", "dist-newstyle", ".stack-work",
        # Elixir/Erlang
        "_build", "deps", "cover",
        # Scala/Metals
        "project", ".bloop", ".metals",
        # Monorepo tools
        "bazel-bin", "bazel-out", "buck-out",
        # VCS
        ".git", ".hg", ".svn",
    }


# Presets persistence (age/size/dev toggle)
def load_presets() -> dict:
    try:
        if CONFIG_FILE.exists():
            return json.loads(CONFIG_FILE.read_text())
    except Exception:
        pass
    return {}


def save_presets(presets: dict) -> None:
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text())
            except Exception:
                data = {}
        data.update(presets)
        CONFIG_FILE.write_text(json.dumps(data, indent=2))
    except Exception:
        pass


# Quick Look preview and Finder helpers
def quick_look_preview(paths: Iterable[Path]) -> None:
    try:
        for p in paths:
            # Launch preview without blocking the UI
            subprocess.Popen(["qlmanage", "-p", str(p)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def open_trash() -> None:
    try:
        trash = Path.home() / ".Trash"
        subprocess.run(["open", str(trash)], check=False)
    except Exception:
        pass


# Action logging
def append_action_log(action: str, items: List[Dict[str, Any]], total_size: int) -> None:
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "action": action,
            "count": len(items),
            "total_size": total_size,
            "items": items[:20],  # cap to keep lines reasonable
        }
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass
