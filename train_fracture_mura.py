# train_fracture_mura.py
#
# Retrains the bone/fracture expert on MURA instead of the small rotated
# dataset.
#
# WHY: the previous fracture dataset was ~120-180 unique images expanded to
# 8,863 via rotation (filenames like "14-rotated1-rotated2.jpg"). Two problems:
#   1. Rotated copies teach the model almost nothing new, so it never learned
#      to generalize -- hence confident nonsense on outside images.
#   2. random_split scattered rotations of the SAME original across train and
#      val, so validation was testing on memorized images. The 98.94% score
#      was inflated by leakage.
#
# MURA has ~36k genuinely distinct radiographs across 7 body parts, labeled
# via folder names (studyN_positive / studyN_negative).
#
# IMPORTANT CAVEAT: MURA labels studies as "abnormal", which covers fractures
# but ALSO hardware, degenerative changes, and lesions. So class 1 here means
# "abnormality detected", which is broader than "fracture". Reflect that in
# your writeup and in the label shown to users.

import os
import json
import time
import copy
import random

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from torchvision import models, transforms
from torch.utils.data import DataLoader, Dataset
from PIL import Image, ImageFile
from sklearn.metrics import classification_report, confusion_matrix

ImageFile.LOAD_TRUNCATED_IMAGES = True

# ---------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------
MURA_TRAIN_DIR = "D:/datasets dp 2/dataset 3/archive (1)/MURA-v1.1/train"
OUTPUT_MODEL = "best_fracture_model.pth"
OUTPUT_CLASS_MAP = "best_fracture_model_class_map.json"
POSITIVE_LABEL = "BONE ABNORMALITY / FRACTURE"

EPOCHS = 10
BATCH_SIZE = 32
VAL_FRACTION = 0.2
SEED = 42

# MURA is large (~36k images). On CPU that's many hours per epoch, so cap it.
# Unlike the rotated dataset, these are all DISTINCT images, so a capped
# sample here is far more valuable than the full rotated set was.
# Set to None to use everything (recommended only if you have a GPU).
MAX_PER_CLASS = 3000

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"⚡ Device: {DEVICE}")

torch.manual_seed(SEED)
np.random.seed(SEED)
random.seed(SEED)


