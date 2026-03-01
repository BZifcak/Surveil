"""
train_weapon_detector.py — Convert real annotated CCTV datasets to YOLO format
and train YOLO11n for weapon detection.

Primary dataset (real 1920×1080 CCTV footage, Pascal VOC XML bounding boxes):
  - Images/      : Handgun (1714), Short_rifle (797), Knife (210)  [5149 XMLs]

Optional dataset (NOT recommended — synthetic: weapons composited onto Oxford-IIIT
Pet Dataset backgrounds, not real CCTV footage — may introduce domain shift):
  - split-2500/  : Rifle (all positives)                           [2500 XMLs]

Classes are merged into 3 YOLO classes: 0=gun, 1=rifle, 2=knife

Run on a DigitalOcean GPU droplet (H100 ~$3.40/hr, ~$20-30 overnight):

    # 1. Upload the dataset and this script to the droplet
    scp -r chats/media/Images train_weapon_detector.py root@<droplet>:~/

    # 2. Install dependencies
    pip install ultralytics

    # 3. Convert + train (all-in-one)
    python train_weapon_detector.py --images-dir Images --train

    # Or just convert if you want to inspect labels first:
    python train_weapon_detector.py --images-dir Images

    # 4. Download the trained weights
    scp root@<droplet>:~/runs/weapon/train/weights/best.pt backend/models/weapon.pt

Output: runs/weapon/train/weights/best.pt
    → copy to backend/models/weapon.pt to enable real-time local weapon detection
"""

import argparse
import random
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

# ---------------------------------------------------------------------------
# Class mapping — both datasets use different case/naming, normalise here
# ---------------------------------------------------------------------------

# Maps every raw XML class name → (yolo_class_index, canonical_name)
CLASS_MAP: dict[str, tuple[int, str]] = {
    # gun class (index 0)
    "handgun":    (0, "gun"),
    "Handgun":    (0, "gun"),
    "pistol":     (0, "gun"),
    "Pistol":     (0, "gun"),
    # rifle class (index 1)
    "rifle":      (1, "rifle"),
    "Rifle":      (1, "rifle"),
    "short_rifle":(1, "rifle"),
    "Short_rifle":(1, "rifle"),
    # knife class (index 2)
    "knife":      (2, "knife"),
    "Knife":      (2, "knife"),
    "machete":    (2, "knife"),
}

CLASSES = ["gun", "rifle", "knife"]   # index → name

# ---------------------------------------------------------------------------
# Pascal VOC XML → YOLO txt
# ---------------------------------------------------------------------------

def voc_to_yolo(xml_path: Path) -> list[str]:
    """Parse a Pascal VOC XML file and return YOLO-format label lines.

    Returns an empty list if there are no annotated objects (negative frame).
    """
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except ET.ParseError:
        return []

    size = root.find("size")
    if size is None:
        return []
    w = float(size.findtext("width") or 0)
    h = float(size.findtext("height") or 0)
    if w == 0 or h == 0:
        return []

    lines = []
    for obj in root.findall("object"):
        name = obj.findtext("name", "").strip()
        if name not in CLASS_MAP:
            continue                       # skip unknown classes
        cls_idx, _ = CLASS_MAP[name]

        bndbox = obj.find("bndbox")
        if bndbox is None:
            continue
        xmin = float(bndbox.findtext("xmin") or 0)
        ymin = float(bndbox.findtext("ymin") or 0)
        xmax = float(bndbox.findtext("xmax") or 0)
        ymax = float(bndbox.findtext("ymax") or 0)

        # Clamp to image bounds
        xmin, xmax = max(0, xmin), min(w, xmax)
        ymin, ymax = max(0, ymin), min(h, ymax)
        if xmax <= xmin or ymax <= ymin:
            continue

        cx = ((xmin + xmax) / 2) / w
        cy = ((ymin + ymax) / 2) / h
        bw = (xmax - xmin) / w
        bh = (ymax - ymin) / h
        lines.append(f"{cls_idx} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")

    return lines


# ---------------------------------------------------------------------------
# Dataset assembly
# ---------------------------------------------------------------------------

def collect_pairs(src_dir: Path) -> list[tuple[Path, Path]]:
    """Return (jpg_path, xml_path) pairs where both files exist."""
    pairs = []
    for xml_path in sorted(src_dir.glob("*.xml")):
        jpg_path = xml_path.with_suffix(".jpg")
        if jpg_path.exists():
            pairs.append((jpg_path, xml_path))
    print(f"  {src_dir.name}: {len(pairs)} image/annotation pairs found")
    return pairs


def convert_and_copy(
    pairs: list[tuple[Path, Path]],
    img_out_dir: Path,
    lbl_out_dir: Path,
) -> dict[str, int]:
    """Convert VOC XMLs to YOLO txts, copy images. Returns class counts."""
    img_out_dir.mkdir(parents=True, exist_ok=True)
    lbl_out_dir.mkdir(parents=True, exist_ok=True)

    counts = {"pos": 0, "neg": 0, **{c: 0 for c in CLASSES}}

    for jpg_path, xml_path in pairs:
        lines = voc_to_yolo(xml_path)

        # Destination filenames (use source stem to avoid collisions from different dirs)
        stem = f"{xml_path.parent.name}_{xml_path.stem}"
        shutil.copy(jpg_path, img_out_dir / f"{stem}.jpg")
        (lbl_out_dir / f"{stem}.txt").write_text("\n".join(lines))

        if lines:
            counts["pos"] += 1
            for line in lines:
                cls_idx = int(line.split()[0])
                counts[CLASSES[cls_idx]] += 1
        else:
            counts["neg"] += 1

    return counts


