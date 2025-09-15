# Project Discussion — Clean Mac

## Goal
Build a macOS-focused Python app with a GUI to scan user storage (excluding apps/system) for files not opened/used recently, then bulk-delete safely.

## Product scope and UX
- **Primary outcome**: Identify and safely remove old/unused large files (focus: images, videos, archives, docs) to reclaim space.
- **Out of scope (initial)**: App binaries, system folders, Photos.app internal library, Mail/VMs, cloud-only placeholders without local data.

### Core features
- **Smart scan**
  - Scans user-selected roots (default: `~/Downloads`, `~/Desktop`, `~/Documents`, `~/Pictures`, iCloud Drive).
  - Uses Spotlight metadata (kMDItemLastUsedDate) for last-opened; falls back to modified date if missing.
  - Filters by file types: images (`public.image`), videos (`public.movie`), documents, archives, custom MIME groups.
  - Age threshold selector: 30/90/180/365 days + custom.
  - Size filter: min size (e.g., >50 MB), and Top-N largest.
  - Exclusions: user-defined folders, file patterns, tags; built-in safeguards for app bundles and system paths.
  - iCloud handling: show local vs cloud-only status; optionally hide cloud-only placeholders (no local space).
- **Results UI**
  - Grouping: by type, by folder, by age bucket, by size bucket.
  - Sorting: size, last-opened, path, type.
  - Quick preview via Quick Look.
  - Path breadcrumb with Reveal in Finder.
  - Summary card: count, total size, potential reclaim.
- **Bulk actions**
  - Select all/none, multi-select by group.
  - Move to Trash (default) with undo (restore from Trash).
  - Permanent delete option (disabled by default; explicit confirmation required).
  - Batch size limit + progress + pause/cancel.
- **Safety**
  - Never touch Photos Library (`~/Pictures/Photos Library.photoslibrary`) internals.
  - Never delete inside app bundles or system directories.
  - Confirmation dialogs with counts and total size.
  - Dry-run report mode (no deletion; export CSV/JSON of candidates).
- **Performance and resiliency**
  - Non-blocking scans with live progress; cancel/pause.
  - Incremental updates in UI as results stream in.
  - Caching of scan results; quick re-scan using last config.
- **Quality-of-life**
  - Saved scan presets (paths, types, thresholds).
  - Ignore list/whitelist that persists.
  - Logs for actions (who/when/what moved to Trash) for audits.
  - Accessibility-friendly UI and dark mode.
  - No telemetry by default.

## Nice-to-haves (Phase 2)
- **Duplicate finder**: hash-based near-duplicate detection (images first, then general files).
- **Screenshot sweeper**: dedicated filter for screenshots older than N days.
- **Downloads cleaner**: opinionated rules (old .dmg, .zip, installers).
- **Similarity for photos**: basic perceptual hashing to catch near-identical images.
- **Schedule**: periodic reminder scans.
- **Space heatmap**: treemap visualization by folder.

## Technical design
### Platform and packaging
- **Language**: Python 3.11+
- **GUI**: PySide6 (Qt) for native-feeling macOS UI.
- **Move to Trash**: `send2trash` package (safe, reversible).
- **Packaging**: `pyinstaller` for `.app` bundle; later codesign + notarization.
- **Permissions**: prompt user to grant Full Disk Access (open System Settings pane); work with partial access gracefully.

### Scanning strategy
- **Primary discovery**: `mdfind` with Spotlight predicates to fetch candidates by type and location quickly.
  - Strategy examples:
    - Content types: `kMDItemContentTypeTree == "public.image"` (and others)
    - Scoped by `-onlyin` per selected root
    - Apply extra constraints in Python for control
- **Per-file metadata**: `mdls -raw -name kMDItemLastUsedDate -name kMDItemFSSize` to get last used and size.
  - Fallbacks: `st_mtime` if last used is missing; lazy directory-size only if needed.
- **iCloud detection**:
  - Prefer NSURL resource values via PyObjC; fallback to Spotlight flags if present.
  - Hide cloud-only items when “local-only” filter is on.
