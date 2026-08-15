import os
import json
import time
import copy

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from torchvision import models, transforms
from torch.utils.data import DataLoader, Dataset, random_split
from PIL import Image
from sklearn.metrics import classification_report, confusion_matrix

# =====================================================================
# What changed vs the original train_experts.py:
#
#   1. ADDED A VALIDATION SPLIT. The original trained on 100% of the data
#      and reported only TRAINING accuracy -- so "Diagnostic Accuracy:
#      0.99" told you nothing about generalization, and overfitting was
#      completely invisible. This was the single biggest problem.
#   2. Class weighting, so an imbalanced dataset can't be gamed by always
#      predicting the majority class.
#   3. Best-checkpoint selection on BALANCED accuracy, not raw accuracy.
#   4. Confusion matrix printed every epoch so collapse is obvious.
#   5. Stronger augmentation (affine, crops, brightness/contrast). This
#      matters a lot for your domain-shift problem: models that only ever
#      see clean, consistent training images learn dataset fingerprints
#      (borders, contrast curves, resolution) instead of anatomy, then
#      fail on X-rays from anywhere else.
#   6. More epochs (5 was far too few) + LR scheduling.
# =====================================================================

EPOCHS = 15
BATCH_SIZE = 16
VAL_FRACTION = 0.2
SEED = 42

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"⚡ Hardware Device Initialized: {DEVICE}")

torch.manual_seed(SEED)
np.random.seed(SEED)


# Training transform -- deliberately aggressive to fight dataset-artifact
# learning. Must still end with the same Resize/Normalize as inference.
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

# Validation transform -- must match INFERENCE_TRANSFORM in model.py exactly.
val_transforms = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])


class MedicalBinaryDataset(Dataset):
    """
    Labels images based on their immediate parent folder name, matched
    EXACTLY (after lowercasing) against a configurable label_map.

    Matching is EXACT, not substring -- this matters because a naive
    substring check like "'fractured' in folder_name" would incorrectly
    match BOTH "fractured" and "not fractured" as positive, since the
    second contains the first as a substring.
    """
    DEFAULT_LABEL_MAP = {"yes": 1, "no": 0, "positive": 1, "negative": 0}

    def __init__(self, root_dir, transform=None, label_map=None):
        self.root_dir = root_dir
        self.transform = transform
        self.image_paths = []
        self.labels = []
        self.label_map = label_map or self.DEFAULT_LABEL_MAP

        unmatched_folders = set()

        print(f"🔍 Deep-scanning directory tree in: {root_dir}...")
        print(f"    Using label map: {self.label_map}")

        for root, dirs, files in os.walk(root_dir):
            if '__MACOSX' in root:
                continue
            for file in files:
                if file.startswith('.') or file.startswith('._'):
                    continue

                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                    full_path = os.path.join(root, file)
                    parent_folder = os.path.basename(root).lower()

                    if parent_folder in self.label_map:
                        self.image_paths.append(full_path)
                        self.labels.append(self.label_map[parent_folder])
                    else:
                        unmatched_folders.add(root)

        if unmatched_folders:
            print(f"⚠️  WARNING: {len(unmatched_folders)} folder(s) did not match "
                  f"the label map and were SKIPPED ENTIRELY:")
            for folder in sorted(unmatched_folders):
                print(f"     - {folder}")

        pos_count = sum(self.labels)
        neg_count = len(self.labels) - pos_count
        print(f"📊 Scan Complete! Found {len(self.image_paths)} valid images "
              f"-> [Normal (0): {neg_count} | Affected (1): {pos_count}]")
        if neg_count > 0 and pos_count > 0:
            ratio = max(neg_count, pos_count) / min(neg_count, pos_count)
            print(f"    Imbalance ratio: {ratio:.2f}:1")

        self.idx_to_class = {0: "NORMAL", 1: "AFFECTED"}

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        img_path = self.image_paths[idx]
        image = Image.open(img_path).convert('RGB')
        label = self.labels[idx]
        if self.transform:
            image = self.transform(image)
        return image, label


class TransformedSubset(Dataset):
    """Applies a different transform to a Subset (augment train, not val)."""

    def __init__(self, subset, transform):
        self.subset = subset
        self.transform = transform

    def __len__(self):
        return len(self.subset)

    def __getitem__(self, idx):
        # subset[idx] returns the raw PIL image because the base dataset
        # was constructed with transform=None
        image, label = self.subset[idx]
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


