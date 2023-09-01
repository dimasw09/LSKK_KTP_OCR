from flask import Flask, render_template, request
import cv2
import pytesseract
import json
import numpy as np
from difflib import SequenceMatcher

app = Flask(__name__)

# Constants
THRESHOLD_VALUE = 170
LANG = "ind"
ALLOWED_FIELDS = ["NIK", "Nama"]
GROUND_TRUTH = {
    "NIK": "6104250903980001",
    "Nama": "HADI WIBOWO"
}

# Function Definitions (keep them the same)

def similarity_ratio(a, b):
    return SequenceMatcher(None, a, b).ratio()

def calculate_accuracy(ground_truth, extracted_text):
    return similarity_ratio(ground_truth, extracted_text) * 100

def extract_data(image_path):
    with open(image_path, "rb") as img_file:
        img = cv2.imdecode(np.frombuffer(img_file.read(), np.uint8), cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, threshed = cv2.threshold(gray, THRESHOLD_VALUE, 200, cv2.THRESH_BINARY)
    result = pytesseract.image_to_string(threshed, lang=LANG)
    cv2.imshow('ocr1', threshed)
    cv2.waitKey(0)
    # print(result)
    return result

def parse_extracted_data(extracted_text):
    data = {}
    lines = extracted_text.split("\n")
    for line in lines:
        print("Line:", line)  # Print the line for debugging
        for field in ALLOWED_FIELDS:
            if field in line:
                field_value = line.split(':', 1)
                if len(field_value) == 2:
                    field, value = field_value
                    data[field.strip()] = value.strip()
    return data


def filter_data(data):
    filtered_data = {field: data[field] for field in ALLOWED_FIELDS if field in data}
    return filtered_data

def create_json_data(image_file, filtered_data):
    ordered_data = {"nama_file": image_file, **filtered_data}
    json_data = json.dumps(ordered_data, indent=3)
    return json_data

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        image_file = request.files["image"]
        if image_file:
            try:
                img_np = np.fromfile(image_file, np.uint8)
                img = cv2.imdecode(img_np, cv2.IMREAD_COLOR)

                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                _, threshed = cv2.threshold(gray, THRESHOLD_VALUE, 200, cv2.THRESH_BINARY)
                extracted_text = pytesseract.image_to_string(threshed, lang=LANG)

                extracted_data = parse_extracted_data(extracted_text)
                filtered_data = filter_data(extracted_data)
                json_data = create_json_data(image_file.filename, filtered_data)

                nik_accuracy = calculate_accuracy(GROUND_TRUTH["NIK"], filtered_data.get("NIK", ""))
                nama_accuracy = calculate_accuracy(GROUND_TRUTH["Nama"], filtered_data.get("Nama", ""))

                return render_template("index.html", json_data=json_data, nik_accuracy=nik_accuracy, nama_accuracy=nama_accuracy)
            except Exception as e:
                error_message = str(e)
                return render_template("index.html", error_message=error_message)
        else:
            error_message = "No image uploaded."
            return render_template("index.html", error_message=error_message)
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
