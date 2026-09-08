# 🖱️ Auto Mouse Mover

A modern, beautiful, and lightweight Windows desktop application that simulates natural, automated cursor movements to keep your computer active, prevent idle sleep/screensavers, and maintain away status across communication platforms (Microsoft Teams, Slack, Zoom, Skype).

---

## ✨ Features

- **🌊 4 Natural Movement Modes**:
  - **Smooth Wander**: Organic cubic Bézier curved paths that mimic human hand movement.
  - **Stealth Nudge**: Subtle 1–2px micro-movement (keeps status active with zero visual distraction).
  - **Gentle Circle**: Smooth orbital circular drift around your current cursor position.
  - **Random Jump**: Direct instant jump to coordinates across your display.
- **🎨 Modern Aesthetic UI**:
  - **Dual-Color Palette**: Electric Indigo primary brand accent with neutral slate surfaces and dedicated high-contrast Crimson Red reserved exclusively for stop and destructive quit actions.
  - **Crisp Vector Icons**: Built with the official Lucide icon library supporting dynamic light and dark appearance modes.
  - **Poppins Typography**: Bundled high-legibility modern sans-serif fonts.
  - **Refined Geometry**: Sleek modern rounded corners and dead-center screen launching on any display resolution and DPI scale.
- **⌨️ Global Hotkey (F6)**:
  - Press **`F6`** from anywhere on your keyboard—even when playing games or working in fullscreen apps—to instantly start or stop mouse movement.
- **📥 Background System Tray Mode**:
  - Click **Hide**, press **`Esc`**, or click the **`[X]` close button** to access the exit dialog: minimize directly into the Windows System Tray (hidden from the taskbar) or quit completely.
  - Right-click or left-click the tray icon anytime to restore the window or toggle movement.
- **🛡️ Smart User Handoff**:
  - Automatically pauses simulation the instant you touch your mouse, ensuring the app never fights with your active work, and resumes seamlessly when you become idle.
- **☕ Keep PC Awake**:
  - Directly interfaces with Windows Win32 API (`SetThreadExecutionState`) to prevent display dimming, lock screens, and sleep timers.
- **🌙 Light & Dark Modes**:
  - One-click instant theme toggle with high-contrast active and inactive states.

---

## 🚀 Getting Started

### Option 1: Standalone Application (.exe) — *No Python Required*

1. Download or run **`AutoMouseMover.exe`**.
2. *(Optional)* Run **`CreateDesktopShortcut.bat`** to generate a desktop shortcut with the official app icon.

### Option 2: Run from Source

#### Prerequisites
- Windows 10 or Windows 11 (64-bit)
- Python 3.10 or newer

#### Installation & Setup

```powershell
# 1. Clone the repository
git clone https://github.com/HumayunK01/AutoMouseMover.git
cd AutoMouseMover

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch the application
python main.py
```

Or simply double-click **`run.bat`** to launch directly using the virtual environment.

---

## 🔨 Building the Standalone Executable

You can compile the entire application, bundled fonts, and Lucide vector icons into a single standalone `.exe` using PyInstaller:

```powershell
# Make sure your virtual environment is active
pip install -r requirements.txt

# Build the executable
pyinstaller AutoMouseMover.spec --noconfirm
```

The compiled binary will be generated in `dist/AutoMouseMover.exe`.

---

## 📁 Project Structure

```
AutoMouseMover/
├── assets/
│   ├── fonts/               # Bundled Poppins TTF fonts
│   ├── icons/               # Pre-rendered multi-theme Lucide vector icon PNGs
│   ├── mouse.ico            # High-resolution application & tray icon
│   └── mouse.png            # Official logo graphic
├── scripts/
│   └── generate_icons.py    # Utility script to re-generate multi-theme Lucide icons
├── app.py                   # CustomTkinter GUI layout, theming, and system tray
├── mover_engine.py          # Mouse movement math, Bezier curves, Win32 hooks
├── main.py                  # Application entry point
├── requirements.txt         # Python package dependencies
├── AutoMouseMover.spec      # PyInstaller compilation specification
├── CreateDesktopShortcut.bat# Windows batch script to create desktop shortcut
├── run.bat                  # Windows batch launcher script
├── .gitignore               # Git ignore rules
└── README.md                # Project documentation
```

---

## ⌨️ Keyboard Shortcuts

| Key | Action |
| :---: | :--- |
| **`F6`** | **Global Hotkey**: Toggle Start / Stop from any application or game |
| **`Space`** | Toggle Start / Stop when the window is focused |
| **`Esc`** | Minimize to background system tray |

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
