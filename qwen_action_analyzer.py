import os
import json
import re
import ollama
from PIL import Image

MODEL_NAME = "qwen2.5vl:7b"


def extract_json(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)

    if match:
        try:
            return json.loads(match.group())
        except:
            pass

    return {
        "action_name": "ASSEMBLE",
        "description": "Assembly activity detected.",
        "lean_type": "VA"
    }


def resize_image(image_path):
    os.makedirs("captured/qwen", exist_ok=True)

    img = Image.open(image_path).convert("RGB")
    img.thumbnail((512, 512))

    output_path = "captured/qwen/qwen_input.jpg"
    img.save(output_path)

    return output_path


def analyze_action(image_path, step):
    image_path = resize_image(image_path)

    response = ollama.chat(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": f"""
You are analyzing a manufacturing assembly image.

Current step:
{step["title"]}

Instruction:
{step["instruction"]}

Identify the specific action shown in the image.

Allowed action_name values:
PICK, PLACE, ASSEMBLE, ADJUST, INSPECT, IDLE, REWORK, USE_TOOL

Rules:
- Do not use VA/NVA/NNVA as action_name.
- lean_type must be VA, NVA, or NNVA.
- VA = assembling, inserting, attaching, placing correct parts
- NVA = idle, waiting, searching, rework
- NNVA = inspecting, verifying, adjusting, preparing

Return JSON only:
{{
  "action_name": "one allowed action label",
  "description": "specific short description",
  "lean_type": "VA | NVA | NNVA"
}}
""",
                "images": [image_path]
            }
        ]
    )

    return extract_json(response["message"]["content"])