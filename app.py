"""
app.py
Ultra-Modern, Beautiful GUI for Auto Mouse Mover using CustomTkinter.
Supports Light/Dark mode, rounded cards, collapsible 1-click presets,
global F6 hotkey, and background System Tray mode (hidden from taskbar).
"""

import ctypes
from ctypes import wintypes
import os
import sys
import time
import threading
from typing import Optional

# Auto-resolve .venv site-packages if running from system Python
_venv_site_pkgs = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv", "Lib", "site-packages")
if os.path.isdir(_venv_site_pkgs) and _venv_site_pkgs not in sys.path:
    sys.path.insert(0, _venv_site_pkgs)

import customtkinter as ctk
from PIL import Image, ImageDraw
import pystray

from mover_engine import MoverEngine

APP_VERSION = "v1.0.0"

# Win32 Constants for Global Hotkey
WM_HOTKEY = 0x0312
VK_F6 = 0x75
HOTKEY_ID = 1001

# Auto-resolve resource paths for dev mode and PyInstaller bundle
def get_resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller bundle."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


try:
    # Set explicit AppUserModelID so Windows taskbar uses custom app icon
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("automousemover.app.v2")
    ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

def load_bundled_fonts():
    """Dynamically loads bundled Poppins TTF fonts into Windows process memory."""
    try:
        fonts_dir = get_resource_path(os.path.join("assets", "fonts"))
        if os.path.isdir(fonts_dir):
            FR_PRIVATE = 0x10
            for fname in os.listdir(fonts_dir):
                if fname.lower().endswith((".ttf", ".otf")):
                    fpath = os.path.abspath(os.path.join(fonts_dir, fname))
                    ctypes.windll.gdi32.AddFontResourceExW(fpath, FR_PRIVATE, 0)
    except Exception:
        pass


load_bundled_fonts()

# Set modern appearance
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")


def load_app_icon(name: str, color_light: str = "dark", color_dark: str = "light", size: tuple = (16, 16)) -> Optional[ctk.CTkImage]:
    """Loads a Lucide icon with light and dark mode variants."""
    try:
        path_l = get_resource_path(os.path.join("assets", "icons", f"{name}_{color_light}.png"))
        path_d = get_resource_path(os.path.join("assets", "icons", f"{name}_{color_dark}.png"))
        if os.path.exists(path_l) and os.path.exists(path_d):
            img_l = Image.open(path_l)
            img_d = Image.open(path_d)
            return ctk.CTkImage(light_image=img_l, dark_image=img_d, size=size)
        elif os.path.exists(path_l):
            img_l = Image.open(path_l)
            return ctk.CTkImage(light_image=img_l, dark_image=img_l, size=size)
    except Exception:
        pass
    return None


def load_tinted_icon(name: str, color: str = "white", size: tuple = (16, 16)) -> Optional[ctk.CTkImage]:
    """Loads a single-color Lucide icon (e.g. white for primary/danger buttons)."""
    try:
        path = get_resource_path(os.path.join("assets", "icons", f"{name}_{color}.png"))
        if os.path.exists(path):
            img = Image.open(path)
            return ctk.CTkImage(light_image=img, dark_image=img, size=size)
    except Exception:
        pass
    return None