# ---------------------------------------------------------------------------
# YAML + training
# ---------------------------------------------------------------------------

def write_yaml(out_dir: Path, val_ratio: float = 0.1) -> Path:
    """Write YOLO dataset YAML with a random train/val split."""
    img_dir = out_dir / "images" / "all"
    all_imgs = list(img_dir.glob("*.jpg"))
    random.shuffle(all_imgs)

    n_val = max(1, int(len(all_imgs) * val_ratio))
    val_imgs  = all_imgs[:n_val]
    train_imgs = all_imgs[n_val:]

    # Symlink (or copy) into train/ and val/ sub-dirs
    for split_name, split_imgs in [("train", train_imgs), ("val", val_imgs)]:
        split_img_dir = out_dir / "images" / split_name
        split_lbl_dir = out_dir / "labels" / split_name
        split_img_dir.mkdir(parents=True, exist_ok=True)
        split_lbl_dir.mkdir(parents=True, exist_ok=True)
        for img in split_imgs:
            lbl = (out_dir / "labels" / "all" / img.name).with_suffix(".txt")
            # Hardlink (saves disk space vs copy)
            dst_img = split_img_dir / img.name
            dst_lbl = split_lbl_dir / img.with_suffix(".txt").name
            if not dst_img.exists():
                shutil.copy(img, dst_img)
            if not dst_lbl.exists() and lbl.exists():
                shutil.copy(lbl, dst_lbl)

    yaml_path = out_dir / "weapon.yaml"
    yaml_path.write_text(f"""\
path: {out_dir.resolve()}
train: images/train
val:   images/val

nc: {len(CLASSES)}
names: {CLASSES}
""")
    print(f"\nDataset YAML: {yaml_path}")
    print(f"  Train: {len(train_imgs)} images")
    print(f"  Val:   {len(val_imgs)} images")
    return yaml_path


def train(yaml_path: Path) -> None:
    from ultralytics import YOLO

    model = YOLO("yolo11n.pt")    # tiny + fast — good for distinctive weapon shapes
    model.train(
        data=str(yaml_path),
        epochs=150,
        imgsz=640,
        batch=64,           # reduce to 32 on smaller GPUs (e.g. RTX 4090 at 1920px input)
        project="runs/weapon",
        name="train",
        exist_ok=True,
        # Augmentation tuned for CCTV: slight rotation, no vertical flip, colour jitter
        hsv_h=0.015,
        hsv_s=0.4,
        hsv_v=0.5,
        degrees=5,
        flipud=0.0,
        fliplr=0.5,
        mosaic=1.0,
        mixup=0.1,
        copy_paste=0.1,
    )

    best = Path("runs/weapon/train/weights/best.pt")
    print(f"\n{'='*60}")
    print(f"Training complete!")
    print(f"Best weights: {best.resolve()}")
    print(f"\nDeploy:")
    print(f"  scp root@droplet:{best.resolve()} backend/models/weapon.pt")
    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert annotated CCTV datasets to YOLO and train weapon detector"
    )
    parser.add_argument("--images-dir", type=Path, default=Path("Images"),
                        help="Path to Images/ directory (Handgun/Short_rifle/Knife)")
    parser.add_argument("--split-dir",  type=Path, default=Path("split-2500"),
                        help="Path to split-2500/ directory (Rifle)")
    parser.add_argument("--out-dir",    type=Path, default=Path("weapon_dataset"),
                        help="Output directory for converted dataset")
    parser.add_argument("--train",      action="store_true",
                        help="Run training after conversion")
    parser.add_argument("--val-ratio",  type=float, default=0.1,
                        help="Fraction of data to use for validation (default: 0.1)")
    args = parser.parse_args()

    out_img_dir = args.out_dir / "images" / "all"
    out_lbl_dir = args.out_dir / "labels" / "all"

    print("\n=== STEP 1: Collect image/annotation pairs ===")
    pairs_images = collect_pairs(args.images_dir) if args.images_dir.exists() else []
    pairs_split  = collect_pairs(args.split_dir)  if args.split_dir.exists()  else []
    all_pairs = pairs_images + pairs_split
    print(f"  Total: {len(all_pairs)} pairs")

    print("\n=== STEP 2: Convert Pascal VOC → YOLO ===")
    counts = convert_and_copy(all_pairs, out_img_dir, out_lbl_dir)
    print(f"  Positive frames (with objects): {counts['pos']}")
    print(f"  Negative frames (no objects):   {counts['neg']}")
    for cls in CLASSES:
        print(f"    {cls}: {counts[cls]} instances")

    print("\n=== STEP 3: Build train/val split ===")
    yaml_path = write_yaml(args.out_dir, args.val_ratio)

    if args.train:
        print("\n=== STEP 4: Train YOLO11n ===")
        train(yaml_path)
    else:
        print(f"\nDataset ready. Run with --train to start training, or:")
        print(f"  yolo train data={yaml_path} model=yolo11n.pt epochs=150 imgsz=640")


if __name__ == "__main__":
    main()
