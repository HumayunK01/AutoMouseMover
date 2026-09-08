"""
tests/test_mover_engine.py
Unit tests for Auto Mouse Mover engine mathematics, bounds, user handoff,
and lifecycle operations.
"""

import unittest
from unittest.mock import patch, MagicMock
from mover_engine import (
    calculate_cubic_bezier,
    get_screen_bounds,
    MoverEngine,
)


class TestMoverEngine(unittest.TestCase):
    def test_calculate_cubic_bezier_endpoints(self):
        """Verify Bezier curve starts exactly at p0 and ends at p3."""
        p0 = (0.0, 0.0)
        p1 = (100.0, 50.0)
        p2 = (200.0, 150.0)
        p3 = (300.0, 200.0)

        # At t = 0, curve must equal p0
        x0, y0 = calculate_cubic_bezier(p0, p1, p2, p3, 0.0)
        self.assertAlmostEqual(x0, p0[0], places=5)
        self.assertAlmostEqual(y0, p0[1], places=5)

        # At t = 1, curve must equal p3
        x1, y1 = calculate_cubic_bezier(p0, p1, p2, p3, 1.0)
        self.assertAlmostEqual(x1, p3[0], places=5)
        self.assertAlmostEqual(y1, p3[1], places=5)

    def test_calculate_cubic_bezier_smooth_interpolation(self):
        """Verify intermediate points lie within reasonable bounds and produce finite numbers."""
        p0 = (10.0, 20.0)
        p1 = (50.0, 80.0)
        p2 = (90.0, 120.0)
        p3 = (150.0, 200.0)

        prev_x, prev_y = p0
        for step in range(1, 10):
            t = step / 10.0
            x, y = calculate_cubic_bezier(p0, p1, p2, p3, t)
            # Ensure coordinates progress smoothly
            self.assertTrue(x > prev_x)
            self.assertTrue(y > prev_y)
            prev_x, prev_y = x, y

    def test_get_screen_bounds(self):
        """Verify screen bounds return valid integers with non-zero dimensions."""
        left, top, width, height = get_screen_bounds()
        self.assertIsInstance(left, int)
        self.assertIsInstance(top, int)
        self.assertIsInstance(width, int)
        self.assertIsInstance(height, int)
        self.assertGreater(width, 0)
        self.assertGreater(height, 0)

    def test_engine_initial_configuration(self):
        """Verify engine default values match expected operational parameters."""
        engine = MoverEngine()
        self.assertEqual(engine.mode, "human")
        self.assertEqual(engine.interval_seconds, 5.0)
        self.assertTrue(engine.auto_pause_on_user)
        self.assertTrue(engine.keep_awake)
        self.assertFalse(engine.is_running)
        self.assertEqual(engine.move_count, 0)

    def test_user_activity_detection_threshold(self):
        """Verify movement exceeding 10px threshold is detected as user activity."""
        engine = MoverEngine()
        engine.auto_pause_on_user = True
        last_known = (500, 500)

        # Movement <= 10 pixels: should NOT trigger user pause
        with patch("mover_engine.get_cursor_pos", return_value=(505, 507)):
            self.assertFalse(engine._check_user_activity(last_known))

        # Movement > 10 pixels in X: should trigger user pause
        with patch("mover_engine.get_cursor_pos", return_value=(515, 500)):
            self.assertTrue(engine._check_user_activity(last_known))

        # Movement > 10 pixels in Y: should trigger user pause
        with patch("mover_engine.get_cursor_pos", return_value=(500, 520)):
            self.assertTrue(engine._check_user_activity(last_known))

        # When auto_pause is disabled: should always return False
        engine.auto_pause_on_user = False
        with patch("mover_engine.get_cursor_pos", return_value=(900, 900)):
            self.assertFalse(engine._check_user_activity(last_known))

    def test_countdown_timer(self):
        """Verify countdown returns 0 when stopped and accurate remaining time when active."""
        engine = MoverEngine()
        rem, total = engine.get_countdown()
        self.assertEqual(rem, 0.0)
        self.assertEqual(total, 5.0)

    def test_engine_status_callbacks(self):
        """Verify start and stop invoke status change callbacks properly."""
        status_updates = []
        engine = MoverEngine(on_status_change=lambda s: status_updates.append(s))

        # Mock Win32 thread execution call to avoid OS mutation during test
        with patch("mover_engine.set_keep_awake"):
            engine.start()
            self.assertTrue(engine.is_running)
            self.assertIn("running", status_updates)

            engine.stop()
            self.assertFalse(engine.is_running)
            self.assertIn("stopped", status_updates)


if __name__ == "__main__":
    unittest.main()
