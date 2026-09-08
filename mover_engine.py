"""
mover_engine.py
Windows Mouse Movement Engine using Win32 ctypes.
Handles natural Bezier curve movement, stealth nudges, sleep prevention,
and user-activity detection.
"""

import ctypes
import math
import random
import time
import threading
from typing import Callable, Optional, Tuple

# Win32 Constants
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

SM_CXSCREEN = 0
SM_CYSCREEN = 1
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79

MOUSEEVENTF_MOVE = 0x0001
DESKTOP_ALL = 0x01FF


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def ensure_input_desktop():
    """
    Ensures the current thread is attached to the active interactive input desktop.
    Fixes ERROR_ACCESS_DENIED (5) when running in background threads or subshells.
    """
    try:
        user32 = ctypes.windll.user32
        h_desk = user32.OpenInputDesktop(0, False, DESKTOP_ALL)
        if h_desk:
            user32.SetThreadDesktop(h_desk)
            user32.CloseDesktop(h_desk)
    except Exception:
        pass


def get_cursor_pos() -> Tuple[int, int]:
    """Get current cursor screen position."""
    ensure_input_desktop()
    pt = POINT()
    res = ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    if not res:
        # Retry with fresh desktop attach if failed
        ensure_input_desktop()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return int(pt.x), int(pt.y)


def set_cursor_pos(x: int, y: int):
    """Set cursor screen position and send input event."""
    ensure_input_desktop()
    ctypes.windll.user32.SetCursorPos(int(x), int(y))
    # Send a zero-delta mouse event to trigger OS input activity flags
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_MOVE, 0, 0, 0, 0)


def get_screen_bounds() -> Tuple[int, int, int, int]:
    """
    Get virtual screen bounds (supports multi-monitor setups).
    Returns (left, top, width, height).
    """
    user32 = ctypes.windll.user32
    left = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    top = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    width = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    height = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)

    # Fallback to primary monitor if virtual screen metrics are 0
    if width <= 0 or height <= 0:
        left = 0
        top = 0
        width = user32.GetSystemMetrics(SM_CXSCREEN)
        height = user32.GetSystemMetrics(SM_CYSCREEN)

    return left, top, width, height


def set_keep_awake(enabled: bool):
    """
    Inform Windows to prevent display sleep and system idle sleep while enabled.
    """
    kernel32 = ctypes.windll.kernel32
    if enabled:
        flags = ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
        kernel32.SetThreadExecutionState(flags)
    else:
        kernel32.SetThreadExecutionState(ES_CONTINUOUS)


def calculate_cubic_bezier(p0, p1, p2, p3, t):
    """Calculate point on cubic Bezier curve for parameter t in [0, 1]."""
    u = 1.0 - t
    tt = t * t
    uu = u * u
    uuu = uu * u
    ttt = tt * t

    x = uuu * p0[0] + 3 * uu * t * p1[0] + 3 * u * tt * p2[0] + ttt * p3[0]
    y = uuu * p0[1] + 3 * uu * t * p1[1] + 3 * u * tt * p2[1] + ttt * p3[1]
    return x, y


