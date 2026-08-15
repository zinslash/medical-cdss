# train_chest_rsna.py
#
# Retrains the chest expert on ADULT chest X-rays (RSNA) combined with the
# existing PEDIATRIC Kaggle set.
#
# WHY: the current chest model was trained only on the Kaggle pneumonia
# dataset, which is entirely children aged 1-5 from a single hospital in
# Guangzhou. It has never seen adult anatomy -- different rib spacing,
# heart-to-chest ratio, and lung field shape -- so it reads those normal
# adult differences as pathology. Hence "normal adult chest -> PNEUMONIA
# at 95.77% confidence".
#
# RSNA provides ~26,700 adult radiographs with radiologist-annotated lung
# opacity labels (Target=1 means pneumonia-consistent opacity).
#
# Combining both datasets gives a model that handles either age group,
# which matters if someone uploads an arbitrary image during a demo.

import os
import json
import time
import copy
import random

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import pandas as pd
from torchvision import models, transforms
from torch.utils.data import DataLoader, Dataset
from PIL import Image, ImageFile
from sklearn.metrics import classification_report, confusion_matrix

ImageFile.LOAD_TRUNCATED_IMAGES = True

try:
    import pydicom
except ImportError:
    raise SystemExit("pydicom not installed. Run:  pip install pydicom")

# ---------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------
RSNA_ROOT = "D:/datasets dp 2/dataset 6_rsna"
RSNA_IMAGES = os.path.join(RSNA_ROOT, "stage_2_train_images")
RSNA_LABELS = os.path.join(RSNA_ROOT, "stage_2_train_labels.csv")

# Existing pediatric Kaggle set (set to None to train on RSNA alone)
PEDIATRIC_DIR = "D:/datasets dp 2/dataset 4/archive/chest_xray/train"

OUTPUT_MODEL = "best_chest_model.pth"
OUTPUT_CLASS_MAP = "best_chest_model_class_map.json"
POSITIVE_LABEL = "PNEUMONIA"

EPOCHS = 8
BATCH_SIZE = 32
VAL_FRACTION = 0.2
SEED = 42

# Images per class from EACH source. 2500 adult + 2500 pediatric per class
# = 10,000 training images total. Keeps CPU training to roughly 2-3 hours.
MAX_PER_CLASS_PER_SOURCE = 2500

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"⚡ Device: {DEVICE}")

torch.manual_seed(SEED)
np.random.seed(SEED)
random.seed(SEED)


def resolve_csv_path(path):
    """
    Extraction sometimes creates a FOLDER named stage_2_train_labels.csv
    containing the actual csv. Handle both layouts.
    """
    if os.path.isfile(path):
        return path
    if os.path.isdir(path):
        for f in os.listdir(path):
            if f.lower().endswith('.csv'):
                found = os.path.join(path, f)
                print(f"ℹ️  CSV was nested inside a folder; using: {found}")
                return found
    raise SystemExit(f"❌ Could not find the labels CSV at or inside: {path}")


def resolve_images_dir(path):
    """Handle the case where extraction nested the images one level deeper."""
    if not os.path.isdir(path):
        raise SystemExit(f"❌ Images folder not found: {path}")

    entries = os.listdir(path)
    if any(f.lower().endswith('.dcm') for f in entries):
        return path

    # Look one level down
    for entry in entries:
        sub = os.path.join(path, entry)
        if os.path.isdir(sub) and any(f.lower().endswith('.dcm') for f in os.listdir(sub)):
            print(f"ℹ️  DICOMs were nested one level deeper; using: {sub}")
            return sub

    raise SystemExit(f"❌ No .dcm files found in: {path}")


