## Phase Plans — Clean Mac

This document breaks the MVP into three phases. Each phase includes a clear description, scoped requirements, technical specifications, and concrete results/exit criteria. Phase 1 also includes a developer setup guide.

---

## Phase 1 — Core MVP Scanner

### Description
Deliver a minimal but usable macOS app to discover unused user files (images, videos, documents, archives), list them with metadata, and safely move selected items to Trash. Exclude apps and system areas by default.

### Functional Requirements
- Select scan roots (defaults): `~/Downloads`, `~/Desktop`, `~/Documents`, `~/Pictures`.
- Discover files using Spotlight and fetch metadata:
  - Discovery via `mdfind` scoped to each selected root.
  - Metadata via `mdls` for `kMDItemLastUsedDate` and `kMDItemFSSize`.
- Filters:
  - Type groups: images, videos, documents, archives.
  - Age thresholds: 30/90/180/365 days + custom.
  - Size threshold: minimum size in bytes; optional "Top N largest" toggle.
- Results table columns: Name, Path, Type, Last opened (fallback to modified), Size.
- Selection model: multi-select, select-all for current filtered set.
- Actions: Move to Trash using `send2trash`.
- Context actions: Reveal in Finder for any row.
- Safety:
  - Skip system folders and app/framework bundles.
  - Never touch internals of `*.photoslibrary`.
- Reporting: Dry-run mode; export candidates to CSV/JSON.

### Non-Functional Requirements
- Responsive UI: scanning must not block the UI thread.
- Clear error handling for permission-denied paths.
- macOS 12+; Python 3.11+; Apple Silicon and Intel supported.
- Basic logging to file and console.

### Technical Specifications
- Language/Runtime: Python 3.11+.
- GUI: PySide6 (Qt) desktop app; single-window layout with sidebar filters and main results table.
- Process/Concurrency model:
  - UI thread for rendering and interactions.
  - One discovery worker issuing `mdfind` per root and streaming file paths.
  - N metadata workers (ThreadPoolExecutor) fetching `mdls` data and `os.stat` fallbacks.
  - Bounded `queue.Queue` for backpressure between stages.
- Discovery strategy:
  - Command template per root:
    - `mdfind -onlyin <root> '(kMDItemContentTypeTree == "public.image" || kMDItemContentTypeTree == "public.movie" || kMDItemContentTypeTree == "public.archive" || kMDItemContentTypeTree == "public.content")'`
  - For documents, include UTTypes such as: `public.text`, `public.data`, `com.adobe.pdf`, `org.openxmlformats.wordprocessingml.document`, `org.openxmlformats.spreadsheetml.sheet`.
  - Final filtering by size/age/groups applied in Python after metadata resolution.
- Metadata retrieval:
  - Command: `mdls -raw -name kMDItemLastUsedDate -name kMDItemFSSize <path>`
  - Fallbacks: `os.stat(path).st_mtime` when last used is missing.
- Safety rules (skip if any is true):
  - Path under `/System`, `/Library`, `/Applications`, `/usr`, `/bin`, `/sbin`, `/opt`.
  - Inside bundle directories: `.app`, `.framework`, `.photoslibrary`, `.aplibrary`, `.appbundle`, `.kext`.
- Data model (Python classes or TypedDicts):
  - FileItem: path, displayName, sizeBytes, lastUsedAt, lastModifiedAt, contentType, typeGroup, isBundle, isCloudOnly(False in P1), parentDir, isHidden.
  - ScanConfig: roots, includeGroups, minAgeDays, minSizeBytes, excludePaths, excludePatterns, localOnly(False in P1).
  - ScanResult: items, totalSizeBytes, scanDurationMs, errors.
- Move to Trash: `send2trash.send2trash(path)` only; never `os.remove`.
- CSV/JSON export: Python `csv` and `json` modules.
- Logging: `logging` with rotating file handler in user config dir via `platformdirs`.
- Packaging: run as a Python script in Phase 1; app bundling deferred to Phase 3.

### Developer Setup Guide (Phase 1)
1) Prerequisites
- macOS 12+ with Spotlight enabled
- Xcode Command Line Tools: `xcode-select --install`
- Homebrew (optional): `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
- Python 3.11+: `brew install python@3.11`

2) Create project venv
```bash
/opt/homebrew/bin/python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

3) Install dependencies
```bash
pip install PySide6 send2trash platformdirs rich
```
- Optional (not used in Phase 1): `pyobjc` for native APIs; `typer` for CLI helpers.

4) Run dev app
```bash
python -m app.main
```
- If Full Disk Access is needed for certain directories, grant access to the Python interpreter (System Settings → Privacy & Security → Full Disk Access).

5) Troubleshooting
- If `mdfind` returns nothing, ensure Spotlight indexing is enabled for the target volume.
- If UI freezes, verify scanning is in worker threads, not the UI thread.

### Results / Exit Criteria
- You can launch the app, select roots, scan, filter by age and size, select items, and move them to Trash.
- Dry-run export produces valid CSV/JSON of candidates.
- Demo: defaults + filter >180 days and >50 MB; reveal an item in Finder; Trash two items.
- Deliverables: runnable code, requirements file, minimal developer README section (this setup guide), and sample exports.

