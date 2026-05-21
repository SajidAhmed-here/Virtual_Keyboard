# Virtual Keyboard with Hand Gestures

A real-time virtual keyboard using OpenCV + MediaPipe hand tracking.

Control the keyboard entirely using webcam hand gestures:
- Pinch fingers to type
- Hold Backspace for continuous delete
- Wave hand to clear text

---

# Features

- Real-time hand tracking
- Full QWERTY keyboard
- Pinch-to-click typing
- Hold Backspace support
- Wave gesture detection
- FPS counter
- Dark theme UI
- Smooth cursor movement
- Debounce protection

---

# Tech Stack

- Python
- OpenCV
- MediaPipe
- NumPy

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
```

---

# Requirements

- Python 3.11 recommended
- Webcam

IMPORTANT:

MediaPipe may not work correctly on Python 3.13+ or Python 3.14.

Use Python 3.11 for best compatibility.

---

# Create Virtual Environment

## Windows (Git Bash)

```bash
py -3.11 -m venv venv
source venv/Scripts/activate
```

## Windows (CMD)

```cmd
py -3.11 -m venv venv
venv\Scripts\activate
```

---

# Install Dependencies

```bash
pip install -r requirements.txt
```

---

# Run Project

```bash
python main.py
```

---

# Controls

| Action | Gesture |
|---|---|
| Type | Hover + pinch |
| Delete one character | Press Backspace |
| Continuous delete | Hold Backspace |
| Clear all text | Wave hand 3x |
| Exit | ESC key |

---

# requirements.txt

```txt
opencv-python==4.9.0.80
mediapipe==0.10.14
numpy==1.26.4
python-dotenv==1.0.1
```

---

# Troubleshooting

## MediaPipe Error

If you see:

```python
AttributeError: module 'mediapipe' has no attribute 'solutions'
```

You are likely using Python 3.14.

Fix:

```bash
py -3.11 -m venv venv
source venv/Scripts/activate
pip install -r requirements.txt
```

---

# License

MIT License