train_transforms = transforms.Compose([
    transforms.Resize((256, 256)),
    transforms.RandomResizedCrop(224, scale=(0.8, 1.0)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(15),
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


def scan_mura(root_dir):
    """
    Walks MURA's structure:
      train/XR_WRIST/patient00001/study1_positive/image1.png

    Returns (records, patients) where each record is
    (image_path, label, patient_id, body_part).

    Label comes from the study folder name: _positive -> 1, _negative -> 0.
    """
    records = []
    body_part_counts = {}

    print(f"🔍 Scanning MURA at: {root_dir}")

    for body_part in sorted(os.listdir(root_dir)):
        bp_path = os.path.join(root_dir, body_part)
        if not os.path.isdir(bp_path):
            continue

        bp_pos = bp_neg = 0

        for patient in os.listdir(bp_path):
            patient_path = os.path.join(bp_path, patient)
            if not os.path.isdir(patient_path):
                continue

            for study in os.listdir(patient_path):
                study_path = os.path.join(patient_path, study)
                if not os.path.isdir(study_path):
                    continue

                study_lower = study.lower()
                if study_lower.endswith('_positive'):
                    label = 1
                elif study_lower.endswith('_negative'):
                    label = 0
                else:
                    continue  # unrecognized study folder, skip

                for file in os.listdir(study_path):
                    if file.startswith('.') or file.startswith('._'):
                        continue
                    if not file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                        continue

                    # patient id is namespaced by body part so IDs can't collide
                    patient_key = f"{body_part}/{patient}"
                    records.append((
                        os.path.join(study_path, file), label, patient_key, body_part
                    ))
                    if label == 1:
                        bp_pos += 1
                    else:
                        bp_neg += 1

        if bp_pos or bp_neg:
            body_part_counts[body_part] = (bp_neg, bp_pos)

    print("\n📊 Images per body part [normal / abnormal]:")
    for bp, (neg, pos) in body_part_counts.items():
        print(f"    {bp:15s} {neg:6d} / {pos:6d}")

    return records


class MuraDataset(Dataset):
    def __init__(self, records, transform=None):
        self.records = records
        self.transform = transform

    def __len__(self):
        return len(self.records)

    def __getitem__(self, idx):
        path, label, _, _ = self.records[idx]
        image = Image.open(path).convert('RGB')
        if self.transform:
            image = self.transform(image)
        return image, label


def balanced_accuracy(y_true, y_pred, n_classes=2):
    recalls = []
    for c in range(n_classes):
        mask = (y_true == c)
        if mask.sum() > 0:
            recalls.append((y_pred[mask] == c).sum() / mask.sum())
    return float(np.mean(recalls))


def main():
    if not os.path.isdir(MURA_TRAIN_DIR):
        print(f"❌ ERROR: '{MURA_TRAIN_DIR}' not found.")
        return

    records = scan_mura(MURA_TRAIN_DIR)
    if not records:
        print("❌ ERROR: no images found. Check the folder structure.")
        return

    total_pos = sum(1 for r in records if r[1] == 1)
    print(f"\n📊 Total: {len(records)} images "
          f"[normal: {len(records) - total_pos} | abnormal: {total_pos}]")

    # -----------------------------------------------------------------
    # PATIENT-LEVEL SPLIT. This is the critical fix. Splitting by image
    # would put different X-rays of the SAME patient in both train and val,
    # letting the model recognize the patient rather than the pathology --
    # the same leakage that inflated the old rotated dataset's scores.
    # -----------------------------------------------------------------
    patients = sorted({r[2] for r in records})
    random.Random(SEED).shuffle(patients)
    n_val_patients = int(len(patients) * VAL_FRACTION)
    val_patients = set(patients[:n_val_patients])

    train_records = [r for r in records if r[2] not in val_patients]
    val_records = [r for r in records if r[2] in val_patients]

    print(f"\n📁 Patient-level split: {len(patients) - n_val_patients} train "
          f"patients / {n_val_patients} val patients")

    # Cap per class (training only -- keep validation intact for honest eval)
    if MAX_PER_CLASS is not None:
        by_class = {0: [], 1: []}
        for r in train_records:
            by_class[r[1]].append(r)

        capped = []
        rng = random.Random(SEED)
        for label, items in by_class.items():
            if len(items) > MAX_PER_CLASS:
                items = rng.sample(items, MAX_PER_CLASS)
            capped.extend(items)
        rng.shuffle(capped)
        train_records = capped
        print(f"    Capped training set to {MAX_PER_CLASS} per class")

    train_pos = sum(1 for r in train_records if r[1] == 1)
    val_pos = sum(1 for r in val_records if r[1] == 1)
    print(f"    Train: {len(train_records)} images "
          f"[normal: {len(train_records) - train_pos} | abnormal: {train_pos}]")
    print(f"    Val:   {len(val_records)} images "
          f"[normal: {len(val_records) - val_pos} | abnormal: {val_pos}]\n")

    dataloaders = {
        'train': DataLoader(MuraDataset(train_records, train_transforms),
                            batch_size=BATCH_SIZE, shuffle=True),
        'val': DataLoader(MuraDataset(val_records, val_transforms),
                          batch_size=BATCH_SIZE, shuffle=False),
    }
    dataset_sizes = {'train': len(train_records), 'val': len(val_records)}

    # ---------------- Model ----------------
    model = models.densenet121(weights=models.DenseNet121_Weights.DEFAULT)
    num_ftrs = model.classifier.in_features
    model.classifier = nn.Linear(num_ftrs, 2)
    model = model.to(DEVICE)

    train_counts = np.bincount([r[1] for r in train_records], minlength=2)
    class_weights = torch.tensor(
        train_counts.sum() / (2 * train_counts), dtype=torch.float
    ).to(DEVICE)
    print(f"⚖️  Class weights -> NORMAL: {class_weights[0]:.3f}, "
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
    print("\nNOTE: expect a LOWER number than the old rotated dataset's 98.9%. "
          "That score was inflated by leakage. A ~80-85% here on unseen "
          "patients is a genuine result and will generalize far better.")

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
    print("FINAL VALIDATION REPORT (unseen patients)")
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