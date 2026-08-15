# verify_fracture.py
#
# Tests the SAVED best_fracture_model.pth directly against images from the
# "not fractured" folder, using the exact same transform model.py uses.
#
# This bypasses app.py entirely, which separates two very different problems:
#   - If this script gets them RIGHT but the app gets them WRONG, the bug is
#     in how the app loads/serves the model (e.g. stale weights in memory).
#   - If this script ALSO gets them wrong, the saved weights themselves are
#     bad and the problem is in training/saving.

import os
import json
import random

import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image

MODEL_PATH = "best_fracture_model.pth"
CLASS_MAP_PATH = "best_fracture_model_class_map.json"

# Point these at your actual fracture dataset folders
NOT_FRACTURED_DIR = "D:/datasets dp 2/dataset 2/archive (3)/archive (6)/train/not fractured"
FRACTURED_DIR = "D:/datasets dp 2/dataset 2/archive (3)/archive (6)/train/fractured"

N_SAMPLES = 20  # how many random images to test from each folder

# Must match INFERENCE_TRANSFORM in model.py exactly
INFERENCE_TRANSFORM = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])


def load_model():
    model = models.densenet121(weights=None)
    num_ftrs = model.classifier.in_features

    state_dict = torch.load(MODEL_PATH, map_location=torch.device('cpu'))
    num_classes = state_dict['classifier.weight'].shape[0]
    model.classifier = nn.Linear(num_ftrs, num_classes)
    model.load_state_dict(state_dict)
    model.eval()

    print(f"Loaded {MODEL_PATH} with {num_classes} output classes")

    with open(CLASS_MAP_PATH) as f:
        raw = json.load(f)
    class_map = {int(k): v for k, v in raw.items()}
    print(f"Class map: {class_map}\n")

    return model, class_map


def sample_images(folder, n):
    if not os.path.isdir(folder):
        print(f"❌ Folder not found: {folder}")
        return []
    files = [f for f in os.listdir(folder)
             if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))
             and not f.startswith('.')]
    random.seed(42)
    return [os.path.join(folder, f) for f in random.sample(files, min(n, len(files)))]


def test_folder(model, class_map, folder, expected_label, expected_index):
    paths = sample_images(folder, N_SAMPLES)
    if not paths:
        return

    print("=" * 60)
    print(f"Testing {len(paths)} images from: {os.path.basename(folder)}")
    print(f"Expected prediction: {expected_label} (index {expected_index})")
    print("=" * 60)

    correct = 0
    for path in paths:
        image = Image.open(path).convert('RGB')
        tensor = INFERENCE_TRANSFORM(image).unsqueeze(0)

        with torch.no_grad():
            output = model(tensor)
            probs = torch.nn.functional.softmax(output, dim=1).squeeze()
            pred_idx = torch.argmax(probs).item()

        is_correct = (pred_idx == expected_index)
        correct += is_correct
        mark = "✅" if is_correct else "❌"

        print(f"  {mark} {os.path.basename(path)[:35]:35s} "
              f"-> {class_map[pred_idx]:20s} "
              f"[{class_map.get(0)}: {probs[0]*100:5.1f}% | "
              f"{class_map.get(1)}: {probs[1]*100:5.1f}%]")

    print(f"\n  Result: {correct}/{len(paths)} correct "
          f"({100*correct/len(paths):.1f}%)\n")


if __name__ == "__main__":
    model, class_map = load_model()
    test_folder(model, class_map, NOT_FRACTURED_DIR, "NORMAL", 0)
    test_folder(model, class_map, FRACTURED_DIR, "FRACTURE DETECTED", 1)