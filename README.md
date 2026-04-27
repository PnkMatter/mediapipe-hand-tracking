# 🖐️ AR Voxel Builder — Hand Tracking with MediaPipe

An augmented reality voxel construction engine controlled entirely by hand gestures. Built with **Python**, **OpenCV**, and **MediaPipe's Hand Landmarker**, this project lets you build 3D isometric structures in real-time using your webcam — no mouse or keyboard required for building.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10.30%2B-orange?logo=google)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green?logo=opencv)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 📖 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [How It Works](#how-it-works)
- [Demo Controls](#demo-controls)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Project Structure](#project-structure)
- [Technical Details](#technical-details)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## Overview

This project combines computer vision and isometric rendering to create a Minecraft-like building experience in augmented reality. The system tracks two hands simultaneously through a **State Machine** with four modes:

- **IDLE** — No action, cursor tracking only
- **BUILDING** — Place blocks (single or continuous)
- **ERASING** — Remove blocks
- **MOVING MODEL** — Grab & move the entire structure

Blocks float freely in 3D space with no base grid — build anywhere!

---

## Features

| Feature | Description |
|---|---|
| ✋ **Dual Hand Tracking** | Left hand for aiming, right hand for actions |
| 🧱 **Free-form Building** | Place blocks anywhere in 3D space (no base grid) |
| 🔄 **Continuous Building** | Hold pinch and drag to build walls and lines |
| 🗑️ **Block Deletion** | Open palm gesture removes the nearest block |
| 👻 **Face-Adjacent Ghost** | Preview appears on the face of existing blocks closest to your finger |
| 📐 **Block Scaling** | Toggle 1×, 2×, or 3× block size via gesture or keyboard |
| 🎨 **Color Palette** | 6 colors, switchable via gesture or on-screen palette |
| 🤏 **Grab & Move** | Two closed fists to translate the entire structure |
| ❓ **Help Screen** | Press `H` to see all shortcuts and gestures |
| 💾 **Save / Load** | Persist your builds to JSON files |
| 📦 **OBJ Export** | Export as a 3D `.obj` mesh for Blender, Unity, etc. |
| 🎯 **Anti-Jitter Filter** | EMA smoothing for stable cursor tracking |

---

## How It Works

### Hand Gestures

The system uses **MediaPipe's HandLandmarker** (Tasks API) to detect 21 landmarks per hand in real-time.

#### Cursor (Left Hand)
The tip of your **index finger** (landmark #8) controls a crosshair on screen. An EMA filter smooths the movement to reduce jitter.

#### Actions (Right Hand)

| Gesture | Description | Action |
|---|---|---|
| **Pinch (Index + Thumb)** | Tips of index and thumb together | **Place block** at ghost position |
| **Hold pinch + move** | Keep pinch while moving left hand | **Continuous building** along path |
| **Open palm (5 fingers)** | All fingers extended | **Delete** nearest block |
| **Thumb + Ring finger** | Tips together | **Cycle color** to next in palette |
| **Thumb + Pinky** | Tips together | **Cycle block scale** (1×→2×→3×) |

#### Two-Hand Gestures

| Gesture | Action |
|---|---|
| **Two closed fists** | **Grab & Move** — translate entire structure |

### Isometric Projection

Blocks are rendered using a diamond-shaped isometric projection with three shaded faces, creating a convincing 3D appearance using only 2D drawing primitives.

### Ghost Block (Face-Adjacent)

The ghost preview block appears on the **face** of an existing block closest to your cursor:
- Cursor above a block → ghost on **top face**
- Cursor to the left → ghost on **left face**
- Cursor to the right → ghost on **right face**

If no blocks exist, the ghost appears at the grid position at Z=0.

---

## Demo Controls

```
  Left Hand (index finger)          Right Hand (gesture actions)
  ┌──────────────────────┐          ┌──────────────────────────────┐
  │                      │          │                              │
  │   👆 Index finger    │          │  👌 Pinch = PLACE            │
  │   moves the cursor   │          │  ✋ Open palm = DELETE        │
  │                      │          │  🤏 Thumb+Ring = COLOR        │
  │                      │          │  🤙 Thumb+Pinky = SCALE      │
  └──────────────────────┘          └──────────────────────────────┘
```

---

## Prerequisites

- **Python** 3.10 or higher
- A **webcam** (built-in or external)
- **pip** package manager

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/mediapipe-hand-tracking.git
cd mediapipe-hand-tracking
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Download the Hand Landmarker model

The project requires the MediaPipe Hand Landmarker model file (`.task`). Download it into the project root:

```bash
# Linux / macOS
curl -O https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task

# Windows (PowerShell)
Invoke-WebRequest -Uri "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task" -OutFile "hand_landmarker.task"
```

> **Note:** The `.task` file is ~7 MB and is **not included in the repository** (listed in `.gitignore`).

### 4. Verify your setup

```bash
python -c "import cv2, mediapipe, numpy; print('All dependencies OK!')"
```

---

## Usage

```bash
python main.py
```

1. The application will open your webcam and display the AR view.
2. Use your **left hand's index finger** to move the cursor.
3. Use your **right hand** to perform gestures (pinch, open palm, etc.)
4. Hover the cursor over the **color palette** (top-left) and pinch to select a color.
5. Press **H** to see all available shortcuts.
6. Press **ESC** to exit.

---

## Keyboard Shortcuts

| Key | Action |
|---|---|
| `H` | Toggle help screen (shows all shortcuts) |
| `ESC` | Quit the application |
| `C` | Clear all blocks |
| `S` | Save the current build to `mundo_voxel.json` |
| `L` | Load a previously saved build |
| `O` | Export the build as `voxel_art.obj` |
| `R` | Reset camera position (after Grab & Move) |
| `+` / `-` | Increase / decrease block scale |

---

## Project Structure

```
mediapipe-hand-tracking/
├── main.py                  # Main application (rendering, tracking, logic)
├── hand_landmarker.task     # MediaPipe model (downloaded separately, in .gitignore)
├── requirements.txt         # Python dependencies
├── .gitignore               # Git ignore rules
├── LICENSE                  # MIT License
├── README.md                # This file
├── mundo_voxel.json         # Save file (auto-generated, in .gitignore)
└── voxel_art.obj            # Exported 3D mesh (auto-generated, in .gitignore)
```

---

## Technical Details

### Architecture

```
┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Webcam    │───>│  MediaPipe Hand  │───>│  Gesture Logic  │
│   (OpenCV)  │    │   Landmarker     │    │  (6 detectors)  │
└─────────────┘    └──────────────────┘    └────────┬────────┘
                                                    │
                                              ┌─────┴─────┐
                                              │   State    │
                                              │  Machine   │
                                              └─────┬─────┘
                                                    │
┌─────────────┐    ┌──────────────────┐    ┌────────┴────────┐
│   Display   │<───│  Isometric       │<───│  Voxel Engine   │
│   (OpenCV)  │    │  Renderer        │    │  (Add/Remove)   │
└─────────────┘    └──────────────────┘    └─────────────────┘
```

### State Machine

```
          ┌──────────┐
          │   IDLE   │◄─── No gesture detected
          └────┬─────┘
               │
    ┌──────────┼──────────┐
    │          │          │
    ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────────┐
│BUILDING│ │ERASING │ │MOVING_MODEL│
│(Pinch) │ │(Palm)  │ │(2 Fists)   │
└────────┘ └────────┘ └────────────┘
```

### Key Parameters

| Parameter | Value | Description |
|---|---|---|
| `TAMANHO_MATRIZ` | 10 | Maximum grid range |
| `LARGURA_BLOCO` | 40 px | Isometric block width |
| `ALTURA_BLOCO` | 20 px | Isometric block height |
| `EMA_ALPHA` | 0.3 | Cursor smoothing factor |
| `escala_bloco` | 1-3 | Block scale (1×, 2×, 3×) |
| `num_hands` | 2 | Maximum tracked hands |
| `min_detection_confidence` | 0.7 | Hand detection threshold |

### MediaPipe Tasks API

This project uses the **new MediaPipe Tasks API** (`mp.tasks.python.vision.HandLandmarker`) with `LIVE_STREAM` running mode for asynchronous, non-blocking hand detection.

### Gesture Detection Functions

| Function | Gesture | Landmarks Used |
|---|---|---|
| `detectar_pinca()` | Pinch | Thumb tip (#4) + Index tip (#8) |
| `detectar_mao_espalmada()` | Open palm | All 5 finger tips vs PIPs |
| `detectar_punho_fechado()` | Closed fist | All tips below MCPs |
| `detectar_polegar_anelar()` | Thumb + Ring | Thumb tip (#4) + Ring tip (#16) |
| `detectar_polegar_mindinho()` | Thumb + Pinky | Thumb tip (#4) + Pinky tip (#20) |

### Save Format (`mundo_voxel.json`)

```json
[
  [grid_x, grid_y, grid_z, [B, G, R]],
  [0, 0, 0, [0, 200, 0]],
  ...
]
```

### OBJ Export

Each voxel is exported as a unit cube with 8 vertices and 6 quad faces. The `.obj` file can be imported into Blender, Unity, Unreal Engine, or any 3D software.

---

## Troubleshooting

### `FileNotFoundError: hand_landmarker.task`

Download the model file. See [Installation — Step 3](#3-download-the-hand-landmarker-model).

### Camera not opening / black screen

- Verify your webcam is connected and not being used by another application.
- Try changing `cv2.VideoCapture(0)` to `cv2.VideoCapture(1)` if you have multiple cameras.

### Low FPS / laggy tracking

- Close other applications using the webcam.
- Reduce the resolution in `main.py`:
  ```python
  cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
  cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
  ```

### Hands not detected / wrong hand labels

- Ensure good lighting conditions.
- Keep your hands within the camera frame.
- MediaPipe mirrors the labels — "Left" on screen corresponds to your left hand (since the image is flipped).

---

## Contributing

Contributions are welcome! Some ideas for improvement:

- 🌈 Custom color picker (RGB sliders)
- 🏗️ Undo/Redo system
- 🎮 Additional gesture mappings (rotate view, zoom)
- 🖼️ Texture mapping on blocks
- 🌐 Multi-user / networked building
- 📱 Mobile support via MediaPipe on Android/iOS

Feel free to open issues or submit pull requests.

---

## License

This project is open source and available under the [MIT License](LICENSE).
