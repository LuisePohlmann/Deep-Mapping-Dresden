from openai import OpenAI
from dotenv import load_dotenv
import os
import csv
import time
import re
import sys

# Load environment variables
load_dotenv()

api_key = os.environ.get("API_KEY")
base_url = os.environ.get("API_ENDPOINT")

client = OpenAI(api_key=api_key, base_url=base_url)

model = "openai-gpt-oss-120b"

main_txt_folder = r"C:\Users\Mirco\Desktop\Luise\reiseberichte_dresden\texts"

# Create sibling output folder "NER" next to "texts"
project_root = os.path.dirname(main_txt_folder.rstrip("\\/"))
ner_root = os.path.join(project_root, "NER")
os.makedirs(ner_root, exist_ok=True)

processed_files = 0
MAX_FILES = None  # set None or large number to process all

def is_api_limit_exceeded_error(e: Exception) -> bool:
    msg = str(e).lower()
    return (
        "api limit exceeded" in msg
        or "rate limit" in msg
        or "too many requests" in msg
        or "429" in msg
        or "insufficient_quota" in msg
        or "quota" in msg
    )

def strip_code_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    return s.strip()

def run_one_file(text: str) -> str:
    prompt = (
        "Finde alle named entities im folgenden Text und bestimme deren Typ. "
        "Für Orte: recherchiere online mit dem Zusatz 'Dresden', ob es einen Wikipedia Artikel "
        "oder eine andere Quelle gibt, die den historischen Ort bestätigt. "
        "Wenn du nichts findest, lasse die Spalte leer. "
        "Gib das Ergebnis als CSV mit drei Spalten zurück: 'Entity', 'Type', 'Link'."
    )

    resp = client.chat.completions.create(
        model=model,
        temperature=0.0,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": f"{prompt}\n\n{text}"},
        ],
    )
    return resp.choices[0].message.content.strip()

def write_csv_from_model_output(content: str, csv_path: str) -> None:
    content = strip_code_fences(content)
    lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
    if not lines:
        raise ValueError("Model returned empty content.")

    # Detect delimiter
    sample = "\n".join(lines[:5])
    delim = ";" if sample.count(";") > sample.count(",") else ","

    os.makedirs(os.path.dirname(csv_path), exist_ok=True)

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # Ensure header exists
        writer.writerow(["Entity", "Type", "Link"])

        reader = csv.reader(lines, delimiter=delim)
        for row in reader:
            row = [c.strip() for c in row if c is not None]
            if not row:
                continue
            # Skip header if model included it
            low = [c.lower() for c in row]
            if len(low) >= 2 and "entity" in low[0] and "type" in low[1]:
                continue

            if len(row) >= 3:
                writer.writerow([row[0], row[1], row[2]])
            elif len(row) == 2:
                writer.writerow([row[0], row[1], ""])
            else:
                print(f"⚠️ Skipped malformed row: {row}")

stop_all = False

# Walk through the texts folder and process .txt files directly inside any subfolder
for root, dirs, files in os.walk(main_txt_folder):
    if stop_all:
        break

    # Skip the base folder itself if you only want subfolders
    # (optional; harmless either way)
    # if os.path.abspath(root) == os.path.abspath(main_txt_folder):
    #     continue

    txt_files = [f for f in files if f.lower().endswith(".txt")]
    if not txt_files:
        continue

    # Output folder mirrors the structure under texts/
    rel_root = os.path.relpath(root, main_txt_folder)
    out_folder = os.path.join(ner_root, rel_root)
    os.makedirs(out_folder, exist_ok=True)

    for file in txt_files:
        if MAX_FILES is not None and processed_files >= MAX_FILES:
            break
        if stop_all:
            break

        file_path = os.path.join(root, file)

        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

        csv_path = os.path.join(out_folder, os.path.splitext(file)[0] + ".csv")

                # ✅ NEW: skip if transcription already exists
        if os.path.exists(csv_path):
            print(f"Skipping (already transcribed): {csv_path}")
            continue

        attempt = 0
        while True:
            try:
                attempt += 1
                content = run_one_file(text)
                write_csv_from_model_output(content, csv_path)
                print(f"✅ Saved: {csv_path}")
                processed_files += 1
                break

            except Exception as e:
                if is_api_limit_exceeded_error(e):
                    if attempt == 1:
                        print("⚠️ API limit exceeded. Waiting 60 minutes, then retrying once...")
                        time.sleep(60 * 60)
                        continue
                    else:
                        print("❌ API limit exceeded again on retry. Stopping script.")
                        stop_all = True
                        break
                else:
                    print(f"❌ Failed to process {file_path}: {e}")
                    break

    if MAX_FILES is not None and processed_files >= MAX_FILES:
        break

print(f"🎉 All done! Processed {processed_files} files.")
print(f"📁 Results saved under: {ner_root}")
