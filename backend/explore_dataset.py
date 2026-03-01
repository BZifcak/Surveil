"""
explore_dataset.py — Understand the jsalazar CCTV gun detection dataset.

Streams a sample without downloading all 2.72 GB, then:
  1. Prints schema and column names
  2. Checks for label columns and their distribution
  3. Saves a grid of sample frames to dataset_samples/
  4. Optionally runs Gemini on N frames and reports hit rate

Usage:
    python explore_dataset.py                  # inspect 20 frames
    python explore_dataset.py --n 50           # inspect 50 frames
    python explore_dataset.py --n 50 --gemini  # also run Gemini on each frame
"""
import argparse
import os
import sys
import time
from pathlib import Path
from collections import Counter

import cv2
import numpy as np
from dotenv import load_dotenv

load_dotenv()

DATASET_ID = "jsalazar/US-Real-time-gun-detection-in-CCTV-An-open-problem-dataset"
SAMPLES_DIR = Path("dataset_samples")


# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------

def _decode_image(raw) -> np.ndarray | None:
    """Convert whatever the dataset gives us into a BGR numpy array."""
    # Case 1: PIL Image (normal auto-decode)
    if hasattr(raw, "size") and hasattr(raw, "mode"):
        arr = np.array(raw)
        if arr.ndim == 3 and arr.shape[2] == 3:
            return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        return arr

    # Case 2: dict with "bytes" key (decode=False path)
    if isinstance(raw, dict):
        blob = raw.get("bytes") or raw.get("data") or raw.get("image")
        if blob is None:
            return None
        arr = np.frombuffer(blob, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return img  # may be None if still undecodable

    # Case 3: raw bytes
    if isinstance(raw, (bytes, bytearray)):
        arr = np.frombuffer(raw, np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)

    return None


def stream_dataset(n: int):
    try:
        from datasets import load_dataset, Image as HFImage
        import fsspec
    except ImportError:
        print("ERROR: pip install datasets fsspec")
        sys.exit(1)

    print(f"Streaming up to {n} rows from {DATASET_ID} ...")

    # decode=False prevents PIL from crashing the streaming iterator on corrupt frames.
    # We load image bytes ourselves: prefer the inline bytes field, fall back to the
    # hf:// zip path via fsspec, then decode with cv2 (more permissive than PIL).
    ds = load_dataset(DATASET_ID, split="train", streaming=True)
    ds = ds.cast_column("image", HFImage(decode=False))

    rows = []
    skipped = 0
    for row in ds:
        if len(rows) >= n:
            break

        img_info = row.get("image") or {}
        bdata = img_info.get("bytes") if isinstance(img_info, dict) else None
        path  = img_info.get("path")  if isinstance(img_info, dict) else None

        if bdata:
            data = bdata
        elif path:
            try:
                with fsspec.open(path, "rb") as fh:
                    data = fh.read()
            except Exception:
                skipped += 1
                continue
        else:
            skipped += 1
            continue

        arr = np.frombuffer(data, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            skipped += 1
            continue

        row["_image_np"] = img
        rows.append(row)
        if len(rows) % 10 == 0:
            print(f"  fetched {len(rows)}/{n} rows (skipped {skipped} bad)", end="\r", flush=True)

    print(f"  fetched {len(rows)} rows  (skipped {skipped} undecodable)")
    return rows


# ---------------------------------------------------------------------------
# Schema inspection
# ---------------------------------------------------------------------------

def inspect_schema(rows: list[dict]) -> None:
    if not rows:
        print("No rows fetched.")
        return

    first = rows[0]
    print("\n=== SCHEMA ===")
    for col, val in first.items():
        if col == "_image_np":
            print(f"  {'image (decoded)':<20} ndarray  shape={val.shape}  dtype={val.dtype}")
            continue
        t = type(val).__name__
        extra = ""
        if isinstance(val, dict):
            extra = f"  keys={list(val.keys())}"
        elif isinstance(val, str):
            extra = f"  sample={val!r}"
        elif isinstance(val, (int, float)):
            extra = f"  sample={val}"
        print(f"  {col:<20} {t}{extra}")

    print(f"\nTotal rows sampled: {len(rows)}")


# ---------------------------------------------------------------------------
# Label distribution
# ---------------------------------------------------------------------------

def inspect_labels(rows: list[dict]) -> dict[str, Counter]:
    label_cols = {}
    skip = {"image", "_image_np"}
    for col in rows[0].keys():
        if col in skip:
            continue
        vals = [r[col] for r in rows]
        if all(isinstance(v, (str, int, float, bool, type(None))) for v in vals):
            label_cols[col] = Counter(str(v) for v in vals)

    if not label_cols:
        print("\n=== LABELS ===")
        print("  No label/categorical columns found — dataset may be images-only.")
        return {}

    print("\n=== LABEL DISTRIBUTIONS ===")
    for col, counts in label_cols.items():
        print(f"\n  Column: {col!r}")
        for val, count in counts.most_common():
            bar = "█" * int(count / len(rows) * 40)
            print(f"    {val:<20} {count:>5}  {bar}")
    return label_cols


# ---------------------------------------------------------------------------
# Save sample images
# ---------------------------------------------------------------------------

def save_samples(rows: list[dict], max_save: int = 20) -> None:
    SAMPLES_DIR.mkdir(exist_ok=True)
    saved = 0
    skip = {"image", "_image_np"}
    for i, row in enumerate(rows[:max_save]):
        img_np = row.get("_image_np")
        if img_np is None:
            continue
        label_parts = [f"{k}={v}" for k, v in row.items() if k not in skip and isinstance(v, (str, int, float, bool))]
        label_str = "_".join(label_parts) if label_parts else "nolabel"
        filename = SAMPLES_DIR / f"{i:04d}_{label_str[:50]}.jpg"
        cv2.imwrite(str(filename), img_np)
        saved += 1

    print(f"\n=== SAMPLES ===")
    print(f"  Saved {saved} images to {SAMPLES_DIR.resolve()}/")
    print(f"  Open a few to visually confirm content and label accuracy.")


# ---------------------------------------------------------------------------
# Gemini evaluation
# ---------------------------------------------------------------------------

_GEMINI_RPM_LIMIT = 2          # free-tier requests per minute
_GEMINI_CALL_INTERVAL = 60.0 / _GEMINI_RPM_LIMIT + 2  # 32s — small safety margin


def run_gemini_eval(rows: list[dict]) -> None:
    import json

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("\nGEMINI_API_KEY not set — skipping Gemini eval.")
        return

    try:
        from google import genai
        from google.genai import types as genai_types
    except ImportError:
        print("pip install google-genai — skipping Gemini eval.")
        return

    client = genai.Client(api_key=api_key)

    _PROMPT = (
        "You are a security surveillance AI. This is a real CCTV camera frame. "
        "Does this image contain a visible weapon (handgun, pistol, rifle, shotgun, knife)? "
        "Respond ONLY with valid JSON: "
        '{{"weapon_detected": true, "type": "handgun", "confidence": 0.9}} '
        'or {{"weapon_detected": false}}. No other text.'
    )

    hits = 0
    misses = 0
    errors = 0
    results = []

    print(f"\n=== GEMINI EVAL ({len(rows)} frames) — ~{_GEMINI_CALL_INTERVAL:.0f}s between calls ===")
    last_call = 0.0
    for i, row in enumerate(rows):
        img_np = row.get("_image_np")
        if img_np is None:
            continue

        # Respect the 2 RPM free-tier limit
        elapsed = time.monotonic() - last_call
        if elapsed < _GEMINI_CALL_INTERVAL:
            wait = _GEMINI_CALL_INTERVAL - elapsed
            print(f"  [rate limit] waiting {wait:.0f}s ...", end="\r", flush=True)
            time.sleep(wait)

        h, w = img_np.shape[:2]
        if w > 1280:
            img_np = cv2.resize(img_np, (1280, int(h * 1280 / w)))

        _, buf = cv2.imencode(".jpg", img_np, [cv2.IMWRITE_JPEG_QUALITY, 85])
        image_part = genai_types.Part.from_bytes(data=buf.tobytes(), mime_type="image/jpeg")

        try:
            last_call = time.monotonic()
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[_PROMPT, image_part],
            )
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            data = json.loads(text)
            detected = data.get("weapon_detected", False)
            wtype = data.get("type", "—")
            conf = data.get("confidence", "—")
        except Exception as exc:
            errors += 1
            print(f"  [{i:03d}] ERROR: {exc}")
            continue

        if detected:
            hits += 1
            status = f"HIT  type={wtype} conf={conf}"
        else:
            misses += 1
            status = "MISS"

        results.append({"frame": i, "detected": detected, "type": wtype, "conf": conf})
        print(f"  [{i:03d}] {status}")

    total = hits + misses
    print(f"\n  Results: {hits}/{total} frames flagged as weapon  ({100*hits/total:.0f}% hit rate)")
    print(f"  Errors:  {errors}")
    if total > 0:
        print(
            "\n  If all frames in this dataset contain guns (all-positive dataset),\n"
            f"  then {100*hits/total:.0f}% is the recall of Gemini on real CCTV gun footage."
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Explore the jsalazar CCTV gun dataset")
    parser.add_argument("--n", type=int, default=20, help="Number of rows to stream (default: 20)")
    parser.add_argument("--gemini", action="store_true", help="Run Gemini on each frame and report hit rate")
    args = parser.parse_args()

    rows = stream_dataset(args.n)
    inspect_schema(rows)
    inspect_labels(rows)
    save_samples(rows)

    if args.gemini:
        run_gemini_eval(rows)
    else:
        print("\nTip: run with --gemini to test Gemini weapon detection recall on these frames.")


if __name__ == "__main__":
    main()
