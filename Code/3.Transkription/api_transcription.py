from openai import OpenAI
from dotenv import load_dotenv
import os
import base64

load_dotenv()

# API configuration
api_key = os.environ.get("API_KEY")
base_url = os.environ.get("API_ENDPOINT")

# Start OpenAI client
client = OpenAI(
    api_key=api_key,
    base_url=base_url
)

model = "qwen2.5-omni-7b"  # vision-capable model

IMAGES_ROOT = "images"
TEXT_ROOT = "texts"

# Supported image extensions
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tiff", ".bmp"}

os.makedirs(TEXT_ROOT, exist_ok=True)

def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

for root, _, files in os.walk(IMAGES_ROOT):
    for file in files:
        ext = os.path.splitext(file)[1].lower()
        if ext not in IMAGE_EXTENSIONS:
            continue

        image_path = os.path.join(root, file)

        # Preserve folder structure in /texts
        relative_path = os.path.relpath(root, IMAGES_ROOT)
        output_dir = os.path.join(TEXT_ROOT, relative_path)
        os.makedirs(output_dir, exist_ok=True)

        output_file = os.path.join(
            output_dir,
            os.path.splitext(file)[0] + ".txt"
        )

        # ✅ NEW: skip if transcription already exists
        if os.path.exists(output_file):
            print(f"Skipping (already transcribed): {output_file}")
            continue

        print(f"Transcribing: {image_path}")

        try:
            image_base64 = encode_image(image_path)

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "You are an OCR engine for historical Latin-script documents. You never output non-Latin characters.",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Please transcribe the text in this image exactly as it appears. "
                                    "Keep original orthography, punctuation, and line breaks. "
                                    "Do not translate, modernize, or add any extra text."
                                )
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ]
            )

            transcription = response.choices[0].message.content or ""

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(transcription)

        except Exception as e:
            print(f"❌ Error processing {image_path}: {e}")
