# <img src="assets/mouse.png" width="36" valign="middle" alt="Auto Mouse Mover Logo" /> Auto Mouse Mover

[![CI](https://github.com/HumayunK01/AutoMouseMover/actions/workflows/ci.yml/badge.svg)](https://github.com/HumayunK01/AutoMouseMover/actions/workflows/ci.yml)
[![Latest Release](https://img.shields.io/github/v/release/HumayunK01/AutoMouseMover?color=success&label=Release)](https://github.com/HumayunK01/AutoMouseMover/releases/latest)
[![Direct Download](https://img.shields.io/badge/Download-AutoMouseMover.exe-4f46e5?logo=windows&logoColor=white)](https://github.com/HumayunK01/AutoMouseMover/releases/latest/download/AutoMouseMover.exe)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6.svg)](https://microsoft.com/windows)
[![Offline Safe](https://img.shields.io/badge/Network-100%25%20Offline%20(No%20Telemetry)-brightgreen.svg)](#)

> A lightweight, offline Windows utility for simulating periodic cursor movement and preventing unwanted system idle states.

Auto Mouse Mover is designed for long-running computational jobs, presentations, reading sessions, and continuous display monitoring where systems would otherwise go to sleep or screensavers kick in. Rather than blindly jumping cursor coordinates, it combines smooth cubic Bézier trajectories, subtle micro-nudges, randomized intervals, and an automatic user handoff system that yields immediately when you touch your mouse.

---

## 📸 Visual Preview & Workflow

| 1. Idle / Configuration | 2. Active / Running State | 3. Smart Exit / Tray Dialog |
| :---: | :---: | :---: |
| ![Normal Preview](assets/preview.png) | ![Running Preview](assets/runningpreview.png) | ![Exit Dialog Preview](assets/exitpreview.png) |
| **Configure Modes & Timers**<br>Select movement strategies, base intervals, and timing variations. | **Active Simulation**<br>Live countdown progress, move counters, and active status display. | **Zero Desktop Clutter**<br>Minimize silently to the Windows system tray or exit cleanly. |

---

## ✨ Features & Engineering Highlights

- **🌊 Smooth Wander (Cubic Bézier Curves)**: Generates curved cursor paths using cubic Bézier equations with acceleration and deceleration profiles instead of rigid linear jumps.
- **🛡️ Smart User Handoff**: Continuously calculates cursor delta. If physical user movement is detected (`>10px`), the engine pauses automatically so it never fights your hand, resuming smoothly when you become idle.
- **🥷 Stealth Nudge Mode**: Performs sub-pixel / 1–2px micro-shifts that keep system timers active without causing visual distraction during reading or presentations.
- **🎲 Randomized Interval Jitter**: Applies configurable timing variations between movement cycles to prevent fixed-period repetition.
- **📥 Background System Tray & Global Hotkey (`F6`)**: Minimizes cleanly to the Windows notification tray (hidden from taskbar and Alt+Tab) and toggles from any application via the `F6` global hotkey.
- **☕ Native Win32 Sleep Prevention**: Interfaces directly with `kernel32.SetThreadExecutionState` (`ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED`) to request active system and display power states.
- **🔒 Zero Telemetry & Fully Offline**: No network sockets, no cloud dependencies, no analytics. Works entirely offline by design.
- **🚀 Portable & No Admin Rights Required**: Operates strictly within user space using Win32 API ctypes bindings. Requires no installer, setup wizard, or UAC elevation.

---

## 🎯 Movement Strategies

| Mode | Behavior | Ideal Use Case |
| :--- | :--- | :--- |
| **🌊 Smooth Wander** | Traverses curved cubic Bézier paths with acceleration and deceleration. | Natural cursor movement across display boundaries. |
| **🥷 Stealth Nudge** | Micro-shifts the cursor 1–2 pixels and immediately returns. | Presentations, reading, videos, or full-screen dashboards. |
| **🔄 Gentle Circle** | Smoothly drifts in an orbital elliptical loop around the current position. | Continuous, predictable activity keeping displays awake. |
| **⚡ Random Jump** | Coordinates randomized jumps across multi-monitor virtual screen bounds. | Multi-display testing and keeping secondary workspaces active. |

---

## 📥 Download & Installation

### Option 1: Standalone Executable (Recommended)

1. Download **[`AutoMouseMover.exe`](https://github.com/HumayunK01/AutoMouseMover/releases/latest/download/AutoMouseMover.exe)** from the [Latest GitHub Release](https://github.com/HumayunK01/AutoMouseMover/releases/latest).
2. Run the executable. No installation wizard, registry edits, or administrator privileges are required.
3. *(Optional)* Run `CreateDesktopShortcut.bat` to place an official shortcut with the bundled application icon on your Desktop.

---

### Option 2: Run from Source (Python)

```powershell
# 1. Clone the repository
git clone https://github.com/HumayunK01/AutoMouseMover.git
cd AutoMouseMover

# 2. Set up virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. Install dependencies & launch
pip install -r requirements.txt
python main.py
```
*(Or double-click `run.bat` to launch automatically.)*

---

## 🏗️ Architecture & Implementation

The project is structured with strict separation between presentation, state orchestration, and OS input generation:

```
AutoMouseMover/
├── main.py                  # Entrypoint bootstrap & environment resolution
├── app.py                   # CustomTkinter GUI, theme handling, hotkey thread & tray
├── mover_engine.py          # Win32 ctypes input dispatch, Bezier math, and handoff logic
├── tests/
│   └── test_mover_engine.py # Automated unit tests for math, thresholds, and lifecycle
├── assets/                  # High-DPI icons, vector graphics, and bundled fonts
├── AutoMouseMover.spec      # PyInstaller compilation specification
└── .github/workflows/ci.yml # Continuous Integration (test matrix + build verification)
```

### Win32 API Integration Details

- **Input Dispatch**: Dispatches cursor coordinates and zero-delta move events via `ctypes.windll.user32.SetCursorPos` and `mouse_event(MOUSEEVENTF_MOVE, 0, 0, 0, 0)`, actively updating the Windows user input timestamp (`GetLastInputInfo`).
- **Power Management**: Calls `kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED)` to inform the Windows power subsystem that the application requires the display and system to remain in a working state.
- **Desktop Context Isolation**: Calls `user32.OpenInputDesktop` to ensure background execution threads remain attached to the active interactive input desktop session without access-denied errors.

---

## 🧪 Testing

The repository includes a comprehensive unit test suite covering Bézier mathematical formulas, multi-monitor bounds resolution, user handoff thresholding, and engine lifecycle:

```powershell
python -m unittest discover -s tests -v
```

Automated testing and build verification are continuously validated across Python 3.10, 3.11, and 3.12 via GitHub Actions.

---

## 🔨 Building the Executable

You can compile the application, bundled fonts, and vector assets into a single standalone `.exe` using PyInstaller:

```powershell
pyinstaller AutoMouseMover.spec --noconfirm
```

The compiled binary will be generated in `dist/AutoMouseMover.exe`.

---

## ⌨️ Global Shortcuts & Controls

| Shortcut | Function | Context |
| :---: | :--- | :--- |
| **`F6`** | **Global Toggle**: Start / Stop mouse movement | Works globally across any active application or game |
| **`Space`** | Toggle Start / Stop | When the application window is focused |
| **`Esc`** | Minimize to background System Tray | When the application window is focused |

---

## 📄 License

This project is licensed under the **[MIT License](LICENSE)**.
