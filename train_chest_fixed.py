# train_chest_fixed.py
#
# Corrected chest X-ray trainer.
#
# Fixes three problems in the original train.py:
#   1. Class imbalance (~3:1 PNEUMONIA:NORMAL) was unaddressed, so the model
#      collapsed toward always predicting PNEUMONIA.
#   2. The entire backbone was frozen, leaving too little capacity to adapt
#      ImageNet features to X-rays.
#   3. Kaggle's val/ folder has only 16 images, making "best model" selection
#      pure noise. We build a real validation split out of train/ instead.
#
# Also saves best_chest_model_class_map.json automatically so inference can
# never drift out of sync with training.

import os
import json
import time
import copy

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from torchvision import datasets, transforms, models
from torch.utils.data import DataLoader, random_split
from sklearn.metrics import classification_report, confusion_matrix

# ---------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------
DATA_DIR = "DATA_DIR = D:/datasets dp 2/dataset 4/archive/chest_xray/train"   # folder holding NORMAL/ and PNEUMONIA/
OUTPUT_MODEL = "best_chest_model.pth"
OUTPUT_CLASS_MAP = "best_chest_model_class_map.json"

EPOCHS = 12
BATCH_SIZE = 32
VAL_FRACTION = 0.2       # carve 20% of train/ off for real validation
SEED = 42

DEVICE = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print(f"Training on device: {DEVICE}")

torch.manual_seed(SEED)
np.random.seed(SEED)


# ---------------------------------------------------------------------
# Ignore macOS junk (__MACOSX, ._files) that can silently become a class
# ---------------------------------------------------------------------
def is_valid_image(path):
    filename = os.path.basename(path)
    if filename.startswith('.') or filename.startswith('._'):
        return False
    if '__MACOSX' in path:
        return False
    return filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))


# ---------------------------------------------------------------------
# Transforms. Validation must NOT have random augmentation.
# Resize((224,224)) is a squash resize -- this must stay identical to
# INFERENCE_TRANSFORM in model.py or inference sees different geometry.
# ---------------------------------------------------------------------
train_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(10),
    transforms.ColorJitter(brightness=0.15, contrast=0.15),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

val_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])


# ---------------------------------------------------------------------
# Dataset + real train/val split
# ---------------------------------------------------------------------
full_dataset = datasets.ImageFolder(root=DATA_DIR, is_valid_file=is_valid_image)
class_names = full_dataset.classes

print(f"\nDetected classes (index -> label): {full_dataset.class_to_idx}")
if len(class_names) != 2:
    raise SystemExit(
        f"Expected exactly 2 classes, found {len(class_names)}: {class_names}. "
        f"Check for stray folders like __MACOSX inside {DATA_DIR}."
    )

# Count per-class images so we can weight the loss correctly
label_counts = np.bincount([label for _, label in full_dataset.samples], minlength=len(class_names))
for idx, name in enumerate(class_names):
    print(f"  {name} (index {idx}): {label_counts[idx]} images")

imbalance_ratio = label_counts.max() / max(label_counts.min(), 1)
print(f"  Imbalance ratio: {imbalance_ratio:.2f}:1")

val_size = int(len(full_dataset) * VAL_FRACTION)
train_size = len(full_dataset) - val_size
train_subset, val_subset = random_split(
    full_dataset, [train_size, val_size],
    generator=torch.Generator().manual_seed(SEED)
)

# random_split shares the underlying dataset, so we wrap each subset to
# apply the correct transform (augment train, don't augment val).
class TransformedSubset(torch.utils.data.Dataset):
    def __init__(self, subset, transform):
        self.subset = subset
        self.transform = transform

    def __len__(self):
        return len(self.subset)

    def __getitem__(self, idx):
        image, label = self.subset[idx]
        if self.transform:
            image = self.transform(image)
        return image, label


train_dataset = TransformedSubset(train_subset, train_transform)
val_dataset = TransformedSubset(val_subset, val_transform)

dataloaders = {
    'train': DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True),
    'val': DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False),
}
dataset_sizes = {'train': len(train_dataset), 'val': len(val_dataset)}
print(f"\nSplit: {dataset_sizes['train']} train / {dataset_sizes['val']} val\n")


# ---------------------------------------------------------------------
# Model: unfreeze the last dense block so it can actually adapt
# ---------------------------------------------------------------------
model = models.densenet121(weights=models.DenseNet121_Weights.DEFAULT)