- **Exclusions/safety**:
  - Skip bundles (`.app`, `.framework`, `.photoslibrary`, `.aplibrary`, etc.).
  - Skip system dirs (`/System`, `/Library`, `/Applications`, `/usr`, `/bin`, etc.).
  - Respect user-defined excludes.
- **Concurrency**:
  - Producer-consumer: discovery thread(s) → metadata workers → UI event thread.
  - Bounded queues to avoid memory spikes; backpressure if UI is slow.

### Data model
- **FileItem**
  - path: str
  - displayName: str
  - sizeBytes: int
  - lastUsedAt: datetime | None
  - lastModifiedAt: datetime
  - contentType: str
  - typeGroup: enum {image, video, doc, archive, other}
  - isBundle: bool
  - isCloudOnly: bool
  - parentDir: str
  - isHidden: bool
- **ScanConfig**
  - roots: list[str]
  - includeGroups: set[typeGroup]
  - minAgeDays: int
  - minSizeBytes: int | 0
  - excludePaths: list[str]
  - excludePatterns: list[str]
  - localOnly: bool
- **ScanResult**
  - items: list[FileItem]
  - totalSizeBytes: int
  - scanDurationMs: int
  - errors: list[str]
- **ActionLogEntry**
  - timestamp, action, paths, count, totalSize, configSnapshot

### UI flows
- **Home/Dashboard**
  - Storage summary and quick “Scan now” with selected preset.
- **Scan screen**
  - Progress bar, live count/size, cancel/pause.
  - Filter chips (type, age, size) and search box.
  - Table/list with columns: Name, Path, Type, Last opened, Size.
  - Row preview button; context menu for “Reveal in Finder”.
- **Review & Clean**
  - Summary card of selected items.
  - “Move to Trash” with confirmation and estimate of time.
  - After-action snackbar with “Undo” link.
- **Settings**
  - Roots, excludes, presets, confirmations, permanent delete toggle.

### Safety and correctness
- Use `send2trash` instead of `os.remove`.
- Double-check each path against blocklists before action.
- Batch deletion in chunks (e.g., 100–500 files) to keep UI responsive.
- Keep a manifest of last batch for quick restore shortcut.
- Unit tests around: Spotlight parsing and fallbacks; exclusion logic; trash/undo; iCloud detection.

### Performance considerations
- Rely on Spotlight for fast discovery instead of crawling the filesystem.
- Avoid per-file heavy operations before the user shows interest (lazy preview, lazy directory-size).
- Cache MDLS results during a session to reduce repeated calls when filtering/sorting.

### Packaging and distribution
- App bundle via PyInstaller with an entry `.app` and icon.
- Post-MVP: codesign with a Developer ID, enable hardened runtime, then notarize.
- First-run guide to grant Full Disk Access and select roots.

## Risks and mitigations
- **Last-used accuracy**: Some files lack `kMDItemLastUsedDate`. Show “last used unknown”; fallback to modified date.
- **Permissions**: Without Full Disk Access some folders are skipped. Detect and link to System Settings.
- **Photos library safety**: Hard-block any paths inside `.photoslibrary`.
- **iCloud placeholders**: Cloud-only files may not reclaim local space. Detect and optionally hide.
- **Large batches**: Deleting thousands can be slow. Chunk operations, show ETA, allow pause.

## MVP cut
- PySide6 UI with scan → list → select → Move to Trash
- Spotlight-based discovery; MDLS for last used + size
- Filters: types, age, size; grouping and sorting
- Exclusions + Photos library protection
- Quick Look previews
- Undo via Trash

## Future extensions
- Duplicate finder
- Similar-photo clustering
- Scheduled scans
- Treemap visualization

## Key choices to confirm
- Preferred UI toolkit: PySide6 (proposed)
- Default scan roots and age threshold: `~/Downloads`, `~/Desktop`, `~/Documents`, `~/Pictures` and 180 days
- Include videos/docs in MVP or start with images only?
- Treat iCloud cloud-only items: hide by default?
- Packaging now (local use) vs codesigning later?