---

## Phase 2 — UX, Performance, and Safety Enhancements

### Description
Make frequent use smooth, safe, and performant at scale. Add streaming, previews, grouping/sorting, presets, ignore lists, iCloud awareness, and undo for the last batch.

### Functional Requirements
- Live streaming of results with progress; pause and cancel scan.
- Sorting and grouping by type, folder, age bucket, and size bucket.
- Quick Look preview for images/videos/docs from the results table.
- Batch delete with progress; chunk operations; undo (restore last batch from Trash when possible).
- Presets: save/load scan presets (roots, groups, age/size thresholds).
- Persistent ignore list (paths/patterns) applied to scans.
- iCloud awareness: show local-only vs cloud-only status; Local-only filter toggle.
- Action log with timestamp, action, count, total size, sample paths.

### Non-Functional Requirements
- Handle up to 10k results while keeping UI responsive; bounded memory usage.
- Robust error and cancellation handling; skipped items listed with reasons.
- In-app Settings for presets, ignore list, confirmations, and local-only toggle.

### Technical Specifications
- Concurrency: producer/consumer with bounded `queue.Queue`.
  - Discovery thread(s) push candidate paths.
  - Metadata worker pool enriches with mdls/stat.
  - UI thread consumes batches via Qt timers/signals to avoid long UI blocks.
- Progress reporting: track scanned count per root and total candidates; estimate remaining via moving average.
- Grouping/sorting: in-memory keyed sorts; cache computed buckets to avoid expensive recompute.
- Quick Look integration options:
  - Simple: spawn `qlmanage -p <path>` detached.
  - Better: PyObjC to invoke Quick Look (`QLPreviewPanel`) if feasible; fallback to `qlmanage`.
- Presets and ignore list storage: JSON files in `platformdirs.user_config_dir("clean-mac")`.
- iCloud detection (PyObjC preferred):
  - Query NSURL resource values: `NSURLIsUbiquitousItemKey`, `NSURLUbiquitousItemDownloadingStatusKey` to determine cloud-only state.
  - Mark `isCloudOnly` and hide when local-only filter is enabled.
- Undo for last batch:
  - Maintain manifest `{original_path → trashed_item_name}` at action time.
  - Attempt restore by moving from user Trash back to `original_path` if available; resolve conflicts.
  - If restore fails, open Trash in Finder.
- Action log: append JSONL entries in `platformdirs.user_log_dir("clean-mac")`.

### Results / Exit Criteria
- Large scans stream smoothly; user can pause/cancel.
- Previews open quickly; grouping/sorting behaves as expected.
- Presets and ignore lists persist across sessions.
- iCloud-only items are indicated/hidden when toggled.
- Undo restores the last batch in common cases; otherwise clearly guides the user.
- Deliverables: action log file, UX walkthrough, short performance note (counts/timings on test data).

---

## Phase 3 — Pre-Release Polish and Packaging

### Description
Prepare the app for broader distribution: onboarding, permissions guidance, packaging, optional codesigning/notarization, accessibility checks, and stability hardening.

### Functional Requirements
- First-run onboarding: choose roots, explain Full Disk Access, one-click open System Settings pane.
- Permission checks during scans with friendly prompts for missing access.
- Report export: detailed JSON/CSV of selected items and a summary card (counts, total reclaimable size).
- About/Help view and diagnostics export (logs + environment summary).

### Non-Functional Requirements
- Distributable `.app` via PyInstaller with custom icon.
- Optional codesign + notarization if Developer ID is available; otherwise document Gatekeeper steps.
- Accessibility and dark mode verification; keyboard navigation for core flows.
- Stability pass: timeouts around `mdfind`/`mdls`; resilient to missing metadata and iCloud placeholders.

### Technical Specifications
- Packaging: PyInstaller `.spec` with:
  - Hidden imports for Qt plugins; include `platforms/libqcocoa.dylib`.
  - Bundle resources: app icon, default preset JSON.
  - Entry point: `app/main.py`.
- Codesigning (optional):
  - `codesign --deep --force --options runtime --sign "Developer ID Application: <Name> (<TeamID>)" CleanMac.app`
  - Notarize with `xcrun notarytool submit --wait --apple-id <id> --team-id <team> --password <app-specific-password> CleanMac.zip`
- Onboarding: helper to open System Settings pane via `open x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles`.
- Crash/diagnostics: wrap entrypoint with top-level exception handler → write to logs and show friendly dialog.
- Versioning: semantic version in `__version__`; show in About dialog.

### Results / Exit Criteria
- `.app` runs on another Mac without a dev environment; onboarding explains and links to permissions.
- Documentation: install/run guide, permissions instructions, troubleshooting, and release notes.
- Optional signed/notarized build if credentials exist; otherwise unsigned build with guidance.

---

## Out-of-Scope for MVP
- Duplicate and near-duplicate detection (post-MVP candidate).
- Screenshot sweeper heuristics.
- Treemap visualization (space heatmap).
- Scheduled scans.
