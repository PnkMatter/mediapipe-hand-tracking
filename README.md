---
title: AR Voxel Builder
emoji: 🧱
colorFrom: green
colorTo: blue
sdk: streamlit
sdk_version: "1.30.0"
python_version: "3.11"
app_file: app.py
pinned: false
---

# 🖐️ AR Voxel Builder — Hand Tracking with MediaPipe

An augmented reality voxel construction engine controlled entirely by hand gestures. Built with **Python**, **OpenCV**, and **MediaPipe's Hand Landmarker**, this project lets you build 3D isometric structures in real-time using your webcam — no mouse or keyboard required for building.

**🌐 [Try it live on Hugging Face Spaces](https://huggingface.co/spaces/PnkMatter/ar-voxel-builder)**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10.30%2B-orange?logo=google)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green?logo=opencv)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30%2B-red?logo=streamlit)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 📖 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [How It Works](#how-it-works)
- [Live Demo (Web)](#live-demo-web)
- [Local Version](#local-version)
- [Project Structure](#project-structure)
- [Technical Details](#technical-details)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## Overview

This project combines computer vision and isometric rendering to create a Minecraft-like building experience in augmented reality. The system tracks two hands simultaneously through a **State Machine** with four modes:

- **IDLE** — No action, cursor tracking only
- **BUILDING** — Place blocks (single or continuous, with 300ms cooldown)
- **ERASING** — Remove blocks
- **MOVING MODEL** — Grab & move the entire structure

Blocks float freely in 3D space with no base grid — build anywhere!

The project has **two versions**:
- **`app.py`** — Web version (Streamlit + WebRTC), deployed on Hugging Face Spaces
- **`main.py`** — Local desktop version (OpenCV window)

---

## Features

| Feature | Description |
|---|---|
| ✋ **Dual Hand Tracking** | Left hand for aiming, right hand for actions |
| 🧱 **Free-form Building** | Place blocks anywhere in 3D space (no base grid) |
| 🔄 **Continuous Building** | Hold pinch and drag to build walls and lines |
| ⏱️ **Placement Cooldown** | 300ms interval prevents accidental rapid placement |
| 🗑️ **Block Deletion** | Open palm gesture removes the nearest block |
| 👻 **Face-Adjacent Ghost** | Preview appears on the face of existing blocks closest to your finger |
| 📐 **Block Scaling** | Toggle 1×, 2×, or 3× block size |
| 🎨 **Color Palette** | 6 colors, switchable via sidebar or gesture |
| 🤏 **Grab & Move** | Two closed fists to translate the entire structure |
| 💾 **Save / Load** | Persist your builds to JSON files |
| 🎯 **Anti-Jitter Filter** | EMA smoothing for stable cursor tracking |
| 🌐 **Web Version** | Run in the browser via Hugging Face Spaces |

---

## How It Works

### Hand Gestures

The system uses **MediaPipe's HandLandmarker** (Tasks API) to detect 21 landmarks per hand in real-time.

#### Cursor (Left Hand)
The tip of your **index finger** (landmark #8) controls a crosshair on screen. An EMA filter smooths the movement to reduce jitter.

#### Actions (Right Hand)

| Gesture | Description | Action |
|---|---|---|
| **👌 Pinch** | Index + thumb tips together | **Place block** at ghost position |
| **Hold pinch + move** | Keep pinch while moving left hand | **Continuous building** along path |
| **✋ Open palm** | All 5 fingers extended | **Delete** nearest block |
| **✊✊ Two closed fists** | Both hands closed | **Grab & Move** entire structure |

### Isometric Projection

Blocks are rendered using a diamond-shaped isometric projection with three shaded faces, creating a convincing 3D appearance using only 2D drawing primitives.

### Ghost Block (Face-Adjacent)

The ghost preview block appears on the **face** of an existing block closest to your cursor:
- Cursor above a block → ghost on **top face**
- Cursor to the left → ghost on **left face**
- Cursor to the right → ghost on **right face**

If no blocks exist, the ghost appears at the grid position at Z=0.

---

## Live Demo (Web)

**🌐 https://huggingface.co/spaces/PnkMatter/ar-voxel-builder**

The web version runs on Hugging Face Spaces using Streamlit + WebRTC:

1. Open the link above
2. Allow camera access when prompted
3. Click **START** on the video player
4. Use the sidebar controls to change color, scale, etc.
5. Use hand gestures to build!

### Web Controls (Sidebar)

| Control | Description |
|---|---|
| 🎨 Color | Select block color |
| 📐 Scale | Choose block size (1×, 2×, 3×) |
| 🗑️ Clear All | Remove all blocks |
| 🔄 Reset Camera | Reset view position |
| 💾 Save/Load | Download or upload JSON projects |

---

## Local Version

### Prerequisites

- **Python** 3.10 or higher
- A **webcam** (built-in or external)
- **pip** package manager

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/PnkMatter/mediapipe-hand-tracking.git
cd mediapipe-hand-tracking

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download the Hand Landmarker model (~7MB)
# Linux / macOS
curl -O https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task

# Windows (PowerShell)
Invoke-WebRequest -Uri "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task" -OutFile "hand_landmarker.task"

# 4. Run
python main.py
```

> **Note:** The `.task` file is ~7 MB and is **not included in the repository** (listed in `.gitignore`).

### Keyboard Shortcuts (Local Only)

| Key | Action |
|---|---|
| `H` | Toggle help screen |
| `ESC` | Quit the application |
| `C` | Clear all blocks |
| `S` | Save to `mundo_voxel.json` |
| `L` | Load a saved build |
| `O` | Export as `voxel_art.obj` |
| `R` | Reset camera position |
| `+` / `-` | Increase / decrease block scale |

---

## Project Structure

```
mediapipe-hand-tracking/
├── app.py                   # Web version (Streamlit + WebRTC)
├── main.py                  # Local desktop version (OpenCV)
├── requirements.txt         # Python dependencies
├── packages.txt             # System dependencies (HF Spaces)
├── hand_landmarker.task     # MediaPipe model (downloaded separately, in .gitignore)
├── .gitignore               # Git ignore rules
├── LICENSE                  # MIT License
├── README.md                # This file
├── DEPLOY.txt               # HuggingFace Space re-deploy guide
└── TWILIO_GUIDE.txt         # Twilio TURN server setup guide
```

---

## Technical Details

### Architecture

```
┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Webcam    │───>│  MediaPipe Hand  │───>│  Gesture Logic  │
│  (WebRTC)   │    │   Landmarker     │    │  (3 detectors)  │
└─────────────┘    └──────────────────┘    └────────┬────────┘
                                                    │
                                              ┌─────┴─────┐
                                              │   State    │
                                              │  Machine   │
                                              └─────┬─────┘
                                                    │
┌─────────────┐    ┌──────────────────┐    ┌────────┴────────┐
│  Streamlit  │<───│  Isometric       │<───│  Voxel Engine   │
│  (Browser)  │    │  Renderer        │    │  (Add/Remove)   │
└─────────────┘    └──────────────────┘    └─────────────────┘
```

### Key Parameters

| Parameter | Value | Description |
|---|---|---|
| `LARGURA_BLOCO` | 40 px | Isometric block width |
| `ALTURA_BLOCO` | 20 px | Isometric block height |
| `EMA_ALPHA` | 0.3 | Cursor smoothing factor |
| `COOLDOWN_COLOCAR` | 0.3 s | Interval between block placements |
| `escala_bloco` | 1-3 | Block scale (1×, 2×, 3×) |
| `num_hands` | 2 | Maximum tracked hands |
| `min_detection_confidence` | 0.6 | Hand detection threshold |

### Gesture Detection Functions

| Function | Gesture | Landmarks Used |
|---|---|---|
| `detectar_pinca()` | Pinch | Thumb tip (#4) + Index tip (#8) |
| `detectar_espalmada()` | Open palm | All 5 finger tips vs PIPs |
| `detectar_punho()` | Closed fist | All tips below MCPs |

### Save Format (`mundo_voxel.json`)

```json
[
  [grid_x, grid_y, grid_z, [B, G, R]],
  [0, 0, 0, [0, 200, 0]],
  ...
]
```

---

## Deployment

The web version is deployed on **Hugging Face Spaces** using the Streamlit SDK.

### Requirements for deployment:
- A [Twilio](https://www.twilio.com/try-twilio) account (free trial) for TURN servers
- TURN server credentials set as secrets in the HF Space

See [DEPLOY.txt](DEPLOY.txt) and [TWILIO_GUIDE.txt](TWILIO_GUIDE.txt) for detailed instructions.

---

## Troubleshooting

### Web Version

| Problem | Solution |
|---|---|
| Camera doesn't connect | Check browser permissions, try Chrome |
| "TURN não configurado" warning | Add Twilio secrets to HF Space settings |
| Video freezes/disconnects | Network issue — TURN may be needed |
| "Runtime Error" on HF | Check Logs tab for details |

### Local Version

| Problem | Solution |
|---|---|
| `FileNotFoundError: hand_landmarker.task` | Download the model (see Installation) |
| Camera not opening | Check webcam connection, try index 1 |
| Low FPS | Close other camera apps, reduce resolution |
| Hands not detected | Improve lighting, keep hands in frame |

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
