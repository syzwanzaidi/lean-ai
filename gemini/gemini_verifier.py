import os
import json
import re
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

MODEL_NAME = "gemini-2.5-flash"


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
    prompt = f"""
You are an industrial assembly verification assistant.

Task:
Compare the reference image with the current image.

Instruction for this step:
{instruction}

Rules:
- If the current assembly matches the reference image for this step, return status correct.
- If it does not match, return status wrong.
- If the image is unclear or incomplete, return status waiting.
- Focus only on the assembled object, not the background.
- Be strict but reasonable.

Return JSON only:
{{
  "status": "correct" | "wrong" | "waiting",
  "message": "short explanation"
}}
"""

    with open(reference_image_path, "rb") as ref_file:
        reference_bytes = ref_file.read()

    with open(current_image_path, "rb") as cur_file:
        current_bytes = cur_file.read()

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[
            prompt,
            types.Part.from_bytes(
                data=reference_bytes,
                mime_type="image/jpeg"
            ),
            types.Part.from_bytes(
                data=current_bytes,
                mime_type="image/jpeg"
            ),
        ],
    )

    return extract_json(response.text)