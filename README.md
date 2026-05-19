# Virtual Keyboard with Hand Gestures

A real-time Python virtual keyboard driven entirely by webcam hand gestures —
no physical keyboard or mouse required.

---

## Features

| Feature | Detail |
|---|---|
| Hand tracking | MediaPipe Hands, 1 hand, real-time |
| Full QWERTY layout | A–Z, 0–9, Space, Enter, Backspace, Clear |
| Click gesture | Pinch (index + thumb) to press a key |
| Hold-to-delete | Hold Backspace ≥ 500 ms → continuous delete |
| Wave-to-clear | 3 horizontal sweeps → clear all text |
| Smoothing | Exponential moving average on index fingertip |
| Debounce | Prevents repeat-presses per key (300 ms cooldown) |
| Dark theme UI | Modern overlay with hover + press animation |
| FPS display | Live frame-rate counter |

---

## Quick Start

```bash
# 1. (Recommended) create a virtual environment
python -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
python main.py
```

---

## Controls

| Action | Gesture |
|---|---|
| Type a character | Hover index finger over key → pinch (bring thumb close) |
| Delete one char | Tap Backspace key |
| Delete continuously | Hover Backspace + hold pinch ≥ 0.5 s |
| Clear everything | Wave hand 3× left-right (within 2 seconds) |
| Exit | Press **ESC** |

---

## Project Structure

```
virtual_keyboard_project/
├── main.py               # App entry point & main loop
├── hand_tracker.py       # MediaPipe wrapper with EMA smoothing
├── gesture_detector.py   # Click (pinch) + wave gesture logic
├── virtual_keyboard.py   # Keyboard layout, rendering, hit-test
├── utils.py              # Smoother, FPSCounter, Debouncer, HoldDetector, helpers
├── requirements.txt
└── README.md
```

---

## How It Works — Deep Dive

### 1. Wave Detection (Mathematics)

```
State tracked each frame:
    last_x          — centroid X from previous frame
    swing_min_x     — lowest  X in current swing
    swing_max_x     — highest X in current swing
    wave_direction  — 'left' | 'right'
    dir_persistence — consecutive frames in same direction

Algorithm:
    velocity = current_x − last_x

    if |velocity| > 20 px (noise floor):
        direction = 'left' if velocity < 0 else 'right'

        if direction == prev_direction:
            dir_persistence += 1
        else:
            dir_persistence = 1
            wave_direction  = direction

        update swing_min_x, swing_max_x

        amplitude = swing_max_x − swing_min_x
        if amplitude > 150 px  AND  dir_persistence >= 2:
            wave_count += 1
            reset swing window

    if wave_count >= 3 within 2 seconds:
        TRIGGER clear  →  reset all wave state
```

**Why 150 px amplitude?**
Normal typing drifts < 50 px horizontally.
A deliberate wave sweeps 200–400 px.
150 px sits safely in between.

---

### 2. Click Gesture Threshold

```
normalized_distance = Euclidean(index_tip, thumb_tip) / frame_width
click fires when: normalized_distance < click_threshold (default 0.05)

For 1280 px wide frame: 0.05 × 1280 = 64 px ≈ 3 cm
Open hand:    index–thumb ≈ 10–15 cm (500+ px)
Pinched hand: index–thumb ≈ 1–2  cm  ( 40–80 px)

Tuning:
    0.03 → tight pinch required  (fewer false positives)
    0.05 → comfortable default
    0.07 → very easy to trigger  (more false positives)
```

---

### 3. Debounce — Preventing Duplicate Typing

```
Problem:
    At 30 FPS, hand stays in pinch pose for ~500 ms = ~15 frames.
    Without debounce: 15 identical key presses registered.

Solution (Debouncer class):
    last_trigger_time = 0

    can_trigger():  now_ms − last_trigger_time >= cooldown_ms
    trigger():      last_trigger_time = now_ms

    cooldown_ms values:
        Regular keys:    300 ms  — comfortable typing pace
        Wave gesture:  1500 ms  — prevents accidental re-clear
```

---

### 4. Low-Light Accuracy Tips

1. **Lighting**: Place a lamp *in front of you* (not behind). Avoid backlighting.
2. **Background**: Solid-colour background contrasts the hand.
3. **Median blur** (already in code, commented out):
   ```python
   # In main.py, uncomment:
   frame = cv2.medianBlur(frame, 3)
   ```
4. **Lower confidence threshold** in `main.py`:
   ```python
   self.tracker = HandTracker(confidence_threshold=0.5, ...)
   ```
5. **More smoothing** to reduce jitter:
   ```python
   self.tracker = HandTracker(smoothing_alpha=0.75, ...)
   ```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Black / no webcam window | Check permissions; try `cv2.VideoCapture(1)` in `main.py` |
| Hand not detected | Improve lighting; move closer; wear contrasting sleeve |
| Jittery cursor | Increase `smoothing_alpha` to 0.7–0.8 |
| Keys hard to press | Increase `click_threshold` to 0.06–0.07 |
| Wave keeps mis-firing | Increase `wave_threshold` to 180–200 |
| Low FPS | Close other apps; lower `CAM_W/CAM_H` in `main.py` |
| `mediapipe` install fails | `pip install mediapipe --upgrade` |

---

## Optional Enhancements

### Sound on keypress (Windows)
```python
# main.py, uncomment the two lines at the top of the file
import winsound
def _beep(): winsound.Beep(880, 40)
# Then uncomment _beep() in _handle_key()
```

### Two-hand support
```python
# hand_tracker.py — change max_num_hands=1 to max_num_hands=2
```

### Light theme
```python
# main.py — change is_dark_theme=True to is_dark_theme=False
```

---

## License

MIT — free to use and modify for personal or commercial projects.
# Virtual_Keyboard
