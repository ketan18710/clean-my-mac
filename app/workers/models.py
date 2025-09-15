from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional


@dataclass
class FileItem:
    path: Path
    display_name: str
    size_bytes: int
    last_used_at: Optional[datetime]
    last_modified_at: datetime
    content_type: str
    type_group: str  # image | video | doc | archive | other

    @property
    def last_used_or_modified_str(self) -> str:
        dt = self.last_used_at or self.last_modified_at
        return dt.strftime("%Y-%m-%d %H:%M")


@dataclass
class ScanConfig:
    roots: List[Path]
    min_age_days: int
    min_size_bytes: int
    exclude_paths: List[Path]
    ignore_dev_preset: bool
