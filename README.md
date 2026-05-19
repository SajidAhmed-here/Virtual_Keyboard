# Virtual Keyboard with Hand Gestures

A real-time Python virtual keyboard controlled entirely using webcam hand gestures with OpenCV + MediaPipe.

Users can type using finger pinch gestures, hold backspace for continuous delete, and clear text using wave gestures.

---

# Features

- Real-time hand tracking using MediaPipe Hands
- Full QWERTY keyboard
- Pinch gesture typing
- Hold Backspace for continuous delete
- Wave gesture to clear all text
- FPS counter
- Hover and press animations
- Dark mode UI
- Smoothing + debounce logic
- Optimized webcam performance

---

# Demo Controls

| Action | Gesture |
|---|---|
| Type | Hover key + pinch thumb/index |
| Backspace | Pinch on Backspace |
| Continuous delete | Hold pinch on Backspace |
| Clear all | Wave hand left-right 3x |
| Exit | Press ESC |

---

# Project Structure

```bash
virtual_keyboard/
│
├── main.py
├── hand_tracker.py
├── gesture_detector.py
├── virtual_keyboard.py
├── utils.py
├── requirements.txt
└── README.md
