# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Platform

Raspberry Pi running Linux. Camera is accessed via `picamera2` (not OpenCV's `VideoCapture`). The Pi's IP on the local network is `192.168.0.19`.

## Project Structure

Each sub-project is self-contained with its own virtual environment (`env/`). There is no shared top-level package — to run any project, activate its own venv first.

| Project | Description |
|---|---|
| `stream.py` | Bare MJPEG camera stream (no MediaPipe) |
| `mediapipe-vision/` | Single-frame pose analysis, saves result to `result.jpg` |
| `mp_face_detection/` | Live face detection overlay streamed via Flask |
| `mp_face_mask/` | Face detection + virtual mask drawing overlay |
| `mp_hand_tracking/` | Hand landmark detection with class-based architecture |
| `mp_pose_stream/` | Full-body skeletal pose detection streamed via Flask |
| `mp_Vulcan_salute/` | Vulcan gesture detection + SocketIO audio trigger (threading mode) |
| `vulcan_final/` | Same as above, production version using eventlet for stable async |

## Environment Setup (per project)

```bash
cd ~/projects/<project_name>
python -m venv env
source env/bin/activate
sudo apt install -y libcap-dev   # required for picamera2 on Pi
pip install flask picamera2 opencv-python mediapipe
# For SocketIO projects:
pip install flask-socketio eventlet
```

## Running a Project

```bash
source env/bin/activate
python app.py          # most projects
python stream.py       # stream.py / mp_pose_stream
```

Access in browser: `http://192.168.0.19:5000`

## Architecture Patterns

### 1. Simple MJPEG Stream (e.g. `stream.py`, `mp_face_detection`)

Picamera2 captures RGB888 frames → MediaPipe processes in-place → `cv2.imencode` → Flask `Response` with `multipart/x-mixed-replace` MIME type. Single route at `/`.

### 2. Class-Based Detector + Camera (e.g. `mp_hand_tracking`)

`CameraSource` encapsulates Picamera2 setup; `HandDetector` (or similar) encapsulates MediaPipe init and `process(frame)`. The `generate_frames()` function wires them together. Swapping the camera or detection model requires changing only one class.

### 3. Gesture Event + SocketIO Audio (e.g. `vulcan_final`)

Two routes: `/` serves `index.html`, `/video_feed` streams MJPEG. When a gesture is detected, `socketio.emit('vulcan_detected')` fires; the browser plays audio via Socket.IO. A 5-second cooldown (`last_time`) prevents repeated triggers. `vulcan_final` uses `async_mode='eventlet'` (stable); `mp_Vulcan_salute` uses `async_mode='threading'` with `allow_unsafe_werkzeug=True`.

## Key Implementation Notes

- **Color format**: Picamera2 captures `RGB888`. MediaPipe also expects RGB, so frames pass directly without conversion. `cv2.imencode` handles RGB input correctly for JPEG output.
- **Performance**: Default resolution is 640×480. Drop to 320×240 if video stutters (`vulcan_final` uses 320×240 by default). MediaPipe confidence thresholds (`min_detection_confidence`, `min_tracking_confidence`) around 0.5–0.7 balance accuracy vs CPU load.
- **Vulcan gesture logic**: Checks landmark distances — index↔middle (`lm[8]↔lm[12]`) < 0.05, ring↔pinky (`lm[16]↔lm[20]`) < 0.05, and middle↔ring (`lm[12]↔lm[16]`) > 0.08 — meaning the two pairs are closed but the gap between them is open.
- **writeable flag**: Setting `frame.flags.writeable = False` before `pose.process()` / `face_detection.process()` avoids an unnecessary copy inside MediaPipe; set it back to `True` before drawing.
