import cv2
import pytesseract
import json
from difflib import SequenceMatcher

def similarity_ratio(a, b):
    return SequenceMatcher(None, a, b).ratio()

def calculate_accuracy(ground_truth, extracted_text):
    return similarity_ratio(ground_truth, extracted_text) * 100

def extract_data(image_path):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, threshed = cv2.threshold(gray, 190, 150, cv2.THRESH_BINARY)
    result = pytesseract.image_to_string(threshed, lang="ind")
    cv2.imshow('ocr1',gray)
    cv2.waitKey(0)

    return result

def parse_extracted_data(extracted_text):
    data = {}
    lines = extracted_text.split("\n")
    for line in lines:
        if "NIK" in line or "Nama" in line:
            field, value = line.split(': ', 1)
            data[field] = value.strip()
    return data

def filter_data(data):
    allowed_fields = ["NIK", "Nama"]
    filtered_data = {field: data[field] for field in allowed_fields if field in data}
    return filtered_data

def create_json_data(image_file, filtered_data):
    ordered_data = {"nama_file": image_file, **filtered_data}
    json_data = json.dumps(ordered_data, indent=3)
    return json_data

if __name__ == "__main__":
    image_file = "KTPscan/ktp (1).jpeg"

    try:
        extracted_text = extract_data(image_file)
        extracted_data = parse_extracted_data(extracted_text)
        filtered_data = filter_data(extracted_data)
        json_data = create_json_data(image_file, filtered_data)
        print(json_data)

        ground_truth_nik = "3205020801000001"
        ground_truth_nama = "RIFQI SEFTIAN"

        extracted_nik = extracted_data.get("NIK", "")
        extracted_nama = extracted_data.get("Nama", "")

        nik_accuracy = calculate_accuracy(ground_truth_nik, extracted_nik)
        nama_accuracy = calculate_accuracy(ground_truth_nama, extracted_nama)

        print("Akurasi NIK:", nik_accuracy, "%")
        print("Akurasi Nama:", nama_accuracy, "%")

    except cv2.error as e:
        print("OpenCV Error:", str(e))
    except pytesseract.TesseractError as e:
        print("Tesseract Error:", str(e))
    except Exception as e:
        print("Error:", str(e))
