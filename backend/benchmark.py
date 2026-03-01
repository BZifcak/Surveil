"""
benchmark.py — Compare person detection across YOLO model variants.

Tests each model on real frames sampled from your footage and prints
a comparison table so you can pick the best model before deployment.

Usage:
    python benchmark.py videos/cam_0.mp4
    python benchmark.py videos/cam_0.mp4 --frames 150 --conf 0.25
    python benchmark.py videos/cam_0.mp4 --sahi   # also test SAHI (slow)
"""
import argparse
import time
from pathlib import Path

import cv2
import numpy as np

# Models to benchmark (all auto-download on first use via ultralytics)
# yolo11 naming has no 'v' prefix — that's intentional (Ultralytics convention)
MODELS = [
    ("yolov8n  (baseline)", "yolov8n.pt"),
    ("yolov8s            ", "yolov8s.pt"),
    ("yolov8m            ", "yolov8m.pt"),
    ("yolo11n            ", "yolo11n.pt"),
    ("yolo11s            ", "yolo11s.pt"),
]

PERSON_CLASS = 0  # COCO class 0 = person


# ---------------------------------------------------------------------------
# Frame sampling
# ---------------------------------------------------------------------------

def sample_frames(video_path: str, n: int) -> list[np.ndarray]:
    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total <= 0:
        # Fallback: read sequentially
        frames = []
        while len(frames) < n:
            ok, f = cap.read()
            if not ok:
                break
            frames.append(f)
        cap.release()
        return frames

    indices = np.linspace(0, total - 1, min(n, total), dtype=int)
    frames = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ok, frame = cap.read()
        if ok:
            frames.append(frame)
    cap.release()
    return frames


# ---------------------------------------------------------------------------
# Standard YOLO benchmark
# ---------------------------------------------------------------------------

def benchmark_model(
    label: str, weights: str, frames: list[np.ndarray], conf: float, device: str = "cpu"
) -> dict | None:
    try:
        from ultralytics import YOLO
    except ImportError:
        print("  ultralytics not installed — pip install ultralytics")
        return None

    print(f"  Loading {label.strip()}...", flush=True)
    try:
        model = YOLO(weights)
        model.to(device)
    except Exception as exc:
        print(f"  Failed to load {weights}: {exc}")
        return None

    times, counts = [], []
    for frame in frames:
        t0 = time.perf_counter()
        results = model(frame, conf=conf, classes=[PERSON_CLASS], verbose=False)
        times.append((time.perf_counter() - t0) * 1000)
        counts.append(sum(len(r.boxes) for r in results))

    frames_hit = sum(1 for c in counts if c > 0)
    return {
        "model": label,
        "avg_ms": round(float(np.mean(times)), 1),
        "p95_ms": round(float(np.percentile(times, 95)), 1),
        "total_det": sum(counts),
        "frames_hit": frames_hit,
        "det_rate": round(frames_hit / len(frames) * 100, 1),
        "avg_per_frame": round(float(np.mean(counts)), 2),
    }


# ---------------------------------------------------------------------------
# SAHI (Slicing Aided Hyper Inference) — best for small/distant objects
# ---------------------------------------------------------------------------

