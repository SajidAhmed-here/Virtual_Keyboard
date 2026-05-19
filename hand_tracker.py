"""
hand_tracker.py - Hand tracking using MediaPipe Hands.
Detects and tracks hand landmarks in real-time with exponential smoothing.
"""

import cv2
import mediapipe as mp
import numpy as np
from utils import Smoother


class HandTracker:
    """
    Wraps MediaPipe Hands to track a single hand and expose
    fingertip pixel positions with optional smoothing.

    Key landmarks used:
        0  = WRIST
        4  = THUMB_TIP
        8  = INDEX_FINGER_TIP
        12 = MIDDLE_FINGER_TIP
    """

    INDEX_FINGER_TIP  = 8
    INDEX_FINGER_MCP  = 5
    THUMB_TIP         = 4
    THUMB_IP          = 3
    MIDDLE_FINGER_TIP = 12
    WRIST             = 0

    def __init__(self, confidence_threshold=0.7, smoothing_alpha=0.6):
        """
        Args:
            confidence_threshold: Min detection/tracking confidence (0–1).
            smoothing_alpha:      EMA factor for index fingertip (0–1).
        """
        self.confidence_threshold = confidence_threshold

        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=confidence_threshold,
            min_tracking_confidence=confidence_threshold,
        )
        self.mp_draw = mp.solutions.drawing_utils

        self.smoother = Smoother(alpha=smoothing_alpha)
        self.hand_detected = False
        self.landmarks = None
        self.smoothed_index_tip = None

    # ── Public API ─────────────────────────────────────────────────────────────

    def process_frame(self, frame):
        """
        Detect hand landmarks in *frame* (BGR), draw them, and update state.

        Returns:
            frame: Annotated frame (BGR).
        """
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self.hands.process(rgb)

        # Reset state
        self.hand_detected = False
        self.landmarks = None
        self.smoothed_index_tip = None

        if not results.multi_hand_landmarks:
            # Hand lost → reset smoother so there's no stale carry-over
            self.smoother.reset()
            return frame

        hand_lm = results.multi_hand_landmarks[0]
        self.landmarks = hand_lm

        # Smooth index fingertip
        tip = hand_lm.landmark[self.INDEX_FINGER_TIP]
        self.smoothed_index_tip = self.smoother.filter(np.array([tip.x, tip.y]))
        self.hand_detected = True

        # ── Visual overlays ────────────────────────────────────────────────────
        self.mp_draw.draw_landmarks(
            frame, hand_lm, self.mp_hands.HAND_CONNECTIONS,
            self.mp_draw.DrawingSpec(color=(0, 220, 0), thickness=2, circle_radius=3),
            self.mp_draw.DrawingSpec(color=(0, 220, 220), thickness=2),
        )
        h, w = frame.shape[:2]
        tip_px = (int(self.smoothed_index_tip[0] * w),
                  int(self.smoothed_index_tip[1] * h))
        cv2.circle(frame, tip_px, 12, (0, 0, 255), -1)
        cv2.circle(frame, tip_px, 14, (255, 255, 255), 2)

        return frame

    def get_index_finger_position(self, frame_shape):
        """Return (x, y) pixel coords of smoothed index fingertip, or None."""
        if not self.hand_detected or self.smoothed_index_tip is None:
            return None
        x = int(self.smoothed_index_tip[0] * frame_shape[1])
        y = int(self.smoothed_index_tip[1] * frame_shape[0])
        return (x, y)

    def get_thumb_position(self, frame_shape):
        """Return (x, y) pixel coords of thumb tip, or None."""
        if not self.hand_detected or self.landmarks is None:
            return None
        t = self.landmarks.landmark[self.THUMB_TIP]
        return (int(t.x * frame_shape[1]), int(t.y * frame_shape[0]))

    def get_hand_centroid(self, frame_shape):
        """Return (x, y) centroid of all 21 landmarks, or None."""
        if not self.hand_detected or self.landmarks is None:
            return None
        pts = np.array([[lm.x, lm.y] for lm in self.landmarks.landmark])
        c = pts.mean(axis=0)
        return (int(c[0] * frame_shape[1]), int(c[1] * frame_shape[0]))

    def release(self):
        """Free MediaPipe resources."""
        self.hands.close()
