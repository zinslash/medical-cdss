import json
import torch
import torch.nn as nn
from torchvision import models, transforms
import cv2
import numpy as np
from PIL import Image
import os


# =====================================================================
# Shared transform — THIS MUST MATCH TRAINING EXACTLY.
# Training scripts use transforms.Resize((224, 224)) directly (a squash
# resize, not a resize-then-crop). Inference must use the identical
# pipeline or the model sees geometrically different images than it
# was trained on.
# =====================================================================
INFERENCE_TRANSFORM = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])


def load_class_map(json_path, fallback):
    """
    Loads a {index: label} mapping saved at training time.
    Falls back to a hardcoded guess ONLY if the file doesn't exist yet,
    and prints a loud warning so this never fails silently.
    """
    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            raw = json.load(f)
        # JSON keys are always strings; convert back to int
        class_map = {int(k): v for k, v in raw.items()}
        print(f"✅ Loaded verified label map from {json_path}: {class_map}")
        return class_map
    else:
        print(f"⚠️  WARNING: '{json_path}' not found. Falling back to an "
              f"UNVERIFIED hardcoded guess: {fallback}. "
              f"Re-run training with the updated training scripts to "
              f"generate this file and remove the guesswork.")
        return fallback


class RouterAIModel:
    def __init__(self, model_path='best_router_model.pth', class_map_path='router_class_map.json'):
        self.model = models.densenet121(weights=None)
        num_ftrs = self.model.classifier.in_features
        self.model.classifier = nn.Linear(num_ftrs, 3)  # 3 classes: bone, brain, chest

        if os.path.exists(model_path):
            self.model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
            print(f"✅ Router AI weights loaded successfully from: {model_path}")
        else:
            print(f"⚠️ WARNING: Router weights '{model_path}' not found.")

        self.model.eval()
        self.transform = INFERENCE_TRANSFORM

        # Fallback assumes alphabetical ImageFolder ordering (bone, brain, chest)
        # which is DenseNet/ImageFolder default IF your folders are literally
        # named to sort that way. Verify against router_class_map.json.
        self.class_map = load_class_map(
            class_map_path,
            fallback={0: "bone", 1: "brain", 2: "chest"}
        )

    def predict_scan_type(self, image_bytes):
        self.model.eval()
        image = Image.open(image_bytes).convert('RGB')
        input_tensor = self.transform(image).unsqueeze(0)

        with torch.no_grad():
            output = self.model(input_tensor)
            probabilities = torch.nn.functional.softmax(output, dim=1).squeeze()
            predicted_index = torch.argmax(probabilities).item()
            confidence = probabilities[predicted_index].item()

        if confidence < 0.60:
            return "unknown"

        return self.class_map[predicted_index]