class MoverEngine:
    def __init__(
        self,
        on_move: Optional[Callable[[int, int], None]] = None,
        on_status_change: Optional[Callable[[str], None]] = None,
    ):
        self.on_move = on_move
        self.on_status_change = on_status_change

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Configurable Settings
        self.mode = "human"  # 'human', 'stealth', 'random_jump', 'circle'
        self.interval_seconds = 5.0
        self.interval_random_range = 1.5  # +/- random variation
        self.keep_awake = True
        self.auto_pause_on_user = True
        self.user_pause_duration = 3.5  # seconds to pause if user moves mouse

        # Tracking
        self.move_count = 0
        self.last_engine_pos: Optional[Tuple[int, int]] = None
        self.next_move_timestamp = 0.0
        self.current_wait_seconds = 5.0

    @property
    def is_running(self) -> bool:
        return self._running

    def get_countdown(self) -> Tuple[float, float]:
        """Returns (seconds_remaining, total_wait_duration)."""
        if not self._running or self.next_move_timestamp == 0.0:
            return 0.0, max(1.0, self.interval_seconds)
        rem = max(0.0, self.next_move_timestamp - time.time())
        return rem, max(1.0, self.current_wait_seconds)

    def start(self):
        """Start the mouse mover engine in background thread."""
        if self._running:
            return

        self._running = True
        self._stop_event.clear()

        if self.keep_awake:
            set_keep_awake(True)

        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        if self.on_status_change:
            self.on_status_change("running")

    def stop(self):
        """Stop the mouse mover engine."""
        if not self._running:
            return

        self._running = False
        self._stop_event.set()
        self.next_move_timestamp = 0.0

        if self.keep_awake:
            set_keep_awake(False)

        if self.on_status_change:
            self.on_status_change("stopped")

    def _notify_move(self, x: int, y: int):
        self.move_count += 1
        self.last_engine_pos = (x, y)
        if self.on_move:
            try:
                self.on_move(x, y)
            except Exception:
                pass

    def _check_user_activity(self, last_known_pos: Tuple[int, int]) -> bool:
        """
        Check if user has moved the mouse physically by comparing
        current position with expected position.
        """
        if not self.auto_pause_on_user or last_known_pos is None:
            return False

        cur_x, cur_y = get_cursor_pos()
        dx = abs(cur_x - last_known_pos[0])
        dy = abs(cur_y - last_known_pos[1])
        # A movement threshold of 10 pixels indicates intentional user movement
        return (dx > 10) or (dy > 10)

    def _run_loop(self):
        """Main background loop."""
        ensure_input_desktop()
        self.last_engine_pos = get_cursor_pos()

        while not self._stop_event.is_set():
            # Check if user moved mouse manually
            cur_pos = get_cursor_pos()
            if self._check_user_activity(self.last_engine_pos):
                if self.on_status_change:
                    self.on_status_change("user_paused")
                # Wait for user pause duration in increments of 0.2s
                pause_time = self.user_pause_duration
                while pause_time > 0 and not self._stop_event.is_set():
                    time.sleep(0.2)
                    pause_time -= 0.2
                    new_pos = get_cursor_pos()
                    if abs(new_pos[0] - cur_pos[0]) > 5 or abs(new_pos[1] - cur_pos[1]) > 5:
                        cur_pos = new_pos
                        pause_time = self.user_pause_duration

                if self.on_status_change and not self._stop_event.is_set():
                    self.on_status_change("running")

                self.last_engine_pos = get_cursor_pos()

            if self._stop_event.is_set():
                break

            # Execute movement according to chosen mode
            try:
                if self.mode == "human":
                    self._move_human()
                elif self.mode == "stealth":
                    self._move_stealth()
                elif self.mode == "random_jump":
                    self._move_jump()
                elif self.mode == "circle":
                    self._move_circle()
                else:
                    self._move_human()
            except Exception:
                pass

            # Calculate wait time with slight randomization
            jitter = random.uniform(
                -min(self.interval_random_range, self.interval_seconds * 0.4),
                min(self.interval_random_range, self.interval_seconds * 0.4),
            )
            wait_seconds = max(0.5, self.interval_seconds + jitter)
            self.current_wait_seconds = wait_seconds
            self.next_move_timestamp = time.time() + wait_seconds

            # Sleep in small slices to remain responsive to stop events
            elapsed = 0.0
            slice_sec = 0.1
            while elapsed < wait_seconds and not self._stop_event.is_set():
                if self._check_user_activity(self.last_engine_pos):
                    break
                time.sleep(slice_sec)
                elapsed += slice_sec

    def _move_human(self):
        """
        Smooth, natural curved movement to a random point within screen bounds.
        Uses cubic Bezier curves with ease-in/ease-out acceleration.
        """
        start_x, start_y = get_cursor_pos()
        left, top, width, height = get_screen_bounds()

        margin_x = int(width * 0.15)
        margin_y = int(height * 0.15)
        min_x = left + margin_x
        max_x = left + width - margin_x
        min_y = top + margin_y
        max_y = top + height - margin_y

        target_x = random.randint(min_x, max_x)
        target_y = random.randint(min_y, max_y)

        dx = target_x - start_x
        dy = target_y - start_y
        dist = math.hypot(dx, dy)

        if dist < 10:
            target_x = (target_x + 100) if target_x < max_x - 100 else (target_x - 100)
            dx = target_x - start_x
            dist = math.hypot(dx, dy)

        perp_x = -dy
        perp_y = dx
        perp_len = math.hypot(perp_x, perp_y)
        if perp_len > 0:
            perp_x /= perp_len
            perp_y /= perp_len

        arc_strength = random.uniform(-0.35, 0.35) * dist

        ctrl1_x = start_x + dx * 0.33 + perp_x * arc_strength
        ctrl1_y = start_y + dy * 0.33 + perp_y * arc_strength

        ctrl2_x = start_x + dx * 0.66 + perp_x * (arc_strength * random.uniform(0.5, 1.2))
        ctrl2_y = start_y + dy * 0.66 + perp_y * (arc_strength * random.uniform(0.5, 1.2))

        steps = max(25, min(80, int(dist / 12)))
        duration = random.uniform(0.4, 0.8)
        sleep_per_step = duration / steps

        p0 = (start_x, start_y)
        p1 = (ctrl1_x, ctrl1_y)
        p2 = (ctrl2_x, ctrl2_y)
        p3 = (target_x, target_y)

        for i in range(1, steps + 1):
            if self._stop_event.is_set():
                break

            t = i / steps
            eased_t = t * t * (3 - 2 * t)

            cx, cy = calculate_cubic_bezier(p0, p1, p2, p3, eased_t)
            set_cursor_pos(int(cx), int(cy))
            self.last_engine_pos = (int(cx), int(cy))

            time.sleep(sleep_per_step)

        self._notify_move(target_x, target_y)

    def _move_stealth(self):
        """
        Ultra subtle 2-pixel nudge and return with hardware mouse_event.
        """
        orig_x, orig_y = get_cursor_pos()
        dx = random.choice([-2, 2])
        dy = random.choice([-2, 2])

        # Nudge
        set_cursor_pos(orig_x + dx, orig_y + dy)
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_MOVE, dx, dy, 0, 0)
        self.last_engine_pos = (orig_x + dx, orig_y + dy)
        time.sleep(0.08)

        # Return back
        set_cursor_pos(orig_x, orig_y)
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_MOVE, -dx, -dy, 0, 0)
        self.last_engine_pos = (orig_x, orig_y)

        self._notify_move(orig_x, orig_y)

    def _move_jump(self):
        """Direct random jump to a random location."""
        left, top, width, height = get_screen_bounds()
        target_x = random.randint(left + 80, left + width - 80)
        target_y = random.randint(top + 80, top + height - 80)

        set_cursor_pos(target_x, target_y)
        self._notify_move(target_x, target_y)

    def _move_circle(self):
        """Moves cursor in a gentle circle around its current location."""
        center_x, center_y = get_cursor_pos()
        radius = random.randint(40, 80)
        steps = 40
        duration = random.uniform(0.6, 1.0)
        sleep_step = duration / steps

        for i in range(steps + 1):
            if self._stop_event.is_set():
                break
            angle = (i / steps) * 2 * math.pi
            cx = center_x + radius * math.cos(angle)
            cy = center_y + radius * math.sin(angle)
            set_cursor_pos(int(cx), int(cy))
            self.last_engine_pos = (int(cx), int(cy))
            time.sleep(sleep_step)

        self._notify_move(center_x, center_y)
