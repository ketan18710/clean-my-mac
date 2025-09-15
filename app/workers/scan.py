from __future__ import annotations

import queue
import subprocess
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Iterable, Optional

from .models import FileItem, ScanConfig
from .util import default_dev_ignore_names


SAFE_SYSTEM_PREFIXES = (
    "/System",
    "/Library",
    "/Applications",
    "/usr",
    "/bin",
    "/sbin",
    "/opt",
)

BUNDLE_SUFFIXES = (
    ".app",
    ".framework",
    ".photoslibrary",
    ".aplibrary",
    ".appbundle",
    ".kext",
)


class ScanController:
    def __init__(self, on_result: Callable[[FileItem], None], on_done: Callable[[], None]):
        self.on_result = on_result
        self.on_done = on_done
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start_scan(self, config: ScanConfig) -> None:
        self.stop()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_scan, args=(config,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.2)

    def _run_scan(self, config: ScanConfig) -> None:
        cutoff = datetime.now().replace(tzinfo=None) - timedelta(days=config.min_age_days)
        q: queue.Queue[Optional[Path]] = queue.Queue(maxsize=1000)

        def producer() -> None:
            try:
                for root in config.roots:
                    if self._stop_event.is_set():
                        break
                    for path in spotlight_discover(root, self._stop_event):
                        if self._stop_event.is_set():
                            break
                        skip_for_dev = should_skip_dev(path) if config.ignore_dev_preset else False
                        if skip_for_dev or should_skip(path) or is_excluded(path, config.exclude_paths):
                            continue
                        q.put(path)
            finally:
                q.put(None)

        def consumer() -> None:
            try:
                while True:
                    path = q.get()
                    if path is None or self._stop_event.is_set():
                        break
                    item = build_file_item(path)
                    if item is None:
                        continue
                    # Filters
                    last_dt = item.last_used_at or item.last_modified_at
                    if last_dt.tzinfo is not None:
                        last_dt = last_dt.astimezone().replace(tzinfo=None)
                    if last_dt > cutoff:
                        continue
                    # Apply size threshold to non-images, but always include PDFs regardless of size
                    is_pdf = ("pdf" in (item.content_type or "").lower()) or item.path.suffix.lower() == ".pdf"
                    if (item.type_group != "image" and not is_pdf) and item.size_bytes < config.min_size_bytes:
                        continue
                    self.on_result(item)
            finally:
                self.on_done()

        t_prod = threading.Thread(target=producer, daemon=True)
        t_cons = threading.Thread(target=consumer, daemon=True)
        t_prod.start()
        t_cons.start()
        t_prod.join()
        t_cons.join()


def spotlight_discover(root: Path, stop_event: threading.Event) -> Iterable[Path]:
    # Include images, videos, archives, and common document types (PDF/contents)
    query = (
        "(kMDItemContentTypeTree == \"public.image\" || "
        "kMDItemContentTypeTree == \"public.movie\" || "
        "kMDItemContentTypeTree == \"public.archive\" || "
        "kMDItemContentTypeTree == \"com.adobe.pdf\" || "
        "kMDItemContentTypeTree == \"public.content\")"
    )
    proc: Optional[subprocess.Popen[str]] = None
    try:
        proc = subprocess.Popen(
            ["mdfind", "-onlyin", str(root), query],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            if stop_event.is_set():
                break
            p = Path(line.strip())
            if p.exists():
                yield p
    finally:
        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass
            try:
                proc.wait(timeout=0.5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass


def should_skip(path: Path) -> bool:
    s = str(path)
    if s.startswith(SAFE_SYSTEM_PREFIXES):
        return True
    if any(part.endswith(BUNDLE_SUFFIXES) for part in path.parts):
        return True
    if any(part.startswith(".") for part in path.parts):
        return True
    return False


def should_skip_dev(path: Path) -> bool:
    dev_names = default_dev_ignore_names()
    return any(part in dev_names for part in path.parts)


def is_excluded(path: Path, exclude_paths: list[Path]) -> bool:
    try:
        for base in exclude_paths:
            try:
                # If path is the base or inside it
                if Path(path).resolve().is_relative_to(Path(base).resolve()):
                    return True
            except Exception:
                # Fallback for Python <3.9 on mac: manual prefix check
                ps, bs = str(path), str(base)
                if ps == bs or ps.startswith(bs.rstrip("/") + "/"):
                    return True
        return False
    except Exception:
        return False


def mdls_value(path: Path, name: str) -> Optional[str]:
    try:
        out = subprocess.check_output(
            ["mdls", "-raw", "-name", name, str(path)],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        if out == "(null)":
            return None
        return out
    except Exception:
        return None


def parse_mdls_datetime(value: str) -> Optional[datetime]:
    v = value.strip()
    try:
        if "+" in v and v.endswith("0000") and "T" not in v:
            date_part, time_part, offset = v.split()
            v_iso = f"{date_part}T{time_part}{offset[:3]}:{offset[3:]}"
            dt = datetime.fromisoformat(v_iso)
        else:
            dt = datetime.fromisoformat(v)
        return dt
    except Exception:
        return None


def build_file_item(path: Path) -> Optional[FileItem]:
    try:
        size_raw = mdls_value(path, "kMDItemFSSize")
        size_bytes = int(size_raw) if size_raw else path.stat().st_size
        last_used_raw = mdls_value(path, "kMDItemLastUsedDate")
        last_used_at = None
        if last_used_raw:
            parsed = parse_mdls_datetime(last_used_raw)
            if parsed:
                last_used_at = parsed.astimezone().replace(tzinfo=None)
        last_modified_at = datetime.fromtimestamp(path.stat().st_mtime).replace(tzinfo=None)
        content_type = (mdls_value(path, "kMDItemContentType") or "public.data").lower()
        type_group = infer_group_from_uti(path, content_type)
        return FileItem(
            path=path,
            display_name=path.name,
            size_bytes=size_bytes,
            last_used_at=last_used_at,
            last_modified_at=last_modified_at,
            content_type=content_type,
            type_group=type_group,
        )
    except Exception:
        return None


def infer_group_from_uti(path: Path, uti: str) -> str:
    uti_l = (uti or "").lower()
    ext = path.suffix.lower()
    if "public.image" in uti_l or ext in {".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff", ".heic", ".heif", ".webp", ".bmp", ".raw"}:
        return "image"
    if "public.movie" in uti_l or ext in {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".hevc"}:
        return "video"
    if "archive" in uti_l or ext in {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".dmg", ".iso"}:
        return "archive"
    if "pdf" in uti_l or ext == ".pdf" or "public.content" in uti_l:
        return "other"
    return "other"