def train_binary_diagnostic_model(data_dir, output_filename,
                                  positive_label="AFFECTED", label_map=None):
    """
    positive_label: human-readable label for class 1, e.g.
        "BRAIN ABNORMALITY / TUMOR" or "FRACTURE DETECTED".
        Written into the saved class map so model.py shows the right text.
    """
    print(f"\n==================================================")
    print(f"🏥 Training Diagnostic Expert: {output_filename}")
    print(f"==================================================")

    if not os.path.exists(data_dir):
        print(f"❌ ERROR: Directory '{data_dir}' not found!")
        return

    # transform=None here; the per-split wrappers apply the right transform
    base_dataset = MedicalBinaryDataset(data_dir, transform=None, label_map=label_map)

    if len(base_dataset) == 0 or len(set(base_dataset.labels)) < 2:
        print("❌ ERROR: Could not find both Normal (0) and Affected (1) classes! "
              "Check folder names against the label map above.")
        return

    # ---------------- Real train/val split ----------------
    val_size = int(len(base_dataset) * VAL_FRACTION)
    train_size = len(base_dataset) - val_size
    train_subset, val_subset = random_split(
        base_dataset, [train_size, val_size],
        generator=torch.Generator().manual_seed(SEED)
    )
    print(f"📁 Split: {train_size} train / {val_size} val")

    dataloaders = {
        'train': DataLoader(TransformedSubset(train_subset, train_transforms),
                            batch_size=BATCH_SIZE, shuffle=True),
        'val': DataLoader(TransformedSubset(val_subset, val_transforms),
                          batch_size=BATCH_SIZE, shuffle=False),
    }
    dataset_sizes = {'train': train_size, 'val': val_size}

    # ---------------- Model ----------------
    model = models.densenet121(weights=models.DenseNet121_Weights.DEFAULT)
    num_ftrs = model.classifier.in_features
    model.classifier = nn.Linear(num_ftrs, 2)
    model = model.to(DEVICE)

    # ---------------- Weighted loss ----------------
    label_counts = np.bincount(base_dataset.labels, minlength=2)
    class_weights = torch.tensor(
        label_counts.sum() / (2 * label_counts), dtype=torch.float
    ).to(DEVICE)
    print(f"⚖️  Class weights -> NORMAL: {class_weights[0]:.3f}, "
          f"{positive_label}: {class_weights[1]:.3f}\n")

    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = optim.Adam(model.parameters(), lr=0.0001)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='max', factor=0.5, patience=2
    )

    # ---------------- Training loop ----------------
    since = time.time()
    best_wts = copy.deepcopy(model.state_dict())
    best_bal_acc = 0.0

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
                print(f"  confusion matrix (rows=true, cols=pred) "
                      f"[NORMAL, {positive_label}]:")
                print(confusion_matrix(all_labels, all_preds))

                if epoch_bal > best_bal_acc:
                    best_bal_acc = epoch_bal
                    best_wts = copy.deepcopy(model.state_dict())
                    print(f"  ** new best (balanced acc {best_bal_acc:.4f}) **")
        print()

    elapsed = time.time() - since
    print(f"Training complete in {elapsed // 60:.0f}m {elapsed % 60:.0f}s")
    print(f"Best validation balanced accuracy: {best_bal_acc:.4f}")

    model.load_state_dict(best_wts)

    # ---------------- Final report ----------------
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
                                target_names=["NORMAL", positive_label], digits=4))

    torch.save(model.state_dict(), output_filename)
    print(f"🎉 Saved diagnostic weights to: {output_filename}")

    base = os.path.splitext(output_filename)[0]
    class_map_path = f"{base}_class_map.json"
    class_map = {0: "NORMAL", 1: positive_label}
    with open(class_map_path, 'w') as f:
        json.dump(class_map, f, indent=2)
    print(f"Verified label map saved to '{class_map_path}': {class_map}")


if __name__ == "__main__":
    train_binary_diagnostic_model(
        data_dir="D:/datasets dp 2/dataset 5_brain",
        output_filename="best_brain_model.pth",
        positive_label="BRAIN ABNORMALITY / TUMOR"
    )