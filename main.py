"""
main.py – Virtual Keyboard application (configuration via .env)
Changes:
  - DWELL TYPING: hovering index finger over a key for DWELL_TIME seconds
    triggers the keypress automatically — no pinch needed.
  - Pinch still works too (instant press as before).
  - keyboard.set_dwell_progress() called every frame to animate the arc.
  - frame_h passed to update_hover() so rects are always bottom-pinned.
  - message_clear_counter actually counts down.
  - Backspace hold uses continuous is_clicking state.
"""

import os
import cv2
import sys
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # .env is optional

from hand_tracker     import HandTracker
from gesture_detector import GestureDetector
from virtual_keyboard import VirtualKeyboard
from utils import FPSCounter, HoldDetector


class VirtualKeyboardApp:

    def __init__(self):
        cv2.setUseOptimized(True)

        # ── Config ────────────────────────────────────────────────────────────
        self.screen_width  = int(os.getenv("CAMERA_WIDTH",  1280))
        self.screen_height = int(os.getenv("CAMERA_HEIGHT",  720))
        camera_index       = int(os.getenv("CAMERA_INDEX",     0))

        confidence      = float(os.getenv("HAND_CONFIDENCE_THRESHOLD", 0.65))
        smoothing       = float(os.getenv("SMOOTHING_ALPHA",           0.55))
        click_threshold = float(os.getenv("CLICK_THRESHOLD",           0.07))
        wave_threshold  = float(os.getenv("WAVE_THRESHOLD",            150))
        wave_window     = float(os.getenv("WAVE_WINDOW_SECONDS",         2.0))
        kb_width_ratio  = float(os.getenv("KEYBOARD_WIDTH_RATIO",       0.88))
        kb_height       = int(os.getenv("KEYBOARD_HEIGHT",              200))   # shorter
        dark_theme      = os.getenv("DARK_THEME", "True").lower() == "true"
        fps_limit       = int(os.getenv("FPS_LIMIT",                     60))
        kb_alpha        = float(os.getenv("KB_ALPHA",                   0.35))  # iOS feel

        # Dwell time in seconds — how long finger must hover before key fires
        self.dwell_time = float(os.getenv("DWELL_TIME", 1.5))

        self.wait_delay = max(1, int(1000 / fps_limit))

        # ── Subsystems ────────────────────────────────────────────────────────
        self.hand_tracker = HandTracker(
            confidence_threshold=confidence,
            smoothing_alpha=smoothing
        )
        self.gesture_detector = GestureDetector(
            click_threshold=click_threshold,
            wave_threshold=wave_threshold,
            wave_window_seconds=wave_window
        )

        kb_w = int(self.screen_width * kb_width_ratio)
        kb_x = int(self.screen_width * (1 - kb_width_ratio) / 2)
        self.keyboard = VirtualKeyboard(
            keyboard_width=kb_w,
            keyboard_height=kb_height,
            is_dark_theme=dark_theme,
            position=(kb_x, 0),      # Y ignored; keyboard auto-pins to bottom
            alpha=kb_alpha
        )

        self.fps_counter    = FPSCounter()
        self.backspace_hold = HoldDetector(hold_threshold_ms=450, repeat_interval_ms=80)

        self.current_text          = ""
        self.wave_trigger_message  = ""
        self.message_clear_counter = 0

        # ── Dwell state ───────────────────────────────────────────────────────
        # Which key the finger started dwelling on, and when
        self._dwell_key       = None
        self._dwell_start     = 0.0    # timestamp in seconds
        # After a dwell fires, ignore the SAME key for this cooldown (seconds)
        self._dwell_cooldown  = 0.8
        self._dwell_last_fire : dict = {}   # key → timestamp of last dwell fire
        # Global grace period after ANY key fires — prevents accidental mid-move triggers
        self._post_fire_cooldown = 0.5     # seconds
        self._last_any_fire_time = 0.0

        # ── Webcam ────────────────────────────────────────────────────────────
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            raise RuntimeError(
                f"Cannot open webcam (index {camera_index}).\n"
                "Try CAMERA_INDEX=1 in your .env file."
            )
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  self.screen_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.screen_height)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self):
        print("Virtual Keyboard started.  ESC to quit.")
        print(f"  Dwell time      : {self.dwell_time}s")
        print(f"  Click threshold : {self.gesture_detector.click_threshold}")
        print(f"  KB transparency : {self.keyboard.alpha}")

        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("Frame capture failed.")
                break

            frame   = cv2.flip(frame, 1)
            frame   = self.hand_tracker.process_frame(frame)
            frame_h = frame.shape[0]
            self.fps_counter.update()

            index_pos = self.hand_tracker.get_index_finger_position(frame.shape)
            thumb_pos = self.hand_tracker.get_thumb_position(frame.shape)
            centroid  = self.hand_tracker.get_hand_centroid(frame.shape)

            # Hover (must pass frame_h so rects are at the right Y)
            self.keyboard.update_hover(index_pos, frame_h)
            current_key = self.keyboard.hovered_key

            # ── Dwell typing ──────────────────────────────────────────────────
            now = datetime.now().timestamp()

            if current_key is None:
                # Finger not over any key → reset dwell
                self._dwell_key   = None
                self._dwell_start = 0.0
                self.keyboard.set_dwell_progress(0.0)

            else:
                if current_key != self._dwell_key:
                    # Moved to a new key → restart dwell timer
                    self._dwell_key   = current_key
                    self._dwell_start = now
                    self.keyboard.set_dwell_progress(0.0)

                else:
                    # Still on same key → compute progress
                    # If we're still inside the global post-fire grace window,
                    # keep resetting the dwell clock so no accumulation happens.
                    # This prevents accidental fires while the finger moves to
                    # the next intended key after a successful dwell press.
                    time_since_last_fire = now - self._last_any_fire_time
                    if time_since_last_fire < self._post_fire_cooldown:
                        self._dwell_start = now
                        self.keyboard.set_dwell_progress(0.0)
                    else:
                        elapsed  = now - self._dwell_start
                        progress = min(elapsed / self.dwell_time, 1.0)
                        self.keyboard.set_dwell_progress(progress)

                        # Check if dwell time completed AND per-key cooldown expired
                        last_fire = self._dwell_last_fire.get(current_key, 0.0)
                        if (elapsed >= self.dwell_time
                                and (now - last_fire) >= self._dwell_cooldown):
                            self._dwell_last_fire[current_key] = now
                            self._last_any_fire_time = now   # start global grace window
                            self._dwell_start = now          # restart for Backspace hold-repeat
                            self.keyboard.handle_press()
                            self.handle_key_press()

            # ── Pinch click (instant, still supported) ────────────────────────
            click = self.gesture_detector.detect_click(index_pos, thumb_pos, frame.shape)
            if click:
                self.keyboard.handle_press()
                self.handle_key_press()

            # ── Backspace hold via pinch ───────────────────────────────────────
            if current_key == 'Backspace':
                is_pinching = self.gesture_detector.get_click_state()
                if self.backspace_hold.update(is_pinching) and self.current_text:
                    self.current_text = self.current_text[:-1]
            else:
                self.backspace_hold.reset()

            # ── Wave gesture ──────────────────────────────────────────────────
            if centroid:
                waves = self.gesture_detector.detect_wave(centroid[0])
                if waves >= 3:
                    self.clear_all_text()

            wave_count = self.gesture_detector.wave_count

            # ── Render ────────────────────────────────────────────────────────
            self.keyboard.update_animation()
            frame = self.keyboard.draw(frame)
            frame = self.keyboard.draw_overlay_info(
                frame, self.current_text, wave_count, self.wave_trigger_message
            )
            frame = self.fps_counter.draw_fps(frame, (self.screen_width - 110, 18))

            if self.message_clear_counter > 0:
                self.message_clear_counter -= 1
                if self.message_clear_counter == 0:
                    self.wave_trigger_message = ""

            cv2.imshow('Virtual Keyboard', frame)
            if cv2.waitKey(self.wait_delay) & 0xFF == 27:
                break

        self.cleanup()

    # ── Key handling ──────────────────────────────────────────────────────────

    def handle_key_press(self):
        key = self.keyboard.hovered_key
        if key is None:
            return
        if key == 'Backspace':
            if self.current_text:
                self.current_text = self.current_text[:-1]
        elif key in ('Enter', 'Space'):
            self.current_text += ' '
        elif key == 'Clear':
            self.current_text = ""
        else:
            self.current_text += key

    def clear_all_text(self):
        self.current_text          = ""
        self.wave_trigger_message  = "Sentence Cleared!"
        self.message_clear_counter = 150
        self.gesture_detector.reset_wave_counter()

    def cleanup(self):
        self.cap.release()
        cv2.destroyAllWindows()
        self.hand_tracker.release()
        print("Cleaned up.")


if __name__ == "__main__":
    try:
        VirtualKeyboardApp().run()
    except RuntimeError as e:
        print(f"Error: {e}")
        sys.exit(1)