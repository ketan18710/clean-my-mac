from __future__ import annotations

import queue
from pathlib import Path
from typing import List, Dict

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QPushButton,
    QFileDialog,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QCheckBox,
    QMessageBox,
    QProgressBar,
    QComboBox,
    QGroupBox,
)
from PySide6.QtGui import QIcon, QPixmap

from send2trash import send2trash

from app.workers.scan import ScanController
from app.workers.models import FileItem, ScanConfig
from app.workers.util import (
    human_readable_size,
    reveal_in_finder,
    load_excluded_paths,
    save_excluded_paths,
    load_presets,
    save_presets,
    quick_look_preview,
    open_trash,
    append_action_log,
)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Clean my Mac")
        self.resize(1100, 720)

        # UI State
        self.selected_roots: List[Path] = self._default_roots()
        presets = load_presets()
        self.min_age_days: int = int(presets.get("min_age_days", 180))
        self.min_size_bytes: int = int(presets.get("min_size_bytes", 50 * 1024 * 1024))
        self.items_by_path: Dict[Path, FileItem] = {}
        self._result_queue: "queue.Queue[FileItem]" = queue.Queue()
        self._scan_done: bool = False
        self.excluded_paths: List[Path] = load_excluded_paths()
        self.last_trashed_paths: List[Path] = []

        # Central widget
        central = QWidget(self)
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)

        # Filter panel (modern grouped, spacious)
        filters_group = QGroupBox("Scan Filters", self)
        filters_group.setStyleSheet(
            "QGroupBox { font-weight: 600; border: 1px solid #444; border-radius: 8px; margin-top: 12px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }"
        )
        filters_layout = QGridLayout(filters_group)
        filters_layout.setContentsMargins(12, 12, 12, 12)
        filters_layout.setHorizontalSpacing(16)
        filters_layout.setVerticalSpacing(10)

        self.roots_label = QLabel(", ".join(str(p) for p in self.selected_roots), self)
        self.roots_label.setWordWrap(True)
        btn_choose_roots = QPushButton("Choose Roots")
        btn_choose_roots.clicked.connect(self._choose_roots)

        self.excludes_label = QLabel(self._format_excludes(), self)
        self.excludes_label.setWordWrap(True)
        btn_add_exclude = QPushButton("Add Exclude")
        btn_add_exclude.clicked.connect(self._add_exclude)
        btn_clear_excludes = QPushButton("Clear")
        btn_clear_excludes.clicked.connect(self._clear_excludes)

        self.age_input = QLineEdit(str(self.min_age_days))
        self.age_input.setFixedWidth(100)

        self.size_dropdown = QComboBox(self)
        self.size_dropdown.addItems(["50 MB", "200 MB", "1 GB", "Custom…"])
        self.size_dropdown.currentIndexChanged.connect(self._on_size_preset)
        self.size_input = QLineEdit(str(self.min_size_bytes))
        self.size_input.setFixedWidth(160)
        # Hide custom input by default; will be toggled after init
        self.size_input.setVisible(False)
        self.size_input.setEnabled(False)

        self.dry_run_checkbox = QCheckBox("Dry Run")
        self.dry_run_checkbox.setChecked(False)
        self.dev_ignore_checkbox = QCheckBox("Ignore dev folders preset")
        self.dev_ignore_checkbox.setChecked(bool(load_presets().get("ignore_dev_preset", True)))

        btn_scan = QPushButton("Scan")
        btn_scan.setFixedWidth(120)
        btn_scan.clicked.connect(self._start_scan)

        # Row 0 — Roots (spans)
        filters_layout.addWidget(QLabel("Roots:"), 0, 0)
        filters_layout.addWidget(self.roots_label, 0, 1, 1, 6)
        filters_layout.addWidget(btn_choose_roots, 0, 7)

        # Row 1 — Exclusions
        filters_layout.addWidget(QLabel("Exclude folders:"), 1, 0)
        filters_layout.addWidget(self.excludes_label, 1, 1, 1, 5)
        filters_layout.addWidget(btn_add_exclude, 1, 6)
        filters_layout.addWidget(btn_clear_excludes, 1, 7)

        # Row 2 — Filters
        filters_layout.addWidget(QLabel("Min age (days):"), 2, 0)
        filters_layout.addWidget(self.age_input, 2, 1)
        filters_layout.addWidget(QLabel("Min size:"), 2, 2)
        filters_layout.addWidget(self.size_dropdown, 2, 3)
        filters_layout.addWidget(self.size_input, 2, 4)
        filters_layout.addWidget(self.dev_ignore_checkbox, 2, 5)
        filters_layout.addWidget(self.dry_run_checkbox, 2, 6)
        filters_layout.addWidget(btn_scan, 2, 7, 1, 1, Qt.AlignRight)

        # Row 3 — Type filters
        self.type_image_cb = QCheckBox("Images")
        self.type_video_cb = QCheckBox("Videos")
        self.type_archive_cb = QCheckBox("Archives")
        self.type_other_cb = QCheckBox("Others")
        for cb in (self.type_image_cb, self.type_video_cb, self.type_archive_cb, self.type_other_cb):
            cb.setChecked(True)
            cb.toggled.connect(self._apply_type_filter)
        filters_layout.addWidget(QLabel("Show types:"), 3, 0)
        filters_layout.addWidget(self.type_image_cb, 3, 1)
        filters_layout.addWidget(self.type_video_cb, 3, 2)
        filters_layout.addWidget(self.type_archive_cb, 3, 3)
        filters_layout.addWidget(self.type_other_cb, 3, 4)

        # Column stretch to breathe
        filters_layout.setColumnStretch(1, 5)
        filters_layout.setColumnStretch(3, 2)
        filters_layout.setColumnStretch(4, 2)
        filters_layout.setColumnStretch(5, 2)
        filters_layout.setColumnStretch(6, 1)
        filters_layout.setColumnStretch(7, 1)

        root_layout.addWidget(filters_group)
        # Initialize presets-driven UI state and persistence hooks
        self._init_size_preset_from_value(self.min_size_bytes)
        self.age_input.editingFinished.connect(self._save_current_presets)
        self.size_input.editingFinished.connect(self._save_current_presets)
        self.dev_ignore_checkbox.toggled.connect(self._save_current_presets)

        # Status bar: loader + status text + stop
        status_row = QHBoxLayout()
        status_row.setSpacing(10)
        self.progress = QProgressBar(self)
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.status_text = QLabel("Idle")
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setVisible(False)
        self.btn_stop.clicked.connect(self._stop_scan)
        status_row.addWidget(self.progress)
        status_row.addWidget(self.status_text)
        status_row.addStretch(1)
        status_row.addWidget(self.btn_stop)
        root_layout.addLayout(status_row)

        # Table
        self.table = QTableWidget(0, 6, self)
        self.table.setHorizontalHeaderLabels(["Select", "Name", "Path", "Type", "Last Opened/Modified", "Size"])
        # Enable sorting; we will intercept clicks on the Select header to toggle select-all instead of sorting
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(self.table.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(self.table.SelectionMode.ExtendedSelection)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        # Add a header checkbox in the Select column (text icon only)
        select_header_item = QTableWidgetItem("☐ Select")
        self._header_checked = False
        self.table.setHorizontalHeaderItem(0, select_header_item)
        header.sectionClicked.connect(self._on_header_clicked)
        self._sort_column = 5
        self._sort_desc = True
        self.table.itemSelectionChanged.connect(self._update_selection_summary)
        root_layout.addWidget(self.table, 1)

        # Action row
        actions = QHBoxLayout()
        actions.setSpacing(10)
        btn_trash = QPushButton("Move Selected to Trash")
        btn_trash.clicked.connect(self._move_selected_to_trash)
        btn_reveal = QPushButton("Reveal in Finder")
        btn_reveal.clicked.connect(self._reveal_selected)
        btn_preview = QPushButton("Quick Look Preview")
        btn_preview.clicked.connect(self._preview_selected)
        btn_open_trash = QPushButton("Open Trash")
        btn_open_trash.clicked.connect(lambda: open_trash())
        self.btn_undo = QPushButton("Undo Last Move")
        self.btn_undo.setEnabled(False)
        self.btn_undo.clicked.connect(self._undo_last_move)
        self.selection_summary = QLabel("Selected: 0 files, Total: 0 B")
        self.found_summary = QLabel("Found: 0")
        actions.addWidget(btn_trash)
        actions.addWidget(btn_reveal)
        actions.addWidget(btn_preview)
        actions.addWidget(btn_open_trash)
        actions.addWidget(self.btn_undo)
        actions.addStretch(1)
        actions.addWidget(self.found_summary)
        actions.addSpacing(12)
        actions.addWidget(self.selection_summary)
        root_layout.addLayout(actions)

        # Drain timer for UI updates
        self._found_count = 0
        self._drain_timer = QTimer(self)
        self._drain_timer.setInterval(100)
        self._drain_timer.timeout.connect(self._drain_results)
        self._drain_timer.start()

        # Workers
        self.scan_controller = ScanController(self._on_scan_result_bg, self._on_scan_done_bg)

    def _on_size_preset(self) -> None:
        label = self.size_dropdown.currentText()
        mapping = {"50 MB": 50 * 1024 * 1024, "200 MB": 200 * 1024 * 1024, "1 GB": 1024 * 1024 * 1024}
        if label in mapping:
            # Preset selected: set value and hide the custom box
            self.size_input.setText(str(mapping[label]))
            self.size_input.setVisible(False)
            self.size_input.setEnabled(False)
        else:
            # Custom selected: show the input
            self.size_input.setVisible(True)
            self.size_input.setEnabled(True)
        self._save_current_presets()

    def _init_size_preset_from_value(self, value: int) -> None:
        # Match saved value to presets; otherwise select Custom
        presets = [
            (50 * 1024 * 1024, 0),
            (200 * 1024 * 1024, 1),
            (1024 * 1024 * 1024, 2),
        ]
        for bytes_val, idx in presets:
            if value == bytes_val:
                self.size_dropdown.setCurrentIndex(idx)
                self.size_input.setVisible(False)
                self.size_input.setEnabled(False)
                return
        # Custom
        self.size_dropdown.setCurrentIndex(3)
        self.size_input.setVisible(True)
        self.size_input.setEnabled(True)

    def _save_current_presets(self) -> None:
        # Sync and persist current inputs as presets
        try:
            self.min_age_days = int(self.age_input.text())
        except Exception:
            pass
        try:
            self.min_size_bytes = int(self.size_input.text())
        except Exception:
            pass
        save_presets({
            "min_age_days": self.min_age_days,
            "min_size_bytes": self.min_size_bytes,
            "ignore_dev_preset": self.dev_ignore_checkbox.isChecked(),
        })

    def _msg(self, title: str, text: str) -> None:
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.NoIcon)
        box.setWindowIcon(QIcon())
        box.setIconPixmap(QPixmap())
        box.setWindowTitle(title)
        box.setText(text)
        box.setStandardButtons(QMessageBox.StandardButton.Ok)
        box.exec()

    def _default_roots(self) -> List[Path]:
        home = Path.home()
        candidates = [home / "Downloads", home / "Desktop", home / "Documents", home / "Pictures"]
        return [p for p in candidates if p.exists()]

    def _choose_roots(self) -> None:
        dlg = QFileDialog(self)
        dlg.setFileMode(QFileDialog.FileMode.Directory)
        dlg.setOption(QFileDialog.Option.DontUseNativeDialog, False)
        if dlg.exec():
            selected = dlg.selectedFiles()
            self.selected_roots = [Path(p) for p in selected]
            self.roots_label.setText(", ".join(str(p) for p in self.selected_roots))
            self._clear_results()

    def _start_scan(self) -> None:
        try:
            self.min_age_days = int(self.age_input.text())
            self.min_size_bytes = int(self.size_input.text())
        except ValueError:
            self._msg("Invalid input", "Age and size must be integers")
            return
        self.table.setRowCount(0)
        self.items_by_path.clear()
        self._found_count = 0
        self._scan_done = False
        self._update_selection_summary()
        self.found_summary.setText("Found: 0")
        self.progress.setVisible(True)
        self.status_text.setText("Scanning…")
        self.btn_stop.setVisible(True)
        # Persist current presets
        save_presets({
            "min_age_days": self.min_age_days,
            "min_size_bytes": self.min_size_bytes,
            "ignore_dev_preset": self.dev_ignore_checkbox.isChecked(),
        })

        config = ScanConfig(
            roots=self.selected_roots,
            min_age_days=self.min_age_days,
            min_size_bytes=self.min_size_bytes,
            exclude_paths=self.excluded_paths,
            ignore_dev_preset=self.dev_ignore_checkbox.isChecked(),
        )
        self.scan_controller.start_scan(config)

    def _stop_scan(self) -> None:
        self.scan_controller.stop()
        self._scan_done = True
        self.progress.setVisible(False)
        self.status_text.setText("Stopped")
        self.btn_stop.setVisible(False)

    def _format_excludes(self) -> str:
        if not self.excluded_paths:
            return "(none)"
        return ", ".join(str(p) for p in self.excluded_paths)

    def _add_exclude(self) -> None:
        dlg = QFileDialog(self)
        dlg.setFileMode(QFileDialog.FileMode.Directory)
        dlg.setOption(QFileDialog.Option.DontUseNativeDialog, False)
        if dlg.exec():
            selected = [Path(p) for p in dlg.selectedFiles()]
            # Deduplicate while preserving order
            existing = {str(p): p for p in self.excluded_paths}
            for p in selected:
                existing[str(p)] = p
            self.excluded_paths = list(existing.values())
            save_excluded_paths(self.excluded_paths)
            self.excludes_label.setText(self._format_excludes())

    def _clear_excludes(self) -> None:
        self.excluded_paths = []
        save_excluded_paths(self.excluded_paths)
        self.excludes_label.setText(self._format_excludes())

    # Background-thread callbacks enqueue data only
    def _on_scan_result_bg(self, item: FileItem) -> None:
        self._result_queue.put(item)

    def _on_scan_done_bg(self) -> None:
        self._scan_done = True

    # Runs on UI thread periodically
    def _drain_results(self) -> None:
        drained = 0
        # Temporarily disable sorting while inserting to avoid churn
        sorting_prev = self.table.isSortingEnabled()
        if sorting_prev:
            self.table.setSortingEnabled(False)
        while not self._result_queue.empty():
            try:
                item = self._result_queue.get_nowait()
            except Exception:
                break
            # Type filter
            if not self._type_allowed(item.type_group):
                continue
            self.items_by_path[item.path] = item
            row = self.table.rowCount()
            self.table.insertRow(row)
            # Checkbox in column 0
            check_it = QTableWidgetItem(" ")
            check_it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            check_it.setCheckState(Qt.CheckState.Unchecked)
            check_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, check_it)

            name_it = QTableWidgetItem(item.display_name)
            # Store the absolute path in user data so selection is robust under sorting
            name_it.setData(Qt.ItemDataRole.UserRole, str(item.path))
            self.table.setItem(row, 1, name_it)
            self.table.setItem(row, 2, QTableWidgetItem(str(item.path)))
            self.table.setItem(row, 3, QTableWidgetItem(item.type_group))
            self.table.setItem(row, 4, QTableWidgetItem(item.last_used_or_modified_str))
            self.table.setItem(row, 5, SizeItem(human_readable_size(item.size_bytes), item.size_bytes))
            drained += 1
        if sorting_prev:
            self.table.setSortingEnabled(True)
        if drained:
            self._found_count += drained
            self.found_summary.setText(f"Found: {self._found_count}")
            self.status_text.setText("Scanning…")
        if self._scan_done and self._result_queue.empty():
            self.progress.setVisible(False)
            self.status_text.setText("Done")
            self.btn_stop.setVisible(False)

    def _selected_paths(self) -> List[Path]:
        rows = set(idx.row() for idx in self.table.selectedIndexes())
        paths: List[Path] = []
        # Include rows selected by checkbox as well
        for r in range(self.table.rowCount()):
            check_it = self.table.item(r, 0)
            if check_it and check_it.checkState() == Qt.CheckState.Checked:
                rows.add(r)
        for r in rows:
            # Prefer the path stored in the Name cell's user data
            name_item = self.table.item(r, 1)
            path_from_data = None
            if name_item is not None:
                data = name_item.data(Qt.ItemDataRole.UserRole)
                if isinstance(data, str) and data:
                    path_from_data = Path(data)
            if path_from_data:
                paths.append(path_from_data)
                continue
            # Fallback: read from Path column text
            path_item = self.table.item(r, 2)
            if path_item and path_item.text():
                paths.append(Path(path_item.text()))
        return paths

    def _selected_items(self) -> List[FileItem]:
        return [self.items_by_path[p] for p in self._selected_paths() if p in self.items_by_path]

    def _update_selection_summary(self) -> None:
        items = self._selected_items()
        total = sum(i.size_bytes for i in items)
        self.selection_summary.setText(f"Selected: {len(items)} files, Total: {human_readable_size(total)}")

    def _remove_row_by_path(self, path: Path) -> None:
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 2)
            if item and Path(item.text()) == path:
                self.table.removeRow(row)
                break

    def _move_selected_to_trash(self) -> None:
        items = self._selected_items()
        if not items:
            return
        total = sum(i.size_bytes for i in items)
        confirm = QMessageBox(self)
        confirm.setIcon(QMessageBox.Icon.NoIcon)
        confirm.setWindowIcon(QIcon())
        confirm.setIconPixmap(QPixmap())
        confirm.setWindowTitle("Confirm Trash")
        confirm.setText(f"Move {len(items)} file(s) to Trash?")
        confirm.setInformativeText(f"Total size: {human_readable_size(total)}")
        confirm.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        confirm.setDefaultButton(QMessageBox.StandardButton.Cancel)
        if confirm.exec() != QMessageBox.StandardButton.Yes:
            return
        moved = 0
        log_items = []
        self.last_trashed_paths = []
        for item in items:
            try:
                send2trash(str(item.path))
                moved += 1
                self._remove_row_by_path(item.path)
                self.items_by_path.pop(item.path, None)
                log_items.append({"path": str(item.path), "size": item.size_bytes})
                self.last_trashed_paths.append(item.path)
            except Exception as exc:  # noqa: BLE001
                print(f"Failed to trash {item.path}: {exc}")
        append_action_log("move_to_trash", log_items, total)
        self._msg("Done", f"Moved {moved} file(s) to Trash.")
        self._update_selection_summary()
        self.btn_undo.setEnabled(bool(self.last_trashed_paths))

    def _reveal_selected(self) -> None:
        paths = self._selected_paths()
        if not paths:
            return
        reveal_in_finder(paths[0])

    def _preview_selected(self) -> None:
        paths = self._selected_paths()
        if not paths:
            return
        if len(paths) > 1:
            self._msg("Preview limited", "Quick Look preview is disabled for multiple selections. Select a single file to preview.")
            return
        quick_look_preview(paths)

    def _toggle_select_all(self, checked: bool) -> None:
        for r in range(self.table.rowCount()):
            it = self.table.item(r, 0)
            if it:
                it.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        self._update_selection_summary()

    def _on_header_clicked(self, logical_index: int) -> None:
        # Clicking the Select header toggles select-all; disable sorting on this column
        if logical_index == 0:
            hdr_item = self.table.horizontalHeaderItem(0)
            self._header_checked = not getattr(self, "_header_checked", False)
            hdr_item.setText("☑ Select" if self._header_checked else "☐ Select")
            self._toggle_select_all(self._header_checked)
            return
        # For other columns, implement basic toggle sort (excluding Select)
        if logical_index == 5:
            # Size column: numeric sort via built-in since we use SizeItem
            order = Qt.SortOrder.DescendingOrder if getattr(self, "_sort_desc", True) else Qt.SortOrder.AscendingOrder
            self.table.sortItems(5, order)
            self._sort_desc = not getattr(self, "_sort_desc", True)
        else:
            # Use built-in sorting for other columns
            order = Qt.SortOrder.DescendingOrder if getattr(self, "_sort_desc", True) else Qt.SortOrder.AscendingOrder
            self.table.sortItems(logical_index, order)
            self._sort_desc = not getattr(self, "_sort_desc", True)

    # No manual _sort_by_column needed; using built-in sortItems with SizeItem for numeric size

    def _type_allowed(self, type_group: str) -> bool:
        return (
            (self.type_image_cb.isChecked() if type_group == "image" else True)
            and (self.type_video_cb.isChecked() if type_group == "video" else True)
            and (self.type_archive_cb.isChecked() if type_group == "archive" else True)
            and (self.type_other_cb.isChecked() if type_group == "other" else True)
        )

    def _apply_type_filter(self) -> None:
        # Simple approach: clear and rescan to apply type filters quickly
        # Could be optimized by hiding rows instead
        self._start_scan()

    def _undo_last_move(self) -> None:
        if not self.last_trashed_paths:
            return
        # Best-effort: open Trash so user can restore; automated restore can be added later
        open_trash()
        self.btn_undo.setEnabled(False)

    def _clear_results(self) -> None:
        # Clear table and reset counters/UI when changing roots
        self.table.setRowCount(0)
        self.items_by_path.clear()
        self._found_count = 0
        self.found_summary.setText("Found: 0")
        self.selection_summary.setText("Selected: 0 files, Total: 0 B")
        self.status_text.setText("Idle")
        self._scan_done = True
        self.progress.setVisible(False)
        self.btn_stop.setVisible(False)
        # Reset Select header checkbox visual
        hdr_item = self.table.horizontalHeaderItem(0)
        if hdr_item is not None:
            hdr_item.setText("☐ Select")
        self._header_checked = False


class SizeItem(QTableWidgetItem):
    def __init__(self, display: str, size_bytes: int) -> None:
        super().__init__(display)
        self._size_bytes = int(size_bytes)
        # Right align numbers
        self.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def __lt__(self, other: QTableWidgetItem) -> bool:  # type: ignore[override]
        try:
            if isinstance(other, SizeItem):
                return self._size_bytes < other._size_bytes
            return super().__lt__(other)
        except Exception:
            return super().__lt__(other)