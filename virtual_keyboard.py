"""
virtual_keyboard.py – QWERTY keyboard rendering
Changes:
  - iOS-style frosted glass transparency (alpha=0.35, GaussianBlur under KB)
  - Smaller keyboard (default height 240px instead of 300)
  - Space="SPACE", Backspace="<-"  (plain ASCII, OpenCV can't render Unicode)
  - update_hover() / draw() accept frame_h so keyboard is always bottom-pinned
  - set_dwell_progress(0.0–1.0) draws a progress arc on the hovered key
"""

import cv2
import numpy as np
from utils import get_key_color, get_text_color, get_background_color, point_in_rectangle


class VirtualKeyboard:
    LAYOUT = [
        ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', 'Backspace'],
        ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
        ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', 'Enter'],
        ['Z', 'X', 'C', 'V', 'B', 'N', 'M', 'Clear'],
        ['Space'],
    ]

    # Plain ASCII labels (OpenCV default font has no Unicode glyphs)
    LABELS = {
        'Space':     'SPACE',
        'Backspace': '<-',
        'Enter':     'OK',
        'Clear':     'CLR',
    }

    def __init__(self, keyboard_width=800, keyboard_height=240,
                 is_dark_theme=True, position=(50, 0), alpha=0.35):
        """
        alpha : 0.0 = fully invisible, 1.0 = fully opaque.
                0.35 mimics iOS keyboard frosted-glass feel.
        keyboard_height : reduced to 240 (was 300) → smaller, less intrusive.
        """
        self.keyboard_width  = keyboard_width
        self.keyboard_height = keyboard_height
        self.is_dark_theme   = is_dark_theme
        self.kb_left         = position[0]
        self.alpha           = alpha
        self.key_gap         = 4

        rows = len(self.LAYOUT)
        self.key_height = int((keyboard_height - (rows - 1) * self.key_gap) / rows)

        self.key_multipliers = {
            'Backspace': 1.6,
            'Enter':     1.6,
            'Clear':     1.6,
            'Space':     7.0,
        }

        self.hovered_key         = None
        self.pressed_key         = None
        self.pressed_frame_count = 0
        self._dwell_progress     = 0.0   # 0.0–1.0, updated by main.py

        self._cached_frame_h = None
        self._cached_rects   = {}

    # ── Layout helpers ────────────────────────────────────────────────────────

    def _row_layout(self, row):
        total_mult = sum(self.key_multipliers.get(k, 1.0) for k in row)
        unit_w = (self.keyboard_width - (len(row) - 1) * self.key_gap) / total_mult
        result, cx = [], 0.0
        for key in row:
            w = unit_w * self.key_multipliers.get(key, 1.0)
            result.append((key, int(cx), int(w)))
            cx += w + self.key_gap
        return result

    def _kb_top(self, frame_h):
        """Y of keyboard top edge, pinned 8 px above bottom of frame."""
        return frame_h - self.keyboard_height - 8

    def _build_rects(self, frame_h):
        rects  = {}
        kb_top = self._kb_top(frame_h)
        for row_idx, row in enumerate(self.LAYOUT):
            layout      = self._row_layout(row)
            total_row_w = layout[-1][1] + layout[-1][2]
            start_x     = self.kb_left + (self.keyboard_width - total_row_w) // 2
            row_y       = kb_top + row_idx * (self.key_height + self.key_gap)
            for key, rel_x, w in layout:
                rects[key] = (start_x + rel_x, row_y, w, self.key_height)
        return rects

    def _rects(self, frame_h):
        if frame_h != self._cached_frame_h:
            self._cached_rects   = self._build_rects(frame_h)
            self._cached_frame_h = frame_h
        return self._cached_rects

    # ── Public API ────────────────────────────────────────────────────────────

    def set_dwell_progress(self, progress: float):
        """main.py calls this every frame with 0.0→1.0 as the user dwells."""
        self._dwell_progress = max(0.0, min(1.0, progress))

    def get_key_rect(self, key, frame_h=720):
        return self._rects(frame_h).get(key)

    def get_key_at_position(self, pos, frame_h=720):
        if pos is None:
            return None
        for key, rect in self._rects(frame_h).items():
            if point_in_rectangle(pos, rect):
                return key
        return None

    def update_hover(self, pos, frame_h=720):
        self.hovered_key = self.get_key_at_position(pos, frame_h)

    def handle_press(self):
        if self.hovered_key:
            self.pressed_key         = self.hovered_key
            self.pressed_frame_count = 6

    def update_animation(self):
        if self.pressed_frame_count > 0:
            self.pressed_frame_count -= 1
            if self.pressed_frame_count == 0:
                self.pressed_key = None

    # ── Drawing ───────────────────────────────────────────────────────────────

    def draw(self, frame):
        fh, fw = frame.shape[:2]
        rects  = self._rects(fh)
        kb_top = self._kb_top(fh)

        overlay = frame.copy()

        # Step 1: blur the webcam pixels under the keyboard → frosted glass
        roi = frame[kb_top:kb_top + self.keyboard_height,
                    self.kb_left:self.kb_left + self.keyboard_width]
        if roi.size > 0:
            blurred = cv2.GaussianBlur(roi, (25, 25), 0)
            overlay[kb_top:kb_top + self.keyboard_height,
                    self.kb_left:self.kb_left + self.keyboard_width] = blurred

        # Step 2: semi-transparent dark/light tint over blurred area
        bg = get_background_color(self.is_dark_theme)
        cv2.rectangle(overlay,
                      (self.kb_left, kb_top),
                      (self.kb_left + self.keyboard_width, kb_top + self.keyboard_height),
                      bg, -1)

        # Step 3: draw each key onto overlay
        font = cv2.FONT_HERSHEY_SIMPLEX
        for key, (x, y, kw, kh) in rects.items():
            is_hov = (key == self.hovered_key)
            is_prs = (key == self.pressed_key)
            color  = get_key_color(is_hov, is_prs, self.is_dark_theme)

            # Key background
            cv2.rectangle(overlay, (x, y), (x + kw, y + kh), color, -1)
            # Key border
            border = (90, 90, 100) if self.is_dark_theme else (175, 175, 185)
            cv2.rectangle(overlay, (x, y), (x + kw, y + kh), border, 1)

            # Label
            label = self.LABELS.get(key, key)
            scale = 0.38 if len(label) > 3 else (0.46 if len(label) > 1 else 0.60)
            tc    = get_text_color(self.is_dark_theme)
            (tw, th), _ = cv2.getTextSize(label, font, scale, 1)
            tx = x + (kw - tw) // 2
            ty = y + (kh + th) // 2
            cv2.putText(overlay, label, (tx, ty), font, scale, tc, 1, cv2.LINE_AA)

            # Dwell progress arc: cyan ring fills clockwise as user hovers
            if is_hov and self._dwell_progress > 0.01:
                cx_a   = x + kw // 2
                cy_a   = y + kh // 2
                radius = max(4, min(kw, kh) // 2 - 2)
                end_a  = int(-90 + 360 * self._dwell_progress)
                cv2.ellipse(overlay, (cx_a, cy_a), (radius, radius),
                            0, -90, end_a, (0, 220, 255), 2, cv2.LINE_AA)

        # Step 4: blend overlay onto original frame
        cv2.addWeighted(overlay, self.alpha, frame, 1.0 - self.alpha, 0, frame)

        # Keyboard outline (drawn on final frame, always crisp)
        cv2.rectangle(frame,
                      (self.kb_left, kb_top),
                      (self.kb_left + self.keyboard_width, kb_top + self.keyboard_height),
                      (200, 200, 210), 1)
        return frame

    def draw_overlay_info(self, frame, current_text, wave_count, wave_trigger_message):
        fh, fw = frame.shape[:2]

        # Semi-transparent top info bar
        bar = frame.copy()
        cv2.rectangle(bar, (0, 0), (fw, 78), (0, 0, 0), -1)
        cv2.addWeighted(bar, 0.50, frame, 0.50, 0, frame)
        cv2.rectangle(frame, (0, 0), (fw, 78), (200, 200, 210), 1)

        cv2.putText(frame, "Text:", (12, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.60, (0, 220, 0), 2, cv2.LINE_AA)
        display = current_text[-65:] if len(current_text) > 65 else current_text
        cv2.putText(frame, display, (78, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.60, (255, 255, 255), 2, cv2.LINE_AA)

        cv2.putText(frame, f"Wave:{wave_count}/3", (12, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 200, 255), 2, cv2.LINE_AA)
        cv2.putText(frame, "Ready", (135, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 220, 0), 2, cv2.LINE_AA)

        if wave_trigger_message:
            cv2.putText(frame, wave_trigger_message, (12, 105),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.72, (0, 140, 255), 2, cv2.LINE_AA)

        # Hint strip just above keyboard
        kb_top = self._kb_top(fh)
        hint = "Hover 1.5s=type  |  Wave x3=clear  |  Hold <-=delete  |  ESC=exit"
        cv2.putText(frame, hint, (self.kb_left + 4, kb_top - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (180, 180, 200), 1, cv2.LINE_AA)

        return frame