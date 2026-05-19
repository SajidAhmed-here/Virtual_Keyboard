"""
gesture_detector.py – Click and wave gesture detection
"""

import numpy as np
from datetime import datetime
from collections import deque
from utils import Debouncer, calculate_distance


class GestureDetector:
    def __init__(self, click_threshold=0.05, wave_threshold=150, wave_window_seconds=2.0):
        self.click_threshold = click_threshold
        self.wave_threshold = wave_threshold
        self.wave_window_seconds = wave_window_seconds

        self.click_debouncer = Debouncer(cooldown_ms=300)

        # Wave state
        self.wave_direction = None
        self.wave_count = 0
        self.wave_timestamps = deque(maxlen=10)
        self.last_centroid_x = None
        self.last_centroid_velocity = 0
        self.min_x = float('inf')
        self.max_x = float('-inf')
        self.direction_persistence_count = 0

        self.wave_debouncer = Debouncer(cooldown_ms=1500)
        self.is_clicking = False

    def detect_click(self, index_tip, thumb_tip, frame_shape):
        if index_tip is None or thumb_tip is None:
            self.is_clicking = False
            return False

        distance = calculate_distance(index_tip, thumb_tip)
        normalized = distance / frame_shape[1]
        is_pinch = normalized < self.click_threshold

        if is_pinch:
            if not self.is_clicking and self.click_debouncer.can_trigger():
                self.is_clicking = True
                self.click_debouncer.trigger()
                return True
            self.is_clicking = True
            return False
        else:
            self.is_clicking = False
            return False

    def detect_wave(self, centroid_x):
        if centroid_x is None:
            return 0

        current_time = datetime.now().timestamp()
        while self.wave_timestamps and (current_time - self.wave_timestamps[0]) > self.wave_window_seconds:
            self.wave_timestamps.popleft()

        if self.last_centroid_x is None:
            self.last_centroid_x = centroid_x
            self.min_x = centroid_x
            self.max_x = centroid_x
            return 0

        velocity = centroid_x - self.last_centroid_x
        abs_velocity = abs(velocity)
        min_velocity = 20  # ignore tiny jitter

        if abs_velocity > min_velocity:
            current_direction = 'left' if velocity < 0 else 'right'

            if current_direction == self.wave_direction:
                self.direction_persistence_count += 1
            else:
                self.direction_persistence_count = 1
                self.wave_direction = current_direction

            self.min_x = min(self.min_x, centroid_x)
            self.max_x = max(self.max_x, centroid_x)

            amplitude = self.max_x - self.min_x
            if amplitude > self.wave_threshold and self.direction_persistence_count >= 2:
                # Complete wave detected
                self.min_x = centroid_x
                self.max_x = centroid_x
                self.direction_persistence_count = 0
                self.wave_count += 1
                self.wave_timestamps.append(current_time)

        self.last_centroid_x = centroid_x
        self.last_centroid_velocity = velocity

        if self.wave_count >= 3 and self.wave_debouncer.can_trigger():
            waves = self.wave_count
            self.wave_count = 0
            self.wave_direction = None
            self.min_x = float('inf')
            self.max_x = float('-inf')
            self.last_centroid_x = None
            self.last_centroid_velocity = 0
            self.direction_persistence_count = 0
            self.wave_debouncer.trigger()
            return waves

        return 0

    def reset_wave_counter(self):
        self.wave_count = 0
        self.wave_direction = None
        self.min_x = float('inf')
        self.max_x = float('-inf')
        self.last_centroid_x = None
        self.last_centroid_velocity = 0
        self.direction_persistence_count = 0
        self.wave_timestamps.clear()

    def get_click_state(self):
        return self.is_clicking