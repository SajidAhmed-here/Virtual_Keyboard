"""
utils.py - Utility functions for the virtual keyboard project
Includes: smoothing, FPS counter, color helpers, debouncer, hold detector
"""

import cv2
import numpy as np
from collections import deque
from datetime import datetime


class Smoother:
    """
    Exponential moving average smoother for hand landmark positions.

    Formula:
        filtered = alpha * new_value + (1 - alpha) * previous_filtered

    alpha=1.0 → no smoothing (raw input)
    alpha=0.1 → heavy smoothing (very laggy but stable)
    alpha=0.5 → balanced (recommended default)
    """

    def __init__(self, alpha=0.5):
        self.alpha = alpha
        self.filtered = None

    def filter(self, point):
        """Apply exponential smoothing to a numpy point (x, y)."""
        if self.filtered is None:
            self.filtered = point.copy()
        else:
            self.filtered = self.alpha * point + (1 - self.alpha) * self.filtered
        return self.filtered.copy()

    def reset(self):
        """Reset smoother state (call when hand is lost)."""
        self.filtered = None


class FPSCounter:
    """Tracks and displays frames per second."""

    def __init__(self):
        self.previous_time = 0
        self.fps = 0
        self.fps_history = deque(maxlen=30)

    def update(self):
        current_time = datetime.now().timestamp()
        if self.previous_time > 0:
            delta = current_time - self.previous_time
            if delta > 0:
                self.fps = int(1 / delta)
                self.fps_history.append(self.fps)
        self.previous_time = current_time
        return self.fps

    def get_average_fps(self):
        if not self.fps_history:
            return 0
        return int(np.mean(self.fps_history))

    def draw_fps(self, frame, position=(10, 30)):
        cv2.putText(frame, f"FPS: {self.fps}", position,
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        return frame


class Debouncer:
    """
    Prevents repeated triggers within a cooldown window.

    Why needed:
        At 30 FPS a hand stays over a key for ~500ms = ~15 frames.
        Without debounce that would type the same key 15 times.
        With 300ms cooldown only 1 press is registered.
    """

    def __init__(self, cooldown_ms=300):
        self.cooldown_ms = cooldown_ms
        self.last_trigger_time = 0

    def can_trigger(self):
        current_time = datetime.now().timestamp() * 1000
        return (current_time - self.last_trigger_time) >= self.cooldown_ms

    def trigger(self):
        self.last_trigger_time = datetime.now().timestamp() * 1000

    def reset(self):
        self.last_trigger_time = 0


class HoldDetector:
    """
    Detects a sustained hold gesture for continuous operations.

    Workflow:
        1. First press → immediate action (is_pressing=True)
        2. Hold for hold_threshold_ms → start repeating
        3. Repeat every repeat_interval_ms until released

    Used for: holding Backspace to continuously delete characters.
    """

    def __init__(self, hold_threshold_ms=500, repeat_interval_ms=100):
        self.hold_threshold_ms = hold_threshold_ms
        self.repeat_interval_ms = repeat_interval_ms
        self.press_start_time = 0
        self.last_repeat_time = 0
        self.is_holding = False

    def update(self, is_pressed):
        """
        Call every frame with the current press state.
        Returns True when an action should fire.
        """
        current_time = datetime.now().timestamp() * 1000

        if is_pressed:
            if not self.is_holding:
                # First contact — fire immediately
                self.is_holding = True
                self.press_start_time = current_time
                self.last_repeat_time = current_time
                return True
            else:
                time_held = current_time - self.press_start_time
                time_since_repeat = current_time - self.last_repeat_time
                if (time_held >= self.hold_threshold_ms
                        and time_since_repeat >= self.repeat_interval_ms):
                    self.last_repeat_time = current_time
                    return True
                return False
        else:
            self.is_holding = False
            return False

    def reset(self):
        self.is_holding = False
        self.press_start_time = 0
        self.last_repeat_time = 0


# ── Color helpers ──────────────────────────────────────────────────────────────

def get_key_color(is_hovered, is_pressed, is_dark_theme=False):
    """Return BGR key fill color based on state."""
    if is_pressed:
        return (0, 100, 255) if is_dark_theme else (0, 200, 255)
    elif is_hovered:
        return (60, 130, 230) if is_dark_theme else (100, 180, 255)
    else:
        return (45, 45, 55) if is_dark_theme else (210, 210, 220)


def get_text_color(is_dark_theme=False):
    return (230, 230, 230) if is_dark_theme else (20, 20, 20)


def get_background_color(is_dark_theme=False):
    return (18, 18, 28) if is_dark_theme else (235, 235, 245)


# ── Geometry helpers ───────────────────────────────────────────────────────────

def calculate_distance(p1, p2):
    """Euclidean distance between two (x, y) points."""
    return np.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


def point_in_rectangle(point, rect):
    """Return True if point (x,y) is inside rect (x, y, w, h)."""
    x, y, w, h = rect
    return x <= point[0] <= x + w and y <= point[1] <= y + h
