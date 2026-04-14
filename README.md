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

This project combines computer vision and isometric rendering to create a Minecraft-like building experience in augmented reality. The system tracks two hands simultaneously:

- **Left hand** → Controls a cursor/crosshair on the isometric grid
- **Right hand** → Performs actions (place or delete blocks) via pinch gestures

The voxel world is rendered as an isometric grid overlaid on your live camera feed, giving it an AR feel.

---

## Features

| Feature | Description |
|---|---|
| ✋ **Dual Hand Tracking** | Left hand for aiming, right hand for actions |
| 🧱 **Voxel Placement** | Stack blocks up to 10 layers high on a 10×10 grid |
| 🗑️ **Block Deletion** | Remove blocks from the top of any column |
| 🎨 **Color Palette** | 6 selectable colors (Green, Red, Blue, Yellow, Magenta, White) |
| 👻 **Ghost Preview** | Transparent preview of where the next block will be placed |
| 💾 **Save / Load** | Persist your builds to JSON files |
| 📦 **OBJ Export** | Export your voxel art as a 3D `.obj` mesh for use in Blender, Unity, etc. |
| 🎯 **Anti-Jitter Filter** | EMA (Exponential Moving Average) smoothing for stable cursor tracking |
| 🖥️ **Isometric Rendering** | Pseudo-3D rendering with shading and depth sorting |

---

## How It Works

### Hand Gestures

The system uses **MediaPipe's HandLandmarker** (Tasks API) to detect 21 landmarks per hand in real-time.