# Freeze everything first...
for param in model.parameters():
    param.requires_grad = False

# ...then unfreeze the final dense block + its norm layer. This gives the
# model real capacity to learn X-ray-specific features instead of relying
# purely on ImageNet edges/textures.
for param in model.features.denseblock4.parameters():
    param.requires_grad = True
for param in model.features.norm5.parameters():
    param.requires_grad = True

num_ftrs = model.classifier.in_features
model.classifier = nn.Linear(num_ftrs, len(class_names))
model = model.to(DEVICE)

trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
total = sum(p.numel() for p in model.parameters())
print(f"Trainable parameters: {trainable:,} / {total:,}\n")


# ---------------------------------------------------------------------
# Weighted loss -- this is the key fix for the majority-class collapse.
# Rarer class gets a proportionally larger weight.
# ---------------------------------------------------------------------
class_weights = torch.tensor(
    label_counts.sum() / (len(class_names) * label_counts),
    dtype=torch.float
).to(DEVICE)
print(f"Class weights (applied to loss): {dict(zip(class_names, class_weights.tolist()))}\n")

criterion = nn.CrossEntropyLoss(weight=class_weights)
optimizer = optim.Adam(
    [p for p in model.parameters() if p.requires_grad],
    lr=0.0001  # lower LR since we're fine-tuning real feature layers now
)
scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', factor=0.5, patience=2)


# ---------------------------------------------------------------------
# Training loop -- selects best model on BALANCED ACCURACY, not raw
# accuracy, so a majority-class-guessing model can't score well.
# ---------------------------------------------------------------------
def balanced_accuracy(y_true, y_pred, n_classes):
    recalls = []
    for c in range(n_classes):
        mask = (y_true == c)
        if mask.sum() > 0:
            recalls.append((y_pred[mask] == c).sum() / mask.sum())
    return float(np.mean(recalls))


def train_model():
    since = time.time()
    best_model_wts = copy.deepcopy(model.state_dict())
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
            epoch_bal_acc = balanced_accuracy(all_labels, all_preds, len(class_names))

            print(f"  {phase:5s} loss: {epoch_loss:.4f} | acc: {epoch_acc:.4f} | balanced acc: {epoch_bal_acc:.4f}")

            if phase == 'val':
                scheduler.step(epoch_bal_acc)
                # Per-class breakdown catches majority-class collapse immediately
                cm = confusion_matrix(all_labels, all_preds)
                print(f"  confusion matrix (rows=true, cols=pred):\n{cm}")

                if epoch_bal_acc > best_bal_acc:
                    best_bal_acc = epoch_bal_acc
                    best_model_wts = copy.deepcopy(model.state_dict())
                    print(f"  ** new best (balanced acc {best_bal_acc:.4f}) **")
        print()

    elapsed = time.time() - since
    print(f"Training complete in {elapsed // 60:.0f}m {elapsed % 60:.0f}s")
    print(f"Best validation balanced accuracy: {best_bal_acc:.4f}")

    model.load_state_dict(best_model_wts)
    return model


if __name__ == '__main__':
    trained_model = train_model()

    # Final detailed report on the validation split
    trained_model.eval()
    all_preds, all_labels = [], []
    with torch.no_grad():
        for inputs, labels in dataloaders['val']:
            inputs = inputs.to(DEVICE)
            outputs = trained_model(inputs)
            _, preds = torch.max(outputs, 1)
            all_preds.append(preds.cpu().numpy())
            all_labels.append(labels.numpy())

    all_preds = np.concatenate(all_preds)
    all_labels = np.concatenate(all_labels)

    print("\n" + "=" * 55)
    print("FINAL VALIDATION REPORT")
    print("=" * 55)
    print(classification_report(all_labels, all_preds, target_names=class_names, digits=4))

    torch.save(trained_model.state_dict(), OUTPUT_MODEL)
    print(f"Model weights saved to '{OUTPUT_MODEL}'")

    # Save the class map so inference can never drift out of sync.
    # ImageFolder's class_to_idx is the single source of truth.
    class_map = {str(idx): name.upper() for name, idx in full_dataset.class_to_idx.items()}
    with open(OUTPUT_CLASS_MAP, 'w') as f:
        json.dump(class_map, f, indent=2)
    print(f"Class map saved to '{OUTPUT_CLASS_MAP}': {class_map}")