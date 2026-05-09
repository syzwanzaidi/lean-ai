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


def verify_step(reference_image_paths, current_image_path, step):
    for ref_path in reference_image_paths:
        if file_hash(ref_path) == file_hash(current_image_path):
            return {
                "status": "correct",
                "message": "Current image exactly matches one of the reference images."
            }

    must_have_text = "\n".join([f"- {item}" for item in step.get("must_have", [])])
    must_not_require_text = "\n".join([f"- {item}" for item in step.get("must_not_require", [])])

    prompt = f"""
You are an industrial assembly verification inspector.

You will receive:
- Several reference images showing acceptable correct versions of the current step
- One current image showing the user's assembly

Current Step:
Step {step["id"]}: {step["title"]}

Instruction:
{step["instruction"]}

Verification Goal:
{step["verification_goal"]}

Required visible conditions:
{must_have_text}

Do NOT require these for this step:
{must_not_require_text}

Strict rules:
1. Only judge the CURRENT STEP, not the final product.
2. The current image only needs to match ONE acceptable reference image.
3. Ignore position, rotation, cable shape, lighting, shadows, and background.
4. Do NOT invent missing screws/nuts/bolts unless they are clearly required in the Required visible conditions.
5. If a Required visible condition is clearly missing, return wrong.
6. If all Required visible conditions are visible, return correct.
7. If the image is blurry, blocked, or the part is outside the view, return waiting.
8. Be consistent and practical for a live showcase demo.

Return JSON only:
{{
  "status": "correct" | "wrong" | "waiting",
  "message": "short explanation"
}}
"""

    content = [{"type": "text", "text": prompt}]

    for index, ref_path in enumerate(reference_image_paths, start=1):
        content.append({"type": "text", "text": f"Reference image {index}:"})
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{encode_image(ref_path)}",
                "detail": "high"
            }
        })

    content.append({"type": "text", "text": "Current user assembly image:"})
    content.append({
        "type": "image_url",
        "image_url": {
            "url": f"data:image/jpeg;base64,{encode_image(current_image_path)}",
            "detail": "high"
        }
    })

    response = client.chat.completions.create(
        model=MODEL_NAME,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "user",
                "content": content
            }
        ],
        max_tokens=250
    )

    return extract_json(response.choices[0].message.content)