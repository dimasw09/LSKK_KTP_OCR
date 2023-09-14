from flask import Flask, render_template, request
import cv2
from PIL import Image
import pytesseract
import json
import numpy as np
from difflib import SequenceMatcher

app = Flask(__name__)

# Constants
THRESHOLD_VALUE = 125 
LANG = "ind"
ALLOWED_FIELDS = ["NIK", "Nama"]

# Function Definitions

def similarity_ratio(a, b):
    return SequenceMatcher(None, a, b).ratio()

def calculate_accuracy(ground_truth, extracted_text):
    return similarity_ratio(ground_truth, extracted_text) * 100

def extract_data(image_path):
    with open(image_path, "rb") as img_file:
        img = cv2.imdecode(np.frombuffer(img_file.read(), np.uint8), cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, threshed = cv2.threshold(gray, THRESHOLD_VALUE, 255, cv2.THRESH_BINARY)
    result = pytesseract.image_to_string(threshed, lang=LANG, config='--psm 6 --oem 3')
    return result

# def parse_extracted_data(extracted_text):
#     data = {}
#     lines = extracted_text.split("\n")
#     for line in lines:
#         for field in ALLOWED_FIELDS:
#             if field in line:
#                 field_value = line.split(':', 1)
#                 if len(field_value) == 2:
#                     field, value = field_value
#                     data[field.strip()] = value.strip()
#     return data
def parse_extracted_data(extracted_text):
    data = {}
    lines = extracted_text.split("\n")
    nik = ""
    nama = ""

    for line in lines:
        for field in ALLOWED_FIELDS:
            if field in line:
                field_value = line.split(':', 1)
                if len(field_value) == 2:
                    field, value = field_value
                    data[field.strip()] = value.strip()
                else:
                    # Jika ":" tidak ada, coba ambil angka sebagai NIK
                    nik_parts = line.split()
                    for part in nik_parts:
                        if part.isdigit() and len(part) >= 10:
                            nik = part
                            data["NIK"] = nik
                            break
                    # Jika bukan angka, anggap sebagai Nama
                    if not nik:
                        nama = line.strip()
                        data["Nama"] = nama

    return data


def filter_data(data):
    return {field: data[field] for field in ALLOWED_FIELDS if field in data}

def create_json_data(image_file, filtered_data):
    ordered_data = {"nama_file": image_file, **filtered_data}
    json_data = json.dumps(ordered_data, indent=3)
    return json_data

@app.route("/", methods=["GET","POST"])
def index():
    if request.method == "POST":
        image_file = request.files["image"]
        if image_file:
            try:
                # Menyimpan gambar di lokasi sementara
                image_temp_path = "temp_" + image_file.filename
                image_file.save(image_temp_path)

                # Mengubah ukuran gambar ke lebar 500 piksel dengan BILINEAR
                img = Image.open(image_temp_path)
                img = img.resize((3205, int(img.height * (3325 / img.width))), Image.BILINEAR)

                img_np = np.fromfile(image_temp_path, np.uint8)
                img = cv2.imdecode(img_np, cv2.IMREAD_COLOR)

                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                _, threshed = cv2.threshold(gray, THRESHOLD_VALUE, 200, cv2.THRESH_BINARY)
                extracted_text = pytesseract.image_to_string(threshed, lang=LANG, config='--psm 6 --oem 3')

                extracted_data = parse_extracted_data(extracted_text)
                filtered_data = filter_data(extracted_data)
                json_data = create_json_data(image_file.filename, filtered_data)

                # Menyimpan hasil thresholding (thresed) sebagai gambar
                result_image_path = "F:\KerjaPraktik\KTP-SCAN1\hasil threshold\T."+image_file.filename
                cv2.imwrite(result_image_path, threshed)

                return render_template("index.html", json_data=json_data, result=extracted_text)
            except Exception as e:
                error_message = str(e)
                return render_template("index.html", error_message=error_message)
        else:
            error_message = "No image uploaded."
            return render_template("index.html", error_message=error_message)

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
