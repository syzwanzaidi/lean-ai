import json
import os

ZONE_FILE = "zone_config.json"

DEFAULT_ZONE = {
    "x1_ratio": 0.32,
    "y1_ratio": 0.45,
    "x2_ratio": 0.68,
    "y2_ratio": 0.88
}

def load_zone():
    if os.path.exists(ZONE_FILE):
        with open(ZONE_FILE, "r") as file:
            return json.load(file)

    return DEFAULT_ZONE

def save_zone(zone):
    with open(ZONE_FILE, "w") as file:
        json.dump(zone, file, indent=4)