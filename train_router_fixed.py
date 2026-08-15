# train_router_fixed.py
#
# Corrected router trainer (decides: chest vs brain vs bone).
#
# Fixes the problems in the original train_router.py:
#   1. It never saved a class map, so router_class_map.json was a hand-written
#      guess. If that guess didn't match ImageFolder's alphabetical ordering,
#      EVERY routing decision came out scrambled. Now the map is derived
#      directly from the data and saved automatically.
#   2. Only 2 epochs with no validation split -- no way to know if it learned.
#   3. No class weighting, so an imbalanced router dataset biases toward
#      whichever organ has the most images.
#   4. No __MACOSX / hidden-file filtering.

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
from PIL import ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True

# ---------------------------------------------------------------------
# Config -- UPDATE DATA_DIR to wherever your router folders actually live.
# That folder must contain one subfolder per organ, e.g.:
#   router_data/train/bone/    router_data/train/brain/    router_data/train/chest/
# ---------------------------------------------------------------------
DATA_DIR = "data/router_data/train"
OUTPUT_MODEL = "best_router_model.pth"
OUTPUT_CLASS_MAP = "router_class_map.json"

EPOCHS = 10
BATCH_SIZE = 32
VAL_FRACTION = 0.2
SEED = 42

# Cap images per class. The router dataset is wildly imbalanced
# (~49k bone vs ~253 brain), which both (a) biases the model toward
# never predicting the rare class and (b) makes each epoch take hours
# on CPU. Distinguishing bone/brain/chest is a visually easy task, so
# a few hundred balanced images per class is plenty -- far better than
# relying on a class weight of ~80x to paper over a 195:1 ratio.
# Set to None to use every image.
MAX_PER_CLASS = 253

DEVICE = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print(f"Training on device: {DEVICE}")

torch.manual_seed(SEED)
np.random.seed(SEED)


def is_valid_image(path):
    filename = os.path.basename(path)
    if filename.startswith('.') or filename.startswith('._'):
        return False
    if '__MACOSX' in path:
        return False
    return filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))


# Must stay identical to INFERENCE_TRANSFORM in model.py
train_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(10),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

val_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])


# ---------------------------------------------------------------------
# Load data and inspect what we actually got
# ---------------------------------------------------------------------
full_dataset = datasets.ImageFolder(root=DATA_DIR, is_valid_file=is_valid_image)
base_dataset = full_dataset  # keep a handle to the original for class_to_idx / samples
class_names = full_dataset.classes

print(f"\nDetected classes (label -> index): {full_dataset.class_to_idx}")
print("^^ THIS is the ground truth. router_class_map.json will be written to match it.\n")

if len(class_names) < 2:
    raise SystemExit(
        f"Only found {len(class_names)} class folder(s) in {DATA_DIR}: {class_names}. "
        f"Expected one subfolder per organ (e.g. bone/, brain/, chest/)."
    )

label_counts = np.bincount([label for _, label in full_dataset.samples], minlength=len(class_names))
for idx, name in enumerate(class_names):
    print(f"  {name} (index {idx}): {label_counts[idx]} images")

if label_counts.min() == 0:
    raise SystemExit("At least one class folder contains zero valid images.")

print(f"  Imbalance ratio: {label_counts.max() / label_counts.min():.2f}:1\n")

# ---------------------------------------------------------------------
# Balance by capping each class. Keeps a random sample per class so we
# don't just take the alphabetically-first N files from one folder.
# ---------------------------------------------------------------------
if MAX_PER_CLASS is not None:
    rng = np.random.default_rng(SEED)
    indices_by_class = {c: [] for c in range(len(class_names))}
    for i, (_, label) in enumerate(full_dataset.samples):
        indices_by_class[label].append(i)

    kept_indices = []
    for c, idxs in indices_by_class.items():
        idxs = np.array(idxs)
        if len(idxs) > MAX_PER_CLASS:
            idxs = rng.choice(idxs, size=MAX_PER_CLASS, replace=False)
        kept_indices.extend(idxs.tolist())

    rng.shuffle(kept_indices)
    full_dataset = torch.utils.data.Subset(full_dataset, kept_indices)

    # Recount after capping
    capped_labels = [base_dataset.samples[i][1] for i in kept_indices]
    label_counts = np.bincount(capped_labels, minlength=len(class_names))
    print(f"After capping to {MAX_PER_CLASS} per class:")
    for idx, name in enumerate(class_names):
        print(f"  {name} (index {idx}): {label_counts[idx]} images")
    print(f"  Imbalance ratio: {label_counts.max() / label_counts.min():.2f}:1\n")

