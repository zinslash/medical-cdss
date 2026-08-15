# export_demo_images.py
#
# Converts a small sample of RSNA DICOM files into ordinary JPGs you can
# open, look at, and upload through the dashboard.
#
# Pulls a mix of confirmed-normal and confirmed-pneumonia cases straight
# from the labels CSV, so you know the ground truth for each demo image --
# unlike random Google images, where the caption may not match the actual
# pathology.

import os
import random

import pandas as pd
import numpy as np
from PIL import Image

try:
    import pydicom
except ImportError:
    raise SystemExit("pydicom not installed. Run:  pip install pydicom")

RSNA_ROOT = "D:/datasets dp 2/dataset 6_rsna"
RSNA_IMAGES = os.path.join(RSNA_ROOT, "stage_2_train_images")
RSNA_LABELS = os.path.join(RSNA_ROOT, "stage_2_train_labels.csv")

OUTPUT_DIR = "demo_images"
N_PER_CLASS = 10
SEED = 1234  # different from the training seed so we're less likely to
             # pick images the model trained on


def resolve_csv_path(path):
    if os.path.isfile(path):
        return path
    if os.path.isdir(path):
        for f in os.listdir(path):
            if f.lower().endswith('.csv'):
                return os.path.join(path, f)
    raise SystemExit(f"Could not find labels CSV at or inside: {path}")


def resolve_images_dir(path):
    if not os.path.isdir(path):
        raise SystemExit(f"Images folder not found: {path}")
    entries = os.listdir(path)
    if any(f.lower().endswith('.dcm') for f in entries):
        return path
    for entry in entries:
        sub = os.path.join(path, entry)
        if os.path.isdir(sub) and any(f.lower().endswith('.dcm') for f in os.listdir(sub)):
            return sub
    raise SystemExit(f"No .dcm files found in: {path}")


def dicom_to_jpg(dcm_path, out_path):
    ds = pydicom.dcmread(dcm_path)
    arr = ds.pixel_array

    if arr.dtype != np.uint8:
        arr = arr.astype(np.float32)
        arr = 255.0 * (arr - arr.min()) / max(arr.max() - arr.min(), 1e-6)
        arr = arr.astype(np.uint8)

    Image.fromarray(arr).convert('RGB').save(out_path, quality=95)


def main():
    csv_path = resolve_csv_path(RSNA_LABELS)
    images_dir = resolve_images_dir(RSNA_IMAGES)

    df = pd.read_csv(csv_path)
    labels = df.groupby('patientId')['Target'].max().reset_index()

    rng = random.Random(SEED)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for target, name in [(0, "NORMAL"), (1, "PNEUMONIA")]:
        subset = labels[labels['Target'] == target]['patientId'].tolist()
        picked = rng.sample(subset, min(N_PER_CLASS, len(subset)))

        out_folder = os.path.join(OUTPUT_DIR, name)
        os.makedirs(out_folder, exist_ok=True)

        exported = 0
        for pid in picked:
            dcm_path = os.path.join(images_dir, f"{pid}.dcm")
            if not os.path.exists(dcm_path):
                continue
            out_path = os.path.join(out_folder, f"{name}_{pid[:8]}.jpg")
            try:
                dicom_to_jpg(dcm_path, out_path)
                exported += 1
            except Exception as e:
                print(f"  skipped {pid}: {e}")

        print(f"✅ Exported {exported} {name} images -> {out_folder}")

    print(f"\nDone. Open the '{OUTPUT_DIR}' folder -- these are ordinary JPGs "
          f"you can view and upload to the dashboard.")
    print("Ground truth is in the folder name, so you know what each SHOULD be.")


if __name__ == "__main__":
    main()