train_transforms = transforms.Compose([
    transforms.Resize((256, 256)),
    transforms.RandomResizedCrop(224, scale=(0.8, 1.0)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(10),
    transforms.RandomAffine(degrees=0, translate=(0.1, 0.1)),
    transforms.ColorJitter(brightness=0.25, contrast=0.25),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

# Must match INFERENCE_TRANSFORM in model.py exactly
val_transforms = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])


def load_rsna_records():
    """
    RSNA labels CSV has one row PER BOUNDING BOX, so a patient with two
    opacities appears twice. Deduplicate by patientId, taking max Target
    (if any box exists, the study is positive).
    """
    csv_path = resolve_csv_path(RSNA_LABELS)
    images_dir = resolve_images_dir(RSNA_IMAGES)

    df = pd.read_csv(csv_path)
    print(f"\n🔍 RSNA labels: {len(df)} rows")

    # Collapse to one row per patient
    labels = df.groupby('patientId')['Target'].max().reset_index()
    print(f"    Unique patients: {len(labels)}")

    records = []
    missing = 0
    for _, row in labels.iterrows():
        path = os.path.join(images_dir, f"{row['patientId']}.dcm")
        if os.path.exists(path):
            records.append((path, int(row['Target']), 'rsna'))
        else:
            missing += 1

    if missing:
        print(f"    ⚠️  {missing} labelled patients had no matching .dcm file")

    pos = sum(1 for r in records if r[1] == 1)
    print(f"    RSNA usable: {len(records)} images "
          f"[normal: {len(records) - pos} | pneumonia: {pos}]")

    return records


def load_pediatric_records():
    """Kaggle pediatric set: NORMAL/ and PNEUMONIA/ subfolders."""
    if not PEDIATRIC_DIR or not os.path.isdir(PEDIATRIC_DIR):
        print("\nℹ️  Pediatric dataset not found or disabled; using RSNA only.")
        return []

    records = []
    for folder, label in [("NORMAL", 0), ("PNEUMONIA", 1)]:
        folder_path = os.path.join(PEDIATRIC_DIR, folder)
        if not os.path.isdir(folder_path):
            print(f"    ⚠️  Missing pediatric folder: {folder_path}")
            continue
        for f in os.listdir(folder_path):
            if f.startswith('.') or f.startswith('._'):
                continue
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                records.append((os.path.join(folder_path, f), label, 'pediatric'))

    pos = sum(1 for r in records if r[1] == 1)
    print(f"\n🔍 Pediatric: {len(records)} images "
          f"[normal: {len(records) - pos} | pneumonia: {pos}]")

    return records


class ChestDataset(Dataset):
    """Handles both DICOM (RSNA) and standard image files (pediatric)."""

    def __init__(self, records, transform=None):
        self.records = records
        self.transform = transform

    def __len__(self):
        return len(self.records)

    def __getitem__(self, idx):
        path, label, source = self.records[idx]

        if path.lower().endswith('.dcm'):
            ds = pydicom.dcmread(path)
            arr = ds.pixel_array
            # RSNA DICOMs are 8-bit grayscale; normalize defensively anyway
            if arr.dtype != np.uint8:
                arr = arr.astype(np.float32)
                arr = 255.0 * (arr - arr.min()) / max(arr.max() - arr.min(), 1e-6)
                arr = arr.astype(np.uint8)
            image = Image.fromarray(arr).convert('RGB')
        else:
            image = Image.open(path).convert('RGB')

        if self.transform:
            image = self.transform(image)
        return image, label


def cap_per_class_per_source(records, cap):
    """Keeps the adult/pediatric mix balanced instead of letting one dominate."""
    if cap is None:
        return records

    buckets = {}
    for r in records:
        buckets.setdefault((r[1], r[2]), []).append(r)

    rng = random.Random(SEED)
    kept = []
    for (label, source), items in sorted(buckets.items()):
        if len(items) > cap:
            items = rng.sample(items, cap)
        kept.extend(items)
        print(f"    {source:10s} label {label}: {len(items)} images")

    rng.shuffle(kept)
    return kept


def balanced_accuracy(y_true, y_pred, n_classes=2):
    recalls = []
    for c in range(n_classes):
        mask = (y_true == c)
        if mask.sum() > 0:
            recalls.append((y_pred[mask] == c).sum() / mask.sum())
    return float(np.mean(recalls))


def main():
    records = load_rsna_records() + load_pediatric_records()

    if not records:
        print("❌ No images loaded. Check the paths at the top of this file.")
        return

    print(f"\n📊 Combined pool: {len(records)} images")
    print("    Capping per class per source:")
    records = cap_per_class_per_source(records, MAX_PER_CLASS_PER_SOURCE)

    # Split. Each RSNA patientId maps to exactly one image and pediatric
    # filenames are distinct patients, so an image-level split here does
    # NOT leak the way the rotated fracture dataset did.
    rng = random.Random(SEED)
    rng.shuffle(records)
    val_size = int(len(records) * VAL_FRACTION)
    val_records = records[:val_size]
    train_records = records[val_size:]

    train_pos = sum(1 for r in train_records if r[1] == 1)
    val_pos = sum(1 for r in val_records if r[1] == 1)
    print(f"\n📁 Split:")
    print(f"    Train: {len(train_records)} "
          f"[normal: {len(train_records) - train_pos} | pneumonia: {train_pos}]")
    print(f"    Val:   {len(val_records)} "
          f"[normal: {len(val_records) - val_pos} | pneumonia: {val_pos}]")

    dataloaders = {
        'train': DataLoader(ChestDataset(train_records, train_transforms),
                            batch_size=BATCH_SIZE, shuffle=True),
        'val': DataLoader(ChestDataset(val_records, val_transforms),
                          batch_size=BATCH_SIZE, shuffle=False),
    }
    dataset_sizes = {'train': len(train_records), 'val': len(val_records)}

    model = models.densenet121(weights=models.DenseNet121_Weights.DEFAULT)
    num_ftrs = model.classifier.in_features
    model.classifier = nn.Linear(num_ftrs, 2)
    model = model.to(DEVICE)

    train_counts = np.bincount([r[1] for r in train_records], minlength=2)
    class_weights = torch.tensor(
        train_counts.sum() / (2 * train_counts), dtype=torch.float
    ).to(DEVICE)
    print(f"\n⚖️  Class weights -> NORMAL: {class_weights[0]:.3f}, "
          f"{POSITIVE_LABEL}: {class_weights[1]:.3f}\n")

    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = optim.Adam(model.parameters(), lr=0.0001)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='max', factor=0.5, patience=2
    )

    since = time.time()
    best_wts = copy.deepcopy(model.state_dict())
    best_bal = 0.0

    for epoch in range(EPOCHS):
        print(f"Epoch {epoch + 1}/{EPOCHS}")
        print('-' * 40)

        for phase in ['train', 'val']:
            model.train() if phase == 'train' else model.eval()

            running_loss = 0.0
            all_preds, all_labels = [], []

            for inputs, labels in dataloaders[phase]:
                inputs, labels = inputs.to(DEVICE), labels.to(DEVICE)
                optimizer.zero_grad()

                with torch.set_grad_enabled(phase == 'train'):
                    outputs = model(inputs)
                    _, preds = torch.max(outputs, 1)
                    loss = criterion(outputs, labels)
                    if phase == 'train':
                        loss.backward()
                        optimizer.step()

                running_loss += loss.item() * inputs.size(0)
                all_preds.append(preds.cpu().numpy())
                all_labels.append(labels.cpu().numpy())

            all_preds = np.concatenate(all_preds)
            all_labels = np.concatenate(all_labels)

            epoch_loss = running_loss / dataset_sizes[phase]
            epoch_acc = (all_preds == all_labels).mean()
            epoch_bal = balanced_accuracy(all_labels, all_preds)

            print(f"  {phase:5s} loss: {epoch_loss:.4f} | acc: {epoch_acc:.4f} "
                  f"| balanced acc: {epoch_bal:.4f}")

            if phase == 'val':
                scheduler.step(epoch_bal)
                print(f"  confusion matrix [NORMAL, {POSITIVE_LABEL}]:")
                print(confusion_matrix(all_labels, all_preds))

                if epoch_bal > best_bal:
                    best_bal = epoch_bal
                    best_wts = copy.deepcopy(model.state_dict())
                    print(f"  ** new best (balanced acc {best_bal:.4f}) **")
        print()

    elapsed = time.time() - since
    print(f"Training complete in {elapsed // 60:.0f}m {elapsed % 60:.0f}s")
    print(f"Best validation balanced accuracy: {best_bal:.4f}")
    print("\nNOTE: expect LOWER than the pediatric-only model's 97.7%. RSNA is "
          "a harder, more varied dataset and radiologists themselves disagree "
          "on many studies. ~75-85% here is a genuine result that generalizes "
          "to adults, which the 97.7% model could not do at all.")

    model.load_state_dict(best_wts)

    model.eval()
    all_preds, all_labels = [], []
    with torch.no_grad():
        for inputs, labels in dataloaders['val']:
            outputs = model(inputs.to(DEVICE))
            _, preds = torch.max(outputs, 1)
            all_preds.append(preds.cpu().numpy())
            all_labels.append(labels.numpy())

    all_preds = np.concatenate(all_preds)
    all_labels = np.concatenate(all_labels)

    print("\n" + "=" * 55)
    print("FINAL VALIDATION REPORT")
    print("=" * 55)
    print(classification_report(all_labels, all_preds,
                                target_names=["NORMAL", POSITIVE_LABEL], digits=4))

    torch.save(model.state_dict(), OUTPUT_MODEL)
    print(f"🎉 Saved weights to: {OUTPUT_MODEL}")

    class_map = {0: "NORMAL", 1: POSITIVE_LABEL}
    with open(OUTPUT_CLASS_MAP, 'w') as f:
        json.dump(class_map, f, indent=2)
    print(f"Class map saved to '{OUTPUT_CLASS_MAP}': {class_map}")


if __name__ == "__main__":
    main()