def benchmark_sahi(
    frames: list[np.ndarray], conf: float, slice_size: int = 512, device: str = "cpu"
) -> dict | None:
    try:
        from sahi import AutoDetectionModel
        from sahi.predict import get_sliced_prediction
    except ImportError:
        print("  sahi not installed — pip install sahi  (skipping)")
        return None

    label = f"yolov8n+SAHI({slice_size})"
    print(f"  Loading {label}...", flush=True)

    try:
        detection_model = AutoDetectionModel.from_pretrained(
            model_type="ultralytics",
            model_path="yolov8n.pt",
            confidence_threshold=conf,
            device=device,
        )
    except Exception as exc:
        print(f"  SAHI load failed: {exc}")
        return None

    times, counts = [], []
    for frame in frames:
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        t0 = time.perf_counter()
        result = get_sliced_prediction(
            frame_rgb,
            detection_model,
            slice_height=slice_size,
            slice_width=slice_size,
            overlap_height_ratio=0.2,
            overlap_width_ratio=0.2,
            verbose=0,
        )
        times.append((time.perf_counter() - t0) * 1000)
        person_preds = [
            p for p in result.object_prediction_list
            if p.category.id == PERSON_CLASS
        ]
        counts.append(len(person_preds))

    frames_hit = sum(1 for c in counts if c > 0)
    return {
        "model": f"{label:<20}",
        "avg_ms": round(float(np.mean(times)), 1),
        "p95_ms": round(float(np.percentile(times, 95)), 1),
        "total_det": sum(counts),
        "frames_hit": frames_hit,
        "det_rate": round(frames_hit / len(frames) * 100, 1),
        "avg_per_frame": round(float(np.mean(counts)), 2),
    }


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def print_table(results: list[dict], n_frames: int) -> None:
    print(f"\n{'=' * 82}")
    print(
        f"{'Model':<22} {'Avg ms':>8} {'p95 ms':>8} "
        f"{'Det/frame':>10} {'Det rate':>10} {'Total':>8}"
    )
    print(f"{'-' * 82}")
    for r in results:
        if r is None:
            continue
        print(
            f"{r['model']:<22} {r['avg_ms']:>8} {r['p95_ms']:>8} "
            f"{r['avg_per_frame']:>10} {r['det_rate']:>9}% {r['total_det']:>8}"
        )
    print(f"{'=' * 82}")
    print(f"Frames sampled: {n_frames}   |   Det rate = % of frames where ≥1 person found")
    print(
        "\nAt 1fps detection, anything <1000ms avg is fine on CPU.\n"
        "Pick the model with the highest det rate within your latency budget."
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark YOLO person detection on footage")
    parser.add_argument("video", help="Path to video file (e.g. videos/cam_0.mp4)")
    parser.add_argument(
        "--frames", type=int, default=100,
        help="Number of frames to sample evenly from the video (default: 100)"
    )
    parser.add_argument(
        "--conf", type=float, default=0.25,
        help="Confidence threshold (default: 0.25)"
    )
    parser.add_argument(
        "--device", type=str, default="mps",
        help="Inference device: cpu | mps (Apple Silicon) | cuda (default: mps)"
    )
    parser.add_argument(
        "--sahi", action="store_true",
        help="Also benchmark SAHI sliced inference (much slower, best for distant people)"
    )
    parser.add_argument(
        "--sahi-slice", type=int, default=512,
        help="SAHI slice size in pixels (default: 512, try 320 for very small people)"
    )
    args = parser.parse_args()

    if not Path(args.video).exists():
        print(f"Error: video not found at '{args.video}'")
        return

    print(f"\nSampling {args.frames} frames from {args.video}...")
    frames = sample_frames(args.video, args.frames)
    print(f"Got {len(frames)} frames. Benchmarking at conf={args.conf}...\n")

    print(f"Device: {args.device}\n")

    results = []
    for label, weights in MODELS:
        print(f"Benchmarking {label.strip()}...")
        r = benchmark_model(label, weights, frames, args.conf, args.device)
        if r:
            results.append(r)
            print(f"  {r['avg_ms']}ms avg  |  {r['det_rate']}% frames hit  |  {r['total_det']} total detections")

    if args.sahi:
        print(f"\nBenchmarking SAHI (slice={args.sahi_slice}px) — this will be slow...")
        r = benchmark_sahi(frames, args.conf, args.sahi_slice, args.device)
        if r:
            results.append(r)
            print(f"  {r['avg_ms']}ms avg  |  {r['det_rate']}% frames hit  |  {r['total_det']} total detections")

    print_table(results, len(frames))


if __name__ == "__main__":
    main()
