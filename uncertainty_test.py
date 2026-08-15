import torch
import torch.nn.functional as F
import numpy as np


def evaluate_prediction_uncertainty(model, input_tensor, num_mc_samples=25):
    """
    Evaluates the prediction uncertainty of a PyTorch medical imaging model.

    Args:
        model: Your trained PyTorch model (e.g., DenseNet121).
        input_tensor: Preprocessed image tensor of shape (1, C, H, W).
        num_mc_samples: Number of forward passes for Monte Carlo Dropout.

    Returns:
        dict: Contains mean predictions, confidence, Shannon entropy, and MC variance.
    """

    model.eval()
    with torch.no_grad():
        standard_logits = model(input_tensor)
        standard_probs = F.softmax(standard_logits, dim=1).squeeze()
        predicted_class = torch.argmax(standard_probs).item()
        standard_confidence = standard_probs[predicted_class].item()


    clamped_probs = torch.clamp(standard_probs, min=1e-7)
    shannon_entropy = -torch.sum(clamped_probs * torch.log(clamped_probs)).item()


    model.train()
    mc_predictions = []

    with torch.no_grad():
        for _ in range(num_mc_samples):
            mc_logits = model(input_tensor)
            mc_probs = F.softmax(mc_logits, dim=1).squeeze().cpu().numpy()
            mc_predictions.append(mc_probs)

    mc_predictions = np.array(mc_predictions)
    mc_mean_probs = np.mean(mc_predictions, axis=0)
    mc_variance = np.var(mc_predictions, axis=0)
    total_epistemic_uncertainty = np.mean(mc_variance)
    model.eval()

    return {
        "predicted_class": predicted_class,
        "standard_confidence": round(standard_confidence * 100, 2),
        "shannon_entropy": round(shannon_entropy, 4),
        "mc_mean_confidence": round(float(mc_mean_probs[predicted_class]) * 100, 2),
        "epistemic_uncertainty_score": round(float(total_epistemic_uncertainty), 6),
        "is_uncertain": shannon_entropy > 0.65 or total_epistemic_uncertainty > 0.01
    }


if __name__ == "__main__":
    import torchvision.models as models
    import torch.nn as nn
    from torchvision import transforms
    from PIL import Image
    import os


    print("⏳ Loading trained Router model...")
    device = torch.device('cpu')
    router_model = models.densenet121(weights=None)
    num_ftrs = router_model.classifier.in_features
    router_model.classifier = nn.Linear(num_ftrs, 3)  # 3 classes: bone, brain, chest

    model_path = 'best_router_model.pth'
    if os.path.exists(model_path):
        router_model.load_state_dict(torch.load(model_path, map_location=device))
        print("✅ Router weights successfully loaded!")
    else:
        print(f"❌ Error: Could not find '{model_path}' in your directory.")
        exit()


    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])


    sample_image_path = 'data/router_data/train/chest/chest_xray/train/NORMAL/IM-0115-0001.jpeg'


    if not os.path.exists(sample_image_path):
        print(f"⚠️ Sample image path not found. Please verify your folder path to run a test.")
        exit()

    img = Image.open(sample_image_path).convert('RGB')
    input_tensor = transform(img).unsqueeze(0)  # Shape becomes (1, 3, 224, 224)


    print("🧠 Running evaluation and Monte Carlo dropout passes...")
    results = evaluate_prediction_uncertainty(router_model, input_tensor, num_mc_samples=15)


    class_map = {0: "BONE (Fracture Dataset)", 1: "BRAIN (Tumor Dataset)", 2: "CHEST (X-Ray Dataset)"}

    print("\n===========================================")
    print("      🏥 CLINICAL UNCERTAINTY REPORT       ")
    print("===========================================")
    print(f"Predicted Organ Category : {class_map.get(results['predicted_class'], 'Unknown')}")
    print(f"Model Class Index        : {results['predicted_class']}")
    print(f"Standard Confidence      : {results['standard_confidence']}%")
    print(f"Shannon Entropy Score    : {results['shannon_entropy']}  (Lower = Confident Data)")
    print(f"MC Epistemic Variance   : {results['epistemic_uncertainty_score']}  (Lower = Stable Network)")
    print("-------------------------------------------")
    if results['is_uncertain']:
        print("🚨 FLAG STATUS           : YES - High Uncertainty Detected!")
        print("                           (Recommended for manual clinical review)")
    else:
        print("🟢 FLAG STATUS           : NO - Safe & Trustworthy Prediction")
    print("===========================================\n")