class MedicalAIModel:
    def __init__(self, model_path='best_chest_model.pth', num_classes=2, organ_type=None,
                 class_map_path=None):
        self.model = models.densenet121(weights=None)
        num_ftrs = self.model.classifier.in_features

        if os.path.exists(model_path):
            state_dict = torch.load(model_path, map_location=torch.device('cpu'))
            if 'classifier.weight' in state_dict:
                num_classes = state_dict['classifier.weight'].shape[0]
            self.model.classifier = nn.Linear(num_ftrs, num_classes)
            self.model.load_state_dict(state_dict)
            print(f"✅ Expert AI weights ({num_classes} classes) loaded successfully from: {model_path}")
        else:
            self.model.classifier = nn.Linear(num_ftrs, num_classes)
            print(f"⚠️ WARNING: '{model_path}' not found. Predictions will not be accurate.")

        self.num_classes = num_classes
        self.model.eval()

        if organ_type:
            self.organ_type = organ_type.lower()
        elif "brain" in model_path.lower():
            self.organ_type = "brain"
        elif "fracture" in model_path.lower() or "bone" in model_path.lower():
            self.organ_type = "bone"
        else:
            self.organ_type = "chest"

        # Auto-derive the expected class-map filename if not explicitly given,
        # e.g. best_chest_model.pth -> chest_class_map.json
        if class_map_path is None:
            base = os.path.splitext(os.path.basename(model_path))[0]
            class_map_path = f"{base}_class_map.json"

        default_fallback = {
            "chest": {0: "NORMAL", 1: "PNEUMONIA"},
            "brain": {0: "NORMAL", 1: "BRAIN ABNORMALITY / TUMOR"},
            "bone": {0: "NORMAL", 1: "FRACTURE DETECTED"}
        }.get(self.organ_type, {0: "NORMAL", 1: "ABNORMALITY DETECTED"})

        # MURA-style 7-class bone model uses a different label set entirely.
        self.mura_labels = {
            0: "ELBOW ABNORMALITY / FRACTURE", 1: "FINGER ABNORMALITY / FRACTURE",
            2: "FOREARM ABNORMALITY / FRACTURE", 3: "HAND ABNORMALITY / FRACTURE",
            4: "HUMERUS ABNORMALITY / FRACTURE", 5: "SHOULDER ABNORMALITY / FRACTURE",
            6: "WRIST ABNORMALITY / FRACTURE"
        }

        if self.organ_type == "bone" and self.num_classes > 2:

            self.class_labels = self.mura_labels
        else:
            self.class_labels = load_class_map(class_map_path, fallback=default_fallback)

        self.gradients = None
        self.activations = None

        target_layer = self.model.features.denseblock4.denselayer16.conv2
        target_layer.register_forward_hook(self.save_activation)
        target_layer.register_full_backward_hook(self.save_gradient)

        self.transform = INFERENCE_TRANSFORM

    def save_activation(self, module, input, output):
        self.activations = output

    def save_gradient(self, module, grad_input, grad_output):
        self.gradients = grad_output[0]

    def predict_and_explain(self, image_bytes):
        self.model.eval()

        image = Image.open(image_bytes).convert('RGB')
        input_tensor = self.transform(image).unsqueeze(0)

        torch.set_grad_enabled(True)
        output = self.model(input_tensor)
        probabilities = torch.nn.functional.softmax(output, dim=1).squeeze()

        print("\n" + "=" * 50)
        print(f"🧠 [DEBUG] INFERENCE ENGINE ({self.organ_type.upper()})")
        if self.num_classes == 2:
            print(f"   -> {self.class_labels.get(0, 'Class 0')}: {probabilities[0].item() * 100:.2f}%")
            print(f"   -> {self.class_labels.get(1, 'Class 1')}: {probabilities[1].item() * 100:.2f}%")
        print("=" * 50 + "\n")

        # No more hardcoded threshold override — always trust the model's
        # own decision boundary, exactly as it was trained with CrossEntropyLoss.
        predicted_index = torch.argmax(probabilities).item()
        confidence = probabilities[predicted_index].item()

        predicted_class = self.class_labels.get(
            predicted_index, f"ABNORMALITY DETECTED (CLASS {predicted_index})"
        )

        self.model.zero_grad()
        output[0, predicted_index].backward(retain_graph=True)

        activations = self.activations.detach().clone()
        gradients = self.gradients.detach().clone()

        pooled_gradients = torch.mean(gradients, dim=[0, 2, 3])
        for i in range(activations.size(1)):
            activations[:, i, :, :] *= pooled_gradients[i]

        raw_cam = torch.mean(activations, dim=1).squeeze().numpy()
        raw_cam = np.maximum(raw_cam, 0)

        if np.max(raw_cam) == 0:
            raw_cam = np.abs(torch.mean(activations, dim=1).squeeze().numpy())

        max_val = np.max(raw_cam)
        min_val = np.min(raw_cam)
        if max_val - min_val > 0:
            raw_cam = (raw_cam - min_val) / (max_val - min_val)
        else:
            raw_cam = np.zeros_like(raw_cam)

        raw_cam = cv2.resize(raw_cam, (224, 224))
        colored_heatmap = np.uint8(255 * raw_cam)
        colored_heatmap = cv2.applyColorMap(colored_heatmap, cv2.COLORMAP_JET)

        return predicted_class, confidence, colored_heatmap, raw_cam