#### Cursor (Left Hand)
The tip of your **index finger** (landmark #8) controls a crosshair on screen. An EMA filter smooths the movement to reduce jitter.

#### Actions (Right Hand)

| Gesture | Landmarks | Action |
|---|---|---|
| **Pinch (Index + Thumb)** | Tip of index (#8) close to tip of thumb (#4) | **Place block** at cursor position |
| **Pinch (Middle + Thumb)** | Tip of middle (#12) close to tip of thumb (#4) | **Delete block** at cursor position |

> The pinch threshold is `40 pixels`. A cooldown of `0.4 seconds` prevents accidental rapid placement.

### Isometric Projection

Blocks are rendered using a diamond-shaped isometric projection:

```
         Top Face (lighter)
        /         \
       /           \
Left Face          Right Face
(base color)       (darker)
```

Each cube is composed of three quadrilaterals with different brightness levels, creating a convincing 3D appearance using only 2D drawing primitives.

---

## Demo Controls

```
  Left Hand (index finger)          Right Hand (pinch gestures)
  ┌──────────────────────┐          ┌──────────────────────────┐
  │                      │          │                          │
  │   👆 Index finger    │          │  👌 Index+Thumb = PLACE  │
  │   moves the cursor   │          │  🤏 Middle+Thumb = DELETE│
  │                      │          │                          │
  └──────────────────────┘          └──────────────────────────┘
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
pip install opencv-python mediapipe numpy
```

### 3. Download the Hand Landmarker model

The project requires the MediaPipe Hand Landmarker model file (`.task`). Download it into the project root:

```bash
# Linux / macOS
curl -O https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task

# Windows (PowerShell)
Invoke-WebRequest -Uri "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task" -OutFile "hand_landmarker.task"
```

> **Note:** The `.task` file is ~5 MB and is **not included in the repository** to keep it lightweight.

### 4. Verify your setup

```bash
python -c "import cv2, mediapipe, numpy; print('All dependencies OK!')"
```

---

## Usage

```bash
python main.py
```

1. The application will open your webcam and display the isometric grid overlaid on the camera feed.
2. Use your **left hand's index finger** to move the cursor over the grid.
3. Use your **right hand** to perform pinch gestures:
   - **Index + Thumb pinch** → Place a block
   - **Middle + Thumb pinch** → Delete the top block
4. Hover the cursor over the **color palette** (top-left) and pinch to select a new color.
5. Press **ESC** to exit.

---

## Keyboard Shortcuts

| Key | Action |
|---|---|
| `ESC` | Quit the application |
| `C` | Clear all blocks |
| `S` | Save the current build to `mundo_voxel.json` |
| `L` | Load a previously saved build from `mundo_voxel.json` |
| `O` | Export the build as a 3D mesh to `voxel_art.obj` |

---

## Project Structure

```
mediapipe-hand-tracking/
├── main.py                  # Main application (rendering, tracking, logic)
├── hand_landmarker.task     # MediaPipe Hand Landmarker model (downloaded separately)
├── mundo_voxel.json         # Save file for voxel builds (auto-generated)
├── voxel_art.obj            # Exported 3D mesh (auto-generated)
└── README.md                # This file
```

---

## Technical Details

### Architecture

```
┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Webcam    │───>│  MediaPipe Hand  │───>│  Gesture Logic  │
│   (OpenCV)  │    │   Landmarker     │    │  (Pinch detect) │
└─────────────┘    └──────────────────┘    └────────┬────────┘
                                                    │
                                                    v
┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Display   │<───│  Isometric       │<───│  Voxel Engine   │
│   (OpenCV)  │    │  Renderer        │    │  (Add/Remove)   │
└─────────────┘    └──────────────────┘    └─────────────────┘
```

### Key Parameters

| Parameter | Value | Description |
|---|---|---|
| `TAMANHO_MATRIZ` | 10 | Grid size (10×10 base) |
| `LARGURA_BLOCO` | 40 px | Isometric block width |
| `ALTURA_BLOCO` | 20 px | Isometric block height |
| `ORIGEM_X` | 640 px | Grid horizontal origin (screen center) |
| `ORIGEM_Y` | 370 px | Grid vertical origin (screen center) |
| `num_hands` | 2 | Maximum number of tracked hands |
| `min_detection_confidence` | 0.7 | Hand detection threshold |
| `min_tracking_confidence` | 0.7 | Hand tracking threshold |

### MediaPipe Tasks API

This project uses the **new MediaPipe Tasks API** (`mp.tasks.python.vision.HandLandmarker`) with `LIVE_STREAM` running mode for asynchronous, non-blocking hand detection. This is the modern replacement for the deprecated `mp.solutions.hands` API.

### Rendering Pipeline

1. **Floor rendering** — Draws the 10×10 base grid at `z = -1`
2. **UI rendering** — Draws the color palette overlay
3. **Ghost block** — Renders a semi-transparent preview block (50% opacity via `cv2.addWeighted`)
4. **Saved blocks** — Renders all placed blocks sorted by depth (`z`, then `x + y`) for correct overlap

### Save Format (`mundo_voxel.json`)

```json
[
  [grid_x, grid_y, grid_z, [B, G, R]],
  [0, 0, 0, [0, 200, 0]],
  ...
]
```

### OBJ Export

Each voxel is exported as a unit cube (1×1×1) with 8 vertices and 6 quad faces. The resulting `.obj` file can be imported directly into Blender, Unity, Unreal Engine, or any 3D software.

---

## Troubleshooting

### `AttributeError: module 'mediapipe' has no attribute 'solutions'`

You're using MediaPipe ≥ 0.10.30 which removed the legacy `solutions` API. This project already uses the new Tasks API — make sure you're running the latest version of `main.py`.

### Camera not opening / black screen

- Verify your webcam is connected and not being used by another application.
- Try changing `cv2.VideoCapture(0)` to `cv2.VideoCapture(1)` if you have multiple cameras.

### `FileNotFoundError: hand_landmarker.task`

Download the model file. See [Installation — Step 3](#3-download-the-hand-landmarker-model).

### Low FPS / laggy tracking

- Close other applications using the webcam.
- Reduce the resolution in `main.py`:
  ```python
  cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
  cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
  ```
- The `model_complexity` is already set to the lightest option.

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