def create_tray_image(status: str = "idle") -> Image.Image:
    """Generates a sharp 64x64 mouse tray icon from assets/mouse.png with status indicator."""
    mouse_png_path = get_resource_path(os.path.join("assets", "mouse.png"))
    if os.path.exists(mouse_png_path):
        try:
            base = Image.open(mouse_png_path).convert("RGBA")
            bbox = base.getbbox()
            if bbox:
                base = base.crop(bbox)
            w, h = base.size
            max_dim = max(w, h)
            square = Image.new("RGBA", (max_dim, max_dim), (0, 0, 0, 0))
            square.paste(base, ((max_dim - w) // 2, (max_dim - h) // 2), mask=base)
            tray = square.resize((64, 64), Image.Resampling.LANCZOS)

            draw = ImageDraw.Draw(tray)
            # Emerald green when running, Indigo when idle
            color = (16, 185, 129, 255) if status == "running" else (99, 102, 241, 255)
            # Status pip circle at bottom-right with high-contrast border
            draw.ellipse([(42, 42), (62, 62)], fill=(15, 17, 23, 255))
            draw.ellipse([(45, 45), (59, 59)], fill=color)
            return tray
        except Exception:
            pass

    # Fallback geometric icon
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    fill_color = (16, 185, 129, 255) if status == "running" else (99, 102, 241, 255)
    draw.rounded_rectangle([(14, 8), (50, 56)], radius=8, fill=fill_color)
    draw.rectangle([(30, 14), (34, 26)], fill=(255, 255, 255, 240))
    return img


class GlobalHotkeyThread(threading.Thread):
    """
    Background Windows message loop listening for global F6 hotkey.
    Allows toggling mouse movement from any active window or game,
    even when hidden in the background tray.
    """

    def __init__(self, on_hotkey):
        super().__init__(daemon=True)
        self.on_hotkey = on_hotkey
        self._stop_event = threading.Event()

    def run(self):
        user32 = ctypes.windll.user32
        res = user32.RegisterHotKey(None, HOTKEY_ID, 0, VK_F6)
        if not res:
            return

        msg = wintypes.MSG()
        while not self._stop_event.is_set():
            has_msg = user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1)
            if has_msg:
                if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                    self.on_hotkey()
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            else:
                time.sleep(0.04)

        user32.UnregisterHotKey(None, HOTKEY_ID)

    def stop(self):
        self._stop_event.set()


class ModernMouseMoverApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"Auto Mouse Mover {APP_VERSION}")

        # Fixed dimensions (fullscreen and window resizing disabled)
        self.geometry("460x570")
        self.resizable(False, False)
        self.configure(fg_color=("#f1f5f9", "#0f1117"))

        # Set Window & Taskbar Icon
        ico_file = get_resource_path("app_icon.ico")
        if not os.path.exists(ico_file):
            ico_file = get_resource_path(os.path.join("assets", "mouse.ico"))
        if os.path.exists(ico_file):
            try:
                self.iconbitmap(ico_file)
            except Exception:
                pass

        # State Variables
        self.current_theme = "Light"
        self.start_time: Optional[float] = None
        self.selected_mode = "human"
        self.mode_buttons = {}
        self.tray_icon: Optional[pystray.Icon] = None

        # Cohesive Dual-Color Palette (Primary Indigo Accent + Clean Slate Neutrals, Red for Stop)
        self.CLR_PRIMARY = "#4f46e5"         # Electric Indigo
        self.CLR_PRIMARY_HOVER = "#4338ca"   # Deep Indigo Hover
        self.CLR_DANGER = "#ef4444"          # Red for Stop & Destructive
        self.CLR_DANGER_HOVER = "#dc2626"

        self.CLR_TEXT_HEADER = ("#0f172a", "#f8fafc")       # Slate-900 / Slate-50
        self.CLR_TEXT_SECTION = ("#334155", "#cbd5e1")      # Slate-700 / Slate-300
        self.CLR_TEXT_BODY = ("#1e293b", "#e2e8f0")         # Slate-800 / Slate-200
        self.CLR_TEXT_MUTED = ("#64748b", "#94a3b8")        # Slate-500 / Slate-400
        self.CLR_CARD_BG = ("#ffffff", "#1e222d")           # White / Dark Card
        self.CLR_CARD_BORDER = ("#e2e8f0", "#2d3343")       # Slate-200 / Dark Border
        self.CLR_CHIP_BG = ("#f8fafc", "#282f3f")           # Chip Fill

        # Typography (Modern, clean Poppins)
        self.font_title = ctk.CTkFont(family="Poppins", size=16, weight="bold")
        self.font_h2 = ctk.CTkFont(family="Poppins", size=14, weight="bold")
        self.font_body = ctk.CTkFont(family="Poppins", size=11)
        self.font_body_bold = ctk.CTkFont(family="Poppins", size=11, weight="bold")
        self.font_caption = ctk.CTkFont(family="Poppins", size=10)
        self.font_caption_bold = ctk.CTkFont(family="Poppins", size=10, weight="bold")
        self.font_big_btn = ctk.CTkFont(family="Poppins", size=14, weight="bold")

        # Pre-load Lucide icons for UI elements
        self.icon_hide = load_app_icon("inbox", "dark", "light", (14, 14))
        self.icon_moon = load_app_icon("moon", "dark", "light", (14, 14))
        self.icon_sun = load_app_icon("sun", "dark", "light", (14, 14))
        self.icon_behavior = load_app_icon("mouse-pointer-2", "dark", "light", (14, 14))
        self.icon_timer = load_app_icon("timer", "dark", "light", (14, 14))

        self.icon_play = load_tinted_icon("play", "white", (16, 16))
        self.icon_stop = load_tinted_icon("square", "white", (14, 14))

        self.mode_icons = {
            "human": {
                "active": load_tinted_icon("wind", "white", (15, 15)),
                "inactive": load_app_icon("wind", "dark", "light", (15, 15)),
            },
            "stealth": {
                "active": load_tinted_icon("shield", "white", (15, 15)),
                "inactive": load_app_icon("shield", "dark", "light", (15, 15)),
            },
            "circle": {
                "active": load_tinted_icon("orbit", "white", (15, 15)),
                "inactive": load_app_icon("orbit", "dark", "light", (15, 15)),
            },
            "random_jump": {
                "active": load_tinted_icon("zap", "white", (15, 15)),
                "inactive": load_app_icon("zap", "dark", "light", (15, 15)),
            },
        }

        # Initialize Mover Engine
        self.engine = MoverEngine(
            on_move=self._on_engine_move,
            on_status_change=self._on_engine_status_change,
        )

        # Build Interface
        self._build_header()
        self._build_hero_status_card()
        self._build_modes_section()
        self._build_frequency_section()
        self._build_toggles_section()
        self._build_action_button()

        # Keyboard shortcuts
        self.bind("<F6>", lambda e: self.toggle_mover())
        self.bind("<space>", lambda e: self.toggle_mover())
        self.bind("<Escape>", lambda e: self.hide_to_background())

        # Global Hotkey Thread
        self.hotkey_thread = GlobalHotkeyThread(on_hotkey=self._on_global_hotkey)
        self.hotkey_thread.start()

        # Initialize System Tray in background thread
        self._init_tray_icon()

        # Close button behavior
        self.protocol("WM_DELETE_WINDOW", self._on_window_close_clicked)

        # Center dead-center on screen after all widgets are packed
        self.center_on_screen()

    def center_on_screen(self):
        """
        Calculates exact physical monitor work area (excluding taskbar)
        and positions the window dead-center on the primary display.
        """
        self.update_idletasks()

        # Determine physical scaled window size
        scaling = ctk.ScalingTracker.get_window_scaling(self)
        phys_w = round(460 * scaling)
        phys_h = round(570 * scaling)

        pos_x = None
        pos_y = None
        try:
            user32 = ctypes.windll.user32
            rect = wintypes.RECT()
            # SPI_GETWORKAREA = 0x0030: returns usable desktop area excluding taskbar
            if user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0):
                work_w = rect.right - rect.left
                work_h = rect.bottom - rect.top
                pos_x = rect.left + max(0, (work_w - phys_w) // 2)
                pos_y = rect.top + max(0, (work_h - phys_h) // 2)
        except Exception:
            pass

        if pos_x is None or pos_y is None:
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            pos_x = max(0, (sw - phys_w) // 2)
            pos_y = max(0, (sh - phys_h) // 2)

        self.geometry(f"460x570+{pos_x}+{pos_y}")

    # ------------------------------------------------------------------
    # System Tray & Background Execution
    # ------------------------------------------------------------------
    def _init_tray_icon(self):
        """Creates the background Windows System Tray icon."""
        menu = pystray.Menu(
            pystray.MenuItem("Show Window", self._tray_show_window, default=True),
            pystray.MenuItem(
                lambda text: "Stop Mover (F6)" if self.engine.is_running else "Start Mover (F6)",
                self._tray_toggle_mover,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit Application", self.quit_completely),
        )

        self.tray_icon = pystray.Icon(
            "AutoMouseMover",
            create_tray_image("idle"),
            f"Auto Mouse Mover {APP_VERSION} (F6 to toggle)",
            menu,
        )

        # Run tray loop in dedicated daemon thread
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def _update_tray_state(self, status: str):
        """Updates tray icon image and tooltip when status changes."""
        if self.tray_icon:
            try:
                self.tray_icon.icon = create_tray_image(status)
                tip = f"Auto Mouse Mover {APP_VERSION} (Running • F6)" if status == "running" else f"Auto Mouse Mover {APP_VERSION} (Idle • F6)"
                self.tray_icon.title = tip
            except Exception:
                pass

    def _tray_show_window(self, icon=None, item=None):
        self.after(0, self.restore_from_background)

    def _tray_toggle_mover(self, icon=None, item=None):
        self.after(0, self.toggle_mover)

    def hide_to_background(self):
        """Hides the window from screen AND Windows taskbar into the system tray."""
        self.withdraw()

    def restore_from_background(self):
        """Restores window from background to foreground."""
        self.deiconify()
        self.lift()
        self.focus_force()

    def _on_window_close_clicked(self):
        """When close (X) is clicked, ask whether to quit completely or minimize to tray."""
        if hasattr(self, "_close_dialog") and self._close_dialog and self._close_dialog.winfo_exists():
            self._close_dialog.lift()
            self._close_dialog.focus_force()
            return
        self._show_close_dialog()

    def _show_close_dialog(self):
        dialog = ctk.CTkToplevel(self)
        self._close_dialog = dialog
        dialog.title("Exit Auto Mouse Mover?")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        dialog.configure(fg_color=self.CLR_CARD_BG)

        # Set dialog icon if available
        ico_file = get_resource_path("app_icon.ico")
        if not os.path.exists(ico_file):
            ico_file = get_resource_path(os.path.join("assets", "mouse.ico"))
        if os.path.exists(ico_file):
            try:
                dialog.iconbitmap(ico_file)
                dialog.after(20, lambda: dialog.iconbitmap(ico_file))
            except Exception:
                pass

        # Content directly on window canvas (tight, balanced padding)
        content = ctk.CTkFrame(dialog, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=(8, 10))

        # Title
        title_lbl = ctk.CTkLabel(
            content,
            text="Exit Auto Mouse Mover?",
            font=self.font_h2,
            text_color=self.CLR_TEXT_HEADER,
            anchor="w",
        )
        title_lbl.pack(fill="x", pady=(0, 2))

        # Description
        desc_lbl = ctk.CTkLabel(
            content,
            text="Would you like to quit the application completely, or minimize it to run in the background system tray?",
            font=self.font_body,
            text_color=self.CLR_TEXT_MUTED,
            justify="left",
            wraplength=380,
            anchor="w",
        )
        desc_lbl.pack(fill="x", pady=(0, 10))

        # Action Buttons row
        btn_row = ctk.CTkFrame(content, fg_color="transparent")
        btn_row.pack(fill="x")

        def on_quit():
            dialog.destroy()
            self.quit_completely()

        def on_minimize():
            dialog.destroy()
            self.hide_to_background()

        def on_cancel():
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", on_cancel)
        dialog.bind("<Escape>", lambda e: on_cancel())

        icon_quit = load_tinted_icon("log-out", "white", (14, 14))
        icon_min = load_tinted_icon("inbox", "white", (14, 14))

        # Quit Button
        quit_btn = ctk.CTkButton(
            btn_row,
            text=" Quit",
            image=icon_quit,
            compound="left",
            font=self.font_body_bold,
            width=80,
            height=32,
            corner_radius=5,
            fg_color=self.CLR_DANGER,
            hover_color=self.CLR_DANGER_HOVER,
            text_color="#ffffff",
            command=on_quit,
        )
        quit_btn.pack(side="right", padx=(4, 0))

        # Minimize to Tray Button
        min_btn = ctk.CTkButton(
            btn_row,
            text=" Minimize to Tray",
            image=icon_min,
            compound="left",
            font=self.font_body_bold,
            width=135,
            height=32,
            corner_radius=5,
            fg_color=self.CLR_PRIMARY,
            hover_color=self.CLR_PRIMARY_HOVER,
            text_color="#ffffff",
            command=on_minimize,
        )
        min_btn.pack(side="right", padx=4)

        # Cancel Button
        cancel_btn = ctk.CTkButton(
            btn_row,
            text="Cancel",
            font=self.font_body,
            width=70,
            height=32,
            corner_radius=5,
            fg_color="transparent",
            hover_color=("#e2e8f0", "#282f3f"),
            text_color=self.CLR_TEXT_HEADER,
            border_width=1,
            border_color=self.CLR_CARD_BORDER,
            command=on_cancel,
        )
        cancel_btn.pack(side="right", padx=(0, 4))

        # Center on parent window
        self.update_idletasks()
        pw_x = self.winfo_x()
        pw_y = self.winfo_y()
        pw_w = self.winfo_width()
        pw_h = self.winfo_height()
        dlg_w, dlg_h = 420, 125
        pos_x = max(0, pw_x + (pw_w - dlg_w) // 2)
        pos_y = max(0, pw_y + (pw_h - dlg_h) // 2)
        dialog.geometry(f"{dlg_w}x{dlg_h}+{pos_x}+{pos_y}")

    def quit_completely(self, icon=None, item=None):
        """Exits the application completely."""
        self.stop_mover()
        try:
            self.hotkey_thread.stop()
        except Exception:
            pass
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        self.destroy()

    # ------------------------------------------------------------------
    # UI Building Blocks
    # ------------------------------------------------------------------
    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 8))

        # Title with custom logo
        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left")

        logo_path = get_resource_path(os.path.join("assets", "mouse.png"))
        logo_lbl = None
        if os.path.exists(logo_path):
            try:
                logo_pil = Image.open(logo_path).convert("RGBA")
                bbox = logo_pil.getbbox()
                if bbox:
                    logo_pil = logo_pil.crop(bbox)
                w, h = logo_pil.size
                max_dim = max(w, h)
                square = Image.new("RGBA", (max_dim, max_dim), (0, 0, 0, 0))
                square.paste(logo_pil, ((max_dim - w) // 2, (max_dim - h) // 2), mask=logo_pil)
                self.logo_ctk_img = ctk.CTkImage(
                    light_image=square,
                    dark_image=square,
                    size=(24, 24),
                )
                logo_lbl = ctk.CTkLabel(
                    title_box,
                    image=self.logo_ctk_img,
                    text="",
                    width=26,
                    height=26,
                )
            except Exception:
                logo_lbl = None

        if logo_lbl is None:
            logo_lbl = ctk.CTkLabel(
                title_box,
                text="🖱",
                font=ctk.CTkFont(family="Segoe UI Emoji", size=17),
                width=20,
            )
        logo_lbl.pack(side="left", padx=(0, 6))

        app_title = ctk.CTkLabel(
            title_box,
            text="Auto Mouse Mover",
            font=self.font_title,
            text_color=self.CLR_TEXT_HEADER,
        )
        app_title.pack(side="left")

        version_badge = ctk.CTkLabel(
            title_box,
            text=APP_VERSION,
            font=self.font_caption_bold,
            text_color=self.CLR_TEXT_MUTED,
            fg_color=("#e2e8f0", "#1e293b"),
            corner_radius=4,
            width=44,
            height=20,
        )
        version_badge.pack(side="left", padx=(8, 0))

        # Controls (Theme + Tray)
        controls_box = ctk.CTkFrame(header, fg_color="transparent")
        controls_box.pack(side="right")

        # Hide to background button
        self.tray_btn = ctk.CTkButton(
            controls_box,
            text=" Hide",
            image=self.icon_hide,
            compound="left",
            width=68,
            height=28,
            corner_radius=6,
            font=self.font_caption_bold,
            fg_color=("#e2e8f0", "#1e293b"),
            text_color=self.CLR_TEXT_HEADER,
            hover_color=("#cbd5e1", "#334155"),
            border_width=1,
            border_color=self.CLR_CARD_BORDER,
            command=self.hide_to_background,
        )
        self.tray_btn.pack(side="left", padx=(0, 5))

        self.theme_btn = ctk.CTkButton(
            controls_box,
            text=" Dark",
            image=self.icon_moon,
            compound="left",
            width=72,
            height=28,
            corner_radius=6,
            font=self.font_caption_bold,
            fg_color=("#e2e8f0", "#1e293b"),
            text_color=self.CLR_TEXT_HEADER,
            hover_color=("#cbd5e1", "#334155"),
            border_width=1,
            border_color=self.CLR_CARD_BORDER,
            command=self.toggle_theme,
        )
        self.theme_btn.pack(side="left")

    def _build_hero_status_card(self):
        self.hero_card = ctk.CTkFrame(
            self,
            corner_radius=8,
            fg_color=self.CLR_CARD_BG,
            border_width=1,
            border_color=self.CLR_CARD_BORDER,
        )
        self.hero_card.pack(fill="x", padx=16, pady=(0, 8))

        inner = ctk.CTkFrame(self.hero_card, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=10)

        # Status row
        top_row = ctk.CTkFrame(inner, fg_color="transparent")
        top_row.pack(fill="x")

        self.hero_badge = ctk.CTkLabel(
            top_row,
            text="● IDLE",
            font=self.font_caption_bold,
            fg_color=("#e2e8f0", "#282f3f"),
            text_color=("#1e293b", "#94a3b8"),
            corner_radius=4,
            padx=10,
            pady=4,
        )
        self.hero_badge.pack(side="left")

        # Big Headline & Subtitle
        self.hero_title = ctk.CTkLabel(
            inner,
            text="Auto Cursor is Off",
            font=self.font_h2,
            text_color=self.CLR_TEXT_HEADER,
            anchor="w",
        )
        self.hero_title.pack(fill="x", pady=(4, 2))

        self.hero_desc = ctk.CTkLabel(
            inner,
            text="Click START or press F6 anywhere to begin random movements.",
            font=self.font_body,
            text_color=self.CLR_TEXT_MUTED,
            anchor="w",
        )
        self.hero_desc.pack(fill="x")

    def _build_modes_section(self):
        section = ctk.CTkFrame(self, fg_color="transparent")
        section.pack(fill="x", padx=16, pady=(0, 8))

        lbl = ctk.CTkLabel(
            section,
            text="  MOVEMENT BEHAVIOR",
            image=self.icon_behavior,
            compound="left",
            font=self.font_caption_bold,
            text_color=self.CLR_TEXT_SECTION,
        )
        lbl.pack(anchor="w", pady=(0, 5))

        # 2x2 Grid of Mode Buttons
        grid_frame = ctk.CTkFrame(section, fg_color="transparent")
        grid_frame.pack(fill="x")
        grid_frame.columnconfigure(0, weight=1)
        grid_frame.columnconfigure(1, weight=1)

        modes = [
            ("human", "Smooth Wander", 0, 0),
            ("stealth", "Stealth Nudge", 0, 1),
            ("circle", "Gentle Circle", 1, 0),
            ("random_jump", "Random Jump", 1, 1),
        ]

        for mode_val, title, r, c in modes:
            btn = ctk.CTkButton(
                grid_frame,
                text=f"  {title}",
                font=self.font_body_bold,
                height=38,
                corner_radius=6,
                compound="left",
                command=lambda m=mode_val: self.select_mode(m),
            )
            btn.grid(row=r, column=c, sticky="nsew", padx=3, pady=3)
            self.mode_buttons[mode_val] = btn

        self._refresh_mode_buttons()

        self.mode_desc_lbl = ctk.CTkLabel(
            section,
            text="Organic cubic Bezier curved paths mimicking natural human hand movement.",
            font=self.font_caption,
            text_color=self.CLR_TEXT_MUTED,
            anchor="w",
        )
        self.mode_desc_lbl.pack(fill="x", pady=(3, 0), padx=2)

    def _refresh_mode_buttons(self):
        """Updates mode buttons style so active is highlighted and inactive are high-contrast."""
        for m_val, btn in self.mode_buttons.items():
            icons_dict = self.mode_icons.get(m_val, {})
            if m_val == self.selected_mode:
                btn.configure(
                    fg_color=self.CLR_PRIMARY,
                    hover_color=self.CLR_PRIMARY_HOVER,
                    text_color="#ffffff",
                    border_width=0,
                    image=icons_dict.get("active"),
                    compound="left",
                )
            else:
                btn.configure(
                    fg_color=self.CLR_CARD_BG,
                    hover_color=("#f1f5f9", "#282f3f"),
                    text_color=self.CLR_TEXT_HEADER,
                    border_width=1,
                    border_color=self.CLR_CARD_BORDER,
                    image=icons_dict.get("inactive"),
                    compound="left",
                )

    def _build_frequency_section(self):
        card = ctk.CTkFrame(
            self,
            corner_radius=8,
            fg_color=self.CLR_CARD_BG,
            border_width=1,
            border_color=self.CLR_CARD_BORDER,
        )
        card.pack(fill="x", padx=16, pady=(0, 8))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=10)

        top_row = ctk.CTkFrame(inner, fg_color="transparent")
        top_row.pack(fill="x")

        tk_lbl = ctk.CTkLabel(
            top_row,
            text="  MOVE FREQUENCY",
            image=self.icon_timer,
            compound="left",
            font=self.font_caption_bold,
            text_color=self.CLR_TEXT_SECTION,
        )
        tk_lbl.pack(side="left")

        self.freq_val_lbl = ctk.CTkLabel(
            top_row,
            text="Every 5s",
            font=self.font_body_bold,
            text_color=self.CLR_PRIMARY,
        )
        self.freq_val_lbl.pack(side="right")

        # Slider
        self.slider = ctk.CTkSlider(
            inner,
            from_=1,
            to=60,
            number_of_steps=59,
            height=18,
            corner_radius=4,
            button_corner_radius=6,
            button_color=self.CLR_PRIMARY,
            button_hover_color=self.CLR_PRIMARY_HOVER,
            progress_color=self.CLR_PRIMARY,
            command=self._on_slider_change,
        )
        self.slider.pack(fill="x", pady=(6, 8))
        self.slider.set(5)

        # Chips row
        chips_row = ctk.CTkFrame(inner, fg_color="transparent")
        chips_row.pack(fill="x")

        self.chip_buttons = {}
        for sec in [3, 5, 10, 15, 30, 60]:
            chip = ctk.CTkButton(
                chips_row,
                text=f"{sec}s",
                font=self.font_caption_bold,
                height=28,
                width=0,
                corner_radius=6,
                command=lambda s=sec: self.set_interval(s),
            )
            chip.pack(side="left", fill="x", expand=True, padx=2)
            self.chip_buttons[sec] = chip

        self._refresh_chip_buttons()

    def _refresh_chip_buttons(self):
        curr_val = int(self.slider.get())
        for sec, chip in self.chip_buttons.items():
            if sec == curr_val:
                chip.configure(
                    fg_color=self.CLR_PRIMARY,
                    hover_color=self.CLR_PRIMARY_HOVER,
                    text_color="#ffffff",
                    border_width=0,
                )
            else:
                chip.configure(
                    fg_color=self.CLR_CHIP_BG,
                    hover_color=("#e2e8f0", "#334155"),
                    text_color=self.CLR_TEXT_HEADER,
                    border_width=1,
                    border_color=self.CLR_CARD_BORDER,
                )

    def _build_toggles_section(self):
        section = ctk.CTkFrame(self, fg_color="transparent")
        section.pack(fill="x", padx=16, pady=(0, 8))

        self.awake_switch = ctk.CTkSwitch(
            section,
            text="Keep PC Awake (Prevent sleep, lock, & screensaver)",
            font=self.font_body,
            text_color=self.CLR_TEXT_HEADER,
            progress_color=self.CLR_PRIMARY,
            command=self._on_toggle_awake,
        )
        self.awake_switch.pack(anchor="w", pady=2)
        self.awake_switch.select()

        self.autopause_switch = ctk.CTkSwitch(
            section,
            text="Smart Handoff (Auto-pause when you touch the mouse)",
            font=self.font_body,
            text_color=self.CLR_TEXT_HEADER,
            progress_color=self.CLR_PRIMARY,
            command=self._on_toggle_autopause,
        )
        self.autopause_switch.pack(anchor="w", pady=2)
        self.autopause_switch.select()

    def _build_action_button(self):
        box = ctk.CTkFrame(self, fg_color="transparent")
        box.pack(fill="x", padx=16, pady=(0, 14))

        self.action_btn = ctk.CTkButton(
            box,
            text="  START MOVING  (F6)",
            image=self.icon_play,
            compound="left",
            font=self.font_big_btn,
            height=50,
            corner_radius=8,
            fg_color=self.CLR_PRIMARY,
            hover_color=self.CLR_PRIMARY_HOVER,
            text_color="#ffffff",
            command=self.toggle_mover,
        )
        self.action_btn.pack(fill="x")

    # ------------------------------------------------------------------
    # User Interactions & Handlers
    # ------------------------------------------------------------------
    def toggle_theme(self):
        if self.current_theme == "Light":
            self.current_theme = "Dark"
            ctk.set_appearance_mode("Dark")
            self.theme_btn.configure(text=" Light", image=self.icon_sun)
        else:
            self.current_theme = "Light"
            ctk.set_appearance_mode("Light")
            self.theme_btn.configure(text=" Dark", image=self.icon_moon)
        self._refresh_mode_buttons()
        self._refresh_chip_buttons()

    def select_mode(self, mode_val: str):
        descriptions = {
            "human": "Organic cubic Bezier curved paths mimicking natural human hand movement.",
            "stealth": "Imperceptible 1-2px jitter and return. Keeps status green with zero distraction.",
            "circle": "Gentle orbital circular movement around your current cursor position.",
            "random_jump": "Instant direct jump to random coordinates across your screen.",
        }
        self.selected_mode = mode_val
        self.engine.mode = mode_val
        self.mode_desc_lbl.configure(text=descriptions.get(mode_val, ""))
        self._refresh_mode_buttons()

    def set_interval(self, seconds: int):
        self.slider.set(seconds)
        self._on_slider_change(seconds)

    def _on_slider_change(self, val):
        sec = int(val)
        self.freq_val_lbl.configure(text=f"Every {sec}s")
        self.engine.interval_seconds = float(sec)
        self._refresh_chip_buttons()


    def _on_toggle_awake(self):
        self.engine.keep_awake = bool(self.awake_switch.get())
        if self.engine.is_running:
            from mover_engine import set_keep_awake
            set_keep_awake(self.engine.keep_awake)

    def _on_toggle_autopause(self):
        self.engine.auto_pause_on_user = bool(self.autopause_switch.get())

    def _on_global_hotkey(self):
        self.after(0, self.toggle_mover)

    def toggle_mover(self):
        if self.engine.is_running:
            self.stop_mover()
        else:
            self.start_mover()

    def start_mover(self):
        self.engine.mode = self.selected_mode
        self.engine.interval_seconds = float(int(self.slider.get()))
        self.engine.keep_awake = bool(self.awake_switch.get())
        self.engine.auto_pause_on_user = bool(self.autopause_switch.get())

        self.start_time = time.time()
        self.engine.start()

        self.action_btn.configure(
            text="  STOP MOVING  (F6)",
            image=self.icon_stop,
            compound="left",
            fg_color=self.CLR_DANGER,
            hover_color=self.CLR_DANGER_HOVER,
        )
        self._update_hero_ui("running")
        self._update_tray_state("running")

    def stop_mover(self):
        self.engine.stop()
        self.start_time = None
        self.action_btn.configure(
            text="  START MOVING  (F6)",
            image=self.icon_play,
            compound="left",
            fg_color=self.CLR_PRIMARY,
            hover_color=self.CLR_PRIMARY_HOVER,
        )
        self._update_hero_ui("stopped")
        self._update_tray_state("idle")

    def _on_engine_move(self, x: int, y: int):
        pass

    def _on_engine_status_change(self, status: str):
        self.after(0, lambda: self._update_hero_ui(status))

    def _update_hero_ui(self, status: str):
        if status == "running":
            self.hero_badge.configure(
                text="● RUNNING",
                fg_color=("#eef2ff", "#1e1b4b"),
                text_color=("#4f46e5", "#818cf8"),
            )
            self.hero_title.configure(text="Auto Cursor is Active")
            self.hero_desc.configure(text="Moving randomly. Sleep and away status are prevented.")
        elif status == "user_paused":
            self.hero_badge.configure(
                text="● USER ACTIVE",
                fg_color=("#fef3c7", "#78350f"),
                text_color=("#b45309", "#fbbf24"),
            )
            self.hero_title.configure(text="Auto-Paused for You")
            self.hero_desc.configure(text="You are moving the mouse. Resuming automatically when idle.")
        else:
            self.hero_badge.configure(
                text="● IDLE",
                fg_color=("#f1f5f9", "#282f3f"),
                text_color=("#64748b", "#94a3b8"),
            )
            self.hero_title.configure(text="Auto Cursor is Off")
            self.hero_desc.configure(text="Click START or press F6 anywhere to begin random movements.")


def run_app():
    try:
        app = ModernMouseMoverApp()
        app.mainloop()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        import traceback
        with open("crash.log", "w", encoding="utf-8") as f:
            traceback.print_exc(file=f)


if __name__ == "__main__":
    run_app()
