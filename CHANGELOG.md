# Changelog

All notable changes recorded commit-by-commit from the provided diffs (entries that matched commits on the repository's main branch were removed). The newest entry below reflects the last diff you provided and is placed at the head of the file.

---

## HEAD — refactor(tooling): integrate Python 'toolbox' modules; remove Deno helper (yt.ts)
Author: abx-dx  
Date: 2026-08-06  
Message: Replace the Deno helper script with a native Python toolbox package; add runner/parser/tools to orchestrate yt-dlp and improve cross-platform behavior

Highlights:
- Major architecture change:
  - Removed Deno helper files: `yt.ts`, `settings.ts`, and `deno.json`.
  - Added a Python-first "toolbox" package to centralize download logic and utilities:
    - `toolbox/command.py`, `cookies.py`, `metadata.py`, `output.py`, `parser.py`, `playlist.py`, `playlist_info.py`, `profiles.py`, `runner.py`, `tools.py`, `__init__.py`.
  - The GUI (`video_indirici.py`) now uses Toolbox classes (Tools, YtDlpRunner, OutputParser, profiles) instead of invoking the Deno script.
- New/changed behaviors:
  - Directly spawn `yt-dlp` from Python (via YtDlpRunner) with unbuffered stdout handling and typed events (ProgressEvent, PlaylistEvent, FileDoneEvent, WarningEvent, ErrorEvent, LogEvent).
  - Output parsing and FILE_DONE reporting moved into Python (toolbox.parser + toolbox.metadata) to produce richer reports and resolution-aware messages.
  - Profiles and format-building logic moved to Python (`toolbox.profiles`) with a video max-resolution option (build_video_format / RESOLUTIONS).
  - Tools discovery and environment management consolidated in `toolbox.tools` (Tools.discover and env()) — bin/ is added to PATH for subprocesses.
  - Runner stop/termination handles child processes safely across OS: taskkill on Windows, terminate on POSIX; subprocess args prevent windows popups.
  - DownloadWorker refactored to use YtDlpRunner and toolbox events; reports playlist counters and formatted FileDone reports to GUI.
- Packaging/build changes:
  - `build-portable.sh` updated:
    - Scans Python project and toolbox subpackage for bin dependencies.
    - Avoids copying TypeScript files; the TypeScript copy step was removed.
    - Maintains cross-platform filename handling and fallback when .exe is absent.
  - `.gitignore` extended (added `.cache/`).
- UI changes:
  - `video_indirici.py` UI refreshed:
    - New app title ("Video / Ses / Playlist İndirici"), resolution combobox shown for video profile, improved tools status panel listing `yt-dlp`, `ffmpeg`, `ffprobe`, `deno`.
    - Right-click context menu and improved encoding handling for stdout/stderr reconfiguration on Windows.
    - More robust self-test and tool status refresh logic.
- Removed/Deleted files:
  - `deno.json`, `settings.ts`, `yt.ts` (Deno helper stack removed).
- Rationale:
  - Simplify distribution and runtime by reducing the cross-language dependency surface.
  - Move real-time parsing and event handling into Python to allow richer GUI integration and improved cross-platform process handling.

Files modified/added/removed in this change:
- Added: `toolbox/*` (command.py, cookies.py, metadata.py, output.py, parser.py, playlist.py, playlist_info.py, profiles.py, runner.py, tools.py, __init__.py)
- Modified: `build-portable.sh`, `video_indirici.py`, `.gitignore`, `CHANGELOG.md`, `README.md`
- Removed: `deno.json`, `settings.ts`, `yt.ts`

---

## 0277710 — refactor(build): cross-platform build & runtime improvements
Author: abx-dx  
Date: 2026-08-02 23:22:22 +0300  
Message: Relax dependency matching, improve cross-platform binary handling, refine ffmpeg update logic, and add UI context menus

Highlights:
- build-portable.sh
  - Relaxed dependency regex to accept bin/<name> (not requiring .exe) and normalize paths.
  - Platform-aware filename handling: adds .exe on Windows, preserves no-extension on POSIX/CI.
  - Fallback logic: if the expected .exe isn't present, try the basename variant.
  - Ensure copied binaries are executable on POSIX (chmod +x) when appropriate.
  - Open portable output folder in explorer.exe on local Windows environments (non-CI).
- update-bin.sh
  - Changed FFmpeg update logic to use a different repository JSON source and improved download filtering for win64-gpl auto-builds.
  - Better handling and messaging when API data or download URL cannot be retrieved.
  - Tracks published_at date for update detection and avoids unnecessary downloads.
- video_indirici.py
  - Improved wording in header and clarified packaging expectations.
  - Added cross-platform support:
    - IS_WINDOWS and EXE_EXT computed from runtime platform.
    - TOOL_FILENAMES generated using EXE_EXT so binaries work on Windows and POSIX.
    - get_creation_flags() returns CREATE_NO_WINDOW only on Windows.
  - Moved and re-applied download progress regex definitions after platform constants.
  - ToolManager: run version checks in parallel (keeps previous behavior) but adjusted subprocess env to point to bin/ for tools.
  - Download worker:
    - Uses different process-termination strategy: taskkill on Windows; process.terminate() on POSIX.
    - Updates error text to tell users tools should be under bin/.
    - Launch subprocess with env referencing bin/.
  - UI:
    - Added a right-click context menu (Cut/Copy/Paste/Select All) for text entry fields (URL and output dir).
    - Updated error dialogs to reference `bin/` folder.
  - Minor cleanup: removed a stray blank, adjusted some log/status messages, and simplified run_self_test expectations.
- Overall: better cross-platform robustness for the portable build pipeline and runtime, improved resiliency when bin files are named without .exe, and small UX improvements in the GUI.

Files modified:
- build-portable.sh
- update-bin.sh
- video_indirici.py

---

## 9592ecc — feat(ci): add portable build scripts and github actions workflow
Author: abx-dx  
Date: 2026-07-26 13:05:52 +0300  
Message: feat(ci): add portable build scripts and github actions workflow

Highlights:
- Added CI and build automation for producing a portable Windows package:
  - `.github/workflows/build.yml` — GitHub Actions workflow to build on `windows-latest` and run `build-portable.sh`.
  - `build-portable.sh` — robust packaging script: runs PyInstaller, assembles `portable-app`, copies bin/ executables and .ts files.
  - `update-bin.sh` — downloads/updates `bin/` dependencies (yt-dlp, deno, ffmpeg/ffprobe) from upstream releases and extracts them into `bin/`.
- Reorganized repository packaging rules and ignores:
  - `.gitignore` updated to include `bin/`, portable artifacts, and other build outputs.
- Cleanups:
  - Removed `Video Indirici.spec`.
  - Adjusted `video_indirici.py` header docstring (notes for packaging), added `ffprobe` to tool list, further parallelization of ToolManager checks with ThreadPoolExecutor, and minor UI/footer tweaks (rowspan).
- Overall: CI/build pipeline to produce `portable-app` (MediaDownloader) and utilities to keep bin tools updated.

Files added/modified:
- Added: `.github/workflows/build.yml`, `build-portable.sh`, `update-bin.sh`
- Modified: `.gitignore`, `video_indirici.py`, removed `Video Indirici.spec`

---

## fe8a23b — refactor(yt): implement unbuffered stdout/stderr streaming and parallel downloads
Author: abx-dx  
Date: 2026-07-23 13:06:11 +0300  
Message: refactor(yt): implement unbuffered stdout/stderr streaming and parallel downloads

Highlights:
- `yt.ts` significantly refactored to improve live streaming of output:
  - Adds `--no-quiet` and `--concurrent-fragments 16` to ytdlp args.
  - Spawns ytdlp and reads both stdout and stderr in parallel.
  - Implements `streamOutput` to read chunks unbuffered and flush immediately to stdout using `Deno.stdout.writeSync`.
  - Ensures FILE_DONE events and other lines are forwarded immediately to the Python GUI (reduces latency).
  - Stderr is also captured and streamed.
- Settings cleanup:
  - `settings.ts` updated (removed aria2 field).
- Adds `yt-dlp.conf` with base flags `--proxy ""` and `--newline`.
- UI and repo housekeeping:
  - .gitignore adjusted.
  - README.md wording updated to reflect README.md usage.
- Effect: lower-latency console integration, better real-time progress & logs, concurrency tweaks for faster fragment downloads.

Files modified/added:
- `yt.ts` (major refactor), `settings.ts` (tweak), `yt-dlp.conf`, `README.md`, `.gitignore`

---

## 798ccb9 — Remove obsolete config and README.txt
Author: abx-dx  
Date: 2026-07-21 01:32:18 +0300  
Message: Remove obsolete config and README.txt

Highlights:
- Clean-up: removed obsolete `README.txt` and legacy `config.json` (now replaced by `settings.ts`).

Files removed:
- `README.txt`, `config.json`

---

## 63f194c — Improve downloader architecture
Author: abx-dx  
Date: 2026-07-20 20:24:09 +0300  
Message: Improve downloader architecture

Highlights:
- Introduces a TypeScript config file `settings.ts` (replaces/augments prior JSON config).
  - `settings.ts` holds ytdlp/ffmpeg/aria2/cookies and profiles (video/audio/playlist).
- Changes to `video_indirici.py`:
  - Removes embedded QUALITY_FORMATS and related helpers — offloads format selection to the Deno layer.
  - Adds `ffprobe` to `TOOL_FILENAMES`.
  - ToolManager `check()` runs checks in parallel via ThreadPoolExecutor for speed.
  - Improved cancellation: attempts `taskkill /PID ...` on Windows to ensure child process termination.
  - Minor UI layout tweaks (tools button rowspan).
  - Adjusted run_self_test to avoid iterating by removed QUALITY_FORMATS.
- `yt.ts` updated to:
  - Import `settings.ts`.
  - Accept `--output` and `--cookies` flags from the Python launcher.
  - Use `settings` values for ytdlp, ffmpeg, aria2, profiles, and output calculation.
  - Improved playlist output path handling (baseDir replacement when a custom output is passed).
  - Overall better separation: Python launches Deno script and feeds it params; Deno does actual yt-dlp orchestration.

Files added/modified:
- Added: `settings.ts`
- Modified: `video_indirici.py`, `yt.ts`

---

## a626665 — Sprint 2.1 - Replace quality selector with profile selector
Author: abx-dx  
Date: 2026-07-19 20:14:40 +0300  
Message: Sprint 2.1 - Replace quality selector with profile selector

Highlights:
- Replaced per-resolution quality selector in the GUI with profile selector (Video / Audio / Playlist).
- Introduced `PROFILE_OPTIONS` mapping.
- `build_download_command` and DownloadWorker updated to accept a `profile` parameter instead of `quality`.
- UI updated: combobox for selecting profile; wiring to translate UI selection to the profile name passed to Deno script.

Files modified:
- `video_indirici.py` (profile UI and worker changes)

---

## 21346bc — Sprint 1 - GUI integrated with Deno engine
Author: abx-dx  
Date: 2026-07-19 19:37:56 +0300  
Message: Sprint 1 - GUI integrated with Deno engine

Highlights:
- Integrates a Deno helper script (`yt.ts`) to drive yt-dlp logic and split responsibilities:
  - `yt.ts` created: constructs ytdlp command-lines, handles playlist info, prints FILE_DONE events.
- Adds `config.json` (ytdlp, aria2, profiles, cookies) to drive `yt.ts`.
- Adds `deno.json` with a task.
- Modifies `video_indirici.py` to:
  - Look for tools under `bin/`.
  - Invoke `deno run --allow-* yt.ts` instead of calling yt-dlp directly.
  - Change worker cwd to tool_manager.app_dir (so Deno script runs from app dir).
  - Adjust command assembly to call the Deno script with profiles.
- Overall: shifts download control from Python to Deno, centralizing yt-dlp argument construction in `yt.ts`.

Files added/modified:
- Added: `yt.ts`, `config.json`, `deno.json`
- Modified: `video_indirici.py` (tool paths, command-building, subprocess cwd)

---