val_size = int(len(full_dataset) * VAL_FRACTION)
train_size = len(full_dataset) - val_size
train_subset, val_subset = random_split(
    full_dataset, [train_size, val_size],
    generator=torch.Generator().manual_seed(SEED)
)


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


dataloaders = {
    'train': DataLoader(TransformedSubset(train_subset, train_transform),
                        batch_size=BATCH_SIZE, shuffle=True),
    'val': DataLoader(TransformedSubset(val_subset, val_transform),
                      batch_size=BATCH_SIZE, shuffle=False),
}
dataset_sizes = {'train': train_size, 'val': val_size}
print(f"Split: {train_size} train / {val_size} val\n")


# ---------------------------------------------------------------------
# Model -- unfreeze last dense block so it can learn organ-level features
# ---------------------------------------------------------------------
model = models.densenet121(weights=models.DenseNet121_Weights.DEFAULT)

for param in model.parameters():
    param.requires_grad = False
for param in model.features.denseblock4.parameters():
    param.requires_grad = True
for param in model.features.norm5.parameters():
    param.requires_grad = True

num_ftrs = model.classifier.in_features
model.classifier = nn.Linear(num_ftrs, len(class_names))
model = model.to(DEVICE)

trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
print(f"Trainable parameters: {trainable:,}\n")

class_weights = torch.tensor(
    label_counts.sum() / (len(class_names) * label_counts),
    dtype=torch.float
).to(DEVICE)
print(f"Class weights: {dict(zip(class_names, [round(w, 3) for w in class_weights.tolist()]))}\n")

criterion = nn.CrossEntropyLoss(weight=class_weights)
optimizer = optim.Adam([p for p in model.parameters() if p.requires_grad], lr=0.0001)
scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', factor=0.5, patience=2)


def balanced_accuracy(y_true, y_pred, n_classes):
    recalls = []
    for c in range(n_classes):
        mask = (y_true == c)
        if mask.sum() > 0:
            recalls.append((y_pred[mask] == c).sum() / mask.sum())
    return float(np.mean(recalls))


def train_model():
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
            epoch_bal = balanced_accuracy(all_labels, all_preds, len(class_names))

            print(f"  {phase:5s} loss: {epoch_loss:.4f} | acc: {epoch_acc:.4f} | balanced acc: {epoch_bal:.4f}")

            if phase == 'val':
                scheduler.step(epoch_bal)
                print(f"  confusion matrix (rows=true, cols=pred) order={class_names}:")
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
    return model


if __name__ == '__main__':
    trained = train_model()

    trained.eval()
    all_preds, all_labels = [], []
    with torch.no_grad():
        for inputs, labels in dataloaders['val']:
            outputs = trained(inputs.to(DEVICE))
            _, preds = torch.max(outputs, 1)
            all_preds.append(preds.cpu().numpy())
            all_labels.append(labels.numpy())

    all_preds = np.concatenate(all_preds)
    all_labels = np.concatenate(all_labels)

    print("\n" + "=" * 55)
    print("FINAL ROUTER VALIDATION REPORT")
    print("=" * 55)
    print(classification_report(all_labels, all_preds, target_names=class_names, digits=4))

    torch.save(trained.state_dict(), OUTPUT_MODEL)
    print(f"Model weights saved to '{OUTPUT_MODEL}'")

    # THE CRITICAL FIX: derive the class map from ImageFolder's own
    # class_to_idx rather than guessing. model.py reads this file, so
    # inference labels can now never drift out of sync with training.
    class_map = {str(idx): name.lower() for name, idx in base_dataset.class_to_idx.items()}
    with open(OUTPUT_CLASS_MAP, 'w') as f:
        json.dump(class_map, f, indent=2)
    print(f"Class map saved to '{OUTPUT_CLASS_MAP}': {class_map}")

    print("\nNOTE: model.py expects the labels 'chest', 'brain', and 'bone' "
          "(app.py branches on those exact strings). If the map above shows "
          "different names, either rename your dataset folders to match, or "
          "update the branching logic in app.py accordingly.")