# cam_regions.py
#
# Derives bounding boxes from a Grad-CAM activation map.
#
# WHAT THIS IS: weakly-supervised localization. The classifier was never
# trained on bounding boxes -- it only ever saw image-level labels. But
# Grad-CAM tells us which spatial regions drove the decision, so
# thresholding that map and taking connected components gives us regions
# the model actually attended to. This is the approach CheXNet used to
# produce localization from a classification-only model.
#
# WHAT THIS IS NOT: object detection. The boxes indicate "the model looked
# here", not "there is a lesion here with these exact borders". Every box
# carries the SAME class label, because the underlying model is binary --
# it cannot distinguish cardiomegaly from a nodule from an effusion.
# Say this plainly in your writeup; it's a meaningful limitation.

import cv2
import numpy as np


def extract_regions(raw_cam, label, overall_confidence,
                    threshold=0.55, min_area_frac=0.015, max_boxes=3):
    """
    raw_cam            : 2-D float array, values normalized 0-1 (as returned
                         by MedicalAIModel.predict_and_explain)
    label              : the predicted class string, e.g. "PNEUMONIA"
    overall_confidence : model confidence 0-1, used to scale region scores
    threshold          : activation cutoff. Higher = fewer, tighter regions.
    min_area_frac      : ignore blobs smaller than this fraction of the image,
                         which are usually noise rather than real focus areas
    max_boxes          : cap, keeping the strongest regions

    Returns a list of dicts with NORMALIZED coordinates (0-1), so the
    frontend can scale them to whatever size the image is displayed at:

        [{"x": .31, "y": .44, "w": .22, "h": .19,
          "label": "PNEUMONIA", "score": 0.83, "rank": 1}, ...]
    """
    if raw_cam is None or raw_cam.size == 0:
        return []

    h, w = raw_cam.shape[:2]
    total_area = float(h * w)

    # Normalize defensively -- callers should already have done this, but a
    # flat or unnormalized map would otherwise threshold to nothing/everything
    cam_min, cam_max = float(raw_cam.min()), float(raw_cam.max())
    if cam_max - cam_min < 1e-6:
        return []
    cam_norm = (raw_cam - cam_min) / (cam_max - cam_min)

    cam_uint8 = np.uint8(255 * cam_norm)

    # Light blur first so we get coherent blobs rather than speckle
    cam_blur = cv2.GaussianBlur(cam_uint8, (9, 9), 0)

    _, binary = cv2.threshold(cam_blur, int(threshold * 255), 255, cv2.THRESH_BINARY)

    # Close small gaps so one anatomical area doesn't fragment into 5 boxes
    kernel = np.ones((7, 7), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    regions = []
    for contour in contours:
        x, y, bw, bh = cv2.boundingRect(contour)

        if (bw * bh) / total_area < min_area_frac:
            continue

        # Region score = mean activation inside the box, scaled by how
        # confident the model was overall. A weakly-activated region on a
        # low-confidence prediction should not display as "91%".
        patch = cam_norm[y:y + bh, x:x + bw]
        mean_activation = float(patch.mean()) if patch.size else 0.0
        score = mean_activation * float(overall_confidence)

        regions.append({
            "x": round(x / w, 4),
            "y": round(y / h, 4),
            "w": round(bw / w, 4),
            "h": round(bh / h, 4),
            "label": label,
            "score": round(score, 4),
            "mean_activation": round(mean_activation, 4),
        })

    # Strongest first, then cap
    regions.sort(key=lambda r: r["score"], reverse=True)
    regions = regions[:max_boxes]

    for i, r in enumerate(regions, start=1):
        r["rank"] = i

    return regions