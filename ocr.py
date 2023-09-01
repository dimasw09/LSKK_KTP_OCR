import cv2
import pytesseract
import json
import numpy as np
from difflib import SequenceMatcher

# Constants
IMAGE_FILE = "KTPscan/ktp (3).jpg"
THRESHOLD_VALUE = 170
LANG = "ind"
ALLOWED_FIELDS = ["NIK", "Nama"]
GROUND_TRUTH = {
    "NIK": "6104250903980001",
    "Nama": "HADI WIBOWO"
}

# Function Definitions
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

if __name__ == "__main__":
    image_file = IMAGE_FILE

    try:
        extracted_text = extract_data(image_file)
        print("Extracted Text:", extracted_text)  # Print the extracted text for debugging

        extracted_data = parse_extracted_data(extracted_text)
        filtered_data = filter_data(extracted_data)
        json_data = create_json_data(image_file, filtered_data)
        print(json_data)

        nik_accuracy = calculate_accuracy(GROUND_TRUTH["NIK"], filtered_data.get("NIK", ""))
        nama_accuracy = calculate_accuracy(GROUND_TRUTH["Nama"], filtered_data.get("Nama", ""))

        print("Akurasi NIK:", nik_accuracy, "%")
        print("Akurasi Nama:", nama_accuracy, "%")

    except FileNotFoundError:
        print("Image file not found.")
    except cv2.error as e:
        print("OpenCV Error:", str(e))
    except pytesseract.TesseractError as e:
        print("Tesseract Error:", str(e))
    except Exception as e:
        print("Error:", str(e))
