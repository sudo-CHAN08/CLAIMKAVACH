import os

DATASET_ROOT = "./dataset"
CLASSES = [
    "natural_fire",
    "inundation_flood",
    "lodging_cyclone_wind",
    "drought_dry_spell",
    "healthy_undamaged"
]

for split in ["train", "val"]:
    for cls in CLASSES:
        os.makedirs(os.path.join(DATASET_ROOT, split, cls), exist_ok=True)

print("Directories ready! Paste your downloaded images into their respective folders inside ml_pipeline/dataset/")
