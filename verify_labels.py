"""
Run this once to generate the missing *_class_map.json files for your
ALREADY-TRAINED chest and router models, without retraining anything.

This works because torchvision's ImageFolder assigns label indices by
sorting folder names alphabetically — a deterministic rule. As long as
your dataset folders haven't been renamed/reorganized since you last
trained best_chest_model.pth and best_router_model.pth, this script
reconstructs the EXACT mapping those models were actually trained with.

If your folder structure HAS changed since training, this won't help —
you'll need to retrain using the updated train.py / train_router.py,
which now save this file automatically.
"""
import json
import os
from torchvision import datasets


def verify_and_save(data_dir, output_json):
    if not os.path.exists(data_dir):
        print(f"❌ Skipping '{output_json}': folder '{data_dir}' not found.")
        return

    dataset = datasets.ImageFolder(data_dir)
    class_to_idx = dataset.class_to_idx
    idx_to_class = {v: k for k, v in class_to_idx.items()}

    print(f"\n📋 {data_dir}")
    print(f"    class_to_idx: {class_to_idx}")
    print(f"    -> saving as: {output_json}")

    with open(output_json, 'w') as f:
        json.dump(idx_to_class, f, indent=2)


if __name__ == "__main__":
    # Adjust these paths if your folder structure differs
    verify_and_save('data/chest_xray/train', 'best_chest_model_class_map.json')
    verify_and_save('data/router_data/train', 'router_class_map.json')

    print("\n✅ Done. Compare the printed class_to_idx above against what you "
          "EXPECT (e.g. chest should show something like "
          "{'NORMAL': 0, 'PNEUMONIA': 1}). If the label names or order look "
          "wrong, that confirms the folder names/structure themselves need "
          "fixing, not just the code.")