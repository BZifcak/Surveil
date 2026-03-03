# Surveil

### AI-powered campus surveillance that acts before disaster strikes.

---

## The Problem

91% of US campuses have video surveillance systems — yet footage is almost entirely used *after* incidents occur, not to prevent them. A single security officer cannot realistically monitor 9, 16, or 32 feeds simultaneously without missing something. The cameras record. Nobody watches.

Over 23,400 on-campus criminal incidents are reported annually at US postsecondary institutions. The average active shooter incident lasts 12.5 minutes. The average law enforcement response time is 18 minutes — a **5.5-minute gap** where lives are lost. The infrastructure exists. The gap is in real-time human attention.

---

## The Solution

Surveil is a live surveillance dashboard that watches your cameras so your officers don't have to.

It integrates with existing camera infrastructure, runs AI detection continuously across all feeds simultaneously, and immediately surfaces threats — ranked by severity — to the people who need to act on them. When a weapon is spotted, a fight breaks out, or a fire starts, Surveil flags it instantly.

Surveil does not replace security officers. It makes the ones you have dramatically more effective by telling them exactly where to look, the moment something happens.

---

## Features

**Split View** — The primary monitoring view. A live MapBox GL map shows the physical location of every camera on campus. The selected camera feed streams in real time alongside a grid of thumbnail previews of all other cameras. When a threat is detected, the corresponding map marker highlights and a red threat badge appears in the nav bar.

**Grid View** — Multi-feed view displaying a 2×3 paginated grid of live camera feeds with automatic threat prioritization. When a critical event is detected, that camera automatically moves to the top-left position so the officer's eye goes there first.

**Log View** — Audit and investigation view. Every detection event is logged with a timestamp, camera, event type, and AI confidence score. The log is searchable and filterable by camera or event type.

Keyboard shortcuts let officers switch views instantly — `A` for Split, `D` for Grid — and arrow keys cycle through cameras.

---

## Tech Stack

### Frontend
- **React 19 + TypeScript + Vite** — Single-page application
- **React Map GL + MapBox GL** — Geospatial camera map
- **Radix UI** — Accessible interface components
- **WebSocket + HTTP** — Dual-channel architecture for sub-second alert delivery

### Backend
- **Python 3.12 + FastAPI + Uvicorn** — Async server handling simultaneous camera streams, AI inference, and WebSocket broadcasting
- **OpenCV** — Video capture and MJPEG streaming. MOG2 motion detection.
- **MJPEG streaming** — Live video delivered to the frontend over HTTP

### AI Detection Pipeline
Detection runs continuously across all feeds in a round-robin loop at 1 frame/second per camera, balancing responsiveness with computational load.

| Detector | Priority | Approach |
|---|---|---|
| Weapon Detection | Critical | Custom-trained YOLOv11n on CCTV footage |
| Fight Detection | Critical | YOLOv8n-pose skeleton keypoint behavioral heuristics |
| Person Detection | Low | Pre-trained YOLOv11s (COCO) |
| Motion Detection | Low | OpenCV MOG2 background subtraction |

---

## Custom Weapon Detection Model
We trained a custom YOLOv11n model on a dataset of 5,149 real CCTV frames (1920×1080) specifically because off-the-shelf models trained on clean stock photos fail on grainy surveillance footage.

**Dataset:** [Real-time gun detection in CCTV: An open problem](https://deepknowledge-us.github.io/US-Real-time-gun-detection-in-CCTV-An-open-problem-dataset/)
- 1,534 positive frames with weapon annotations
- 3,615 negative frames
- 2,721 total annotations across 3 classes: handgun, rifle, knife

**Training:** 150 epochs, YOLOv11n (nano), 640px, batch size 128, dual NVIDIA T4 GPUs on Kaggle. Augmentations tuned for CCTV: HSV jitter, rotation, horizontal flip, mosaic, mixup, and copy-paste. Output weights: `backend/models/weapon.pt` (5.5 MB).

**View on Kaggle:** [frankmurphy24/cctv-weapon-detector](https://www.kaggle.com/datasets/frankmurphy24/cctv-weapon-detector)

### Fight Detection
Uses YOLOv8n-pose to detect 17 skeletal keypoints per person and evaluates 4 behavioral criteria simultaneously: proximity, arm intrusion, rapid limb movement, and aggressive posture. An alert requires proximity plus 2 of the other 3 criteria, sustained for 3 consecutive frames, with a 3-second cooldown per camera.

---

## Getting Started

### Prerequisites
- Node.js 18+
- Python 3.12
- A MapBox API token

### Frontend
```bash
cd my-app
npm install
cp .env.example .env   # add your VITE_MAPBOX_TOKEN
npm run dev
```

### Backend
```bash
cd backend
py -3.12 -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
uvicorn main:app --reload
```

---

## Demo Footage

The 12 camera feeds in the demo (cam_0 through cam_11) are sourced from two datasets:
- the [VIRAT Video Dataset](https://viratdata.org/) — a DARPA-funded large-scale surveillance benchmark — to simulate realistic campus camera deployment.
- dataset from [Real-time gun detection in CCTV: An open problem](https://deepknowledge-us.github.io/US-Real-time-gun-detection-in-CCTV-An-open-problem-dataset/)
---

## Citations

1. Campus Safety Magazine, "More Than 8 in 10 Campuses Use Their Security Cameras Daily," 2024 Video Surveillance Survey.
2. National Center for Education Statistics, "Fast Facts: College Crime (804)."
3. ALICE Training Institute, "Understanding Active Shooter Statistics & Incident Response Times."
4. frankmurphy24, "CCTV Weapon Detector," Kaggle Dataset.
5. Tsung-Yi Lin et al., "Microsoft COCO: Common Objects in Context," ECCV 2014.
6. Sangmin Oh et al., "A Large-scale Benchmark Dataset for Event Recognition in Surveillance Video," CVPR 2011.
