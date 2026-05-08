import os
import json
import re
import base64
import hashlib

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL_NAME = "gpt-4.1"
# If still inconsistent, change to:
# MODEL_NAME = "gpt-4.1"


def file_hash(image_path):
    with open(image_path, "rb") as file:
        return hashlib.md5(file.read()).hexdigest()


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def extract_json(text):
    try:
        return json.loads(text)
    except:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)

    if match:
        try:
            return json.loads(match.group())
        except:
            pass

    return {
        "status": "waiting",
        "message": "Unable to parse AI response."
    }


def verify_step(reference_image_path, current_image_path, instruction):
    if file_hash(reference_image_path) == file_hash(current_image_path):
        return {
            "status": "correct",
            "message": "Current image exactly matches the reference image."
        }

    reference_base64 = encode_image(reference_image_path)
    current_base64 = encode_image(current_image_path)

    prompt = f"""
You are a visual assembly verification system.

Compare two images:
- Image 1: Reference correct assembly for this step
- Image 2: Current user assembly

Instruction:
{instruction}

Decision rules:
1. Judge mainly by visible assembly shape and visible connected parts.
2. Ignore object position, rotation, angle, and small placement differences.
3. Ignore background, baskets, table, lighting, shadows, and camera crop differences.
4. Do NOT invent missing screws, nuts, bolts, or hidden parts unless they are clearly visible in Image 1 and clearly absent in Image 2.
5. If Image 2 shows the same visible assembly state as Image 1, return correct.
6. If Image 2 is clearly missing a major visible component compared to Image 1, return wrong.
7. If the object is blocked, blurry, or outside the image, return waiting.
8. Be practical for a showcase demo. Do not be overly strict.

Return JSON only:
{{
  "status": "correct" | "wrong" | "waiting",
  "message": "short explanation"
}}
"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{reference_base64}",
                            "detail": "high"
                        }
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{current_base64}",
                            "detail": "high"
                        }
                    }
                ]
            }
        ],
        max_tokens=250
    )

    text = response.choices[0].message.content
    return extract_json(text)