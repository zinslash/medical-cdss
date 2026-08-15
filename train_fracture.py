# train_fracture.py
#
# Trains the fracture-vs-normal model using the clean binary dataset
# (fractured / not fractured folders), reusing the already-fixed
# training logic from train_experts.py so it benefits from the same
# corrected transform and automatic class-map saving.

from train_experts import train_binary_diagnostic_model

if __name__ == "__main__":
    DATA_DIR = "D:/datasets dp 2/dataset 2/archive (3)/archive (6)/train"

    # Exact folder-name match — "not fractured" and "fractured" would be
    # ambiguous under substring matching (the first contains the second),
    # so we match the full folder name exactly instead.
    FRACTURE_LABEL_MAP = {
        "fractured": 1,
        "not fractured": 0,
    }

    train_binary_diagnostic_model(
        data_dir=DATA_DIR,
        output_filename="best_fracture_model.pth",
        positive_label="FRACTURE DETECTED",
        label_map=FRACTURE_LABEL_MAP
    )